/**
 * Компонент Header с навигацией для FREESPORT Platform
 * Поддержка B2B/B2C интерфейсов и аутентификации
 */
"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { authSelectors } from "@/stores/authStore";
import Button from "@/components/ui/Button";

const Header: React.FC = () => {
  const pathname = usePathname();
  const isAuthenticated = authSelectors.useIsAuthenticated();
  const user = authSelectors.useUser();
  const isB2BUser = authSelectors.useIsB2BUser();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Навигационные элементы
  const navigationItems = [
    { href: "/", label: "Главная" },
    { href: "/catalog", label: "Каталог" },
    { href: "/about", label: "О нас" },
    { href: "/contacts", label: "Контакты" },
  ];

  // B2B навигация (дополнительные элементы для бизнес-пользователей)
  const b2bNavigationItems = [
    { href: "/wholesale", label: "Оптовые цены" },
    { href: "/orders", label: "Заказы" },
  ];

  const isActivePage = (href: string) => {
    return pathname === href;
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Логотип */}
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-blue-600">
                FREESPORT
              </span>
              {isB2BUser && (
                <span className="ml-2 px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded-full font-semibold">
                  B2B
                </span>
              )}
            </Link>
          </div>

          {/* Основная навигация (десктоп) */}
          <nav className="hidden md:flex space-x-8">
            {navigationItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-2 text-sm font-medium transition-colors duration-200 ${
                  isActivePage(item.href)
                    ? "text-blue-600 border-b-2 border-blue-600"
                    : "text-gray-700 hover:text-blue-600"
                }`}
              >
                {item.label}
              </Link>
            ))}

            {/* B2B дополнительная навигация */}
            {isB2BUser &&
              b2bNavigationItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 text-sm font-medium transition-colors duration-200 ${
                    isActivePage(item.href)
                      ? "text-orange-600 border-b-2 border-orange-600"
                      : "text-gray-700 hover:text-orange-600"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
          </nav>

          {/* Правая часть - аутентификация и корзина */}
          <div className="flex items-center space-x-4">
            {/* Корзина */}
            <Link
              href="/cart"
              className="p-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 relative"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-1.5 1.5M7 13l1.5 1.5M17 21a2 2 0 100-4 2 2 0 000 4zM9 21a2 2 0 100-4 2 2 0 000 4z"
                />
              </svg>
              {/* TODO: Добавить счетчик товаров в корзине */}
            </Link>

            {/* Авторизация/Профиль */}
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-700">
                  Привет, {user.firstName}!
                </span>
                <Link href="/profile">
                  <Button variant="outline" size="sm">
                    Профиль
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link href="/auth/login">
                  <Button variant="outline" size="sm">
                    Войти
                  </Button>
                </Link>
                <Link href="/auth/register">
                  <Button variant="primary" size="sm">
                    Регистрация
                  </Button>
                </Link>
              </div>
            )}

            {/* Мобильное меню - кнопка */}
            <button
              className="md:hidden p-2 text-gray-600 hover:text-blue-600 transition-colors duration-200"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {isMobileMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Мобильная навигация */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200">
            <nav className="flex flex-col space-y-2">
              {[
                ...navigationItems,
                ...(isB2BUser ? b2bNavigationItems : []),
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block px-3 py-2 text-base font-medium transition-colors duration-200 ${
                    isActivePage(item.href)
                      ? "text-blue-600 bg-blue-50"
                      : "text-gray-700 hover:text-blue-600 hover:bg-gray-50"
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
