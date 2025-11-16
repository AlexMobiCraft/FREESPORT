/**
 * Главная страница FREESPORT Platform
 * Hero секция и основная информация
 */
import Link from 'next/link';
import Button from '@/components/ui/Button';

export default function Home() {
  return (
    <div className="bg-white">
      {/* Hero секция */}
      <section className="relative bg-gradient-to-r from-blue-600 to-blue-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold mb-6">FREESPORT Platform</h1>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto text-blue-100">
              Ведущая платформа B2B/B2C продаж спортивных товаров. Объединяем 5 торговых марок в
              единой экосистеме.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/catalog">
                <Button
                  variant="primary"
                  size="lg"
                  className="bg-white text-blue-600 hover:bg-gray-100"
                >
                  Перейти в каталог
                </Button>
              </Link>
              <Link href="/wholesale">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white text-white hover:bg-white hover:text-blue-600"
                >
                  Оптовые продажи
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Преимущества */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Преимущества платформы</h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Современные решения для розничных и оптовых покупателей
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Быстрое оформление</h3>
              <p className="text-gray-600">Современный интерфейс и простой процесс заказа</p>
            </div>

            <div className="text-center">
              <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Проверенное качество</h3>
              <p className="text-gray-600">
                Только сертифицированные товары от надежных поставщиков
              </p>
            </div>

            <div className="text-center">
              <div className="bg-orange-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-orange-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Выгодные цены</h3>
              <p className="text-gray-600">
                Специальные условия для оптовых покупателей и тренеров
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Для бизнеса */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-gray-900 to-gray-700 rounded-2xl p-8 md:p-12 text-white">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-3xl font-bold mb-4">Решения для бизнеса</h2>
                <p className="text-gray-300 text-lg mb-6">
                  Специальные условия для тренеров, спортивных федераций и дистрибьюторов.
                  Многоуровневая система скидок и персональный менеджер.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link href="/wholesale">
                    <Button variant="primary" size="lg">
                      Узнать условия
                    </Button>
                  </Link>
                  <Link href="/contacts">
                    <Button
                      variant="outline"
                      size="lg"
                      className="border-white text-white hover:bg-white hover:text-gray-900"
                    >
                      Связаться с нами
                    </Button>
                  </Link>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-blue-400 mb-1">1000+</div>
                  <div className="text-sm text-gray-300">Товаров в каталоге</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400 mb-1">500+</div>
                  <div className="text-sm text-gray-300">B2B партнеров</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-orange-400 mb-1">24/7</div>
                  <div className="text-sm text-gray-300">Поддержка</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-purple-400 mb-1">5</div>
                  <div className="text-sm text-gray-300">Торговых марок</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
