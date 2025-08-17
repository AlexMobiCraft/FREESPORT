# Стандарты тестирования FREESPORT Backend

## Единая система организации тестов

### 📁 ФИНАЛЬНАЯ структура тестов (После очистки дубликатов)

```
backend/
├── apps/                         # Django приложения
│   ├── products/
│   │   ├── tests.py              # ✅ Django Unit Tests API (TestCase)
│   │   ├── models.py
│   │   ├── views.py
│   │   └── ...
│   ├── users/
│   │   ├── tests.py              # ✅ Django Unit Tests API (TestCase)
│   │   └── ...
│   ├── cart/
│   │   ├── tests.py              # ✅ Django Unit Tests API (TestCase)
│   │   └── ...
│   ├── common/
│   │   ├── tests.py              # ✅ Django Unit Tests API (TestCase)
│   │   └── ...
│   └── orders/
│       ├── tests.py              # ✅ Django Unit Tests API (TestCase)
│       └── ...
├── tests/                        # Общие тесты проекта
│   ├── __init__.py
│   ├── conftest.py               # ✅ Pytest фабрики и конфигурация
│   ├── run_tests_utf8.py         # ✅ Скрипт запуска с UTF-8
│   │
│   ├── functional/               # ✅ HTTP API тесты (requests)
│   │   ├── __init__.py
│   │   ├── test_user_management_api.py    # Story 2.2
│   │   ├── test_personal_cabinet_api.py   # Story 2.3
│   │   ├── test_catalog_api.py            # Story 2.4
│   │   └── test_product_detail_api.py     # Story 2.5
│   │
│   ├── test_products/            # ✅ Pytest тесты моделей
│   │   └── test_models.py        # Pytest + Factory Boy
│   ├── test_users/               # ✅ Pytest тесты моделей
│   │   └── test_models.py        # Pytest + Factory Boy
│   ├── test_cart/                # ✅ Pytest тесты моделей
│   │   └── test_models.py        # Pytest + Factory Boy
│   ├── test_common/              # ✅ Pytest тесты моделей
│   │   └── test_models.py        # Pytest + Factory Boy
│   ├── test_orders/              # ✅ Pytest тесты моделей
│   │   └── test_models.py        # Pytest + Factory Boy
│   │
│   └── test_integration/         # Пустая (для будущих интеграционных тестов)
├── freesport/
│   └── settings/
│       └── test.py               # ✅ Django тестовые настройки
└── pytest.ini                   # ✅ Pytest конфигурация
```

### 🧹 **ВЫПОЛНЕНА ОЧИСТКА ДУБЛИКАТОВ:**

#### ❌ Удалены пустые дубликаты:
- `apps/cart/cart/tests.py` (пустой файл)
- `apps/products/products/tests.py` (пустой файл) 
- `apps/common/common/tests.py` (пустой файл)
- `apps/orders/orders/tests.py` (пустой файл)

#### ❌ Удалены старые функциональные тесты:
- `tests/test_catalog_api.py` → перенесен в `tests/functional/`
- `tests/test_manual.py` → перенесен в `tests/functional/test_user_management_api.py`
- `tests/test_personal_cabinet.py` → перенесен в `tests/functional/`

## 🔧 Типы тестов и их назначение

### 1. **Django Unit Tests** (`apps/{app}/tests.py`)
- **Назначение**: Тестирование моделей, serializers, ViewSets изнутри Django
- **Технология**: `django.test.TestCase`, `rest_framework.test.APIClient`
- **Запуск**: `python manage.py test apps.{app}`
- **Особенности**: 
  - Доступ к Django ORM
  - Автоматические транзакции
  - Django fixtures

**Пример структуры:**
```python
# apps/products/tests.py
from django.test import TestCase
from rest_framework.test import APIClient

class ProductDetailAPITestCase(TestCase):
    def setUp(self):
        # Django setup с моделями
        
    def test_product_detail_view(self):
        # Тест ViewSet через APIClient
```

### 2. **Functional HTTP API Tests** (`tests/functional/`)
- **Назначение**: Полнофункциональное тестирование API через HTTP
- **Технология**: `requests` библиотека, реальные HTTP запросы
- **Запуск**: `python tests/run_tests_utf8.py --functional`
- **Особенности**:
  - Требует запущенный сервер (`python manage.py runserver`)
  - Тестирует полный HTTP pipeline
  - Проверяет JWT аутентификацию
  - Ролевое ценообразование

