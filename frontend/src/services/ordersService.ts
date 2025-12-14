/**
 * Orders Service - методы для работы с заказами
 * Story 15.2: Интеграция с Orders API
 *
 * Features:
 * - Создание заказа с маппингом CheckoutFormData -> CreateOrderPayload
 * - Обработка ошибок (400, 401, 500)
 * - Retry логика встроена в apiClient (exponential backoff)
 */

import apiClient from './api-client';
import type { CheckoutFormData } from '@/schemas/checkoutSchema';
import type { CartItem } from '@/types/cart';
import type {
  Order,
  CreateOrderPayload,
  CreateOrderResponse,
  OrderValidationError,
} from '@/types/order';
import type { PaginatedResponse } from '@/types/api';
import { AxiosError } from 'axios';

/**
 * Фильтры для списка заказов
 */
interface OrderFilters {
  page?: number;
  limit?: number;
}

/**
 * Маппинг CheckoutFormData -> CreateOrderPayload
 * Преобразует данные формы в формат API
 */
function mapFormDataToPayload(
  formData: CheckoutFormData,
  cartItems: CartItem[]
): CreateOrderPayload {
  return {
    email: formData.email,
    phone: formData.phone,
    first_name: formData.firstName,
    last_name: formData.lastName,
    delivery_address: {
      city: formData.city,
      street: formData.street,
      house: formData.house,
      apartment: formData.apartment || undefined,
      postal_code: formData.postalCode,
    },
    delivery_method_id: formData.deliveryMethod,
    items: cartItems.map(item => ({
      variant_id: item.variant_id,
      quantity: item.quantity,
    })),
    comment: formData.comment || undefined,
  };
}

/**
 * Парсинг ошибки API в читаемое сообщение
 */
function parseApiError(
  error: AxiosError<OrderValidationError | { error?: string; message?: string }>
): string {
  const status = error.response?.status;
  const data = error.response?.data;

  // 400 Bad Request - валидационные ошибки
  if (status === 400) {
    const validationError = data as OrderValidationError;
    // Пытаемся получить конкретное сообщение об ошибке
    if (validationError.details?.items?.[0]) {
      return validationError.details.items[0];
    }
    if (validationError.error) {
      return validationError.error;
    }
    return 'Ошибка валидации данных заказа';
  }

  // 401 Unauthorized - сессия истекла
  if (status === 401) {
    return 'Сессия истекла. Войдите заново.';
  }

  // 500+ Server errors
  if (status && status >= 500) {
    return 'Ошибка сервера. Попробуйте позже.';
  }

  // Network errors
  if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') {
    return 'Ошибка сети. Проверьте подключение к интернету.';
  }

  // Fallback
  return 'Ошибка создания заказа. Попробуйте снова.';
}

class OrdersService {
  /**
   * Создать новый заказ
   *
   * @param formData - данные формы checkout
   * @param cartItems - товары из корзины
   * @returns Order - созданный заказ
   * @throws Error - с локализованным сообщением об ошибке
   */
  async createOrder(formData: CheckoutFormData, cartItems: CartItem[]): Promise<Order> {
    // Проверка на пустую корзину
    if (!cartItems || cartItems.length === 0) {
      throw new Error('Корзина пуста, невозможно оформить заказ');
    }

    const payload = mapFormDataToPayload(formData, cartItems);

    try {
      const response = await apiClient.post<CreateOrderResponse>('/orders/', payload);

      // Маппинг ответа в Order
      return {
        id: response.data.id,
        order_number: response.data.order_number,
        status: response.data.status,
        total_amount: response.data.total_amount,
        created_at: response.data.created_at,
        delivery_method: response.data.delivery_method,
        items: response.data.items,
      };
    } catch (error) {
      const axiosError = error as AxiosError<OrderValidationError>;
      const message = parseApiError(axiosError);
      throw new Error(message);
    }
  }

  /**
   * Получить список заказов с пагинацией
   */
  async getAll(filters?: OrderFilters): Promise<PaginatedResponse<Order>> {
    const response = await apiClient.get<PaginatedResponse<Order>>('/orders/', {
      params: filters,
    });
    return response.data;
  }

  /**
   * Получить заказ по ID
   * Используется для страницы success (Story 15.4)
   */
  async getById(orderId: string): Promise<Order> {
    const response = await apiClient.get<Order>(`/orders/${orderId}/`);
    return response.data;
  }
}

const ordersService = new OrdersService();
export default ordersService;

// Export для тестирования
export { mapFormDataToPayload, parseApiError };
