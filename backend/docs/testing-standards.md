# Стандарты тестирования FREESPORT Backend

## 1. Философия тестирования

Наша стратегия основана на классической **пирамиде тестирования**, принятой в архитектурной документации. Мы стремимся иметь широкое основание из быстрых и изолированных **Unit-тестов**, слой **интеграционных тестов** для проверки взаимодействия компонентов и несколько ключевых **E2E-тестов** для проверки критических пользовательских сценариев.

```
                  E2E Tests (Playwright)
                 /        \
        Integration Tests (Pytest + APIClient)
           /            \
      Backend Unit Tests (Pytest)
```

## 2. Технологический стек

*   **Основной фреймворк**: `pytest`
*   **Интеграция с Django**: `pytest-django`
*   **Генерация данных**: `Factory Boy`
*   **Мокинг (Mocking)**: `pytest-mock`

## 3. Структура тестов

Все тесты для backend должны находиться в директории `backend/tests/`.

```
backend/
└── tests/
    ├── __init__.py
    ├── conftest.py                 # ✅ Общие фикстуры Pytest (Factory Boy, APIClient)
    │
    ├── unit/                       # ✅ Unit-тесты (быстрые, изолированные)
    │   ├── test_models/
    │   │   └── test_product_properties.py
    │   ├── test_serializers/
    │   │   └── test_user_validation.py
    │   └── test_services/
    │       └── test_pricing_engine.py
    │
    ├── integration/                # ✅ Интеграционные тесты (проверка взаимодействия)
    │   ├── test_auth_api.py
    │   ├── test_products_api.py    # Тестирование API каталога
    │   ├── test_orders_api.py      # Тестирование API заказов
    │   └── test_1c_integration.py
    │
    ├── legacy/                     # ⚠️  Устаревшие тесты
    │   └── test_old_feature.py
    │
    └── fixtures/                   # (Опционально) Статические JSON фикстуры
        ├── categories.json
        └── brands.json
```

## 4. Типы тестов и их назначение

### 4.1. Unit-тесты (`tests/unit/`)

*   **Назначение**: Тестирование одного изолированного компонента (модели, сериализатора, сервиса, утилиты). Эти тесты не должны обращаться к базе данных или внешним сервисам.
*   **Технологии**: `pytest`, `pytest-mock`.
*   **Пример**: Проверка, что метод модели `Product.can_be_ordered()` корректно возвращает `False`, если `stock_quantity = 0`.

### 4.2. Интеграционные тесты (`tests/integration/`)

*   **Назначение**: Тестирование взаимодействия между несколькими компонентами системы. В первую очередь, это тесты API endpoints.
*   **Технологии**: `pytest`, `pytest-django`, `APIClient`, `Factory Boy`.
*   **Особенности**:
    *   Используют тестовую базу данных.
    *   Проверяют полный цикл "запрос-ответ" для API.
    *   Тестируют права доступа, валидацию, бизнес-логику в связке.
*   **Пример**: Отправка POST-запроса на `/api/v1/orders/`, проверка создания заказа в БД и корректности ответа (статус 201, данные заказа).

### 4.3. E2E-тесты (внешняя директория `e2e/`)

*   **Назначение**: Тестирование полных пользовательских сценариев через браузер. Эти тесты находятся вне backend-проекта.
*   **Технологии**: `Playwright`.
*   **Пример**: Сценарий "Пользователь логинится, добавляет товар в корзину, оформляет заказ и видит страницу подтверждения".

### 4.4. Устаревшие тесты (`tests/legacy/`)

*   **Назначение**: Эта директория содержит тесты для устаревшего или удаленного функционала. Они сохраняются для временной обратной совместимости или для возможности восстановления логики в будущем.
*   **Особенности**:
    *   Эти тесты **не должны** запускаться в основном CI-пайплайне.
    *   Их следует исключить из отчетов о покрытии кода.
    *   Новые тесты **запрещено** добавлять в эту директорию.
    *   Основная цель — постепенное удаление этих тестов по мере стабилизации кодовой базы.
*   **Команда для исключения из запуска**:
    ```bash
    pytest --ignore=tests/legacy
    ```

## 5. Генерация тестовых данных

Для создания тестовых объектов в БД **необходимо использовать `Factory Boy`**. Это обеспечивает гибкость и читаемость тестов.

**Пример фабрики:**
```python
# tests/factories.py (или в conftest.py)
import factory
from apps.products.models import Product, Brand, Category

class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand
    name = factory.Faker('company')
    slug = factory.Sequence(lambda n: f'brand-{n}')

class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    name = "Тестовый товар"
    brand = factory.SubFactory(BrandFactory)
    # ... другие поля
```

