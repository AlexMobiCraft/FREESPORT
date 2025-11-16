/**
 * Cart Service - методы для работы с корзиной
 */

import apiClient from './api-client';
import type { Cart, CartItem } from '@/types/api';

class CartService {
  /**
   * Получить текущую корзину
   */
  async get(): Promise<Cart> {
    const response = await apiClient.get<Cart>('/cart/');
    return response.data;
  }

  /**
   * Добавить товар в корзину
   */
  async add(productId: number, quantity: number): Promise<CartItem> {
    const response = await apiClient.post<CartItem>('/cart/items/', {
      product_id: productId,
      quantity,
    });
    return response.data;
  }

  /**
   * Обновить количество товара в корзине
   */
  async update(itemId: number, quantity: number): Promise<CartItem> {
    const response = await apiClient.patch<CartItem>(`/cart/items/${itemId}/`, {
      quantity,
    });
    return response.data;
  }

  /**
   * Удалить товар из корзины
   */
  async remove(itemId: number): Promise<void> {
    await apiClient.delete(`/cart/items/${itemId}/`);
  }

  /**
   * Применить промокод
   */
  async applyPromo(code: string): Promise<Cart> {
    const response = await apiClient.post<Cart>('/cart/apply-promo/', { code });
    return response.data;
  }
}

const cartService = new CartService();
export default cartService;
