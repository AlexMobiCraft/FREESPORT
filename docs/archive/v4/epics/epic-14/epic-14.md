# Epic 14: Product Attributes System

## Epic Overview

Реализация полноценной системы атрибутов товаров для структурированного хранения характеристик (размер, цвет, материал и т.д.) вместо неструктурированного JSON поля `specifications`.

## Business Value

- **Структурированные данные:** Переход от JSON поля к нормализованным моделям БД
- **Фильтрация каталога:** Возможность создания динамических фильтров по атрибутам
- **Качество данных:** Дедупликация и модерация атрибутов администратором
- **Интеграция с 1С:** Автоматическая синхронизация атрибутов из propertiesGoods/propertiesOffers
- **SEO оптимизация:** Структурированная разметка характеристик товаров

## Epic Status

**В разработке** (In Progress)

## Stories

### ✅ Story 14.1: Attribute Models
**Status:** Done
**File:** [14.1.attribute-models.md](./14.1.attribute-models.md)

Создание моделей `Attribute` и `AttributeValue` для хранения атрибутов товаров.

**Deliverables:**
- Модели Attribute и AttributeValue
- M2M связи с Product и ProductVariant
- Миграции БД
- Unit-тесты моделей

---

### ✅ Story 14.2: Import Attributes from 1C
**Status:** Ready for Done
**File:** [14.2.import-attributes.md](./14.2.import-attributes.md)

