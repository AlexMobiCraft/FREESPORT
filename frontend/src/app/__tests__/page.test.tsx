/**
 * Интеграционные тесты для главной страницы (/)
 *
 * Проверяет:
 * - Корректный рендеринг страницы на роуте /
 * - Наличие SEO метатегов
 * - Интеграцию с HeroSection
 * - Адаптивность на разных viewport размерах
 */

import { describe, it, expect, vi, beforeEach, beforeAll, afterEach, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import Home, { metadata, revalidate } from '../page';

// Mock authStore state (mutable)
let mockAuthState = {
  user: null,
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  setTokens: vi.fn(),
  setUser: vi.fn(),
  logout: vi.fn(),
  getRefreshToken: vi.fn().mockReturnValue(null),
};

// Mock Zustand store with getState method
vi.mock('@/stores/authStore', () => ({
  useAuthStore: Object.assign(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.fn((selector: any) => {
      return selector ? selector(mockAuthState) : mockAuthState;
    }),
    {
      getState: () => mockAuthState,
    }
  ),
  authSelectors: {
    useUser: () => mockAuthState.user,
    useIsAuthenticated: () => mockAuthState.isAuthenticated,
  },
}));

// Mock Next.js Link component
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Setup MSW server for API mocking
const server = setupServer(
  http.get('*/api/v1/banners/', () => {
    return HttpResponse.json([
      {
        id: 1,
        title: 'FREESPORT - Спортивные товары для профессионалов и любителей',
        subtitle: '5 брендов. 1000+ товаров. Доставка по всей России.',
        image_url: '/test-banner.jpg',
        image_alt: 'FREESPORT баннер',
        cta_text: 'Начать покупки',
        cta_link: '/catalog',
      },
    ]);
  }),
  // Other endpoints can be added here as needed
  http.get('*/api/v1/categories/', () => {
    return HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  }),
  http.get('*/api/v1/products/', () => {
    return HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Главная страница (/)', () => {
  beforeEach(() => {
    // Reset mock state before each test
    mockAuthState = {
      user: null,
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      setTokens: vi.fn(),
      setUser: vi.fn(),
      logout: vi.fn(),
      getRefreshToken: vi.fn().mockReturnValue(null),
    };
  });

  describe('Рендеринг страницы', () => {
    it('должна рендериться без ошибок', () => {
      const { container } = render(<Home />);
      expect(container).toBeInTheDocument();
    });

    it('должна содержать HeroSection компонент', async () => {
      render(<Home />);

      // Проверка наличия hero секции по заголовку (ждём загрузку)
      expect(
        await screen.findByText(/FREESPORT - Спортивные товары для профессионалов и любителей/i)
      ).toBeInTheDocument();
    });

    it('должна содержать секцию "Преимущества платформы"', async () => {
      render(<Home />);

      expect(await screen.findByText(/Преимущества платформы/i)).toBeInTheDocument();
    });

    it('должна содержать секцию "Решения для бизнеса"', async () => {
      render(<Home />);

      expect(await screen.findByText(/Решения для бизнеса/i)).toBeInTheDocument();
    });
  });

  describe('SEO Metadata', () => {
    it('должна содержать правильный title', () => {
      expect(metadata.title).toBe(
        'FREESPORT - Оптовые поставки спортивных товаров | B2B и Розница'
      );
    });

    it('должна содержать правильный description', () => {
      expect(metadata.description).toContain('Оптовые поставки спортивных товаров');
      expect(metadata.description).toContain('B2B и розничных покупателей');
      expect(metadata.description).toContain('5 брендов');
    });

    it('должна содержать keywords', () => {
      expect(metadata.keywords).toBeDefined();
      expect(Array.isArray(metadata.keywords)).toBe(true);
      expect(metadata.keywords).toContain('спортивные товары оптом');
      expect(metadata.keywords).toContain('FREESPORT');
    });

    it('должна содержать OpenGraph метатеги', () => {
      expect(metadata.openGraph).toBeDefined();
      expect(metadata.openGraph?.title).toBe('FREESPORT - Оптовые поставки спортивных товаров');
      expect(metadata.openGraph?.description).toContain('B2B и B2C продажи');
      expect(metadata.openGraph?.url).toBe('https://freesport.ru');
      expect(metadata.openGraph?.siteName).toBe('FREESPORT');
      expect(metadata.openGraph?.locale).toBe('ru_RU');
      expect(metadata.openGraph?.type).toBe('website');
    });

    it('должна содержать OpenGraph изображение', () => {
      expect(metadata.openGraph?.images).toBeDefined();
      expect(Array.isArray(metadata.openGraph?.images)).toBe(true);

      const images = metadata.openGraph?.images as Array<{
        url: string;
        width: number;
        height: number;
        alt?: string;
      }>;

      expect(images[0]).toEqual({
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'FREESPORT - Платформа спортивных товаров',
      });
    });

    it('должна содержать Twitter метатеги', () => {
      expect(metadata.twitter).toBeDefined();
      expect(metadata.twitter?.card).toBe('summary_large_image');
      expect(metadata.twitter?.title).toBe('FREESPORT - Оптовые поставки спортивных товаров');
      expect(metadata.twitter?.images).toContain('/og-image.jpg');
    });
  });

  describe('SSG/ISR конфигурация', () => {
    it('должна иметь правильное значение revalidate для ISR', () => {
      expect(revalidate).toBe(3600); // 1 час в секундах
    });
  });

  describe('Адаптивность', () => {
    it('должна иметь responsive контейнер', () => {
      const { container } = render(<Home />);

      // Проверка наличия контейнеров с max-width
      const containers = container.querySelectorAll('.max-w-7xl, .mx-auto');
      expect(containers.length).toBeGreaterThan(0);
    });

    it('должна содержать адаптивные padding классы', () => {
      const { container } = render(<Home />);

      // Проверка responsive padding (sm:px-6, lg:px-8)
      const responsiveContainers = container.querySelectorAll('[class*="px-"]');
      expect(responsiveContainers.length).toBeGreaterThan(0);
    });
  });

  describe('Интеграция с authStore', () => {
    it('должна корректно работать с авторизованным B2B пользователем', async () => {
      mockAuthState.user = {
        id: 1,
        email: 'b2b@test.com',
        first_name: 'Test',
        last_name: 'B2B',
        phone: '+79001234567',
        role: 'wholesale_level1',
        is_verified: true,
      };
      mockAuthState.isAuthenticated = true;
      mockAuthState.accessToken = 'mock-token';

      render(<Home />);

      // HeroSection должен показывать баннер (может быть любой текст из баннера)
      await waitFor(() => {
        expect(
          screen.getByText(/FREESPORT - Спортивные товары для профессионалов и любителей/i)
        ).toBeInTheDocument();
      });
    });

    it('должна корректно работать с авторизованным B2C пользователем', async () => {
      mockAuthState.user = {
        id: 2,
        email: 'retail@test.com',
        first_name: 'Test',
        last_name: 'Retail',
        phone: '+79001234567',
        role: 'retail',
        is_verified: true,
      };
      mockAuthState.isAuthenticated = true;
      mockAuthState.accessToken = 'mock-token';

      render(<Home />);

      // HeroSection должен показывать баннер (может быть любой текст из баннера)
      await waitFor(() => {
        expect(
          screen.getByText(/FREESPORT - Спортивные товары для профессионалов и любителей/i)
        ).toBeInTheDocument();
      });
    });
  });
});
