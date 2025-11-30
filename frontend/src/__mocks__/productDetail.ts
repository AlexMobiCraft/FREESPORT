/**
 * Mock данные для детальной страницы товара (Story 12.1)
 */

import type { ProductDetail } from '@/types/api';

export const MOCK_PRODUCT_DETAIL: ProductDetail = {
  id: 101,
  slug: 'asics-gel-blast-ff',
  name: 'ASICS Gel-Blast FF',
  sku: 'AS-GB-FF-2025',
  brand: 'ASICS',
  description: 'Профессиональные кроссовки для интенсивных тренировок',
  full_description:
    'ASICS Gel-Blast FF - это кроссовки нового поколения для игры в зале. Технология FlyteFoam обеспечивает превосходную амортизацию при минимальном весе. Гелевая прокладка в пятке гарантирует комфорт при приземлении.',
  price: {
    retail: 12990,
    wholesale: {
      level1: 11890,
      level2: 11290,
      level3: 10790,
    },
    trainer: 10990,
    federation: 9990,
    currency: 'RUB',
  },
  stock_quantity: 34,
  images: [
    {
      id: 1,
      image: 'https://cdn.freesport.ru/products/asics-gel-blast-ff/main.jpg',
      alt_text: 'ASICS Gel-Blast FF front',
      is_primary: true,
    },
    {
      id: 2,
      image: 'https://cdn.freesport.ru/products/asics-gel-blast-ff/side.jpg',
      alt_text: 'ASICS Gel-Blast FF side',
      is_primary: false,
    },
    {
      id: 3,
      image: 'https://cdn.freesport.ru/products/asics-gel-blast-ff/back.jpg',
      alt_text: 'ASICS Gel-Blast FF back',
      is_primary: false,
    },
  ],
  rating: 4.7,
  reviews_count: 38,
  specifications: {
    Материал: 'Полиамид + сетка',
    Вес: '310 г',
    Цвета: 'black, lime',
    Размеры: '36-46',
    'Страна производства': 'Вьетнам',
    Назначение: 'Зальный гандбол, волейбол',
    Технологии: 'FlyteFoam, Gel, Trusstic System',
  },
  category: {
    id: 1,
    name: 'Обувь',
    slug: 'obuv',
    breadcrumbs: ['Главная', 'Обувь', 'Зал', 'ASICS'],
  },
  is_in_stock: true,
  can_be_ordered: true,
};

export const MOCK_OUT_OF_STOCK_PRODUCT: ProductDetail = {
  ...MOCK_PRODUCT_DETAIL,
  id: 102,
  slug: 'out-of-stock-product',
  stock_quantity: 0,
  is_in_stock: false,
  can_be_ordered: true,
};

export const MOCK_UNAVAILABLE_PRODUCT: ProductDetail = {
  ...MOCK_PRODUCT_DETAIL,
  id: 103,
  slug: 'unavailable-product',
  stock_quantity: 0,
  is_in_stock: false,
  can_be_ordered: false,
};
