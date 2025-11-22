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

import React, { useEffect, useRef, useState } from 'react';
import { ProductCard } from '@/components/business/ProductCard/ProductCard';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import productsService from '@/services/productsService';
import type { Product } from '@/types/api';

/**
 * Компонент блока "Новинки"
 */
export const NewArrivalsSection: React.FC = () => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNewArrivals = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await productsService.getNew();
      setProducts(data);
    } catch (err) {
      console.error(err);
      setError('Не удалось загрузить новинки');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchNewArrivals();
  }, []);

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

  if (!isLoading && !error && products.length === 0) {
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

      {/* Состояние загрузки */}
      {isLoading && (
        <div
          role="status"
          aria-label="Загрузка новинок"
          className="flex gap-2 overflow-hidden pb-3"
        >
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="flex-shrink-0 w-[200px] snap-start rounded-2xl bg-white p-3 shadow-default animate-pulse"
            >
              <div className="h-40 rounded-xl bg-neutral-200 mb-4" />
              <div className="h-4 bg-neutral-200 rounded mb-2" />
              <div className="h-4 bg-neutral-200 rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Ошибка загрузки */}
      {error && !isLoading && (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
          <p className="text-body-m text-text-secondary text-center">{error}</p>
          <button
            type="button"
            onClick={fetchNewArrivals}
            className="px-6 py-2 rounded-lg bg-[#0b1220] text-white hover:bg-[#070d19] transition"
          >
            Повторить попытку
          </button>
        </div>
      )}

      {/* Горизонтальная лента товаров */}
      {!isLoading && !error && products.length > 0 && (
        <div
          ref={scrollContainerRef}
          className="flex gap-2 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-3"
          role="list"
        >
          {products.map(product => (
            <div key={product.id} className="flex-shrink-0 w-[200px] snap-start" role="listitem">
              <ProductCard product={product} layout="compact" userRole="retail" />
            </div>
          ))}
        </div>
      )}

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
