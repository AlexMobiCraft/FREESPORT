# Анализ тестов Backend FREESPORT - План исправлений

**Дата анализа:** 15 января 2026
**Аналитик:** Claude AI Agent
**Статус:** Требуется исправление

---

## Краткое резюме

Проведен анализ тестового покрытия backend проекта FREESPORT. Обнаружено несколько категорий проблем, требующих внимания:

- **23 ошибки линтера** (flake8 E501 - длинные строки)
- **3 пропущенных теста** с маркером @pytest.mark.skip
- **Незавершенные функции** (TODO/FIXME комментарии)
- **Покрытие кода 83%** для критического модуля products/models.py
- **Сложная логика фабрик** требует рефакторинга

---

## Статистика тестов

| Метрика | Значение |
|---------|----------|
| Всего тестовых файлов | 88 |
| Файлов с тестовыми функциями | 90 |
| Integration тестов | 43+ |
| Unit тестов | 47+ |
| Пропущенных тестов (@skip/@xfail) | 3 |
| Ошибок линтера | 23 |
| Покрытие кода (products/models.py) | 83.33% |

---

## 🔴 Критические проблемы

### Проблема 1: Пропущенные тесты (@pytest.mark.skip)

**Локация:** 3 теста в 2 файлах

#### 1.1. tests/integration/test_auth_api.py

**Тест 1:** `test_schema_includes_logout_endpoint`
**Причина пропуска:** "Schema generation fails due to existing Decimal import issue (not related to logout)"

```python
@pytest.mark.skip(
    reason="Schema generation fails due to existing Decimal import issue "
    "(not related to logout)"
)
def test_schema_includes_logout_endpoint(self, api_client: APIClient):
    ...
```

**Проблема:** Ошибка генерации OpenAPI схемы из-за импорта Decimal
**Влияние:** Критическое - документация API может быть неполной

**Тест 2:** `test_swagger_ui_accessible`
**Причина пропуска:** "Swagger UI endpoint not configured in test environment"

```python
@pytest.mark.skip(reason="Swagger UI endpoint not configured in test environment")
def test_swagger_ui_accessible(self, api_client: APIClient):
    ...
```

**Проблема:** Swagger UI не настроен для тестового окружения
**Влияние:** Среднее - разработчики не могут проверить UI документации в тестах

#### 1.2. tests/unit/test_models/test_cart_models.py

**Тест:** `test_min_order_quantity_validation`
**Причина пропуска:** "Validation for min_order_quantity not implemented in CartItem model yet"

```python
@pytest.mark.skip(
    reason="Validation for min_order_quantity not implemented in CartItem model yet"
)
def test_min_order_quantity_validation(self):
    ...
```

**Проблема:** Валидация min_order_quantity не реализована в модели CartItem
**Влияние:** Критическое - пользователи могут добавлять товары с количеством меньше минимального

---

### Проблема 2: Ошибки линтера flake8 (E501 - длинные строки)

**Локация:** 23 ошибки в 15 файлах

**Список затронутых файлов:**

1. **apps/products/management/commands/deduplicate_images.py** - 9 ошибок (строки 15, 19, 61, 68, 354, 390, 418, 527, 574)
2. **apps/products/tests/test_api_attributes.py** - 1 ошибка (строка 239)
3. **apps/products/tests/test_product_variant_models.py** - 1 ошибка (строка 456)
4. **apps/products/tests/test_serializers.py** - 1 ошибка (строка 99)
5. **apps/products/views.py** - 1 ошибка (строка 53)
6. **tests/conftest.py** - 1 ошибка (строка 564)
7. **tests/integration/test_auth_api.py** - 1 ошибка (строка 44)
8. **tests/integration/test_banners_api.py** - 1 ошибка (строка 278)
9. **tests/integration/test_product_attributes_api.py** - 1 ошибка (строка 258)
10. **tests/integration/test_variant_import.py** - 1 ошибка (строка 859)
11. **tests/integration/test_verification_workflow.py** - 2 ошибки (строки 49, 124)
12. **tests/regression/test_epic_28_intact.py** - 1 ошибка (строка 48)
13. **tests/unit/test_models/test_blog_post.py** - 1 ошибка (строка 172)
14. **tests/unit/test_serializers/test_logout_serializer.py** - 1 ошибка (строка 5)

