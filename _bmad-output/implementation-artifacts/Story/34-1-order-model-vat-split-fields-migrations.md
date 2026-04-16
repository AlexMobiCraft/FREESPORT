# Story 34.1: Order/OrderItem — новые поля для VAT-разбивки + миграции

Status: ready-for-dev

## Story

As a **разработчик**,
I want **добавить поля parent_order, is_master, vat_group в модель Order и поле vat_rate в OrderItem**,
so that **система может хранить parent/child структуру заказов и делать корректную разбивку по ставке НДС для экспорта в 1С**.

## Acceptance Criteria

1. **AC1:** `Order` имеет поле `parent_order` — ForeignKey на себя (self), `null=True, blank=True`, `on_delete=CASCADE`, `related_name='sub_orders'`.
2. **AC2:** `Order` имеет поле `is_master` — BooleanField, `default=True`, `verbose_name='Мастер-заказ'`.
3. **AC3:** `Order` имеет поле `vat_group` — DecimalField(`max_digits=5, decimal_places=2`), `null=True, blank=True`, `verbose_name='Группа НДС (%)'`.
4. **AC4:** `OrderItem` имеет поле `vat_rate` — DecimalField(`max_digits=5, decimal_places=2`), `null=True, blank=True`, `verbose_name='Ставка НДС (%)'`.
5. **AC5:** Миграция создана (`0012_*.py`) и применяется без ошибок на существующих данных (все новые поля имеют `null=True` или `default`).
6. **AC6:** Django Admin обновлён — новые поля видны в форме заказа (`OrderAdmin`): `parent_order`, `is_master`, `vat_group` в новом fieldset "VAT / Субзаказы".
7. **AC7:** Сериализаторы обновлены: `is_master`, `vat_group` добавлены в `OrderDetailSerializer` как `read_only`. `OrderCreateSerializer` — НЕ изменять. `OrderListSerializer` — добавить `is_master` как `read_only` (фильтрация по нему будет в Story 34-2).
8. **AC8:** Unit-тесты покрывают: дефолтные значения всех новых полей, создание дочернего заказа с `parent_order`, проверку `related_name` (`sub_orders`), сериализацию новых полей.

## Tasks / Subtasks

- [ ] Task 1: Добавить поля в модель `Order` (AC: 1, 2, 3)
  - [ ] 1.1: Добавить `parent_order` ForeignKey в `Order` (см. раздел "Dev Notes" — точный код)
  - [ ] 1.2: Добавить `is_master` BooleanField в `Order`
  - [ ] 1.3: Добавить `vat_group` DecimalField в `Order`
  - [ ] 1.4: Обновить TYPE_CHECKING блок — добавить аннотации типов для новых полей
  - [ ] 1.5: Обновить docstring класса `Order`
- [ ] Task 2: Добавить поле `vat_rate` в модель `OrderItem` (AC: 4)
  - [ ] 2.1: Добавить `vat_rate` DecimalField в `OrderItem` после существующих snapshot-полей
  - [ ] 2.2: Обновить TYPE_CHECKING блок `OrderItem`
  - [ ] 2.3: Обновить метод `save()` в `OrderItem` — снимок `vat_rate` из `variant.vat_rate` при первом сохранении (аналогично `product_name` и `product_sku`)
- [ ] Task 3: Создать и применить миграцию (AC: 5)
  - [ ] 3.1: `python manage.py makemigrations orders --name="add_vat_split_fields"`
  - [ ] 3.2: Проверить сгенерированную миграцию — должна быть `0012_add_vat_split_fields.py`
  - [ ] 3.3: Убедиться что все новые поля в миграции имеют `null=True` или `default`
  - [ ] 3.4: Применить миграцию в тестовой среде Docker
- [ ] Task 4: Обновить Django Admin (AC: 6)
  - [ ] 4.1: Добавить новый fieldset "VAT / Субзаказы" в `OrderAdmin`
  - [ ] 4.2: Включить в fieldset: `('parent_order', 'is_master', 'vat_group')`
  - [ ] 4.3: Добавить `is_master` в `list_display`
  - [ ] 4.4: Добавить `is_master` в `list_filter`
- [ ] Task 5: Обновить сериализаторы (AC: 7)
  - [ ] 5.1: `OrderDetailSerializer`: добавить `is_master`, `vat_group` как `read_only`
  - [ ] 5.2: `OrderListSerializer`: добавить `is_master` как `read_only`
  - [ ] 5.3: `OrderCreateSerializer`: НЕ изменять
