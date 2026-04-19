# Sprint Change Proposal: Разбивка заказов по ставке НДС
**Дата:** 2026-04-16
**Проект:** FREESPORT
**Автор:** Alex
**Scope:** Moderate

---

## Раздел 1: Описание проблемы

### Проблема

В ходе реализации модуля экспорта заказов в 1С (Epic 4) обнаружено, что товары на платформе могут иметь **две различные ставки НДС** (5% и 22%), при этом:

- Товары со ставкой **НДС 5%** хранятся на **Складе А** (ИП Терещенко)
- Товары со ставкой **НДС 22%** хранятся на **Складе Б** (ИП Семерюк)
- Система 1С:УТ 11 требует **отдельного документа «Заказ»** для каждой ставки НДС / склада

### Контекст обнаружения

Проблема выявлена после завершения Epic 4 (`4-2-order-export-service-xml-generation`) при анализе реальных данных из 1С. Текущая реализация `OrderExportService._get_order_vat_rate()` (`order_export.py:371`) берёт ставку НДС только с **первого товара** заказа и применяет её ко всему XML-документу. Если заказ содержит товары с обеими ставками, в 1С уходит один документ с некорректными реквизитами склада/организации.

### Доказательства

```python
# order_export.py:371 — текущий код (проблемное место)
def _get_order_vat_rate(self, order: "Order") -> Decimal:
    for item in order.items.all():
        if not item.variant:
            continue
        if item.variant.vat_rate is not None:
            return Decimal(str(item.variant.vat_rate))  # ← берёт первый и выходит
        ...
    return default_rate
```

---

## Раздел 2: Анализ влияния

### Влияние на эпики

| Эпик | Статус | Влияние |
|------|--------|---------|
| Epic 4: Экспорт заказов в 1С | done | ❗ Доработка `OrderExportService` |
| Epic 5: Импорт статусов заказов | done | ❗ Доработка `OrderStatusImportService` |
| **Epic 34 (новый)** | backlog | ✅ Реализация parent/child структуры заказов |

### Влияние на истории

**Epic 4 — доработка:**
- `4-2-order-export-service-xml-generation`: генерировать N XML-документов из одного заказа (по числу VAT-групп), работать только с дочерними заказами

**Epic 5 — доработка:**
- `5-1-order-status-import-service`: при получении статуса из 1С обновлять дочерний заказ; агрегировать статус на мастер-заказе

### Конфликты артефактов

| Артефакт | Тип конфликта |
|----------|---------------|
| `apps/orders/models.py` | ❗ Новые поля: `parent_order`, `is_master`, `vat_group` |
| `apps/orders/models.py` — `OrderItem` | ❗ Новое поле: `vat_rate` (снимок ставки на момент заказа) |
| `apps/orders/services/order_export.py` | ❗ Разбивка по VAT-группам, работа с дочерними заказами |
| `apps/orders/services/order_status_import.py` | ❗ Маппинг статусов на дочерние заказы + агрегация |
| `apps/orders/views.py` / `serializers.py` | ❗ API создания заказа, фильтрация (клиенту — только мастера) |
| `architecture.md` | ❗ Обновить ADR-002, описание модели Order |
| Тесты Epic 4+5 | ❗ Обновить фикстуры и тест-кейсы |
| Миграции БД | ❗ 1–2 новые миграции |

### Техническое влияние

- **БД:** без data migration (тестовые заказы можно удалить перед деплоем)
- **API:** обратная совместимость сохраняется — клиент по-прежнему видит один заказ
- **1С:** два отдельных XML `<Документ>` вместо одного при смешанном НДС

---

## Раздел 3: Рекомендуемый подход

### Выбранный вариант: Direct Adjustment (Гибридный A→B)

Реализовать полную parent/child архитектуру заказов сразу, без промежуточного "A только для экспорта". Обоснование:

1. **Статусы из 1С** (Epic 5) уже реализованы и при подходе "только экспорт" потребовали бы хаков (`status_1c_vat5`, `status_1c_vat22`)
2. **Нет данных для миграции** — БД содержит только тестовые заказы
3. **Чистая архитектура** — один раз правильно, без технического долга

### UX-решение

Клиент видит **один мастер-заказ** с агрегированным статусом:
- `pending` → пока хотя бы один дочерний `pending`
- `confirmed` → все дочерние `confirmed`
- `delivered` → все дочерние `delivered`
- `partially_delivered` → дочерние в разных статусах (опционально, на усмотрение)

### Оценка

- **Усилие:** Medium (3–4 истории)
- **Риск:** Medium (затрагивает core-логику заказов)
- **Влияние на таймлайн:** +1 эпик в бэклог

---

## Раздел 4: Детальные предложения по изменениям

### 4.1 Изменения модели `Order`

**Story: Epic 34, Story 34-1**

```
OLD (apps/orders/models.py — класс Order):
  # Нет полей для parent/child структуры

NEW:
  parent_order = models.ForeignKey(
      'self',
      on_delete=models.CASCADE,
      null=True, blank=True,
      related_name='sub_orders',
      verbose_name='Мастер-заказ',
      help_text='Заполнено только для дочерних заказов'
  )
  is_master = models.BooleanField(
      'Мастер-заказ', default=True,
      help_text='True — заказ видит клиент; False — технический субзаказ для 1С'
  )
  vat_group = models.DecimalField(
      'Группа НДС (%)', max_digits=5, decimal_places=2,
      null=True, blank=True,
      help_text='Ставка НДС группы товаров в этом субзаказе (5 или 22)'
  )
```

