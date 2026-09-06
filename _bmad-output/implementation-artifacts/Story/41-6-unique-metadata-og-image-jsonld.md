---
baseline_commit: "4e386a95"
review_head: "" # пусто: правки ревью 2026-09-06 коммитит владелец, значение ставится после коммита
# Канонический changeset стори. Область приёмки =
#   git log --oneline baseline_commit..review_head  МИНУС excluded_commits.
# baseline_commit заполняется в Task 1 фактическим HEAD ветки на момент старта
# (см. callout про зависимость от стори 41.4 — до её мержа в develop
# frontend/src/config/contacts.ts в базе отсутствует).
# review_head устанавливается один раз по завершении содержательной работы и
# НЕ сдвигается документационными правками метаданных.
excluded_commits: []
---

# Story 41.6: Уникальные метаданные, корректное соцпревью и JSON-LD

Status: review

> 🔴 **`og-image.jpg` НЕ является неиспользуемым — премиса AC эпика неверна.** Файл читают два живых компонента: `frontend/src/components/home/HeroSection.tsx:178` (статическая ветка hero, когда баннеров из API нет) и `frontend/src/components/home/ElectricHeroSection.tsx:162` (fallback `currentBanner?.image_url || '/og-image.jpg'`). Простое `rm` даст битую картинку на `/home` и `/electric` в момент недоступности API баннеров — то есть ровно тогда, когда сайт и так деградировал. Решение стори: **переименовать** файл в `hero-fallback.jpg` и поправить обе ссылки. Имя `og-image.jpg` исчезает (буква AC выполнена), превью остаётся ровно одно — `/image.jpg` (смысл AC выполнен), hero не ломается. Альтернатива «удалить файл и подставить в hero `/image.jpg`» отвергнута: `image.jpg` — соцпревью 1040×680, а hero рисует картинку в `aspect-[7/4]` с `object-cover`; это два разных назначения у одного файла.
> 🔴 **Из `/login` нельзя экспортировать `metadata` — это Client Component.** `frontend/src/app/(blue)/(auth)/login/page.tsx:11` начинается с `'use client'` (нужны `useSearchParams`, `useRouter`, Zustand). Next.js собирает метаданные только из серверных модулей. Приём, уже применённый в проекте: метаданные выносятся в `layout.tsx` сегмента (`frontend/src/app/(blue)/catalog/layout.tsx:5-14`, там прямым текстом написано почему). Значит заводится **новый** `frontend/src/app/(blue)/(auth)/login/layout.tsx`. «Сделать страницу серверной» — не вариант: это сломает форму входа.
> 🔴 **Единственное место, где размеры `og:image` сегодня объявлены, объявляет их неверно.** `frontend/src/app/(electric)/electric/page.tsx:60-63` пишет `width: 1200, height: 630` для `/image.jpg`, у которого фактический размер **1040×680**. Это прямое нарушение AC «объявленные размеры совпадают с фактическими размерами файла», и его нельзя закрыть, тронув только корневой layout. Правится тем же коммитом.
> ⚠️ **`buildMetadata` — risk CRITICAL.** `npx gitnexus impact buildMetadata --direction upstream --repo "C:\Users\1\DEV\FREESPORT"` (индекс на `17e17d9e`): **14 прямых вызывающих**, 6 затронутых процессов, 2 модуля, `"risk": "CRITICAL"`. Из-за этого **сигнатура не меняется**: добавляются необязательные поля в тип `PageSeoOptions['image']` и нормализация значения по умолчанию внутри функции. Ни один из 14 вызовов править не требуется — именно поэтому выбран этот способ, а не «пусть каждая страница объявляет размеры сама».
> ⚠️ **Ломаются четыре существующих теста** (их правка — часть стори, а не побочный ущерб): `about/__tests__/page.test.tsx:180,192` (`title` toBe `'О компании'`), `home/__tests__/page.test.tsx:175` (`openGraph.images` `toContain('/image.jpg')`), `blog/[slug]/__tests__/page.test.tsx:282` и `news/[slug]/__tests__/page.test.tsx:227` (`toEqual(['/image.jpg'])`). Полный разбор — в Dev Notes, таблица «Тесты: что сломается».
> ⚠️ **`SearchAction` в `WebSite` НЕ добавлять.** Стандартный соблазн при разметке `WebSite` — `potentialAction: SearchAction` на `/search?q=`. Здесь это ложь роботу: `/search` перечислен в `Disallow` (`frontend/src/app/robots.ts:24`), а sitelinks searchbox требует индексируемую страницу результатов. Разметка ограничивается `name`, `url`, `inLanguage`, `publisher`.
> ⚠️ **Зависимость от стори 41.4.** JSON-LD берёт телефон и почту из `frontend/src/config/contacts.ts` — файла, созданного стори 41.4. На 2026-09-05 её ветка `feature/story-41-4-checkout-trade-info` в `develop` **не влита** (`develop` = `87b00945`). Ветку 41.6 заводить от `develop` **после** мержа PR стори 41.4; если старт раньше — контакты пришлось бы продублировать, чего делать не нужно.
> 🚫 **Стори не трогает бэкенд.** Сериализаторы, `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`, миграции, модель `Page` — вне объёма. **NFR-41-02 не задействуется**, `npm run generate:types` не запускается.
> 🚫 **`robots.ts`, `sitemap.ts`, `middleware.ts` и `next.config.ts` не меняются.** `/coming-soon`, `/login` и `/search` остаются в `Disallow` в том же виде. Disallow — не замена уникальному `title`: соцсети и сканер аудита читают метатеги независимо от robots.txt, а «поставить `noindex` вместо заголовка» требование FR-41-11 не закрывает.

## Story

As a **пользователь поиска и соцсетей**,
I want **видеть осмысленный заголовок, описание и превью страницы**,
so that **понимать, куда веду, ещё до перехода**.

**Закрывает:** FR-41-11, FR-41-12, FR-41-13, FR-41-14. **Соблюдает:** NFR-41-01, NFR-41-03.

## Acceptance Criteria

### AC1 (FR-41-11) — собственные метаданные у `/coming-soon`

**Given** страница `/coming-soon`
**When** запрашиваются её метаданные
**Then** `title` — `OPTISPORT скоро откроется — оптовые продажи спорттоваров`
**And** `description` — `OPTISPORT — оптовые и розничные продажи спортивных товаров. Сайт скоро откроется, по вопросам сотрудничества пишите на info@optisport.ru.`
**And** оба значения отличаются от значений корневого layout (`app/layout.tsx:20-22`)
**And** метаданные собраны через `buildMetadata` с `path: '/coming-soon'` — то есть страница получает и `canonical`, и `og:*`, и `twitter:*`
**And** `robots` для этой страницы **не** задаётся: она остаётся ровно в том состоянии индексируемости, что и до стори

### AC2 (FR-41-11) — собственные метаданные у `/login`

**Given** страница `/login`
**When** запрашиваются её метаданные
**Then** `title` — `Вход в личный кабинет | OPTISPORT`
**And** `description` — `Вход в личный кабинет OPTISPORT для оптовых клиентов: заказы, цены по вашей роли, история отгрузок и документы.`
**And** метаданные объявлены в **новом** `frontend/src/app/(blue)/(auth)/login/layout.tsx`, а `page.tsx` остаётся клиентским и не меняется
**And** layout рендерит только `children` — никакой разметки, обёрток и провайдеров он не добавляет
**And** задан `noIndex: true` — по образцу `/cart` (`cart/page.tsx:16-19`) и `/checkout`: страница уже в `Disallow` robots.txt, и разметка обязана говорить то же самое
**And** форма входа, редирект аутентифицированного пользователя и поддержка `?next=`/`?redirect=` работают как прежде

### AC3 (FR-41-12) — `title` страницы «О компании» в диапазоне 30–60 символов

**Given** страница `/about`
**When** проверяется `title`
**Then** он равен `О компании OPTISPORT — оптовый поставщик спорттоваров` (53 символа)
**And** его длина находится в диапазоне 30–60 символов, и это закреплено тестом как **диапазон**, а не только как точная строка (замена формулировки не должна молча вывести title за границу)
**And** `description` страницы **не** меняется — три существующие проверки на её содержимое (`about/__tests__/page.test.tsx:184-187`) остаются зелёными без правок
**And** `openGraph.title` совпадает с `title` (следствие `buildMetadata`, отдельной правки не требует)

### AC4 (FR-41-13) — `og:image` с объявленными размерами, совпадающими с файлом

**Given** любая страница, отдающая соцпревью по умолчанию (`/home`, `/about`, `/catalog`, `/coming-soon`, `/electric`, статья блога без своей картинки)
**When** проверяются метатеги
**Then** присутствуют `og:image`, `og:image:width`, `og:image:height` и `og:image:type`
**And** значения — `1040`, `680` и `image/jpeg` соответственно
**And** они совпадают с фактическими параметрами `frontend/public/image.jpg`, и это доказано тестом, который **читает файл** и разбирает его заголовок, а не сверяет две константы между собой
**And** источник значений — один: константы в `frontend/src/utils/seo.ts`; ни одна страница не объявляет размеры сама
**And** `frontend/src/app/(electric)/electric/page.tsx` больше не содержит `width: 1200, height: 630`
**And** страницы со **своей** картинкой (карточка товара, статья блога/новости с `image`) размеров не получают — их габариты неизвестны, объявлять их было бы ложью

