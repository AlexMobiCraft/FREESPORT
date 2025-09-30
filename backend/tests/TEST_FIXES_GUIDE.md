# Руководство по исправлению тестов

## Проблемы, обнаруженные в CI

### 1. Ошибка доступа к базе данных

**Проблема:**
```
RuntimeError: Database access not allowed, use the "django_db" mark, or the "db" or "transactional_db" fixtures to enable it.
```

**Решение:**
Добавьте декоратор `@pytest.mark.django_db` к тестам, которые обращаются к базе данных:

```python
import pytest

@pytest.mark.django_db
def test_serializer(...):
    # Ваш тест
    pass
```

Или для всего класса:

```python
@pytest.mark.django_db
class TestMySerializer:
    def test_something(self):
        # Ваш тест
        pass
```

### 2. Ошибка сравнения с Mock-объектом

**Проблема:**
```
assert "<Mock name='...'>" == 'Доставлен'
```

**Причина:**
Вы сравниваете сам Mock-объект, а не результат вызова метода.

**Неправильно:**
```python
result = mock_instance.get_status_display
assert result == 'Доставлен'  # Сравнивается Mock, а не результат
```

**Правильно:**
```python
result = mock_instance.get_status_display()  # Вызываем метод
assert result == 'Доставлен'
```

### 3. Дублирование ключей в базе данных

**Проблема:**
```
duplicate key value violates unique constraint
```

**Решение:**
Используйте уникальные значения для полей с ограничением unique:

```python
# Используйте функцию get_unique_suffix() из conftest.py
from tests.conftest import get_unique_suffix

def test_something():
    suffix = get_unique_suffix()
    product = product_factory.create(
        sku=f"TEST-{suffix}",
        name=f"Test Product {suffix}"
    )
```

### 4. Соединения с БД не закрываются

**Проблема:**
```
database 'test_test_db' is being accessed by other users
```

**Решение:**
Уже исправлено! Добавлена автоматическая фикстура `close_db_connections` в `conftest.py`, которая закрывает все соединения после каждого теста.

Если нужно явное закрытие в конкретном тесте:

```python
def test_something():
    # Ваш тест
    
    # Явное закрытие соединений
    from django.db import connections
    connections.close_all()
```

## Чеклист перед коммитом

- [ ] Все тесты, использующие БД, имеют декоратор `@pytest.mark.django_db`
- [ ] Все вызовы методов Mock-объектов включают скобки `()`
- [ ] Используются уникальные значения для полей с ограничением unique
- [ ] Тесты проходят локально: `pytest tests/`
- [ ] Нет предупреждений о незакрытых соединениях

## Запуск тестов

### Локально
```bash
cd backend
pytest tests/ -v
```

### Конкретный файл
```bash
pytest tests/unit/test_serializers/test_order_serializers.py -v
```

### Конкретный тест
```bash
pytest tests/unit/test_serializers/test_order_serializers.py::TestOrderDetailSerializer::test_serializer_fields -v
```

### С покрытием
```bash
pytest --cov=apps --cov-report=html
```

## Полезные команды

### Проверка настроек Django
```bash
python manage.py check --deploy
```

### Применение миграций
```bash
python manage.py migrate --settings=freesport.settings.test
```

### Закрытие всех соединений с БД
```python
python -c "import django; django.setup(); from django.db import connections; connections.close_all()"
```
