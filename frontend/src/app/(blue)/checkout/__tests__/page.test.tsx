import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderToString } from 'react-dom/server';
import { CheckoutPageClient } from '../CheckoutPageClient';
import { useAuth } from '@/providers/AuthProvider';
import { useAuthStore } from '@/stores/authStore';
import { useCartStore } from '@/stores/cartStore';
import { useOrderStore } from '@/stores/orderStore';
import type { User } from '@/types/api';
import type { Order } from '@/types/order';

// Мок @/providers/AuthProvider обязателен (Story 41.10, врезка 🔴):
// useAuth() вне AuthProvider навсегда возвращает isInitialized: false.
vi.mock('@/providers/AuthProvider', () => ({
  useAuth: vi.fn(() => ({ isInitialized: true, isLoading: false })),
}));
vi.mock('@/stores/authStore');
vi.mock('@/stores/cartStore');
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  first_name: 'Иван',
  last_name: 'Петров',
  phone: '+79001234567',
  role: 'retail',
};

/**
 * Mock структуры CartItem согласно типу из @/types/cart.ts
 */
const mockCartItems = [
  {
    id: 1,
    variant_id: 1,
    product: {
      id: 1,
      name: 'Test Product',
      slug: 'test-product',
      image: null,
    },
    variant: {
      sku: 'TEST-001',
      color_name: 'Red',
      size_value: 'M',
    },
    quantity: 1,
    unit_price: '100.00',
    total_price: '100.00',
    added_at: new Date().toISOString(),
  },
];

function mockAuthState(overrides: { isInitialized?: boolean; isLoading?: boolean } = {}) {
  (useAuth as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    isInitialized: true,
    isLoading: false,
    ...overrides,
  });
}

function mockAuthStoreState(overrides: { user?: User | null; isAuthenticated?: boolean } = {}) {
  (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    user: null,
    isAuthenticated: false,
    ...overrides,
  });
}

/** Мокирует useCartStore() и его статический useCartStore.getState() одним и тем же состоянием. */
function mockCartState(
  overrides: {
    items?: typeof mockCartItems;
    error?: string | null;
    fetchCart?: ReturnType<typeof vi.fn>;
  } = {}
) {
  const state = {
    items: [] as typeof mockCartItems,
    totalPrice: 0,
    totalItems: 0,
    error: null as string | null,
    fetchCart: vi.fn().mockResolvedValue(undefined),
    getPromoDiscount: vi.fn().mockReturnValue(0),
    ...overrides,
  };
  const mocked = useCartStore as unknown as ReturnType<typeof vi.fn> & {
    getState: ReturnType<typeof vi.fn>;
  };
  mocked.mockReturnValue(state);
  mocked.getState = vi.fn(() => state);
  return state;
}

