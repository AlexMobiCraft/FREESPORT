# **CLAUDE.md**

Всегда отвечай на русском языке.

Этот файл предоставляет руководство для работы с кодом в этом репозитории.

## **Архитектура проекта**

FREESPORT - API-First E-commerce платформа для B2B/B2C продаж спортивных товаров. Monorepo архитектура с Django REST API backend и Next.js frontend.

### **Технологический стек**

**Backend:**

* Django 5.2.7 + Django REST Framework 3.14+
* **PostgreSQL 15+ (ТОЛЬКО PostgreSQL)** - база данных с поддержкой партиционирования и JSONB
* Redis 7.0+ (кэширование и сессии)
* JWT токены для аутентификации с refresh стратегией
* Celery + Celery Beat (асинхронные задачи и планировщик)
* **drf-spectacular 0.28.0** для спецификации OpenAPI 3.1.0

**ВАЖНО:** Проект разработан исключительно для работы с PostgreSQL и другие СУБД НЕ поддерживаются.

**Frontend:**

* Next.js 15.4.6 + TypeScript 5.0+
* React 19.1.0
* Zustand 4.5.7 (state management)
* Tailwind CSS 4.0
* **React Hook Form 7.62.0** (управление формами)
* **Vitest 2.1.5 + React Testing Library 16.3.0** (тестирование)
* **MSW 2.12.2** (API mocking для тестов)

**Инфраструктура:**

* Среда разработки Windows 11 + Docker Compose (обязательно для разработки и тестирования)
* Nginx (reverse proxy, SSL, load balancing)
* **Docker + Docker Compose (обязательно для разработки и тестирования)**
* **PostgreSQL 15+ в Docker контейнере** с JSONB поддержкой для спецификаций товаров
* **GitHub Actions** (CI/CD)

**КРИТИЧНО:** Все разработка, тестирование и деплой происходят через Docker. Локальная установка БД не поддерживается.

### **Архитектурные принципы**

**API-First + SSR/SSG Approach:**

* Обеспечивает SEO оптимизацию и производительность  
* Независимая разработка frontend и backend  
* Next.js Hybrid Rendering: SSG для статических страниц, SSR для динамических, ISR для каталогов

**BFF (Backend for Frontend) Layer:**

* Next.js API Routes как прослойка для агрегации данных  
* Дополнительная безопасность между клиентом и основным API

**Monorepo Structure:**

* Упрощает управление общими компонентами между брендами
* Централизованная конфигурация и зависимости

### **Структура проекта**

**Корневая директория:**

```
FREESPORT/
├── backend/           # Django REST API
├── frontend/          # Next.js приложение
├── docker/            # Docker конфигурации
├── docs/              # Проектная документация
├── scripts/           # Утилиты и скрипты
├── data/              # Данные для импорта (1С)
├── web-bundles/       # Web компоненты и пакеты
├── .bmad-core/        # BMAD методология
├── .claude/           # Claude AI конфигурация
├── .github/           # GitHub Actions workflows
├── Makefile           # Команды разработки
└── CLAUDE.md          # Это руководство
```

**Frontend структура (src/):**

```
frontend/src/
├── app/               # Next.js App Router
│   ├── (auth)/        # Группа маршрутов авторизации
│   ├── catalog/       # Страницы каталога
│   ├── api/           # API routes (BFF layer)
│   ├── news/          # Список и детали новостей
│   ├── blog/          # Список и детали статей блога
│   └── __tests__/     # Тесты страниц
├── components/        # React компоненты
│   ├── common/        # Общие компоненты
│   ├── layout/        # Layout компоненты
│   ├── home/          # Компоненты главной страницы
│   └── ui/            # UI kit компоненты
├── hooks/             # Custom React hooks
├── services/          # API клиенты и сервисы
├── stores/            # Zustand state management
├── types/             # TypeScript типы
├── utils/             # Утилиты
└── __mocks__/         # Моки для тестов
```

**Документация (docs/):**

```
docs/
├── index.md                    # Главная страница документации
├── PROJECT_PROGRESS.md         # Отслеживание прогресса
├── PRD.md                      # Product Requirements
├── architecture.md             # Архитектура системы
├── api-spec.yaml               # OpenAPI спецификация
├── api-views-documentation.md  # Документация API endpoints
├── stories/                    # User stories по Epic
│   ├── epic-1/  epic-2/  epic-3/  ... epic-26/
├── decisions/                  # Архитектурные решения
├── guides/                     # Руководства
├── qa/                         # Тестирование и QA
└── releases/                   # Релизы
```