### AC5 (FR-41-13) — одно превью, один файл, hero не сломан

**Given** каталог `frontend/public`
**When** стори завершена
**Then** файла `og-image.jpg` в нём нет
**And** файл `hero-fallback.jpg` существует и байт в байт совпадает с прежним `og-image.jpg` (переименование через `git mv`, а не пересохранение)
**And** в `frontend/src` не остаётся ни одной ссылки на **путь** `/og-image` — проверяется регулярным выражением `(^|[^\w-])og-image`, а не голым `grep -rn "og-image"`: подстрока `og-image` входит в имя чужой фикстуры `blog-image.jpg` (`blog/[slug]/__tests__/page.test.tsx:57,273`), которую Task 9 прямо запрещает трогать, поэтому буквальный grep не может быть пустым в принципе
**And** `HeroSection.tsx` и `ElectricHeroSection.tsx` ссылаются на `/hero-fallback.jpg`, и обе fallback-ветки продолжают показывать картинку
**And** единственный файл соцпревью — `/image.jpg`, и он же остаётся значением `DEFAULT_OG_IMAGE`

### AC6 (FR-41-14) — JSON-LD `Organization` и `WebSite` на публичных страницах

**Given** любая страница сайта
**When** проверяется разметка
**Then** в документе присутствует ровно **один** блок `<script type="application/ld+json">` **уровня сайта** — то есть один корневой `@graph`
**And** требование «ровно один» относится именно к разметке уровня сайта: маршрутные схемы отдельных страниц (существующий `Product` в `ProductPageClient.tsx:81`) остаются допустимыми и под это ограничение не подпадают — на карточке товара блоков ld+json будет два, и это корректно (решение владельца по находке ревью, вариант 1: код вывода JSON-LD не меняется)
**And** в `@graph` два узла: `@type: "Organization"` и `@type: "WebSite"`
**And** `Organization` содержит `@id`, `name`, `url`, `logo` (объект `ImageObject` с фактическими `width`/`height` файла `/LOGO_OPTIsport.png` — 1014×101), `email`, `telephone`, `address` (`PostalAddress` с `addressCountry: 'RU'`), `sameAs`
**And** `telephone` и `email` берутся из `frontend/src/config/contacts.ts` — новых копий контактов не заводится
**And** `WebSite` содержит `@id`, `name`, `url`, `inLanguage: 'ru-RU'` и `publisher` со ссылкой `{'@id': <@id организации>}` — то есть узлы связаны, а не лежат рядом
**And** `potentialAction`/`SearchAction` **отсутствует** (см. callout)
**And** все абсолютные URL строятся из `SITE_URL`/`absoluteUrl` (`utils/seo.ts:11,60`), домен `optisport.ru` в разметке не захардкожен
**And** разметка проходит валидатор schema.org без ошибок — проверка выполняется вставкой сгенерированного JSON в https://validator.schema.org (режим Code snippet), результат фиксируется в Dev Agent Record

### AC7 (NFR-41-01) — тесты

**Given** изменённый код
**When** прогоняется `npm run test`
**Then** все тесты зелёные, включая четыре приведённых к новым значениям (`about`, `home`, `blog/[slug]`, `news/[slug]`)
**And** существует тест-страж, который падает, если размеры в `seo.ts` разойдутся с файлом `public/image.jpg`
**And** существует тест, который падает, если `public/og-image.jpg` вернётся или если в `src/` появится ссылка на него
**And** метаданные `/coming-soon`, `/login` и `/about` покрыты тестами на конкретные значения (AC1–AC3)
**And** JSON-LD покрыт тестом на состав узлов и связь `publisher → @id` (AC6)
**And** `npm run lint`, `npm run format:check` и `npx tsc --noEmit` проходят без ошибок

### AC8 (границы) — что стори НЕ делает

**Then** **не** трогается бэкенд, `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`; `npm run generate:types` не запускается
**And** **не** меняются `frontend/src/app/robots.ts`, `frontend/src/app/sitemap.ts`, `frontend/src/middleware.ts`, `frontend/next.config.ts`, `docker/nginx/**`
**And** **не** добавляются метаданные страницам `/register`, `/b2b-register`, `/profile/*`, `/test`, `/examples`, `/design-comparison`, `/electric-orange-test`, `/electric/catalog` — они тоже наследуют корневые значения, но FR-41-11 сужен до двух страниц решением 2026-08-24; факт записывается в `deferred-work.md`
**And** **не** переснимается и не пересохраняется `public/image.jpg` — приведение к эталонным 1200×630 требует нового файла от владельца и в объём не входит; стори объявляет **фактические** размеры и делает так, что при замене файла достаточно поменять две константы
**And** **не** мигрируется на `config/contacts.ts` существующий хардкод контактов в `Footer.tsx`, `ElectricFooter.tsx`, `delivery/page.tsx`, `ComingSoonClient.tsx` — граница, унаследованная от стори 41.4
**And** **не** добавляется JSON-LD `BreadcrumbList`, `Product` (уже есть в `ProductPageClient.tsx:81`) и `Organization` с `taxID` на `/requisites` — отдельная запись в `deferred-work.md`
**And** **не** правится захардкоженный `https://optisport.ru` в `ProductPageClient.tsx:96` — предсуществующая непоследовательность, записывается в `deferred-work.md`
**And** **не** добавляется `noindex` странице `/coming-soon` (AC1)

## Tasks / Subtasks

- [x] **Task 1. Ветка и baseline** (все AC)
  - [x] Убедиться, что PR стори 41.4 влит в `develop`: `git log --oneline develop -5` содержит `d0772737`/`99358186`/`17e17d9e` или merge-коммит поверх них. Если нет — **остановиться и сообщить владельцу**: без `frontend/src/config/contacts.ts` Task 6 выполнить нечем
  - [x] `git switch develop; git pull`, затем `git switch -c feature/story-41-6-metadata-og-jsonld` (прямые коммиты в `develop` запрещены)
  - [x] `git rev-parse --short HEAD` → записать значение в `baseline_commit` фронтматтера этого файла
  - [x] Зафиксировать базис тестов ДО правок: `cd frontend; npm run test -- --run src/app src/components/home src/__tests__` → записать число зелёных в Debug Log

- [x] **Task 2. Blast radius перед правкой `buildMetadata`** (AC4)
  - [x] `npx gitnexus impact buildMetadata --direction upstream --repo "C:\Users\1\DEV\FREESPORT"` — подтвердить, что список вызывающих совпадает с зафиксированным в Dev Notes (14 прямых, risk CRITICAL). Если список изменился — перечитать координаты, прежде чем править
  - [x] Сообщить владельцу уровень риска до внесения правок (требование `project-context.md` §5)

- [x] **Task 3. Константы og:image и нормализация в `utils/seo.ts`** (AC4)
  - [x] `frontend/src/utils/seo.ts`: рядом с `DEFAULT_OG_IMAGE` (строка 14) завести
        ```ts
        /**
         * Фактические параметры файла public/image.jpg. Меняются вместе с файлом —
         * расхождение ловит тест-страж src/__tests__/og-image.test.ts.
         */
        export const DEFAULT_OG_IMAGE_WIDTH = 1040;
        export const DEFAULT_OG_IMAGE_HEIGHT = 680;
        export const DEFAULT_OG_IMAGE_TYPE = 'image/jpeg';

        export const DEFAULT_OG_IMAGE_META = {
          url: DEFAULT_OG_IMAGE,
          width: DEFAULT_OG_IMAGE_WIDTH,
          height: DEFAULT_OG_IMAGE_HEIGHT,
          type: DEFAULT_OG_IMAGE_TYPE,
          alt: 'OPTISPORT — платформа продаж спортивных товаров',
        } as const;
        ```
  - [x] Расширить тип `PageSeoOptions['image']`: `string | { url: string; alt?: string; width?: number; height?: number; type?: string } | null`
  - [x] Внутри `seo.ts` добавить хелпер, который дополняет размерами **только** картинку по умолчанию:
        ```ts
        /**
         * Дополняет размерами ровно картинку по умолчанию: габариты чужих
         * изображений (карточки товара, обложки статей) нам неизвестны.
         */
        function withDefaultImageMeta(image: NonNullable<PageSeoOptions['image']>) {
          const url = typeof image === 'string' ? image : image.url;
          if (url !== DEFAULT_OG_IMAGE) return image;
          return typeof image === 'string'
            ? DEFAULT_OG_IMAGE_META
            : { ...DEFAULT_OG_IMAGE_META, ...image };
        }
        ```
  - [x] Применить его к `images` **только** в блоке `openGraph`. `twitterImages` уже сводит объект к `url` (строка 79) — их трогать не нужно и не следует: Twitter размеров не читает
  - [x] **Сигнатуру `buildMetadata` не менять**, новых обязательных параметров не вводить, порядок полей возвращаемого объекта не переставлять (`(blue)/[slug]/__tests__/page.test.tsx:52` сравнивает результат целиком)
  - [x] Комментарии и docstring — на русском (NFR-41-03)

