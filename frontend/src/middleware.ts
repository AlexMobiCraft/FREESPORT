/**
 * Next.js Middleware - защита маршрутов и настоящий HTTP 404
 *
 * Edge Runtime - совместимый код (только Web APIs)
 * Проверяет authenticated routes и редиректит неавторизованных пользователей на /login.
 * Дополнительно возвращает настоящий 404 на несуществующие адреса верхнего уровня:
 * App Router фиксирует статус до вызова notFound(), а middleware выполняется
 * до стриминга и статус вернуть может.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { isSafeRedirectUrl } from '@/utils/urlUtils';

/**
 * Односегментные маршруты, которые обслуживает сам Next.js.
 *
 * Список сверяется с фактической структурой `src/app` тест-стражем
 * `src/__tests__/app-routes-allowlist.test.ts`: добавил страницу верхнего уровня —
 * добавь её сюда, иначе она начнёт отдавать 404.
 *
 * `electric-orange` страницей НЕ является: это rewrite на статику
 * `public/electric-orange/index.html` (`next.config.ts`). Rewrites из
 * `next.config.ts` (afterFiles) выполняются ПОСЛЕ middleware, поэтому без записи
 * здесь рабочий адрес превратится в 404. Не удалять как «лишний».
 *
 * `/product`, `/orders` и `/b2b-dashboard` сюда намеренно не входят — страниц под
 * такими путями нет.
 */
export const KNOWN_TOP_LEVEL_ROUTES: ReadonlySet<string> = new Set([
  'about',
  'b2b-register',
  'blog',
  'cart',
  'catalog',
  'checkout',
  'coming-soon',
  'delivery',
  'design-comparison',
  'electric',
  'electric-orange',
  'electric-orange-test',
  'examples',
  'home',
  'login',
  'news',
  'partners',
  'password-reset',
  'privacy-policy',
  'profile',
  'register',
  'requisites',
  'search',
  'test',
]);

/**
 * Время жизни кэша списка опубликованных CMS-слагов.
 *
 * Нижняя граница задаётся ценой промаха: каждый промах — сетевой запрос на пути
 * HTML-ответа. Верхняя — требованием видимости: вновь опубликованная в админке
 * страница обязана открыться «не позднее TTL», и ждать час редактор не должен.
 * Пять минут дают ~12 запросов в час независимо от трафика.
 */
const SLUG_CACHE_TTL_MS = 5 * 60 * 1000;

/** Предельное время ожидания списка слагов: недоступный backend не должен подвешивать сайт */
const SLUGS_FETCH_TIMEOUT_MS = 2000;

/** Размер страницы выдачи: DRF по умолчанию отдаёт 20 записей, этого мало */
const SLUGS_PAGE_SIZE = 1000;

interface SlugCache {
  slugs: Set<string>;
  fetchedAt: number;
}

/** Кэш в памяти модуля: middleware не имеет доступа к Data Cache Next.js */
let slugCache: SlugCache | null = null;

/** Текущий запрос за списком — схлопывает параллельные промахи кэша в один вызов API */
let inflightSlugsRequest: Promise<Set<string> | null> | null = null;

/**
 * Базовый URL API для запроса из middleware.
 *
 * ВАЖНО: в edge-бандл middleware переменные подставляются на этапе СБОРКИ, и
 * попадают туда только `NEXT_PUBLIC_*`. Поэтому `INTERNAL_API_URL`, с которого
 * начинают цепочку серверные компоненты (`app/sitemap.ts`, `(blue)/[slug]/page.tsx`),
 * здесь неприменим — в собранном middleware он будет undefined.
 */
function getApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL_INTERNAL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://backend:8000/api/v1'
  );
}

/**
 * Забирает список опубликованных CMS-слагов.
 * Возвращает `null`, если список получить не удалось — вызывающий обязан
 * трактовать это как «не знаю» и пропустить запрос дальше (fail-open).
 */
async function fetchPublishedSlugs(): Promise<Set<string> | null> {
  const url = `${getApiBaseUrl()}/pages/?page_size=${SLUGS_PAGE_SIZE}`;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(SLUGS_FETCH_TIMEOUT_MS) });

    if (!res.ok) {
      console.warn(`[middleware] Список CMS-слагов недоступен: HTTP ${res.status}`);
      return null;
    }

    const data = (await res.json()) as { results?: unknown };

    if (!Array.isArray(data.results)) {
      console.warn('[middleware] Ответ со списком CMS-слагов не разобрался');
      return null;
    }

    const slugs = new Set<string>();
    for (const item of data.results as Array<{ slug?: unknown }>) {
      if (item && typeof item.slug === 'string') slugs.add(item.slug);
    }

    return slugs;
  } catch (error) {
    console.warn('[middleware] Не удалось получить список CMS-слагов:', error);
    return null;
  }
}

