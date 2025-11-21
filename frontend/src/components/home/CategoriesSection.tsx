/**
 * CategoriesSection Component
 *
 * Блок "Категории" на главной странице (Story 12.7).
 * Отображает 5 основных категорий в grid layout согласно Design System v2.0.
 *
 * Features:
 * - Grid layout: 5 колонок на desktop, 2-3 на tablet, 1 на mobile
 * - Использует CategoryCard компонент
 * - Mock данные для development
 *
 * @example
 * ```tsx
 * <CategoriesSection />
 * ```
 */

'use client';

import React from 'react';
import { CategoryCard } from './CategoryCard';
import { MOCK_CATEGORIES } from '@/__mocks__/categories';

/**
 * Компонент блока "Категории"
 */
export const CategoriesSection: React.FC = () => {
  return (
    <section
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6"
      aria-labelledby="categories-heading"
    >
      {/* Заголовок секции - headline-l */}
      <h2 id="categories-heading" className="text-3xl font-bold mb-8 text-primary">
        Категории
      </h2>

      {/* Grid категорий: 5 колонок на desktop, 3 на tablet, 2 на mobile */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {MOCK_CATEGORIES.map(category => (
          <CategoryCard
            key={category.id}
            name={category.name}
            image={category.image}
            href={category.href}
            alt={category.alt}
          />
        ))}
      </div>
    </section>
  );
};

CategoriesSection.displayName = 'CategoriesSection';
