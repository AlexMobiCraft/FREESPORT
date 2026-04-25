# FREESPORT Brownfield Architecture Document

## Введение

Этот документ описывает РЕАЛЬНОЕ ТЕКУЩЕЕ СОСТОЯНИЕ кодовой базы FREESPORT, включая технический долг, обходные пути и фактические паттерны реализации. Он служит справочным материалом для AI агентов, работающих над улучшениями системы.

### Масштаб документа

**Комплексная документация всей системы** - данный документ покрывает всю платформу E-commerce с акцентом на B2B функционал согласно PRD.

### История изменений

| Дата       | Версия | Описание                    | Автор       |
| ---------- | ------ | --------------------------- | ----------- |
| 2025-09-06 | 1.0    | Начальный brownfield анализ | BMad Master |

## Быстрая справка - Ключевые файлы и точки входа

### Критические файлы для понимания системы

**Backend (Django):**

- **Главная точка входа**: `backend/manage.py`
- **Настройки конфигурации**: `backend/freesport/settings/` (base.py, development.py, production.py)
- **URL маршрутизация**: `backend/freesport/urls.py`
- **Модели пользователей**: `backend/apps/users/models.py` (7 ролей + B2B поля)
- **Модели товаров**: `backend/apps/products/models.py` (роле-ориентированное ценообразование)
- **Модели заказов**: `backend/apps/orders/models.py` (B2B/B2C заказы)
- **API документация**: Swagger UI на `/api/docs/`

**Frontend (Next.js):**

- **Главная точка входа**: `frontend/src/app/page.tsx`
- **Конфигурация**: `frontend/next.config.ts`
- **App Router**: `frontend/src/app/` (файловая маршрутизация)
- **Компоненты**: `frontend/src/components/`
- **State Management**: `frontend/src/stores/` (Zustand)
- **API клиенты**: `frontend/src/services/`

**Docker и инфраструктура:**

- **Основная композиция**: `docker-compose.yml`
- **Тестовая среда**: `docker-compose.test.yml`
- **Команды разработки**: `Makefile`

### Анализ воздействия планируемых улучшений

Основано на PRD документе - система активно развивается для достижения целей **Эпика 1-8** (28 недель разработки).

**Файлы/модули, подверженные изменениям:**

- `backend/apps/users/` - расширение B2B функционала
- `backend/apps/products/` - интеграция с 1С для каталога
- `backend/apps/orders/` - процесс оформления заказов B2B/B2C
- `frontend/src/app/` - страницы каталога и личного кабинета

## Высокоуровневая архитектура

### Техническая сводка

**Архитектурный подход:** API-First с разделением на независимые backend (Django REST) и frontend (Next.js)

**Состояние реализации:**

- ✅ **Эпик 1 (ЗАВЕРШЕН)** - Фундамент проекта и БД
- ✅ **Эпик 2 (ЗАВЕРШЕН)** - Упрощенный API
- 🔄 **Эпик 3 (В ПРОЦЕССЕ)** - Загрузка тестовых данных
- ⏳ **Эпики 4-8** - Планируются к реализации

### Реальный технологический стек (из файлов зависимостей)

#### Backend Stack

| Категория        | Технология            | Версия | Примечания                    |
| ---------------- | --------------------- | ------ | ----------------------------- |
| Runtime          | Python                | 3.11+  | Используется в Docker         |
| Framework        | Django                | 4.2.16 | LTS версия, стабильная основа |
| API Framework    | Django REST Framework | 3.14.0 | Для REST API                  |
| База данных      | PostgreSQL            | 15+    | Во всех средах через Docker   |
| Кэширование      | Redis                 | 7.0+   | Для Celery и кэширования      |
| Аутентификация   | SimpleJWT             | 5.3.1  | JWT токены с refresh          |
| API документация | drf-spectacular       | 0.28.0 | OpenAPI 3.1.0 спецификация    |
| Тестирование     | pytest                | 7.4.3  | + pytest-django, pytest-cov   |
| Качество кода    | black, flake8, mypy   | latest | Автоматическое форматирование |

#### Frontend Stack

| Категория        | Технология      | Версия | Примечания                    |
| ---------------- | --------------- | ------ | ----------------------------- |
| Framework        | Next.js         | 15.4.6 | App Router, Turbopack для dev |
| UI Library       | React           | 19.1.0 | Современная версия            |
| TypeScript       | TypeScript      | 5.0+   | Строгая типизация             |
| State Management | Zustand         | 4.5.7  | Легковесное решение           |
| HTTP Client      | Axios           | 1.11.0 | API запросы                   |
| Forms            | React Hook Form | 7.62.0 | Производительные формы        |
| Стилизация       | Tailwind CSS    | 4.0    | Utility-first                 |
| Тестирование     | Jest            | 29.7.0 | + Testing Library             |

### Структура репозитория (Реальность)

