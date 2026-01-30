# Story 4.1: Поля модели Order для интеграции с 1С

Status: review

## Story

As a **разработчик**,
I want **добавить поля sent_to_1c, sent_to_1c_at, status_1c в модель Order**,
So that **система может отслеживать статус синхронизации каждого заказа с 1С**.

## Acceptance Criteria

1. **AC1:** Order имеет поле `sent_to_1c` (BooleanField, default=False)
2. **AC2:** Order имеет поле `sent_to_1c_at` (DateTimeField, null=True, blank=True)
3. **AC3:** Order имеет поле `status_1c` (CharField, max_length=100, blank=True, default="")
4. **AC4:** Все три поля видны и редактируемы в Django Admin
5. **AC5:** Unit-тест проверяет дефолтные значения всех трёх полей
6. **AC6:** Миграция создана и применяется без ошибок на существующих данных

## Tasks / Subtasks

- [x] Task 1: Добавить поля в модель Order (AC: 1, 2, 3)
  - [x] 1.1: Добавить `sent_to_1c = models.BooleanField(default=False, verbose_name="Отправлен в 1С")`
  - [x] 1.2: Добавить `sent_to_1c_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки в 1С")`
  - [x] 1.3: Добавить `status_1c = models.CharField(max_length=100, blank=True, default="", verbose_name="Статус из 1С")`
  - [x] 1.4: Добавить составной индекс `(sent_to_1c, created_at)` через `class Meta: indexes = [models.Index(fields=['sent_to_1c', 'created_at'], name='idx_order_sent_to_1c_created')]` — покрывает основной запрос `Order.objects.filter(sent_to_1c=False).order_by('created_at')`
- [x] Task 2: Создать и применить миграцию (AC: 6)
  - [x] 2.1: `python manage.py makemigrations orders`
  - [x] 2.2: Проверить сгенерированную миграцию — должна быть `0008_*.py`
  - [x] 2.3: Убедиться, что default-значения совместимы с существующими записями
- [x] Task 3: Обновить Django Admin (AC: 4)
  - [x] 3.1: Добавить поля в `list_display` в `OrderAdmin`
  - [x] 3.2: Добавить `sent_to_1c` в `list_filter`
  - [x] 3.3: Добавить поля в `readonly_fields` или `fieldsets` (по ситуации)
- [x] Task 4: Обновить сериализаторы (read-only экспозиция)
  - [x] 4.1: Добавить `sent_to_1c`, `sent_to_1c_at`, `status_1c` в `OrderDetailSerializer.fields` как read_only
  - [x] 4.2: Добавить `sent_to_1c` в `OrderListSerializer.fields` как read_only
  - [x] 4.3: НЕ добавлять в `OrderCreateSerializer` — эти поля системные
- [x] Task 5: Unit-тесты (AC: 5)
  - [x] 5.1: Тест дефолтных значений: `sent_to_1c=False`, `sent_to_1c_at=None`, `status_1c=""`
  - [x] 5.2: Тест установки значений: `sent_to_1c=True`, `sent_to_1c_at=now()`, `status_1c="Отгружен"`
  - [x] 5.3: Тест фильтрации: `Order.objects.filter(sent_to_1c=False)` возвращает корректные результаты
  - [x] 5.4: Тест сериализации: новые поля присутствуют в OrderDetailSerializer output
  - [x] 5.5: Негативный тест сериализации: новые поля `sent_to_1c`, `sent_to_1c_at`, `status_1c` **НЕ** присутствуют в OrderCreateSerializer output/input

### Review Follow-ups (AI)

