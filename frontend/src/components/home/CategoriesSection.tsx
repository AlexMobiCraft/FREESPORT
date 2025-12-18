/**
 * CategoriesSection Component
 *
 * Блок "Категории" на главной странице (Story 12.7).
 * Отображает категории в горизонтальной карусели с навигацией.
 *
 * Features:
 * - Горизонтальная карусель с scroll-snap
 * - Кнопки навигации prev/next
 * - Использует CategoryCard компонент
 * - Mock данные для development
 *
 * @example
 * ```tsx
 * <CategoriesSection />
 * ```
 */

'use client';

import React, { useRef, useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { CategoryCard } from './CategoryCard';
import { MOCK_CATEGORIES } from '@/__mocks__/categories';

/**
 * Компонент блока "Категории"
 */
export const CategoriesSection: React.FC = () => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollButtons = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollLeft, scrollWidth, clientWidth } = container;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 4);
  };

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    updateScrollButtons();

    const handleResize = () => updateScrollButtons();
    container.addEventListener('scroll', updateScrollButtons);
    window.addEventListener('resize', handleResize);

    return () => {
      container.removeEventListener('scroll', updateScrollButtons);
      window.removeEventListener('resize', handleResize);
    };
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

  return (
    <section
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 relative"
      aria-labelledby="categories-heading"
    >
      {/* Заголовок секции - headline-l */}
      <h2 id="categories-heading" className="text-3xl font-bold mb-8 text-text-primary">
        Категории
      </h2>

      {/* Кнопки навигации */}
      {canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="absolute left-1 top-1/2 -translate-y-1/2 z-10 hidden lg:flex items-center justify-center w-12 h-12 bg-transparent text-primary transition-opacity focus:outline-none"
          aria-label="Предыдущие категории"
        >
          <ChevronLeft className="w-7 h-7" />
        </button>
      )}

      {canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="absolute right-1 top-1/2 -translate-y-1/2 z-10 hidden lg:flex items-center justify-center w-12 h-12 bg-transparent text-primary transition-opacity focus:outline-none"
          aria-label="Следующие категории"
        >
          <ChevronRight className="w-7 h-7" />
        </button>
      )}

      {/* Горизонтальная карусель категорий */}
      <div
        ref={scrollContainerRef}
        className="flex gap-4 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-3"
        role="list"
      >
        {MOCK_CATEGORIES.map(category => (
          <div key={category.id} className="flex-shrink-0 w-[200px] snap-start" role="listitem">
            <CategoryCard
              name={category.name}
              image={category.image}
              href={category.href}
              alt={category.alt}
            />
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

CategoriesSection.displayName = 'CategoriesSection';
