# Структура исходного кода FREESPORT

## Общая структура проекта

```
FREESPORT/
├── backend/                    # Django REST API backend
├── frontend/                   # Next.js frontend приложение
├── docs/                       # Документация проекта
├── docker/                     # Docker конфигурации
├── scripts/                    # Скрипты автоматизации
├── .bmad-core/                 # BMad методология и агенты
├── .claude/                    # Claude AI конфигурации
├── .github/                    # GitHub Actions CI/CD
├── docker-compose.yml          # Основная Docker композиция
├── docker-compose.test.yml     # Тестовая среда
├── Makefile                    # Команды разработки
├── CLAUDE.md                   # Руководство для Claude AI
└── README.md                   # Основная документация
```

## Backend структура (Django)

### Корневая директория backend/
```
backend/
├── apps/                       # Django приложения
│   ├── users/                 # Пользователи и аутентификация
│   ├── products/              # Каталог товаров
│   ├── orders/                # Система заказов
│   ├── cart/                  # Корзина покупок
│   └── common/                # Общие компоненты
├── freesport/                 # Основное Django приложение
│   ├── settings/              # Настройки для разных сред
│   ├── __init__.py
│   ├── asgi.py               # ASGI конфигурация
│   ├── urls.py               # URL маршрутизация
│   └── wsgi.py               # WSGI конфигурация
├── docs/                      # Backend документация
├── media/                     # Загруженные файлы
├── static/                    # Статические файлы
├── staticfiles/               # Собранные статические файлы
├── tests/                     # Интеграционные тесты
├── venv/                      # Виртуальное окружение Python
├── manage.py                  # Django CLI инструмент
├── requirements.txt           # Python зависимости
├── pytest.ini               # Конфигурация pytest
├── mypy.ini                  # Конфигурация mypy
├── Dockerfile                # Docker образ для продакшена
├── Dockerfile.test           # Docker образ для тестирования
└── .env.example              # Пример переменных окружения
```

### Структура Django приложений

#### apps/users/ - Пользователи и ролевая система
```
apps/users/
├── migrations/                # Django миграции
├── views/                     # Разделенные представления
│   ├── __init__.py
│   ├── auth_views.py         # Аутентификация
│   ├── profile_views.py      # Профиль пользователя
│   └── dashboard_views.py    # Дашборд пользователя
├── __init__.py
├── models.py                 # Модели пользователей (7 ролей)
├── serializers.py            # DRF сериализаторы
├── tests.py                  # Unit тесты
├── urls.py                   # URL маршруты
└── views_old.py              # Устаревшие представления
```

**Ключевые модели:**
- `CustomUser` - расширенная модель пользователя
- 7 ролей: retail, wholesale_level1-3, trainer, federation_rep, admin
- B2B поля: company_name, tax_id, verification_status

#### apps/products/ - Каталог товаров
```
apps/products/
├── migrations/               # Django миграции
├── products/                 # Подприложение для логики товаров
│   └── migrations/          # Внутренние миграции
├── __init__.py
├── admin.py                 # Django Admin настройки
├── apps.py                  # Конфигурация приложения
├── filters.py               # django-filter настройки
├── models.py                # Модели товаров, категорий, брендов
├── serializers.py           # DRF сериализаторы
├── urls.py                  # URL маршруты
└── views.py                 # API представления
```

**ВАЖНО:** Тесты для products находятся в `backend/tests/unit/test_models/test_product_models.py`, 
не в `apps/products/tests.py` как указано в некоторых устаревших документах.

**Ключевые модели:**
- `Product` - товары с многоуровневым ценообразованием
- `Category` - категории товаров с иерархией
- `Brand` - бренды товаров
- `ProductSpecification` - JSONB спецификации товаров

#### apps/orders/ - Система заказов
```
apps/orders/
├── migrations/               # Django миграции
├── orders/                   # Подприложение для логики заказов
│   └── migrations/          # Внутренние миграции
├── __init__.py
├── models.py                # Модели заказов и позиций
├── serializers.py           # DRF сериализаторы
├── views.py                 # API представления
└── urls.py                  # URL маршруты
```