- [x] **Task 4. Корневой layout и страница `/electric`** (AC4)
  - [x] `frontend/src/app/layout.tsx`: импортировать `DEFAULT_OG_IMAGE_META`, в `openGraph.images` подставить `[DEFAULT_OG_IMAGE_META]`; `twitter.images` оставить `[DEFAULT_OG_IMAGE]`
  - [x] `frontend/src/app/(electric)/electric/page.tsx:57-64`: заменить объект с неверными `width: 1200, height: 630` на `images: [DEFAULT_OG_IMAGE_META]` (импорт из `@/utils/seo`); `twitter.images` привести к `[DEFAULT_OG_IMAGE]`
  - [x] `frontend/src/app/(blue)/catalog/layout.tsx:13` — строку `image: '/image.jpg'` **можно оставить**: нормализация из Task 3 подставит размеры и для неё. Если решено убрать как избыточную — допустимо, но тогда добавить проверку в тест каталога

- [x] **Task 5. Метаданные `/coming-soon` и `/login`** (AC1, AC2)
  - [x] `frontend/src/app/(coming-soon)/coming-soon/page.tsx` — Server Component, метаданные ставятся прямо в нём:
        ```ts
        export const metadata: Metadata = buildMetadata({
          title: 'OPTISPORT скоро откроется — оптовые продажи спорттоваров',
          description:
            'OPTISPORT — оптовые и розничные продажи спортивных товаров. Сайт скоро откроется, по вопросам сотрудничества пишите на info@optisport.ru.',
          path: '/coming-soon',
        });
        ```
  - [x] `noIndex` здесь **не** ставить (AC1): страница — фактическая главная прода (`GET https://optisport.ru/` → 307 на `/coming-soon`, проверено 2026-09-05)
  - [x] Создать `frontend/src/app/(blue)/(auth)/login/layout.tsx`:
        ```tsx
        import type { Metadata } from 'next';
        import { buildMetadata } from '@/utils/seo';

        // Сама страница входа — клиентский компонент ('use client'), экспортировать
        // metadata из неё нельзя, поэтому SEO-теги живут в этом layout
        // (тот же приём, что и в (blue)/catalog/layout.tsx).
        export const metadata: Metadata = buildMetadata({
          title: 'Вход в личный кабинет | OPTISPORT',
          description:
            'Вход в личный кабинет OPTISPORT для оптовых клиентов: заказы, цены по вашей роли, история отгрузок и документы.',
          path: '/login',
          noIndex: true,
        });

        export default function LoginLayout({ children }: { children: React.ReactNode }) {
          return children;
        }
        ```
  - [x] `login/page.tsx` **не** трогать: ни `'use client'`, ни `Suspense`, ни логику редиректа
  - [x] Проверить, что новый layout не добавил обёртки в DOM — возвращается `children`, а не `<div>{children}</div>`

- [x] **Task 6. Данные организации и JSON-LD** (AC6)
  - [x] Создать `frontend/src/config/organization.ts` рядом с `contacts.ts`:
        ```ts
        import { SUPPORT_EMAIL, SUPPORT_PHONE_DISPLAY } from './contacts';
        import { SITE_NAME, SITE_URL, absoluteUrl } from '@/utils/seo';

        /** Идентификаторы узлов графа: связывают WebSite с Organization */
        export const ORGANIZATION_ID = `${SITE_URL}/#organization`;
        export const WEBSITE_ID = `${SITE_URL}/#website`;
        ```
  - [x] Значения `ORGANIZATION_JSON_LD`: `name` = `SITE_NAME`; `url` = `SITE_URL`; `logo` = `{ '@type': 'ImageObject', url: absoluteUrl('/LOGO_OPTIsport.png'), width: 1014, height: 101 }`; `email` = `SUPPORT_EMAIL`; `telephone` = `SUPPORT_PHONE_DISPLAY`; `address` = `{ '@type': 'PostalAddress', addressCountry: 'RU', addressLocality: 'Ставрополь', streetAddress: 'ул. Коломийцева, 40/1' }` (адрес — из колонки «Контакты» подвала, `Footer.tsx:78`)
  - [x] `sameAs` = `['https://vk.com/optisport', 'https://t.me/optisport', 'https://youtube.com/@optisport']` — те же три адреса, что в `Footer.tsx` (`DEFAULT_SOCIAL_LINKS`). **Перед коммитом открыть все три и убедиться, что аккаунты существуют.** Несуществующий адрес из `sameAs` убрать и завести запись в `deferred-work.md` о мёртвой ссылке подвала — это дефект подвала, а не разметки
  - [x] `WEBSITE_JSON_LD`: `@id` = `WEBSITE_ID`, `name` = `SITE_NAME`, `url` = `SITE_URL`, `inLanguage: 'ru-RU'`, `publisher: { '@id': ORGANIZATION_ID }`. `potentialAction` не добавлять
  - [x] Создать `frontend/src/components/common/SiteJsonLd.tsx` — Server Component без `'use client'`, один `<script type="application/ld+json">` с `{ '@context': 'https://schema.org', '@graph': [ORGANIZATION_JSON_LD, WEBSITE_JSON_LD] }` через `dangerouslySetInnerHTML` (образец — `ProductPageClient.tsx:81-119`)
  - [x] Экспортировать из `frontend/src/components/common/index.ts` (паттерн файла — экспорт компонента и типа пропсов, если он появится)
  - [x] Смонтировать в `frontend/src/app/layout.tsx` внутри `<body>`, рядом с `<CookieConsentBanner />`. Именно корневой layout: только он покрывает и `(blue)`, и `(electric)`, и `(coming-soon)` — а `/coming-soon` сейчас единственная страница, которую видит посетитель прода
  - [x] Осознанное следствие: блок попадёт и на `not-found.tsx`. Это принято — 404 уже несёт `noindex`, разметка на ней инертна; три копии компонента по трём layout ради этого не заводятся

- [x] **Task 7. `title` страницы «О компании»** (AC3)
  - [x] `frontend/src/app/(blue)/about/page.tsx:22` — `title: 'О компании OPTISPORT — оптовый поставщик спорттоваров'`
  - [x] `description` и остальной файл не трогать

- [x] **Task 8. Переименование `og-image.jpg`** (AC5)
  - [x] `git mv frontend/public/og-image.jpg frontend/public/hero-fallback.jpg` (именно `git mv` — переименование должно быть видно в истории, а не как «удалил + добавил»)
  - [x] `frontend/src/components/home/HeroSection.tsx:178` — `src="/hero-fallback.jpg"`
  - [x] `frontend/src/components/home/ElectricHeroSection.tsx:162` — `'/hero-fallback.jpg'`
  - [x] Проверка: `cd frontend; grep -rn "og-image" src/ public/` → пусто
  - [x] Оба `alt` оставить как есть — текст описывает содержимое картинки, а не имя файла

- [x] **Task 9. Тесты** (AC7, NFR-41-01)
  - [x] **Правка сломанных** (сначала убедиться, что они падают именно от наших правок):
        - `frontend/src/app/(blue)/about/__tests__/page.test.tsx:180` — вместо `toBe('О компании')` проверять новое значение **и** диапазон длины 30…60 (AC3)
        - там же `:192` — `openGraph.title` привести к новому значению
        - `frontend/src/app/(blue)/home/__tests__/page.test.tsx:175` — `toContain('/image.jpg')` → сверка с `DEFAULT_OG_IMAGE_META`
        - `frontend/src/app/(blue)/blog/[slug]/__tests__/page.test.tsx:282` и `frontend/src/app/(blue)/news/[slug]/__tests__/page.test.tsx:227` — `toEqual(['/image.jpg'])` → `toEqual([DEFAULT_OG_IMAGE_META])`; **строки 273 и 220 не трогать** — там чужие картинки статей, и они обязаны остаться голыми строками
  - [x] **Новый тест-страж** `frontend/src/__tests__/og-image.test.ts`:
        - читает `frontend/public/image.jpg` через `node:fs`, разбирает SOF-маркер JPEG и сверяет ширину/высоту с `DEFAULT_OG_IMAGE_WIDTH`/`DEFAULT_OG_IMAGE_HEIGHT` (образец работы с `fs` в тесте — `src/__tests__/next-config-headers.test.ts:19-33`)
        - проверяет, что `DEFAULT_OG_IMAGE` заканчивается на `.jpg`, а `DEFAULT_OG_IMAGE_TYPE` = `image/jpeg`
        - проверяет, что `frontend/public/og-image.jpg` **не существует**, а `hero-fallback.jpg` существует
        - рекурсивно обходит `frontend/src` и проверяет отсутствие подстроки `og-image`
  - [x] **Новый тест** `frontend/src/utils/__tests__/seo.test.ts` (каталог существует): `buildMetadata` без `image` отдаёт `openGraph.images = [DEFAULT_OG_IMAGE_META]`; с явным `image: '/image.jpg'` — то же самое; с чужим URL — голую строку без размеров; `twitter.images` во всех случаях остаётся массивом строк
  - [x] **Новые тесты метаданных**: `frontend/src/app/(coming-soon)/coming-soon/__tests__/page.test.tsx` (каталог создаётся) и `frontend/src/app/(blue)/(auth)/login/__tests__/layout.test.tsx` — точные `title`/`description`, отличие от корневых значений, `robots` (есть у `/login`, нет у `/coming-soon`), `alternates.canonical`
  - [x] **Новый тест** `frontend/src/components/common/__tests__/SiteJsonLd.test.tsx`: ровно один `script[type="application/ld+json"]`; `JSON.parse` содержимого даёт `@graph` из двух узлов нужных типов; `publisher['@id']` равен `@id` организации; `potentialAction` отсутствует; `telephone`/`email` совпадают с константами из `config/contacts.ts`
  - [x] Прогон: `cd frontend; npm run test`, `npm run lint`, `npm run format:check`, `npx tsc --noEmit`
  - [x] Backend не прогонять — код бэкенда не менялся

- [x] **Task 10. Ручная проверка** (AC1–AC6)
  - [x] `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`; при 502 после рестарта — `docker compose --env-file .env -f docker/docker-compose.yml restart nginx`
  - [x] `curl -s http://localhost:3000/coming-soon | grep -o '<title>[^<]*</title>'` — новый заголовок; то же для `/login` и `/about`
  - [x] `curl -s http://localhost:3000/home | grep -o 'og:image[^>]*'` — присутствуют `og:image`, `og:image:width`, `og:image:height`, `og:image:type`
  - [x] `curl -s http://localhost:3000/home | grep -c 'application/ld+json'` — ровно одно вхождение; повторить на `/coming-soon`
  - [x] Скопировать содержимое JSON-LD в https://validator.schema.org (Code snippet) — ошибок нет; результат записать в Dev Agent Record
  - [x] Открыть `/home` при недоступном API баннеров — картинка hero отображается, в консоли нет 404 на `/hero-fallback.jpg`
  - [x] Открыть три адреса из `sameAs` — все три существуют (Task 6)

