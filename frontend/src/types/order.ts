/**
 * TypeScript типы для заказов
 * Story 15.2: Интеграция с Orders API
 */

/**
 * Статус заказа
 */
export type OrderStatus = 'new' | 'paid' | 'shipped' | 'delivered' | 'cancelled';

/**
 * Способ доставки
 */
export interface DeliveryMethod {
  id: string;
  name: string;
  description?: string;
}

/**
 * Адрес доставки
 */
export interface DeliveryAddress {
  city: string;
  street: string;
  house: string;
  apartment?: string;
  postal_code: string;
}

/**
 * Элемент заказа
 */
export interface OrderItem {
  variant_id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  price: number;
  total: number;
}

/**
 * Полный заказ (ответ API)
 */
export interface Order {
  id: string;
  order_number: string;
  status: OrderStatus;
  total_amount: number;
  created_at: string;
  delivery_address?: DeliveryAddress;
  delivery_method?: DeliveryMethod;
  items?: OrderItem[];
}

/**
 * Ответ при создании заказа
 */
export interface CreateOrderResponse {
  id: string;
  order_number: string;
  status: OrderStatus;
  total_amount: number;
  created_at: string;
  delivery_method?: DeliveryMethod;
  items?: OrderItem[];
}

/**
 * Payload для создания заказа
 * Маппится из CheckoutFormData + CartItem[]
 */
export interface CreateOrderPayload {
  // Контактные данные
  email: string;
  phone: string;
  first_name: string;
  last_name: string;

  // Адрес доставки
  delivery_address: {
    city: string;
    street: string;
    house: string;
    apartment?: string;
    postal_code: string;
  };

  // Способ доставки
  delivery_method_id: string;

  // Товары из корзины (используем variant_id из cartStore)
  items: Array<{
    variant_id: number;
    quantity: number;
  }>;

  // Комментарий
  comment?: string;
}

/**
 * Ошибка валидации от API
 */
export interface OrderValidationError {
  error: string;
  details?: {
    items?: string[];
    [key: string]: string[] | undefined;
  };
}

/**
 * Ошибка аутентификации от API
 */
export interface OrderAuthError {
  error: string;
  message: string;
}