**Проблема:** Нарушение стандарта PEP8 - строки длиннее 88 символов
**Влияние:** Низкое - но ухудшает читаемость кода и нарушает CI/CD pipeline

---

### Проблема 3: Незавершенные функции (TODO/FIXME)

**Локация:** 14 TODO комментариев в тестах

**Критические TODO:**

1. **tests/integration/test_guest_session_integration.py**
   - TODO: Реализовать автоматический перенос корзины в сигналах
   - TODO: Тестировать management команду cleanup_guest_carts

2. **tests/integration/test_b2b_workflow.py**
   - TODO: Добавить метод удаления заказа или отмены

3. **tests/integration/test_b2c_workflow.py**
   - TODO: Определить, требует ли система авторизации для заказов

4. **tests/integration/test_filtering_api.py** (6 TODO)
   - TODO: Реализовать после Story 2.9
   - TODO: Реализовать фильтрацию по min_price, max_price
   - TODO: Реализовать фильтрацию по категориям
   - TODO: Реализовать фильтрацию по брендам
   - TODO: Реализовать фильтрацию in_stock
   - TODO: Реализовать применение нескольких фильтров одновременно
   - TODO: Реализовать отображение количества товаров для каждого фильтра

5. **tests/integration/test_user_cart_integration.py**
   - TODO: Реализовать логику переноса корзины в сигналах

**Проблема:** Функциональность частично реализована или тесты написаны до реализации функций
**Влияние:** Среднее - указывает на технический долг

---

### Проблема 4: Покрытие кода (Code Coverage)

**Анализ coverage.json для apps/products/models.py:**

**Общее покрытие:** 83.33% (225/270 строк)
**Непокрытые строки:** 45

**Методы с низким/нулевым покрытием:**

| Метод | Покрытие | Строки |
|-------|----------|--------|
| `Brand.save()` | 30% | 67, 69-71, 73, 76-77 не покрыты |
| `Brand.__str__()` | 0% | Не тестируется |
| `Brand1CMapping.__str__()` | 0% | Не тестируется |
| `Category.save()` | 22% | 188, 190-192, 194, 197-198 не покрыты |
| `Category.__str__()` | 0% | Не тестируется |
| `Category.full_name()` | 0% | Полностью не покрыт |
| `Product.save()` | 12% | 408, 410-412, 414, 417-418, 421-426, 428-430 не покрыты |
| `Product.__str__()` | 0% | Не тестируется |
| `ProductImage.__str__()` | 0% | Не тестируется |
| `ProductImage.save()` | 0% | Полностью не покрыт |
| `ImportSession.__str__()` | 0% | Не тестируется |
| `PriceType.__str__()` | 0% | Не тестируется |
| `ColorMapping.__str__()` | 0% | Не тестируется |

**Проблема:** Критические методы (save(), __str__()) не тестируются
**Влияние:** Высокое - возможны баги в логике сохранения и строковом представлении

---

### Проблема 5: Сложность фабрик (Factory Boy)

**Файл:** tests/factories.py

**Проблема:** ProductFactory имеет сложную логику передачи параметров в ProductVariant

```python
class ProductFactory(DjangoModelFactory):
    """
    Factory for Product with automatic ProductVariant creation.

    Price and stock fields (retail_price, stock_quantity, etc.) are passed
    to the auto-created ProductVariant. Access via product.variants.first().
    """

    # Class-level storage for variant params (thread-safe per-instance)
    _variant_params_storage = {}

    _VARIANT_FIELDS = [
        "retail_price", "opt1_price", "opt2_price", "opt3_price",
        "trainer_price", "federation_price", "stock_quantity",
        "reserved_quantity", "sku", "onec_variant_id",
    ]
```

**Сложности:**

1. **Thread-safety concerns:** Использование class-level storage `_variant_params_storage`
2. **Неявное поведение:** Параметры автоматически перенаправляются в ProductVariant
3. **Сложная логика:** Методы `_create()` и `post_generation` с манипуляцией параметрами
4. **Поддержка:** Сложно отлаживать при падении тестов

**Влияние:** Среднее - затрудняет написание и отладку тестов

---

### Проблема 6: Недавние изменения и технический долг

**Анализ git log (последние 20 коммитов):**

**Обнаружено:**

1. **Массовые исправления тестов** (9+ коммитов с "Исправление тестов")
   - Переход на ProductVariant вызвал каскад изменений
   - Исправления в ProductFactory, тестах корзины, заказов, атрибутов

