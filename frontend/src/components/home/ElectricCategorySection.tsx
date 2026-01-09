/**
 * ElectricCategorySection Component
 *
 * Секция "Популярные категории" для главной страницы.
 * Использует ElectricCategoryCard из дизайн-системы.
 *
 * Design System: Electric Orange v2.3.0
 * - Grid layout: 3 колонки на desktop, 2 на tablet, 1 на mobile
 * - Square cards (aspect-ratio 1:1)
 * - Grayscale → Color hover effect
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ElectricCategoryCard } from '@/components/ui/CategoryCard/ElectricCategoryCard';
import { ElectricButton } from '@/components/ui/Button/ElectricButton';
import categoriesService from '@/services/categoriesService';
import type { Category } from '@/types/api';

/**
 * Loading skeleton for categories
 */
const CategoriesSkeleton = () => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
    {Array.from({ length: 6 }).map((_, i) => (
      <div
        key={i}
        className="aspect-square bg-[var(--bg-card)] border border-[var(--border-default)] animate-pulse"
      />
    ))}
  </div>
);

export const ElectricCategorySection: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await categoriesService.getCategories({
        parent_id__isnull: true,
        limit: 6,
      });
      setCategories(data);
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError('Не удалось загрузить категории');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  // Don't render if no categories
  if (!isLoading && !error && categories.length === 0) {
    return null;
  }

  return (
    <section
      className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-12"
      aria-labelledby="categories-heading"
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-8">
        {/* Skewed title */}
        <h2
          id="categories-heading"
          className="text-2xl md:text-3xl font-black uppercase tracking-tight text-[var(--color-text-primary)]"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
            transformOrigin: 'left',
          }}
        >
          <span style={{ display: 'inline-block', transform: 'skewX(12deg)' }}>
            ПОПУЛЯРНЫЕ КАТЕГОРИИ
          </span>
        </h2>

        {/* View all link */}
        <Link href="/electric/catalog">
          <ElectricButton variant="outline" size="sm">
            Все категории
          </ElectricButton>
        </Link>
      </div>

      {/* Loading state */}
      {isLoading && <CategoriesSkeleton />}

      {/* Error state */}
      {error && !isLoading && (
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <p className="text-[var(--color-text-secondary)]">{error}</p>
          <ElectricButton variant="outline" size="sm" onClick={loadCategories}>
            Повторить
          </ElectricButton>
        </div>
      )}

      {/* Categories grid */}
      {!isLoading && !error && categories.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5" role="list">
          {categories.map(category => (
            <div key={category.id} role="listitem">
              <ElectricCategoryCard
                title={category.name}
                image={`/categories/${category.slug}.jpg`}
                productCount={category.products_count}
                href={`/electric/catalog?category=${category.slug}`}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

ElectricCategorySection.displayName = 'ElectricCategorySection';

export default ElectricCategorySection;
