/**
 * Утилиты для работы с ценообразованием (Story 12.1)
 */

import type { ProductDetail, ProductPrice, ProductVariant } from '@/types/api';

export type UserRole =
  | 'retail'
  | 'wholesale_level1'
  | 'wholesale_level2'
  | 'wholesale_level3'
  | 'wholesale_level4'
  | 'trainer'
  | 'federation_rep'
  | 'admin'
  // Контрагент 1С без портального аккаунта: цены розничные (ветка default)
  | 'unregistered'
  | 'guest';

/**
 * Видит ли роль B2B-информацию (РРЦ, МРЦ, оптовые условия).
 *
 * Не «всё, кроме retail»: гость, а также контрагент 1С без портального
 * аккаунта (`unregistered`) к B2B-ценам доступа не имеют.
 */
export function isB2BRole(role: UserRole | undefined): boolean {
  return (
    role === 'wholesale_level1' ||
    role === 'wholesale_level2' ||
    role === 'wholesale_level3' ||
    role === 'wholesale_level4' ||
    role === 'trainer' ||
    role === 'federation_rep'
  );
}

/**
 * Получает цену для конкретной роли пользователя
 * @param price - Объект цен товара
 * @param userRole - Роль пользователя
 * @returns Цена для данной роли (fallback на retail)
 */
export function getPriceForRole(price: ProductPrice, userRole: UserRole): number {
  switch (userRole) {
    case 'retail':
      return price.retail;
    case 'wholesale_level1':
      return price.wholesale?.level1 || price.retail;
    case 'wholesale_level2':
      return price.wholesale?.level2 || price.retail;
    case 'wholesale_level3':
      return price.wholesale?.level3 || price.retail;
    case 'wholesale_level4':
      return price.wholesale?.level4 || price.retail;
    case 'trainer':
      return price.trainer || price.retail;
    case 'federation_rep':
      return price.federation || price.retail;
    case 'admin':
      return price.retail;
    case 'guest':
    default:
      return price.retail;
  }
}

/**
 * Цена товара, которую видит покупатель на странице товара.
 *
 * Один источник для экрана (`ProductInfo`) и разметки JSON-LD (`ProductPageClient`):
 * поисковикам уходит та же сумма, что на экране, в том числе до выбора варианта.
 * Акция действует для всех ролей; без варианта и без акции — цена по роли.
 *
 * @param product - Товар из ответа API
 * @param userRole - Роль пользователя
 * @param variant - Выбранный вариант (null, пока вариант не выбран)
 */
export function getProductDisplayPrice(
  product: Pick<ProductDetail, 'price' | 'current_price' | 'promo_price'>,
  userRole: UserRole,
  variant?: Pick<ProductVariant, 'current_price' | 'promo_price'> | null
): number {
  if (variant && variant.current_price) return parseFloat(variant.current_price);

  // Поля акции — выбранного варианта, без него — товара (они по первому варианту из ответа)
  const pricingSource = variant ?? product;
  const promoPrice = pricingSource.promo_price ? parseFloat(pricingSource.promo_price) : NaN;
  if (promoPrice > 0) return parseFloat(product.current_price || '') || promoPrice;

  return getPriceForRole(product.price || { retail: 0, currency: 'RUB' }, userRole);
}

/**
 * Форматирует цену в рублях с валютой
 * @param price - Цена в числовом формате
 * @param currency - Код валюты (по умолчанию RUB)
 * @returns Отформатированная строка цены
 */
export function formatPrice(price: number, currency: string = 'RUB'): string {
  const formatter = new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  return formatter.format(price);
}

/**
 * Форматирует цену, сохраняя копейки, если они есть
 *
 * Для пары «акционная и зачёркнутая цены»: после округления до рубля 800,49 и 800,40
 * выглядели бы одинаково, хотя проверка «зачёркнутая выше акционной» их различает.
 * Целые суммы остаются без копеек, как у `formatPrice`.
 */
export function formatExactPrice(price: number, currency: string = 'RUB'): string {
  const formatter = new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: Number.isInteger(price) ? 0 : 2,
    maximumFractionDigits: 2,
  });
  return formatter.format(price);
}
