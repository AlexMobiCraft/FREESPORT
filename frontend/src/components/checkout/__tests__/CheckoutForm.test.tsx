import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CheckoutForm } from '../CheckoutForm';
import { useCartStore } from '@/stores/cartStore';
import type { User } from '@/types/api';

// Mock зависимостей
vi.mock('@/stores/cartStore');
vi.mock('@/stores/orderStore', () => ({
  useOrderStore: vi.fn(() => ({
    createOrder: vi.fn(),
    isSubmitting: false,
    error: null,
    clearOrder: vi.fn(),
  })),
}));
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('CheckoutForm', () => {
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
   * Исправлено по результатам QA review: добавлен product объект,
   * структура variant обновлена с color_name и size_value
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
      quantity: 2,
      unit_price: '100.00',
      total_price: '200.00',
      added_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (useCartStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      items: mockCartItems,
      totalPrice: 200,
      totalItems: 2,
      fetchCart: vi.fn(),
      getPromoDiscount: vi.fn().mockReturnValue(0),
    });
  });

  describe('Rendering', () => {
    it('должен отображать все секции формы', () => {
      render(<CheckoutForm user={null} />);

      expect(screen.getByText('Контактные данные')).toBeInTheDocument();
      expect(screen.getByText('Адрес доставки')).toBeInTheDocument();
      expect(screen.getByText('Способ доставки')).toBeInTheDocument();
      expect(screen.getByText('Комментарий к заказу')).toBeInTheDocument();
      expect(screen.getByText('Ваш заказ')).toBeInTheDocument();
    });

    it('должен отображать кнопку "Оформить заказ"', () => {
      render(<CheckoutForm user={null} />);

      const submitButton = screen.getByRole('button', {
        name: /оформить заказ/i,
      });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('Автозаполнение для авторизованных пользователей', () => {
    it('должен автозаполнять контактные данные из user', () => {
      render(<CheckoutForm user={mockUser} />);

      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+79001234567')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Иван')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Петров')).toBeInTheDocument();
    });

    it('должен отображать пустые поля для неавторизованных пользователей', () => {
      render(<CheckoutForm user={null} />);

      const emailInput = screen.getByLabelText('Email') as HTMLInputElement;
      const phoneInput = screen.getByLabelText('Телефон') as HTMLInputElement;

      expect(emailInput.value).toBe('');
      expect(phoneInput.value).toBe('');
    });
  });

  describe('Валидация формы', () => {
    it('должен показывать ошибки при отправке пустой формы', async () => {
      render(<CheckoutForm user={null} />);

      const submitButton = screen.getByRole('button', {
        name: /оформить заказ/i,
      });

      fireEvent.click(submitButton);

      await waitFor(() => {
        // Input компонент рендерит ошибку в двух местах (visible + sr-only)
        const errors = screen.getAllByText('Email обязателен');
        expect(errors.length).toBeGreaterThan(0);
      });
    });

    it('должен показывать ошибку при некорректном формате email', async () => {
      render(<CheckoutForm user={null} />);

      const emailInput = screen.getByLabelText('Email');
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.blur(emailInput);

      await waitFor(() => {
        // Input компонент рендерит ошибку в двух местах (visible + sr-only)
        const errors = screen.getAllByText('Некорректный формат email');
        expect(errors.length).toBeGreaterThan(0);
      });
    });

    it('должен показывать ошибку при некорректном формате телефона', async () => {
      render(<CheckoutForm user={null} />);

      const phoneInput = screen.getByLabelText('Телефон');
      fireEvent.change(phoneInput, { target: { value: '1234567890' } });
      fireEvent.blur(phoneInput);

      await waitFor(() => {
        expect(screen.getByText(/Формат: \+7XXXXXXXXXX/)).toBeInTheDocument();
      });
    });
  });

  describe('Отправка формы', () => {
    it('должен блокировать кнопку во время отправки', async () => {
      // Mock orderStore с isSubmitting = true для проверки disabled состояния
      const { useOrderStore } = await import('@/stores/orderStore');
      (useOrderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        createOrder: vi.fn(),
        isSubmitting: true,
        error: null,
        clearOrder: vi.fn(),
      });

      render(<CheckoutForm user={mockUser} />);

      // Проверяем, что кнопка disabled при isSubmitting = true
      const submitButton = screen.getByRole('button', {
        name: /оформление/i,
      });

      expect(submitButton).toBeDisabled();
    });
  });

  describe('OrderSummary интеграция', () => {
    it('должен отображать товары из корзины', () => {
      render(<CheckoutForm user={null} />);

      expect(screen.getByText('Test Product')).toBeInTheDocument();
      expect(screen.getByText('2 × 100 ₽')).toBeInTheDocument();
      // Цена отображается в нескольких местах (item total, cart total, итого)
      const prices = screen.getAllByText(/200\s*₽/);
      expect(prices.length).toBeGreaterThan(0);
    });

    it('должен показывать сообщение о пустой корзине', () => {
      (useCartStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        items: [],
        totalPrice: 0,
        totalItems: 0,
        fetchCart: vi.fn(),
        getPromoDiscount: vi.fn().mockReturnValue(0),
      });

      render(<CheckoutForm user={null} />);

      // Message may appear multiple times in different components
      expect(screen.getAllByText('Корзина пуста').length).toBeGreaterThan(0);
    });
  });

  describe('Discount UI (Story 34-2 regression)', () => {
    it('не показывает строку скидки при нулевом промокоде', () => {
      render(<CheckoutForm user={null} />);

      expect(screen.queryByTestId('promo-discount-row')).not.toBeInTheDocument();
    });

    it('показывает строку скидки при promoDiscount > 0', () => {
      (useCartStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        items: mockCartItems,
        totalPrice: 200,
        totalItems: 2,
        fetchCart: vi.fn(),
        getPromoDiscount: vi.fn().mockReturnValue(50),
      });

      render(<CheckoutForm user={null} />);

      expect(screen.getByTestId('promo-discount-row')).toBeInTheDocument();
      expect(screen.getByTestId('promo-discount-amount')).toHaveTextContent('50');
    });

    it('итого уменьшается на размер скидки', () => {
      (useCartStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        items: mockCartItems,
        totalPrice: 200,
        totalItems: 2,
        fetchCart: vi.fn(),
        getPromoDiscount: vi.fn().mockReturnValue(50),
      });

      render(<CheckoutForm user={null} />);

      // totalPrice - discount = 150
      expect(screen.getByTestId('total-price')).toHaveTextContent('150');
    });

    it('показывает метку "До скидки" при наличии скидки', () => {
      (useCartStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        items: mockCartItems,
        totalPrice: 200,
        totalItems: 2,
        fetchCart: vi.fn(),
        getPromoDiscount: vi.fn().mockReturnValue(50),
      });

      render(<CheckoutForm user={null} />);

      expect(screen.getByTestId('price-before-discount')).toBeInTheDocument();
      expect(screen.getByTestId('price-before-discount')).toHaveTextContent('200');
    });
  });
});
