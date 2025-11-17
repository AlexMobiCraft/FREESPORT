/**
 * Интеграционные тесты для главной страницы (/)
 *
 * Проверяет:
 * - Корректный рендеринг страницы на роуте /
 * - Наличие SEO метатегов
 * - Интеграцию с HeroSection
 * - Адаптивность на разных viewport размерах
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Home, { metadata, revalidate } from '../page';
import { useAuthStore } from '@/stores/authStore';

// Mock Zustand store
vi.mock('@/stores/authStore');

// Mock Next.js Link component
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('Главная страница (/)', () => {
  describe('Рендеринг страницы', () => {
    it('должна рендериться без ошибок', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<Home />);
      expect(container).toBeInTheDocument();
    });

    it('должна содержать HeroSection компонент', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<Home />);

      // Проверка наличия hero секции по заголовку
      expect(
        screen.getByText(/FREESPORT - Спортивные товары для профессионалов и любителей/i)
      ).toBeInTheDocument();
    });

    it('должна содержать секцию "Преимущества платформы"', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<Home />);

      expect(screen.getByText(/Преимущества платформы/i)).toBeInTheDocument();
    });

    it('должна содержать секцию "Решения для бизнеса"', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<Home />);

      expect(screen.getByText(/Решения для бизнеса/i)).toBeInTheDocument();
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
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<Home />);

      // Проверка наличия контейнеров с max-width
      const containers = container.querySelectorAll('.max-w-7xl, .mx-auto');
      expect(containers.length).toBeGreaterThan(0);
    });

    it('должна содержать адаптивные padding классы', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<Home />);

      // Проверка responsive padding (sm:px-6, lg:px-8)
      const responsiveContainers = container.querySelectorAll('[class*="px-"]');
      expect(responsiveContainers.length).toBeGreaterThan(0);
    });
  });

  describe('Интеграция с authStore', () => {
    it('должна корректно работать с авторизованным B2B пользователем', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: {
          id: 1,
          email: 'b2b@test.com',
          first_name: 'Test',
          last_name: 'B2B',
          phone: '+79001234567',
          role: 'wholesale_level1',
        },
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<Home />);

      // HeroSection должен показывать B2B баннер
      expect(screen.getByText(/Оптовые поставки спортивных товаров/i)).toBeInTheDocument();
    });

    it('должна корректно работать с авторизованным B2C пользователем', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: {
          id: 2,
          email: 'retail@test.com',
          first_name: 'Test',
          last_name: 'Retail',
          phone: '+79001234567',
          role: 'retail',
        },
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<Home />);

      // HeroSection должен показывать B2C баннер
      expect(screen.getByText(/Новая коллекция 2025/i)).toBeInTheDocument();
    });
  });
});
