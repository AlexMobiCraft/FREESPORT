/**
 * HomePage - Главная страница с полной интеграцией секций
 * Story 19.2 - Homepage Teasers Integration
 *
 * Порядок секций:
 * 1. HeroSection (баннеры)
 * 2. CategoriesSection (категории)
 * 3. WhyFreesportSection ← НОВЫЙ (после категорий)
 * 4. HitsSection (хиты продаж)
 * 5. NewArrivalsSection (новинки)
 * 6. PromoSection / SaleSection (акции/распродажа)
 * 7. DeliveryTeaser ← НОВЫЙ (перед Footer)
 * 8. AboutTeaser ← НОВЫЙ (перед Footer)
 * 9. Footer
 */

'use client';

import React from 'react';
import {
  HeroSection,
  CategoriesSection,
  WhyFreesportSection,
  HitsSection,
  NewArrivalsSection,
  SaleSection,
  DeliveryTeaser,
  AboutTeaser,
} from '@/components/home';

export const HomePage: React.FC = () => {
  return (
    <main className="min-h-screen bg-white">
      {/* 1. Hero Section - Баннеры */}
      <HeroSection />

      {/* 2. Categories Section */}
      <CategoriesSection />

      {/* 3. Why FREESPORT Section - Новый тизер (Story 19.2) */}
      <WhyFreesportSection />

      {/* 4. Hits Section - Хиты продаж */}
      <HitsSection />

      {/* 5. New Arrivals Section - Новинки */}
      <NewArrivalsSection />

      {/* 6. Sale Section - Распродажа */}
      <SaleSection />

      {/* 7. Delivery Teaser - Новый тизер (Story 19.2) */}
      <DeliveryTeaser />

      {/* 8. About Teaser - Новый тизер (Story 19.2) */}
      <AboutTeaser />

      {/* Footer рендерится в layout */}
    </main>
  );
};

export default HomePage;
