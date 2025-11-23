/**
 * Страница каталога товаров FREESPORT Platform
 * Центральная часть оформлена по макету каталога (Story 12.7)
 */

'use client';

import React, { useState } from 'react';
import Button from '@/components/ui/Button';
import { Badge, type BadgeVariant } from '@/components/ui/Badge/Badge';
import { Heart, Grid2x2, List } from 'lucide-react';

type ProductCard = {
  id: number;
  brand: string;
  name: string;
  price: string;
  oldPrice: string | null;
  badge: { variant: BadgeVariant; label: string } | null;
};

const productCards: ProductCard[] = [
  {
    id: 1,
    brand: 'Nike',
    name: 'Sportswear Club Fleece',
    price: '7 499₽',
    oldPrice: null,
    badge: null,
  },
  {
    id: 2,
    brand: 'Adidas',
    name: 'Essentials Hoodie',
    price: '5 999₽',
    oldPrice: '8 299₽',
    badge: { variant: 'sale', label: 'SALE' },
  },
  {
    id: 3,
    brand: 'Puma',
    name: 'Graphic Sweatshirt',
    price: '6 899₽',
    oldPrice: null,
    badge: null,
  },
  {
    id: 4,
    brand: 'The North Face',
    name: 'Box NSE Pullover',
    price: '9 199₽',
    oldPrice: null,
    badge: null,
  },
  {
    id: 5,
    brand: 'Nike',
    name: 'Tech Fleece Full-Zip',
    price: '11 499₽',
    oldPrice: null,
    badge: null,
  },
  {
    id: 6,
    brand: 'Under Armour',
    name: 'Rival Fleece Logo',
    price: '6 299₽',
    oldPrice: null,
    badge: { variant: 'new', label: 'NEW' },
  },
];

const categories = [
  'Вся одежда',
  'Футболки и майки',
  'Худи и толстовки',
  'Жилеты',
  'Свиты',
  'Олимпийки',
  'Брюки и шорты',
  'Куртки и ветровки',
];

const formatCurrency = (value: number) =>
  value.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });

const PriceRangeSlider: React.FC = () => {
  const minValue = 0;
  const maxValue = 20000;
  const [range, setRange] = useState({ min: 500, max: 10000 });

  const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

  const handleMinChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setRange(prev => ({ ...prev, min: Math.min(value, prev.max - 500) }));
  };

  const handleMaxChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setRange(prev => ({ ...prev, max: Math.max(value, prev.min + 500) }));
  };

  const minPercent =
    ((clamp(range.min, minValue, maxValue) - minValue) / (maxValue - minValue)) * 100;
  const maxPercent =
    ((clamp(range.max, minValue, maxValue) - minValue) / (maxValue - minValue)) * 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>Цена</span>
        <span>
          {formatCurrency(range.min)} — {formatCurrency(range.max)}
        </span>
      </div>

      <div className="relative h-10">
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="h-[4px] w-full rounded-full bg-[#E1E6EF]" />
        </div>
        <div
          className="absolute inset-y-0 flex items-center"
          style={{ left: `${minPercent}%`, right: `${100 - maxPercent}%` }}
        >
          <div className="h-[4px] w-full rounded-full bg-[#1E6FFF]" />
        </div>

        <input
          type="range"
          min={minValue}
          max={maxValue}
          value={range.min}
          onChange={handleMinChange}
          className="price-range-thumb absolute inset-x-0 top-1/2 -translate-y-1/2 w-full appearance-none bg-transparent"
        />
        <input
          type="range"
          min={minValue}
          max={maxValue}
          value={range.max}
          onChange={handleMaxChange}
          className="price-range-thumb absolute inset-x-0 top-1/2 -translate-y-1/2 w-full appearance-none bg-transparent"
        />
      </div>

      <div className="flex justify-between text-xs text-gray-500">
        <span>
          {minValue.toLocaleString('ru-RU')}
          <span className="ml-1 text-gray-400">₽</span>
        </span>
        <span>
          {maxValue.toLocaleString('ru-RU')}
          <span className="ml-1 text-gray-400">₽</span>
        </span>
      </div>

      <style jsx>{`
        .price-range-thumb::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          height: 18px;
          width: 18px;
          border-radius: 50%;
          background: #1e6fff;
          border: 4px solid #dbe9ff;
          box-shadow: 0 2px 6px rgba(30, 111, 255, 0.35);
          cursor: pointer;
          margin-top: -9px;
        }

        .price-range-thumb::-moz-range-thumb {
          height: 18px;
          width: 18px;
          border-radius: 50%;
          background: #1e6fff;
          border: 4px solid #dbe9ff;
          box-shadow: 0 2px 6px rgba(30, 111, 255, 0.35);
          cursor: pointer;
        }

        .price-range-thumb::-webkit-slider-runnable-track {
          height: 1px;
          background: transparent;
        }

        .price-range-thumb::-moz-range-track {
          height: 1px;
          background: transparent;
        }
      `}</style>
    </div>
  );
};