**Ключевые модели:**
- `Order` - заказы с поддержкой B2B/B2C
- `OrderItem` - позиции заказа со снимком данных товара
- Интеграция с платежными системами (YuKassa)

#### apps/cart/ - Корзина покупок
```
apps/cart/
├── migrations/               # Django миграции
├── cart/                     # Подприложение для логики корзины
│   └── migrations/          # Внутренние миграции
├── management/               # Django команды управления
│   └── commands/            # Пользовательские команды
├── __init__.py
├── models.py                # Модели корзины
├── serializers.py           # DRF сериализаторы
├── views.py                 # API представления
└── urls.py                  # URL маршруты
```

**Функциональность:**
- Корзина для авторизованных пользователей
- Гостевая корзина через сессии
- Автоматическое применение скидок по ролям

#### apps/common/ - Общие компоненты
```
apps/common/
├── migrations/               # Django миграции
├── common/                   # Подприложение общих компонентов
│   └── migrations/          # Внутренние миграции
├── __init__.py
├── models.py                # Базовые модели (BaseModel, AuditMixin)
├── serializers.py           # Общие сериализаторы
├── utils.py                 # Утилиты и хелперы
├── permissions.py           # Пользовательские разрешения
└── pagination.py            # Пагинация для API
```

### Настройки Django (freesport/settings/)
```
freesport/settings/
├── __init__.py
├── base.py                  # Базовые настройки
├── development.py           # Настройки разработки
├── production.py            # Продакшн настройки
└── test.py                  # Настройки для тестирования
```

### Документация backend (backend/docs/)
```
backend/docs/
├── testing-standards.md     # Стандарты тестирования
├── api-documentation.md     # Документация API
└── deployment-guide.md      # Руководство по деплою
```

## Frontend структура (Next.js)

### Корневая директория frontend/
```
frontend/
├── public/                   # Публичные статические файлы
├── src/                      # Исходный код приложения
├── docs/                     # Frontend документация
├── __mocks__/               # Mock данные для тестов
├── .next/                   # Next.js сборка (генерируется)
├── node_modules/            # npm зависимости
├── .env.example             # Пример переменных окружения
├── Dockerfile               # Docker образ
├── eslint.config.mjs        # ESLint конфигурация
├── jest.config.js           # Jest конфигурация тестов
├── jest.setup.js            # Jest настройки
├── next.config.ts           # Next.js конфигурация
├── next-env.d.ts           # Next.js типы TypeScript
├── package.json             # npm зависимости и скрипты
├── postcss.config.mjs       # PostCSS конфигурация
├── README.md                # Frontend документация
└── tsconfig.json            # TypeScript конфигурация
```

### Структура исходного кода (src/)
```
src/
├── app/                     # Next.js App Router
│   ├── (auth)/             # Группа маршрутов аутентификации
│   ├── (dashboard)/        # Группа маршрутов дашборда
│   ├── api/                # Next.js API Routes (BFF слой)
│   ├── globals.css         # Глобальные стили
│   ├── layout.tsx          # Корневой layout
│   ├── page.tsx            # Главная страница
│   └── loading.tsx         # Loading UI компонент
├── components/              # Переиспользуемые React компоненты
│   ├── ui/                 # Базовые UI компоненты
│   ├── forms/              # Формы приложения
│   ├── layout/             # Layout компоненты
│   └── features/           # Feature-specific компоненты
├── hooks/                   # Кастомные React хуки
│   ├── useAuth.ts          # Хук аутентификации
│   ├── useCart.ts          # Хук корзины
│   └── useApi.ts           # Хук для API запросов
├── services/                # API клиенты и бизнес-логика
│   ├── api/                # API клиенты
│   ├── auth/               # Сервисы аутентификации
│   └── utils/              # Утилиты сервисов
├── stores/                  # Zustand stores
│   ├── authStore.ts        # Store аутентификации
│   ├── cartStore.ts        # Store корзины
│   └── productStore.ts     # Store товаров
├── types/                   # TypeScript определения типов
│   ├── auth.ts             # Типы аутентификации
│   ├── product.ts          # Типы товаров
│   └── api.ts              # API типы
└── utils/                   # Утилиты и хелперы
    ├── constants.ts         # Константы приложения
    ├── formatters.ts        # Форматирование данных
    └── validators.ts        # Валидация данных
```

