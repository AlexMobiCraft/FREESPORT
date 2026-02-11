# FREESPORT Платформа (Legacy)

Этот файл является архивом оригинального README.md проекта.

---

# FREESPORT Платформа

> API-First E-commerce платформа для B2B/B2C продаж спортивных товаров

## 📋 Описание проекта

FREESPORT - современная платформа электронной коммерции, объединяющая 5 торговых марок в единой экосистеме B2B/B2C продаж. Проект реализует полнофункциональный интернет-магазин с акцентом на оптовые продажи для тренеров, спортивных федераций и дистрибьюторов.

## 🏗️ Архитектура

- **Backend:** Django 4.2 LTS + Django REST Framework 3.14+
- **Frontend:** Next.js 14+ + TypeScript 5.0+
- **Database:** PostgreSQL 15+
- **Cache:** Redis 7.0+
- **Authentication:** JWT токены с refresh стратегией

## 📁 Структура проекта (Monorepo)

```text
freesport/
├── backend/                    # Django + DRF API
│   ├── apps/                   # Django приложения
│   │   ├── users/              # Пользователи и роли
│   │   │   ├── views/          # ✅ Модульная структура (Story 2.3)
│   │   │   │   ├── authentication.py  # Регистрация, авторизация
│   │   │   │   ├── profile.py         # Профиль пользователя
│   │   │   │   ├── personal_cabinet.py # Дашборд, адреса, избранное
│   │   │   │   └── misc.py             # Вспомогательные функции
│   │   ├── products/           # Каталог товаров
│   │   ├── orders/             # Система заказов
│   │   ├── cart/               # Корзина покупок
│   │   └── common/             # Общие утилиты и компоненты
│   ├── freesport/              # Django settings
│   ├── static/                 # Статические файлы
│   ├── tests/                  # Тесты backend
│   ├── requirements.txt        # Python зависимости
│   ├── manage.py               # Django CLI
│   ├── Dockerfile              # Docker образ backend
│   ├── pytest.ini             # Настройки тестирования
│   └── .env.example            # Пример переменных окружения
├── frontend/                   # Next.js 14+ SPA
│   ├── src/                    # Исходный код
│   │   ├── app/                # App Router (Next.js 13+)
│   │   ├── components/         # React компоненты
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API сервисы
│   │   ├── stores/             # State management
│   │   ├── types/              # TypeScript типы
│   │   └── utils/              # Утилиты
│   ├── public/                 # Публичные файлы
│   ├── __mocks__/              # Jest моки
│   ├── package.json            # Node.js зависимости
│   ├── tsconfig.json           # TypeScript конфигурация
│   ├── next.config.ts          # Next.js конфигурация
│   ├── jest.config.js          # Jest конфигурация
│   ├── Dockerfile              # Docker образ frontend
│   └── .env.example            # Пример переменных окружения
├── docs/                       # Документация проекта
│   ├── index.md                # 📚 Главная страница документации
│   ├── PROJECT_PROGRESS.md     # 📈 Отслеживание прогресса проекта
... (остальное обрезано для краткости архива)
```