- [x] **Task 11. Записи в `deferred-work.md`** (AC8)
  - [x] `/register`, `/b2b-register` и страницы `/profile/*` по-прежнему наследуют корневые `title`/`description` — FR-41-11 сужен решением 2026-08-24 до двух страниц; правка тривиальна (по `layout.tsx` на сегмент), но за пределами эпика
  - [x] `public/image.jpg` имеет пропорцию 1.53 против эталонной 1.905 (1200×630) — соцсети срежут превью примерно по 20 % сверху и снизу; замена файла требует нового изображения от владельца
  - [x] `logo` организации 1014×101 — высота ниже рекомендованных Google 112 px для `Organization.logo`
  - [x] `ProductPageClient.tsx:96` хардкодит `https://optisport.ru` вместо `absoluteUrl()`
  - [x] JSON-LD `Organization` с `taxID` на `/requisites` и `BreadcrumbList` — расширение разметки за пределами FR-41-14 (перекликается с существующей записью по `spec-requisites-page-update.md`)

- [x] **Task 12. Перед коммитом**
  - [x] `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — затронуты только ожидаемые символы; HIGH/CRITICAL в отчёте объяснены
  - [x] `File List` сверить с `git diff --name-only <baseline_commit>..HEAD`, а не с памятью (находка ревью в 41.0, 41.4 и 41.5)
  - [ ] Установить `review_head` на коммит, завершающий содержательную работу — **ждёт коммита владельца** (решение 2026-09-06: коммит правок ревью делает владелец сам). Заполняется одним значением: `git rev-parse --short HEAD` после коммита
  - [x] Коммит и push — только по явной просьбе владельца

### Review Findings

- [x] [Review][Patch] Уточнить AC6: требование «ровно один» относится к site-level `@graph`; отдельные маршрутные схемы вроде существующего `Product` разрешены. Решение Alex: вариант 1, код вывода JSON-LD оставить без изменений. [`frontend/src/app/layout.tsx:66-76`, `frontend/src/components/product/ProductPageClient.tsx:79-120`]
- [x] [Review][Patch] Не позволять объекту `image: { url: '/image.jpg', ... }` переопределять фактические `width`, `height` и `type` картинки по умолчанию [`frontend/src/utils/seo.ts:58-61,96-99`]
- [x] [Review][Patch] Нормализовать завершающий `/` в `SITE_URL`, иначе JSON-LD получает `//#organization`, `//#website` и `//LOGO_OPTIsport.png` [`frontend/src/utils/seo.ts:11,88-89`, `frontend/src/config/organization.ts:14-15`]
- [x] [Review][Patch] Экранировать `<` при сериализации JSON-LD перед `dangerouslySetInnerHTML`; `SITE_URL` поступает из окружения и не является литеральной константой [`frontend/src/components/common/SiteJsonLd.tsx:19-28`]
- [x] [Review][Patch] Сделать JPEG guard корректным для валидных fill-байтов `FF FF … marker` и добавить проверки SOI/границ сегмента [`frontend/src/__tests__/og-image.test.ts:36-68`]
- [ ] [Review][Patch] Заполнить `review_head` — **отметка Task 12 исправлена на невыполненную** (это и было существом находки: подпункт стоял `[x]` при пустом поле). Само поле заполняется после коммита правок ревью, который по решению владельца от 2026-09-06 делает он сам [`41-6-unique-metadata-og-image-jsonld.md:2-10,275-279`]
- [x] [Review][Patch] Согласовать буквальный AC5 `grep -rn "og-image"` с реализованной проверкой именно пути: текущая команда неизбежно находит сам guard и фикстуру `blog-image.jpg` [`41-6-unique-metadata-og-image-jsonld.md:81-87,235-240`, `frontend/src/__tests__/og-image.test.ts:105-123`]
- [x] [Review][Patch] Исправить отметки двух ручных проверок: браузерный fallback `/home` был заменён тестами, а существование VK не подтверждено, хотя обе задачи отмечены `[x]` [`41-6-unique-metadata-og-image-jsonld.md:259-266,485-491`]
- [x] [Review][Defer] `/electric` хардкодит корневой production URL в `openGraph.url`, поэтому staging и путь `/electric` описываются неверно [`frontend/src/app/(electric)/electric/page.tsx:55-63`] — deferred, pre-existing
- [x] [Review][Defer] Метаданные статей блога и новостей передают сырой API URL изображения без обязательного `normalizeImageUrl()` [`frontend/src/app/(blue)/blog/[slug]/page.tsx:29-38`, `frontend/src/app/(blue)/news/[slug]/page.tsx:29-38`] — deferred, pre-existing
- [x] [Review][Defer] API-баннеры hero передают `image_url` напрямую; `HeroSection` дополнительно не имеет fallback для пустой строки [`frontend/src/components/home/HeroSection.tsx:192-232`, `frontend/src/components/home/ElectricHeroSection.tsx:152-187`] — deferred, pre-existing

## Dev Notes

### Фактическое состояние прода (замер 2026-09-05)

```
GET https://optisport.ru/            -> 307 -> /coming-soon
GET https://optisport.ru/coming-soon -> <title>OPTISPORT Platform | B2B/B2C спортивные товары</title>
                                        <meta name="description" content="Ведущая платформа продаж..."/>
                                        og:image = https://optisport.ru/image.jpg  (без width/height/type)
GET https://optisport.ru/login       -> <title>OPTISPORT Platform | B2B/B2C спортивные товары</title>
GET https://optisport.ru/about       -> <title>О компании</title>                  (10 символов)
```

Все три дефекта FR-41-11/12/13 наблюдаемы на живом сайте, а `/coming-soon` — страница, которую видит **каждый** посетитель. Метаданные, которые пишет эта стори, — метаданные фактической главной.

### Кто сегодня наследует корневые метаданные

Обход всех `page.tsx` без `export const metadata` и без `generateMetadata` (с поправкой на `/catalog`, закрытый своим `layout.tsx`):

| Маршрут | В объёме? | Почему |
|---|---|---|
| `/coming-soon` | **Да** | Фактическая главная прода |
| `/login` | **Да** | Реальная публичная страница, найдена аудитом |
| `/register`, `/b2b-register` | Нет | Тот же класс дефекта, но FR-41-11 сужен решением 2026-08-24 → `deferred-work.md` |
| `/profile/*` (7 страниц) | Нет | За авторизацией, в `Disallow` robots.txt |
| `/test`, `/examples`, `/design-comparison`, `/electric-orange-test` | Нет | Демо-страницы, в `Disallow` |
| `/electric/catalog` | Нет | Витрина альтернативной темы, в `Disallow` |
| `/checkout/success/[orderId]` | Нет | Динамический приватный маршрут |
| `/` (`app/page.tsx`) | Нет | Только `redirect()`, документа не отдаёт |