### Next.js App Router структура (src/app/)
```
src/app/
├── (auth)/                  # Группа аутентификации
│   ├── login/
│   │   └── page.tsx        # Страница входа
│   ├── register/
│   │   └── page.tsx        # Страница регистрации
│   └── layout.tsx          # Layout для аутентификации
├── (dashboard)/             # Группа дашборда
│   ├── profile/
│   │   └── page.tsx        # Профиль пользователя
│   ├── orders/
│   │   └── page.tsx        # История заказов
│   └── layout.tsx          # Layout для дашборда
├── api/                     # BFF API Routes
│   ├── auth/
│   │   └── route.ts        # Эндпоинты аутентификации
│   ├── products/
│   │   └── route.ts        # Эндпоинты товаров
│   └── cart/
│       └── route.ts        # Эндпоинты корзины
├── products/                # Каталог товаров
│   ├── [slug]/
│   │   └── page.tsx        # Страница товара (SSG)
│   └── page.tsx            # Список товаров (ISR)
├── cart/
│   └── page.tsx            # Страница корзины
├── globals.css             # Глобальные стили Tailwind
├── layout.tsx              # Корневой layout
├── page.tsx                # Главная страница
├── loading.tsx             # Глобальный loading
├── error.tsx               # Глобальная обработка ошибок
└── not-found.tsx           # Страница 404
```

### Компоненты (src/components/)
```
src/components/
├── ui/                      # Базовые UI компоненты
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
│   ├── Input/
│   │   ├── Input.tsx
│   │   ├── Input.test.tsx
│   │   └── index.ts
│   └── Modal/
│       ├── Modal.tsx
│       ├── Modal.test.tsx
│       └── index.ts
├── forms/                   # Формы приложения
│   ├── LoginForm/
│   ├── RegisterForm/
│   └── CheckoutForm/
├── layout/                  # Layout компоненты
│   ├── Header/
│   ├── Footer/
│   ├── Sidebar/
│   └── Navigation/
└── features/                # Feature-specific компоненты
    ├── ProductCard/
    ├── CartWidget/
    └── UserProfile/
```

## Документация (docs/)

### Структура документации
```
docs/
├── architecture/            # Архитектурная документация
│   ├── coding-standards.md  # Стандарты кодирования (создан)
│   ├── tech-stack.md        # Технологический стек (создан)
│   └── source-tree.md       # Структура кода (этот файл)
├── prd/                     # Product Requirements Documents
├── stories/                 # User Stories для разработки
├── qa/                      # QA документация и отчеты
├── database/                # Схемы и документация БД
├── decisions/               # Архитектурные решения (ADR)
├── api-spec.yaml           # OpenAPI спецификация
├── architecture.md         # Общая архитектура
├── PRD.md                  # Основной PRD
├── Brief.md                # Бриф проекта
├── front-end-spec.md       # Спецификация фронтенда
├── testing-docker.md       # Тестирование в Docker
└── docker-configuration.md # Конфигурация Docker
```

## Инфраструктура

### Docker конфигурации (docker/)
```
docker/
├── nginx/                   # Nginx конфигурации
│   ├── nginx.conf          # Основная конфигурация
│   └── default.conf        # Default виртуальный хост
└── postgres/                # PostgreSQL настройки
    └── init.sql            # Инициализация БД
```


```
scripts/
├── test.sh                 # Скрипт запуска тестов (Linux/Mac)
├── test.bat                # Скрипт запуска тестов (Windows)
├── setup.sh                # Настройка среды разработки
└── deploy.sh               # Скрипт деплоя
```