/** Обновляет кэш, схлопывая параллельные вызовы в один запрос к API */
function refreshSlugCache(): Promise<Set<string> | null> {
  if (inflightSlugsRequest) return inflightSlugsRequest;

  inflightSlugsRequest = fetchPublishedSlugs()
    .then(slugs => {
      if (slugs) slugCache = { slugs, fetchedAt: Date.now() };
      return slugs;
    })
    .finally(() => {
      inflightSlugsRequest = null;
    });

  return inflightSlugsRequest;
}

/**
 * Отдаёт список опубликованных слагов.
 *
 * Свежий кэш возвращается сразу; протухший тоже возвращается сразу, а обновление
 * идёт фоном (stale-while-revalidate) — протухание не должно добавлять задержку
 * в запрос пользователя. Пустой кэш приходится ждать.
 */
async function getPublishedSlugs(): Promise<Set<string> | null> {
  if (slugCache) {
    const isStale = Date.now() - slugCache.fetchedAt > SLUG_CACHE_TTL_MS;
    if (isStale) {
      // Фоновое обновление обязано глотать свои ошибки, иначе unhandled rejection
      void refreshSlugCache().catch(() => null);
    }
    return slugCache.slugs;
  }

  return refreshSlugCache();
}

/**
 * Возвращает единственный сегмент пути или null.
 *
 * Один сегмент — в точности зона перехвата catch-all `(blue)/[slug]`.
 * Корень и многосегментные пути Next обрабатывает сам и на несуществующие
 * из них уже отдаёт 404.
 */
function getSingleSegment(pathname: string): string | null {
  const segments = pathname.split('/').filter(Boolean);
  return segments.length === 1 ? segments[0] : null;
}

/**
 * Проверяет, является ли маршрут защищенным
 */
function isProtectedRoute(pathname: string): boolean {
  const protectedPaths = ['/profile', '/orders', '/b2b-dashboard'];
  return protectedPaths.some(path => pathname.startsWith(path));
}

/**
 * Проверяет, является ли маршрут публичным (auth routes)
 */
function isAuthRoute(pathname: string): boolean {
  const authPaths = ['/login', '/register', '/password-reset', '/b2b-register'];
  return authPaths.some(path => pathname.startsWith(path));
}

/**
 * Middleware function
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Проверяем наличие refresh token в cookies
  // ВАЖНО: В Edge Runtime нет доступа к localStorage, используем cookies
  const refreshToken = request.cookies.get('refreshToken')?.value;
  const isAuthenticated = !!refreshToken;

  // Если это protected route и пользователь не авторизован - редирект на /login
  if (isProtectedRoute(pathname) && !isAuthenticated) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';

    // Сохраняем исходный путь для редиректа после входа
    // НЕ добавляем next параметр, если уже на /login (предотвращение бесконечного редиректа)
    if (pathname !== '/login') {
      url.searchParams.set('next', pathname);
    }

    return NextResponse.redirect(url);
  }

  // Если пользователь авторизован и пытается открыть auth route - редирект на главную
  if (isAuthRoute(pathname) && isAuthenticated) {
    const url = request.nextUrl.clone();
    const nextParam = url.searchParams.get('next') || url.searchParams.get('redirect');

    // Если есть next/redirect параметр и он валидный
    if (isSafeRedirectUrl(nextParam)) {
      return NextResponse.redirect(new URL(nextParam!, request.url));
    }

    url.pathname = '/';
    return NextResponse.redirect(url);
  }

  // Настоящий 404 вместо soft-404 из catch-all `(blue)/[slug]`.
  // Проверка идёт последней: редиректы выше не должны ждать сетевой запрос.
  const segment = getSingleSegment(pathname);
  if (segment && !KNOWN_TOP_LEVEL_ROUTES.has(segment)) {
    const publishedSlugs = await getPublishedSlugs();

    if (publishedSlugs === null) {
      // Fail-open: список получить не удалось — вслепую 404 не отдаём,
      // иначе недоступный backend превратит весь сайт в 404.
      console.warn(`[middleware] Проверка адреса ${pathname} пропущена: список слагов недоступен`);
      return NextResponse.next();
    }

    if (!publishedSlugs.has(segment)) {
      // Rewrite на внутренний маршрут `/_not-found` со статусом 404: Next
      // переносит статус ответа middleware на ответ (resolve-routes) и рендерит
      // `app/not-found.tsx` (base-server). Если статус когда-нибудь перестанет
      // переноситься — запасной вариант в стори 41.0: rewrite на заведомо
      // несуществующий ДВУХсегментный путь (односегментный перехватит catch-all).
      return NextResponse.rewrite(new URL('/_not-found', request.url), { status: 404 });
    }
  }

  return NextResponse.next();
}

/**
 * Matcher config - определяет маршруты, к которым применяется middleware
 *
 * ВАЖНО: Matcher запускается для ВСЕХ указанных путей
 * Внутри middleware мы делаем дополнительную проверку
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico (favicon)
     * - public folder
     * - API routes (handled separately)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\..*|api/).*)',
  ],
};
