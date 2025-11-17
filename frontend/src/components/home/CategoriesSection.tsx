/**
 * CategoriesSection Component
 *
 * Блок "Популярные категории" на главной странице (Story 11.2).
 * Загружает и отображает до 6 корневых категорий в grid layout.
 *
 * Features:
 * - Загрузка данных через categoriesService.getCategories()
 * - Grid layout (responsive: 1/2/3 колонки)
 * - Отображение иконки категории и количества товаров
 * - Кликабельные ссылки на /catalog/[slug]
 * - Loading/Error states
 *
 * @example
 * ```tsx
 * <CategoriesSection />
 * ```
 */

'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui';
import { Button } from '@/components/ui';
import categoriesService from '@/services/categoriesService';
import type { Category } from '@/types/api';
import { cn } from '@/utils/cn';

/**
 * Skeleton Loader для загрузки категорий
 */
const SkeletonLoader: React.FC = () => (
  <div className="py-12" role="status" aria-busy="true" aria-label="Загрузка категорий">
    {/* Заголовок skeleton */}
    <div className="h-7 w-56 bg-neutral-200 rounded-md animate-pulse mb-6"></div>

    {/* Grid категорий skeleton */}
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="bg-neutral-100 rounded-md p-6 animate-pulse">
          <div className="flex items-center gap-4">
            {/* Иконка */}
            <div className="w-12 h-12 bg-neutral-200 rounded-full"></div>
            {/* Текст */}
            <div className="flex-1">
              <div className="h-5 bg-neutral-200 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-neutral-200 rounded w-1/2"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/**
 * Error State компонент
 */
interface ErrorStateProps {
  onRetry: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({ onRetry }) => (
  <div className="py-12">
    <div className="text-center py-8 px-4 bg-neutral-50 rounded-lg">
      <div className="mb-4">
        <svg
          className="w-12 h-12 mx-auto text-neutral-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <p className="text-body-m text-text-secondary mb-4">Не удалось загрузить категории</p>
      <Button variant="secondary" onClick={onRetry}>
        Повторить попытку
      </Button>
    </div>
  </div>
);

/**
 * Компонент блока "Популярные категории"
 */
export const CategoriesSection: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadCategories = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await categoriesService.getCategories();
      setCategories(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Failed to load categories:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  // Loading state
  if (isLoading) {
    return <SkeletonLoader />;
  }

  // Error state
  if (error) {
    return <ErrorState onRetry={loadCategories} />;
  }

  // Edge Case: Пустые данные - не отображаем блок
  if (!categories || categories.length === 0) {
    return null;
  }

  return (
    <section className="py-12" aria-labelledby="categories-heading">
      {/* Заголовок секции */}
      <h2 id="categories-heading" className="text-title-m font-semibold mb-6 text-text-primary">
        Популярные категории
      </h2>

      {/* Grid категорий */}
      <div
        className={cn(
          // Responsive grid
          'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
          // Gap между карточками (24px)
          'gap-6'
        )}
        role="list"
      >
        {categories.map(category => (
          <Link
            key={category.id}
            href={`/catalog/${category.slug}`}
            className="focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-lg"
            role="listitem"
          >
            <Card hover className="h-full">
              <div className="flex items-center gap-4">
                {/* Иконка категории */}
                <div
                  className={cn(
                    'w-12 h-12 flex items-center justify-center',
                    'bg-primary-50 rounded-full text-2xl',
                    'flex-shrink-0'
                  )}
                  aria-hidden="true"
                >
                  {/* Edge Case: Emoji из API - безопасно рендерим через Unicode */}
                  {category.icon || '📦'}
                </div>

                {/* Информация о категории */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-body-m font-semibold text-text-primary mb-1 truncate">
                    {category.name}
                  </h3>
                  <p className="text-caption text-text-secondary">
                    {category.products_count} {getProductsLabel(category.products_count)}
                  </p>
                </div>

                {/* Стрелка */}
                <svg
                  className="w-5 h-5 text-neutral-400 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
};

CategoriesSection.displayName = 'CategoriesSection';

/**
 * Вспомогательная функция для правильного склонения "товар/товара/товаров"
 */
function getProductsLabel(count: number): string {
  if (count % 10 === 1 && count % 100 !== 11) {
    return 'товар';
  }
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
    return 'товара';
  }
  return 'товаров';
}