### **Структура приложений Django**

Проект использует модульную архитектуру Django apps:

* apps/users/ - пользователи и ролевая система (7 ролей: retail, wholesale_level1-3, trainer, federation_rep, admin)
* apps/products/ - каталог товаров, бренды, категории с многоуровневым ценообразованием
* apps/orders/ - система заказов с поддержкой B2B/B2C процессов
* apps/cart/ - корзина покупок для авторизованных и гостевых пользователей
* apps/common/ - общие утилиты, аудит, управление контентом (новости, блог)
* apps/pages/ - управление динамическими страницами и контентом
* apps/integrations/ - интеграции с внешними системами (1С, платежные системы)

### **Ключевые модели данных**

**User Model:**

* 7 ролей пользователей с разными уровнями ценообразования
* Поддержка B2B полей (company_name, tax_id, verification)
* JWT аутентификация с refresh токенами

**Product Model:**

* Многоуровневое ценообразование (retail_price, opt1_price, opt2_price, opt3_price, trainer_price, federation_price)
* Информационные цены для B2B (RRP, MSRP)
* JSON спецификации товаров в поле specifications
* Интеграция с 1С через onec_id
* Computed properties: is_in_stock, can_be_ordered

**Order/OrderItem Models:**

* Поддержка как B2B, так и B2C заказов  
* Снимок данных о товаре на момент заказа  
* Интеграция с платежными системами (YuKassa)  
* Статусы заказов и аудиторский след

## **Команды разработки и запуска**

### **Docker**

Рекомендуемый способ запуска проекта - через Docker Compose.

**Local Development:**

docker compose --env-file .env -f docker/docker-compose.yml

**Production:**

docker compose --env-file .env.prod -f docker/docker-compose.prod.yml

**ВАЖНО:** Все файлы docker-compose*.yml находятся в директории `docker/`:

* `docker/docker-compose.yml` - основная конфигурация для разработки
* `docker/docker-compose.test.yml` - конфигурация для тестирования
* `docker/docker-compose.prod.yml` - конфигурация для production
* `docker/docker-compose-temp.yml` - временная конфигурация

# Сборка и запуск всех сервисов в фоновом режиме
cd docker && docker compose up -d --build

# ИЛИ из корневой директории:
docker compose --env-file .env -f docker/docker-compose.yml up -d --build

# Остановка и удаление всех сервисов
cd docker && docker compose down

# ИЛИ из корневой директории:
docker compose --env-file .env -f docker/docker-compose.yml down

Будут запущены следующие сервисы:

* db: база данных PostgreSQL
* redis: кэш Redis
* backend: API на Django
* frontend: приложение на Next.js
* nginx: reverse proxy Nginx
* celery: Celery worker для асинхронных задач
* celery-beat: Celery Beat scheduler для периодических задач

### **Локальная разработка**

**Backend (Django)**

⚠️ **ВАЖНО**: Для разработки и тестирования используйте исключительно Docker Compose с PostgreSQL.

cd backend
# Активация виртуального окружения (только для локальной отладки)
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
# Установка зависимостей
pip install -r requirements.txt
# Запуск сервера разработки
python manage.py runserver 8001
# Запуск Celery (в отдельных терминалах)
celery -A freesport worker --loglevel=info
celery -A freesport beat --loglevel=info

**РЕКОМЕНДУЕМЫЙ способ - Docker:**
docker compose up -d --build

### **Важные правила работы с Python и виртуальным окружением**

1. **Всегда проверять активацию виртуального окружения перед запуском Python:**

   * Убедиться, что в терминале отображается `(venv)` или аналогичный индикатор
   * При необходимости активировать окружение командой:
     * Linux/Mac: `source venv/bin/activate`
     * Windows: `venv\\Scripts\\activate`

2. **Обязательно обновлять requirements.txt после установки новых пакетов:**

   ```bash
   # После установки любых новых пакетов через pip install
   pip freeze > requirements.txt
   ```

   * Это обеспечивает синхронизацию зависимостей между разработчиками
   * Позволяет воспроизвести точную среду разработки

