/**
 * MSW Handlers для Orders API
 * Story 15.2: Интеграция с Orders API
 */

import { http, HttpResponse } from 'msw';

// Используем wildcard для матчинга любых URL
// MSW 2.x поддерживает wildcard patterns

/**
 * Mock данные успешного заказа
 */
export const mockSuccessOrder = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  order_number: 'ORD-2025-001',
  status: 'new' as const,
  total_amount: 5000.0,
  created_at: '2025-12-14T12:00:00Z',
  delivery_method: {
    id: 'courier',
    name: 'Курьер',
    description: 'Доставка курьером до двери',
  },
  items: [
    {
      variant_id: 123,
      product_id: 1,
      product_name: 'Футбольный мяч Nike',
      quantity: 2,
      price: 2500,
      total: 5000,
    },
  ],
};

/**
 * Orders API Handlers
 */
export const ordersHandlers = [
  // POST /orders/ - Создание заказа
  http.post('*/orders/', async ({ request }) => {
    const body = (await request.json()) as {
      email: string;
      phone: string;
      first_name: string;
      last_name: string;
      delivery_address: {
        city: string;
        street: string;
        house: string;
        apartment?: string;
        postal_code: string;
      };
      delivery_method_id: string;
      items: Array<{ variant_id: number; quantity: number }>;
      comment?: string;
    };

    // Проверка на пустые items
    if (!body.items || body.items.length === 0) {
      return HttpResponse.json(
        {
          error: 'Validation failed',
          details: {
            items: ['Корзина пуста'],
          },
        },
        { status: 400 }
      );
    }

    // Проверка на "недоступный" товар (для тестов)
    const unavailableItem = body.items.find(item => item.variant_id === 999);
    if (unavailableItem) {
      return HttpResponse.json(
        {
          error: 'Validation failed',
          details: {
            items: ['Товар с ID 999 закончился на складе'],
          },
        },
        { status: 400 }
      );
    }

    // Успешный ответ
    return HttpResponse.json(mockSuccessOrder, { status: 201 });
  }),

  // GET /orders/ - Список заказов
  http.get('*/orders/', () => {
    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [mockSuccessOrder],
    });
  }),

  // GET /orders/:id/ - Получить заказ по ID
  http.get('*/orders/:id/', ({ params }) => {
    const { id } = params;

    // 404 для несуществующего заказа
    if (id === 'not-found' || id === '00000000-0000-0000-0000-000000000000') {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
    }

    return HttpResponse.json({
      ...mockSuccessOrder,
      id: id as string,
    });
  }),
];

/**
 * Handlers для тестирования ошибок
 */
export const ordersErrorHandlers = {
  // 400 Bad Request - валидационная ошибка
  validation400: http.post('*/orders/', () => {
    return HttpResponse.json(
      {
        error: 'Validation failed',
        details: {
          items: ['Недостаточно товара на складе'],
        },
      },
      { status: 400 }
    );
  }),

  // 401 Unauthorized
  unauthorized401: http.post('*/orders/', () => {
    return HttpResponse.json(
      {
        error: 'Unauthorized',
        message: 'Token expired',
      },
      { status: 401 }
    );
  }),

  // 500 Server Error
  serverError500: http.post('*/orders/', () => {
    return HttpResponse.json(
      {
        error: 'Internal server error',
        message: 'Failed to create order',
      },
      { status: 500 }
    );
  }),

  // Network error
  networkError: http.post('*/orders/', () => {
    return HttpResponse.error();
  }),
};