**Пример структуры:**
```python
# tests/functional/test_product_detail_api.py
import requests

def test_product_detail_basic():
    response = requests.get(f"{BASE_URL}/products/{product_id}/")
    assert response.status_code == 200
```

### 3. **Integration Tests** (`tests/integration/`)
- **Назначение**: Тестирование взаимодействия между компонентами
- **Запуск**: `python tests/run_tests_utf8.py --integration`

### 4. **Performance Tests** (`tests/performance/`)
- **Назначение**: Тестирование производительности API
- **Запуск**: `python tests/run_tests_utf8.py --performance`

## 🚀 Команды запуска

### Все тесты
```bash
# Все Django unit тесты
python tests/run_tests_utf8.py --unit

# Все функциональные HTTP тесты  
python tests/run_tests_utf8.py --functional

# Все тесты (unit + functional)
python tests/run_tests_utf8.py
```

### Конкретные тесты
```bash
# Django unit тест конкретного приложения
python manage.py test apps.products

# Функциональный тест конкретной Story
python tests/functional/test_product_detail_api.py

# С корректной кодировкой UTF-8
python tests/run_tests_utf8.py --functional --story=2.5
```

## 📝 Соглашения по именованию

### Файлы тестов
- **Django Unit**: `apps/{app}/tests.py`
- **Functional**: `tests/functional/test_{story_name}_api.py`
- **Integration**: `tests/integration/test_{feature}_integration.py`

### Классы и функции
- **Django Unit**: `{Feature}APITestCase(TestCase)`
- **Functional**: `test_{feature}_{aspect}()`

### Тестовые данные
- **SKU Pattern**: `{BRAND}_{TYPE}_{NUM}` (например: `NIKE_DETAIL_001`)
- **Email Pattern**: `test_{story}_{role}@example.com`
- **User Pattern**: `Тест {Story} {Role}`

## 🔧 Настройка кодировки UTF-8

### Проблема Windows
На Windows консоль по умолчанию использует CP-1251, что приводит к искажению русских символов.

### Решение
Всегда используйте `run_tests_utf8.py` для корректного отображения:

```python
# tests/run_tests_utf8.py автоматически настраивает:
os.environ['PYTHONIOENCODING'] = 'utf-8'
subprocess.run(command, encoding='utf-8')
```

## 📊 QA Review процесс

### Для каждой Story:
1. **Unit тесты** - проверяются автоматически через Django
2. **Functional тесты** - создаются в `tests/functional/`
3. **QA Review** - документируется в `docs/stories/{story}.md`
4. **Acceptance Criteria** - проверяются через функциональные тесты

### Пример QA Review:
```markdown
## QA Results
### ✅ Общий результат: ОДОБРЕНО
#### 1. Acceptance Criteria ✅ (5/5 ПРОШЛИ)
#### 2. Функциональное тестирование ✅ (12/12 ТЕСТОВ)
#### 3. Архитектурная совместимость ✅
```

## 🎯 Миграция существующих тестов

### Текущее состояние (устаревшее):
```
backend/tests/test_manual.py           → tests/functional/test_user_management_api.py
backend/tests/test_personal_cabinet.py → tests/functional/test_personal_cabinet_api.py  
backend/tests/test_catalog_api.py      → tests/functional/test_catalog_api.py
```

### Новая структура (рекомендуемая):
```
tests/functional/test_user_management_api.py    # Story 2.2
tests/functional/test_personal_cabinet_api.py   # Story 2.3  
tests/functional/test_catalog_api.py             # Story 2.4
tests/functional/test_product_detail_api.py     # Story 2.5
```

## ⚡ Быстрый старт

### Создание нового функционального теста:
1. Создать файл: `tests/functional/test_{story_name}_api.py`
2. Использовать шаблон из `test_catalog_api.py`
3. Добавить в `run_tests_utf8.py` 
4. Запустить: `python tests/run_tests_utf8.py --functional`

### Создание Django unit теста:
1. Добавить в `apps/{app}/tests.py`
2. Наследоваться от `TestCase`
3. Запустить: `python manage.py test apps.{app}`

---

**Дата создания**: 17 августа 2025  
**Версия**: 1.0  
**Статус**: ✅ УТВЕРЖДЕНО