/**
 * NewArrivalsSection Component
 *
 * Блок "Новинки" на главной странице (Story 12.7).
 * Отображает товары с флагом is_new=true в горизонтальной ленте.
 *
 * Features:
 * - Горизонтальная лента с scroll-snap
 * - Использует ProductCard из Story 12.4
 * - Кнопки навигации prev/next
 * - Бейдж "NEW" на карточках
 *
 * @example
 * ```tsx
 * <NewArrivalsSection />
 * ```
 */

'use client';

import React, { useRef } from 'react';
import { ProductCard } from '@/components/business/ProductCard/ProductCard';
import { MOCK_NEW_PRODUCTS } from '@/__mocks__/products';
import { ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * Компонент блока "Новинки"
 */
export const NewArrivalsSection: React.FC = () => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const scrollAmount = container.clientWidth * 0.8;
    const targetScroll =
      container.scrollLeft + (direction === 'right' ? scrollAmount : -scrollAmount);

    container.scrollTo({
      left: targetScroll,
      behavior: 'smooth',
    });
  };

  if (!MOCK_NEW_PRODUCTS || MOCK_NEW_PRODUCTS.length === 0) {
    return null;
  }

  return (
    <section
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 relative"
      aria-labelledby="new-arrivals-heading"
    >
      {/* Заголовок секции - headline-l */}
      <h2 id="new-arrivals-heading" className="text-3xl font-bold mb-8 text-primary">
        Новинки
      </h2>

      {/* Кнопки навигации */}
      <button
        onClick={() => scroll('left')}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 hidden lg:flex items-center justify-center w-10 h-10 bg-white rounded-full shadow-default hover:shadow-hover transition-shadow focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="Предыдущие товары"
      >
        <ChevronLeft className="w-6 h-6 text-primary" />
      </button>

      <button
        onClick={() => scroll('right')}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 hidden lg:flex items-center justify-center w-10 h-10 bg-white rounded-full shadow-default hover:shadow-hover transition-shadow focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="Следующие товары"
      >
        <ChevronRight className="w-6 h-6 text-primary" />
      </button>

      {/* Горизонтальная лента товаров */}
      <div
        ref={scrollContainerRef}
        className="flex gap-4 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-4"
        role="list"
      >
        {MOCK_NEW_PRODUCTS.map(product => (
          <div key={product.id} className="flex-shrink-0 w-[280px] snap-start" role="listitem">
            <ProductCard product={product} layout="compact" userRole="retail" />
          </div>
        ))}
      </div>

      <style jsx>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </section>
  );
};

NewArrivalsSection.displayName = 'NewArrivalsSection';
