/**
 * Компонент Header с навигацией для FREESPORT Platform
 * Поддержка B2B/B2C интерфейсов и аутентификации
 * Design System v2.1.0 - сине-голубая цветовая схема
 */
'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Search, Heart, ShoppingCart, Menu, X } from 'lucide-react';
import { authSelectors } from '@/stores/authStore';
import { useCartStore } from '@/stores/cartStore';
import { Button } from '@/components/ui/Button';

const Header: React.FC = () => {
  const pathname = usePathname();
  const isAuthenticated = authSelectors.useIsAuthenticated();
  const user = authSelectors.useUser();
  const isB2BUser = authSelectors.useIsB2BUser();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Получаем количество товаров из корзины
  const cartItemsCount = useCartStore(state => state.totalItems);

  // Навигационные элементы
  const navigationItems = [
    { href: '/', label: 'Главная' },
    { href: '/catalog', label: 'Каталог' },
    { href: '/brands', label: 'Бренды' },
    { href: '/news', label: 'Новости' },
    { href: '/promotions', label: 'Акции' },
  ];

  // B2B навигация (дополнительные элементы для бизнес-пользователей)
  const b2bNavigationItems = [
    { href: '/wholesale', label: 'Оптовые цены' },
    { href: '/orders', label: 'Заказы' },
  ];

  const isActivePage = (href: string) => {
    return pathname === href;
  };

  return (
    <header className="bg-white sticky top-0 z-50 shadow-[0_6px_16px_rgba(31,42,68,0.05)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-[60px]">
          {/* Логотип */}
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center gap-2">
              <Image
                src="/Freesport_logo.svg"
                alt="FREESPORT"
                width={120}
                height={32}
                className="h-8 w-auto"
                priority
              />
              {isB2BUser && (
                <span className="px-2 py-1 text-[10px] bg-accent-danger-bg text-accent-danger rounded-full font-bold">
                  B2B
                </span>
              )}
            </Link>
          </div>

          {/* Основная навигация (десктоп) */}
          <nav aria-label="Основная навигация" className="hidden md:flex items-center gap-6">
            {navigationItems.map(item => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-body-m font-medium transition-colors duration-short ${
                  isActivePage(item.href)
                    ? 'text-text-primary'
                    : 'text-text-primary hover:text-text-secondary'
                }`}
              >
                {item.label}
              </Link>
            ))}

            {/* B2B дополнительная навигация */}
            {isB2BUser &&
              b2bNavigationItems.map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`text-body-m font-medium transition-colors duration-short ${
                    isActivePage(item.href)
                      ? 'text-text-primary'
                      : 'text-text-primary hover:text-text-secondary'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
          </nav>

          {/* Правая часть - иконки действий и аутентификация */}
          <div className="flex items-center gap-4">
            {/* Action Icons (desktop) */}
            <div className="hidden md:flex items-center gap-4">
              {/* Поиск */}
              <button
                aria-label="Поиск"
                className="p-2 text-text-primary hover:text-text-secondary transition-colors duration-short focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-sm"
              >
                <Search className="w-6 h-6" />
              </button>

              {/* Избранное */}
              <Link
                href="/favorites"
                aria-label="Избранное"
                className="p-2 text-text-primary hover:text-text-secondary transition-colors duration-short focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-sm"
              >
                <Heart className="w-6 h-6" />
              </Link>

              {/* Корзина с Badge */}
              <Link
                href="/cart"
                aria-label={`Корзина (${cartItemsCount} товаров)`}
                className="relative p-2 text-text-primary hover:text-text-secondary transition-colors duration-short focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-sm"
              >
                <ShoppingCart className="w-6 h-6" />
                {cartItemsCount > 0 && (
                  <span
                    data-testid="cart-count"
                    className="absolute top-0 right-0 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold bg-accent-danger-bg text-accent-danger rounded-full"
                  >
                    {cartItemsCount > 99 ? '99+' : cartItemsCount}
                  </span>
                )}
              </Link>
            </div>

            {/* Авторизация/Профиль (desktop) */}
            <div className="hidden md:flex items-center gap-2">
              {isAuthenticated && user ? (
                <>
                  <span className="text-body-s text-text-secondary">
                    Привет, {user.first_name}!
                  </span>
                  <Link href="/profile">
                    <Button variant="secondary" size="small">
                      Профиль
                    </Button>
                  </Link>
                </>
              ) : (
                <>
                  <Link href="/auth/register">
                    <Button variant="secondary" size="small">
                      Регистрация
                    </Button>
                  </Link>
                  <Link href="/auth/login">
                    <Button variant="primary" size="small">
                      Войти
                    </Button>
                  </Link>
                </>
              )}
            </div>

            {/* Мобильное меню - кнопка */}
            <button
              className="md:hidden p-2 text-text-primary hover:text-text-secondary transition-colors duration-short focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label={isMobileMenuOpen ? 'Закрыть меню' : 'Открыть меню'}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Мобильная навигация */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-neutral-300">
            <nav aria-label="Мобильная навигация" className="flex flex-col space-y-2">
              {/* Основная навигация */}
              {[...navigationItems, ...(isB2BUser ? b2bNavigationItems : [])].map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block px-3 py-2 text-body-m font-medium rounded-sm transition-colors duration-short ${
                    isActivePage(item.href)
                      ? 'text-text-primary bg-neutral-200'
                      : 'text-text-primary hover:text-text-secondary hover:bg-neutral-200'
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}

              {/* Мобильные иконки действий */}
              <div className="flex items-center gap-4 px-3 py-2 border-t border-neutral-300 mt-2 pt-4">
                <button
                  aria-label="Поиск"
                  className="p-2 text-text-primary hover:text-text-secondary transition-colors"
                >
                  <Search className="w-6 h-6" />
                </button>
                <Link
                  href="/favorites"
                  aria-label="Избранное"
                  className="p-2 text-text-primary hover:text-text-secondary transition-colors"
                >
                  <Heart className="w-6 h-6" />
                </Link>
                <Link
                  href="/cart"
                  aria-label="Корзина"
                  className="relative p-2 text-text-primary hover:text-text-secondary transition-colors"
                >
                  <ShoppingCart className="w-6 h-6" />
                  {cartItemsCount > 0 && (
                    <span
                      data-testid="cart-count"
                      className="absolute top-0 right-0 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold bg-accent-danger-bg text-accent-danger rounded-full"
                    >
                      {cartItemsCount > 99 ? '99+' : cartItemsCount}
                    </span>
                  )}
                </Link>
              </div>

              {/* Авторизация (mobile) */}
              <div className="flex flex-col gap-2 px-3 py-2 border-t border-neutral-300 mt-2 pt-4">
                {isAuthenticated && user ? (
                  <>
                    <span className="text-body-s text-text-secondary mb-2">
                      Привет, {user.first_name}!
                    </span>
                    <Link href="/profile" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="secondary" size="small" className="w-full">
                        Профиль
                      </Button>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link href="/auth/register" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="secondary" size="small" className="w-full">
                        Регистрация
                      </Button>
                    </Link>
                    <Link href="/auth/login" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="primary" size="small" className="w-full">
                        Войти
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