2. **Проблемы с уникальностью**
   - Коммит: "один тест на уникальность имеет небольшую нестабильность в CI"
   - Указывает на возможные race conditions в тестах

3. **Исправления линтера** (3 коммита)
   - Black, flake8 - указывает на игнорирование стандартов кода

**Проблема:** Технический долг накапливается, требуется рефакторинг
**Влияние:** Среднее - но может перерасти в высокое при дальнейшем развитии

---

## 📋 План исправлений

### Приоритет 1: Критические исправления (немедленно)

#### 1.1. Реализовать валидацию min_order_quantity в CartItem

**Файл:** apps/cart/models.py
**Время:** 2-3 часа

**Шаги:**

1. Добавить метод `clean()` в модель CartItem:
```python
def clean(self):
    if self.variant.min_order_quantity and self.quantity < self.variant.min_order_quantity:
        raise ValidationError(
            f"Минимальное количество для заказа: {self.variant.min_order_quantity}"
        )
```

2. Добавить валидацию в `save()`:
```python
def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)
```

3. Убрать @pytest.mark.skip из теста `test_min_order_quantity_validation`
4. Запустить тест: `pytest tests/unit/test_models/test_cart_models.py::test_min_order_quantity_validation -v`

#### 1.2. Исправить генерацию OpenAPI схемы (Decimal import issue)

**Файл:** Требуется диагностика
**Время:** 3-4 часа

**Шаги:**

1. Диагностировать проблему:
```bash
pytest tests/integration/test_auth_api.py::test_schema_includes_logout_endpoint -xvs
```

2. Проверить импорты в serializers:
```bash
grep -r "from decimal import Decimal" apps/*/serializers.py
```

3. Исправить использование Decimal в drf-spectacular:
   - Проверить настройки SPECTACULAR_SETTINGS
   - Возможно требуется custom schema generator

4. Убрать @pytest.mark.skip
5. Запустить тест повторно

#### 1.3. Увеличить покрытие критических методов до 90%+

**Файлы:** tests/unit/test_models/test_product_models.py
**Время:** 4-5 часов

**Шаги:**

1. Написать тесты для `__str__()` методов:
```python
def test_brand_str_representation(self):
    brand = BrandFactory.create(name="Nike")
    assert str(brand) == "Nike"

def test_category_str_representation(self):
    category = CategoryFactory.create(name="Обувь")
    assert str(category) == "Обувь"
```

2. Написать тесты для `save()` методов:
```python
def test_brand_save_generates_slug(self):
    brand = Brand(name="New Brand")
    brand.save()
    assert brand.slug == "new-brand"

def test_category_save_full_path(self):
    parent = CategoryFactory.create(name="Спорт")
    child = CategoryFactory.create(name="Футбол", parent=parent)
    child.save()
    assert child.full_path == "спорт/футбол"
```

3. Написать тесты для `Category.full_name()`:
```python
def test_category_full_name_with_parent(self):
    parent = CategoryFactory.create(name="Спорт")
    child = CategoryFactory.create(name="Футбол", parent=parent)
    assert child.full_name() == "Спорт > Футбол"
```

4. Запустить тесты с coverage:
```bash
pytest tests/unit/test_models/test_product_models.py --cov=apps/products/models --cov-report=term
```

5. Проверить, что покрытие >= 90%

---

### Приоритет 2: Важные исправления (в течение недели)

#### 2.1. Исправить все 23 ошибки flake8 (E501)

**Время:** 1-2 часа

**Шаги:**

1. Запустить flake8 с автофиксом (если используется autopep8):
```bash
autopep8 --in-place --max-line-length=88 apps/products/management/commands/deduplicate_images.py
```

2. Вручную исправить длинные строки в тестах:
   - Разбить длинные assert на несколько строк
   - Использовать переменные для длинных строк
   - Использовать f-строки вместо конкатенации

3. Пример исправления:
```python
# До
assert response_data["message"] == "This is a very long message that exceeds 88 characters limit"

# После
expected_message = (
    "This is a very long message that exceeds 88 characters limit"
)
assert response_data["message"] == expected_message
```

4. Проверить:
```bash
flake8 apps/ tests/ --count --select=E501 --show-source --statistics
```

5. Убедиться, что ошибок 0

#### 2.2. Настроить Swagger UI для тестового окружения

