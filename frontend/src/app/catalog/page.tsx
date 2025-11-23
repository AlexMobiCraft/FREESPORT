/**
 * Страница каталога товаров FREESPORT Platform
 * Список товаров с фильтрацией и поиском
 */
import React from 'react';
import Button from '@/components/ui/Button';

const CatalogPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Заголовок страницы */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Каталог товаров</h1>
        <p className="text-gray-600">Широкий ассортимент спортивного оборудования и инвентаря</p>
      </div>

      {/* Фильтры и поиск */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Поиск */}
          <div className="flex-1">
            <div className="relative">
              <input
                type="text"
                placeholder="Поиск товаров..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg
                  className="h-5 w-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
            </div>
          </div>

          {/* Категории */}
          <div className="lg:w-64">
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
              <option value="">Все категории</option>
              <option value="fitness">Фитнес оборудование</option>
              <option value="sports">Спортивный инвентарь</option>
              <option value="clothing">Спортивная одежда</option>
              <option value="accessories">Аксессуары</option>
            </select>
          </div>

          {/* Сортировка */}
          <div className="lg:w-48">
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500">
              <option value="name">По названию</option>
              <option value="price_asc">По цене (возр.)</option>
              <option value="price_desc">По цене (убыв.)</option>
              <option value="date">По дате добавления</option>
            </select>
          </div>
        </div>
      </div>

      {/* Сетка товаров */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
        {/* Placeholder товары */}
        {Array.from({ length: 12 }).map((_, index) => (
          <div
            key={index}
            className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow duration-200"
          >
            {/* Изображение товара */}
            <div className="aspect-square bg-gray-200 relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <svg
                  className="h-16 w-16 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
              </div>
            </div>

            {/* Информация о товаре */}
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                Название товара {index + 1}
              </h3>
              <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                Краткое описание товара и его основные характеристики
              </p>

              {/* Цена */}
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="text-lg font-bold text-gray-900">
                    {(1000 + index * 500).toLocaleString('ru-RU')} ₽
                  </span>
                  {index % 3 === 0 && (
                    <span className="text-sm text-gray-500 line-through ml-2">
                      {(1200 + index * 500).toLocaleString('ru-RU')} ₽
                    </span>
                  )}
                </div>
                {index % 3 === 0 && (
                  <span className="bg-red-100 text-red-800 text-xs font-medium px-2 py-1 rounded-full">
                    -15%
                  </span>
                )}
              </div>

              {/* Кнопка в корзину */}
              <Button variant="primary" size="small" className="w-full">
                В корзину
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Пагинация */}
      <div className="flex justify-center">
        <nav className="flex items-center space-x-2">
          <Button variant="secondary" size="small" disabled>
            Предыдущая
          </Button>

          {[1, 2, 3, 4, 5].map(page => (
            <Button
              key={page}
              variant={page === 1 ? 'primary' : 'secondary'}
              size="small"
              className="min-w-[40px]"
            >
              {page}
            </Button>
          ))}

          <Button variant="secondary" size="small">
            Следующая
          </Button>
        </nav>
      </div>
    </div>
  );
};

export default CatalogPage;
