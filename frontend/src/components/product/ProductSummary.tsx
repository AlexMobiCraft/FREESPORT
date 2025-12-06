/**
 * ProductSummary Component (Story 12.3, 13.5a, 13.5b)
 * Компонент-обёртка для ProductInfo и ProductOptions
 * Управляет состоянием выбранного варианта товара и добавлением в корзину
 *
 * @see docs/stories/epic-12/12.3.add-to-cart.md
 * @see docs/stories/epic-13/13.5a.productoptions-ui-msw-mock.md
 * @see docs/stories/epic-13/13.5b.productoptions-api-integration.md
 */

'use client';

import React, { useState, useCallback, useMemo } from 'react';
import type { ProductDetail } from '@/types/api';
import type { UserRole } from '@/utils/pricing';
import { useCartStore } from '@/stores/cartStore';
import { useToast } from '@/components/ui/Toast';
import ProductInfo from './ProductInfo';
import { ProductOptions, type ProductVariant, type SelectedOptions } from './ProductOptions';

/**
 * Расширенный интерфейс товара с вариантами
 */
export interface ProductDetailWithVariants extends ProductDetail {
  variants?: ProductVariant[];
}

/**
 * Результат валидации опций
 */
export interface ValidationResult {
  valid: boolean;
  message?: string;
}

/**
 * Валидирует выбранные опции товара
 * @param selectedOptions - текущие выбранные опции
 * @param variants - доступные варианты товара
 * @returns результат валидации с сообщением об ошибке
 */
export function validateOptions(
  selectedOptions: SelectedOptions,
  variants: ProductVariant[]
): ValidationResult {
  // Извлечь уникальные опции
  const sizes = [...new Set(variants.map(v => v.size_value).filter(Boolean))];
  const colors = [...new Set(variants.map(v => v.color_name).filter(Boolean))];

  // Проверить обязательные опции
  if (sizes.length > 0 && !selectedOptions.size) {
    return {
      valid: false,
      message: 'Пожалуйста, выберите размер',
    };
  }

  if (colors.length > 0 && !selectedOptions.color) {
    return {
      valid: false,
      message: 'Пожалуйста, выберите цвет',
    };
  }

  return { valid: true };
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
  /** Callback при изменении выбранного варианта (для интеграции с ProductGallery) */
  onVariantChange?: (variant: ProductVariant | null) => void;
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
  onVariantChange,
}: ProductSummaryProps) {
  // Состояние выбранных опций
  const [selectedOptions, setSelectedOptions] = useState<SelectedOptions>({});
  // Состояние ошибки валидации
  const [validationError, setValidationError] = useState<string>('');
  // Состояние количества
  const [quantity, setQuantity] = useState<number>(1);

  // Hooks для работы с корзиной и уведомлениями
  const { addItem, isLoading } = useCartStore();
  const { success, error: toastError } = useToast();

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
   * Уведомляет родительский компонент об изменении варианта
   */
  const handleSelectionChange = useCallback(
    (newOptions: SelectedOptions) => {
      setSelectedOptions(newOptions);
      setValidationError(''); // Сбрасываем ошибку при изменении выбора

      // Найти новый вариант и уведомить родителя
      if (onVariantChange && variants.length > 0) {
        const newVariant =
          variants.find(v => {
            const sizeMatch = !newOptions.size || v.size_value === newOptions.size;
            const colorMatch = !newOptions.color || v.color_name === newOptions.color;
            return sizeMatch && colorMatch;
          }) || null;
        onVariantChange(newVariant);
      }
    },
    [onVariantChange, variants]
  );

  /**
   * Обработчик добавления в корзину с валидацией
   */
  const handleAddToCart = useCallback(async () => {
    // Валидация перед добавлением в корзину
    if (variants.length > 0) {
      const validation = validateOptions(selectedOptions, variants);
      if (!validation.valid) {
        setValidationError(validation.message || 'Пожалуйста, выберите все опции товара');
        toastError(validation.message || 'Пожалуйста, выберите все опции товара');
        return;
      }

      if (!selectedVariant) {
        const msg = 'Пожалуйста, выберите все опции товара';
        setValidationError(msg);
        toastError(msg);
        return;
      }

      if (!selectedVariant.is_in_stock) {
        const msg = 'Выбранный вариант недоступен';
        setValidationError(msg);
        toastError(msg);
        return;
      }
    }

    setValidationError('');

    // Добавляем в корзину через cartStore
    const variantId = selectedVariant?.id;
    if (!variantId) {
      toastError('Не удалось определить вариант товара');
      return;
    }

    const result = await addItem(variantId, quantity);

    if (result.success) {
      success('Товар добавлен в корзину');
      // Сбрасываем количество после успешного добавления
      setQuantity(1);

      // Вызываем внешний callback если он есть
      if (onAddToCart) {
        onAddToCart(variantId);
      }
    } else {
      toastError(result.error || 'Ошибка при добавлении в корзину');
    }
  }, [
    addItem,
    quantity,
    selectedVariant,
    selectedOptions,
    variants,
    onAddToCart,
    success,
    toastError,
  ]);

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

      {/* Сообщение об ошибке валидации */}
      {validationError && (
        <div
          className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm"
          data-testid="validation-error"
          role="alert"
        >
          {validationError}
        </div>
      )}

      {/* Кнопка добавления в корзину */}
      <button
        type="button"
        onClick={handleAddToCart}
        disabled={!canAddToCart || (variants.length > 0 && !selectedVariant) || isLoading}
        className={`
          w-full px-6 py-3 font-medium rounded-lg transition-colors
          focus:outline-none focus:ring-2 focus:ring-offset-2
          flex items-center justify-center gap-2
          ${
            canAddToCart && (variants.length === 0 || selectedVariant) && !isLoading
              ? 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500'
              : 'bg-neutral-300 text-neutral-500 cursor-not-allowed'
          }
        `}
        data-testid="add-to-cart-button"
      >
        {isLoading && (
          <svg
            className="animate-spin h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        )}
        {isLoading ? 'Добавление...' : addToCartButtonText}
      </button>
    </div>
  );
}