- **Тип**: Monorepo с физическим разделением backend/frontend
- **Менеджер пакетов**: pip для backend, npm для frontend
- **Особенности**: .bmad-core/ для AI-агентов, .claude/ для конфигурации

## Структура исходного кода и организация модулей

### Структура проекта (Фактическая)

```text
FREESPORT/
├── backend/                    # Django REST API (основная логика)
│   ├── apps/                  # Django приложения (модульная архитектура)
│   │   ├── users/             # Пользователи с 7 ролями + B2B
│   │   ├── products/          # Каталог товаров с ценообразованием
│   │   ├── orders/            # Система заказов B2B/B2C
│   │   ├── cart/              # Корзина (авторизованные + гостевые)
│   │   ├── pages/             # API информационных страниц
│   │   └── common/            # Общие компоненты, BaseModel
│   ├── freesport/             # Основное Django приложение
│   │   └── settings/          # Настройки для разных сред
│   ├── tests/                 # Интеграционные тесты
│   ├── requirements.txt       # Python зависимости (69 пакетов)
│   └── db.sqlite3            # Исторический артефакт (не используется)
├── frontend/                   # Next.js приложение
│   ├── src/
│   │   ├── app/              # Next.js App Router (файловая маршрутизация)
│   │   ├── components/       # React компоненты
│   │   ├── stores/           # Zustand state management
│   │   ├── services/         # API клиенты
│   │   └── types/            # TypeScript определения
│   └── package.json          # npm зависимости
├── docs/                      # Обширная документация (124 файла, 1.2MB)
│   ├── architecture/         # 42 файла архитектурной документации
│   ├── stories/              # User Stories для разработки
│   └── PRD.md               # Product Requirements Document
├── .bmad-core/               # BMad методология для AI агентов
├── docker-compose.yml        # Основная Docker композиция
├── codebase.xml             # Сгенерированная структура (2.8MB)
└── codebase.stats.md        # Статистика кодовой базы
```

### Ключевые модули и их назначение

#### Backend модули

**apps/users/ - Пользователи и ролевая система**

- `models.py` - CustomUser с email аутентификацией
- 7 ролей: retail, wholesale_level1-3, trainer, federation_rep, admin
- B2B поля: company_name, tax_id, verification_status
- Проблемы: Временные заглушки в dashboard API (см. TODO_TEMPORARY_FIXES.md)

**apps/products/ - Каталог товаров**

- `models.py` - Brand, Category, Product с иерархией
- Многоуровневое ценообразование (6 типов цен по ролям)
- JSONB спецификации товаров для гибкости
- Интеграция с 1С через onec_id

**apps/orders/ - Система заказов**

- Поддержка B2B и B2C процессов
- OrderItem со снимком данных товара на момент заказа
- Интеграция с YuKassa для платежей
- ИСПРАВЛЕНО: Заглушки в Personal Cabinet API удалены

**apps/cart/ - Корзина покупок**

- Авторизованные пользователи (в БД)
- Гостевые пользователи (через сессии)
- Автоматическое применение скидок по ролям

#### Frontend модули

**src/app/ - Next.js App Router**

- Файловая маршрутизация
- BFF слой через API Routes
- SSG для товаров, ISR для каталога

**src/components/ - Компоненты**

- Модульная структура ui/forms/features/
- TypeScript типизация
- Testing Library тесты

## Модели данных и API

### Модели данных

Вместо дублирования, ссылки на фактические файлы модели:

**Модели пользователей**: См. `backend/apps/users/models.py`

- CustomUser с UserManager для email аутентификации
- 7 ролей с роле-ориентированным ценообразованием
- B2B поля для компаний

**Модели товаров**: См. `backend/apps/products/models.py`

- Brand, Category (иерархические), Product
- 6 типов цен: retail_price, opt1-3_price, trainer_price, federation_price
- RRP/MSRP информационные цены для B2B

**Модели заказов**: См. `backend/apps/orders/models.py`

- Order с поддержкой B2B/B2C
- OrderItem со снимком данных товара
- Computed properties: total_items, calculated_total

### API спецификации

- **OpenAPI Spec**: Доступна на `/api/docs/` через drf-spectacular
- **REST API**: Полностью реализованное API согласно DRF конвенциям
- **Версионирование**: Пока не реализовано

## Технический долг и известные проблемы

### Критический технический долг

1. **База данных для разработки**: использование PostgreSQL обязательно
   - **Файл**: `backend/freesport/settings/development.py`
   - **Статус**: Настройки переключены на PostgreSQL
   - **Примечание**: Старый `db.sqlite3` сохранён для истории, но не применяется

2. **Временные заглушки удалены**: ✅ **ИСПРАВЛЕНО**
   - **Статус**: TODO_TEMPORARY_FIXES.md показывает, что Order модель реализована
   - **Готово к интеграции**: Dashboard API может использовать реальные данные