### Почему `Disallow` в robots.txt не отменяет требование

`/coming-soon`, `/login` и `/search` перечислены в `Disallow` (`app/robots.ts:24-31`). Соблазн закрыть FR-41-11 через «поставить `noindex` и забыть» неверен по трём причинам: (1) сканер аудита ходил по сайту и читал метатеги, игнорируя robots.txt — замечание про дубли останется; (2) соцсети (VK, Telegram, WhatsApp) при вставке ссылки читают `og:*` независимо от robots.txt, и сейчас ссылка на `/coming-soon` разворачивается в общий текст платформы; (3) требование сформулировано как «собственные `title` и `description`», а не как «страница не в индексе».

Поэтому `noIndex: true` у `/login` — это **дополнение** к уникальным метаданным (согласование с уже существующим `Disallow` и с конвенцией `/cart`, `/checkout`), а не замена им. У `/coming-soon` `robots` не трогается вовсе: менять индексируемость фактической главной страницы прода — не задача этой стори.

### `buildMetadata`: почему нормализация внутри, а не размеры на каждой странице

`npx gitnexus impact buildMetadata --direction upstream` (индекс на `17e17d9e`): **14 прямых вызывающих**, `"risk": "CRITICAL"`, 6 затронутых процессов (`generateMetadata` в `[slug]`, `privacy-policy`, `news/[slug]`, `blog/[slug]`, `search`, `product/[slug]`), 2 модуля.

Вызывающие: `about`, `blog`, `blog/[slug]`, `catalog/layout`, `delivery`, `home`, `news`, `news/[slug]`, `partners`, `privacy-policy`, `product/[slug]`, `requisites`, `search`, `[slug]`.

При CRITICAL правильный ход — **не расширять контракт**, а поменять значение по умолчанию и нормализовать его внутри. Тогда:

- ни один из 14 вызовов править не нужно;
- страницы, передающие `image: '/image.jpg'` явно (`catalog/layout.tsx:13`), получают размеры автоматически — иначе они молча остались бы без них;
- страницы с чужой картинкой (`blog/[slug]`, `news/[slug]`, `product/[slug]`) размеров не получают, потому что габариты чужого файла неизвестны;
- тест `(blue)/[slug]/__tests__/page.test.tsx:52`, сравнивающий `generateMetadata` с результатом `buildMetadata` целиком, остаётся зелёным без правок.

Какие теги это даёт: Next разворачивает объект `{url, width, height, type, alt}` в `og:image`, `og:image:width`, `og:image:height`, `og:image:type`, `og:image:alt`. Строка даёт только `og:image` — ровно то, что сейчас на проде.

### Тесты: что сломается и что нет

| Файл:строка | Как проверяет | Ломается? |
|---|---|---|
| `about/__tests__/page.test.tsx:180` | `metadata.title` `toBe('О компании')` | **Да** — AC3 |
| `about/__tests__/page.test.tsx:192` | `openGraph.title` `toBe('О компании')` | **Да** — то же значение |
| `about/__tests__/page.test.tsx:184-187` | `description` `toContain(...)` ×3 | Нет — описание не меняется |
| `home/__tests__/page.test.tsx:175` | `openGraph.images` `toContain('/image.jpg')` | **Да** — массив станет массивом объектов |
| `home/__tests__/page.test.tsx:173-174` | `toBeDefined`, `Array.isArray` | Нет |
| `blog/[slug]/__tests__/page.test.tsx:282` | `toEqual(['/image.jpg'])` | **Да** |
| `blog/[slug]/__tests__/page.test.tsx:273` | `toEqual(['http://example.com/blog-image.jpg'])` | Нет — чужая картинка остаётся строкой |
| `news/[slug]/__tests__/page.test.tsx:227` | `toEqual(['/image.jpg'])` | **Да** |
| `news/[slug]/__tests__/page.test.tsx:220` | чужая картинка | Нет |
| `(blue)/[slug]/__tests__/page.test.tsx:52` | сравнение с `buildMetadata(...)` | Нет — сверяется сам с собой |
| `privacy-policy/__tests__/page.test.tsx:153` | `generateMetadata()` | Нет — картинку не проверяет |
| `src/__tests__/app-routes-allowlist.test.ts` | ищет только `page.*` | Нет — новый `login/layout.tsx` его не задевает |
| `src/app/__tests__/ComingSoonClient.test.tsx` | рендер клиента | Нет — правится `page.tsx`, не клиент |
| `home/__tests__/HeroSection.test.tsx` | рендер hero | Нет — на имя файла картинки не смотрит (`grep og-image` по тестам пуст) |
| backend-тесты | — | Нет — бэкенд не менялся |

Дисциплина, унаследованная от стори 41.3 и 41.4: **сначала прогнать затрагиваемые файлы на неизменённом коде** и записать число зелёных, иначе «упало из-за моей правки» и «падало и раньше» не отличить.

### Почему `/login` не может объявить метаданные сам

`login/page.tsx:11` — `'use client'`. Next.js собирает `metadata` только из серверных модулей; экспорт из клиентского файла работать не будет. Приём, уже применённый в проекте: `(blue)/catalog/layout.tsx:5-6` — комментарий там объясняет ровно этот случай. Копируем приём, а не изобретаем.

Layout возвращает `children` без обёртки — иначе в DOM появится лишний узел внутри `(blue)`-раскладки, а `LayoutWrapper` рассчитывает на текущую структуру.

### Что кладём в JSON-LD и чего не кладём

- **`@graph` вместо двух отдельных `<script>`** — так `WebSite.publisher` ссылается на `Organization` по `@id`, и робот видит связанные сущности, а не две карточки рядом.
- **`SearchAction` — нет.** `/search` в `Disallow` (`robots.ts:24`), а sitelinks searchbox требует индексируемую страницу результатов. Объявлять действие, ведущее в закрытый раздел, — противоречие в разметке.
- **`sameAs`** — три адреса из подвала. Их существование проверяется руками (Task 6): `sameAs` на несуществующий аккаунт хуже отсутствия `sameAs`.
- **Абсолютные URL — только через `SITE_URL`/`absoluteUrl`.** В прод-сборке `NEXT_PUBLIC_APP_URL` приходит из `SITE_URL` (`docker/docker-compose.prod.yml:126,140` — и как build-arg, и как runtime-env), локально по умолчанию `http://localhost:3000`. Локальный JSON-LD с `localhost` — ожидаемое поведение, а не дефект; хардкодить домен нельзя.
- **Экранирование в `dangerouslySetInnerHTML` обязательно** (посылка исправлена находкой ревью 2026-09-06). Изначально здесь стояло «XSS не рассматривается: данные — статические константы модуля». Это неверно: `SITE_URL` — константа модуля, но не литеральная, её значение приходит из `NEXT_PUBLIC_APP_URL`, то есть из окружения сборки. Литеральный `</script>` в этом значении закрыл бы инлайн-скрипт и вынес остаток графа в документ как разметку. Поэтому каждый `<` заменяется на `\\u003c` перед вставкой; для JSON это та же строка, робот читает граф без изменений.
- **CSP не мешает.** Действующая политика (`next.config.ts:146-149`) — `default-src 'self' http: https: data: blob: 'unsafe-inline'`, отдельного `script-src` нет; инлайн-скрипт `application/ld+json` проходит.

### `og-image.jpg`: разбор премисы

| Утверждение эпика | Факт |
|---|---|
| «Неиспользуемый `frontend/public/og-image.jpg`» | Используется дважды: `HeroSection.tsx:178` (статическая ветка hero), `ElectricHeroSection.tsx:162` (fallback при отсутствии баннеров из API) |
| «квадрат 1024×1024» | Верно, проверено по заголовку файла |
| «удаляется» | Удаление даст битую картинку в обеих fallback-ветках. Выполняем переименование в `hero-fallback.jpg` |
| «используется один файл превью» | Выполняется: `DEFAULT_OG_IMAGE = '/image.jpg'` и был, и остаётся единственным превью |

Имя `og-image.jpg` и породило ошибку в эпике: файл называется как соцпревью, а работает как заглушка hero. После переименования такой ловушки нет.

### `image.jpg`: объявляем фактическое, а не эталонное

Файл — **1040×680** (проверено разбором JPEG-заголовка), пропорция 1.53 против эталонных 1.905 для 1200×630. Эпик прямо предписывает: «объявлять в метатегах следует фактические размеры файла, а не эталонные». Поэтому в константы идут 1040×680, а тест-страж читает файл и падает при расхождении. Когда владелец принесёт файл 1200×630, поменять нужно будет ровно две константы — и тест сразу скажет, если этого не сделали.

### Окружение

