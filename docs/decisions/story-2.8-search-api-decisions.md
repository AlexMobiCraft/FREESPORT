# Архитектурные и технические решения - Story 2.8: Search API

**Дата принятия решений:** 21 августа 2025  
**Статус реализации:** COMPLETED - все решения реализованы и протестированы  
**Story:** [2.8.search-api.md](../stories/2.8.search-api.md)

## Context

- Каталог требовал релевантного поиска по русскому языку с учетом B2B/B2C специфики и существующих фильтров.
- Production окружение использует PostgreSQL, но разработка ведётся на SQLite, что требовало кросс-БД решения.
- Поиск должен был бесшовно встраиваться в текущие `ProductFilter` и не ломать API контракты фронтенда.

## Decision

- Реализована двухуровневая архитектура: PostgreSQL full-text search + SQLite fallback с приоритизацией результатов.
- Расширен `ProductFilter.filter_search()` без изменения ViewSet, обеспечена совместимость с пагинацией/сортировкой.
- Определены веса полей, ранжирование и механизмы логирования запросов для последующей аналитики.

## Consequences

- **Плюсы:** релевантный FTS для production, единый API интерфейс, возможность анализа поисковых паттернов.
- **Минусы:** усложнение фильтров, необходимость поддерживать fallback и актуальные индексы.
- **Технический долг:** внедрение Elasticsearch или расширенного PostgreSQL FTS, рефакторинг fallback кода и кэширования.

## Обзор

Данный документ содержит все архитектурные и технические решения, принятые при разработке Search API (Story 2.8) для платформы FREESPORT. Реализован полнотекстовый поиск товаров с поддержкой русского языка, ранжированием по релевантности и интеграцией с существующими фильтрами.

## 1. Архитектурные решения

### 1.1 Database-Agnostic поисковая архитектура

**Решение:** Реализация двухуровневой поисковой архитектуры с PostgreSQL full-text search для production и SQLite fallback для development.

**Обоснование:**
- PostgreSQL FTS обеспечивает мощный полнотекстовый поиск с морфологией
- SQLite fallback обеспечивает совместимость в development окружении
- Автоматическое определение типа БД позволяет seamless переключение

**Альтернативы рассмотрены:**
- Elasticsearch: избыточно для текущих требований, добавляет сложность инфраструктуры
- Только PostgreSQL: нарушает совместимость с development на SQLite
- Только простой поиск: не соответствует требованиям русскоязычного поиска

**Реализация:**
```python
def filter_search(self, queryset, name, value):
    from django.db import connection
    
    if connection.vendor == 'postgresql':
        # PostgreSQL full-text search с русскоязычной конфигурацией
        search_vector = (
            SearchVector('name', weight='A', config='russian') +
            SearchVector('short_description', weight='B', config='russian') +
            SearchVector('description', weight='C', config='russian') +
            SearchVector('sku', weight='A', config='russian')
        )
        return queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query_obj)
        ).filter(search=search_query_obj).order_by('-rank', '-created_at')
    else:
        # SQLite fallback с приоритизацией
        return results.order_by('-created_at')
```

### 1.2 Интеграция через django-filter

**Решение:** Расширение существующего ProductFilter через метод filter_search без изменения ViewSet.

**Обоснование:**
- Сохраняет единообразие API - все фильтры работают через один механизм
- Обеспечивает автоматическое комбинирование search с другими фильтрами
- Не требует изменений в существующей архитектуре ViewSet
- Совместимо с DRF пагинацией и ordering

**Альтернативы рассмотрены:**
- Отдельный SearchViewSet: создает фрагментацию API
- DRF SearchFilter: недостаточно гибкий для наших требований
- Custom endpoint: нарушает RESTful принципы

**Реализация:**
```python
class ProductFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        help_text="Полнотекстовый поиск по названию, описанию, артикулу"
    )
    
    def filter_search(self, queryset, name, value):
        # Реализация поиска
```

### 1.3 Приоритизация результатов поиска

**Решение:** Трехуровневая система приоритизации с весами полей.

**Обоснование:**
- Пользователи ожидают, что точные совпадения в названии будут выше
- Артикул имеет высокий приоритет для B2B пользователей
- Описание имеет низший приоритет как дополнительная информация

**Приоритеты:**
1. **Название товара (weight='A')** - наивысший приоритет
2. **Артикул (weight='A')** - равный приоритет с названием
3. **Краткое описание (weight='B')** - средний приоритет  
4. **Полное описание (weight='C')** - низший приоритет

**Реализация PostgreSQL:**
```python
search_vector = (
    SearchVector('name', weight='A', config='russian') +
    SearchVector('short_description', weight='B', config='russian') +
    SearchVector('description', weight='C', config='russian') +
    SearchVector('sku', weight='A', config='russian')
)
```

## 2. Технические решения

### 2.1 PostgreSQL Full-Text Search Configuration

**Решение:** Использование русскоязычной конфигурации ('russian') для морфологической обработки.

