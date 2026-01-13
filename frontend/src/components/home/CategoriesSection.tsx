/**
 * CategoriesSection Component
 *
 * Блок "Популярные категории" на главной странице.
 * Отображает 7 конкретных категорий в Smart Grid layout.
 *
 * Features:
 * - API integration через categoriesService
 * - Фильтрация по слагам (TARGET_CATEGORIES)
 * - Smart Grid: Row 1 (3 элемента), Row 2 (4 элемента)
 * - Mobile: Горизонтальная карусель
 * - Loading skeleton
 * - Error state с retry функциональностью
 * - Resilience: graceful degradation при отсутствии категорий
 *
 * @example
 * ```tsx
 * <CategoriesSection />
 * ```
 */

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import categoriesService from '@/services/categoriesService';
import type { Category } from '@/types/api';

/**
 * Целевые категории для отображения (в порядке приоритета)
 */
const TARGET_CATEGORIES: { slug: string; priority: number }[] = [
  { slug: 'sportivnye-igry', priority: 1 },
  { slug: 'fitnes-i-atletika', priority: 2 },
  { slug: 'gimnastika-i-tantsy', priority: 3 },
  { slug: 'plavanie', priority: 4 },
  { slug: 'edinoborstva', priority: 5 },
  { slug: 'detskij-transport', priority: 6 },
  { slug: 'oborudovanie', priority: 7 },
];

/**
 * Фильтрует и сортирует категории согласно TARGET_CATEGORIES
 */
const filterAndSortCategories = (categories: Category[]): Category[] => {
  const slugToPriority = new Map(TARGET_CATEGORIES.map(tc => [tc.slug, tc.priority]));

  return categories
    .filter(cat => slugToPriority.has(cat.slug))
    .sort((a, b) => {
      const priorityA = slugToPriority.get(a.slug) ?? 999;
      const priorityB = slugToPriority.get(b.slug) ?? 999;
      return priorityA - priorityB;
    });
};

/**
 * Loading Skeleton для Smart Grid (Desktop)
 */
