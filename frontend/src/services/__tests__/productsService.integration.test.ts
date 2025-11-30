/**
 * Integration тесты для productsService (Story 12.1)
 * Тестирование API интеграции с MSW моками
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '@/__mocks__/api/handlers';
import productsService from '../productsService';
import { MOCK_PRODUCT_DETAIL } from '@/__mocks__/productDetail';

// Setup MSW server
const server = setupServer(...handlers);

describe('productsService Integration Tests', () => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('getProductBySlug', () => {
    it('получает детальную информацию о товаре по slug', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product).toEqual(MOCK_PRODUCT_DETAIL);
      expect(product.id).toBe(101);
      expect(product.name).toBe('ASICS Gel-Blast FF');
      expect(product.slug).toBe('asics-gel-blast-ff');
      expect(product.sku).toBe('AS-GB-FF-2025');
    });

    it('возвращает все поля ProductDetail', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      // Проверяем наличие всех обязательных полей
      expect(product).toHaveProperty('id');
      expect(product).toHaveProperty('slug');
      expect(product).toHaveProperty('name');
      expect(product).toHaveProperty('sku');
      expect(product).toHaveProperty('brand');
      expect(product).toHaveProperty('description');
      expect(product).toHaveProperty('price');
      expect(product).toHaveProperty('stock_quantity');
      expect(product).toHaveProperty('images');
      expect(product).toHaveProperty('category');
      expect(product).toHaveProperty('is_in_stock');
      expect(product).toHaveProperty('can_be_ordered');
    });

    it('возвращает корректную структуру цен', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product.price).toHaveProperty('retail');
      expect(product.price).toHaveProperty('wholesale');
      expect(product.price).toHaveProperty('trainer');
      expect(product.price).toHaveProperty('federation');
      expect(product.price).toHaveProperty('currency');

      expect(product.price.retail).toBe(12990);
      expect(product.price.wholesale?.level1).toBe(11890);
      expect(product.price.wholesale?.level2).toBe(11290);
      expect(product.price.wholesale?.level3).toBe(10790);
      expect(product.price.trainer).toBe(10990);
      expect(product.price.federation).toBe(9990);
      expect(product.price.currency).toBe('RUB');
    });

    it('возвращает корректную структуру категории с breadcrumbs', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product.category).toHaveProperty('id');
      expect(product.category).toHaveProperty('name');
      expect(product.category).toHaveProperty('slug');
      expect(product.category).toHaveProperty('breadcrumbs');

      expect(product.category.breadcrumbs).toEqual(['Главная', 'Обувь', 'Зал', 'ASICS']);
    });

    it('возвращает изображения товара', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product.images).toHaveLength(3);
      expect(product.images[0]).toHaveProperty('id');
      expect(product.images[0]).toHaveProperty('image');
      expect(product.images[0]).toHaveProperty('is_primary');
      expect(product.images[0].is_primary).toBe(true);
    });

    it('возвращает рейтинг и отзывы', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product.rating).toBe(4.7);
      expect(product.reviews_count).toBe(38);
    });

    it('возвращает спецификации товара', async () => {
      const product = await productsService.getProductBySlug('asics-gel-blast-ff');

      expect(product.specifications).toBeDefined();
      expect(product.specifications?.['Материал']).toBe('Полиамид + сетка');
      expect(product.specifications?.['Вес']).toBe('310 г');
    });

    it('обрабатывает товар "Под заказ"', async () => {
      const product = await productsService.getProductBySlug('out-of-stock-product');

      expect(product.stock_quantity).toBe(0);
      expect(product.is_in_stock).toBe(false);
      expect(product.can_be_ordered).toBe(true);
    });

    it('обрабатывает недоступный товар', async () => {
      const product = await productsService.getProductBySlug('unavailable-product');

      expect(product.stock_quantity).toBe(0);
      expect(product.is_in_stock).toBe(false);
      expect(product.can_be_ordered).toBe(false);
    });

    it('выбрасывает ошибку для несуществующего товара', async () => {
      await expect(productsService.getProductBySlug('non-existent-slug')).rejects.toThrow();
    });
  });
});