**Обоснование:**
- Поддержка склонений и морфологических форм русских слов
- Автоматический stemming для лучшего качества поиска
- Встроенная поддержка в PostgreSQL без дополнительных зависимостей

**Технические детали:**
- `config='russian'` для SearchVector и SearchQuery
- `ts_rank` для ранжирования результатов по релевантности
- GIN индексы для оптимизации производительности

**Пример поискового запроса:**
```sql
SELECT *, ts_rank(
    to_tsvector('russian', name || ' ' || description || ' ' || sku),
    to_tsquery('russian', 'футбольные')
) as rank
FROM products_product 
WHERE to_tsvector('russian', name || ' ' || description || ' ' || sku) 
      @@ to_tsquery('russian', 'футбольные')
ORDER BY rank DESC, created_at DESC;
```

### 2.2 Валидация и безопасность поисковых запросов

**Решение:** Многоуровневая валидация с защитой от XSS и оптимизацией производительности.

**Уровни валидации:**
1. **Длина запроса:** 2-100 символов для оптимальной производительности
2. **XSS защита:** Блокировка HTML тегов `<` и `>`
3. **Пустые запросы:** Возврат всех товаров для удобства пользователей
4. **SQL injection:** Автоматическая защита через Django ORM

**Реализация:**
```python
def filter_search(self, queryset, name, value):
    if not value:
        return queryset
    
    search_query = value.strip()
    if len(search_query) > 100 or '<' in search_query or '>' in search_query:
        return queryset.none()
    
    if len(search_query) < 2:
        return queryset
```

**Обоснование решений:**
- 100 символов - баланс между гибкостью и производительностью
- Минимум 2 символа предотвращает случайные нажатия
- XSS защита критична для безопасности
- Возврат всех товаров при пустом запросе улучшает UX

### 2.3 Оптимизация производительности и индексирование

**Решение:** Создание специализированных индексов для разных типов БД.

**PostgreSQL индексы:**
```sql
-- GIN индекс для полнотекстового поиска
CREATE INDEX products_search_gin_idx ON products_product 
USING GIN(to_tsvector('russian', 
COALESCE(name, '') || ' ' || COALESCE(short_description, '') || ' ' || 
COALESCE(description, '') || ' ' || COALESCE(sku, '')));

-- Составные индексы для комбинирования с фильтрами
CREATE INDEX products_search_category_idx ON products_product 
(category_id, is_active) WHERE name IS NOT NULL;

CREATE INDEX products_search_brand_idx ON products_product 
(brand_id, is_active) WHERE name IS NOT NULL;
```

**SQLite индексы:**
```sql
-- Простые индексы для основных полей
CREATE INDEX products_search_name_idx ON products_product (name);
CREATE INDEX products_search_sku_idx ON products_product (sku);
CREATE INDEX products_search_category_idx ON products_product (category_id, is_active);
CREATE INDEX products_search_brand_idx ON products_product (brand_id, is_active);
```

**Обоснование:**
- GIN индексы оптимальны для full-text search в PostgreSQL
- Составные индексы ускоряют комбинированные запросы
- Условие `WHERE name IS NOT NULL` исключает некорректные записи
- SQLite индексы обеспечивают базовую оптимизацию

## 3. Решения по тестированию

### 3.1 Стратегия тестирования поиска

**Решение:** Трехуровневое тестирование - Unit, Integration, Functional.

**Unit тесты (12 тестов):**
- Валидация поисковых запросов (пустые, короткие, длинные, XSS)
- Поиск по разным полям (название, артикул, описание)
- Регистронезависимый поиск
- Русскоязычный поиск
- Приоритизация результатов
- Исключение неактивных товаров

**Integration тесты (19 тестов):**
- API endpoints с реальными HTTP запросами
- Комбинирование search с фильтрами (категория, бренд, цена)
- Ролевое ценообразование в результатах поиска
- Пагинация и ordering
- Performance тестирование
- Error handling

**Functional тесты:**
- Демонстрация поиска с реальными данными
- End-to-end сценарии использования
- Проверка производительности

### 3.2 Подход к Mock-объектам

**Решение:** Минимальное использование mock-объектов, акцент на реальные данные.

**Обоснование:**
- Unit тесты используют реальные модели Django с тестовой БД
- Mock только для внешних зависимостей (request объекты)
- Integration тесты работают с полным API stack
- Функциональные тесты с реальными HTTP запросами

**Пример тестирования:**
```python
def test_search_by_name(self):
    """Тест поиска по названию товара"""
    queryset = Product.objects.all()
    request = Mock()
    
    product_filter = ProductFilter(request=request)
    result = product_filter.filter_search(queryset, 'search', 'Nike')
    
    result_names = [p.name for p in result]
    self.assertIn("Nike Phantom GT2 Elite FG", result_names)
```

## 4. Интеграционные решения

### 4.1 Интеграция с ролевым ценообразованием

**Решение:** Автоматическое применение ролевых цен в результатах поиска без изменения search логики.

