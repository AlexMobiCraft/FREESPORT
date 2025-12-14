/**
 * CheckoutForm Integration Tests
 * Story 15.2: Интеграция с Orders API
 *
 * Тест-кейсы:
 * - Успешная отправка формы создаёт заказ и перенаправляет на success
 * - Кнопка отправки disabled во время isSubmitting
 * - Ошибка отображается в InfoPanel при сбое
 * - Предупреждение о пустой корзине
 */

import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CheckoutForm } from '../CheckoutForm';
import { useOrderStore } from '@/stores/orderStore';
import { useCartStore } from '@/stores/cartStore';
import { server } from '@/__mocks__/server';
import { ordersErrorHandlers } from '@/__mocks__/handlers/ordersHandlers';
import type { CartItem } from '@/types/cart';

// Mock next/navigation с использованием vi.mock (Vitest)
const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
};

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
}));

/**
 * Mock данные корзины
 */
const mockCartItems: CartItem[] = [
  {
    id: 1,
    variant_id: 123,
    product: {
      id: 1,
      name: 'Футбольный мяч Nike',
      slug: 'football-nike',
      image: '/images/ball.jpg',
    },
    variant: {
      sku: 'NIKE-001',
      color_name: 'Белый',
      size_value: '5',
    },
    quantity: 2,
    unit_price: '2500.00',
    total_price: '5000.00',
    added_at: '2025-12-14T10:00:00Z',
  },
];

/**
 * Mock пользователь
 */
const mockUser = {
  id: 1,
  email: 'test@example.com',
  first_name: 'Иван',
  last_name: 'Петров',
  phone: '+79001234567',
  role: 'retail' as const,
};

describe('CheckoutForm Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Reset stores
    useOrderStore.setState({
      currentOrder: null,
      isSubmitting: false,
      error: null,
    });

    useCartStore.setState({
      items: mockCartItems,
      totalItems: 2,
      totalPrice: 5000,
      isLoading: false,
      error: null,
      promoCode: null,
      discountType: null,
      discountValue: 0,
    });
  });

  describe('Отображение', () => {
    test('отображает форму с секциями', () => {
      render(<CheckoutForm user={null} />);

      // Проверяем наличие основных секций
      expect(screen.getByText('Контактные данные')).toBeInTheDocument();
      expect(screen.getByText('Адрес доставки')).toBeInTheDocument();
      expect(screen.getByText('Способ доставки')).toBeInTheDocument();
      expect(screen.getByText('Комментарий к заказу')).toBeInTheDocument();
      expect(screen.getByText('Ваш заказ')).toBeInTheDocument();
    });

    test('автозаполняет данные для авторизованного пользователя', () => {
      render(<CheckoutForm user={mockUser} />);

      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument();
      expect(screen.getByDisplayValue('+79001234567')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Иван')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Петров')).toBeInTheDocument();
    });

    test('показывает предупреждение при пустой корзине', () => {
      useCartStore.setState({ items: [], totalItems: 0, totalPrice: 0 });

      render(<CheckoutForm user={null} />);

      expect(screen.getByText('Корзина пуста')).toBeInTheDocument();
      expect(
        screen.getByText('Добавьте товары в корзину для оформления заказа')
      ).toBeInTheDocument();
    });

    test('кнопка "Оформить заказ" disabled при пустой корзине', () => {
      useCartStore.setState({ items: [], totalItems: 0, totalPrice: 0 });

      render(<CheckoutForm user={null} />);

      const submitButton = screen.getByRole('button', { name: /оформить заказ/i });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Состояние загрузки', () => {
    test('кнопка показывает "Оформление..." во время isSubmitting', () => {
      useOrderStore.setState({ isSubmitting: true });

      render(<CheckoutForm user={null} />);

      expect(screen.getByRole('button', { name: /оформление/i })).toBeInTheDocument();
    });

    test('кнопка disabled во время isSubmitting', () => {
      useOrderStore.setState({ isSubmitting: true });

      render(<CheckoutForm user={null} />);

      const submitButton = screen.getByRole('button', { name: /оформление/i });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Отображение ошибок', () => {
    test('показывает ошибку API в InfoPanel', () => {
      useOrderStore.setState({ error: 'Недостаточно товара на складе' });

      render(<CheckoutForm user={null} />);

      expect(screen.getByText('Ошибка оформления заказа')).toBeInTheDocument();
      expect(screen.getByText('Недостаточно товара на складе')).toBeInTheDocument();
    });

    test('показывает ошибку валидации формы', async () => {
      render(<CheckoutForm user={null} />);

      // Пытаемся отправить пустую форму
      const submitButton = screen.getByRole('button', { name: /оформить заказ/i });
      fireEvent.click(submitButton);

      // Ждём появления ошибок валидации
      await waitFor(() => {
        expect(screen.getByText('Ошибки в форме')).toBeInTheDocument();
      });
    });
  });

  describe('Отправка формы', () => {
    test('заполненная форма отправляется успешно', async () => {
      const user = userEvent.setup();
      render(<CheckoutForm user={null} />);

      // Заполняем форму
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/телефон/i), '+79001234567');
      await user.type(screen.getByLabelText(/имя/i), 'Иван');
      await user.type(screen.getByLabelText(/фамилия/i), 'Петров');
      await user.type(screen.getByLabelText(/город/i), 'Москва');
      await user.type(screen.getByLabelText(/улица/i), 'Ленина');
      await user.type(screen.getByLabelText(/дом/i), '10');
      await user.type(screen.getByLabelText(/индекс/i), '123456');

      // Выбираем способ доставки (если есть select)
      const deliveryInput = screen.getByLabelText(/способ доставки/i);
      if (deliveryInput.tagName === 'SELECT') {
        await user.selectOptions(deliveryInput, 'courier');
      } else {
        await user.type(deliveryInput, 'courier');
      }

      // Отправляем форму
      const submitButton = screen.getByRole('button', { name: /оформить заказ/i });
      await user.click(submitButton);

      // Проверяем что router.push был вызван с correct URL
      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith(
          expect.stringMatching(/\/checkout\/success\//)
        );
      });
    });

    test('отображает ошибку при неуспешном создании заказа', async () => {
      server.use(ordersErrorHandlers.validation400);

      const user = userEvent.setup();
      render(<CheckoutForm user={mockUser} />);

      // Заполняем минимальные поля
      await user.type(screen.getByLabelText(/город/i), 'Москва');
      await user.type(screen.getByLabelText(/улица/i), 'Ленина');
      await user.type(screen.getByLabelText(/дом/i), '10');
      await user.type(screen.getByLabelText(/индекс/i), '123456');

      const deliveryInput = screen.getByLabelText(/способ доставки/i);
      await user.type(deliveryInput, 'courier');

      // Отправляем
      const submitButton = screen.getByRole('button', { name: /оформить заказ/i });
      await user.click(submitButton);

      // Ждём появления ошибки
      await waitFor(() => {
        const errorState = useOrderStore.getState().error;
        expect(errorState).toBeTruthy();
      });
    });
  });

  describe('Интеграция с корзиной', () => {
    test('отображает товары из корзины в OrderSummary', () => {
      render(<CheckoutForm user={null} />);

      expect(screen.getByText('Футбольный мяч Nike')).toBeInTheDocument();
      expect(screen.getByText(/5\s*000/)).toBeInTheDocument(); // totalPrice
    });

    test('отображает информацию о варианте товара', () => {
      render(<CheckoutForm user={null} />);

      // Проверяем что отображается цвет/размер
      expect(screen.getByText(/Белый/)).toBeInTheDocument();
    });
  });
});
