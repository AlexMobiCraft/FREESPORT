/**
 * Главная страница FREESPORT Platform (Story 12.7 - Design System v2.0)
 */

import type { Metadata } from 'next';
import HeroSection from '@/components/home/HeroSection';
import { HitsSection, NewArrivalsSection, CategoriesSection } from '@/components/home';
import { NewsSection } from '@/components/home/NewsSection';
import { SubscribeNewsSection } from '@/components/home/SubscribeNewsSection';

// ISR конфигурация: ревалидация каждый час
export const revalidate = 3600;

// SEO Metadata (Story 12.7 - AC 10)
export const metadata: Metadata = {
  title: 'FREESPORT - Спортивные товары оптом и в розницу',
  description:
    'Крупнейший интернет-магазин спортивной одежды и экипировки в России. Более 10 000 товаров от ведущих брендов. Выгодные цены для B2B клиентов.',
  keywords: [
    'спортивные товары',
    'спортивная одежда',
    'оптом',
    'FREESPORT',
    'B2B спорттовары',
    'экипировка',
  ],
  openGraph: {
    title: 'FREESPORT - Спортивные товары оптом и в розницу',
    description: 'Крупнейший интернет-магазин спортивной одежды и экипировки в России.',
    url: 'https://freesport.ru',
    siteName: 'FREESPORT',
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'FREESPORT',
      },
    ],
    locale: 'ru_RU',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FREESPORT - Спортивные товары',
    description: 'Более 10 000 товаров от ведущих брендов',
    images: ['/og-image.jpg'],
  },
};

export default function HomePage() {
  return (
    <main className="bg-[#F5F7FB]">
      {/* Hero секция */}
      <HeroSection />

      {/* Section spacing: 64px (py-16) для первой секции после hero */}
      <section className="py-16" aria-label="Хиты продаж">
        <HitsSection />
      </section>

      {/* Section spacing: 48px (py-12) для остальных секций */}
      <section className="py-12" aria-label="Новинки">
        <NewArrivalsSection />
      </section>

      <section className="py-12" aria-label="Категории товаров">
        <CategoriesSection />
      </section>

      <section className="py-12" aria-label="Новости">
        <NewsSection />
      </section>

      <section className="py-12" aria-label="Подписка на новости">
        <SubscribeNewsSection />
      </section>
    </main>
  );
}