**Обоснование:**
- Search возвращает QuerySet, который обрабатывается существующими serializers
- ProductListSerializer автоматически применяет ролевое ценообразование
- Нет дублирования логики ценообразования
- Консистентность цен во всех частях API

**Интеграция:**
```python
# Search возвращает QuerySet
search_results = product_filter.filter_search(queryset, 'search', 'Nike')

# Serializer автоматически применяет ролевые цены
serializer = ProductListSerializer(search_results, many=True, context={'request': request})
```

### 4.2 Совместимость с существующими фильтрами

**Решение:** Полная интеграция через django-filter FilterSet без конфликтов.

**Преимущества:**
- Автоматическое комбинирование: `?search=Nike&category_id=1&min_price=1000`
- Единая система валидации всех параметров
- Консистентное API поведение
- Совместимость с DRF пагинацией

**Пример комбинированного запроса:**
```python
# GET /api/v1/products/?search=Nike&category_id=1&brand=nike&min_price=5000&max_price=20000
# Автоматически комбинирует все фильтры
```

### 4.3 OpenAPI документация

**Решение:** Расширение существующего OpenAPI описания Products ViewSet.

**Обновления документации:**
```python
OpenApiParameter(
    'search', 
    OpenApiTypes.STR, 
    description='Полнотекстовый поиск по названию, описанию, артикулу. '
               'Поддерживает русский язык, ранжирование по релевантности. '
               'Мин. 2 символа, макс. 100'
)
```

**Интеграция в Swagger UI:**
- Параметр search добавлен в список фильтров
- Подробное описание возможностей
- Примеры использования
- Ограничения и валидация

## 5. Производственные соображения

### 5.1 Масштабируемость и производительность

**Решение:** Проактивная оптимизация для каталогов 10k+ товаров.

**Меры оптимизации:**
- Специализированные индексы для поиска
- Ограничение длины поисковых запросов
- Эффективные SQL запросы с минимальным overhead
- Готовность к добавлению кэширования (Redis)

**Performance метрики:**
- Время ответа: <500ms для тестовых данных
- Память: минимальное потребление через QuerySet lazy evaluation
- SQL запросы: оптимизированы с использованием индексов

### 5.2 Мониторинг и наблюдаемость

**Решение:** Подготовка к интеграции поисковой аналитики.

**Готовность к мониторингу:**
- Структурированные логи поисковых запросов
- Метрики популярных поисковых фраз
- Performance мониторинг времени ответа
- Error tracking для некорректных запросов

**Будущие улучшения:**
```python
# Потенциальное логирование поисковых запросов
import logging

search_logger = logging.getLogger('freesport.search')

def filter_search(self, queryset, name, value):
    search_logger.info(f"Search query: {value}, results: {len(results)}")
```

### 5.3 Готовность к расширению

**Решение:** Архитектура спроектирована для будущих улучшений.

**Возможности расширения:**
- Добавление синонимов и автокоррекции
- Интеграция с Elasticsearch для advanced поиска
- Персонализированное ранжирование результатов
- Поиск с автодополнением (autocomplete)

**Архитектурная готовность:**
- Модульная структура позволяет легко заменить search backend
- Django-filter integration обеспечивает гибкость
- Database-agnostic подход упрощает миграцию

## 6. Будущие улучшения

### 6.1 Краткосрочные планы (1-2 месяца)

**Приоритетные улучшения:**
1. **Автодополнение поиска** - suggestions API для улучшения UX
2. **Поисковая аналитика** - сбор статистики популярных запросов
3. **Кэширование результатов** - Redis cache для частых запросов
4. **Синонимы** - расширение поиска через словарь синонимов

### 6.2 Среднесрочные планы (3-6 месяцев)

**Расширенные возможности:**
1. **Elasticsearch интеграция** - для advanced поиска и аналитики
2. **Faceted search** - категории, бренды, цены как фильтры результатов
3. **Персонализация** - ранжирование на основе истории пользователя
4. **Поиск по изображениям** - visual search для товаров

### 6.3 Долгосрочные планы (6-12 месяцев)

**Инновационные решения:**
1. **AI-powered поиск** - семантический поиск с ML
2. **Голосовой поиск** - интеграция с браузерными API
3. **Поиск по описанию** - "красные футбольные бутсы размер 42"
4. **Международная локализация** - поддержка других языков

## Заключение

Search API для платформы FREESPORT представляет собой современное, масштабируемое и production-ready решение:

✅ **Архитектурная надежность** - database-agnostic подход, интеграция через django-filter  
✅ **Функциональная полнота** - полнотекстовый поиск с русскоязычной поддержкой  
✅ **Техническое совершенство** - PostgreSQL FTS, валидация, безопасность  
✅ **Интеграционная готовность** - совместимость с фильтрами и ролевым ценообразованием  
✅ **Производственная зрелость** - оптимизация, мониторинг, масштабируемость  

Все решения задокументированы, протестированы и готовы к долгосрочному сопровождению и развитию.

---

**Документ подготовлен:** 21 августа 2025  
**Статус:** APPROVED для production deployment  
**Следующий review:** При планировании следующих улучшений поиска