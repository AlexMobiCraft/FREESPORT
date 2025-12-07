/**
 * CartPage Component
 *
 * Главный компонент страницы корзины:
 * - Интеграция с cartStore для данных корзины
 * - Hydration-safe паттерн для Zustand persist + SSR
 * - Loading/Error/Empty states
 * - Responsive двухколоночный layout
 */

'use client';

import { useEffect, useState } from 'react';
import { useCartStore } from '@/stores/cartStore';
import { Breadcrumb } from '@/components/ui';
import { EmptyCart } from './EmptyCart';
import { CartSkeleton } from './CartSkeleton';
import { CartError } from './CartError';
import type { CartItem } from '@/types/cart';

const breadcrumbItems = [{ label: 'Главная', href: '/' }, { label: 'Корзина' }];

/**
 * Временный placeholder для CartItemCard (будет реализован в Story 26.2)
 */
const CartItemCard = ({ item }: { item: CartItem }) => (
  <div
    className="bg-white rounded-[var(--radius-md)] p-6 shadow-[var(--shadow-default)]"
    data-testid={`cart-item-${item.id}`}
  >
    <div className="flex gap-4">
      <div className="w-20 h-20 bg-neutral-100 rounded-[var(--radius-sm)] flex items-center justify-center">
        {item.product.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.product.image}
            alt={item.product.name}
            className="w-full h-full object-cover rounded-[var(--radius-sm)]"
          />
        ) : (
          <span className="text-neutral-400 text-body-s">Нет фото</span>
        )}
      </div>
      <div className="flex-1">
        <h3 className="text-title-s font-medium text-text-primary">{item.product.name}</h3>
        {(item.variant.color_name || item.variant.size_value) && (
          <p className="text-body-s text-text-secondary mt-1">
            {item.variant.color_name}
            {item.variant.color_name && item.variant.size_value && ' / '}
            {item.variant.size_value}
          </p>
        )}
        <p className="text-body-s text-text-secondary">Артикул: {item.variant.sku}</p>
      </div>
      <div className="text-right">
        <p className="text-title-s font-semibold text-text-primary">
          {parseFloat(item.total_price).toLocaleString('ru-RU')} ₽
        </p>
        <p className="text-body-s text-text-secondary">
          {item.quantity} шт. × {parseFloat(item.unit_price).toLocaleString('ru-RU')} ₽
        </p>
      </div>
    </div>
  </div>
);

/**
 * Временный placeholder для CartSummary (будет реализован в Story 26.3)
 */
const CartSummary = ({ totalPrice, totalItems }: { totalPrice: number; totalItems: number }) => (
  <aside
    className="bg-white rounded-[var(--radius-md)] p-6 shadow-[var(--shadow-default)] lg:sticky lg:top-6"
    aria-live="polite"
    data-testid="cart-summary"
  >
    <h2 className="text-title-m font-semibold text-text-primary mb-4">Итого</h2>
    <div className="space-y-3">
      <div className="flex justify-between text-body-m">
        <span className="text-text-secondary">Товаров:</span>
        <span className="text-text-primary font-medium">{totalItems} шт.</span>
      </div>
      <div className="flex justify-between text-body-m">
        <span className="text-text-secondary">Сумма:</span>
        <span className="text-text-primary font-medium">
          {totalPrice.toLocaleString('ru-RU')} ₽
        </span>
      </div>
      <hr className="border-neutral-200" />
      <div className="flex justify-between text-title-s">
        <span className="font-semibold text-text-primary">К оплате:</span>
        <span className="font-bold text-primary">{totalPrice.toLocaleString('ru-RU')} ₽</span>
      </div>
    </div>
    <button
      className="w-full mt-6 h-12 bg-primary hover:bg-primary-hover text-text-inverse font-medium rounded-[var(--radius-sm)] transition-colors"
      data-testid="checkout-button"
    >
      Оформить заказ
    </button>
  </aside>
);

export const CartPage = () => {
  const [mounted, setMounted] = useState(false);
  const { items, isLoading, error, fetchCart, totalPrice, totalItems } = useCartStore();

  // Hydration: ждём монтирования на клиенте
  useEffect(() => {
    setMounted(true);
  }, []);

  // Загружаем корзину при монтировании (если items пустые)
  useEffect(() => {
    if (mounted && items.length === 0) {
      fetchCart();
    }
  }, [mounted, items.length, fetchCart]);

  // SSR: показываем skeleton до hydration
  if (!mounted) {
    return <CartSkeleton />;
  }

  // Loading state (только при первой загрузке, когда items пустые)
  if (isLoading && items.length === 0) {
    return <CartSkeleton />;
  }

  // Error state
  if (error) {
    return <CartError error={error} onRetry={fetchCart} />;
  }

  // Empty state
  if (items.length === 0) {
    return <EmptyCart />;
  }

  // Main content
  return (
    <main className="max-w-[1280px] mx-auto px-4 lg:px-6 py-6" data-testid="cart-page" role="main">
      <Breadcrumb items={breadcrumbItems} className="mb-6" data-testid="cart-breadcrumb" />

      <h1 className="text-display-m font-bold text-text-primary mb-8">Ваша корзина</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Список товаров - 2 колонки на desktop */}
        <section
          className="lg:col-span-2 space-y-4"
          aria-label="Товары в корзине"
          data-testid="cart-items-list"
        >
          {items.map(item => (
            <CartItemCard key={item.id} item={item} />
          ))}
        </section>

        {/* Итоги - 1 колонка, sticky на desktop */}
        <div className="lg:col-span-1">
          <CartSummary totalPrice={totalPrice} totalItems={totalItems} />
        </div>
      </div>
    </main>
  );
};

CartPage.displayName = 'CartPage';
