/**
 * Unit тесты для HeroSection компонента
 *
 * Проверяет:
 * - Рендеринг правильного баннера для разных ролей пользователей
 * - Применение design tokens
 * - CTA кнопки и их handlers
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import HeroSection from '../HeroSection';
import { useAuthStore } from '@/stores/authStore';
import type { User } from '@/types/api';

// Mock Zustand store
vi.mock('@/stores/authStore');

// Mock Next.js Link component
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('HeroSection Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Рендеринг баннеров для разных ролей', () => {
    it('должен отображать B2B баннер для wholesale_level1 пользователя', () => {
      const mockUser: User = {
        id: 1,
        email: 'b2b@test.com',
        first_name: 'Test',
        last_name: 'B2B',
        phone: '+79001234567',
        role: 'wholesale_level1',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      expect(screen.getByText(/Оптовые поставки спортивных товаров/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Специальные цены для бизнеса. Персональный менеджер и гибкие условия./i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Узнать оптовые условия/i)).toBeInTheDocument();
    });

    it('должен отображать B2B баннер для wholesale_level2 пользователя', () => {
      const mockUser: User = {
        id: 2,
        email: 'b2b2@test.com',
        first_name: 'Test',
        last_name: 'B2B2',
        phone: '+79001234567',
        role: 'wholesale_level2',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      expect(screen.getByText(/Оптовые поставки спортивных товаров/i)).toBeInTheDocument();
    });

    it('должен отображать B2B баннер для wholesale_level3 пользователя', () => {
      const mockUser: User = {
        id: 3,
        email: 'b2b3@test.com',
        first_name: 'Test',
        last_name: 'B2B3',
        phone: '+79001234567',
        role: 'wholesale_level3',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      expect(screen.getByText(/Оптовые поставки спортивных товаров/i)).toBeInTheDocument();
    });

    it('должен отображать B2C баннер для retail пользователя', () => {
      const mockUser: User = {
        id: 4,
        email: 'retail@test.com',
        first_name: 'Test',
        last_name: 'Retail',
        phone: '+79001234567',
        role: 'retail',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      expect(screen.getByText(/Новая коллекция 2025/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Стиль и качество для вашего спорта. Эксклюзивные новинки уже в продаже./i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Перейти в каталог/i)).toBeInTheDocument();
    });

    it('должен отображать универсальный баннер для неавторизованного пользователя', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      expect(
        screen.getByText(/FREESPORT - Спортивные товары для профессионалов и любителей/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/5 брендов. 1000\+ товаров. Доставка по всей России./i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Начать покупки/i)).toBeInTheDocument();
    });
  });

  describe('Проверка CTA кнопок', () => {
    it('B2B баннер должен содержать ссылку на /wholesale', () => {
      const mockUser: User = {
        id: 1,
        email: 'b2b@test.com',
        first_name: 'Test',
        last_name: 'B2B',
        phone: '+79001234567',
        role: 'wholesale_level1',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/wholesale');
    });

    it('B2C баннер должен содержать ссылку на /catalog', () => {
      const mockUser: User = {
        id: 4,
        email: 'retail@test.com',
        first_name: 'Test',
        last_name: 'Retail',
        phone: '+79001234567',
        role: 'retail',
      };

      vi.mocked(useAuthStore).mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        accessToken: 'mock-token',
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/catalog');
    });

    it('Универсальный баннер должен содержать ссылку на /catalog', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      render(<HeroSection />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/catalog');
    });
  });

  describe('Применение Design Tokens', () => {
    it('должен применять правильные CSS классы для типографики', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<HeroSection />);

      // Проверка hero секции
      const section = container.querySelector('section');
      expect(section).toHaveClass('text-text-inverse');

      // Проверка заголовка (h1 должен иметь display-l стили)
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveClass('font-bold');
      expect(heading).toHaveClass('text-text-inverse');
    });

    it('должен применять цветовую схему из design system', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<HeroSection />);

      const section = container.querySelector('section');
      expect(section).toHaveClass('bg-gradient-to-r');
      expect(section).toHaveClass('from-neutral-900');
      expect(section).toHaveClass('to-neutral-700');
    });
  });

  describe('Адаптивность', () => {
    it('должен рендерить responsive контейнер с max-width 1280px', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        user: null,
        isAuthenticated: false,
        accessToken: null,
        setTokens: vi.fn(),
        setUser: vi.fn(),
        logout: vi.fn(),
        getRefreshToken: vi.fn(),
      });

      const { container } = render(<HeroSection />);

      const innerContainer = container.querySelector('.mx-auto');
      expect(innerContainer).toBeInTheDocument();
      expect(innerContainer).toHaveStyle({ maxWidth: '1280px' });
    });
  });
});
