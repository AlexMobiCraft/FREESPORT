/**
 * ProductBreadcrumbs Component (Story 12.1)
 * Навигационная цепочка для страницы товара
 * Поддерживает оба формата: string[] (legacy) и CategoryBreadcrumb[]
 */

import React from 'react';
import Link from 'next/link';
import { CategoryBreadcrumb } from '@/types/api';

// Поддержка обоих форматов для обратной совместимости
type BreadcrumbItem = string | CategoryBreadcrumb;

interface ProductBreadcrumbsProps {
  breadcrumbs: BreadcrumbItem[];
  productName: string;
}

// Проверка, является ли элемент объектом CategoryBreadcrumb
function isCategoryBreadcrumb(item: BreadcrumbItem): item is CategoryBreadcrumb {
  return typeof item === 'object' && item !== null && 'name' in item;
}

export default function ProductBreadcrumbs({
  breadcrumbs = [],
  productName,
}: ProductBreadcrumbsProps) {
  // Защита от undefined/null
  const safeBreadcrumbs = breadcrumbs || [];

  return (
    <nav aria-label="Breadcrumb" className="mb-6">
      <ol
        className="flex items-center gap-2 text-sm text-neutral-700 flex-wrap"
        itemScope
        itemType="https://schema.org/BreadcrumbList"
      >
        {/* Главная страница */}
        <li itemProp="itemListElement" itemScope itemType="https://schema.org/ListItem">
          <Link href="/" className="hover:text-primary-600 transition-colors" itemProp="item">
            <span itemProp="name">Главная</span>
          </Link>
          <meta itemProp="position" content="1" />
        </li>

        {/* Категории из breadcrumbs - с активными ссылками */}
        {safeBreadcrumbs.map((crumb, index) => {
          const isObject = isCategoryBreadcrumb(crumb);
          const name = isObject ? crumb.name : crumb;
          const slug = isObject ? crumb.slug : null;
          const key = isObject ? crumb.id || index : index;

          // Пропускаем "Главная" в начале если это строковый формат
          if (!isObject && name === 'Главная') {
            return null;
          }

          return (
            <li
              key={key}
              className="flex items-center gap-2"
              itemProp="itemListElement"
              itemScope
              itemType="https://schema.org/ListItem"
            >
              <svg
                className="w-4 h-4 text-neutral-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              {slug ? (
                <Link
                  href={`/catalog?category=${slug}`}
                  className="text-neutral-700 hover:text-primary-600 transition-colors"
                  itemProp="item"
                >
                  <span itemProp="name">{name}</span>
                </Link>
              ) : (
                <span className="text-neutral-700" itemProp="name">
                  {name}
                </span>
              )}
              <meta itemProp="position" content={String(index + 2)} />
            </li>
          );
        })}

        {/* Текущий товар */}
        <li
          className="flex items-center gap-2"
          itemProp="itemListElement"
          itemScope
          itemType="https://schema.org/ListItem"
          aria-current="page"
        >
          <svg
            className="w-4 h-4 text-neutral-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-neutral-900 font-medium" itemProp="name">
            {productName}
          </span>
          <meta itemProp="position" content={String(safeBreadcrumbs.length + 2)} />
        </li>
      </ol>
    </nav>
  );
}
