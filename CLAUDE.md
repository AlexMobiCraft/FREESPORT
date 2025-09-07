# **CLAUDE.md**

Этот файл предоставляет руководство для работы с кодом в этом репозитории.

## **Архитектура проекта**

FREESPORT \- API-First E-commerce платформа для B2B/B2C продаж спортивных товаров. Monorepo архитектура с Django REST API backend и Next.js frontend.

### **Технологический стек**

**Backend:**

* Django 4.2 LTS \+ Django REST Framework 3.14+  
* **PostgreSQL 15+ (ТОЛЬКО PostgreSQL)** - база данных с поддержкой партиционирования и JSONB
* Redis 7.0+ (кэширование и сессии)  
* JWT токены для аутентификации с refresh стратегией  
* Celery \+ Celery Beat (асинхронные задачи и планировщик)  
* **drf-spectacular** для спецификации OpenAPI 3.1.0

**ВАЖНО:** Проект разработан исключительно для работы с PostgreSQL. SQLite, MySQL и другие СУБД НЕ поддерживаются.

**Frontend:**

* Next.js 14+ \+ TypeScript 5.0+  
* React 19.1.0  
* Zustand (state management)  
* Tailwind CSS 4.0  
* **React Hook Form** (управление формами)  
* **Jest \+ React Testing Library** (тестирование)

**Инфраструктура:**

* Nginx (reverse proxy, SSL, load balancing)  
* **Docker \+ Docker Compose (обязательно для разработки и тестирования)**
* **PostgreSQL 15+ в Docker контейнере** с JSONB поддержкой для спецификаций товаров  
* **GitHub Actions** (CI/CD)

**КРИТИЧНО:** Все разработка, тестирование и деплой происходят через Docker. Локальная установка БД не поддерживается.

### **Архитектурные принципы**

**API-First \+ SSR/SSG Approach:**

* Обеспечивает SEO оптимизацию и производительность  
* Независимая разработка frontend и backend  
* Next.js Hybrid Rendering: SSG для статических страниц, SSR для динамических, ISR для каталогов

**BFF (Backend for Frontend) Layer:**

* Next.js API Routes как прослойка для агрегации данных  
* Дополнительная безопасность между клиентом и основным API

**Monorepo Structure:**

* Упрощает управление общими компонентами между брендами  
* Централизованная конфигурация и зависимости

### **Структура приложений Django**

Проект использует модульную архитектуру Django apps:

* apps/users/ \- пользователи и ролевая система (7 ролей: retail, wholesale\_level1-3, trainer, federation\_rep, admin)  
* apps/products/ \- каталог товаров, бренды, категории с многоуровневым ценообразованием  
* apps/orders/ \- система заказов с поддержкой B2B/B2C процессов  
* apps/cart/ \- корзина покупок для авторизованных и гостевых пользователей  
* apps/common/ \- общие утилиты, компоненты и аудит

### **Ключевые модели данных**

**User Model:**

* 7 ролей пользователей с разными уровнями ценообразования  
* Поддержка B2B полей (company\_name, tax\_id, verification)  
* JWT аутентификация с refresh токенами

**Product Model:**

* Многоуровневое ценообразование (retail\_price, opt1-3\_price, trainer\_price, federation\_price)  
* Информационные цены для B2B (RRP, MSRP)  
* JSON спецификации товаров в поле specifications  
* Интеграция с 1С через onec\_id  
* Computed properties: is\_in\_stock, can\_be\_ordered

**Order/OrderItem Models:**

* Поддержка как B2B, так и B2C заказов  
* Снимок данных о товаре на момент заказа  
* Интеграция с платежными системами (YuKassa)  
* Статусы заказов и аудиторский след

## **Команды разработки и запуска**

### **Docker**

Рекомендуемый способ запуска проекта \- через Docker Compose.

\# Сборка и запуск всех сервисов в фоновом режиме  
docker-compose up \-d \--build

\# Остановка и удаление всех сервисов  
docker-compose down

Будут запущены следующие сервисы:

* db: база данных PostgreSQL  
* redis: кэш Redis  
* backend: API на Django  
* frontend: приложение на Next.js  
* nginx: reverse proxy Nginx

### **Локальная разработка**

**Backend (Django)**

cd backend  
\# Активация виртуального окружения  
source venv/bin/activate  \# Linux/Mac  
venv\\Scripts\\activate     \# Windows  
\# Установка зависимостей  
pip install \-r requirements.txt  
\# Запуск сервера разработки  
python manage.py runserver 8001  
\# Запуск Celery (в отдельных терминалах)  
celery \-A freesport worker \--loglevel=info  
celery \-A freesport beat \--loglevel=info

### **Важные правила работы с Python и виртуальным окружением**

1. **Всегда проверять активацию виртуального окружения перед запуском Python:**
   - Убедиться, что в терминале отображается `(venv)` или аналогичный индикатор
   - При необходимости активировать окружение командой:
     - Linux/Mac: `source venv/bin/activate`
     - Windows: `venv\\Scripts\\activate`