- Правки `frontend/src/` применяются рестартом контейнера: `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`. Пересбор (`up -d --build frontend`) нужен только при изменении зависимостей или `next.config.ts` — здесь ни того, ни другого нет
- Bind-mount `../frontend:/app` на Windows не пробрасывает inotify — HMR правки не подхватывает, рестарт обязателен (находка стори 41.4)
- После рестарта frontend nginx может отдать 502 на новый IP upstream — лечится рестартом nginx
- Файлы из `public/` отдаёт сам Next; переименование подхватывается тем же рестартом
- Локально `ACTIVE_THEME=blue` (`.env:118`), на проде — `coming_soon`. Чтобы посмотреть `/coming-soon` локально, ходить на адрес напрямую, тему не переключать
- Ветка от `develop`; прямые коммиты в `develop` запрещены

### Project Structure Notes

- Метаданные клиентской страницы → `layout.tsx` того же сегмента (прецедент: `(blue)/catalog/layout.tsx`)
- Данные организации → `frontend/src/config/organization.ts`, рядом с `contacts.ts`, `quickLinks.tsx`, `theme.ts`. Каталога `src/constants/` в проекте нет — не заводить (находка стори 41.4)
- Компонент разметки → `frontend/src/components/common/` и его barrel `index.ts`: он не принадлежит ни одному домену и монтируется в корневом layout
- Тесты-стражи уровня проекта → `frontend/src/__tests__/` (там уже `app-routes-allowlist.test.ts`, `next-config-headers.test.ts`, `docker-environment.test.ts`)
- Тесты страниц → `__tests__/` внутри каталога страницы (принятый паттерн `app/(blue)/*/__tests__/`)
- SEO-константы — только в `frontend/src/utils/seo.ts`: второй источник размеров превью сразу разойдётся с первым

### Актуальные версии стека (из `frontend/package.json`)