describe('CheckoutPageClient (Story 41.10)', () => {
  beforeEach(() => {
    useOrderStore.setState({ currentOrder: null, isSubmitting: false, error: null });
    mockAuthState();
    mockAuthStoreState();
    mockCartState();
  });

  describe('AC1 — аноним видит приглашение, а не форму', () => {
    it('показывает checkout-login-required и не запрашивает корзину', () => {
      mockAuthStoreState({ user: null, isAuthenticated: false });
      const cart = mockCartState();

      const { container } = render(<CheckoutPageClient />);

      expect(screen.getByTestId('checkout-login-required')).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { level: 2, name: 'Войдите, чтобы оформить заказ' })
      ).toBeInTheDocument();
      expect(
        screen.getByText('Оформление заказа доступно после входа в личный кабинет.')
      ).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Войти' })).toHaveAttribute(
        'href',
        '/login?next=%2Fcheckout'
      );
      expect(cart.fetchCart).not.toHaveBeenCalled();
      expect(container.querySelector('form')).toBeNull();
      expect(container.querySelector('input')).toBeNull();
      expect(container.querySelector('textarea')).toBeNull();
      expect(container.querySelector('select')).toBeNull();
    });

    it('то же самое при непустой гостевой корзине', () => {
      mockAuthStoreState({ user: null, isAuthenticated: false });
      const cart = mockCartState({ items: mockCartItems });

      const { container } = render(<CheckoutPageClient />);

      expect(screen.getByTestId('checkout-login-required')).toBeInTheDocument();
      expect(cart.fetchCart).not.toHaveBeenCalled();
      expect(container.querySelector('form')).toBeNull();
    });
  });

  describe('AC2 — загрузка не выглядит как пустая корзина', () => {
    it('isInitialized=false → checkout-loading, без текста "Корзина пуста"', () => {
      mockAuthState({ isInitialized: false, isLoading: true });
      mockAuthStoreState({ user: null, isAuthenticated: false });
      mockCartState();

      render(<CheckoutPageClient />);

      expect(screen.getByTestId('checkout-loading')).toBeInTheDocument();
      expect(screen.getByText('Загрузка…')).toBeInTheDocument();
      expect(screen.queryByText('Корзина пуста')).not.toBeInTheDocument();
    });

    it('авторизован, fetchCart ещё не разрешился → checkout-loading', () => {
      mockAuthState({ isInitialized: true, isLoading: false });
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      // Промис, который никогда не разрешается в рамках теста — имитирует "в полёте" запрос.
      mockCartState({ fetchCart: vi.fn(() => new Promise(() => {})) });

      render(<CheckoutPageClient />);

      expect(screen.getByTestId('checkout-loading')).toBeInTheDocument();
    });

    it('renderToString: первый рендер — индикатор загрузки при любом состоянии сторов', () => {
      mockAuthState({ isInitialized: true, isLoading: false });
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      mockCartState({ items: mockCartItems });

      const html = renderToString(<CheckoutPageClient />);

      expect(html).not.toContain('name="email"');
      expect(html).toContain('checkout-loading');
    });
  });

  describe('AC3 — авторизованный с пустой корзиной', () => {
    it('показывает checkout-empty-cart без нулевого итога', async () => {
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      mockCartState({ items: [] });

      render(<CheckoutPageClient />);

      await screen.findByTestId('checkout-empty-cart');
      expect(
        screen.getByRole('heading', { level: 2, name: 'Корзина пуста' })
      ).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'В каталог' })).toHaveAttribute('href', '/catalog');
      expect(screen.queryByTestId('total-price')).not.toBeInTheDocument();
      expect(screen.queryByTestId('total-price-items')).not.toBeInTheDocument();
    });
  });

  describe('AC4 — ошибка загрузки корзины с повтором', () => {
    it('показывает checkout-cart-error и повторяет запрос по клику "Повторить"', async () => {
      const user = userEvent.setup();
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      const cart = mockCartState({ error: 'Network Error' });

      render(<CheckoutPageClient />);

      await screen.findByTestId('checkout-cart-error');
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.queryByText('Network Error')).not.toBeInTheDocument();
      expect(cart.fetchCart).toHaveBeenCalledTimes(1);

      await user.click(screen.getByRole('button', { name: 'Повторить' }));

      expect(cart.fetchCart).toHaveBeenCalledTimes(2);
    });
  });

  describe('AC5 — авторизованный с товарами: регрессии нет', () => {
    it('показывает форму, сводку и автозаполнение из user', async () => {
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      mockCartState({ items: mockCartItems });

      render(<CheckoutPageClient />);

      await screen.findByText('Контактные данные');
      expect(screen.getByText('Адрес доставки')).toBeInTheDocument();
      expect(screen.getByText('Здравствуйте, Иван Петров')).toBeInTheDocument();
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+79001234567')).toBeInTheDocument();
      expect(screen.getByText('Test Product')).toBeInTheDocument();
      expect(screen.getByText('Ваш заказ')).toBeInTheDocument();
    });
  });

  describe('AC6 — после успешного заказа не мигает пустое состояние', () => {
    it('currentOrder, появившийся во время сессии, показывает checkout-redirecting', async () => {
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      mockCartState({ items: [] });

      render(<CheckoutPageClient />);

      await screen.findByTestId('checkout-empty-cart');

      act(() => {
        useOrderStore.setState({
          currentOrder: { id: 42 } as Order,
          isSubmitting: false,
          error: null,
        });
      });

      expect(screen.getByTestId('checkout-redirecting')).toBeInTheDocument();
      expect(
        screen.getByText('Заказ оформлен. Переходим к подтверждению…')
      ).toBeInTheDocument();
    });

    it('устаревший currentOrder от прошлого заказа не блокирует новую форму', async () => {
      useOrderStore.setState({
        currentOrder: { id: 1 } as Order,
        isSubmitting: false,
        error: null,
      });
      mockAuthStoreState({ user: mockUser, isAuthenticated: true });
      mockCartState({ items: mockCartItems });

      render(<CheckoutPageClient />);

      await waitFor(() => {
        expect(useOrderStore.getState().currentOrder).toBeNull();
      });
      await screen.findByText('Контактные данные');
      expect(screen.queryByTestId('checkout-redirecting')).not.toBeInTheDocument();
    });
  });

  describe('AC7 — ровно один returns-support-notice в любом состоянии', () => {
    const scenarios: Array<[string, () => void]> = [
      [
        'anonymous',
        () => {
          mockAuthStoreState({ user: null, isAuthenticated: false });
          mockCartState();
        },
      ],
      [
        'loading',
        () => {
          mockAuthState({ isInitialized: false, isLoading: true });
          mockAuthStoreState({ user: null, isAuthenticated: false });
          mockCartState();
        },
      ],
      [
        'empty',
        () => {
          mockAuthStoreState({ user: mockUser, isAuthenticated: true });
          mockCartState({ items: [] });
        },
      ],
      [
        'error',
        () => {
          mockAuthStoreState({ user: mockUser, isAuthenticated: true });
          mockCartState({ error: 'Network Error' });
        },
      ],
      [
        'form',
        () => {
          mockAuthStoreState({ user: mockUser, isAuthenticated: true });
          mockCartState({ items: mockCartItems });
        },
      ],
    ];

    it.each(scenarios)('%s: ровно один returns-support-notice', async (_name, setup) => {
      setup();

      render(<CheckoutPageClient />);

      await waitFor(() => {
        expect(screen.getAllByTestId('returns-support-notice')).toHaveLength(1);
      });
    });
  });

  describe('Заголовок страницы', () => {
    it('всегда отображает "Оформление заказа"', () => {
      mockAuthStoreState({ user: null, isAuthenticated: false });

      render(<CheckoutPageClient />);

      expect(
        screen.getByRole('heading', { name: /оформление заказа/i, level: 1 })
      ).toBeInTheDocument();
    });
  });
});
