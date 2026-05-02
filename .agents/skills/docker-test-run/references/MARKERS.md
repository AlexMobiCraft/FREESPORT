# Pytest-маркеры FREESPORT

В проекте используются кастомные маркеры для классификации тестов.

## Доступные маркеры

### `unit`
Юнит-тесты бэкенда (модульные тесты). Быстрые, не требуют БД/внешних сервисов.

```bash
pytest -m unit
```

### `integration`
Интеграционные тесты. Требуют PostgreSQL, Redis, внешние API.

```bash
pytest -m integration
```

### `data_dependent`
Тесты, зависящие от внешних данных (1С-импорт, сторонние API).

```bash
# Запуск только тестов, НЕ зависящих от внешних данных
pytest -m "not data_dependent"
```

## Комбинации

```bash
# Все кроме data_dependent
pytest -m "not data_dependent"

# Unit + coverage
pytest -m unit --cov=apps --cov-report=term-missing

# Все тесты с coverage
pytest -v --cov=apps --cov-report=term-missing
```