const CatalogPage: React.FC = () => {
  return (
    <div className="bg-[#F5F7FB] min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Хлебные крошки */}
        <nav className="text-sm text-gray-500 flex gap-2 flex-wrap">
          <span>Главная</span>
          <span>/</span>
          <span>Спорт</span>
          <span>/</span>
          <span className="text-gray-900">Единоборства</span>
        </nav>

        {/* Заголовок */}
        <h1 className="text-4xl font-semibold text-gray-900 mt-3">Единоборства</h1>

        <div className="mt-8 grid gap-8 lg:grid-cols-[280px_1fr]">
          {/* Sidebar */}
          <aside className="space-y-8">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">Категории</h2>
              <ul className="space-y-3 text-sm">
                {categories.map(category => (
                  <li
                    key={category}
                    className={
                      category === 'Худи и толстовки'
                        ? 'text-blue-600 font-semibold'
                        : 'text-gray-600'
                    }
                  >
                    {category}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-6">
              <h2 className="text-base font-semibold text-gray-900">Фильтры</h2>

              <PriceRangeSlider />

              <div className="space-y-2 text-sm text-gray-600">
                <details open>
                  <summary className="cursor-pointer font-medium text-gray-900">Бренд</summary>
                  <ul className="mt-2 space-y-1">
                    {['Nike', 'Adidas', 'Puma', 'Under Armour'].map(brand => (
                      <li key={brand} className="flex items-center gap-2">
                        <input type="checkbox" className="rounded" />
                        <span>{brand}</span>
                      </li>
                    ))}
                  </ul>
                </details>
                <details>
                  <summary className="cursor-pointer font-medium text-gray-900">Размер</summary>
                </details>
                <details>
                  <summary className="cursor-pointer font-medium text-gray-900">Цвет</summary>
                </details>
              </div>

              <div className="flex flex-col gap-3">
                <Button variant="primary" size="small">
                  Применить
                </Button>
                <Button variant="secondary" size="small">
                  Сбросить
                </Button>
              </div>
            </div>
          </aside>

          {/* Main content */}
          <section className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <span className="text-sm text-gray-600">Показано 12 из 210 товаров</span>

              <div className="flex items-center gap-3">
                <div className="inline-flex items-center rounded-full bg-gray-100 p-1">
                  <button className="flex items-center gap-1 rounded-full bg-white px-3 py-2 text-sm font-medium text-gray-900 shadow">
                    <Grid2x2 className="h-4 w-4" />
                    <span className="hidden sm:inline">Сетка</span>
                  </button>
                  <button className="flex items-center gap-1 rounded-full px-3 py-2 text-sm font-medium text-gray-500">
                    <List className="h-4 w-4" />
                    <span className="hidden sm:inline">Список</span>
                  </button>
                </div>

                <div className="relative">
                  <select className="appearance-none border border-gray-200 rounded-full py-2 pl-4 pr-10 text-sm text-gray-700">
                    <option>По популярности</option>
                    <option>По цене (возр.)</option>
                    <option>По цене (убыв.)</option>
                  </select>
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
                    ▼
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {productCards.map(product => (
                <article
                  key={product.id}
                  className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden"
                >
                  <div className="relative">
                    <div className="aspect-[4/3] bg-gray-100" />
                    <button className="absolute top-4 right-4 bg-white rounded-full p-2 shadow-sm">
                      <Heart className="h-4 w-4 text-gray-600" />
                    </button>
                    {product.badge && (
                      <Badge
                        variant={product.badge.variant}
                        className="absolute top-4 left-4 shadow-sm"
                      >
                        {product.badge.label}
                      </Badge>
                    )}
                  </div>

                  <div className="p-5 space-y-2">
                    <span className="text-xs uppercase tracking-wide text-gray-500">
                      {product.brand}
                    </span>
                    <h3 className="text-lg font-semibold text-gray-900">{product.name}</h3>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-bold text-gray-900">{product.price}</span>
                      {product.oldPrice && (
                        <span className="text-sm text-gray-400 line-through">
                          {product.oldPrice}
                        </span>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <div className="flex justify-center">
              <nav className="flex items-center gap-2 text-sm">
                <button className="h-10 w-10 rounded-full border border-gray-200 text-gray-500">
                  ←
                </button>
                {[1, 2, 3].map(page => (
                  <button
                    key={page}
                    className={
                      page === 1
                        ? 'h-10 w-10 rounded-full bg-blue-600 text-white'
                        : 'h-10 w-10 rounded-full border border-gray-200 text-gray-600'
                    }
                  >
                    {page}
                  </button>
                ))}
                <button className="h-10 w-10 rounded-full border border-gray-200 text-gray-600">
                  …
                </button>
                <button className="h-10 w-10 rounded-full border border-gray-200 text-gray-600">
                  18
                </button>
                <button className="h-10 w-10 rounded-full border border-gray-200 text-gray-500">
                  →
                </button>
              </nav>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default CatalogPage;