- [ ] Task 6: Unit-тесты (AC: 8)
  - [ ] 6.1: Тест дефолтных значений новых полей: `is_master=True`, `parent_order=None`, `vat_group=None`
  - [ ] 6.2: Тест создания дочернего заказа: `Order(parent_order=master, is_master=False, vat_group=Decimal("5.00"))`
  - [ ] 6.3: Тест `related_name`: `master.sub_orders.count() == 1` после создания дочернего
  - [ ] 6.4: Тест `OrderItem.vat_rate`: по умолчанию `None`, устанавливается из `variant.vat_rate` при `save()`
  - [ ] 6.5: Тест сериализации: `is_master`, `vat_group` присутствуют в `OrderDetailSerializer` output
  - [ ] 6.6: Тест сериализации: `is_master` присутствует в `OrderListSerializer` output
  - [ ] 6.7: Негативный тест: `is_master`, `vat_group` **НЕ** принимаются `OrderCreateSerializer` как input

## Dev Notes

### Точный код для новых полей модели `Order`

Добавить в `backend/apps/orders/models.py` в класс `Order`, в секцию "# Интеграция с 1С" (после поля `export_skipped`), новый блок "# VAT / Субзаказы":

```python
# VAT / Субзаказы
parent_order = cast(
    "Order | None",
    models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sub_orders",
        verbose_name="Мастер-заказ",
        help_text="Заполнено только для дочерних субзаказов",
    ),
)
is_master = cast(
    bool,
    models.BooleanField(
        "Мастер-заказ",
        default=True,
        help_text="True — заказ видит клиент; False — технический субзаказ для 1С",
    ),
)
vat_group = cast(
    "Decimal | None",
    models.DecimalField(
        "Группа НДС (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Ставка НДС группы товаров в этом субзаказе (5 или 22)",
    ),
)
```

Также добавить в TYPE_CHECKING блок `Order`:
```python
parent_order: "Order | None"
is_master: bool
vat_group: "Decimal | None"
sub_orders: "RelatedManager[Order]"
```

### Точный код для нового поля `OrderItem.vat_rate`

Добавить в класс `OrderItem` после поля `variant_info`:

```python
vat_rate = cast(
    "Decimal | None",
    models.DecimalField(
        "Ставка НДС (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Снимок ставки НДС варианта на момент создания заказа",
    ),
)
```

Добавить в TYPE_CHECKING блок `OrderItem`:
```python
vat_rate: "Decimal | None"
```

Обновить `OrderItem.save()` — добавить снимок `vat_rate` по аналогии с существующими snapshot-полями:
```python
if self.variant and self.vat_rate is None:
    vat = getattr(self.variant, "vat_rate", None)
    if vat is not None:
        self.vat_rate = Decimal(str(vat))
```
Вставить этот блок после блока снимка `variant_info` в методе `save()`.

### Ключевые файлы для изменения

| Файл | Действие |
|------|----------|
| `backend/apps/orders/models.py` | Добавить поля в `Order` и `OrderItem` |
| `backend/apps/orders/admin.py` | Добавить fieldset "VAT / Субзаказы" |
| `backend/apps/orders/serializers.py` | Обновить Detail и List сериализаторы |
| `backend/apps/orders/migrations/0012_*.py` | Автогенерация через makemigrations |
| `backend/tests/unit/test_models/test_order_models.py` | Добавить тесты новых полей |
| `backend/tests/unit/test_orders_1c_fields.py` | Опционально — добавить тесты сериализаторов |

### Текущее состояние модели Order (на момент истории)

Поля, актуальные для контекста:
- `order_number`, `user`, `customer_name/email/phone`
- `status` (choices из `ORDER_STATUSES` в `constants.py`)
- `total_amount`, `discount_amount`, `delivery_cost`
- `delivery_address`, `delivery_method`, `delivery_date`, `tracking_number`
- `payment_method`, `payment_status`, `payment_id`
- `sent_to_1c`, `sent_to_1c_at`, `status_1c` (добавлены в Story 4.1)
- `export_skipped`, `paid_at`, `shipped_at` (добавлены позже)
- `notes`, `created_at`, `updated_at`

Текущий `Meta.indexes` включает partial index `idx_order_sent_to_1c_created` — сохранить его без изменений.

