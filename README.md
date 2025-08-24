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
│   ├── decisions/              # 📋 Архитектурные и технические решения
│   │   ├── README.md           # Индекс всех документов решений
│   │   ├── SUMMARY.md          # Сводка архитектурных принципов
│   │   ├── story-2.1-api-documentation-decisions.md  # OpenAPI 3.1.0
│   │   ├── story-2.2-user-management-api-decisions.md # JWT + роли
│   │   ├── story-2.3-personal-cabinet-api-decisions.md # Дашборд
│   │   ├── story-2.4-catalog-api-decisions.md         # Каталог
│   │   ├── story-2.5-product-detail-api-decisions.md  # Товары
│   │   ├── story-2.6-cart-api-decisions.md            # Корзина
│   │   └── story-2.7-order-api-decisions.md           # Заказы
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
│       ├── 1.9.design-brief.md # Дизайн бриф
│       ├── 2.1.swagger-documentation.md ✅ # API документация
│       ├── 2.2.user-management-api.md ✅   # Пользователи
│       ├── 2.3.personal-cabinet-api.md ✅  # Личный кабинет
│       ├── 2.4.catalog-api.md ✅           # Каталог товаров
│       ├── 2.5.product-detail-api.md ✅    # Детали товара
│       ├── 2.6.cart-api.md ✅              # Корзина
│       └── 2.7.order-api.md ✅             # Заказы
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

### Основная документация
- [Brief](docs/Brief.md) - Обзор проекта
- [PRD](docs/PRD.md) - Технические требования (Product Requirements Document)
- [Architecture](docs/architecture.md) - Архитектурная документация
- [API Specification](docs/api-spec.yaml) - OpenAPI 3.1.0 спецификация
- [Frontend Specification](docs/front-end-spec.md) - Полная UI/UX спецификация FREESPORT
- [User Stories](docs/stories/) - Этапы разработки (1.1-1.9)

### Docker и тестирование
- [Docker Configuration](docs/docker-configuration.md) - Полная документация по Docker настройкам
- [Testing in Docker](docs/testing-docker.md) - Руководство по тестированию в Docker среде

### Архитектурные решения
- **[Индекс решений](docs/decisions/README.md)** - Полный каталог принятых технических решений
- **[Сводка решений](docs/decisions/SUMMARY.md)** - Архитектурные принципы и ключевые решения API Backend
- [Решения по Stories 2.1-2.7](docs/decisions/) - Детальная документация решений для каждой Story

## 🛠️ Разработка

### Рабочий процесс Git

- `main` - продакшен ветка (защищена)
- `develop` - основная ветка разработки (защищена)
- `feature/*` - ветки для новых функций
- `hotfix/*` - ветки для критических исправлений

### Команды разработки

```bash
# Backend локально
cd backend
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows  
python manage.py runserver 8001

# Frontend локально
cd frontend
npm run dev

# Docker (рекомендуется)
docker-compose up -d --build    # Вся платформа
docker-compose down             # Остановка
```

### Тестирование

#### Docker тестирование (рекомендуется)
```bash
# Все тесты в Docker с полной средой
make test

# Специализированные тесты  
make test-unit         # Только unit-тесты
make test-integration  # Только интеграционные тесты
make test-fast         # Быстрые тесты без пересборки

# Скрипты автоматизации
scripts\test.bat       # Windows
./scripts/test.sh      # Linux/macOS
```

#### Локальное тестирование Backend
```bash
cd backend
source venv/bin/activate

# Все тесты (unit + integration)
pytest

# Категорированные тесты
pytest -m unit                    # Unit-тесты
pytest -m integration             # Интеграционные тесты

# Тесты с покрытием кода
pytest --cov=apps --cov-report=html
```

#### Frontend тестирование
```bash
cd frontend
npm test                    # Jest тесты
npm run test:watch         # Watch режим
npm run test:coverage      # С покрытием кода
```

### Make команды (полный список)
```bash
# Разработка
make build          # Собрать Docker образы
make up             # Запустить среду разработки
make down           # Остановить среду
make logs           # Показать логи сервисов
make clean          # Очистить volumes и образы

# Отладка  
make shell          # Shell в backend контейнере
make db-shell       # Подключение к БД
make format         # Форматирование кода
make lint           # Проверка кода
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
- [x] [Story 2.4:](docs/stories/2.4.catalog-api.md) Catalog API ✅ ЗАВЕРШЕНА
- [x] [Story 2.5:](docs/stories/2.5.product-detail-api.md) Product Detail API ✅ ЗАВЕРШЕНА
- [x] [Story 2.6:](docs/stories/2.6.cart-api.md) Cart API ✅ ЗАВЕРШЕНА
- [x] [Story 2.7:](docs/stories/2.7.order-api.md) Order API ✅ ЗАВЕРШЕНА
- [x] [Story 2.8:](docs/stories/2.8.search-api.md) Search API ✅ ЗАВЕРШЕНА
- [ ] [Story 2.9:](docs/stories/2.9.filtering-api.md) Filtering API
- [ ] [Story 2.10:](docs/stories/2.10.pages-api.md) Pages API

## 📞 Контакты

**Команда разработчиков:** FREESPORT Dev Team  
**Руководитель проекта:** Александр Ткаченко  
**Продолжительность:** 28 недель (6 недель до демо)

---

*Создано с ❤️ для спортивного сообщества*