**Файлы:** freesport/settings/test.py, urls.py
**Время:** 1-2 часа

**Шаги:**

1. Добавить настройки в test.py:
```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'FREESPORT API (Test)',
    'DESCRIPTION': 'E-commerce API для тестирования',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': True,
}
```

2. Убедиться, что URL настроен в urls.py:
```python
urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

3. Убрать @pytest.mark.skip из test_swagger_ui_accessible
4. Запустить тест

#### 2.3. Упростить ProductFactory

**Файл:** tests/factories.py
**Время:** 3-4 часа

**Шаги:**

1. Рефакторинг: создать отдельную фабрику ProductWithVariantFactory:
```python
class ProductFactory(DjangoModelFactory):
    """Simple Product factory without auto-variant creation"""
    class Meta:
        model = Product

    name = factory.Faker("catch_phrase")
    brand = factory.SubFactory(BrandFactory)
    category = factory.SubFactory(CategoryFactory)
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name) + "-" + str(uuid.uuid4())[:8])

class ProductWithVariantFactory(ProductFactory):
    """Product with auto-created variant"""
    @factory.post_generation
    def variant(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is False:
            return

        variant_params = kwargs or {}
        variant_params.setdefault('retail_price', Decimal("1000.00"))
        variant_params.setdefault('stock_quantity', 10)

        ProductVariantFactory.create(product=self, **variant_params)
```

2. Обновить существующие тесты:
   - Заменить ProductFactory на ProductWithVariantFactory где нужен variant
   - Оставить ProductFactory для тестов только Product модели

3. Запустить все тесты:
```bash
pytest tests/unit/test_models/ -v
```

---

### Приоритет 3: Рекомендуемые улучшения (в течение месяца)

#### 3.1. Реализовать функции из TODO комментариев

**Время:** 2-3 дня (по мере приоритета Story)

**Список TODO:**

1. **Автоматический перенос корзины** (guest → authenticated)
   - Создать signal handler для user_logged_in
   - Написать интеграционный тест

2. **Management команда cleanup_guest_carts**
   - Создать команду в apps/cart/management/commands/
   - Написать unit тест

3. **Метод удаления/отмены заказа**
   - Добавить method cancel() в модель Order
   - Написать тесты для B2B/B2C workflow

4. **Фильтрация API** (Story 2.9)
   - Реализовать django-filter для ProductViewSet
   - Написать тесты для всех фильтров

5. **Определить требования авторизации для заказов**
   - Документировать в PRD
   - Обновить тесты B2C workflow

**Шаги:**

1. Создать отдельные задачи в issue tracker для каждого TODO
2. Приоритизировать по бизнес-ценности
3. Реализовать по одной функции за спринт
4. Удалить TODO комментарии после реализации

#### 3.2. Стабилизация тестов (race conditions)

**Время:** 1-2 дня

**Проблема:** "один тест на уникальность имеет небольшую нестабильность в CI"

**Шаги:**

1. Найти нестабильный тест:
```bash
grep -r "unique\|unikal" tests/ --include="*.py" -l
```

2. Проверить использование фабрик:
   - Убедиться, что используются LazyFunction для уникальных полей
   - Проверить, что нет жестко закодированных значений

3. Добавить retry механизм для CI:
```python
@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_unique_constraint(self):
    ...
```

4. Использовать изоляцию БД (truncate):
```python
@pytest.fixture(autouse=True)
def _db_isolation(self, db):
    """Ensure DB is clean before each test"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE products_product CASCADE")
```

#### 3.3. Добавить CI/CD проверки

**Файл:** .github/workflows/tests.yml
**Время:** 2-3 часа

**Шаги:**

1. Добавить flake8 проверку:
```yaml
- name: Lint with flake8
  run: |
    flake8 apps/ tests/ --count --select=E9,F63,F7,F82,E501 --show-source --statistics
    flake8 apps/ tests/ --count --exit-zero --max-line-length=88 --statistics
```

2. Добавить проверку покрытия:
```yaml
- name: Test with coverage
  run: |
    pytest --cov=apps --cov-report=xml --cov-fail-under=80
```

3. Добавить badge в README:
```markdown
![Coverage](https://img.shields.io/codecov/c/github/yourorg/freesport)
![Tests](https://img.shields.io/github/actions/workflow/status/yourorg/freesport/tests.yml)
```

---

## 🛠️ Инструменты и команды

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Только пропущенные тесты
pytest tests/ -v -m skip

# С покрытием
pytest tests/ --cov=apps --cov-report=html --cov-report=term

# Только упавшие тесты
pytest --lf -v

# Остановиться на первой ошибке
pytest -x -v
```

### Линтинг

```bash
# Проверить все ошибки flake8
flake8 apps/ tests/ --count --statistics

# Только E501 (длинные строки)
flake8 apps/ tests/ --select=E501

# Автофикс с black
black apps/ tests/

# Сортировка импортов
isort apps/ tests/
```

### Coverage анализ

```bash
# Генерация HTML отчета
pytest --cov=apps --cov-report=html
open htmlcov/index.html

# JSON отчет
pytest --cov=apps --cov-report=json

# Показать непокрытые строки
pytest --cov=apps --cov-report=term-missing
```

---

## ✅ Чеклист для агента AI

### Перед началом исправлений

- [ ] Создать ветку: `git checkout -b fix/backend-tests-improvements`
- [ ] Убедиться, что Docker запущен (для PostgreSQL)
- [ ] Активировать виртуальное окружение
- [ ] Установить зависимости: `pip install -r requirements.txt`

### Приоритет 1 (Критические)

- [ ] Реализовать валидацию min_order_quantity в CartItem
- [ ] Убрать @pytest.mark.skip из test_min_order_quantity_validation
- [ ] Исправить генерацию OpenAPI схемы (Decimal issue)
- [ ] Убрать @pytest.mark.skip из test_schema_includes_logout_endpoint
- [ ] Написать тесты для __str__() методов (Brand, Category, Product, etc.)
- [ ] Написать тесты для save() методов
- [ ] Написать тесты для Category.full_name()
- [ ] Проверить покрытие: должно быть >= 90% для products/models.py

### Приоритет 2 (Важные)

- [ ] Исправить все 23 ошибки flake8 E501
- [ ] Настроить Swagger UI для тестов
- [ ] Убрать @pytest.mark.skip из test_swagger_ui_accessible
- [ ] Рефакторинг ProductFactory → ProductWithVariantFactory
- [ ] Обновить существующие тесты для новой фабрики

### Приоритет 3 (Рекомендуемые)

- [ ] Создать задачи для TODO комментариев
- [ ] Исправить нестабильный тест (race condition)
- [ ] Добавить CI/CD проверки (flake8, coverage)
- [ ] Обновить документацию

### Финальная проверка

- [ ] Запустить все тесты: `pytest tests/ -v`
- [ ] Проверить coverage: `pytest --cov=apps --cov-report=term`
- [ ] Запустить flake8: `flake8 apps/ tests/`
- [ ] Запустить black: `black apps/ tests/ --check`
- [ ] Запустить isort: `isort apps/ tests/ --check`
- [ ] Коммит и push: `git push origin fix/backend-tests-improvements`
- [ ] Создать Pull Request

---

## 📊 Метрики успеха

| Метрика | Текущее значение | Целевое значение |
|---------|------------------|------------------|
| Покрытие кода | 83.33% | >= 90% |
| Пропущенные тесты | 3 | 0 |
| Ошибки flake8 | 23 | 0 |
| TODO комментарии | 14 | Задокументированы |
| Нестабильные тесты | 1 | 0 |
| Время выполнения тестов | ? | < 5 минут |

---

## 📝 Дополнительные заметки

### Рекомендации по стилю

1. **Всегда используйте factory.LazyFunction для уникальных полей:**
```python
email = factory.LazyFunction(lambda: f"user-{uuid.uuid4().hex[:8]}@test.com")
```

2. **Используйте timezone-aware datetime:**
```python
from django.utils import timezone
created_at = factory.LazyFunction(timezone.now)
```

3. **Явно указывайте параметры в тестах:**
```python
# Плохо
product = ProductFactory.create()

# Хорошо
product = ProductFactory.create(
    name="Test Product",
    retail_price=Decimal("999.99"),
    stock_quantity=5
)
```

### Полезные ссылки

- [Pytest Documentation](https://docs.pytest.org/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [Flake8 Error Codes](https://flake8.pycqa.org/en/latest/user/error-codes.html)

---

**Следующие шаги:**
Начать с Приоритета 1, исправлять критические проблемы по одной, коммитить после каждого успешного исправления.

**Ожидаемое время:** 2-3 рабочих дня для всех приоритетов 1-2.
