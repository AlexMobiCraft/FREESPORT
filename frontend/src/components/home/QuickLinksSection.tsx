/**
 * QuickLinksSection Component
 *
 * Горизонтально прокручиваемый список быстрых ссылок на главной странице.
 * Первые 3 элемента — статические (Новинки, Хиты, Скидки).
 * Остальные — динамически подгружаемые корневые категории.
 *
 * Features:
 * - Горизонтальный скролл с snap
 * - Кнопки-стрелки на десктопе
 * - Graceful degradation при ошибке API
 *
 * @example
 * ```tsx
 * <QuickLinksSection />
 * ```
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import categoriesService from '@/services/categoriesService';
import type { Category } from '@/types/api';
import { STATIC_QUICK_LINKS } from '@/config/quickLinks';
import type { QuickLink } from '@/config/quickLinks';

/** Цвета для вариантов статических ссылок */
const VARIANT_STYLES: Record<QuickLink['variant'], string> = {
    new: 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-blue-200',
    hit: 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-orange-200',
    sale: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-emerald-200',
};

export const QuickLinksSection: React.FC = () => {
    const [categories, setCategories] = useState<Category[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(false);

    // Загрузка категорий
    useEffect(() => {
        const loadCategories = async () => {
            try {
                const data = await categoriesService.getCategories({
                    parent_id__isnull: true,
                    limit: 100,
                });
                setCategories(data);
            } catch {
                // При ошибке API показываем только статические ссылки
                setCategories([]);
            } finally {
                setIsLoading(false);
            }
        };
        loadCategories();
    }, []);

    // Обновление состояния кнопок скролла
    const updateScrollButtons = useCallback(() => {
        const el = scrollRef.current;
        if (!el) return;
        setCanScrollLeft(el.scrollLeft > 0);
        setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
    }, []);

    useEffect(() => {
        const el = scrollRef.current;
        if (!el) return;

        updateScrollButtons();
        el.addEventListener('scroll', updateScrollButtons, { passive: true });
        window.addEventListener('resize', updateScrollButtons);

        return () => {
            el.removeEventListener('scroll', updateScrollButtons);
            window.removeEventListener('resize', updateScrollButtons);
        };
    }, [isLoading, categories, updateScrollButtons]);

    const scroll = (direction: 'left' | 'right') => {
        scrollRef.current?.scrollBy({
            left: direction === 'left' ? -300 : 300,
            behavior: 'smooth',
        });
    };

    return (
        <section
            className="relative max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 py-4 md:py-6"
            aria-label="Быстрые ссылки"
        >
            <div className="relative group">
                {/* Стрелка влево (десктоп) */}
                {canScrollLeft && (
                    <button
                        type="button"
                        onClick={() => scroll('left')}
                        className="hidden md:flex absolute left-0 top-1/2 -translate-y-1/2 -translate-x-3 z-10 w-9 h-9 items-center justify-center rounded-full bg-white shadow-md hover:shadow-lg transition-shadow border border-neutral-200"
                        aria-label="Прокрутить влево"
                    >
                        <ChevronLeft className="w-5 h-5 text-neutral-600" />
                    </button>
                )}

                {/* Контейнер с горизонтальным скроллом */}
                <div
                    ref={scrollRef}
                    className="flex gap-3 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-1"
                    role="list"
                >
                    {/* Статические ссылки */}
                    {STATIC_QUICK_LINKS.map((item) => (
                        <Link
                            key={item.variant}
                            href={item.link}
                            role="listitem"
                            className={`
                flex-shrink-0 snap-start inline-flex items-center gap-2
                px-5 py-2.5 rounded-full text-sm font-semibold
                shadow-sm hover:shadow-md transition-all duration-200
                hover:scale-105
                ${VARIANT_STYLES[item.variant]}
              `}
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </Link>
                    ))}

                    {/* Loading skeleton */}
                    {isLoading &&
                        [...Array(4)].map((_, i) => (
                            <div
                                key={`skeleton-${i}`}
                                className="flex-shrink-0 snap-start h-10 w-28 rounded-full bg-neutral-100 animate-pulse"
                                role="listitem"
                                aria-hidden="true"
                            />
                        ))}

                    {/* Динамические категории */}
                    {!isLoading &&
                        categories.map((category) => (
                            <Link
                                key={category.id}
                                href={`/catalog/${category.slug}`}
                                role="listitem"
                                className="
                  flex-shrink-0 snap-start inline-flex items-center gap-2
                  px-5 py-2.5 rounded-full text-sm font-medium
                  bg-[var(--bg-panel,#f5f5f5)] text-[var(--color-text-primary,#1a1a1a)]
                  shadow-sm hover:shadow-md transition-all duration-200
                  hover:scale-105 border border-neutral-200/60
                "
                            >
                                {category.icon && (
                                    <span className="text-base" aria-hidden="true">
                                        {category.icon}
                                    </span>
                                )}
                                <span>{category.name}</span>
                            </Link>
                        ))}
                </div>

                {/* Стрелка вправо (десктоп) */}
                {canScrollRight && (
                    <button
                        type="button"
                        onClick={() => scroll('right')}
                        className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 translate-x-3 z-10 w-9 h-9 items-center justify-center rounded-full bg-white shadow-md hover:shadow-lg transition-shadow border border-neutral-200"
                        aria-label="Прокрутить вправо"
                    >
                        <ChevronRight className="w-5 h-5 text-neutral-600" />
                    </button>
                )}
            </div>
        </section>
    );
};

QuickLinksSection.displayName = 'QuickLinksSection';