**Frontend (Next.js)**

cd frontend
# Установка зависимостей
npm install
# Запуск сервера разработки
npm run dev
# Запуск тестов
npm test
# Запуск тестов с покрытием
npm run test:coverage
# Запуск тестов в режиме наблюдения
npm run test:watch
# Запуск тестов с UI интерфейсом
npm run test:ui

## **Процессы разработки**

### **Git Workflow**

* main - продакшен ветка (защищена)
* develop - основная ветка разработки (защищена)
* feature/* - ветки для новых функций
* hotfix/* - ветки для критических исправлений

### **Стиль кода**

**Backend**

* **Форматирование:** Black  
* **Линтинг:** Flake8  
* **Сортировка импортов:** isort  
* **Проверка типов:** mypy + Pylance (VS Code)

**Frontend**

* **Линтинг:** ESLint 9 + Next.js ESLint config
* **Форматирование:** Prettier 3.3.3
* **Стилизация:** Tailwind CSS 4.0
* **Pre-commit хуки:** Husky 9.1.7 + lint-staged 15.2.10

### **Стратегия тестирования**

Проект следует классической пирамиде тестирования: E2E > Integration > Unit.

**Backend тестирование:**

* **Framework:** Pytest 7.4.3 + pytest-django 4.7.0
* **Coverage:** pytest-cov 4.1.0
* **Factory:** Factory Boy 3.3.0 для генерации тестовых данных
* **Детальные стандарты:** см. документацию в `docs/`

**Frontend тестирование:**

* **Framework:** Vitest 2.1.5 (быстрая альтернатива Jest, совместимая с Vite)
* **UI тестирование:** React Testing Library 16.3.0
* **API mocking:** MSW 2.12.2 (Mock Service Worker)
* **Coverage:** @vitest/coverage-v8 2.1.5
* **UI для тестов:** @vitest/ui 2.1.5

**Основные команды тестирования:**

⚠️ **КРИТИЧЕСКИ ВАЖНО**: Тестирование выполняется ТОЛЬКО с PostgreSQL через Docker Compose!

# Тестирование в Docker (ЕДИНСТВЕННЫЙ поддерживаемый способ)
make test                    # Все тесты с PostgreSQL + Redis
make test-unit               # Только unit-тесты
make test-integration        # Только интеграционные тесты
make test-fast               # Без пересборки образов

# Локальное тестирование через pytest требует настроенного PostgreSQL

**Требования к покрытию:** Общее >= 70%, критические модули >= 90%.

### **Реальные данные из 1С для тестирования**

**КРИТИЧНО:** Для тестирования интеграции с 1С используются ТОЛЬКО реальные данные из production системы 1С.

**Расположение реальных данных:**

```
data/import_1c/
├── contragents/           # XML файлы с реальными контрагентами из 1С (7 файлов)
│   ├── contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml
│   ├── contragents_2_94039c4f-dd9d-48a4-abfa-9ae47b8c2cd1.xml
│   └── ...
├── goods/                 # XML файлы с реальными товарами из 1С
│   ├── goods_1_1_27c08306-a0aa-453b-b436-f9b494ceb889.xml
│   └── import_files/      # Изображения товаров
├── offers/                # Предложения
├── prices/                # Цены
├── rests/                 # Остатки
└── [другие типы]          # units, storages, priceLists и т.д.
```

**Правила использования реальных данных:**

* ❌ **НЕ создавайте** синтетические/тестовые XML данные для тестов импорта из 1С
* ✅ **ВСЕГДА используйте** файлы из `data/import_1c/` для интеграционных тестов
* ✅ **Эти данные содержат** реальную структуру CommerceML 3.1 из production
* ✅ **Включены edge cases:** клиенты без email, разные типы организаций (ООО, ИП, физ.лица), различные форматы данных
* ✅ **Полнота данных:** контрагенты с полными реквизитами, банковскими счетами, адресами

**Примеры команд для тестирования с реальными данными:**

```bash
# Импорт контрагентов из реального файла 1С
cd docker && docker-compose exec backend python manage.py import_customers_from_1c \
  --file=/app/data/import_1c/contragents/contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml

# Dry-run для проверки без сохранения
cd docker && docker-compose exec backend python manage.py import_customers_from_1c \
  --file=/app/data/import_1c/contragents/contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml \
  --dry-run
```

### **Исправления Docker конфигурации (обновлено 23.08.2025)**

**Ключевые исправления:**

 **МИГРАЦИЯ НА PostgreSQL**

* Устранено противоречие БД - теперь везде только PostgreSQL
* Добавлены недостающие сервисы db и redis в docker-compose.test.yml
* Создана nginx конфигурация для основной среды
* Создан оптимизированный Dockerfile.test для тестирования
* Исправлен конфликт портов: Django теперь на порту 8001 вместо 8000
* Добавлен Makefile с удобными командами
* Созданы скрипты автоматизации тестирования

**Новые файлы:**

* docker-compose.test.yml - полная тестовая среда с PostgreSQL и Redis
* backend/Dockerfile.test - оптимизированный образ для тестирования  
* docker/nginx/ - конфигурация Nginx reverse proxy
* Makefile - команды для разработки и тестирования
* scripts/test.* - скрипты запуска тестов для разных ОС

### **Система изоляции тестов (добавлено 23.08.2025)**

**Решенные проблемы:**

* Устранены constraint violations из-за дублирующихся данных в тестах
* Реализована полная изоляция между тестами через autouse фикстуры  
* Создана система генерации абсолютно уникальных данных
* Исправлены интеграционные тесты для работы с изолированными данными

**Ключевые компоненты изоляции:**

* **Автоочистка БД**: `@pytest.fixture(autouse=True)` с TRUNCATE CASCADE перед каждым тестом
* **Уникальные данные**: `get_unique_suffix()` с timestamp + счетчик + UUID
* **Factory Boy правила**: LazyFunction вместо статических значений и Sequence
* **Pytest настройки**: `--create-db --nomigrations` для быстрой изоляции

**Обязательные правила для разработчиков:** см. детальные примеры в `backend/docs/testing-standards.md` разделе 8.5

## **Настройки и конфигурация**

### **Настройки окружения**

* **Настройки Django:** Модульная структура в backend/freesport/settings/ (base.py, development.py, production.py).  
* **Переменные окружения:** Создайте .env файлы на основе .env.example для Backend и Frontend.  
* **Кодировка для Windows:** Backend автоматически настраивает UTF-8 для консоли Windows.

### **Важные файлы конфигурации**

* backend/pytest.ini - настройки тестирования pytest с маркерами
* backend/mypy.ini - статическая типизация
* frontend/package.json - Node.js зависимости
* frontend/vitest.config.mts - настройки Vitest для тестирования
* frontend/tsconfig.json - TypeScript конфигурация
* docker/docker-compose.yml - основная конфигурация Docker
* docker/docker-compose.test.yml - конфигурация Docker для тестирования
* Makefile - команды для разработки, тестирования и документации

## **Интеграции и внешние сервисы**

* **ERP интеграция (1С):** Двусторонний обмен данными (товары, заказы, остатки) через Celery
  * CommerceML 3.1 протокол
  * **Основная команда импорта:** `import_products_from_1c`
    * `python manage.py import_products_from_1c --file-type=all`
    * Поддерживает выборочный импорт: `--file-type=goods` (товары), `--file-type=prices` (цены), `--file-type=rests` (остатки)
  * **Архитектура:**
    * Процессинг: `VariantImportProcessor` (новое поколение)
    * Парсинг: `XMLDataParser`
  * Подробности архитектуры: `docs/architecture/import-architecture.md`
  * Реальные данные для тестирования в `data/import_1c/`
* **Платежные системы:** YuKassa для онлайн платежей
* **Службы доставки:** Интеграция с API CDEK, Boxberry

## **Troubleshooting (Решение типичных проблем)**

### **Docker и контейнеры**

**Проблема: Контейнеры не запускаются или падают**

```bash
# Проверить логи конкретного сервиса
docker compose -f docker/docker-compose.yml logs backend
docker compose -f docker/docker-compose.yml logs db

# Пересоздать контейнеры с нуля
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d --build

# Очистить все неиспользуемые Docker ресурсы
docker system prune -a --volumes
```

**Проблема: Ошибки подключения к PostgreSQL**

```bash
# Проверить статус контейнера БД
docker compose -f docker/docker-compose.yml ps db

# Проверить переменные окружения
docker compose -f docker/docker-compose.yml exec backend env | grep DB

# Подключиться к БД вручную
docker compose -f docker/docker-compose.yml exec db psql -U freesport_user -d freesport_db
```

**Проблема: Конфликт портов**

```bash
# Найти процесс, занимающий порт
# Linux/Mac:
lsof -i :8001
# Windows:
netstat -ano | findstr :8001

# Остановить конфликтующий сервис или изменить порт в docker-compose.yml
```

### **Backend (Django)**

**Проблема: Миграции не применяются**

```bash
# Проверить статус миграций
docker compose -f docker/docker-compose.yml exec backend python manage.py showmigrations

# Применить миграции вручную
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate

# Откатить последнюю миграцию
docker compose -f docker/docker-compose.yml exec backend python manage.py migrate <app_name> <migration_name>

# Создать новую миграцию
docker compose -f docker/docker-compose.yml exec backend python manage.py makemigrations
```

**Проблема: Ошибки импорта из 1С**

```bash
# Включить подробное логирование
docker compose -f docker/docker-compose.yml exec backend python manage.py import_products_from_1c \
  --file-type=goods --verbosity=3

# Проверить структуру XML файла
docker compose -f docker/docker-compose.yml exec backend python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('/app/data/import_1c/goods/goods_1_1.xml')
print(ET.tostring(tree.getroot(), encoding='unicode'))
"
```

**Проблема: Тесты падают с constraint violations**

```bash
# Убедиться, что используется изоляция тестов
# Проверить, что в conftest.py есть autouse fixture для очистки БД

# Запустить тесты с пересозданием БД
make test-clean

# Запустить конкретный тест с подробным выводом
docker compose -f docker/docker-compose.test.yml exec backend \
  pytest -xvs apps/products/tests/test_models.py::TestProductModel::test_create_product
```

### **Frontend (Next.js)**

**Проблема: Ошибки при сборке**

```bash
# Очистить кеш и node_modules
cd frontend
rm -rf node_modules .next
npm install

# Проверить версию Node.js (должна быть >= 18)
node --version

# Запустить сборку с подробным выводом
npm run build -- --debug
```

**Проблема: API запросы возвращают 404/CORS ошибки**

```bash
# Проверить настройки NEXT_PUBLIC_API_URL
cat frontend/.env.local

# Убедиться, что backend запущен и доступен
curl http://localhost:8001/api/v1/health/

# Проверить настройки CORS в Django
docker compose -f docker/docker-compose.yml exec backend python manage.py shell
>>> from django.conf import settings
>>> print(settings.CORS_ALLOWED_ORIGINS)
```

**Проблема: Тесты Vitest не проходят**

```bash
# Запустить тесты с подробным выводом
npm run test -- --reporter=verbose

# Обновить snapshots
npm run test -- -u

# Запустить конкретный тест
npm run test -- src/components/Header.test.tsx
```

### **Redis и Celery**

**Проблема: Celery задачи не выполняются**

```bash
# Проверить статус Celery worker
docker compose -f docker/docker-compose.yml exec celery celery -A freesport inspect active

# Проверить очередь задач
docker compose -f docker/docker-compose.yml exec celery celery -A freesport inspect reserved

# Перезапустить Celery
docker compose -f docker/docker-compose.yml restart celery celery-beat

# Очистить очередь задач
docker compose -f docker/docker-compose.yml exec backend python manage.py shell
>>> from celery import current_app
>>> current_app.control.purge()
```

**Проблема: Redis недоступен**

```bash
# Проверить статус Redis
docker compose -f docker/docker-compose.yml exec redis redis-cli ping

# Проверить подключение из Django
docker compose -f docker/docker-compose.yml exec backend python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> print(cache.get('test'))
```

## **Безопасность и Best Practices**

### **Безопасность Django**

**КРИТИЧНО: Обязательные настройки для production:**

```python
# backend/freesport/settings/production.py

# 1. НИКОГДА не используйте DEBUG=True в production
DEBUG = False

# 2. Установите надежный SECRET_KEY (не храните в коде!)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# 3. Настройте ALLOWED_HOSTS
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# 4. Включите HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 5. Защита от clickjacking
X_FRAME_OPTIONS = 'DENY'

# 6. Защита от XSS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# 7. HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

**Защита от SQL Injection:**

```python
# ✅ ПРАВИЛЬНО - используйте ORM или параметризованные запросы
Product.objects.filter(name=user_input)

# ✅ ПРАВИЛЬНО - параметризованный raw SQL
Product.objects.raw('SELECT * FROM products WHERE name = %s', [user_input])

# ❌ НЕПРАВИЛЬНО - никогда не используйте конкатенацию строк
Product.objects.raw(f'SELECT * FROM products WHERE name = {user_input}')
```

**Защита от XSS (Cross-Site Scripting):**

```python
# Django автоматически экранирует переменные в шаблонах
# ✅ ПРАВИЛЬНО
{{ user_input }}

# ❌ НЕПРАВИЛЬНО - отключает экранирование
{{ user_input|safe }}

# В API всегда валидируйте и sanitize входящие данные
from django.utils.html import escape
safe_data = escape(user_input)
```

**Аутентификация и JWT токены:**

```python
# Используйте короткий срок жизни access токенов
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Всегда валидируйте токены на backend
# Никогда не доверяйте данным из токена без проверки подписи
```

### **Безопасность Next.js**

**Переменные окружения:**

```bash
# ✅ Публичные переменные (доступны в браузере)
NEXT_PUBLIC_API_URL=https://api.example.com

# ✅ Приватные переменные (только на сервере)
DATABASE_URL=postgresql://...
API_SECRET_KEY=...

# ❌ НИКОГДА не добавляйте NEXT_PUBLIC_ к секретам!
```

**Защита API routes:**

```typescript
// app/api/admin/route.ts
import { verifyAuth } from '@/lib/auth';

export async function GET(request: Request) {
  // Всегда проверяйте аутентификацию
  const user = await verifyAuth(request);
  if (!user || user.role !== 'admin') {
    return new Response('Unauthorized', { status: 401 });
  }

  // Ваш код...
}
```

**Content Security Policy (CSP):**

```typescript
// next.config.js
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  }
];
```

### **Работа с секретами**

**❌ НИКОГДА:**

* Не коммитьте .env файлы в Git
* Не храните пароли в коде
* Не логируйте секретные данные
* Не передавайте секреты через URL параметры

**✅ ВСЕГДА:**

* Используйте .env файлы (добавлены в .gitignore)
* Используйте системы управления секретами (AWS Secrets Manager, HashiCorp Vault)
* Ротируйте секреты регулярно
* Используйте разные секреты для разных окружений

```bash
# Создайте .env файлы на основе примеров
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Сгенерируйте надежный SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### **Database Security**

```python
# Используйте connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'sslmode': 'require',  # Требовать SSL в production
        }
    }
}

# Регулярно делайте бэкапы
# Используйте pg_dump для PostgreSQL
docker compose -f docker/docker-compose.yml exec db pg_dump -U freesport_user freesport_db > backup.sql
```

### **Код-ревью чеклист**

**Backend:**
- [ ] Нет SQL injection уязвимостей
- [ ] Нет hardcoded секретов
- [ ] Все эндпоинты требуют аутентификации (где нужно)
- [ ] Валидация входящих данных
- [ ] Правильные permissions на эндпоинтах
- [ ] Логирование security events
- [ ] Тесты на security сценарии

**Frontend:**
- [ ] Нет XSS уязвимостей
- [ ] Санитизация пользовательского ввода
- [ ] CSRF токены для форм
- [ ] Нет секретов в коде
- [ ] Правильная обработка ошибок (без утечки информации)
- [ ] Валидация на клиенте + сервере

## **Production деплоймент**

### **Подготовка к production**

**Чеклист перед деплоем:**

**Backend:**
- [ ] `DEBUG = False` в settings/production.py
- [ ] Настроен надежный `SECRET_KEY`
- [ ] Настроены `ALLOWED_HOSTS`
- [ ] Включены все security headers
- [ ] Настроены SSL сертификаты
- [ ] Настроено логирование (Sentry, CloudWatch)
- [ ] Настроены бэкапы БД
- [ ] Запущены все миграции
- [ ] Собрана статика: `python manage.py collectstatic`
- [ ] Проверены все переменные окружения

**Frontend:**
- [ ] Настроен `NEXT_PUBLIC_API_URL` для production
- [ ] Оптимизированы изображения
- [ ] Настроен CDN для статики
- [ ] Включен compression (gzip/brotli)
- [ ] Настроены SEO метатеги
- [ ] Проверена performance (Lighthouse score)

**Инфраструктура:**
- [ ] Настроен мониторинг (Prometheus, Grafana)
- [ ] Настроены алерты
- [ ] Настроен CI/CD pipeline
- [ ] Настроены health checks
- [ ] Настроен load balancer
- [ ] Настроен firewall
- [ ] Настроен rate limiting

### **Docker Production**

```bash
# Сборка production образов
docker compose -f docker/docker-compose.prod.yml build

# Запуск в production режиме
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d

# Применить миграции
docker compose -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# Собрать статику
docker compose -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Создать суперпользователя
docker compose -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### **Мониторинг и логирование**

**Настройка логирования Django:**

```python
# backend/freesport/settings/production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
```

**Health check эндпоинты:**

```python
# apps/common/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection

@api_view(['GET'])
def health_check(request):
    """Health check для load balancer"""
    try:
        # Проверка БД
        connection.ensure_connection()

        # Проверка Redis
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)

        return Response({'status': 'healthy'})
    except Exception as e:
        return Response({'status': 'unhealthy', 'error': str(e)}, status=503)
```

### **Масштабирование**

**Горизонтальное масштабирование:**

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

**Оптимизация БД:**

```sql
-- Создание индексов для часто используемых запросов
CREATE INDEX idx_products_slug ON products_product(slug);
CREATE INDEX idx_products_category ON products_product(category_id);
CREATE INDEX idx_orders_user ON orders_order(user_id);

-- Анализ производительности запросов
EXPLAIN ANALYZE SELECT * FROM products_product WHERE category_id = 1;
```

**Кеширование:**

```python
# Кеширование на уровне view
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 минут
def product_list(request):
    ...

# Кеширование на уровне queryset
from django.core.cache import cache

def get_featured_products():
    cache_key = 'featured_products'
    products = cache.get(cache_key)

    if products is None:
        products = Product.objects.filter(is_featured=True)[:10]
        cache.set(cache_key, products, 60 * 60)  # 1 час

    return products
```

### **Бэкапы**

```bash
# Создание бэкапа PostgreSQL
docker compose -f docker/docker-compose.prod.yml exec db \
  pg_dump -U freesport_user freesport_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Восстановление из бэкапа
gunzip < backup_20260112.sql.gz | \
  docker compose -f docker/docker-compose.prod.yml exec -T db \
  psql -U freesport_user freesport_db

# Автоматические бэкапы через cron
0 2 * * * /path/to/backup-script.sh
```

## **FAQ (Часто задаваемые вопросы)**

### **Общие вопросы**

**Q: Почему используется только PostgreSQL?**
A: Проект использует специфичные для PostgreSQL возможности: JSONB для хранения спецификаций товаров, партиционирование таблиц, полнотекстовый поиск. Другие БД не поддерживаются.

**Q: Можно ли запустить проект без Docker?**
A: Технически возможно, но не рекомендуется. Docker обеспечивает изоляцию, консистентность окружения и упрощает деплоймент. Все инструкции и CI/CD настроены под Docker.

**Q: Какая версия Python используется?**
A: Python 3.11+. Более старые версии не поддерживаются из-за использования новых возможностей языка.

**Q: Какая версия Node.js нужна?**
A: Node.js 18+ или 20+. Рекомендуется использовать LTS версию.

### **Разработка**

**Q: Как добавить новое приложение Django?**
A:
```bash
# Создать приложение
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py startapp myapp apps/myapp

# Добавить в INSTALLED_APPS в settings/base.py
INSTALLED_APPS = [
    ...
    'apps.myapp',
]

# Создать миграции
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py makemigrations myapp
```

**Q: Как добавить новую зависимость в backend?**
A:
```bash
# Активировать виртуальное окружение
cd backend
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установить пакет
pip install package-name

# Обновить requirements.txt
pip freeze > requirements.txt

# Пересобрать Docker образ
docker compose -f docker/docker-compose.yml build backend
```

**Q: Как добавить новую зависимость в frontend?**
A:
```bash
cd frontend
npm install package-name

# Пересобрать Docker образ
docker compose -f docker/docker-compose.yml build frontend
```

**Q: Как создать новую миграцию Django?**
A:
```bash
# Автоматически создать миграцию на основе изменений в моделях
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py makemigrations

# Создать пустую миграцию для кастомных операций
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py makemigrations --empty myapp

# Посмотреть SQL миграции
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py sqlmigrate myapp 0001
```

### **Тестирование**

**Q: Почему тесты выполняются медленно?**
A: Несколько причин:
- Создание/удаление тестовой БД при каждом запуске
- Медленные фикстуры с большим количеством данных
- Отсутствие `pytest-xdist` для параллельного запуска

Решения:
```bash
# Использовать существующую БД (быстрее, но менее чисто)
make test-fast

# Параллельный запуск тестов
pip install pytest-xdist
pytest -n auto

# Запустить только быстрые тесты
pytest -m "not slow"
```

**Q: Как запустить один конкретный тест?**
A:
```bash
# Backend
docker compose -f docker/docker-compose.test.yml exec backend \
  pytest apps/products/tests/test_models.py::TestProductModel::test_create_product

# Frontend
cd frontend
npm run test -- src/components/Header.test.tsx
```

**Q: Как обновить фикстуры/моки?**
A:
```bash
# Backend (Factory Boy)
# Изменить factories.py в соответствующем приложении

# Frontend (MSW)
# Изменить handlers в src/__mocks__/handlers.ts
```

### **Интеграции**

**Q: Как импортировать данные из 1С?**
A:
```bash
# Импорт всех данных
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py import_products_from_1c --file-type=all

# Импорт только товаров
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py import_products_from_1c --file-type=goods

# Импорт контрагентов
docker compose -f docker/docker-compose.yml exec backend \
  python manage.py import_customers_from_1c \
  --file=/app/data/import_1c/contragents/contragents_1.xml
```

**Q: Как настроить платежную систему YuKassa?**
A:
1. Зарегистрироваться на https://yookassa.ru/
2. Получить shop_id и secret_key
3. Добавить в .env:
```bash
YUKASSA_SHOP_ID=your_shop_id
YUKASSA_SECRET_KEY=your_secret_key
```
4. Настроить webhook URL в личном кабинете YuKassa

**Q: Как настроить интеграцию с CDEK?**
A: См. документацию в `docs/integrations/cdek.md`

### **Production**

**Q: Как выполнить zero-downtime деплоймент?**
A:
1. Использовать blue-green deployment
2. Запустить новые контейнеры параллельно со старыми
3. Переключить load balancer на новые контейнеры
4. Остановить старые контейнеры

```bash
# Docker Swarm / Kubernetes рекомендуются для production
docker stack deploy -c docker-compose.prod.yml freesport
```

**Q: Как мониторить производительность?**
A: Используйте:
- **Backend**: Django Debug Toolbar (dev), Sentry (prod)
- **БД**: pg_stat_statements, pgBadger
- **Infrastructure**: Prometheus + Grafana
- **Логи**: ELK Stack или CloudWatch

**Q: Как обновить версию Django/Next.js?**
A:
1. Прочитать release notes
2. Обновить версию в requirements.txt / package.json
3. Запустить тесты
4. Проверить deprecated warnings
5. Обновить код при необходимости
6. Сделать деплой на staging
7. После проверки - деплой на production

**Q: Как откатить деплоймент?**
A:
```bash
# Откатить к предыдущей версии Docker образа
docker compose -f docker/docker-compose.prod.yml pull
docker compose -f docker/docker-compose.prod.yml up -d

# Откатить миграции Django (ОСТОРОЖНО!)
docker compose -f docker/docker-compose.prod.yml exec backend \
  python manage.py migrate myapp 0042_previous_migration
```

### **Поддержка и контакты**

**Q: Где найти дополнительную документацию?**
A:
- Проектная документация: `docs/` директория
- API документация: `/api/schema/swagger/` (dev сервер)
- Архитектурные решения: `docs/decisions/`

**Q: Как сообщить об ошибке?**
A:
1. Проверить, что ошибка воспроизводится
2. Создать issue в GitHub с:
   - Шагами для воспроизведения
   - Ожидаемым поведением
   - Фактическим поведением
   - Логами и скриншотами
   - Информацией об окружении

**Q: Как предложить улучшение?**
A:
1. Создать feature request в GitHub
2. Описать use case и expected behavior
3. Обсудить с командой
4. После одобрения - создать PR с реализацией

