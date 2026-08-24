import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { NextRequest } from 'next/server';

// Mock NextResponse
vi.mock('next/server', async () => {
  const actual = await vi.importActual('next/server');
  return {
    ...actual,
    NextResponse: {
      next: vi.fn(),
      redirect: vi.fn(),
      rewrite: vi.fn(),
    },
  };
});

/**
 * Загружает middleware с чистым модульным состоянием.
 *
 * Кэш опубликованных слагов живёт в переменных модуля, поэтому без
 * `vi.resetModules()` он протекает между тестами и результат начинает
 * зависеть от порядка их выполнения.
 */
async function loadMiddleware() {
  vi.resetModules();
  const server = await import('next/server');
  const mod = await import('../middleware');
  return { middleware: mod.middleware, NextResponse: server.NextResponse };
}

/** Ответ API со списком опубликованных CMS-слагов */
function slugsResponse(slugs: string[]) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ count: slugs.length, results: slugs.map(slug => ({ slug })) }),
  };
}

describe('Middleware', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock = vi.fn(async () => slugsResponse(['oferta']));
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  const createRequest = (pathname: string, hasToken: boolean = false, nextParam?: string) => {
    const url = new URL(`http://localhost:3000${pathname}`);
    if (nextParam) {
      url.searchParams.set('next', nextParam);
    }

    const req = {
      nextUrl: url,
      cookies: {
        get: (name: string) =>
          name === 'refreshToken' && hasToken ? { value: 'token' } : undefined,
      },
      url: url.toString(),
    } as unknown as NextRequest;

    // Helper needed because NextRequest clone() is complex to mock fully
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    req.nextUrl.clone = () => new URL(url.toString()) as any;

    return req;
  };

  it('redirects unauthenticated user to login when accessing protected route', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/profile');
    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const redirectUrl = (NextResponse.redirect as any).mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/login');
    expect(redirectUrl.searchParams.get('next')).toBe('/profile');
    // Редирект не должен ходить в сеть за списком слагов
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('allows authenticated user to access protected route', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/profile', true);
    await middleware(req);

    expect(NextResponse.next).toHaveBeenCalled();
  });

  it('redirects authenticated user to home from auth page when no next param', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/login', true);
    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const redirectUrl = (NextResponse.redirect as any).mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/');
  });

  it('redirects authenticated user to next param url from auth page', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/login', true, '/cart');
    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const callArgs = (NextResponse.redirect as any).mock.calls[0];
    // NextResponse.redirect(new URL(...))
    const redirectUrl = callArgs[0];
    expect(redirectUrl.pathname).toBe('/cart');
  });

  it('redirects authenticated user to redirect param url from auth page', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const url = new URL('http://localhost:3000/login');
    url.searchParams.set('redirect', '/checkout');
    const req = {
      nextUrl: url,
      cookies: {
        get: (name: string) => (name === 'refreshToken' ? { value: 'token' } : undefined),
      },
      url: url.toString(),
    } as unknown as NextRequest;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    req.nextUrl.clone = () => new URL(url.toString()) as any;

    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const redirectUrl = (NextResponse.redirect as any).mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/checkout');
  });

  it('sanitizes next param: redirects to home if next param is external domain', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/login', true, '//google.com');
    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const redirectUrl = (NextResponse.redirect as any).mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/');
  });

  it('sanitizes next param: redirects to home if next param does not start with /', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    const req = createRequest('/login', true, 'javascript:alert(1)');
    await middleware(req);

    expect(NextResponse.redirect).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const redirectUrl = (NextResponse.redirect as any).mock.calls[0][0];
    expect(redirectUrl.pathname).toBe('/');
  });
});

describe('Middleware: настоящий 404 для несуществующих адресов', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock = vi.fn(async () => slugsResponse(['oferta']));
    vi.stubGlobal('fetch', fetchMock);
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    warnSpy.mockRestore();
    vi.useRealTimers();
  });

  const anonymousRequest = (pathname: string) => {
    const url = new URL(`http://localhost:3000${pathname}`);
    const req = {
      nextUrl: url,
      cookies: { get: () => undefined },
      url: url.toString(),
    } as unknown as NextRequest;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    req.nextUrl.clone = () => new URL(url.toString()) as any;
    return req;
  };

  it('отдаёт 404 на несуществующий адрес верхнего уровня', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [destination, init] = (NextResponse.rewrite as any).mock.calls[0];
    expect(destination.pathname).toBe('/_not-found');
    expect(init).toEqual({ status: 404 });
    expect(NextResponse.next).not.toHaveBeenCalled();
  });

  it.each(['/terms', '/korzina', '/basket', '/order', '/product'])(
    'отдаёт 404 на фантомный адрес %s из отчёта аудита',
    async pathname => {
      const { middleware, NextResponse } = await loadMiddleware();
      await middleware(anonymousRequest(pathname));

      expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    }
  );

  it('пропускает опубликованную CMS-страницу', async () => {
    const { middleware, NextResponse } = await loadMiddleware();
    await middleware(anonymousRequest('/oferta'));

    expect(NextResponse.next).toHaveBeenCalled();
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
  });

  it.each(['/about', '/catalog', '/coming-soon', '/electric-orange'])(
    'пропускает известный маршрут %s без обращения к API',
    async pathname => {
      const { middleware, NextResponse } = await loadMiddleware();
      await middleware(anonymousRequest(pathname));

      expect(NextResponse.next).toHaveBeenCalled();
      expect(NextResponse.rewrite).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    }
  );

  it.each(['/', '/foo/bar', '/profile/orders/1'])(
    'не вмешивается в путь %s (не зона catch-all)',
    async pathname => {
      const { middleware, NextResponse } = await loadMiddleware();
      await middleware(anonymousRequest(pathname));

      expect(NextResponse.rewrite).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    }
  );

  it('fail-open: пропускает запрос, когда backend недоступен', async () => {
    fetchMock.mockRejectedValueOnce(new Error('ECONNREFUSED'));
    const { middleware, NextResponse } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    expect(NextResponse.next).toHaveBeenCalled();
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalled();
  });

  it('fail-open: пропускает запрос, когда API отвечает ошибкой', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({}) });
    const { middleware, NextResponse } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    expect(NextResponse.next).toHaveBeenCalled();
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalled();
  });

  it('fail-open: пропускает запрос, когда ответ API не разобрался', async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ results: 42 }) });
    const { middleware, NextResponse } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    expect(NextResponse.next).toHaveBeenCalled();
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalled();
  });

  it('кэширует список слагов: два запроса подряд дают один вызов API', async () => {
    const { middleware } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));
    await middleware(anonymousRequest('/terms'));

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('запрашивает список слагов заново после истечения TTL', async () => {
    vi.useFakeTimers();
    const { middleware } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // TTL — 5 минут; сдвигаем время за его пределы
    vi.advanceTimersByTime(5 * 60 * 1000 + 1);
    await middleware(anonymousRequest('/terms'));

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('запрашивает список слагов с page_size, покрывающим всю выдачу', async () => {
    const { middleware } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    const requestedUrl = String(fetchMock.mock.calls[0][0]);
    expect(requestedUrl).toContain('/pages/');
    expect(requestedUrl).toContain('page_size=1000');
  });

  it('ограничивает запрос списка слагов таймаутом', async () => {
    const { middleware } = await loadMiddleware();
    await middleware(anonymousRequest('/offer'));

    const init = fetchMock.mock.calls[0][1] as RequestInit | undefined;
    expect(init?.signal).toBeDefined();
  });
});
