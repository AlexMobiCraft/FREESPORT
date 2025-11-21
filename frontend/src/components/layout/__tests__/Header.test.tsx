/**
 * Tests for Header Component
 * Comprehensive testing of all states, variants, and user interactions
 * Covers: authenticated/unauthenticated states, B2B/B2C UI, mobile menu, cart badge
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import Header from '../Header';
import { useCartStore } from '@/stores/cartStore';
import { authSelectors } from '@/stores/authStore';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
}));

// Mock authStore
vi.mock('@/stores/authStore', () => ({
  authSelectors: {
    useIsAuthenticated: vi.fn(() => false),
    useUser: vi.fn(() => null),
    useIsB2BUser: vi.fn(() => false),
  },
}));

// Mock cartStore
vi.mock('@/stores/cartStore', () => ({
  useCartStore: vi.fn(selector =>
    selector({
      items: [],
      totalAmount: 0,
      addItem: vi.fn(),
      removeItem: vi.fn(),
      updateQuantity: vi.fn(),
      clearCart: vi.fn(),
    })
  ),
}));

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering - Unauthenticated State', () => {
    beforeEach(() => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(false);
      vi.mocked(authSelectors.useUser).mockReturnValue(null);
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(false);
    });

    it('should render logo', () => {
      render(<Header />);
      expect(screen.getByText('FREESPORT')).toBeInTheDocument();
    });

    it('should render navigation items', () => {
      render(<Header />);

      expect(screen.getByRole('link', { name: 'Главная' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Каталог' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Бренды' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Новости' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Акции' })).toBeInTheDocument();
    });

    it('should render action icons (search, favorites, cart)', () => {
      render(<Header />);

      expect(screen.getByRole('button', { name: 'Поиск' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Избранное/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Корзина/i })).toBeInTheDocument();
    });

    it('should render login and register buttons', () => {
      render(<Header />);

      const loginButtons = screen.getAllByRole('link', { name: 'Войти' });
      const registerButtons = screen.getAllByRole('link', { name: 'Регистрация' });

      // Desktop + Mobile
      expect(loginButtons.length).toBeGreaterThan(0);
      expect(registerButtons.length).toBeGreaterThan(0);
    });

    it('should NOT render B2B badge when user is not B2B', () => {
      render(<Header />);
      expect(screen.queryByText('B2B')).not.toBeInTheDocument();
    });

    it('should NOT render B2B navigation items', () => {
      render(<Header />);

      expect(screen.queryByRole('link', { name: 'Оптовые цены' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Заказы' })).not.toBeInTheDocument();
    });
  });

  describe('Rendering - Authenticated State (B2C User)', () => {
    beforeEach(() => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(true);
      vi.mocked(authSelectors.useUser).mockReturnValue({
        id: 1,
        email: 'user@example.com',
        first_name: 'Иван',
        last_name: 'Иванов',
        phone: '+79001234567',
        role: 'retail',
      });
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(false);
    });

    it('should render user greeting with first name', () => {
      render(<Header />);

      const greetings = screen.getAllByText(/Привет, Иван!/i);
      expect(greetings.length).toBeGreaterThan(0);
    });

    it('should render profile button instead of login/register', () => {
      render(<Header />);

      const profileButtons = screen.getAllByRole('link', { name: 'Профиль' });
      expect(profileButtons.length).toBeGreaterThan(0);

      expect(screen.queryByRole('link', { name: 'Войти' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Регистрация' })).not.toBeInTheDocument();
    });

    it('should NOT render B2B badge for B2C user', () => {
      render(<Header />);
      expect(screen.queryByText('B2B')).not.toBeInTheDocument();
    });

    it('should NOT render B2B navigation items for B2C user', () => {
      render(<Header />);

      expect(screen.queryByRole('link', { name: 'Оптовые цены' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Заказы' })).not.toBeInTheDocument();
    });
  });

  describe('Rendering - Authenticated State (B2B User)', () => {
    beforeEach(() => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(true);
      vi.mocked(authSelectors.useUser).mockReturnValue({
        id: 2,
        email: 'b2b@example.com',
        first_name: 'Петр',
        last_name: 'Петров',
        phone: '+79007654321',
        role: 'wholesale_level1',
        company_name: 'ООО "Спорт"',
        tax_id: '1234567890',
        is_verified: true,
      });
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(true);
    });

    it('should render B2B badge next to logo', () => {
      render(<Header />);
      expect(screen.getByText('B2B')).toBeInTheDocument();
    });

    it('should render B2B navigation items', () => {
      render(<Header />);

      expect(screen.getByRole('link', { name: 'Оптовые цены' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Заказы' })).toBeInTheDocument();
    });

    it('should render all standard navigation items plus B2B items', () => {
      render(<Header />);

      // Standard items
      expect(screen.getByRole('link', { name: 'Главная' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Каталог' })).toBeInTheDocument();

      // B2B items
      expect(screen.getByRole('link', { name: 'Оптовые цены' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Заказы' })).toBeInTheDocument();
    });
  });

  describe('Cart Badge', () => {
    it('should NOT display cart badge when cart is empty', () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [],
          totalAmount: 0,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      render(<Header />);

      const cartLinks = screen.getAllByRole('link', { name: /Корзина/i });
      cartLinks.forEach(link => {
        expect(link.querySelector('span')).not.toBeInTheDocument();
      });
    });

    it('should display cart badge with correct count when cart has items', () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [
            {
              id: 1,
              product: {
                id: 1,
                name: 'Product 1',
                slug: 'product-1',
                retail_price: 100,
                is_in_stock: true,
              },
              quantity: 1,
              price: 100,
            },
            {
              id: 2,
              product: {
                id: 2,
                name: 'Product 2',
                slug: 'product-2',
                retail_price: 200,
                is_in_stock: true,
              },
              quantity: 2,
              price: 200,
            },
            {
              id: 3,
              product: {
                id: 3,
                name: 'Product 3',
                slug: 'product-3',
                retail_price: 300,
                is_in_stock: true,
              },
              quantity: 1,
              price: 300,
            },
          ],
          totalAmount: 600,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      render(<Header />);

      const badges = screen.getAllByText('3');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should display "99+" when cart has more than 99 items', () => {
      const items = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1,
        product: {
          id: i + 1,
          name: `Product ${i + 1}`,
          slug: `product-${i + 1}`,
          retail_price: 100,
          is_in_stock: true,
        },
        quantity: 1,
        price: 100,
      }));

      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items,
          totalAmount: 10000,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      render(<Header />);

      const badges = screen.getAllByText('99+');
      expect(badges.length).toBeGreaterThan(0);
    });

    it('should have correct aria-label with item count', () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [
            {
              id: 1,
              product: {
                id: 1,
                name: 'Product 1',
                slug: 'product-1',
                retail_price: 100,
                is_in_stock: true,
              },
              quantity: 1,
              price: 100,
            },
            {
              id: 2,
              product: {
                id: 2,
                name: 'Product 2',
                slug: 'product-2',
                retail_price: 200,
                is_in_stock: true,
              },
              quantity: 2,
              price: 200,
            },
          ],
          totalAmount: 300,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      render(<Header />);

      const desktopCartLink = screen.getByRole('link', { name: 'Корзина (2 товаров)' });
      expect(desktopCartLink).toBeInTheDocument();
    });
  });

  describe('Mobile Menu', () => {
    it('should render mobile menu toggle button', () => {
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: 'Открыть меню' });
      expect(menuButton).toBeInTheDocument();
    });

    it('should NOT show mobile navigation by default', () => {
      render(<Header />);

      // Мобильная навигация не видна изначально
      const mobileNavItems = screen.queryAllByRole('link', { name: 'Главная' });
      // Desktop navigation + NO mobile navigation initially
      expect(mobileNavItems.length).toBe(1);
    });

    it('should toggle mobile menu when button is clicked', async () => {
      const user = userEvent.setup();
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: 'Открыть меню' });
      await user.click(menuButton);

      // После клика меню должно открыться
      expect(screen.getByRole('button', { name: 'Закрыть меню' })).toBeInTheDocument();

      // Проверяем наличие мобильной навигации
      const mobileNavItems = screen.getAllByRole('link', { name: 'Главная' });
      expect(mobileNavItems.length).toBe(2); // Desktop + Mobile
    });

    it('should close mobile menu when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<Header />);

      // Открываем меню
      const openButton = screen.getByRole('button', { name: 'Открыть меню' });
      await user.click(openButton);

      // Закрываем меню
      const closeButton = screen.getByRole('button', { name: 'Закрыть меню' });
      await user.click(closeButton);

      // Проверяем что кнопка снова "Открыть меню"
      expect(screen.getByRole('button', { name: 'Открыть меню' })).toBeInTheDocument();
    });

    it('should have correct aria-expanded attribute', async () => {
      const user = userEvent.setup();
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: 'Открыть меню' });
      expect(menuButton).toHaveAttribute('aria-expanded', 'false');

      await user.click(menuButton);
      expect(screen.getByRole('button', { name: 'Закрыть меню' })).toHaveAttribute(
        'aria-expanded',
        'true'
      );
    });

    it('should display B2B navigation items in mobile menu for B2B user', async () => {
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(true);
      const user = userEvent.setup();
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: 'Открыть меню' });
      await user.click(menuButton);

      // В мобильном меню должны быть B2B элементы
      expect(screen.getAllByRole('link', { name: 'Оптовые цены' }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole('link', { name: 'Заказы' }).length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for action buttons', () => {
      render(<Header />);

      expect(screen.getByRole('button', { name: 'Поиск' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Избранное/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Корзина/i })).toBeInTheDocument();
    });

    it('should have focus styles on interactive elements', () => {
      render(<Header />);

      const searchButton = screen.getByRole('button', { name: 'Поиск' });
      expect(searchButton).toHaveClass('focus:ring-2', 'focus:ring-primary');
    });

    it('should use semantic HTML nav elements', () => {
      render(<Header />);

      const navElements = screen.getAllByRole('navigation');
      expect(navElements.length).toBeGreaterThan(0);
    });
  });

  describe('Styling', () => {
    it('should have correct header height (60px)', () => {
      render(<Header />);

      const header = screen.getByRole('banner');
      const innerDiv = header.querySelector('div > div');
      expect(innerDiv).toHaveClass('h-[60px]');
    });

    it('should have correct shadow styling', () => {
      render(<Header />);

      const header = screen.getByRole('banner');
      expect(header).toHaveClass('shadow-[0_6px_16px_rgba(31,42,68,0.05)]');
    });

    it('should have sticky positioning', () => {
      render(<Header />);

      const header = screen.getByRole('banner');
      expect(header).toHaveClass('sticky', 'top-0', 'z-50');
    });

    it('should apply correct Cart Badge colors', () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [
            {
              id: 1,
              product: {
                id: 1,
                name: 'Product',
                slug: 'product',
                retail_price: 100,
                is_in_stock: true,
              },
              quantity: 1,
              price: 100,
            },
          ],
          totalAmount: 100,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      render(<Header />);

      const badge = screen.getAllByText('1')[0];
      expect(badge).toHaveClass('bg-[#F9E1E1]', 'text-[#A63232]');
    });

    it('should apply correct B2B badge colors', () => {
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(true);
      render(<Header />);

      const b2bBadge = screen.getByText('B2B');
      expect(b2bBadge).toHaveClass('bg-[#F9E1E1]', 'text-[#A63232]');
    });
  });

  describe('Automated Accessibility (axe-core)', () => {
    it('should have no accessibility violations (unauthenticated)', async () => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(false);
      vi.mocked(authSelectors.useUser).mockReturnValue(null);
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(false);

      const { container } = render(<Header />);
      const results = await axe(container);

      expect(results.violations).toEqual([]);
    });

    it('should have no accessibility violations (authenticated B2C)', async () => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(true);
      vi.mocked(authSelectors.useUser).mockReturnValue({
        id: 1,
        email: 'user@example.com',
        first_name: 'Иван',
        last_name: 'Иванов',
        phone: '+79001234567',
        role: 'retail',
      });
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(false);

      const { container } = render(<Header />);
      const results = await axe(container);

      expect(results.violations).toEqual([]);
    });

    it('should have no accessibility violations (authenticated B2B)', async () => {
      vi.mocked(authSelectors.useIsAuthenticated).mockReturnValue(true);
      vi.mocked(authSelectors.useUser).mockReturnValue({
        id: 2,
        email: 'b2b@example.com',
        first_name: 'Петр',
        last_name: 'Петров',
        phone: '+79007654321',
        role: 'wholesale_level1',
        company_name: 'ООО "Спорт"',
        tax_id: '1234567890',
        is_verified: true,
      });
      vi.mocked(authSelectors.useIsB2BUser).mockReturnValue(true);

      const { container } = render(<Header />);
      const results = await axe(container);

      expect(results.violations).toEqual([]);
    });

    it('should have no accessibility violations with cart items', async () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [
            {
              id: 1,
              product: {
                id: 1,
                name: 'Product 1',
                slug: 'product-1',
                retail_price: 100,
                is_in_stock: true,
              },
              quantity: 1,
              price: 100,
            },
            {
              id: 2,
              product: {
                id: 2,
                name: 'Product 2',
                slug: 'product-2',
                retail_price: 200,
                is_in_stock: true,
              },
              quantity: 2,
              price: 200,
            },
          ],
          totalAmount: 300,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      const { container } = render(<Header />);
      const results = await axe(container);

      expect(results.violations).toEqual([]);
    });

    it('should have no accessibility violations with mobile menu open', async () => {
      const user = userEvent.setup();
      const { container } = render(<Header />);

      const menuButton = screen.getByRole('button', { name: 'Открыть меню' });
      await user.click(menuButton);

      const results = await axe(container);
      expect(results.violations).toEqual([]);
    });

    it('should verify color contrast for Cart Badge (#A63232 on #F9E1E1)', async () => {
      vi.mocked(useCartStore).mockImplementation(selector =>
        selector({
          items: [
            {
              id: 1,
              product: {
                id: 1,
                name: 'Product',
                slug: 'product',
                retail_price: 100,
                is_in_stock: true,
              },
              quantity: 1,
              price: 100,
            },
          ],
          totalAmount: 100,
          addItem: vi.fn(),
          removeItem: vi.fn(),
          updateQuantity: vi.fn(),
          clearCart: vi.fn(),
        })
      );

      const { container } = render(<Header />);
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });

      expect(results.violations).toEqual([]);
    });
  });
});