Импорт атрибутов из XML файлов 1С (propertiesGoods/*.xml, propertiesOffers/*.xml).

**Deliverables:**
- AttributeImportService для парсинга XML
- Management command `import_attributes`
- Django Admin UI для просмотра атрибутов
- 17 comprehensive тестов
- Реальные данные: 458 атрибутов, 12,260 значений

**Key Achievements:**
- ✅ XXE защита через defusedxml
- ✅ Идемпотентный импорт (update_or_create)
- ✅ Inline display атрибутов в админке
- ✅ Dry-run режим для валидации

---

### 🚧 Story 14.3: Attribute Deduplication
**Status:** Draft
**File:** [14.3.attribute-deduplication.md](./14.3.attribute-deduplication.md)

Устранение дублирования атрибутов при импорте и добавление флага активности.

**Goal:**
- Объединение дубликатов атрибутов по нормализованному имени
- Флаг `is_active` для ручной модерации администратором
- Система маппингов 1С ID на master-атрибуты

**Key Features:**
- `Attribute.normalized_name` — уникальное поле для дедупликации
- `Attribute.is_active` — default=False, требует активации
- `Attribute1CMapping` — связь всех 1С ID с master-атрибутом
- `AttributeValue1CMapping` — маппинг значений атрибутов
- Django Admin actions для массовой активации/объединения

**Sub-stories:**
- 14.3.1: Модели Attribute1CMapping + поле is_active
- 14.3.2: Модель AttributeValue1CMapping
- 14.3.3: Обновление логики импорта с дедупликацией
- 14.3.4: Django Admin для управления атрибутами
- 14.3.5: Обновление UI импорта
- 14.3.6: Фильтрация по активным атрибутам в API
- 14.3.7: Документация и тестирование

**Expected Results:**
- **До:** 458 атрибутов, ~30-40% дубликатов, все активны
- **После:** ~280-320 уникальных атрибутов, 0 дубликатов, ~50-100 активировано

**Estimated Effort:** 35 story points (~3-4 спринта)

---

### 📋 Story 14.4: Link Attributes to Products
**Status:** Draft
**File:** [14.4.link-attributes.md](./14.4.link-attributes.md)

Связывание атрибутов с товарами при импорте из 1С.

**Goal:**
- Парсинг связей атрибутов из goods.xml и offers.xml
- Создание M2M связей Product/ProductVariant ↔ AttributeValue
- Обработка missing attributes

**Dependencies:**
- Story 14.2 (Import Attributes)
- Story 14.3 (Deduplication) — рекомендуется

---

### 📋 Story 14.5: API Enhancement
**Status:** Draft
**File:** [14.5.api-enhancement.md](./14.5.api-enhancement.md)

Добавление атрибутов в API эндпоинты каталога товаров.

**Goal:**
- Отображение атрибутов в ProductSerializer
- Фильтрация только активных атрибутов
- OpenAPI спецификация обновлена

**Dependencies:**
- Story 14.3 (для фильтрации по is_active)
- Story 14.4 (для связей с товарами)

---

### 📋 Story 14.6: Filtering & Facets
**Status:** Draft
**File:** [14.6.filtering-facets.md](./14.6.filtering-facets.md)

Реализация динамических фильтров по атрибутам в каталоге.

**Goal:**
- Faceted search по атрибутам
- Динамическое построение фильтров
- Frontend интеграция

**Dependencies:**
- Story 14.5 (API Enhancement)

---

## Technical Architecture

### Current State (до Epic 14)
```python
Product {
    specifications: JSONField  # Неструктурированные данные
}
```

### Target State (после Epic 14)
```python
Attribute {
    name: str
    slug: str
    normalized_name: str (unique)  # Для дедупликации
    is_active: bool (default=False)  # Модерация
}

Attribute1CMapping {
    attribute: FK(Attribute)
    onec_id: str (unique)
    source: choices['goods', 'offers']
}

AttributeValue {
    attribute: FK(Attribute)
    value: str
    slug: str
}

AttributeValue1CMapping {
    attribute_value: FK(AttributeValue)
    onec_id: str (unique)
}

Product {
    attributes: M2M(AttributeValue)
    specifications: JSONField (legacy, optional)
}

ProductVariant {
    attributes: M2M(AttributeValue)
}
```

### Deduplication Flow

```
1С Import (propertiesGoods + propertiesOffers)
    ↓
AttributeImportService
    ↓ normalize_attribute_name("Размер") → "размер"
    ↓
Check: Attribute.objects.filter(normalized_name="размер").exists()
    ↓
    ├─ Да → Create Attribute1CMapping only
    └─ Нет → Create Attribute (is_active=False) + Attribute1CMapping
    ↓
Administrator Manual Activation (Django Admin)
    ↓
API Filter (only is_active=True)
    ↓
Frontend Catalog
```

## Related Epics

- **Epic 13:** Brand Deduplication — референсная реализация аналогичного паттерна
- **Epic 3:** 1C Integration — базовая интеграция с 1С
- **Epic 10:** Catalog & Filtering — использование атрибутов для фильтрации

## Key Metrics

### Story 14.2 (Import) - Completed
- ✅ 458 атрибутов импортировано
- ✅ 12,260 значений атрибутов
- ✅ 22 XML файла обработано
- ✅ 17/17 тестов пройдено
- ✅ Code quality: 95/100

### Story 14.3 (Deduplication) - Planned
- 🎯 ~280-320 уникальных атрибутов (после дедупликации)
- 🎯 0 дубликатов в каталоге
- 🎯 ~50-100 атрибутов активировано вручную
- 🎯 Сохранены все 458 маппингов для связи с 1С

## Timeline

- **Sprint 1-2:** Story 14.1 (Models) ✅ + Story 14.2 (Import) ✅
- **Sprint 3-5:** Story 14.3 (Deduplication) 🚧
- **Sprint 6:** Story 14.4 (Link to Products)
- **Sprint 7:** Story 14.5 (API Enhancement)
- **Sprint 8:** Story 14.6 (Filtering & Facets)

**Total Estimated Duration:** 8 спринтов (~4 месяца)

## Definition of Done (Epic Level)

- [ ] Все 6 stories выполнены и протестированы
- [ ] Тесты покрывают >85% кода Epic
- [ ] Документация обновлена (архитектура, API, руководства)
- [ ] Интеграционное тестирование с реальными данными из 1С
- [ ] Нет регрессий в существующем функционале каталога
- [ ] Frontend интеграция завершена (фильтры, карточки товаров)
- [ ] Performance тестирование пройдено
- [ ] Production deployment успешен

## Contact & Ownership

- **Product Owner:** Sarah
- **Tech Lead:** [TBD]
- **QA Lead:** Quinn
- **Dev Agent:** Claude Sonnet 4.5

## References

- [PRD: Product Attributes System](../../PRD.md)
- [Architecture: Database Schema](../../architecture.md)
- [Epic 13: Brand Deduplication](../epic-13/epic-13.brand-deduplication.md)
- [1C Integration Documentation](../../guides/1c-integration.md)
