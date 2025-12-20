/**
 * ProductBreadcrumbs Component (Story 12.1)
 * Навигационная цепочка для страницы товара
 */

import React from 'react';
import Link from 'next/link';
import { CategoryBreadcrumb } from '@/types/api';

interface ProductBreadcrumbsProps {
  breadcrumbs: CategoryBreadcrumb[];
  productName: string;
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
        {safeBreadcrumbs.map((crumb, index) => (
          <li
            key={crumb.id || index}
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <Link
              href={`/catalog?category=${crumb.slug}`}
              className="text-neutral-700 hover:text-primary-600 transition-colors"
              itemProp="item"
            >
              <span itemProp="name">{crumb.name}</span>
            </Link>
            <meta itemProp="position" content={String(index + 2)} />
          </li>
        ))}

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
