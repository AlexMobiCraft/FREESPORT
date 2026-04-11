# CLAUDE.md

Всегда отвечай на русском языке.

Руководство по работе с кодом в репозитории FREESPORT.

## Обзор проекта

**FREESPORT** — API-First E-commerce платформа для B2B/B2C продаж спортивных товаров. Monorepo: Django REST API backend + Next.js frontend.

### Технологический стек

- **Backend:** Django 5.2.7 + DRF 3.14+, PostgreSQL 15+, Redis 7.0+, Celery + Celery Beat, JWT (refresh стратегия), drf-spectacular 0.28.0 (OpenAPI 3.1.0)
- **Frontend:** Next.js 15.4.6, React 19.1.0, TypeScript 5.0+, Zustand 4.5.7, Tailwind CSS 4.0, React Hook Form 7.62.0, Vitest 2.1.5 + RTL 16.3.0, MSW 2.12.2
- **Инфраструктура:** Docker Compose (обязательно), Nginx, GitHub Actions

### КРИТИЧНЫЕ правила проекта

1. **Только PostgreSQL.** Другие СУБД НЕ поддерживаются — проект использует JSONB (спецификации товаров), партиционирование, полнотекстовый поиск.
2. **Только Docker.** Вся разработка, тестирование и деплой — через Docker Compose. Локальная установка БД не поддерживается.
3. **Django backend работает на порту 8001** (не 8000 — для избежания конфликтов).
4. **Файлы docker-compose*.yml находятся в `docker/`**, не в корне репозитория.

## Структура проекта

```
FREESPORT/
├── backend/         # Django REST API (порт 8001)
├── frontend/        # Next.js приложение
├── docker/          # docker-compose.yml, docker-compose.test.yml, docker-compose.prod.yml, nginx/
├── docs/            # Проектная документация (см. ниже)
├── data/import_1c/  # РЕАЛЬНЫЕ XML данные из 1С для тестов
├── scripts/         # Утилиты и скрипты
└── Makefile         # Команды разработки и тестирования
```

### Django apps (backend/apps/)

- `users/` — пользователи, **7 ролей**: retail, wholesale_level1-3, trainer, federation_rep, admin
- `products/` — каталог, бренды, категории, многоуровневое ценообразование
- `orders/` — заказы B2B/B2C со снимком данных товара на момент заказа
- `cart/` — корзина (авторизованные + гостевые)
- `common/` — утилиты, аудит, контент (новости, блог)
- `pages/` — динамические страницы
- `integrations/` — 1С, платежные системы

### Ключевые модели

**User:** 7 ролей с разными уровнями ценообразования, B2B поля (`company_name`, `tax_id`, `verification`), JWT с refresh.

**Product:** многоуровневые цены (`retail_price`, `opt1_price`, `opt2_price`, `opt3_price`, `trainer_price`, `federation_price`), информационные цены B2B (`RRP`, `MSRP`), JSONB в `specifications`, интеграция с 1С через `onec_id`, computed: `is_in_stock`, `can_be_ordered`.

**Order/OrderItem:** B2B+B2C, снимок данных товара, YuKassa, аудиторский след.

## Команды разработки

### Docker (основной способ)

```bash
# Запуск всех сервисов (db, redis, backend, frontend, nginx, celery, celery-beat)
docker compose --env-file .env -f docker/docker-compose.yml up -d --build

# Остановка
docker compose --env-file .env -f docker/docker-compose.yml down

# Production
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d
```

### Тестирование (ТОЛЬКО через Docker с PostgreSQL)

```bash
make test                # Все тесты
make test-unit           # Unit тесты
make test-integration    # Интеграционные
make test-fast           # Без пересборки образов
make test-clean          # С пересозданием БД

# Конкретный backend тест
docker compose --env-file .env -f docker/docker-compose.test.yml exec backend \
  pytest -xvs apps/products/tests/test_models.py::TestProductModel::test_create_product

# Frontend
cd frontend && npm run test -- src/components/Header.test.tsx
```