### GitHub Actions (.github/workflows/)
```
.github/workflows/
├── ci.yml                  # Continuous Integration
├── cd.yml                  # Continuous Deployment
├── test.yml                # Запуск тестов
└── security.yml            # Проверки безопасности
```

## BMad методология (.bmad-core/)

### Структура BMad агентов и процессов
```
.bmad-core/
├── agents/                  # BMad агенты
│   ├── dev.md              # Агент разработчика
│   ├── qa.md               # Агент тестировщика
│   ├── pm.md               # Агент проект-менеджера
│   └── architect.md        # Агент архитектора
├── tasks/                   # Задачи агентов
├── templates/               # Шаблоны документов
├── checklists/             # Чек-листы процессов
├── data/                   # Данные методологии
├── utils/                  # Утилиты BMad
└── workflows/              # Рабочие процессы
```

## Файловые соглашения

### Именование файлов

#### Backend (Python/Django)
- **Модели**: `models.py` (snake_case для классов)
- **Представления**: `views.py` или разделение в `views/`
- **Сериализаторы**: `serializers.py`
- **URL маршруты**: `urls.py`
- **Тесты**: `tests.py` или `test_*.py`
- **Миграции**: автоматическое именование Django

#### Frontend (TypeScript/React)
- **Компоненты**: `ComponentName.tsx` (PascalCase)
- **Хуки**: `useHookName.ts` (camelCase с префиксом use)
- **Stores**: `storeNameStore.ts` (camelCase с суффиксом Store)
- **Типы**: `typeName.ts` (camelCase)
- **Утилиты**: `utilityName.ts` (camelCase)
- **Тесты**: `ComponentName.test.tsx`

### Структура файлов компонентов

#### Простой компонент
```
ComponentName/
├── ComponentName.tsx        # Основной компонент
├── ComponentName.test.tsx   # Тесты
├── ComponentName.module.css # Стили (если нужны)
└── index.ts                # Экспорты
```

#### Сложный компонент
```
ComponentName/
├── ComponentName.tsx        # Основной компонент
├── ComponentName.test.tsx   # Тесты
├── hooks/                  # Специфичные хуки
├── types.ts               # Локальные типы
├── utils.ts               # Локальные утилиты
└── index.ts               # Экспорты
```

## Соглашения по импортам

### Backend импорты (Python)
```python
# 1. Стандартная библиотека
import json
import logging
from datetime import datetime

# 2. Сторонние пакеты
import requests
from django.db import models
from rest_framework import serializers

# 3. Локальные импорты
from apps.common.models import BaseModel
from .utils import helper_function
```

### Frontend импорты (TypeScript)
```typescript
// 1. React и Next.js
import React from 'react';
import { NextPage } from 'next';

// 2. Сторонние библиотеки
import axios from 'axios';

// 3. Внутренние импорты (абсолютные пути)
import { Button } from '@/components/ui';
import { useAuth } from '@/hooks';
import { ProductType } from '@/types';

// 4. Относительные импорты
import { LocalComponent } from './LocalComponent';
```

## Настройки среды разработки

### Обязательные файлы конфигурации
- **backend/.env** - переменные окружения Django
- **frontend/.env.local** - переменные окружения Next.js
- **docker-compose.override.yml** - локальные Docker настройки
- **.vscode/settings.json** - настройки VS Code
- **.gitignore** - исключения Git

### Рекомендуемые расширения VS Code
- Python (для Django)
- TypeScript и JavaScript (для Next.js)
- ESLint и Prettier (форматирование)
- Docker (контейнеризация)
- GitLens (Git интеграция)

Эта структура обеспечивает:
- 📁 **Четкое разделение** backend и frontend кода
- 🔧 **Модульность** Django приложений
- 🎯 **Масштабируемость** через компонентный подход
- 🧪 **Тестируемость** через изолированные модули
- 📖 **Maintainability** через понятную структуру директорий