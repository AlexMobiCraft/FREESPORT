/**
 * HomePage - Главная страница
 *
 * Порядок секций:
 * 1. HeroSection (баннеры)
 * 1.5. QuickLinksSection (быстрые ссылки)
 * 2. CategoriesSection (популярные категории)
 * 3. HitsSection (хиты продаж)
 * 4. NewArrivalsSection (новинки)
 * 5. PromoSection (акция)
 * 6. SaleSection (распродажа)
 * 7. NewsSection (новости)
 * 8. BlogSection (блог)
 * 9. SubscribeNewsSection (подписка)
 * 10. WhyFreesportSection (почему выбирают)
 * 11. DeliveryTeaser (доставка)
 * 12. AboutTeaser (FREESPORT + ценности)
 */

'use client';

import React from 'react';
import {
  HeroSection,
  QuickLinksSection,
  MarketingBannersSection,
  HitsSection,
  NewArrivalsSection,
  PromoSection,
  SaleSection,
  NewsSection,
  BlogSection,
  SubscribeNewsSection,
  WhyFreesportSection,
  DeliveryTeaser,
  AboutTeaser,
  CategoriesSection,
} from '@/components/home';

export const HomePage: React.FC = () => {
  return (
    <main className="min-h-screen bg-white">
      {/* 1. Hero Section - Баннеры */}
      <HeroSection />

      {/* 1.5 Quick Links - Быстрые ссылки */}
      <QuickLinksSection />

      {/* 1.6 Marketing Banners - Маркетинговые баннеры */}
      <MarketingBannersSection />

      {/* 2. Popular Categories - Популярные категории */}
      <CategoriesSection />

      {/* 2. Hits Section - Хиты продаж */}
      <HitsSection />

      {/* 3. New Arrivals Section - Новинки */}
      <NewArrivalsSection />

      {/* 4. Promo Section - Акция */}
      <PromoSection />

      {/* 5. Sale Section - Распродажа */}
      <SaleSection />

      {/* 6. News Section - Новости */}
      <NewsSection />

      {/* 7. Blog Section - Наш блог */}
      <BlogSection />

      {/* 8. Subscribe Section - Подписка на новости */}
      <SubscribeNewsSection />

      {/* 9. Why FREESPORT Section */}
      <WhyFreesportSection />

      {/* 10. Delivery Teaser - Доставка по России */}
      <DeliveryTeaser />

      {/* 11. About Teaser - FREESPORT + Наши ценности */}
      <AboutTeaser />

      {/* Footer рендерится в layout */}
    </main>
  );
};

export default HomePage;
