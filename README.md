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

```
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
│   ├── Brief.md                # Техническое задание
│   ├── PRD.md                  # Product Requirements Document
│   ├── architecture.md         # Архитектура системы
│   ├── front-end-spec.md       # 🎨 UI/UX спецификация FREESPORT
│   ├── api-spec.yaml           # OpenAPI спецификация
│   ├── database/               # Схемы БД
│   │   └── er-diagram.md       # ER диаграмма базы данных
│   ├── prd/                    # Детальные требования
│   │   ├── index.md            # Индекс документации PRD
│   │   ├── goals-and-background-context.md  # Цели и контекст
│   │   ├── requirements.md     # Функциональные требования
│   │   ├── technical-assumptions.md  # Технические предположения
│   │   ├── user-interface-design-goals.md  # Цели UI дизайна
│   │   ├── epics-1-28.md       # Этапы разработки
│   │   ├── .md                 # Дополнительная документация
│   │   └── 2.md                # Дополнительная документация
│   └── stories/                # User stories (пошаговые инструкции)
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
- **trainer** - Тренер/Фитнес-клуб (специальные цены)
- **federation_rep** - Представители федераций

## 📚 Документация

- [Brief](docs/Brief.md) - Обзор проекта
- [PRD](docs/PRD.md) - Технические требования (Product Requirements Document)
- [Architecture](docs/architecture.md) - Архитектурная документация
- [Frontend Specification](docs/front-end-spec.md) - Полная UI/UX спецификация FREESPORT
- [API Specification](docs/api-spec.yaml) - OpenAPI 3.1.0 спецификация
- [User Stories](docs/stories/) - Этапы разработки (1.1-1.9)

### Спецификация фронтенда

Файл [docs/front-end-spec.md](docs/front-end-spec.md) содержит комплексную спецификацию пользовательского интерфейса и опыта для платформы FREESPORT:

**Основные разделы:**

- **Целевые персоны B2B** - оптовики (3 уровня), тренеры, представители федераций
- **Информационная архитектура** - полная карта сайта с навигацией
- **Пользовательские потоки** - процессы верификации и заказов с Mermaid диаграммами
- **Библиотека компонентов** - 25+ TypeScript интерфейсов для UI компонентов
- **Каркасы страниц** - макеты главной, каталога, административной панели
- **Административная панель** - дашборд, модерация заявок, мониторинг интеграции с 1С
- **Дизайн-система** - цветовая палитра, типографика, адаптивность

**Ключевые особенности:**

- Ролевая персонализация контента для разных типов B2B клиентов
- Специализированные компоненты для оптовых продаж
- Детализированный процесс верификации B2B заявок
- Интеграция с архитектурой Django + Next.js
- Circuit Breaker мониторинг для интеграции с 1С

## 🛠️ Разработка

### Рабочий процесс Git

- `main` - продакшен ветка (защищена)
- `develop` - основная ветка разработки (защищена)
- `feature/*` - ветки для новых функций
- `hotfix/*` - ветки для критических исправлений

### Команды

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

## 📈 Отслеживание прогресса

**Этап 1 (Недели 1-2): Фундамент проекта**
- [x] [Story 1.1:](docs/stories/1.1.git-setup.md) Настройка Git ✅ ЗАВЕРШЕНА
- [x] [Story 1.2:](docs/stories/1.2.dev-environment.md) Среда разработки ✅ ЗАВЕРШЕНА
- [x] [Story 1.3:](docs/stories/1.3.django-structure.md) Структура Django ✅ ЗАВЕРШЕНА
- [x] [Story 1.4:](docs/stories/1.4.nextjs-structure.md) Структура Next.js ✅ ЗАВЕРШЕНА
- [x] [Story 1.5:](docs/stories/1.5.cicd-infrastructure.md) CI/CD инфраструктура ✅ ЗАВЕРШЕНА
- [x] [Story 1.6:](docs/stories/1.6.docker-containers.md) Docker контейнеры ✅ ЗАВЕРШЕНА
- [x] [Story 1.7:](docs/stories/1.7.testing-environment.md) Тестирование ✅ ЗАВЕРШЕНА
- [x] [Story 1.8:](docs/stories/1.8.database-design.md) База данных ✅ ЗАВЕРШЕНА
- [x] [Story 1.9:](docs/stories/1.9.design-brief.md) UI/UX спецификация ✅ ЗАВЕРШЕНА

**Этап 2 (Недели 3-4): API Backend**
- [x] [Story 2.1:](docs/stories/2.1.swagger-documentation.md) API Документация (OpenAPI 3.1) ✅ ЗАВЕРШЕНА
- [x] [Story 2.2:](docs/stories/2.2.user-management-api.md) User Management API ✅ ЗАВЕРШЕНА
- [x] [Story 2.3:](docs/stories/2.3.personal-cabinet-api.md) Personal Cabinet API ✅ ЗАВЕРШЕНА
- [ ] [Story 2.4:](docs/stories/2.4.catalog-api.md) Catalog API
- [ ] [Story 2.5:](docs/stories/2.5.product-detail-api.md) Product Detail API
- [ ] [Story 2.6:](docs/stories/2.6.cart-api.md) Cart API
- [ ] [Story 2.7:](docs/stories/2.7.order-api.md) Order API
- [ ] [Story 2.8:](docs/stories/2.8.search-api.md) Search API
- [ ] [Story 2.9:](docs/stories/2.9.filtering-api.md) Filtering API
- [ ] [Story 2.10:](docs/stories/2.10.pages-api.md) Pages API

## 📞 Контакты

**Команда разработчиков:** FREESPORT Dev Team  
**Руководитель проекта:** Александр Ткаченко  
**Продолжительность:** 28 недель (6 недель до демо)

---

*Создано с ❤️ для спортивного сообщества*