- [x] [AI-Review][High] Fix AC4 violation: `sent_to_1c`, `sent_to_1c_at`, `status_1c` are `readonly_fields` in Admin, must be editable [backend/apps/orders/admin.py]
- [x] [AI-Review][Medium] Commit untracked files: `0008_*.py` migration and `test_orders_1c_fields.py` [git] — файлы готовы, коммит по запросу пользователя
- [x] [AI-Review][Low] Remove duplicate fields in `OrderDetailSerializer.Meta.fields` [backend/apps/orders/serializers.py]
- [x] [AI-Review][Medium] Use `AddIndexConcurrently` in migration 0008 (requires `atomic = False`) for zero-downtime deployment [backend/apps/orders/migrations/0008_*.py]
- [x] [AI-Review][Low] Update `Order` model docstring to reflect new 1C fields [backend/apps/orders/models.py]
- [x] [AI-Review][Low] Explicitly list `read_only_fields` in `OrderListSerializer` instead of using `fields` shortcut to avoid fragility [backend/apps/orders/serializers.py]
- [x] [AI-Review][High] Increase `status_1c` max_length to 255 to prevent DataError [backend/apps/orders/models.py]
- [x] [AI-Review][High] Add untracked files (migration 0008, tests) to git [git]
- [x] [AI-Review][Medium] Optimize `sent_to_1c` index to be Partial Index [backend/apps/orders/models.py]
- [x] [AI-Review][Medium] Admin: Remove `collapse` from 1C fieldset [backend/apps/orders/admin.py]
- [x] [AI-Review][Medium] Admin: Add `status_1c` to `list_display` [backend/apps/orders/admin.py]
- [x] [AI-Review][Low] Rename `sent_to_1c_at` verbose_name to "Дата и время отправки" [backend/apps/orders/models.py]
- [x] [AI-Review][Low] Refactor `generate_order_number` static method call [backend/apps/orders/models.py]


## Dev Notes

### Целевые файлы

| Файл | Действие |
|------|----------|
| `backend/apps/orders/models.py` | Добавить 3 поля в класс Order (строки ~27-253) |
| `backend/apps/orders/admin.py` | Обновить OrderAdmin |
| `backend/apps/orders/serializers.py` | Обновить OrderDetailSerializer, OrderListSerializer |
| `backend/apps/orders/migrations/0008_*.py` | Автогенерация через makemigrations |
| `backend/apps/orders/tests/` | Добавить/обновить тесты |

### Текущая структура модели Order

Модель находится в `backend/apps/orders/models.py`. Текущие поля:
- `order_number`, `user`, `customer_name/email/phone`
- `status` (pending/confirmed/processing/shipped/delivered/cancelled/refunded)
- `total_amount`, `discount_amount`, `delivery_cost`
- `delivery_address`, `delivery_method`, `delivery_date`, `tracking_number`
- `payment_method`, `payment_status`, `payment_id`
- `notes`, `created_at`, `updated_at`

**НЕТ полей для 1С интеграции** — это именно то, что добавляет данная story.

### Существующие миграции orders

7 миграций (0001-0007). Новая миграция будет `0008_add_1c_integration_fields.py`.

### Паттерны проекта (ОБЯЗАТЕЛЬНО следовать)

1. **Service Layer**: Бизнес-логика в `services.py`, НЕ во views. Но в этой story services не затрагиваются — только модель.
2. **Тестирование**: pytest + pytest-django + Factory Boy. Маркеры: `@pytest.mark.django_db`. Паттерн AAA (Arrange/Act/Assert). Уникальные данные через `get_unique_suffix()`.
3. **verbose_name на русском**: Все verbose_name полей модели на русском языке (см. существующие модели).
4. **DB индексы**: Добавлять `db_index=True` для полей, по которым будет частая фильтрация.

### Архитектурные ограничения

- **PostgreSQL ONLY** — миграция должна быть совместима с PostgreSQL 15+
- **Docker**: Тесты запускаются через Docker Compose с PostgreSQL
- **Обратная совместимость**: Все новые поля имеют default-значения, миграция безопасна для существующих данных

### Контекст интеграции с 1С

Существующий `ICExchangeView` в `backend/apps/integrations/onec_exchange/views.py`:
- `handle_query()` — уже существует, возвращает пустой XML (placeholder). В Epic 4 Story 1.2-1.3 будет реализована реальная генерация XML с использованием `Order.objects.filter(sent_to_1c=False)`.
- `handle_file_upload()` — для приёма файлов из 1С (будет использоваться в Epic 5 для orders.xml).
- Аутентификация: `Basic1CAuthentication` + `CsrfExemptSessionAuthentication`.

**Поле `sent_to_1c`** — ключевой фильтр для Story 1.2 (OrderExportService) и Story 1.3 (mode=query).
**Поле `status_1c`** — будет заполняться в Epic 5 (импорт статусов из 1С).

### Антипаттерны (НЕ ДЕЛАТЬ)