**Rationale:** Мастер-заказ — точка входа для клиента и API. Субзаказы — технические единицы для 1С с изолированными статусами.

---

### 4.2 Новое поле `OrderItem.vat_rate`

**Story: Epic 34, Story 34-1**

```
OLD (класс OrderItem):
  # Нет снимка ставки НДС

NEW:
  vat_rate = models.DecimalField(
      'Ставка НДС (%)', max_digits=5, decimal_places=2,
      null=True, blank=True,
      help_text='Снимок ставки НДС варианта на момент создания заказа'
  )
```

**Rationale:** Снимок необходим для корректной разбивки при экспорте даже если `variant.vat_rate` изменится позже. Соответствует существующему паттерну `price_snapshot` в `OrderItem`.

---

### 4.3 Логика создания заказа (OrderCreateService)

**Story: Epic 34, Story 34-2**

```
OLD (apps/orders/views.py или services):
  # Создаётся один Order со всеми OrderItem

NEW:
  При создании заказа:
  1. Создать мастер-Order (is_master=True, total_amount=сумма всех товаров)
  2. Сгруппировать CartItem по vat_rate варианта
  3. Для каждой VAT-группы создать дочерний Order (is_master=False, parent_order=мастер,
     vat_group=ставка, total_amount=сумма группы)
  4. Перенести OrderItem в соответствующий дочерний заказ
     с заполнением OrderItem.vat_rate (снимок)
  5. Если в заказе товары только одной ставки — создаётся 1 дочерний заказ
```

**Rationale:** Единая точка создания субзаказов. При одной ставке НДС поведение идентично текущему.

---

### 4.4 API — фильтрация для клиента

**Story: Epic 34, Story 34-2**

```
OLD (GET /api/v1/orders/):
  Возвращает все заказы пользователя

NEW:
  Возвращает только мастер-заказы (is_master=True)
  QuerySet: Order.objects.filter(user=request.user, is_master=True)
```

**Rationale:** Клиент не должен видеть технические субзаказы.

---

### 4.5 OrderExportService — разбивка по VAT

**Story: Epic 34, Story 34-3**

```
OLD (order_export.py):
  generate_xml_streaming(orders):
    for order in orders:  # итерация по всем заказам (включая мастера)
      yield _create_document_element(order)  # один документ на заказ

NEW:
  generate_xml_streaming(orders):
    # orders должны быть дочерними заказами (is_master=False)
    # каждый дочерний заказ → один XML-документ
    for sub_order in orders.filter(is_master=False):
      yield _create_document_element(sub_order)
      # org/warehouse определяется по sub_order.vat_group (точно и однозначно)
```

**Rationale:** Каждый субзаказ содержит только товары одной VAT-группы, поэтому `_get_order_vat_rate()` всегда возвращает корректную однородную ставку.

---

### 4.6 OrderStatusImportService — обновление дочерних заказов

**Story: Epic 34, Story 34-4**

```
OLD (order_status_import.py):
  # Ищет Order по order_number или order-{id}
  # Обновляет Order.status_1c, Order.status

NEW:
  При получении статуса от 1С:
  1. Найти дочерний Order по ID из XML (is_master=False)
  2. Обновить sub_order.status_1c, sub_order.status
  3. Агрегировать статус мастера:
     master = sub_order.parent_order
     all_sub_statuses = master.sub_orders.values_list('status', flat=True)
     master.status = _aggregate_status(all_sub_statuses)
     master.save()
```

**Rationale:** Дочерние заказы имеют независимые статусы. Мастер-заказ агрегирует для отображения клиенту.

---

## Раздел 5: Handoff план

### Классификация изменения: **Moderate**

Требует реорганизации бэклога (PO/SM) и реализации командой разработки.

### Новый эпик

**Epic 34: Разбивка заказов по ставке НДС**
- **Goal:** Обеспечить корректное создание и экспорт заказов с товарами разных ставок НДС, с поддержкой независимых статусов субзаказов из 1С.
- **Статус:** backlog

| Story | Описание | Зависимости |
|-------|----------|-------------|
| 34-1 | Order/OrderItem: новые поля + миграции | — |
| 34-2 | Логика создания субзаказов + API фильтрация | 34-1 |
| 34-3 | OrderExportService: работа с субзаказами | 34-1 |
| 34-4 | OrderStatusImportService: агрегация статусов | 34-1 |
| 34-5 | Тесты: обновление фикстур Epic 4+5, новые тест-кейсы | 34-2, 34-3, 34-4 |

### Ответственные

| Роль | Задача |
|------|--------|
| **Dev** | Реализация Story 34-1 → 34-5 последовательно |
| **PO/SM** | Обновить sprint-status.yaml, приоритизировать Epic 34 |
| **PM/Arch** | Обновить ADR-002 в `architecture.md` |

### Критерии успеха

- [ ] Заказ с товарами разных НДС создаёт 1 мастер + N субзаказов
- [ ] `GET /api/v1/orders/` возвращает только мастер-заказы клиенту
- [ ] Экспорт в 1С генерирует отдельный XML-документ на каждый субзаказ
- [ ] Организация и склад в XML определяются точно по `vat_group` субзаказа
- [ ] Статус из 1С обновляет субзаказ; мастер получает агрегированный статус
- [ ] Все тесты Epic 4 и Epic 5 проходят с новой структурой