## 6. Команды запуска тестов

Все тесты запускаются с помощью `pytest` из корневой директории `backend/`.

```bash

# Запустить все тесты (unit + integration)
pytest

# Запустить только unit-тесты
pytest -m unit

# Запустить только интеграционные тесты
pytest -m integration

# Запустить тесты с отчетом о покрытии
pytest --cov=apps

# Запустить тесты для конкретного файла
pytest tests/integration/test_products_api.py
```
Для разделения тестов на `unit` и `integration` используется маркировка `@pytest.mark.unit` и `@pytest.mark.integration`.

## 7. Контрольные точки качества (Quality Gates)

*   **Покрытие кода**:
    *   Общее покрытие по проекту: **не менее 70%**.
    *   Покрытие критических модулей (auth, orders, products): **не менее 90%**.
*   **CI Pipeline**: Все тесты должны успешно проходить в CI перед мержем в `develop` и `main`. Сборка с покрытием ниже минимального должна блокировать мерж.

## 8. Изоляция тестов и уникальность данных

### 8.1. Полная изоляция тестов

**Критически важно**: Каждый тест должен выполняться в полностью изолированной среде. Проект использует автоматические фикстуры для обеспечения полной изоляции:

```python
# conftest.py - автоматические фикстуры
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включает доступ к базе данных для всех тестов"""
    pass

@pytest.fixture(autouse=True) 
def clear_db_before_test(transactional_db):
    """Очищает базу данных перед каждым тестом для полной изоляции"""
    from django.core.cache import cache
    from django.db import connection
    from django.apps import apps
    
    # Очищаем кэши Django
    cache.clear()
    
    # Принудительная очистка всех таблиц перед тестом
    with connection.cursor() as cursor:
        models = apps.get_models()
        for model in models:
            table_name = model._meta.db_table
            try:
                cursor.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
            except Exception:
                pass  # Игнорируем ошибки для системных таблиц
    
    # Используем транзакционную изоляцию
    with transaction.atomic():
        yield
```

### 8.2. Генерация уникальных данных

**Проблема**: Использование статических значений или простых последовательностей может приводить к constraint violations при параллельном выполнении тестов.

**Решение**: Обязательное использование комбинированного подхода для генерации уникальных значений:

```python
import uuid
import time

# Глобальный счетчик для обеспечения уникальности
_unique_counter = 0

def get_unique_suffix():
    """Генерирует абсолютно уникальный суффикс"""
    global _unique_counter
    _unique_counter += 1
    return f"{int(time.time() * 1000)}-{_unique_counter}-{uuid.uuid4().hex[:6]}"

# В Factory Boy
class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand
    
    name = factory.LazyFunction(lambda: f"Brand-{get_unique_suffix()}")  # ✅ Правильно
    # name = factory.Sequence(lambda n: f"Brand-{n}")  # ❌ Может дублироваться
```

### 8.3. Настройки pytest для изоляции

В `pytest.ini` должны быть следующие настройки:

```ini
addopts = 
    --verbose
    --create-db        # ✅ Создавать чистую БД
    --nomigrations     # ✅ Не выполнять миграции для скорости
    # --reuse-db       # ❌ НЕ переиспользовать БД между запусками
```

### 8.4. Правила для интеграционных тестов

Интеграционные тесты должны создавать свои данные в каждом тесте:

```python
@pytest.fixture
def setup_test_data():
    """Создание тестовых данных для каждого теста отдельно"""
    import uuid
    import time
    
    # Уникальный суффикс для избежания конфликтов
    unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    
    brand = Brand.objects.create(
        name=f'Test-Brand-{unique_suffix}',
        slug=f'test-brand-{unique_suffix}'
    )
    
    products = []
    for i in range(3):
        product = Product.objects.create(
            name=f'Test Product {i} {unique_suffix}',
            sku=f'TEST{i:03d}-{unique_suffix}',
            brand=brand,
            # ... другие поля
        )
        products.append(product)
    
    return {'brand': brand, 'products': products, 'unique_suffix': unique_suffix}

def test_products_list(api_client, setup_test_data):
    # ✅ Используем данные из фикстуры текущего теста
    response = api_client.get('/api/products/')
    assert response.status_code == 200
    assert len(response.json()['results']) >= 3
```

**❌ Антипаттерны (избегать):**
- Фикстуры с `scope='module'` или `scope='session'` для данных
- Статические значения в тестах (`name='Nike'`, `sku='TEST001'`)
- Переиспользование данных между тестами
- Ручная очистка данных в тестах

### 8.5. Обязательные правила написания тестов FREESPORT