const CategoriesSkeleton: React.FC = () => (
  <div aria-label="Загрузка категорий" role="status" aria-live="polite">
    {/* Desktop Skeleton */}
    <div className="hidden lg:block space-y-6">
      {/* Row 1: 3 элемента */}
      <div className="grid grid-cols-3 gap-6" role="list">
        {[...Array(3)].map((_, index) => (
          <div
            key={`row1-${index}`}
            className="bg-neutral-100 rounded-lg animate-pulse h-32"
            role="listitem"
            aria-hidden="true"
          >
            <div className="h-full flex items-center justify-center">
              <div className="h-6 bg-neutral-200 rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
      {/* Row 2: 4 элемента */}
      <div className="grid grid-cols-4 gap-6" role="list">
        {[...Array(4)].map((_, index) => (
          <div
            key={`row2-${index}`}
            className="bg-neutral-100 rounded-lg animate-pulse h-28"
            role="listitem"
            aria-hidden="true"
          >
            <div className="h-full flex items-center justify-center">
              <div className="h-5 bg-neutral-200 rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </div>

    {/* Mobile/Tablet Skeleton - Carousel */}
    <div className="lg:hidden">
      <div
        className="flex gap-4 overflow-x-auto scrollbar-hide pb-4"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {[...Array(7)].map((_, index) => (
          <div
            key={`mobile-${index}`}
            className="flex-shrink-0 w-[200px] bg-neutral-100 rounded-lg animate-pulse h-24"
            role="listitem"
            aria-hidden="true"
          >
            <div className="h-full flex items-center justify-center">
              <div className="h-5 bg-neutral-200 rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

/**
 * Error State с retry кнопкой
 */
interface ErrorStateProps {
  onRetry: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({ onRetry }) => (
  <div className="text-center py-12">
    <p className="text-body text-text-secondary mb-4">Не удалось загрузить категории</p>
    <button
      onClick={onRetry}
      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
      type="button"
    >
      Повторить попытку
    </button>
  </div>
);

/**
 * Компонент карточки категории
 */
interface CategoryCardProps {
  category: Category;
  size?: 'large' | 'standard';
}

const CategoryCard: React.FC<CategoryCardProps> = ({ category, size = 'standard' }) => {
  const heightClass = size === 'large' ? 'h-32' : 'h-28';

  return (
    <a
      href={`/catalog?category=${category.slug}`}
      className={`
        block bg-white rounded-lg shadow-default hover:shadow-hover 
        transition-all duration-300 hover:scale-[1.02]
        ${heightClass} flex items-center justify-center p-4
      `}
    >
      <h3 className="text-lg font-semibold text-text-primary text-center leading-tight">
        {category.name}
      </h3>
    </a>
  );
};

/**
 * Компонент блока "Популярные категории"
 */
export const CategoriesSection: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadCategories = async () => {
    try {
      setIsLoading(true);
      setError(null);
      // Получаем все категории (целевые — подкатегории СПОРТ)
      const data = await categoriesService.getCategories({
        limit: 100,
      });
      setCategories(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load categories'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  // Фильтруем и сортируем категории
  const filteredCategories = useMemo(() => filterAndSortCategories(categories), [categories]);

  // Разделяем на ряды для Smart Grid
  const row1Categories = filteredCategories.slice(0, 3);
  const row2Categories = filteredCategories.slice(3, 7);

  // Не рендерим секцию если нет категорий и не идет загрузка
  if (!isLoading && !error && filteredCategories.length === 0) {
    return null;
  }

  return (
    <section
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 mb-16"
      aria-labelledby="categories-heading"
    >
      {/* Заголовок секции */}
      <h2 id="categories-heading" className="text-3xl font-bold mb-8 text-text-primary">
        Популярные категории
      </h2>

      {/* Loading State */}
      {isLoading && <CategoriesSkeleton />}

      {/* Error State */}
      {error && !isLoading && <ErrorState onRetry={loadCategories} />}

      {/* Success State */}
      {!isLoading && !error && filteredCategories.length > 0 && (
        <>
          {/* Desktop: Smart Grid Layout */}
          <div className="hidden lg:block space-y-6">
            {/* Row 1: 3 большие карточки */}
            {row1Categories.length > 0 && (
              <div
                className={`grid gap-6 ${
                  row1Categories.length === 3
                    ? 'grid-cols-3'
                    : row1Categories.length === 2
                      ? 'grid-cols-2 max-w-2xl mx-auto'
                      : 'grid-cols-1 max-w-md mx-auto'
                }`}
                role="list"
              >
                {row1Categories.map(category => (
                  <div key={category.id} role="listitem">
                    <CategoryCard category={category} size="large" />
                  </div>
                ))}
              </div>
            )}

            {/* Row 2: 4 стандартные карточки */}
            {row2Categories.length > 0 && (
              <div
                className={`grid gap-6 ${
                  row2Categories.length === 4
                    ? 'grid-cols-4'
                    : row2Categories.length === 3
                      ? 'grid-cols-3 max-w-3xl mx-auto'
                      : row2Categories.length === 2
                        ? 'grid-cols-2 max-w-xl mx-auto'
                        : 'grid-cols-1 max-w-sm mx-auto'
                }`}
                role="list"
              >
                {row2Categories.map(category => (
                  <div key={category.id} role="listitem">
                    <CategoryCard category={category} size="standard" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Mobile/Tablet: Горизонтальная карусель */}
          <div className="lg:hidden">
            <div
              className="flex gap-4 overflow-x-auto pb-4 -mx-3 px-3"
              style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              role="list"
            >
              {filteredCategories.map(category => (
                <a
                  key={category.id}
                  href={`/catalog?category=${category.slug}`}
                  role="listitem"
                  className="
                    flex-shrink-0 w-[200px] h-24
                    bg-white rounded-lg shadow-default hover:shadow-hover 
                    transition-all duration-300
                    flex items-center justify-center p-4
                  "
                >
                  <h3 className="text-base font-semibold text-text-primary text-center leading-tight">
                    {category.name}
                  </h3>
                </a>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
};

CategoriesSection.displayName = 'CategoriesSection';
