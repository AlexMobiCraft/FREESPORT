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

* Многоуровневое ценообразование (retail\_price, opt1\_price, opt2\_price, opt3\_price, trainer\_price, federation\_price)  
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

**ВАЖНО:** Все файлы docker-compose*.yml находятся в директории `docker/`:
- `docker/docker-compose.yml` - основная конфигурация для разработки
- `docker/docker-compose.test.yml` - конфигурация для тестирования
- `docker/docker-compose.prod.yml` - конфигурация для production
- `docker/docker-compose-temp.yml` - временная конфигурация

\# Сборка и запуск всех сервисов в фоновом режиме
cd docker && docker-compose up \-d \--build

\# ИЛИ из корневой директории:
docker-compose -f docker/docker-compose.yml up -d --build

\# Остановка и удаление всех сервисов
cd docker && docker-compose down

\# ИЛИ из корневой директории:
docker-compose -f docker/docker-compose.yml down

Будут запущены следующие сервисы:

* db: база данных PostgreSQL  
* redis: кэш Redis  
* backend: API на Django  
* frontend: приложение на Next.js  
* nginx: reverse proxy Nginx

### **Локальная разработка**

**Backend (Django)**

⚠️ **ВАЖНО**: Для разработки и тестирования используйте исключительно Docker Compose с PostgreSQL.

cd backend  
\# Активация виртуального окружения (только для локальной отладки)  
source venv/bin/activate  \# Linux/Mac  
venv\\Scripts\\activate     \# Windows  
\# Установка зависимостей  
pip install \-r requirements.txt  
\# Запуск сервера разработки  
python manage.py runserver 8001  
\# Запуск Celery (в отдельных терминалах)  
celery \-A freesport worker \--loglevel=info  
celery \-A freesport beat \--loglevel=info

**РЕКОМЕНДУЕМЫЙ способ - Docker:**
docker-compose up -d --build

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

   * Это обеспечивает синхронизацию зависимостей между разработчиками
   * Позволяет воспроизвести точную среду разработки

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
* **Проверка типов:** mypy + Pylance (VS Code)

**Frontend**

* **Линтинг:** ESLint  
* **Стилизация:** Tailwind CSS

### **Стратегия тестирования**

Проект следует классической пирамиде тестирования: E2E \> Integration \> Unit.

**Детальные стандарты и правила тестирования:** см. `backend/docs/testing-standards.md`

**Основные команды тестирования:**

⚠️ **КРИТИЧЕСКИ ВАЖНО**: Тестирование выполняется ТОЛЬКО с PostgreSQL через Docker Compose!

\# Тестирование в Docker (ЕДИНСТВЕННЫЙ поддерживаемый способ)
make test                    \# Все тесты с PostgreSQL + Redis
make test-unit               \# Только unit-тесты
make test-integration        \# Только интеграционные тесты
make test-fast               \# Без пересборки образов

\# SQLite больше НЕ поддерживается для тестов из-за ограничений JSON операторов
\# Локальное тестирование через pytest требует настроенного PostgreSQL

**Требования к покрытию:** Общее \>= 70%, критические модули \>= 90%.

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

- ❌ **НЕ создавайте** синтетические/тестовые XML данные для тестов импорта из 1С
- ✅ **ВСЕГДА используйте** файлы из `data/import_1c/` для интеграционных тестов
- ✅ **Эти данные содержат** реальную структуру CommerceML 3.1 из production
- ✅ **Включены edge cases:** клиенты без email, разные типы организаций (ООО, ИП, физ.лица), различные форматы данных
- ✅ **Полнота данных:** контрагенты с полными реквизитами, банковскими счетами, адресами

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
- Устранено противоречие БД - теперь везде только PostgreSQL
- Добавлены недостающие сервисы db и redis в docker-compose.test.yml
- Создана nginx конфигурация для основной среды
- Создан оптимизированный Dockerfile.test для тестирования
- Исправлен конфликт портов: Django теперь на порту 8001 вместо 8000
- Добавлен Makefile с удобными командами
- Созданы скрипты автоматизации тестирования

