/**
 * Главная страница FREESPORT Platform
 * Hero секция и основная информация
 *
 * Features:
 * - SSG (Static Site Generation) с ISR revalidation
 * - SEO оптимизация с метатегами и OG tags
 * - Динамический Hero баннер на основе роли пользователя
 */
import type { Metadata } from 'next';
import Link from 'next/link';
import HeroSection from '@/components/home/HeroSection';
import { HitsSection, NewArrivalsSection, CategoriesSection } from '@/components/home';
import { SubscribeNewsSection } from '@/components/home/SubscribeNewsSection';
import { Button } from '@/components/ui/Button/Button';

// ISR конфигурация: ревалидация каждый час
export const revalidate = 3600;

// SEO Metadata
export const metadata: Metadata = {
  title: 'FREESPORT - Оптовые поставки спортивных товаров | B2B и Розница',
  description:
    'Оптовые поставки спортивных товаров для B2B и розничных покупателей. 5 брендов, дифференцированное ценообразование, интеграция с 1С. 1000+ товаров в каталоге.',
  keywords: [
    'спортивные товары оптом',
    'B2B спортивная одежда',
    'оптовые поставки спорттоваров',
    'FREESPORT',
    'спортивная экипировка',
    'товары для спорта',
  ],
  openGraph: {
    title: 'FREESPORT - Оптовые поставки спортивных товаров',
    description: 'B2B и B2C продажи спортивных товаров. 5 брендов. 1000+ товаров.',
    url: 'https://freesport.ru',
    siteName: 'FREESPORT',
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'FREESPORT - Платформа спортивных товаров',
      },
    ],
    locale: 'ru_RU',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FREESPORT - Оптовые поставки спортивных товаров',
    description: 'B2B и B2C продажи спортивных товаров. 5 брендов. 1000+ товаров.',
    images: ['/og-image.jpg'],
  },
};

export default function Home() {
  return (
    <div className="bg-white">
      {/* Hero секция с ролевыми баннерами */}
      <HeroSection />

      {/* Story 11.2: Динамические блоки контента */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Хиты продаж */}
        <HitsSection />

        {/* Новинки */}
        <NewArrivalsSection />

        {/* Популярные категории */}
        <CategoriesSection />
      </div>

      {/* Story 11.3: Подписка и новости */}
      <SubscribeNewsSection />

      {/* Преимущества */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Преимущества платформы</h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Современные решения для розничных и оптовых покупателей
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Быстрое оформление</h3>
              <p className="text-gray-600">Современный интерфейс и простой процесс заказа</p>
            </div>

            <div className="text-center">
              <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Проверенное качество</h3>
              <p className="text-gray-600">
                Только сертифицированные товары от надежных поставщиков
              </p>
            </div>

            <div className="text-center">
              <div className="bg-orange-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-orange-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Выгодные цены</h3>
              <p className="text-gray-600">
                Специальные условия для оптовых покупателей и тренеров
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Для бизнеса */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-gray-900 to-gray-700 rounded-2xl p-8 md:p-12 text-white">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-3xl font-bold mb-4">Решения для бизнеса</h2>
                <p className="text-gray-300 text-lg mb-6">
                  Специальные условия для тренеров, спортивных федераций и дистрибьюторов.
                  Многоуровневая система скидок и персональный менеджер.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link href="/wholesale">
                    <Button variant="primary" size="lg">
                      Узнать условия
                    </Button>
                  </Link>
                  <Link href="/contacts">
                    <Button
                      variant="outline"
                      size="lg"
                      className="border-white text-white hover:bg-white hover:text-gray-900"
                    >
                      Связаться с нами
                    </Button>
                  </Link>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-blue-400 mb-1">1000+</div>
                  <div className="text-sm text-gray-300">Товаров в каталоге</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400 mb-1">500+</div>
                  <div className="text-sm text-gray-300">B2B партнеров</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-orange-400 mb-1">24/7</div>
                  <div className="text-sm text-gray-300">Поддержка</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-purple-400 mb-1">5</div>
                  <div className="text-sm text-gray-300">Торговых марок</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