#### Правила для Factory Boy

**✅ Правильно:**
```python
# Всегда используйте LazyFunction для уникальных полей
class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    
    name = factory.LazyFunction(lambda: f"Product-{get_unique_suffix()}")
    sku = factory.LazyFunction(lambda: f"SKU-{get_unique_suffix().upper()}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
```

**❌ Неправильно:**
```python
# НЕ используйте статические значения или простые Sequence
class ProductFactory(factory.django.DjangoModelFactory):
    name = "Test Product"  # ❌ Статическое значение
    sku = factory.Sequence(lambda n: f"SKU{n}")  # ❌ Может дублироваться
```

#### Правила для интеграционных тестов

**✅ Правильно:**
```python
@pytest.fixture
def test_data():
    """Создаем данные для каждого теста индивидуально"""
    unique_suffix = get_unique_suffix()
    brand = BrandFactory.create(name=f"Brand-{unique_suffix}")
    products = ProductFactory.create_batch(3, brand=brand)
    return {'brand': brand, 'products': products}

def test_api_endpoint(api_client, test_data):
    # Используем данные из текущего теста
    response = api_client.get(f"/api/brands/{test_data['brand'].id}/")
    assert response.status_code == 200
```

**❌ Неправильно:**
```python
# НЕ используйте module scope для данных
@pytest.fixture(scope='module')  # ❌ 
def shared_data():
    return BrandFactory.create(name="Nike")  # ❌ Статическое имя

def test_api_endpoint(api_client, shared_data):  # ❌ Зависимость от общих данных
    pass
```

#### Правила для unit тестов

**✅ Правильно:**
```python
@pytest.mark.unit
def test_product_price_calculation():
    """Unit тест изолированного метода"""
    # Создаем объект только для этого теста
    product = ProductFactory.build(  # build, не create - без БД
        retail_price=Decimal('1000.00'),
        opt1_price=Decimal('800.00')
    )
    
    # Тестируем конкретную логику
    user = UserFactory.build(role='wholesale_level1')
    assert product.get_price_for_user(user) == Decimal('800.00')
```

**❌ Неправильно:**
```python
def test_product_price_calculation():  # ❌ Нет маркировки @pytest.mark.unit
    # ❌ Обращение к БД в unit тесте
    product = ProductFactory.create(retail_price=1000)  
    # ❌ Тестирование нескольких вещей одновременно
    assert product.retail_price == 1000
    assert product.is_active == True
    assert len(product.name) > 0
```

#### Правила маркировки тестов

**Обязательные маркеры:**
- `@pytest.mark.unit` - для unit тестов (без БД, быстрые)
- `@pytest.mark.integration` - для интеграционных тестов (с БД, API)
- `@pytest.mark.django_db` - для всех тестов, использующих БД

**✅ Правильная структура файла:**
```python
import pytest
from rest_framework.test import APIClient

# Маркировка для всего модуля
pytestmark = pytest.mark.django_db

@pytest.mark.integration 
class TestProductAPI:
    def test_product_list_returns_200(self, api_client):
        response = api_client.get('/api/products/')
        assert response.status_code == 200
    
    def test_product_create_requires_auth(self, api_client):
        data = {'name': 'Test Product'}
        response = api_client.post('/api/products/', data)
        assert response.status_code == 401
```

#### Правила именования

**Файлы:**
- Unit тесты: `tests/unit/test_[module]_[component].py`
- Интеграционные: `tests/integration/test_[feature]_api.py`

**Функции и классы:**
- Функции: `test_[action]_[expected_result]()`
- Классы: `Test[ComponentName]` или `Test[FeatureName]API`

**✅ Примеры хороших имен:**
```python
def test_user_registration_creates_inactive_user():
def test_product_search_filters_by_brand():  
def test_order_calculation_includes_delivery_cost():
def test_unauthorized_user_cannot_access_profile():

class TestProductModel:
class TestUserRegistrationAPI:
class TestOrderCalculationService:
```

**❌ Плохие имена:**
```python
def test_user():  # ❌ Неясно что тестируем
def test_api():   # ❌ Слишком общее
def test_bug_fix_123():  # ❌ Не описывает поведение
```

#### Правила структуры тестов (AAA Pattern)

**✅ Обязательная структура:**
```python
def test_order_creation_calculates_total_correctly():
    # ARRANGE - подготовка данных
    user = UserFactory.create()
    product1 = ProductFactory.create(retail_price=100)
    product2 = ProductFactory.create(retail_price=200)
    
    # ACT - выполнение действия
    order = Order.objects.create(user=user)
    OrderItem.objects.create(order=order, product=product1, quantity=1)
    OrderItem.objects.create(order=order, product=product2, quantity=2)
    
    # ASSERT - проверка результата
    assert order.calculate_total() == 500  # 100*1 + 200*2
```