2. **Обязательно обновлять requirements.txt после установки новых пакетов:**
   ```bash
   # После установки любых новых пакетов через pip install
   pip freeze > requirements.txt
   ```
   - Это обеспечивает синхронизацию зависимостей между разработчиками
   - Позволяет воспроизвести точную среду разработки

**Frontend (Next.js)**

cd frontend  
\# Установка зависимостей  
npm install  
\# Запуск сервера разработки  
npm run dev

## **Процессы разработки**

### **Git Workflow**

* main \- продакшен ветка (защищена)  
* develop \- основная ветка разработки (защищена)  
* feature/\* \- ветки для новых функций  
* hotfix/\* \- ветки для критических исправлений

### **Стиль кода**

**Backend**

* **Форматирование:** Black  
* **Линтинг:** Flake8  
* **Сортировка импортов:** isort  
* **Проверка типов:** mypy

**Frontend**

* **Линтинг:** ESLint  
* **Стилизация:** Tailwind CSS

### **Стратегия тестирования**

Проект следует классической пирамиде тестирования: E2E \> Integration \> Unit.

**Детальные стандарты и правила тестирования:** см. `backend/docs/testing-standards.md`

**Основные команды тестирования:**

\# Тестирование в Docker (рекомендуется)
make test                    \# Все тесты с PostgreSQL + Redis
make test-unit               \# Только unit-тесты  
make test-integration        \# Только интеграционные тесты
make test-fast               \# Без пересборки образов

\# Локально
pytest                       \# Все тесты
pytest \-m unit              \# Unit-тесты
pytest \-m integration       \# Интеграционные тесты
pytest \--cov=apps           \# С покрытием кода

**Требования к покрытию:** Общее \>= 70%, критические модули \>= 90%.

### **Исправления Docker конфигурации (обновлено 23.08.2025)**

**Ключевые исправления:**
- ✅ Устранено противоречие БД между test.py (SQLite) и Docker (PostgreSQL)
- ✅ Добавлены недостающие сервисы db и redis в docker-compose.test.yml
- ✅ Создана nginx конфигурация для основной среды
- ✅ Создан оптимизированный Dockerfile.test для тестирования
- ✅ Исправлен конфликт портов: Django теперь на порту 8001 вместо 8000
- ✅ Добавлен Makefile с удобными командами
- ✅ Созданы скрипты автоматизации тестирования

**Новые файлы:**
- docker-compose.test.yml - полная тестовая среда с PostgreSQL и Redis
- backend/Dockerfile.test - оптимизированный образ для тестирования  
- docker/nginx/ - конфигурация Nginx reverse proxy
- Makefile - команды для разработки и тестирования
- scripts/test.* - скрипты запуска тестов для разных ОС

### **Система изоляции тестов (добавлено 23.08.2025)**

**Решенные проблемы:**
- ✅ Устранены constraint violations из-за дублирующихся данных в тестах
- ✅ Реализована полная изоляция между тестами через autouse фикстуры  
- ✅ Создана система генерации абсолютно уникальных данных
- ✅ Исправлены интеграционные тесты для работы с изолированными данными

**Ключевые компоненты изоляции:**
- **Автоочистка БД**: `@pytest.fixture(autouse=True)` с TRUNCATE CASCADE перед каждым тестом
- **Уникальные данные**: `get_unique_suffix()` с timestamp + счетчик + UUID
- **Factory Boy правила**: LazyFunction вместо статических значений и Sequence
- **Pytest настройки**: `--create-db --nomigrations` для быстрой изоляции

**Обязательные правила для разработчиков:** см. детальные примеры в `backend/docs/testing-standards.md` разделе 8.5

**Результат внедрения:**
- 🚀 100% стабильность тестов без flaky failures
- ⚡ Высокая производительность через оптимизированную очистку
- 🔄 Поддержка параллельного выполнения без конфликтов
- 📊 Улучшение с 49 failed/256 passed до стабильных результатов

## **Настройки и конфигурация**

### **Настройки окружения**

* **Настройки Django:** Модульная структура в backend/freesport/settings/ (base.py, development.py, production.py).  
* **Переменные окружения:** Создайте .env файлы на основе .env.example для Backend и Frontend.  
* **Кодировка для Windows:** Backend автоматически настраивает UTF-8 для консоли Windows.

### **Важные файлы конфигурации**

* backend/pytest.ini \- настройки тестирования pytest с маркерами  
* backend/mypy.ini \- статическая типизация  
* frontend/package.json \- Node.js зависимости  
* frontend/jest.config.js \- настройки Jest  
* docker-compose.yml \- конфигурация Docker

## **Интеграции и внешние сервисы**

* **ERP интеграция (1С):** Двусторонний обмен данными (товары, заказы, остатки) через Celery.  
* **Платежные системы:** YuKassa для онлайн платежей.  
* **Службы доставки:** Интеграция с API CDEK, Boxberry.