### Текущие миграции orders

Последняя: `0011_add_payment_shipment_dates.py`. Новая будет `0012_add_vat_split_fields.py`.

### Паттерн снимков в `OrderItem` (соответствие)

Существующие snapshot-поля: `product_name`, `product_sku`, `variant_info` — заполняются в `save()` при первом создании (условие `if not self.product_name`).  
Для `vat_rate` используй условие `if self.vat_rate is None` — это не строка, поэтому `not` не подходит.

### Паттерн `cast()` для TYPE_CHECKING

Весь проект использует `cast()` из `typing` для типизации полей Django:
```python
from typing import TYPE_CHECKING, Any, cast
# ...
is_master = cast(bool, models.BooleanField(...))
```
Следуй этому паттерну строго.

### Архитектурный контекст (зачем нужны эти поля)

Из `sprint-change-proposal-2026-04-16.md`:
- **Проблема:** `OrderExportService._get_order_vat_rate()` (строка ~371 в `order_export.py`) берёт НДС только первого товара. Если заказ содержит товары с НДС 5% и 22% — экспорт в 1С некорректен.
- **Решение:** parent/child архитектура:
  - `is_master=True` — заказ видит клиент через API
  - `is_master=False` — технический субзаказ для 1С (каждый содержит товары одной VAT-группы)
- **Эта история** только закладывает поля. Логика создания субзаказов — Story 34-2. Изменения в ExportService — Story 34-3.

### Поля организации и склада в 1С

Из `order_export.py` (метод `_get_org_and_warehouse`):
- НДС 5% → Склад А (ИП Терещенко)
- НДС 22% → Склад Б (ИП Семерюк)
- Эта логика остаётся в `order_export.py` — Story 34-1 только добавляет поля модели.

### Тестовые паттерны проекта

Из `backend/tests/conftest.py` и `backend/tests/unit/test_models/test_order_models.py`:
- Маркер: `@pytest.mark.django_db`
- Фабрики: `OrderFactory`, `OrderItemFactory`, `UserFactory` из `tests.conftest`
- Уникальность: `get_unique_suffix()` для строковых данных
- `OrderFactory.create()` принимает любые поля модели
- Паттерн AAA (Arrange/Act/Assert)
- Тест-файлы в `backend/tests/unit/test_models/`

### Docker команды для тестирования

```bash
# Применить миграцию
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py migrate orders

# Запустить тесты модели
docker compose --env-file .env -f docker/docker-compose.test.yml exec backend \
  pytest -xvs tests/unit/test_models/test_order_models.py
```

### Архитектурные ограничения

- **PostgreSQL ONLY** — миграция совместима с PostgreSQL 15+
- **Обратная совместимость:** все поля имеют `null=True` или `default` — существующие заказы автоматически получат `is_master=True, parent_order=None, vat_group=None`; OrderItem — `vat_rate=None`
- **cascade delete:** при удалении мастер-заказа дочерние удаляются автоматически (`CASCADE`)

### Антипаттерны (НЕ ДЕЛАТЬ)

- НЕ создавать логику разбивки в этой story — только модель
- НЕ изменять `OrderCreateSerializer` — клиентский API не меняется
- НЕ добавлять `is_master` в фильтр `get_queryset()` в `views.py` — это задача Story 34-2
- НЕ трогать `order_export.py` и `order_status_import.py` — это задачи Story 34-3 и 34-4
- НЕ добавлять индекс на `is_master` вручную — Django автоматически создаёт индекс для ForeignKey (`parent_order`)

### Project Structure Notes

- Структура соответствует unified project structure
- Orders app: `backend/apps/orders/` (models, admin, serializers, views, urls, constants, services/)
- Тесты: `backend/tests/unit/test_models/test_order_models.py` — основной файл для тестов моделей заказов

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.1, #4.2]
- [Source: backend/apps/orders/models.py — Order и OrderItem]
- [Source: backend/apps/orders/constants.py — ORDER_STATUSES]
- [Source: backend/apps/orders/services/order_export.py:371 — _get_order_vat_rate()]
- [Source: backend/tests/unit/test_models/test_order_models.py — паттерны тестов]
- [Source: backend/tests/conftest.py — OrderFactory, get_unique_suffix()]
- [Source: _bmad-output/implementation-artifacts/Story/4-1-order-model-fields-for-1c-integration.md — эталонный паттерн для аналогичной story]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
