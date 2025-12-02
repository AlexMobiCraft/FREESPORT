/**
 * ProductSummary Component (Story 13.5a)
 * Компонент-обёртка для ProductInfo и ProductOptions
 * Управляет состоянием выбранного варианта товара
 *
 * @see docs/stories/epic-13/13.5a.productoptions-ui-msw-mock.md
 */

'use client';

import React, { useState, useCallback, useMemo } from 'react';
import type { ProductDetail } from '@/types/api';
import type { UserRole } from '@/utils/pricing';
import ProductInfo from './ProductInfo';
import { ProductOptions, type ProductVariant, type SelectedOptions } from './ProductOptions';

/**
 * Расширенный интерфейс товара с вариантами
 */
export interface ProductDetailWithVariants extends ProductDetail {
  variants?: ProductVariant[];
}

/**
 * Props компонента ProductSummary
 */
interface ProductSummaryProps {
  /** Данные товара (с опциональными вариантами) */
  product: ProductDetailWithVariants;
  /** Роль пользователя для отображения цены */
  userRole?: UserRole;
  /** Callback при добавлении в корзину */
  onAddToCart?: (variantId?: number) => void;
}

/**
 * ProductSummary - компонент сводки товара с выбором вариантов
 *
 * Объединяет ProductInfo и ProductOptions, управляя состоянием
 * выбранного варианта и обновляя отображаемую цену.
 */
export default function ProductSummary({
  product,
  userRole = 'guest',
  onAddToCart,
}: ProductSummaryProps) {
  // Состояние выбранных опций
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});

  // Варианты товара (если есть) - мемоизируем для стабильности ссылки
  const variants = useMemo(() => product.variants || [], [product.variants]);

  /**
   * Находит вариант по выбранным опциям
   */
  const selectedVariant = useMemo((): ProductVariant | null => {
    if (variants.length === 0) return null;

    // Если ничего не выбрано, возвращаем null
    if (!selectedOptions.size && !selectedOptions.color) return null;

    // Ищем вариант, соответствующий выбранным опциям
    return (
      variants.find(v => {
        const sizeMatch = !selectedOptions.size || v.size_value === selectedOptions.size;
        const colorMatch = !selectedOptions.color || v.color_name === selectedOptions.color;
        return sizeMatch && colorMatch;
      }) || null
    );
  }, [variants, selectedOptions]);

  /**
   * Обработчик изменения выбора опций
   */
  const handleSelectionChange = useCallback((newOptions: SelectedOptions) => {
    setSelectedOptions(newOptions);
  }, []);

  /**
   * Обработчик добавления в корзину
   */
  const handleAddToCart = useCallback(() => {
    if (onAddToCart) {
      onAddToCart(selectedVariant?.id);
    }
  }, [onAddToCart, selectedVariant]);

  /**
   * Проверяет, можно ли добавить товар в корзину
   */
  const canAddToCart = useMemo(() => {
    // Если нет вариантов - проверяем базовый товар
    if (variants.length === 0) {
      return product.is_in_stock || product.can_be_ordered;
    }

    // Если есть варианты - нужно выбрать доступный вариант
    if (!selectedVariant) return false;

    return selectedVariant.is_in_stock;
  }, [variants, product, selectedVariant]);

  /**
   * Текст кнопки добавления в корзину
   */
  const addToCartButtonText = useMemo(() => {
    if (variants.length > 0 && !selectedVariant) {
      return 'Выберите вариант';
    }

    if (!canAddToCart) {
      return 'Нет в наличии';
    }

    return 'Добавить в корзину';
  }, [variants, selectedVariant, canAddToCart]);

  return (
    <div className="space-y-6" data-testid="product-summary">
      {/* Основная информация о товаре */}
      <ProductInfo product={product} userRole={userRole} />

      {/* Выбор вариантов (если есть) */}
      {variants.length > 0 && (
        <div className="pt-4 border-t border-neutral-200">
          <ProductOptions
            variants={variants}
            selectedOptions={selectedOptions}
            onSelectionChange={handleSelectionChange}
          />
        </div>
      )}

      {/* Информация о выбранном варианте */}
      {selectedVariant && (
        <div className="p-3 bg-neutral-50 rounded-lg" data-testid="selected-variant-info">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-600">Артикул варианта:</span>
            <span className="font-medium text-neutral-900">{selectedVariant.sku}</span>
          </div>
          {selectedVariant.current_price && (
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-neutral-600">Цена:</span>
              <span className="font-bold text-neutral-900">
                {parseFloat(selectedVariant.current_price).toLocaleString('ru-RU')} ₽
              </span>
            </div>
          )}
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-neutral-600">В наличии:</span>
            <span
              className={`font-medium ${selectedVariant.is_in_stock ? 'text-green-600' : 'text-red-600'}`}
            >
              {selectedVariant.is_in_stock
                ? `${selectedVariant.available_quantity} шт.`
                : 'Нет в наличии'}
            </span>
          </div>
        </div>
      )}

      {/* Кнопка добавления в корзину */}
      <button
        type="button"
        onClick={handleAddToCart}
        disabled={!canAddToCart || (variants.length > 0 && !selectedVariant)}
        className={`
          w-full px-6 py-3 font-medium rounded-lg transition-colors
          focus:outline-none focus:ring-2 focus:ring-offset-2
          ${
            canAddToCart && (variants.length === 0 || selectedVariant)
              ? 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500'
              : 'bg-neutral-300 text-neutral-500 cursor-not-allowed'
          }
        `}
        data-testid="add-to-cart-button"
      >
        {addToCartButtonText}
      </button>
    </div>
  );
}