3. **Отсутствие frontend реализации**
   - **Статус**: Эпики 4 и 7 (B2B/B2C интерфейсы) еще не реализованы
   - **Структура**: Подготовлена, но компоненты не созданы

### Обходные пути и особенности

- **Переменные окружения**: .env файлы требуют ручной настройки
- **Кодировка Windows**: Backend автоматически настраивает UTF-8 консоль
- **CORS настройки**: Разрешен только localhost:3000 для разработки
- **Debug режим**: Включен только в development.py

## Точки интеграции и внешние зависимости

### Внешние сервисы

| Сервис  | Назначение | Тип интеграции | Ключевые файлы    |
| ------- | ---------- | -------------- | ----------------- |
| 1С      | ERP        | Планируется    | Эпик 5 (4 недели) |
| YuKassa | Платежи    | Планируется    | Эпик 7 (B2C)      |
| CDEK    | Доставка   | Планируется    | Будущие эпики     |

### Внутренние точки интеграции

- **Backend-Frontend**: REST API на порту 8001 (изменен с 8000)
- **База данных**: PostgreSQL во всех средах (Docker Compose)
- **Кэширование**: Redis для Celery и Django cache framework

## Разработка и развертывание

### Локальная настройка разработки

**Актуальные шаги (работающие):**

1. Активация venv: `backend/venv/Scripts/activate` (Windows)
2. Установка зависимостей: `pip install -r requirements.txt`
3. Запуск Django: `python manage.py runserver 8001` (НЕ 8000!)
4. Frontend: `cd frontend && npm install && npm run dev`

**Docker способ (рекомендуемый):**

1. `docker-compose up -d --build`
2. Все сервисы запускаются автоматически

### Процесс сборки и развертывания

- **Команда сборки**: `docker-compose build`
- **Развертывание**: Через Docker Compose
- **Окружения**: development.py, production.py настройки
- **CI/CD**: GitHub Actions настроены (.github/workflows/)

## Реальное состояние тестирования

### Текущее покрытие тестами

- **Система тестирования**: pytest с полной изоляцией
- **База для тестов**: PostgreSQL через Docker
- **Конфигурация**: `backend/pytest.ini`
- **Команды**: `make test`, `pytest`, Docker тесты

**Исправления тестирования (23.08.2025):**

- ✅ Устранена проблема изоляции тестов
- ✅ Уникальные данные через get_unique_suffix()
- ✅ Автоочистка БД через autouse фикстуры
- ✅ 100% стабильность без flaky failures

### Запуск тестов

```bash
# Рекомендуемый способ (Docker)
make test                    # Все тесты с PostgreSQL + Redis
make test-unit               # Unit тесты
make test-integration        # Интеграционные тесты

# Локально
pytest                       # Все тесты
pytest -m unit              # Unit тесты
pytest --cov=apps           # С покрытием кода
```

## Анализ воздействия PRD улучшений

### Файлы, требующие модификации

На основе анализа PRD эпиков 1-8:

**Backend изменения:**

- `backend/apps/users/views.py` - интеграция реальных данных dashboard
- `backend/apps/products/` - интеграция с 1С (Эпик 5)
- `backend/apps/orders/` - процесс checkout (Эпик 2, завершен)

**Frontend создание:**

- `frontend/src/app/` - все основные страницы (Эпики 4, 7)
- `frontend/src/components/` - UI компоненты
- Мобильная адаптивность для всех страниц

### Новые модули, необходимые для реализации

**Интеграция с 1С:**

- Celery задачи для синхронизации
- API endpoints для обмена данными
- Модели для отслеживания синхронизации

**Платежная интеграция:**

- YuKassa API клиент
- Webhook обработчики
- Модели платежных транзакций

### Рекомендации по интеграции

- Следовать существующим паттернам Django apps
- Использовать drf-spectacular для API документации
- Применять established testing patterns с изоляцией
- Интегрироваться с существующей ролевой системой

## Приложение - Полезные команды и скрипты

### Часто используемые команды

**Backend:**

```bash
# Активация окружения (Windows)
backend/venv/Scripts/activate

# Django команды
python manage.py runserver 8001  # НЕ 8000!
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser

# Тестирование
pytest
pytest --cov=apps
make test
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev          # Разработка с Turbopack
npm run build        # Продакшн сборка
npm run test         # Jest тесты
```

**Docker:**

```bash
docker-compose up -d --build    # Сборка и запуск
docker-compose down             # Остановка
make test                       # Тесты в Docker
```

### Отладка и решение проблем

- **Логи Django**: Консоль в development режиме
- **Debug режим**: Django Debug Toolbar на `/__debug__/`
- **Database**: Админка Django `/admin/`
- **API документация**: `/api/docs/` (Swagger UI)
- **Общие проблемы**: См. существующие GitHub Issues

---

**Примечание**: Этот brownfield документ отражает реальное состояние системы на 06.09.2025. Для актуальных изменений проверяйте git commits и обновляйте документ соответствующим образом.