#### Правила для assertions

**✅ Правильно:**
```python
# Конкретные и понятные assertions
assert response.status_code == 201
assert response.data['name'] == expected_name
assert User.objects.filter(email=email).exists()
assert len(response.data['results']) == 3

# С описательными сообщениями для сложных случаев
assert user.is_verified, f"User {user.email} should be verified after registration"
```

**❌ Неправильно:**
```python
# Слишком общие или множественные проверки
assert response  # ❌ Неясно что проверяем
assert response.status_code == 200 and len(response.data) > 0  # ❌ Два условия
assert response.data == expected_data  # ❌ Сравнение больших объектов без указания что важно
```

## 9. Лучшие практики и соглашения

### 9.1. Именование тестов

*   **Имя файла**: Должно начинаться с `test_` и отражать тестируемый модуль.
    *   `test_product_model.py`
    *   `test_cart_api.py`
*   **Имя функции**: Должно быть описательным и следовать формату `test_` + `условие_или_действие` + `_` + `ожидаемый_результат`.
    *   `test_anonymous_user_cannot_access_profile()`
    *   `test_product_creation_fails_if_price_is_negative()`
    *   `test_order_total_is_calculated_correctly()`

### 9.2. Структура теста: Arrange-Act-Assert (AAA)

Каждый тест должен четко следовать паттерну AAA для лучшей читаемости.

```python
# tests/integration/test_orders_api.py
import pytest
from rest_framework.test import APIClient
from .factories import UserFactory, ProductFactory

@pytest.mark.integration
def test_order_creation_for_authenticated_user(db):
    # 1. Arrange (Подготовка)
    # Создаем пользователя, товары и данные для запроса
    user = UserFactory()
    product1 = ProductFactory(price=100)
    product2 = ProductFactory(price=200)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    order_data = {
        "items": [
            {"product_id": product1.id, "quantity": 1},
            {"product_id": product2.id, "quantity": 2}
        ],
        "delivery_address": "123 Main St"
    }

    # 2. Act (Действие)
    # Выполняем запрос к API
    response = client.post("/api/v1/orders/", order_data, format='json')

    # 3. Assert (Проверка)
    # Проверяем результат
    assert response.status_code == 201
    assert response.data['total_amount'] == 500  # 1*100 + 2*200
    assert Order.objects.count() == 1
    assert Order.objects.first().user == user
```

### 9.3. Ассерты (Assertions)

*   **Будьте конкретны**: Проверяйте только то, что относится к тесту. Не нужно проверять все поля объекта, если тест касается только одного.
*   **Один логический ассерт на тест**: В идеале, один тест должен проверять одну вещь. Допускается несколько `assert`, если они проверяют разные аспекты одного и того же логического результата (например, статус код и тело ответа).
*   **Используйте описательные сообщения**: `assert user.is_active, "Пользователь должен быть активным после регистрации"`

### 9.4. Избегайте "хрупких" (Flaky) тестов

*   **Никаких `time.sleep()`**: Не используйте задержки для ожидания асинхронных операций. Используйте предназначенные для этого инструменты (например, `mock` или `celery` в eager-режиме).
*   **Изолируйте тесты**: Тесты не должны зависеть друг от друга или от порядка их выполнения. Каждый тест должен создавать необходимые ему данные.
*   **Очистка**: `pytest-django` автоматически заботится об очистке тестовой БД. Не создавайте данные вне этого механизма.

### 9.5. Мокинг (Mocking)

*   **Назначение**: Используйте моки для изоляции от внешних систем (платежные шлюзы, сервисы 1С, email-рассылки), чтобы сделать тесты быстрыми и предсказуемыми.
*   **Инструмент**: `pytest-mock` (обертка над `unittest.mock`).
*   **Пример**:
    ```python
    def test_order_confirmation_sends_email(mocker):
        # Arrange
        mocker.patch('apps.notifications.services.send_email')
        # ... (создание заказа)
    
        # Act
        # ... (вызов сервиса, который должен отправить email)
    
        # Assert
        send_email.assert_called_once()
    ```

## 10. CI/CD Интеграция

Все тесты автоматически запускаются в GitHub Actions при каждом пуше в ветки `develop` и `main`. Конфигурация находится в файле `.github/workflows/backend-ci.yml`. Пулл-реквесты, в которых тесты не проходят или покрытие падает ниже установленного порога, не могут быть влиты.

```
