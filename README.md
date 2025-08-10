# FREESPORT Platform

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

```
freesport/
├── backend/                    # Django + DRF API
│   ├── apps/                   # Django приложения
│   │   ├── users/              # Пользователи и роли
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
│   ├── Brief.md                # Техническое задание
│   ├── PRD.md                  # Product Requirements Document
│   ├── architecture.md         # Архитектура системы
│   ├── front-end-spec.md       # Спецификация frontend
│   ├── api-spec.yaml           # OpenAPI спецификация
│   ├── database/               # Схемы БД
│   │   └── er-diagram.md       # ER диаграмма базы данных
│   ├── prd/                    # Детальные требования
│   │   ├── index.md            # Индекс документации PRD
│   │   ├── goals-and-background-context.md  # Цели и контекст
│   │   ├── requirements.md     # Функциональные требования
│   │   ├── technical-assumptions.md  # Технические предположения
│   │   ├── user-interface-design-goals.md  # Цели UI дизайна
│   │   ├── epics-1-28.md       # Эпики разработки
│   │   ├── .md                 # Дополнительная документация
│   │   └── 2.md                # Дополнительная документация
│   └── stories/                # User stories (пошаговые гайды)
│       ├── 1.1.git-setup.md    # Настройка Git
│       ├── 1.2.dev-environment.md  # Среда разработки
│       ├── 1.3.django-structure.md  # Структура Django
│       ├── 1.4.nextjs-structure.md  # Структура Next.js
│       ├── 1.5.cicd-infrastructure.md  # CI/CD инфраструктура
│       ├── 1.6.docker-containers.md  # Docker контейнеры
│       ├── 1.7.testing-environment.md  # Тестовая среда
│       ├── 1.8.database-design.md  # Дизайн базы данных
│       └── 1.9.design-brief.md # Дизайн бриф
├── docker/                     # Docker конфигурации
├── scripts/                    # Automation scripts
├── .github/                    # CI/CD workflows
├── docker-compose.yml          # Docker Compose конфигурация
├── .gitignore                  # Git ignore правила
└── Структура категорий товара.md  # Категории товаров
```

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

### Установка

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd freesport

# 2. Настроить backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Настроить frontend
cd ../frontend
npm install

# 4. Запуск с Docker
cd ..
docker-compose up -d
```

## 🔐 Ролевая система

- **retail** - Розничный покупатель
- **wholesale_level1-3** - Оптовики (3 уровня ценообразования)
- **trainer** - Тренеры (специальные цены)
- **federation_rep** - Представители федераций

## 📚 Документация

- [Architecture](docs/architecture.md) - Архитектурная документация
- [User Stories](docs/stories/) - Epic 1 stories (1.1-1.9)
- [PRD](docs/PRD.md) - Product Requirements Document
- [API Specification](docs/api-spec.yaml) - OpenAPI 3.0.3 спецификация

## 🛠️ Разработка

### Git Workflow

- `main` - продакшен ветка (защищена)
- `develop` - основная ветка разработки (защищена)
- `feature/*` - ветки для новых функций
- `hotfix/*` - ветки для критических исправлений

### Commands

```bash
# Backend
cd backend
python manage.py runserver

# Frontend  
cd frontend
npm run dev

# Tests
# Backend (Django + pytest)
cd backend
source venv/bin/activate
pytest --verbose --cov=apps --cov-report=html

# Frontend (Next.js + Jest)
cd frontend
npm test
npm run test:coverage

# Docker
docker-compose up    # Вся платформа
```

## 📈 Progress Tracking

**Epic 1 (Недели 1-2):**
- [x] [Story 1.1:](docs/stories/1.1.git-setup.md) Настройка Git ✅ ЗАВЕРШЕНА
- [x] [Story 1.2:](docs/stories/1.2.dev-environment.md) Среда разработки ✅ ЗАВЕРШЕНА
- [x] [Story 1.3:](docs/stories/1.3.django-structure.md) Структура Django ✅ ЗАВЕРШЕНА
- [x] [Story 1.4:](docs/stories/1.4.nextjs-structure.md) Структура Next.js ✅ ЗАВЕРШЕНА
- [x] [Story 1.5:](docs/stories/1.5.cicd-infrastructure.md) CI/CD инфраструктура ✅ ЗАВЕРШЕНА
- [x] [Story 1.6:](docs/stories/1.6.docker-containers.md) Docker контейнеры ✅ ЗАВЕРШЕНА
- [x] [Story 1.7:](docs/stories/1.7.testing-environment.md) Тестирование ✅ ЗАВЕРШЕНА
- [x] [Story 1.8:](docs/stories/1.8.database-design.md) База данных ✅ ЗАВЕРШЕНА
- [ ] [Story 1.9:](docs/stories/1.9.design-brief.md) Краткое описание дизайна

## 📞 Контакты

**Development Team:** FREESPORT Dev Team  
**Project Manager:** Владелец проекта  
**Timeline:** 28 недель (6 недель до демо)

---

*Создано с ❤️ для спортивного сообщества*