**Новые файлы:**
- docker-compose.test.yml - полная тестовая среда с PostgreSQL и Redis
- backend/Dockerfile.test - оптимизированный образ для тестирования  
- docker/nginx/ - конфигурация Nginx reverse proxy
- Makefile - команды для разработки и тестирования
- scripts/test.* - скрипты запуска тестов для разных ОС

### **Система изоляции тестов (добавлено 23.08.2025)**

**Решенные проблемы:**
- Устранены constraint violations из-за дублирующихся данных в тестах
- Реализована полная изоляция между тестами через autouse фикстуры  
- Создана система генерации абсолютно уникальных данных
- Исправлены интеграционные тесты для работы с изолированными данными

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

## **Стандарты качества кода и типизации**

### **Python Type Hints - Обязательные требования**

**КРИТИЧНО:** Весь новый код ДОЛЖЕН содержать полную типизацию. При изменении существующего кода - добавляйте типизацию.

#### **Обязательные импорты типизации:**
```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from decimal import Decimal

if TYPE_CHECKING:
    from apps.users.models import User
    from apps.products.models import Product
```

#### **Django Models - обязательная типизация:**
```python
# ✅ ПРАВИЛЬНО - все методы типизированы
def save(self, *args, **kwargs) -> None:
    super().save(*args, **kwargs)

def __str__(self) -> str:
    return self.name

@property 
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}".strip()

@property
def is_active_user(self) -> bool:
    return self.is_active and self.is_verified

# ❌ НЕПРАВИЛЬНО - отсутствует типизация
def save(self, *args, **kwargs):  # Без -> None
    super().save(*args, **kwargs)
```

#### **Django REST Framework - обязательная типизация:**
```python
# ✅ ПРАВИЛЬНО - Serializers с типизацией
def validate_email(self, value: str) -> str:
    # валидация
    return value

def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
    # валидация  
    return attrs

def create(self, validated_data: Dict[str, Any]) -> User:
    return User.objects.create(**validated_data)

def get_product_price(self, obj: Product) -> str:
    return str(obj.retail_price)

# ViewSets с типизацией
def get_queryset(self) -> QuerySet[Product]:
    return Product.objects.filter(is_active=True)

def get_serializer_class(self) -> type[ProductSerializer]:
    return ProductSerializer
```

#### **Django Managers - правильная типизация:**

```python
# ✅ ПРАВИЛЬНО
class UserManager(BaseUserManager['User']):
    def create_user(self, email: str, password: str | None = None, **extra_fields) -> User:
        # implementation
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> User:
        # implementation  
        return user

# В модели User:
objects: UserManager['User'] = UserManager()  # type: ignore[type-abstract]
```

#### **OpenAPI/DRF-Spectacular - правильные примеры:**

```python
# ✅ ПРАВИЛЬНО - используем OpenApiExample объекты
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema

@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Успешный ответ",
            examples=[
                OpenApiExample(
                    name="success_example",
                    value={"message": "Success", "data": {...}}
                )
            ]
        )
    }
)

# ❌ НЕПРАВИЛЬНО - словари вместо OpenApiExample
examples={
    "application/json": {"message": "Success"}  # Pylance ошибка!
}
```

### **Правила проверки типизации:**

1. **Перед каждым коммитом:**

   - Запустить `mypy apps/` для проверки типов
   - Проверить отсутствие ошибок Pylance в VS Code
   - Все новые методы ДОЛЖНЫ иметь type hints

2. **При изменении существующего кода:**

   - Добавить типизацию к изменяемым методам
   - Добавить недостающие импорты типизации
   - Исправить найденные Pylance предупреждения

