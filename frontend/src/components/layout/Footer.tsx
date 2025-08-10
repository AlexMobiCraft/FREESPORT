/**
 * Компонент Footer для FREESPORT Platform
 * Информационные ссылки и контакты
 */
import React from 'react';
import Link from 'next/link';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Логотип и описание */}
          <div className="col-span-1 md:col-span-1">
            <Link href="/" className="flex items-center mb-4">
              <span className="text-2xl font-bold text-blue-400">
                FREESPORT
              </span>
            </Link>
            <p className="text-gray-400 text-sm leading-relaxed">
              Ведущая платформа B2B/B2C продаж спортивных товаров. 
              Объединяем 5 торговых марок в единой экосистеме.
            </p>
          </div>
          
          {/* Каталог */}
          <div>
            <h3 className="font-semibold text-lg mb-4">Каталог</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link 
                  href="/catalog" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Все товары
                </Link>
              </li>
              <li>
                <Link 
                  href="/catalog/fitness" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Фитнес оборудование
                </Link>
              </li>
              <li>
                <Link 
                  href="/catalog/sports" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Спортивный инвентарь
                </Link>
              </li>
              <li>
                <Link 
                  href="/catalog/clothing" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Спортивная одежда
                </Link>
              </li>
            </ul>
          </div>
          
          {/* Для бизнеса */}
          <div>
            <h3 className="font-semibold text-lg mb-4">Для бизнеса</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link 
                  href="/wholesale" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Оптовые продажи
                </Link>
              </li>
              <li>
                <Link 
                  href="/partnership" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Партнерство
                </Link>
              </li>
              <li>
                <Link 
                  href="/training" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Для тренеров
                </Link>
              </li>
              <li>
                <Link 
                  href="/federation" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Для федераций
                </Link>
              </li>
            </ul>
          </div>
          
          {/* Поддержка и информация */}
          <div>
            <h3 className="font-semibold text-lg mb-4">Поддержка</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link 
                  href="/contacts" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Контакты
                </Link>
              </li>
              <li>
                <Link 
                  href="/help" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Помощь
                </Link>
              </li>
              <li>
                <Link 
                  href="/delivery" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Доставка и оплата
                </Link>
              </li>
              <li>
                <Link 
                  href="/returns" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                >
                  Возврат товара
                </Link>
              </li>
            </ul>
          </div>
        </div>
        
        {/* Разделитель */}
        <div className="border-t border-gray-800 mt-8 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            {/* Copyright */}
            <div className="text-gray-400 text-sm mb-4 md:mb-0">
              © {currentYear} FREESPORT Platform. Все права защищены.
            </div>
            
            {/* Социальные сети и ссылки */}
            <div className="flex space-x-6">
              <Link 
                href="/privacy" 
                className="text-gray-400 hover:text-white text-sm transition-colors duration-200"
              >
                Политика конфиденциальности
              </Link>
              <Link 
                href="/terms" 
                className="text-gray-400 hover:text-white text-sm transition-colors duration-200"
              >
                Условия использования
              </Link>
              
              {/* Социальные сети (placeholder) */}
              <div className="flex space-x-4">
                <a 
                  href="#" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                  aria-label="ВКонтакте"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M15.684 0H8.316C1.592 0 0 1.592 0 8.316v7.368C0 22.408 1.592 24 8.316 24h7.368C22.408 24 24 22.408 24 15.684V8.316C24 1.592 22.408 0 15.684 0z"/>
                  </svg>
                </a>
                <a 
                  href="#" 
                  className="text-gray-400 hover:text-white transition-colors duration-200"
                  aria-label="Telegram"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2z"/>
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;