`next@15.5.18`, `react@19.1.0`, `vitest@^4.0.15`, `typescript@5.8.2`. Окружение тестов — `happy-dom`, но `node:fs` в тестах доступен (используется в `next-config-headers.test.ts`). React 19: `ref` — обычный prop, `forwardRef` не нужен. Новых зависимостей стори не добавляет.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.6] — исходные AC
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-11] — сужение до `/coming-soon` и `/login`, обоснование 2026-08-24
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-13] — состояние `image.jpg` 1040×680, требование объявлять фактические размеры
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-12, FR-41-14] — длина `title` «О компании», JSON-LD `Organization`/`WebSite`
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#NFR-41-01, NFR-41-03] — тесты и русские комментарии
- [Source: _bmad-output/implementation-artifacts/Story/41-0-real-404-for-nonexistent-urls.md] — почему 41.6 идёт после 41.0; граница «`seo.ts`, `robots.ts`, `sitemap.ts` не трогаем» там была намеренной и снимается здесь только для `seo.ts`
- [Source: _bmad-output/implementation-artifacts/Story/41-4-checkout-trade-info-and-policy-link.md] — `config/contacts.ts`, дисциплина «сначала базис тестов», `git diff --name-only` для File List
- [Source: frontend/src/utils/seo.ts:11-14,62-106] — `SITE_URL`, `DEFAULT_OG_IMAGE`, `buildMetadata`
- [Source: frontend/src/app/layout.tsx:20-22,24-45] — корневые `title`/`description`/`openGraph`, куда монтируется JSON-LD
- [Source: frontend/src/app/(blue)/catalog/layout.tsx:5-14] — эталон выноса метаданных клиентской страницы в layout
- [Source: frontend/src/components/product/ProductPageClient.tsx:81-119] — существующий паттерн JSON-LD в проекте
- [Source: frontend/src/app/robots.ts:24-31] — `Disallow` для `/coming-soon`, `/login`, `/search`
- [Source: frontend/src/__tests__/next-config-headers.test.ts:19-33] — образец теста-стража, читающего файл через `node:fs`
- [Source: frontend/src/config/contacts.ts] — единственный допустимый источник телефона и почты для JSON-LD
- [Source: frontend/src/components/layout/Footer.tsx:74-79,83-106] — контакты, адрес и соцсети, из которых собирается `Organization`
- [Source: project-context.md#7 Frontend-специфика] — Server vs Client Components, `next/image`, рестарт контейнера
- [Source: project-context.md#5 GitNexus-дисциплина] — обязательный `impact` перед правкой символа

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (claude-opus-5), workflow `bmad-dev-story`.

### Debug Log References

**Базис ДО правок (Task 1).** `cd frontend; npm run test -- --run src/app src/components/home src/__tests__` на `4e386a95` — **45 файлов, 782 passed, 2 skipped**, exit 0. Ни одного падения на неизменённом коде, поэтому всё, что упало дальше, — следствие правок стори.

**Блокирующая находка перед Task 1: стори 41.4 не была влита в `develop`.** `sprint-status.yaml` держал ключ `41-4-checkout-trade-info-and-policy-link: done`, но `frontend/src/config/contacts.ts` в рабочем дереве отсутствовал. Разбор: коммит `79542d70` перенёс на `develop` только документацию — файлы стори 41.4/41.6, `deferred-work.md`, `sprint-status.yaml`; код стори 41.4 (`contacts.ts`, `CheckoutForm.tsx`, `ReturnsAndSupportNotice.tsx`, `checkoutDraft.ts` и около 700 строк тестов) остался на `origin/feature/story-41-4-checkout-trade-info`, PR для него не заводился (`gh pr list`: последний PR стори — #128 для 41.2). Для сравнения, стори 41.5 в `develop` присутствует. По решению владельца ветка 41.4 была домержена (`develop` влит в неё, три конфликта — только документация, во всех взята версия `develop` как более поздняя), выпущен **PR #131** и влит в `develop` (`4e386a95`). Только после этого заведена ветка 41.6.

**Task 2, blast radius.** `npx gitnexus impact buildMetadata --direction upstream --repo "C:\Users\1\DEV\FREESPORT"`: `impactedCount: 14`, `"risk": "CRITICAL"`, `processes_affected: 6`, `modules_affected: 2`. Совпало с зафиксированным в Dev Notes. Владелец предупреждён до внесения правок; сигнатура не менялась, ни один из 14 вызовов править не потребовалось. Индекс GitNexus на момент проверки был `stale` на один коммит (`79542d7` против `4e386a9`), список вызывающих при этом совпал — расхождение пришлось на перенос документации.

**Порядок red-green по задачам.** Task 3: `src/utils/__tests__/seo.test.ts` до правки `seo.ts` — 3 failed / 8 passed, после — 11 passed. Task 5: тесты `/coming-soon` и `/login` до создания модулей падали на резолве импорта, после — 11 passed. Task 6: `SiteJsonLd.test.tsx` до создания компонента падал на резолве, после — 10 passed. Task 7: тест `about` после правки ожиданий — 2 failed, после правки `page.tsx` — 32 passed.

**Мок `next/font/google` в двух новых тестах.** Тесты `/coming-soon` и `/login` импортируют корневой layout, чтобы доказать отличие от корневых `title`/`description`. Корневой layout вызывает `Inter()`/`Roboto_Condensed()`, которые в тестовой среде не резолвятся (`TypeError: Inter is not a function`), поэтому в обоих файлах заведена заглушка. Сверка с реальным корневым layout — единственный способ проверить AC1 «оба значения отличаются от значений корневого layout» без дублирования этих значений константами.

**Тест-страж дважды поймал собственные комментарии.** Проверка «в `src/` нет ссылок на `/og-image`» сработала сначала на комментарии в `seo.ts`, называвшем файл теста, затем — на комментариях в двух hero-тестах, упоминавших старое имя файла. Все три переформулированы. Это ожидаемое поведение стража, а не его дефект.

**Финальный прогон.** `npm run test` — **162 файла, 2745 passed, 16 skipped**, exit 0. `npm run lint` — 0. `npm run format:check` — 0 (потребовался один `prettier --write src/utils/seo.ts`). `npx tsc --noEmit` — 0. Backend не прогонялся: код бэкенда не менялся.

**Task 10, замеры на живом контейнере** (`docker compose restart frontend`, рестарт nginx не понадобился):

```
GET /coming-soon -> <title>OPTISPORT скоро откроется — оптовые продажи спорттоваров</title>
GET /login       -> <title>Вход в личный кабинет | OPTISPORT</title>
GET /about       -> <title>О компании OPTISPORT — оптовый поставщик спорттоваров</title>
GET /home        -> og:image=http://localhost/image.jpg, og:image:width=1040,
                    og:image:height=680, og:image:type=image/jpeg,
                    og:image:alt=OPTISPORT — платформа продаж спортивных товаров
GET /hero-fallback.jpg -> 200 image/jpeg 64347 bytes
GET /og-image.jpg      -> text/html (файла нет; 200 вместо 404 — известный soft-404 Next 15.5.18)
```

Блоков `<script type="application/ld+json">` — ровно **1** на `/home`, `/coming-soon`, `/about`, `/electric` (второе вхождение строки `application/ld+json` в HTML — сериализованный RSC-пейлоад dev-сборки, не тег).

**Валидатор schema.org (AC6).** Сгенерированный JSON отправлен на `https://validator.schema.org/validate`. Результат: `"numErrors": 0, "numWarnings": 0, "numNodesWithError": 0, "numNodesWithWarning": 0`. Оба узла распознаны (`typeGroup: WebSite`, `typeGroup: Organization`), `publisher` разрешился в узел организации по `@id`, вложенные `ImageObject` и `PostalAddress` — без ошибок, `addressCountry: RU` распознан как `Country`.

**Task 12, detect-changes.** `npx gitnexus detect-changes --scope all` — 16 файлов, 15 символов, 11 процессов, риск **high**. Состав ожидаемый: `buildMetadata` и `PageSeoOptions` (Task 3), `metadata` в четырёх точках (Tasks 4/5/7), `HeroSection`/`ElectricHeroSection` (Task 8), `RootLayout` (Task 6). `normalizePath` и `absoluteUrl` попали в список только из-за сдвига строк в `seo.ts` — их тела не менялись. Уровень high — следствие того, что `buildMetadata` лежит на 14 путях вызова; именно поэтому её сигнатура и порядок полей результата оставлены нетронутыми.

**Разбор находок ревью (2026-09-06).** Блок из восьми `[Review][Patch]`. Базис до правок: три затрагиваемых файла тестов — 27 passed, exit 0, ни одного падения на неизменённом коде. Blast radius повторно снят на индексе `6ddd94d` (up-to-date): `buildMetadata` — **CRITICAL**, 16 вызывающих (14 прежних плюс `/coming-soon` и `/login`, добавленные этой же стори); `absoluteUrl` — LOW, 6; `SiteJsonLd` — LOW, 1. Владелец предупреждён до правок. Сигнатура `buildMetadata` и порядок полей результата снова не менялись — правилось только тело `withDefaultImageMeta`, поэтому 16 вызовов остались нетронутыми.

Порядок red-green по находкам:

| Находка | RED | GREEN |
|---|---|---|
| Переопределение размеров картинки по умолчанию | 2 failed в `seo.test.ts` | размеры и MIME ставятся ПОСЛЕ разворачивания `image`; `alt` по-прежнему переопределяем |
| Хвостовой слэш `SITE_URL` | 3 failed (`//#organization`, `//LOGO…`) | новый `normalizeSiteUrl`, применён к `SITE_URL` |
| Экранирование `<` в JSON-LD | 1 failed — литеральный `</script>` уходил в разметку | `replaceAll('<', '\\u003c')` перед `dangerouslySetInnerHTML` |
| Корректность JPEG-стража | 4 failed (fill-байты, SOI, границы сегмента ×2) | пропуск байтов-заполнителей, проверка SOI, границ и минимальной длины SOF |

**Грабли экранирования при правке.** Первые две попытки записали в `SiteJsonLd.tsx` последовательность `'\u003c'` с одним обратным слэшем — это JS-escape, вычисляющийся в `<`, то есть замена была холостой. Тест это и поймал: в разметке остался литеральный `</script>`. Та же ошибка повторилась в ожидании самого теста. Обе исправлены на `'\\u003c'`; в `SITE_GRAPH_JSON` теперь уходит именно литеральная escape-последовательность, а `JSON.parse` читает тот же граф.

**Проверки, закрытые владельцем (находка 8).** Браузерные инструменты в этой сессии отключены (`claude-in-chrome` не подключён), `vk.com` заблокирован для `WebFetch`, поиск существование сообщества не подтвердил. Оба вопроса переданы владельцу: (1) **VK-аккаунт существует** — адрес остаётся в `ORGANIZATION_SAME_AS`, код не менялся; (2) **ручной осмотр `/home` при недоступном API баннеров выполнен владельцем** — работает, как описано в Task 10. Обе отметки `[x]` теперь опираются на факт, а не на замену. Три теста на `src="/hero-fallback.jpg"` в обеих fallback-ветках остаются в наборе как постоянная защита. Локально API отдаёт активный баннер (`GET /api/v1/banners/` → 1 hero), поэтому fallback-ветка сама по себе не наблюдаема — это и делало проверку ручной.

**Прогон после правок ревью.** `npm run test` — **162 файла, 2758 passed, 16 skipped** (было 2745 passed: +13 новых тестов), exit 0. `npm run lint` — 0. `npx tsc --noEmit` — 0. `npm run format:check` — потребовался один `prettier --write src/components/common/SiteJsonLd.tsx`, после чего чисто; экранирование правку форматтера пережило (перепроверено тестом). Backend не прогонялся: код бэкенда не менялся.

**Живой замер после правок ревью** (`docker compose restart frontend`, рестарт nginx не понадобился):

```
GET /home -> блоков <script type="application/ld+json"> ровно 1
             @id узлов: http://localhost/#organization, http://localhost/#website
             (одинарный слэш — нормализация SITE_URL работает)
             publisher.@id = http://localhost/#organization — связь узлов на месте
             og:image=http://localhost/image.jpg, og:image:width=1040,
             og:image:height=680, og:image:type=image/jpeg,
             og:image:alt=OPTISPORT — платформа продаж спортивных товаров
```

Экранирование `<` на живой SSR-выдаче разметку не испортило: JSON разбирается, оба узла на месте. Локально `NEXT_PUBLIC_APP_URL` хвостового слэша не имеет, поэтому дефект `//#organization` наблюдался только в тестах со стабом окружения — там он и закреплён.

**detect-changes после правок ревью.** `npx gitnexus detect-changes --scope all` — 10 файлов, 16 символов, 12 процессов, риск **high**. Состав ожидаемый и уже, чем в первом круге: `seo.ts` (новый `normalizeSiteUrl`, константы соцпревью, тело `withDefaultImageMeta` и локальные привязки `buildMetadata`, сдвинутые по строкам) и `SiteJsonLd`. Все затронутые потоки — `GenerateMetadata → NormalizePath` и `GenerateMetadata → WithDefaultImageMeta`, то есть ровно те, через которые `buildMetadata` и работает. Уровень high — снова следствие того, что `buildMetadata` лежит на 16 путях вызова; сигнатура и порядок полей результата не менялись, все 2758 тестов зелёные.

`AGENTS.md` и `CLAUDE.md` числятся изменёнными относительно baseline, но к стори отношения не имеют: `npx gitnexus analyze` переписал внутри своих маркеров счётчик символов (9632 → 9641). В File List они не включены намеренно.

### Completion Notes List

**AC1** — `/coming-soon` получила собственные `title`/`description` через `buildMetadata` с `path: '/coming-soon'`; `robots` не задан, индексируемость страницы не менялась. Проверено тестом на точные значения и живым запросом.

**AC2** — метаданные `/login` объявлены в новом `(blue)/(auth)/login/layout.tsx` с `noIndex: true`; `login/page.tsx` не тронут ни строкой. Layout возвращает `children` без обёртки — закреплено тестом на `container.firstElementChild.tagName === 'SPAN'` и `childElementCount === 1`.

**AC3** — `title` страницы «О компании» = `О компании OPTISPORT — оптовый поставщик спорттоваров`, **53 символа**. Длина закреплена **диапазоном** 30…60, а не только точной строкой. `description` не менялся: три существующие проверки на её содержимое остались зелёными без правок.

**AC4** — размеры объявлены единожды, константами в `utils/seo.ts`, и подставляются нормализацией внутри `buildMetadata`. Из `(electric)/electric/page.tsx` убраны неверные `width: 1200, height: 630`. Страницы с чужой картинкой (`blog/[slug]`, `news/[slug]`, `product/[slug]`) размеров не получают — закреплено отдельными тестами.

**AC5** — `og-image.jpg` переименован в `hero-fallback.jpg` через `git mv`; git видит это как `R100` (переименование без изменения содержимого), обе hero-ветки переведены на новое имя.

**AC6** — один `@graph` с `Organization` и `WebSite`, связанными через `publisher` → `@id`; `potentialAction` отсутствует; контакты берутся из `config/contacts.ts`; все абсолютные URL строятся из `SITE_URL`. Валидатор schema.org — 0 ошибок, 0 предупреждений.

**AC7** — 28 новых тестов в шести файлах, четыре сломанных приведены к новым значениям. `npm run test`, `lint`, `format:check`, `tsc --noEmit` — все зелёные.

**AC8** — бэкенд, `openapi.yaml`, `api.generated.ts`, `robots.ts`, `sitemap.ts`, `middleware.ts`, `next.config.ts`, `docker/nginx/**` не тронуты; `generate:types` не запускался. `catalog/layout.tsx:13` оставлен как есть — нормализация из Task 3 подставляет размеры и для него (проверено тестом `buildMetadata` с явным `image: '/image.jpg'`).

**Открыто и передано владельцу: `review_head`.** Поле остаётся пустым. Существо находки ревью было в рассогласовании — подпункт Task 12 стоял `[x]` при пустом поле; отметка исправлена на `[ ]`. Заполнить его нечем, пока правки ревью не закоммичены, а коммит по решению владельца от 2026-09-06 он делает сам. После коммита: `git rev-parse --short HEAD` → значение в `review_head`. Всё остальное по Task 12 выполнено: `detect-changes` прогнан, File List сверен с `git diff --name-status 4e386a95`.

#### Отклонения от буквы AC — по итогам ревью осталось одно

> Разбор ревью 2026-09-06 снял два из трёх отклонений: буква AC5 приведена в соответствие с реализованной проверкой (правка текста AC), а обе ручные проверки выполнены владельцем. Ниже — итоговое состояние.

1. **Снято ревью: текст AC5 приведён к реализованной проверке.** Формулировка AC изменена — вместо буквального `grep -rn "og-image"` в ней теперь описана проверка ссылки на **путь**. Исходное обоснование сохраняется: буквальный `grep -rn "og-image" frontend/src frontend/public` неисполним. `og-image` — подстрока имени `blog-image.jpg`, чужой фикстуры в тесте блога (`blog/[slug]/__tests__/page.test.tsx:57,273`), которую Task 9 прямо запрещает трогать. Требования «grep пуст» и «строку 273 не трогать» противоречат друг другу. Страж проверяет ссылку на **путь** — регулярное выражение `(^|[^\w-])og-image`, что даёт ноль ложных срабатываний и ловит любое реальное возвращение файла (доказано трижды на живых правках, см. Debug Log). Смысл AC5 — «ссылок на удалённый файл не осталось» — выполнен полностью.

2. **Снято ревью: проверку выполнил владелец.** Осмотр `/home` при недоступном API баннеров подтверждён владельцем 2026-09-06 — работает, как описано в Task 10. Ниже — почему проверка не выполнима из сессии и что осталось в наборе как постоянная защита. Браузерные инструменты в сессии оказались недоступны, а через `curl` эта ветка ненаблюдаема в принципе: `HeroSection` — клиентский компонент, SSR отдаёт скелетон (`isLoading: true`), fallback появляется только после того, как клиентский запрос баннеров завершился ошибкой. Вместо разового осмотра заведены три теста, проверяющие `src="/hero-fallback.jpg"` в обеих fallback-ветках (`HeroSection` при ошибке API; `ElectricHeroSection` при ошибке и при пустом ответе). Это сильнее разового взгляда: проверка остаётся в наборе. Отдельно подтверждено, что файл отдаётся живым сервером — `200 image/jpeg 64347 bytes`.

3. **Снято ревью: владелец подтвердил, что VK-аккаунт существует** (2026-09-06). Адрес остаётся в `sameAs`, код не менялся, правка `config/organization.ts` не потребовалась. Ниже — почему адрес не проверялся автоматически. Task 6 требует открыть три адреса `sameAs`. Telegram (`Telegram: Contact @optisport`) и YouTube (`Optisport - YouTube`) отвечают 200. VK на запросы из этого окружения отдаёт антибот-заглушку (418 на HEAD, 404 на GET с браузерным User-Agent), домен заблокирован для `WebFetch` — отличить «страницы нет» от «запрос отклонён» без браузера нельзя. Адрес оставлен как есть, потому что он совпадает с подвалом: если аккаунта нет, это дефект **подвала**, и убирать ссылку нужно синхронно в обоих местах. Заведена запись в `deferred-work.md`; **владельцу достаточно открыть адрес в браузере**, правка — одна строка в `config/organization.ts`.

#### Наблюдение вне объёма

`GET /never-existed-abcxyz.jpg` на локальном dev-сервере отдаёт **200** `text/html` со страницей «Страница не найдена» и `noindex`. Проверено на пути, который стори не трогала, — то есть к переименованию `og-image.jpg` отношения не имеет; это известный soft-404 Next 15.5.18, уже обойдённый через `noindex` (стори 41.0). Записано в `deferred-work.md` как контрольный замер: он же доказывает, что `og-image.jpg` действительно исчез — запрос к нему отдаёт `text/html`, а не `image/jpeg`.

### File List

Диапазон сверен командой `git diff --name-status 4e386a95` плюс `git ls-files --others --exclude-standard`, не по памяти.

**Новые файлы (9):**

- `frontend/src/app/(blue)/(auth)/login/layout.tsx`
- `frontend/src/config/organization.ts`
- `frontend/src/components/common/SiteJsonLd.tsx`
- `frontend/src/__tests__/og-image.test.ts`
- `frontend/src/utils/__tests__/seo.test.ts`
- `frontend/src/app/(coming-soon)/coming-soon/__tests__/page.test.tsx`
- `frontend/src/app/(blue)/(auth)/login/__tests__/layout.test.tsx`
- `frontend/src/components/common/__tests__/SiteJsonLd.test.tsx`
- `frontend/src/components/home/__tests__/ElectricHeroSection.test.tsx`

**Переименован (1):**

- `frontend/public/og-image.jpg` → `frontend/public/hero-fallback.jpg` (`git mv`, `R100` — содержимое байт в байт прежнее)

**Изменённые (14):**

- `frontend/src/utils/seo.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/(electric)/electric/page.tsx`
- `frontend/src/app/(coming-soon)/coming-soon/page.tsx`
- `frontend/src/app/(blue)/about/page.tsx`
- `frontend/src/components/home/HeroSection.tsx`
- `frontend/src/components/home/ElectricHeroSection.tsx`
- `frontend/src/components/common/index.ts`
- `frontend/src/app/(blue)/about/__tests__/page.test.tsx`
- `frontend/src/app/(blue)/home/__tests__/page.test.tsx`
- `frontend/src/app/(blue)/blog/[slug]/__tests__/page.test.tsx`
- `frontend/src/app/(blue)/news/[slug]/__tests__/page.test.tsx`
- `frontend/src/components/home/__tests__/HeroSection.test.tsx`
- `_bmad-output/implementation-artifacts/deferred-work.md`

**Метаданные процесса (2):**

- `_bmad-output/implementation-artifacts/Story/41-6-unique-metadata-og-image-jsonld.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Дата | Изменение |
|---|---|
| 2026-09-06 | Закрыты находки код-ревью — 8 из 8 `[Review][Patch]`. Код: (1) переданные вызывающим `width`/`height`/`type` больше не могут переопределить фактические размеры картинки по умолчанию — константы ставятся после разворачивания `image`, переопределяемым остаётся только `alt`; (2) новый `normalizeSiteUrl` срезает хвостовой слэш `SITE_URL`, из-за которого JSON-LD получал `//#organization`, `//#website` и `//LOGO_OPTIsport.png`; (3) при сериализации JSON-LD каждый `<` уходит в разметку как escape-последовательность — `SITE_URL` приходит из окружения и литеральной константой не является; (4) JPEG-страж научился пропускать байты-заполнители `FF FF … marker` и проверяет SOI, границы сегмента и минимальную длину SOF. Документация: AC6 уточнён — «ровно один» относится к разметке уровня сайта, маршрутные схемы вроде существующего `Product` допустимы (решение владельца, вариант 1, код не менялся); AC5 приведён к реализованной проверке пути вместо неисполнимого буквального grep; посылка Dev Notes про «XSS не рассматривается» исправлена. Две ручные проверки подтверждены владельцем: VK-сообщество существует (запись в `deferred-work.md` закрыта), осмотр `/home` при недоступном API баннеров выполнен. +13 тестов (всего 162 файла, 2758 passed, 16 skipped); lint/format/tsc — 0. Статус: in-progress → review. |
| 2026-09-05 | Стори реализована (dev-story). Перед стартом обнаружено и устранено блокирующее расхождение: стори 41.4 числилась `done`, но её код в `develop` не был влит — PR #131 заведён и влит, `baseline_commit` = `4e386a95`. Реализованы AC1–AC8: метаданные `/coming-soon` и `/login`, `title` `/about` (53 симв.), размеры `og:image` из одного источника, переименование `og-image.jpg` в `hero-fallback.jpg`, JSON-LD `Organization` + `WebSite`. Тесты: 162 файла, 2745 passed, 16 skipped; lint/format/tsc — 0. Валидатор schema.org — 0 ошибок. Три осознанных отклонения от буквы AC (grep-проверка AC5, ручной осмотр hero, непроверяемый VK) описаны в Completion Notes. Статус: ready-for-dev → review. |
| 2026-09-05 | Решения владельца по трём открытым вопросам разбора: (1) `og-image.jpg` **переименовать** в `hero-fallback.jpg`, не удалять; (2) `/register` и `/b2b-register` в объём **не брать** — в `deferred-work.md`; (3) объявлять **фактические** 1040×680, новый файл 1200×630 не ждать. Все три совпали с решениями, уже заложенными в AC — текст стори не менялся. |
| 2026-09-05 | Стори создана (create-story). Разбор дал четыре поправки к тексту эпика: (а) `og-image.jpg` используется двумя hero-компонентами — удаление заменено переименованием; (б) `/login` — Client Component, метаданные требуют нового `layout.tsx`; (в) единственное объявление размеров `og:image` (`(electric)/electric/page.tsx:60-63`) сегодня лживо — 1200×630 при файле 1040×680; (г) `SearchAction` в `WebSite` исключён, `/search` в `Disallow`. Blast radius `buildMetadata` — **CRITICAL** (14 прямых вызывающих), поэтому сигнатура не меняется. Статус: backlog → ready-for-dev. |
