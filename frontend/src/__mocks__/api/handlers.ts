/**
 * MSW API Handlers для Story 11.2
 * Mock handlers для тестирования динамических блоков контента
 */

import { http, HttpResponse } from 'msw';
import type { Product, Category, NewsItem } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

/**
 * Mock данные для хитов продаж (AC 1)
 */
const mockHitsProducts: Product[] = [
  {
    id: 1,
    name: 'Футбольный мяч Nike Strike',
    slug: 'nike-strike-ball',
    description: 'Профессиональный футбольный мяч',
    retail_price: 2500,
    is_in_stock: true,
    category: { id: 1, name: 'Футбол', slug: 'football' },
    images: [{ id: 1, image: '/images/nike-strike.jpg', is_primary: true }],
    // Story 11.0: Маркетинговые флаги
    is_hit: true,
    is_new: false,
    is_sale: true, // Приоритет 1: показываем sale бейдж
    is_promo: false,
    is_premium: false,
    discount_percent: 20,
  },
  {
    id: 2,
    name: 'Кроссовки Adidas Ultraboost',
    slug: 'adidas-ultraboost',
    description: 'Беговые кроссовки премиум класса',
    retail_price: 15000,
    is_in_stock: true,
    category: { id: 2, name: 'Бег', slug: 'running' },
    images: [{ id: 2, image: '/images/ultraboost.jpg', is_primary: true }],
    // Story 11.0: Только hit флаг
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 3,
    name: 'Ракетка Wilson Pro Staff',
    slug: 'wilson-pro-staff',
    description: 'Профессиональная теннисная ракетка',
    retail_price: 18000,
    is_in_stock: true,
    category: { id: 3, name: 'Теннис', slug: 'tennis' },
    images: [{ id: 3, image: '/images/wilson-racket.jpg', is_primary: true }],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: true, // Приоритет 2
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 4,
    name: 'Велосипед Trek Marlin 7',
    slug: 'trek-marlin-7',
    description: 'Горный велосипед для профессионалов',
    retail_price: 65000,
    is_in_stock: true,
    category: { id: 4, name: 'Велоспорт', slug: 'cycling' },
    images: [{ id: 4, image: '/images/trek-marlin.jpg', is_primary: true }],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: true, // Приоритет 5
    discount_percent: null,
  },
  {
    id: 5,
    name: 'Перчатки вратарские Uhlsport',
    slug: 'uhlsport-gloves',
    description: 'Профессиональные вратарские перчатки',
    retail_price: 4500,
    is_in_stock: true,
    category: { id: 1, name: 'Футбол', slug: 'football' },
    images: [],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 6,
    name: 'Куртка Columbia OutDry',
    slug: 'columbia-outdry',
    description: 'Водонепроницаемая куртка для активного отдыха',
    retail_price: 12000,
    is_in_stock: true,
    category: { id: 5, name: 'Outdoor', slug: 'outdoor' },
    images: [{ id: 6, image: '/images/columbia-jacket.jpg', is_primary: true }],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 7,
    name: 'Мяч баскетбольный Spalding NBA',
    slug: 'spalding-nba',
    description: 'Официальный мяч NBA',
    retail_price: 5500,
    is_in_stock: true,
    category: { id: 6, name: 'Баскетбол', slug: 'basketball' },
    images: [{ id: 7, image: '/images/spalding-nba.jpg', is_primary: true }],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 8,
    name: 'Коньки хоккейные Bauer Vapor',
    slug: 'bauer-vapor',
    description: 'Профессиональные хоккейные коньки',
    retail_price: 22000,
    is_in_stock: true,
    category: { id: 7, name: 'Хоккей', slug: 'hockey' },
    images: [{ id: 8, image: '/images/bauer-vapor.jpg', is_primary: true }],
    is_hit: true,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
];

/**
 * Mock данные для новинок (AC 2)
 */
const mockNewProducts: Product[] = [
  {
    id: 10,
    name: 'Новая модель ракетки Wilson Blade',
    slug: 'wilson-blade-new',
    description: 'Новинка 2025 года',
    retail_price: 19000,
    is_in_stock: true,
    category: { id: 3, name: 'Теннис', slug: 'tennis' },
    images: [{ id: 10, image: '/images/wilson-blade.jpg', is_primary: true }],
    // Story 11.0: Новинка с акцией
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: true, // Приоритет 2 (выше чем new)
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 11,
    name: 'Новые кроссовки Nike Air Zoom',
    slug: 'nike-air-zoom-new',
    description: 'Последняя модель беговых кроссовок',
    retail_price: 13500,
    is_in_stock: true,
    category: { id: 2, name: 'Бег', slug: 'running' },
    images: [{ id: 11, image: '/images/nike-air-zoom.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 12,
    name: 'Тренажер домашний NordicTrack',
    slug: 'nordictrack-home',
    description: 'Инновационный домашний тренажер',
    retail_price: 85000,
    is_in_stock: true,
    category: { id: 8, name: 'Фитнес', slug: 'fitness' },
    images: [{ id: 12, image: '/images/nordictrack.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: true,
    discount_percent: null,
  },
  {
    id: 13,
    name: 'Скейтборд Element Complete',
    slug: 'element-complete',
    description: 'Профессиональный скейтборд',
    retail_price: 7500,
    is_in_stock: true,
    category: { id: 9, name: 'Экстрим', slug: 'extreme' },
    images: [{ id: 13, image: '/images/element-skateboard.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 14,
    name: 'Гантели регулируемые Bowflex',
    slug: 'bowflex-dumbbells',
    description: 'Регулируемые гантели для дома',
    retail_price: 35000,
    is_in_stock: true,
    category: { id: 8, name: 'Фитнес', slug: 'fitness' },
    images: [],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 15,
    name: 'Лыжи горные Rossignol Experience',
    slug: 'rossignol-experience',
    description: 'Горные лыжи нового поколения',
    retail_price: 42000,
    is_in_stock: true,
    category: { id: 10, name: 'Зимние виды спорта', slug: 'winter' },
    images: [{ id: 15, image: '/images/rossignol.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 16,
    name: 'Сноуборд Burton Custom',
    slug: 'burton-custom',
    description: 'Профессиональный сноуборд',
    retail_price: 38000,
    is_in_stock: true,
    category: { id: 10, name: 'Зимние виды спорта', slug: 'winter' },
    images: [{ id: 16, image: '/images/burton-custom.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 17,
    name: 'Палатка туристическая MSR Hubba',
    slug: 'msr-hubba',
    description: 'Легкая туристическая палатка',
    retail_price: 28000,
    is_in_stock: true,
    category: { id: 5, name: 'Outdoor', slug: 'outdoor' },
    images: [{ id: 17, image: '/images/msr-hubba.jpg', is_primary: true }],
    is_hit: false,
    is_new: true,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
];

/**
 * Mock данные для новостей (Story 11.3)
 */
const mockNews: NewsItem[] = [
  {
    id: 1,
    title: 'Новая коллекция 2025',
    slug: 'new-collection-2025',
    excerpt: 'Представляем новую коллекцию спортивной одежды и экипировки на 2025 год.',
    image: '/images/news/collection-2025.jpg',
    published_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    title: 'Скидки на зимнюю экипировку',
    slug: 'winter-sale',
    excerpt: 'До конца месяца скидки до 30% на зимнюю экипировку для всех видов спорта.',
    image: '/images/news/winter-sale.jpg',
    published_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    title: 'Открытие нового склада',
    slug: 'new-warehouse',
    excerpt: 'Мы рады сообщить об открытии нового склада в Москве для более быстрой доставки.',
    image: '/images/news/warehouse.jpg',
    published_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

/**
 * Mock данные для категорий (AC 3)
 */
const mockCategories: Category[] = [
  {
    id: 1,
    name: 'Футбол',
    slug: 'football',
    parent_id: null,
    level: 1,
    icon: '⚽',
    products_count: 150,
    description: 'Товары для футбола',
  },
  {
    id: 2,
    name: 'Бег',
    slug: 'running',
    parent_id: null,
    level: 1,
    icon: '🏃',
    products_count: 230,
    description: 'Беговая экипировка',
  },
  {
    id: 3,
    name: 'Теннис',
    slug: 'tennis',
    parent_id: null,
    level: 1,
    icon: '🎾',
    products_count: 95,
    description: 'Теннисное оборудование',
  },
  {
    id: 4,
    name: 'Велоспорт',
    slug: 'cycling',
    parent_id: null,
    level: 1,
    icon: '🚴',
    products_count: 180,
    description: 'Велосипеды и аксессуары',
  },
  {
    id: 5,
    name: 'Outdoor',
    slug: 'outdoor',
    parent_id: null,
    level: 1,
    icon: '🏔️',
    products_count: 320,
    description: 'Товары для активного отдыха',
  },
  {
    id: 6,
    name: 'Баскетбол',
    slug: 'basketball',
    parent_id: null,
    level: 1,
    icon: '🏀',
    products_count: 85,
    description: 'Баскетбольное оборудование',
  },
];

/**
 * MSW Handlers
 */
export const handlers = [
  // Хиты продаж (AC 1)
  http.get(`${API_BASE_URL}/products/`, ({ request }) => {
    const url = new URL(request.url);
    const isHit = url.searchParams.get('is_hit');
    const isNew = url.searchParams.get('is_new');

    // Запрос хитов продаж
    if (isHit === 'true') {
      return HttpResponse.json({
        count: mockHitsProducts.length,
        next: null,
        previous: null,
        results: mockHitsProducts,
      });
    }

    // Запрос новинок (AC 2)
    if (isNew === 'true') {
      return HttpResponse.json({
        count: mockNewProducts.length,
        next: null,
        previous: null,
        results: mockNewProducts,
      });
    }

    // Default: пустой ответ
    return HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  }),

  // Категории - корневые категории (AC 3)
  http.get(`${API_BASE_URL}/categories/`, ({ request }) => {
    const url = new URL(request.url);
    const parentIdNull = url.searchParams.get('parent_id__isnull');

    // Только корневые категории
    if (parentIdNull === 'true') {
      return HttpResponse.json(mockCategories);
    }

    // Default: все категории
    return HttpResponse.json(mockCategories);
  }),

  // Story 11.3: Subscribe endpoint
  http.post(`${API_BASE_URL}/subscribe`, async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    const email = body.email;

    // Simulate already subscribed
    if (email === 'existing@example.com') {
      return HttpResponse.json(
        {
          error: 'This email is already subscribed',
          email,
        },
        { status: 409 }
      );
    }

    // Simulate validation error
    if (!email || !email.includes('@')) {
      return HttpResponse.json(
        {
          error: 'Invalid email format',
          field: 'email',
        },
        { status: 400 }
      );
    }

    // Success
    return HttpResponse.json(
      {
        message: 'Successfully subscribed',
        email,
      },
      { status: 201 }
    );
  }),

  // Story 11.3: News endpoint
  http.get(`${API_BASE_URL}/news`, () => {
    return HttpResponse.json({
      count: mockNews.length,
      next: null,
      previous: null,
      results: mockNews,
    });
  }),
];

/**
 * Error handlers для тестирования error states
 */
export const errorHandlers = [
  // 500 Server Error для хитов
  http.get(`${API_BASE_URL}/products/`, ({ request }) => {
    const url = new URL(request.url);
    const isHit = url.searchParams.get('is_hit');

    if (isHit === 'true') {
      return HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }

    return HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  }),

  // 500 Server Error для категорий
  http.get(`${API_BASE_URL}/categories/`, () => {
    return HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
  }),
];

/**
 * Empty data handlers для тестирования graceful degradation
 */
export const emptyHandlers = [
  // Пустой ответ для хитов
  http.get(`${API_BASE_URL}/products/`, () => {
    return HttpResponse.json({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });
  }),

  // Пустой ответ для категорий
  http.get(`${API_BASE_URL}/categories/`, () => {
    return HttpResponse.json([]);
  }),
];