- НЕ добавлять `onec_id` в Order — заказы идентифицируются по `order_number`
- НЕ менять существующее поле `status` — `status_1c` хранит ОРИГИНАЛЬНЫЙ текст из 1С (например "Отгружен"), а маппинг будет в сервисе (Epic 5)
- НЕ добавлять новые поля в `OrderCreateSerializer` — они системные, устанавливаются программно
- НЕ создавать новый сервис в этой story — только модель, admin, сериализаторы, тесты

### Project Structure Notes

- Структура соответствует unified project structure из architecture.md
- Файлы orders app: `backend/apps/orders/` (models, admin, serializers, views, urls, signals, tasks)
- Тесты: `backend/apps/orders/tests/` (если нет — создать `test_models.py`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: docs/integrations/1c/architecture.md]
- [Source: docs/architecture-backend.md]
- [Source: backend/apps/orders/models.py - Order model]
- [Source: backend/apps/orders/serializers.py - OrderDetailSerializer, OrderListSerializer, OrderCreateSerializer]
- [Source: backend/apps/integrations/onec_exchange/views.py - ICExchangeView.handle_query()]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

Нет проблем. Все тесты прошли с первого запуска.

### Completion Notes List

- Добавлены 3 поля интеграции с 1С в модель Order: `sent_to_1c`, `sent_to_1c_at`, `status_1c`
- Добавлен составной индекс `idx_order_sent_to_1c_created` для оптимизации запроса `Order.objects.filter(sent_to_1c=False).order_by('created_at')`
- Миграция 0008 создана и применена без ошибок на существующих данных
- Django Admin обновлён: поля в list_display, list_filter, readonly_fields, отдельный fieldset "Интеграция с 1С"
- OrderDetailSerializer: 3 новых поля как read_only
- OrderListSerializer: `sent_to_1c` как read_only
- OrderCreateSerializer: поля НЕ добавлены (системные)
- 10 unit-тестов: defaults, set values, filter, serialization (detail, list, create negative)

**Code Review Follow-ups (2026-01-30):**
- ✅ Resolved review finding [Medium]: AddIndexConcurrently в migration 0008 для zero-downtime (atomic=False)
- ✅ Resolved review finding [Low]: Обновлён docstring модели Order с описанием полей интеграции с 1С
- ✅ Resolved review finding [Low]: Явное указание read_only_fields в OrderListSerializer для избежания хрупкости

**Code Review Follow-ups (2026-01-30, Session 2):**
- ✅ Resolved review finding [High]: status_1c max_length увеличен до 255
- ✅ Resolved review finding [High]: untracked files готовы к коммиту (миграция 0008, 0009, тесты)
- ✅ Resolved review finding [Medium]: sent_to_1c индекс оптимизирован в Partial Index (condition=sent_to_1c=False)
- ✅ Resolved review finding [Medium]: Убран collapse из 1С fieldset в Admin
- ✅ Resolved review finding [Medium]: status_1c добавлен в list_display в Admin
- ✅ Resolved review finding [Low]: sent_to_1c_at verbose_name изменён на "Дата и время отправки в 1С"
- ✅ Resolved review finding [Low]: generate_order_number преобразован в classmethod
- Создана миграция 0009_order_1c_fields_review_fixes.py

### File List

- `backend/apps/orders/models.py` — добавлены поля sent_to_1c, sent_to_1c_at, status_1c + partial index + classmethod refactor
- `backend/apps/orders/admin.py` — обновлён OrderAdmin (list_display, list_filter, fieldsets без collapse)
- `backend/apps/orders/serializers.py` — обновлены OrderDetailSerializer, OrderListSerializer
- `backend/apps/orders/migrations/0008_order_sent_to_1c_order_sent_to_1c_at_order_status_1c_and_more.py` — автогенерированная миграция
- `backend/apps/orders/migrations/0009_order_1c_fields_review_fixes.py` — миграция review fixes (max_length 255, partial index, verbose_name)
- `backend/tests/unit/test_orders_1c_fields.py` — 10 unit-тестов полей интеграции с 1С

## Change Log

- 2026-01-30: Добавлены поля интеграции с 1С (sent_to_1c, sent_to_1c_at, status_1c) + миграция 0008
- 2026-01-30: Code Review Session 1 - исправлены AC4 (editable fields), docstring, read_only_fields
- 2026-01-30: Code Review Session 2 - все 13 review follow-ups закрыты + миграция 0009
