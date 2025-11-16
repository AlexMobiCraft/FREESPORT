/**
 * Orders Service Tests
 */
import ordersService from '../ordersService';
import { server } from '../../../__mocks__/server';
import { http, HttpResponse } from 'msw';

describe('ordersService', () => {
  describe('create', () => {
    test('creates order successfully', async () => {
      server.use(
        http.post('http://localhost:8001/api/v1/orders/', async ({ request }) => {
          const body = (await request.json()) as {
            delivery_address: string;
            payment_method: string;
          };
          return HttpResponse.json(
            {
              id: 1,
              order_number: 'ORD-001',
              status: 'pending',
              items: [],
              total_amount: 2500,
              delivery_address: body.delivery_address,
              payment_method: body.payment_method,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            { status: 201 }
          );
        })
      );

      const result = await ordersService.create({
        delivery_address: 'Test Address',
        payment_method: 'card',
      });

      expect(result.id).toBe(1);
      expect(result.order_number).toBe('ORD-001');
      expect(result.status).toBe('pending');
    });

    test('handles validation error', async () => {
      server.use(
        http.post('http://localhost:8001/api/v1/orders/', () => {
          return HttpResponse.json({ detail: 'Delivery address is required' }, { status: 400 });
        })
      );

      await expect(
        ordersService.create({
          delivery_address: '',
          payment_method: 'card',
        })
      ).rejects.toThrow();
    });
  });

  describe('getAll', () => {
    test('fetches orders list successfully', async () => {
      server.use(
        http.get('http://localhost:8001/api/v1/orders/', () => {
          return HttpResponse.json({
            count: 10,
            next: null,
            previous: null,
            results: [
              {
                id: 1,
                order_number: 'ORD-001',
                status: 'delivered',
                items: [],
                total_amount: 2500,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
          });
        })
      );

      const result = await ordersService.getAll();

      expect(result.count).toBe(10);
      expect(result.results).toHaveLength(1);
      expect(result.results[0].order_number).toBe('ORD-001');
    });

    test('fetches orders with pagination', async () => {
      const result = await ordersService.getAll({ page: 1, limit: 20 });

      expect(result.results).toBeDefined();
    });
  });

  describe('getById', () => {
    test('fetches single order successfully', async () => {
      server.use(
        http.get('http://localhost:8001/api/v1/orders/:id/', ({ params }) => {
          return HttpResponse.json({
            id: Number(params.id),
            order_number: 'ORD-001',
            status: 'delivered',
            items: [],
            total_amount: 2500,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        })
      );

      const result = await ordersService.getById(1);

      expect(result.id).toBe(1);
      expect(result.order_number).toBe('ORD-001');
    });

    test('handles 404 error', async () => {
      server.use(
        http.get('http://localhost:8001/api/v1/orders/:id/', () => {
          return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
        })
      );

      await expect(ordersService.getById(999)).rejects.toThrow();
    });
  });
});
