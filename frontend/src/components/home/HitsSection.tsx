/**
 * HitsSection Component
 *
 * Блок "Хиты продаж" на главной странице (Story 11.2).
 * Загружает и отображает 8 товаров с флагом is_hit=true.
 *
 * Features:
 * - Загрузка данных через productsService.getHits()
 * - Loading state с skeleton loaders
 * - Error state с retry кнопкой
 * - Graceful degradation при пустых данных
 *
 * @example
 * ```tsx
 * <HitsSection />
 * ```
 */

'use client';

import React, { useState, useEffect } from 'react';
import { RecommendationsRow } from '@/components/common';
import { Button } from '@/components/ui';
import productsService from '@/services/productsService';
import type { Product } from '@/types/api';

/**
 * Skeleton Loader для загрузки товаров
 */
const SkeletonLoader: React.FC = () => (
  <div className="py-12" role="status" aria-busy="true" aria-label="Загрузка хитов продаж">
    {/* Заголовок skeleton */}
    <div className="h-7 w-48 bg-neutral-200 rounded-md animate-pulse mb-6"></div>

    {/* Карточки товаров skeleton */}
    <div className="flex gap-4 overflow-x-hidden">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="w-[180px] flex-shrink-0">
          <div className="bg-neutral-100 rounded-md p-6 animate-pulse">
            {/* Изображение */}
            <div className="h-[180px] bg-neutral-200 rounded-md mb-3"></div>
            {/* Название */}
            <div className="h-4 bg-neutral-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-neutral-200 rounded w-1/2 mb-3"></div>
            {/* Цена */}
            <div className="h-5 bg-neutral-200 rounded w-2/3"></div>
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
      <p className="text-body-m text-text-secondary mb-4">Не удалось загрузить хиты продаж</p>
      <Button variant="secondary" onClick={onRetry}>
        Повторить попытку
      </Button>
    </div>
  </div>
);

/**
 * Компонент блока "Хиты продаж"
 */
export const HitsSection: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadHits = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await productsService.getHits();
      setProducts(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      console.error('Failed to load hits:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHits();
  }, []);

  // Loading state
  if (isLoading) {
    return <SkeletonLoader />;
  }

  // Error state
  if (error) {
    return <ErrorState onRetry={loadHits} />;
  }

  // Edge Case: Пустые данные - RecommendationsRow сам обработает (return null)
  return <RecommendationsRow title="Хиты продаж" items={products} />;
};

HitsSection.displayName = 'HitsSection';
