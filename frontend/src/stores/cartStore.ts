/**
 * Cart Store - управление корзиной покупок
 *
 * Локальное состояние корзины для быстрого UI
 * Синхронизируется с backend через cartService
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { CartItem, Product } from '@/types/api';

interface CartState {
  items: CartItem[];
  totalAmount: number;

  // Actions
  addItem: (product: Product, quantity: number) => void;
  removeItem: (itemId: number) => void;
  updateQuantity: (itemId: number, quantity: number) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  devtools(
    (set, get) => ({
      items: [],
      totalAmount: 0,

      addItem: (product: Product, quantity: number) => {
        const existingItem = get().items.find(item => item.product.id === product.id);

        if (existingItem) {
          // Обновить количество существующего товара
          set(state => ({
            items: state.items.map(item =>
              item.product.id === product.id
                ? { ...item, quantity: item.quantity + quantity }
                : item
            ),
          }));
        } else {
          // Добавить новый товар
          set(state => ({
            items: [
              ...state.items,
              {
                id: Date.now(), // Временный ID до синхронизации с backend
                product: {
                  id: product.id,
                  name: product.name,
                  slug: product.slug,
                  retail_price: product.retail_price,
                  opt1_price: product.opt1_price,
                  is_in_stock: product.is_in_stock,
                },
                quantity,
                price: product.retail_price,
              },
            ],
          }));
        }

        // Пересчитать total
        const newTotal = get().items.reduce((sum, item) => sum + item.price * item.quantity, 0);
        set({ totalAmount: newTotal });
      },

      removeItem: (itemId: number) => {
        set(state => ({
          items: state.items.filter(item => item.id !== itemId),
        }));

        // Пересчитать total
        const newTotal = get().items.reduce((sum, item) => sum + item.price * item.quantity, 0);
        set({ totalAmount: newTotal });
      },

      updateQuantity: (itemId: number, quantity: number) => {
        set(state => ({
          items: state.items.map(item => (item.id === itemId ? { ...item, quantity } : item)),
        }));

        // Пересчитать total
        const newTotal = get().items.reduce((sum, item) => sum + item.price * item.quantity, 0);
        set({ totalAmount: newTotal });
      },

      clearCart: () => {
        set({ items: [], totalAmount: 0 });
      },
    }),
    { name: 'CartStore' }
  )
);