3. **Обязательная типизация для:**

   - Все методы моделей (`save`, `__str__`, `@property`)
   - Все методы сериализаторов (`validate_*`, `get_*`, `create`, `update`)
   - Все методы ViewSet'ов (`get_queryset`, `get_serializer_class`)
   - Все параметры и возвращаемые значения функций

### **Автоматическая проверка качества:**

```bash
# Запуск всех проверок качества перед коммитом
make lint                    # Flake8 + Black + isort
make type-check             # mypy проверка типов  
make test                   # Все тесты
```

### **VS Code настройки для типизации:**

Рекомендуемые настройки в `.vscode/settings.json`:

```json
{
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.diagnosticMode": "workspace",
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true
}
```

### **Частые ошибки типизации и их исправления:**

1. **OpenApiResponse с dict примерами:**

   ```python
   # ❌ Неправильно
   examples={"key": "value"}
   
   # ✅ Правильно  
   examples=[OpenApiExample(name="example", value={"key": "value"})]
   ```

2. **Django Managers без типизации:**

   ```python
   # ❌ Неправильно
   objects = UserManager()
   
   # ✅ Правильно
   objects: UserManager['User'] = UserManager()  # type: ignore[type-abstract]
   ```

3. **Методы без return типов:**

   ```python
   # ❌ Неправильно  
   def save(self, *args, **kwargs):
   
   # ✅ Правильно
   def save(self, *args, **kwargs) -> None:
   ```

**ВАЖНО:** Нарушение стандартов типизации блокирует merge в develop/main ветки.

### **Команды для проверки качества кода:**

```bash
# === ОБЯЗАТЕЛЬНЫЕ проверки перед коммитом ===
docker-compose -f docker-compose.test.yml run --rm backend pytest --no-cov -q  # Быстрые тесты
docker-compose -f docker-compose.test.yml run --rm backend mypy apps/           # Проверка типов
docker-compose -f docker-compose.test.yml run --rm backend black --check apps/ # Форматирование
docker-compose -f docker-compose.test.yml run --rm backend flake8 apps/         # Линтинг

# === ПОЛНАЯ проверка качества ===
make test                    # Все тесты с покрытием
make lint                    # Все проверки стиля кода
make type-check             # Полная проверка типов

# === Исправление проблем ===  
docker-compose -f docker-compose.test.yml run --rm backend black apps/         # Автоформатирование
docker-compose -f docker-compose.test.yml run --rm backend isort apps/         # Сортировка импортов
```

### **Pre-commit хуки (рекомендуется):**

Создайте `.pre-commit-config.yaml` в корне проекта:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fast
        name: Fast tests
        entry: docker-compose -f docker-compose.test.yml run --rm backend pytest --no-cov -x
        language: system
        pass_filenames: false
        
      - id: mypy
        name: mypy type check
        entry: docker-compose -f docker-compose.test.yml run --rm backend mypy apps/
        language: system
        pass_filenames: false
        
      - id: black
        name: black code formatting  
        entry: docker-compose -f docker-compose.test.yml run --rm backend black --check apps/
        language: system
        pass_filenames: false
```

Установка: `pip install pre-commit && pre-commit install`

### **Исправление legacy кода без типизации:**

При работе с существующим кодом без типизации:

1. **Добавляйте типизацию постепенно** - к файлам которые изменяете
2. **Начинайте с импортов** - `from __future__ import annotations`
3. **Типизируйте новые методы полностью** - все параметры и return типы
4. **Исправляйте Pylance warnings** - они указывают на реальные проблемы
5. **Запускайте тесты после изменений** - типизация не должна ломать функциональность

### **Контрольный чек-лист для типизации:**

**✅ Перед коммитом проверить:**

- [ ] Все новые методы имеют type hints  
- [ ] Добавлены необходимые импорты типизации
- [ ] Нет ошибок Pylance в VS Code
- [ ] `mypy apps/` проходит без ошибок  
- [ ] Все тесты проходят успешно
- [ ] OpenAPI примеры используют OpenApiExample объекты
- [ ] Django Managers правильно типизированы