**Покрытие:** общее ≥ 70%, критические модули ≥ 90%.

### Frontend

```bash
cd frontend
npm install
npm run dev              # Dev сервер
npm run test             # Vitest
npm run test:coverage    # С покрытием
npm run test:ui          # UI интерфейс Vitest
```

### Python: виртуальное окружение

- Всегда проверяй индикатор `(venv)` перед запуском `python`/`pip`.
- После `pip install` **обязательно** обновляй `requirements.txt`: `pip freeze > requirements.txt`.

## Изоляция тестов (специфика проекта)

Решены проблемы с constraint violations через:

- **Автоочистка БД:** `@pytest.fixture(autouse=True)` с `TRUNCATE CASCADE` перед каждым тестом.
- **Уникальные данные:** `get_unique_suffix()` (timestamp + счетчик + UUID).
- **Factory Boy:** `LazyFunction` вместо статических значений и `Sequence`.
- **Pytest:** `--create-db --nomigrations` для быстрой изоляции.

Детальные правила: `backend/docs/testing-standards.md` (раздел 8.5).

## Интеграция с 1С (CommerceML 3.1)

### Реальные данные для тестов — КРИТИЧНО

- ❌ **НЕ создавай** синтетические XML для тестов импорта 1С.
- ✅ **Всегда используй** файлы из `data/import_1c/`:
  - `contragents/` — контрагенты (7 файлов, ООО/ИП/физлица, edge cases)
  - `goods/` — товары + `import_files/` изображения
  - `offers/`, `prices/`, `rests/`, `units/`, `storages/`, `priceLists/`

### Команды импорта

```bash
# Товары (выборочно или все)
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py import_products_from_1c --file-type=all
# --file-type: all | goods | prices | rests

# Контрагенты (с --dry-run для проверки)
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py import_customers_from_1c \
  --file=/app/data/import_1c/contragents/contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml
```

**Архитектура импорта:** процессинг — `VariantImportProcessor`, парсинг — `XMLDataParser`. Подробности: `docs/architecture/import-architecture.md`.

## Внешние интеграции

- **1С (ERP):** двусторонний обмен (товары, заказы, остатки) через Celery, CommerceML 3.1 (см. `docs/integrations/`)
- **Платежи:** YuKassa
- **Доставка:** CDEK, Boxberry (см. `docs/integrations/`)

## Git Workflow

- `main` — production (защищена)
- `develop` — основная ветка разработки (защищена, base для PR)
- `feature/*` — новые функции
- `hotfix/*` — критические исправления

## Стиль кода

- **Backend:** Black, Flake8, isort, mypy
- **Frontend:** ESLint 9 + Next.js config, Prettier 3.3.3, Husky 9.1.7 + lint-staged 15.2.10

## Ключевые файлы конфигурации

- `backend/freesport/settings/` — модульная конфигурация (base/development/production)
- `backend/pytest.ini` — маркеры и настройки тестов
- `backend/mypy.ini` — статическая типизация
- `frontend/vitest.config.mts` — настройки Vitest
- `frontend/tsconfig.json` — TypeScript
- `docker/docker-compose*.yml` — Docker конфигурации
- `Makefile` — команды разработки/тестирования

## Документация проекта

Подробности ищи в `docs/`:

- `docs/index.md` — главная документации
- `docs/PRD.md` — Product Requirements
- `docs/architecture.md` — архитектура системы
- `docs/architecture/import-architecture.md` — архитектура импорта 1С
- `docs/api-spec.yaml` — OpenAPI спецификация
- `docs/api-views-documentation.md` — документация API endpoints
- `docs/stories/epic-*/` — user stories по эпикам (epic-1 … epic-26)
- `docs/decisions/` — архитектурные решения
- `docs/guides/` — руководства
- `docs/qa/` — тестирование и QA
- `docs/integrations/` — интеграции (CDEK, YuKassa и др.)
- `backend/docs/testing-standards.md` — стандарты тестирования
- API Swagger UI: `/api/schema/swagger/` (на dev сервере)
