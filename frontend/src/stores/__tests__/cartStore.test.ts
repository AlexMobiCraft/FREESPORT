/**
 * Cart Store Tests
 */
import { useCartStore } from '../cartStore';
import type { Product } from '@/types/api';

const mockProduct: Product = {
  id: 1,
  name: 'Test Product',
  slug: 'test-product',
  description: 'Test',
  retail_price: 100,
  is_in_stock: true,
  category: { id: 1, name: 'Test', slug: 'test' },
  images: [],
  // Story 11.0: Маркетинговые флаги
  is_hit: false,
  is_new: false,
  is_sale: false,
  is_promo: false,
  is_premium: false,
  discount_percent: null,
};

describe('cartStore', () => {
  beforeEach(() => {
    useCartStore.getState().clearCart();
  });

  test('addItem adds new product to cart', () => {
    const store = useCartStore.getState();

    store.addItem(mockProduct, 2);

    const state = useCartStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.items[0].quantity).toBe(2);
    expect(state.totalAmount).toBe(200);
  });

  test('addItem updates quantity for existing product', () => {
    const store = useCartStore.getState();

    store.addItem(mockProduct, 1);
    store.addItem(mockProduct, 2);

    const state = useCartStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.items[0].quantity).toBe(3);
  });

  test('removeItem removes product from cart', () => {
    const store = useCartStore.getState();

    store.addItem(mockProduct, 1);
    const itemId = useCartStore.getState().items[0].id;

    store.removeItem(itemId);

    const state = useCartStore.getState();
    expect(state.items).toHaveLength(0);
    expect(state.totalAmount).toBe(0);
  });

  test('updateQuantity updates product quantity', () => {
    const store = useCartStore.getState();

    store.addItem(mockProduct, 1);
    const itemId = useCartStore.getState().items[0].id;

    store.updateQuantity(itemId, 5);

    const state = useCartStore.getState();
    expect(state.items[0].quantity).toBe(5);
    expect(state.totalAmount).toBe(500);
  });

  test('clearCart removes all items', () => {
    const store = useCartStore.getState();

    store.addItem(mockProduct, 1);
    store.clearCart();

    const state = useCartStore.getState();
    expect(state.items).toHaveLength(0);
    expect(state.totalAmount).toBe(0);
  });
});
