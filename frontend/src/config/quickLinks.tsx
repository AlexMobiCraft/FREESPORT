/**
 * Quick Links Configuration
 *
 * Статические ссылки для секции быстрого доступа на главной странице.
 * Отображаются перед динамическими категориями.
 */

import React from 'react';
import { Sparkles, Flame, Percent } from 'lucide-react';

export interface QuickLink {
    label: string;
    link: string;
    variant: 'new' | 'hit' | 'sale';
    icon: React.ReactNode;
}

export interface CategoryLink {
    id: number;
    label: string;
    link: string;
    slug: string;
}

export const STATIC_QUICK_LINKS: QuickLink[] = [
    {
        label: 'Новинки',
        icon: <Sparkles className="w-4 h-4" />,
        link: '/catalog?sort=new',
        variant: 'new',
    },
    {
        label: 'Хиты продаж',
        icon: <Flame className="w-4 h-4" />,
        link: '/catalog?sort=popular',
        variant: 'hit',
    },
    {
        label: 'Скидки',
        icon: <Percent className="w-4 h-4" />,
        link: '/catalog?is_discounted=true',
        variant: 'sale',
    },
];
