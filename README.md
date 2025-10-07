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
│   ├── Brief.md                # Техническое задание
│   ├── PRD.md                  # Product Requirements Document
│   ├── architecture.md         # Архитектура системы
│   ├── front-end-spec.md       # 🎨 UI/UX спецификация FREESPORT
│   ├── docker-configuration.md # Конфигурация Docker
│   ├── testing-docker.md       # Тестирование в Docker
│   ├── api-spec.yaml           # OpenAPI спецификация
│   ├── api-views-documentation.md # 📋 Документация Django Views и API endpoints
│   ├── test-catalog-api.md     # 🧪 Структура и организация тестов API
│   ├── database/               # Схемы БД
│   │   └── er-diagram.md       # ER диаграмма базы данных
│   ├── decisions/              # 📋 Архитектурные и технические решения
│   │   ├── README.md           # Индекс всех документов решений
│   │   ├── SUMMARY.md          # Сводка архитектурных принципов
│   │   ├── story-2.1-api-documentation-decisions.md
│   │   ├── ...
│   │   └── story-2.7-order-api-decisions.md
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
│       ├── epic-1/             # Эпик 1: Фундамент проекта
│       │   ├── 1.1.git-setup.md
│       │   ├── ...
│       │   └── 1.9.design-brief.md
│       ├── epic-2/             # Эпик 2: API Backend
│       │   ├── 2.1.swagger-documentation.md
│       │   ├── ...
│       │   └── 2.10.pages-api.md
│       └── epic-3/             # Эпик 3: Интеграция с 1С
│           ├── 3.1.1.import-products-structure.md
│           ├── ...
│           └── 3.5.2.error-notifications.md
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
- **PostgreSQL 15+** (обязательно - SQLite не поддерживается)
- **Docker & Docker Compose** (обязательно для тестирования)

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
- [API Views Documentation](docs/api-views-documentation.md) - 📋 Подробная документация Django Views и endpoints
- [Test Catalog API](docs/test-catalog-api.md) - 🧪 Структура и организация тестов API
- [User Stories](docs/stories/) - Этапы разработки

### API Views Documentation

Файл [docs/api-views-documentation.md](docs/api-views-documentation.md) содержит подробную техническую документацию всех Django ViewSets и API endpoints:

**Покрытые модули:**

- **Products API** - Каталог товаров, категории, бренды с ролевым ценообразованием
- **Cart API** - Управление корзиной с поддержкой гостевых пользователей
- **Orders API** - Система заказов с транзакционной логикой создания из корзины
- **Users API** - Аутентификация, регистрация, личный кабинет
- **Common API** - Утилиты и мониторинг системы

**Документируемые аспекты:**

- Назначение и цель каждого ViewSet
- Подробное описание методов и их логики
- HTTP endpoints с параметрами и ответами
- Бизнес-правила и валидации
- Особенности безопасности и прав доступа
- Сводная таблица всех API endpoints

### Каталог тестов API

Файл [docs/test-catalog-api.md](docs/test-catalog-api.md) содержит полную структуру организации тестов API платформы:

**Структура тестов:**

- **Unit тесты** - Изолированное тестирование моделей, сериализаторов, утилит
- **Functional тесты** - HTTP API endpoints с полным покрытием всех Stories
- **Integration тесты** - Межмодульные взаимодействия и workflow'ы
- **Performance тесты** - Тестирование производительности критических операций

**Покрытие по модулям:**

- ✅ Users API (аутентификация, личный кабинет)
- ✅ Products API (каталог, категории, бренды)
- ✅ Cart API (корзина, гостевые сессии)
- ✅ Orders API (создание заказов, транзакционная логика)
- 🔄 Search API (готовится)
- 🔄 Filtering API (готовится)

**Инструменты тестирования:**

- pytest + pytest-django для backend тестирования
- APIClient для functional тестирования endpoints
- Fixtures для повторного использования тестовых данных
- Coverage reporting с минимальным порогом 80%

### Спецификация фронтенда

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

## 📈 Прогресс проекта

**Текущий статус:** ✅ Этап 2 - API Backend (100% завершено)

- ✅ **Этап 1:** Фундамент проекта - **ЗАВЕРШЕН** (9/9 stories)
- ✅ **Этап 2:** API Backend - **ЗАВЕРШЕН** (10/10 stories)
- 📋 **Этап 3:** Интеграция с 1С - **ЗАПЛАНИРОВАН** (0/10 stories)

**Детальное отслеживание:** [docs/PROJECT_PROGRESS.md](docs/PROJECT_PROGRESS.md)

### Последние завершения (05.10.2025)

- ✅ **Story 2.8: Search API** - Полностью реализован с PostgreSQL FTS
- ✅ **Story 2.9: Filtering API** - Комплексная фильтрация с ролевым ценообразованием
- ✅ **Story 2.10: Pages API** - Статические страницы с кэшированием и HTML sanitization

### Ближайшие задачи

- 📋 Начало Этапа 3: Интеграция с 1С
- 📋 Story 3.1.1: Импорт структуры товаров

## 📞 Контакты

**Команда разработчиков:** FREESPORT Dev Team  
**Руководитель проекта:** Александр Ткаченко  
**Продолжительность:** 28 недель (6 недель до демо)

---

- *Создано с ❤️ для спортивного сообщества*
