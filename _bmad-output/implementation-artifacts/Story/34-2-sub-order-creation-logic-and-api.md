# Story 34.2: Логика создания субзаказов по VAT-группам и API-фильтрация мастер-заказов

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **клиент FREESPORT**,
I want **оформлять заказ как единый заказ, даже если товары имеют разные ставки НДС**,
so that **на моей стороне остаётся привычный UX (один заказ = один чек), а бэкенд при этом корректно разбивает его на технические субзаказы для 1С**.

> Техническая формулировка: реализовать в `OrderCreateSerializer.create()` автоматическую разбивку оформляемого заказа на один **мастер-заказ** (`is_master=True`) и N **дочерних субзаказов** (`is_master=False`) по группам `variant.vat_rate`; обеспечить, что клиентский API (`GET/LIST/RETRIEVE /api/v1/orders/`) возвращает только мастер-заказы.

## Acceptance Criteria

1. **AC1 (разбивка при создании):** При вызове `POST /api/v1/orders/` из корзины, содержащей товары **с разными `variant.vat_rate`**, создаётся **ровно один мастер-заказ** (`is_master=True, parent_order=None`) и **N субзаказов** (`is_master=False, parent_order=<master>`, `vat_group=<ставка>`), где N — количество уникальных ненулевых `vat_rate` в корзине.
2. **AC2 (однородная корзина):** Если в корзине все товары одной `vat_rate` (или только один товар), создаётся **1 мастер + 1 субзаказ** с этой `vat_group`. Мастер-заказ всегда присутствует — это единая точка контракта с клиентом.
3. **AC3 (перенос OrderItem):** Каждый `OrderItem` принадлежит **субзаказу**, соответствующему `vat_rate` его варианта. На мастере `items` не создаются (`master.items.count() == 0`). Поле `OrderItem.vat_rate` заполняется снимком `variant.vat_rate` через существующий `OrderItem.build_snapshot()` (Story 34-1).
4. **AC4 (финансовые поля):** `master.total_amount` = сумма по всем субзаказам (товары + доставка). `sub_order.total_amount` = сумма `OrderItem.total_price` его группы. `delivery_cost` записывается **только на мастере**; у субзаказов `delivery_cost=0` (доставка не дублируется). `discount_amount` — аналогично только на мастере.
5. **AC5 (атомарность и списание остатков):** Вся операция (создание мастера, субзаказов, `OrderItem`, списание `stock_quantity`, очистка корзины) выполняется в одной транзакции (`@transaction.atomic`). При ошибке — ни одна запись не остаётся.
6. **AC6 (общие атрибуты субзаказа):** Каждый субзаказ наследует от мастера: `user`, `customer_name/email/phone`, `delivery_address`, `delivery_method`, `delivery_date`, `payment_method`, `notes`. `status` субзаказа = `pending`, `payment_status` = `pending`. `order_number` — собственный у каждого субзаказа (генерируется автоматически в `Order.save()`).
7. **AC7 (обработка `vat_rate=None`):** Если у варианта `vat_rate` не задан (`None`), позиция попадает в субзаказ с `vat_group=None` (отдельная группа). Это не должно ломать создание заказа; после Story 34-3 такие субзаказы попадут в лог экспорта как требующие проверки.
8. **AC8 (API-фильтрация LIST):** `GET /api/v1/orders/` возвращает **только мастер-заказы** авторизованного пользователя: `Order.objects.filter(user=request.user, is_master=True)`. Субзаказы клиенту не видны.
9. **AC9 (API-фильтрация RETRIEVE):** `GET /api/v1/orders/{id}/` возвращает 404 при попытке прочитать субзаказ напрямую. Доступ разрешён только к мастер-заказам пользователя.
10. **AC10 (CANCEL только мастер):** `POST /api/v1/orders/{id}/cancel/` работает только с мастером. При отмене мастера каскадом отменяются все его субзаказы (`sub_orders` → `status='cancelled'`). Субзаказ напрямую отменить нельзя (404).
11. **AC11 (ответ POST):** `POST /api/v1/orders/` возвращает `OrderDetailSerializer(master).data`. Поле `items` в ответе мастера — **агрегированный список `OrderItem` из всех субзаказов** (клиент видит все позиции в одном заказе); реализуется через property `Order.items_aggregated` или переопределение `items` в сериализаторе для мастера.
12. **AC12 (обратная совместимость клиентского контракта):** Структура ответа `OrderDetailSerializer` и `OrderListSerializer` для клиента не меняется (кроме уже добавленных в Story 34-1 полей `is_master`, `vat_group`). Существующие frontend-вызовы продолжают работать.
13. **AC13 (покрытие тестами):** Новые unit- и integration-тесты покрывают: мульти-VAT разбивку, однородную корзину, агрегированные `items` мастера, 404 при доступе к субзаказу, cascade cancel, корректность `total_amount` мастера и суммы субзаказов, атомарность при ошибке. Тесты размечены `@pytest.mark.unit` / `@pytest.mark.integration`.

## Tasks / Subtasks

- [x] Task 1: Расширить `OrderCreateSerializer.create()` логикой разбивки на мастер + субзаказы (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] 1.1: Извлечь создание мастер-заказа в отдельный блок: `master = Order(**order_data, is_master=True, parent_order=None)`; `master.total_amount` и `delivery_cost` остаются на мастере.
  - [x] 1.2: Сгруппировать `cart.items` по `variant.vat_rate` (helper `_group_cart_items_by_vat(cart_items)` в сервисе/приватный метод сериализатора; ключ группы — `Decimal | None`).
  - [x] 1.3: Для каждой VAT-группы создать `sub_order = Order(parent_order=master, is_master=False, vat_group=<rate>, user=master.user, ..., delivery_cost=Decimal("0"), total_amount=<сумма группы>)` и сохранить.
  - [x] 1.4: `OrderItem` для каждой позиции строить с `order=sub_order` (а не мастер), сохранять через `bulk_create` с вызовом `OrderItem.build_snapshot()` (как в Story 34-1).
  - [x] 1.5: `master.total_amount` = сумма всех позиций + `delivery_cost`; сохранить мастер после расчёта субзаказов.
  - [x] 1.6: Логика списания `stock_quantity` и `cart.clear()` остаётся после создания всех субзаказов, внутри общей `@transaction.atomic`.
  - [x] 1.7: Вернуть `master` из `create()` (а не субзаказ). `to_representation(master)` уже вызывает `OrderDetailSerializer`.
- [x] Task 2: Выделить создание заказа в сервисный слой (AC: 1, 5) — **опционально, рекомендуется**
  - [x] 2.1: Создать `backend/apps/orders/services/order_create.py` с классом `OrderCreateService` (метод `create_from_cart(cart, user, validated_data) -> Order`).
  - [x] 2.2: Перенести туда логику разбивки; `OrderCreateSerializer.create()` становится тонкой обёрткой (соответствие "Service Layer" паттерну, см. `order_export.py`, `order_status_import.py`).
  - [x] 2.3: Если Task 2 пропущен — оставить логику в сериализаторе, но покрыть комментариями и unit-тестами отдельно.
- [x] Task 3: Добавить агрегацию `OrderItem` для мастера в API-ответ (AC: 11)
  - [x] 3.1: Добавить property/метод на `Order` (либо `items_all` в сериализаторе) — при `is_master=True` возвращает `OrderItem.objects.filter(order__in=[self, *self.sub_orders.all()])`.
  - [x] 3.2: Переопределить `OrderDetailSerializer.items` (через `SerializerMethodField` или кастомный источник), чтобы для мастера показывались позиции всех субзаказов.
  - [x] 3.3: `total_items`, `subtotal`, `calculated_total` на мастере — считать с учётом позиций субзаказов (не трогая оригинальные property на `Order` для сохранения обратной совместимости; использовать `SerializerMethodField`).
- [x] Task 4: Обновить `OrderViewSet.get_queryset()` — фильтрация мастер-заказов (AC: 8, 9)
  - [x] 4.1: Добавить `.filter(is_master=True)` в `get_queryset()`.
  - [x] 4.2: Обновить `prefetch_related` — добавить `sub_orders__items__product` чтобы детальный endpoint выдавал `items` без N+1.
  - [x] 4.3: Проверить, что `retrieve(id=<sub_order_id>)` возвращает 404 (за счёт фильтра в queryset).
- [x] Task 5: Cascade cancel мастера (AC: 10)
  - [x] 5.1: В `OrderViewSet.cancel()` после `order.status = "cancelled"; order.save()` добавить: `order.sub_orders.update(status="cancelled")`.
  - [x] 5.2: Явно запрещать cancel субзаказа — за счёт фильтра `is_master=True` в queryset это уже даёт 404, но добавить явную проверку `if not order.is_master: return 400/404` для защиты от обходных путей.
- [x] Task 6: Unit-тесты (AC: 13)
  - [x] 6.1: `test_order_create_service.py` (или `test_order_serializers.py`): тест разбивки корзины с 2 ставками НДС (5% и 22%) → 1 мастер + 2 субзаказа, корректные `vat_group` и `total_amount`.
  - [x] 6.2: Тест однородной корзины (1 ставка) → 1 мастер + 1 субзаказ.
  - [x] 6.3: Тест корзины со смесью `vat_rate=None` и `vat_rate=5` → 2 субзаказа (`vat_group=None` и `vat_group=5`).
  - [x] 6.4: Тест: `master.items.count() == 0`, а позиции живут в субзаказах.
  - [x] 6.5: Тест: `delivery_cost` только на мастере, у субзаказов = 0; `master.total_amount` = сумма по субзаказам + delivery_cost.
  - [x] 6.6: Тест атомарности: при искусственной ошибке (например, `variant.stock_quantity < quantity` после валидации) — ни мастер, ни субзаказы не сохраняются.
  - [x] 6.7: Тест snapshot `OrderItem.vat_rate`: заполняется через `build_snapshot` во всех субзаказах.
  - [x] 6.8: Все тесты файла помечены `@pytest.mark.unit` и `@pytest.mark.django_db`.
- [x] Task 7: Integration/API-тесты (AC: 8, 9, 10, 11, 12, 13)
  - [x] 7.1: В `backend/tests/integration/test_cart_order_integration.py` добавить тест: `POST /api/v1/orders/` с мульти-VAT корзиной → 201, в БД 1 master + 2 sub, ответ содержит все позиции в `items`.
  - [x] 7.2: Тест `GET /api/v1/orders/` возвращает только мастера (субзаказов нет в списке).
  - [x] 7.3: Тест `GET /api/v1/orders/<sub_order_id>/` → 404.
  - [x] 7.4: Тест `POST /api/v1/orders/<master_id>/cancel/` → мастер и все субзаказы в статусе `cancelled`.
  - [x] 7.5: Тест `POST /api/v1/orders/<sub_order_id>/cancel/` → 404.
  - [x] 7.6: Регрессионный тест: существующий сценарий однородной корзины продолжает работать без изменений в клиентском контракте.
  - [x] 7.7: Все тесты помечены `@pytest.mark.integration` и `@pytest.mark.django_db`.
- [x] Task 8: Обновление сериализатора ответа (AC: 11, 12)
  - [x] 8.1: В `OrderDetailSerializer` — переопределить источник `items` через `SerializerMethodField` `get_items(self, obj)`, который для `obj.is_master=True` агрегирует позиции из `sub_orders`.
  - [x] 8.2: Для субзаказа (если каким-то образом попадёт в сериализатор, например во внутренней админке) — отдавать свои `items` как раньше.
  - [x] 8.3: `total_items`, `subtotal`, `calculated_total` — также через `SerializerMethodField` с учётом агрегации для мастера.
- [x] Task 9: Проверка/обновление документации API (опционально)
  - [x] 9.1: Обновить docstring `OrderViewSet` и `extend_schema` description: отметить, что клиенту видны только мастер-заказы, а субзаказы — внутренняя структура для 1С.

### Review Follow-ups (AI)

- [x] [AI-Review][High] Исправить финансовую агрегацию `calculated_total` для мастер-заказа: значение должно включать сумму позиций всех субзаказов и `delivery_cost`, чтобы не расходиться с `total_amount`. [backend/apps/orders/serializers.py:80-85]
- [x] [AI-Review][High] Привести pytest-маркеры новых и изменённых тестов Story 34-2 к project-standard контракту `unit` / `integration`, чтобы AC13 и выборочные прогоны `pytest -m unit` / `pytest -m integration` не пропускали покрытие. [backend/tests/unit/test_serializers/test_order_serializers.py:151-152, backend/tests/integration/test_cart_order_integration.py:17-18]
- [x] [AI-Review][High] Добавить regression-тесты на сериализованный `calculated_total` мастер-заказа, чтобы AC4/AC11 подтверждались не только полем `total_amount`, но и фактическим API/serializer output. [backend/tests/unit/test_serializers/test_order_serializers.py:1058-1063, backend/tests/integration/test_cart_order_integration.py:338-355]
- [x] [AI-Review][Medium] Синхронизировать `Dev Agent Record -> File List` с фактическим git diff: задокументировать изменения story-артефактов (`34-2` story и `sprint-status.yaml`) либо привести review snapshot к полностью воспроизводимому набору файлов. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:367-373]
- [x] [AI-Review][Medium] Уточнить `Debug Log References`: claim `Все 50 тестов прошли с первого запуска. Линтинг (flake8) чистый.` не подтверждён артефактами ревью и должен быть либо доказан командами/логами, либо переформулирован в проверяемый вид. [_bmad-output/implementation-artifacts/Story/34-2-sub-order-creation-logic-and-api.md:353-356]
- [x] [AI-Review][Low] Довести Task 5.2 до буквального соответствия story: добавить явную defensive-проверку `order.is_master` в `cancel()`, а не полагаться только на фильтр queryset и комментарий. [backend/apps/orders/views.py:134-159]
- [x] [AI-Review][High] Исправить регрессию list-contract: `GET /api/v1/orders/` должен возвращать корректный агрегированный `total_items` для мастер-заказов, а не `0` из-за чтения `Order.total_items` только по direct `items`. [backend/apps/orders/views.py:47-60, backend/apps/orders/serializers.py:263-267, backend/apps/orders/models.py:303-305]
- [x] [AI-Review][High] Защитить списание остатков от race condition: текущий decrement `stock_quantity=F("stock_quantity")-qty` без блокировок/условного update может приводить к oversell или `IntegrityError`/500 при параллельном checkout. [backend/apps/orders/serializers.py:170-188, backend/apps/orders/services/order_create.py:108-111, backend/apps/products/models.py:985-988]
- [x] [AI-Review][High] Привести Task 6.6 к фактическому выполнению: добавить тест rollback именно для post-validation stock failure, потому что текущие `test_atomicity_on_error` и `test_transactional_integrity` проверяют другие сценарии и не доказывают закрытую подзадачу. [backend/tests/unit/test_serializers/test_order_serializers.py:908-953, backend/tests/integration/test_cart_order_integration.py:174-205]
- [x] [AI-Review][Medium] Добавить regression-тест для list endpoint на корректный `total_items` у мастер-заказа, чтобы AC12/AC13 ловили регресс после VAT-split. [backend/tests/integration/test_cart_order_integration.py:395-405]
- [x] [AI-Review][High] Восстановить обратную совместимость сериализаторов для legacy master-заказов: если `is_master=True`, но direct `items` ещё существуют и `sub_orders` отсутствуют, `OrderDetailSerializer.items/subtotal/total_items/calculated_total` и `OrderListSerializer.total_items` должны корректно работать по direct items, иначе нарушается AC12. [backend/apps/orders/serializers.py:61-83, backend/apps/orders/serializers.py:274-277]
- [x] [AI-Review][Medium] Синхронизировать существующий integration suite `tests/integration/test_orders_api.py` с новым master/sub-order контрактом и/или добавить отдельные regression-тесты на legacy master-заказ с direct items, чтобы подтверждение AC12 было реальным, а не только в новых Story 34-2 тестах. [backend/tests/integration/test_orders_api.py:53-99, backend/tests/integration/test_orders_api.py:171-201]
- [x] [AI-Review][Medium] Привести unit-покрытие изменённого `OrderListSerializer` к project-standard marker contract: добавить `@pytest.mark.unit` на `TestOrderListSerializer`, иначе `pytest -m unit` пропускает часть изменённого покрытия Story 34-2. [backend/tests/unit/test_serializers/test_order_serializers.py:474-505]
- [x] [AI-Review][Low] Снизить query cost ответа `POST /api/v1/orders/`: переиспользовать prefetched queryset или re-fetch мастера с `prefetch_related` перед сериализацией, чтобы checkout response не делал лишнюю агрегацию без предзагрузки. [backend/apps/orders/views.py:118-126, backend/apps/orders/serializers.py:61-83]
- [ ] [AI-Review][High] Восстановить `vat_group` в `OrderListSerializer`, иначе list endpoint нарушает AC12 и теряет уже добавленное в Story 34-1 поле клиентского контракта. [backend/apps/orders/serializers.py:297-327]
- [ ] [AI-Review][Medium] Сделать `OrderViewSet.cancel()` атомарным, чтобы каскадная отмена мастера и субзаказов не могла завершиться частично при сбое между `order.save()` и `sub_orders.update(...)`. [backend/apps/orders/views.py:195-197]
- [ ] [AI-Review][Medium] Добавить regression-тесты на `vat_group` в API/serializer output (`POST`/`LIST`/`RETRIEVE`), потому что текущий suite проверяет `vat_group` только на уровне БД у `sub_orders`, но не в `POST`/`LIST`/`RETRIEVE` payload, поэтому регресс контракта в сериализаторе прошёл незамеченным. [backend/tests/unit/test_serializers/test_order_serializers.py:734-840, backend/tests/integration/test_cart_order_integration.py:339-423, backend/tests/integration/test_orders_api.py:53-105]
- [ ] [AI-Review][Low] Добавить integration coverage для успешного guest checkout через session cart, чтобы публичный `AllowAny` flow был защищён regression-тестом, а не только негативным кейсом пустой корзины. [backend/apps/orders/views.py:35-37, backend/apps/orders/serializers.py:224-237, backend/tests/integration/test_orders_api.py:161-179]

## Dev Notes

### Архитектурный контекст (почему так)

Из `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md` §4.3–4.4:

- **Проблема:** 1С:УТ 11 требует отдельный документ «Заказ» на каждую пару (ставка НДС / склад / организация). Платформа продаёт товары двух юрлиц (НДС 5% — ИП Терещенко / Склад А; НДС 22% — ИП Семерюк / Склад Б), поэтому заказ со смешанным НДС физически не может быть одним документом в 1С.
- **Решение:** parent/child архитектура. Клиент видит один мастер-заказ; 1С получает N субзаказов, каждый из которых содержит товары только одной VAT-группы.
- **Эта story** реализует шаги 4.3 и 4.4 из proposal. Экспорт в 1С (4.5) — Story 34-3, импорт статусов (4.6) — Story 34-4, обновление фикстур Epic 4+5 — Story 34-5.

### Предыдущая история — Story 34-1 (фундамент)

Story 34-1 (status: review) уже добавила:
- Поля `Order.parent_order`, `Order.is_master`, `Order.vat_group` (миграция `0012_add_vat_split_fields`)
- Поле `OrderItem.vat_rate` и его snapshot через `OrderItem.build_snapshot(product, variant)`
- `OrderItem.vat_rate` уже корректно заполняется в `OrderCreateSerializer.create()` в bulk_create path (используется `build_snapshot` — см. [backend/apps/orders/serializers.py:251-262](file:///c:/Users/1/DEV/FREESPORT/backend/apps/orders/serializers.py))
- `is_master`, `vat_group` добавлены в `OrderDetailSerializer` и `OrderListSerializer` как `read_only`
- `OrderAdmin` получил fieldset "VAT / Субзаказы"
- Pytest markers `@pytest.mark.unit` / `@pytest.mark.integration` используются как стандарт проекта

**Следствие для 34-2:** не дублируй snapshot-логику — используй `OrderItem.build_snapshot()`. Все новые поля модели уже доступны, дополнительных миграций не требуется.

### Ключевые файлы

| Файл | Действие |
|------|----------|
| `backend/apps/orders/serializers.py` | Расширить `OrderCreateSerializer.create()` + `OrderDetailSerializer` (агрегация items) |
| `backend/apps/orders/views.py` | `get_queryset()` → `.filter(is_master=True)`; `cancel()` → cascade на субзаказы |
| `backend/apps/orders/services/order_create.py` | **Новый** (опционально): `OrderCreateService` |
| `backend/apps/orders/models.py` | Опционально: property `items_aggregated` на `Order` |
| `backend/tests/unit/test_serializers/test_order_serializers.py` | Unit-тесты разбивки |
| `backend/tests/unit/test_models/test_order_models.py` | Регрессия: property `items_aggregated` / агрегированные totals |
| `backend/tests/integration/test_cart_order_integration.py` | API-тесты (list/retrieve/create/cancel) |

### Тестовые паттерны проекта

- Маркеры: `@pytest.mark.django_db` + `@pytest.mark.unit` / `@pytest.mark.integration` (из AGENTS.md и Story 34-1 Third Follow-up).
- Фабрики: `UserFactory`, `OrderFactory`, `OrderItemFactory` из `backend/tests/conftest.py`.
- Для API-тестов: `APIClient` из `rest_framework.test`; для cart setup — смотри существующие паттерны в `backend/tests/integration/test_cart_order_integration.py`.
- Для варианта с заданной `vat_rate` — проверь, есть ли в фабриках `ProductVariantFactory` с параметром `vat_rate`; если нет — создавай явно в тесте.

### Docker команды для запуска тестов

```bash
# Unit-тесты сериализаторов/сервисов
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest -xvs -m unit backend/tests/unit/test_serializers/test_order_serializers.py

# Integration-тесты API
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest -xvs -m integration backend/tests/integration/test_cart_order_integration.py

# Полный прогон orders
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  pytest backend/apps/orders backend/tests/unit/test_models/test_order_models.py \
          backend/tests/unit/test_serializers/test_order_serializers.py \
          backend/tests/integration/test_cart_order_integration.py
```

### Архитектурные ограничения

- **PostgreSQL ONLY** — без сырых SQL, только Django ORM.
- **Обратная совместимость API** — клиентский контракт (`OrderDetailSerializer`, `OrderListSerializer`, `OrderCreateSerializer`) не должен сломаться для фронтенда. Поля `is_master`, `vat_group` уже добавлены в Story 34-1 как read_only.
- **Транзакционная целостность** — вся логика создания в одной `@transaction.atomic`.
- **Никаких data migrations** — в БД только тестовые заказы (подтверждено в sprint-change-proposal §Техническое влияние).
- **Не менять поля `OrderCreateSerializer.Meta.fields`** — клиентский input остаётся прежним. Разбивка выполняется полностью на бэкенде, прозрачно для клиента.

### Антипаттерны (НЕ ДЕЛАТЬ)

- НЕ трогать `apps/orders/services/order_export.py` — это Story 34-3.
- НЕ трогать `apps/orders/services/order_status_import.py` — это Story 34-4.
- НЕ создавать новую миграцию — поля уже есть из Story 34-1.
- НЕ ломать property `Order.items`, `Order.subtotal`, `Order.total_items` — они используются в сигналах/сервисах 1С. Для агрегации на мастере добавлять отдельные property/методы или делать агрегацию в `SerializerMethodField`.
- НЕ создавать `OrderItem` на мастере — все позиции живут на субзаказах.
- НЕ дублировать `delivery_cost` на субзаказах — доставка одна на весь заказ (на мастере).
- НЕ забывать про `vat_rate=None` — это валидный кейс (товары без указанной ставки), не падай, клади в группу с `vat_group=None`.
- НЕ хардкодить список ставок (5, 22) — группировка по факту из `variant.vat_rate`, любое число.
- НЕ позволять клиенту видеть субзаказы ни в одном endpoint.

### Project Structure Notes

- Структура соответствует unified project structure.
- Orders app: `backend/apps/orders/` (models, admin, serializers, views, urls, constants, services/).
- При выделении `OrderCreateService` — класть в `backend/apps/orders/services/order_create.py` (рядом с `order_export.py`, `order_status_import.py`).
- Тесты: unit — `backend/tests/unit/test_serializers/`, `backend/tests/unit/test_models/`; integration — `backend/tests/integration/`.

### Potential Risks & Open Questions

1. **Гостевые заказы** (`user=None`): логика та же — мастер и субзаказы с `user=None`, но гость в любом случае не видит список заказов. Проверить, что flow гостя не сломан.
2. **Каскадное удаление**: при `master.delete()` все субзаказы удаляются автоматически (`on_delete=CASCADE` на `parent_order`) — но `ProductVariant.stock_quantity` не возвращается. В текущем flow клиент не удаляет заказы (только cancel), поэтому это не регресс, но зафиксировать в retrospective Epic 34.
3. **Агрегация `status` на мастере** — согласно proposal §3 (UX-решение), мастер должен показывать агрегированный статус (`pending` → `confirmed` → `delivered`). **Эта агрегация — задача Story 34-4** (при импорте статусов из 1С). В 34-2 оставляй `master.status = "pending"` при создании и оставляй `cancel` как прямой переход в `cancelled` (cascade).
4. **Конфликт с `sent_to_1c` / `status_1c`** — эти поля живут на субзаказах (1С шлёт статус отдельно на каждый документ). На мастере они остаются со значениями по умолчанию. Это консистентно со Story 34-3/34-4.
5. **Existing OrderFactory**: может создавать `Order` без `is_master` setup (будет по дефолту `True`). Фикстуры Epic 4+5 — задача Story 34-5; в 34-2 не трогать.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.3-создание]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#4.4-api-фильтрация]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16.md#3-ux-решение]
- [Source: _bmad-output/implementation-artifacts/Story/34-1-order-model-vat-split-fields-migrations.md — модель и snapshot helper]
- [Source: backend/apps/orders/models.py — Order, OrderItem, build_snapshot]
- [Source: backend/apps/orders/serializers.py — OrderCreateSerializer.create(), OrderDetailSerializer]
- [Source: backend/apps/orders/views.py — OrderViewSet.get_queryset(), cancel()]
- [Source: backend/apps/orders/services/order_export.py:371 — _get_order_vat_rate() (контекст потребителя субзаказов)]
- [Source: backend/tests/conftest.py — OrderFactory, UserFactory, get_unique_suffix()]
- [Source: AGENTS.md — pytest markers unit/integration]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

**Команды воспроизведения (Docker, `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend ...`):**

Полная регрессия по затронутым областям:
```bash
pytest apps/orders tests/unit/test_models/test_order_models.py \
       tests/unit/test_serializers/test_order_serializers.py \
       tests/integration/test_cart_order_integration.py
```

Выборочные прогоны маркеров (AC13 — подтверждение contract):
```bash
pytest -m unit tests/unit/test_serializers/test_order_serializers.py
pytest -m integration tests/integration/test_cart_order_integration.py
```

Линтинг:
```bash
flake8 apps/orders/serializers.py apps/orders/views.py apps/orders/services/order_create.py \
       tests/unit/test_serializers/test_order_serializers.py \
       tests/integration/test_cart_order_integration.py
black --check apps/orders/serializers.py apps/orders/views.py apps/orders/services/order_create.py \
       tests/unit/test_serializers/test_order_serializers.py \
       tests/integration/test_cart_order_integration.py
```

**Результаты запусков в рамках follow-up (2026-04-16):**
- Финальная регрессия (93 теста в apps/orders + order_models + order_serializers + cart_order_integration): `93 passed, 6 warnings in 55.70s`.
- `pytest -m unit tests/unit/test_serializers/test_order_serializers.py`: `30 passed, 9 deselected in 24.93s`.
- `pytest -m integration tests/integration/test_cart_order_integration.py`: `14 passed in 20.43s`.
- `flake8`: чистый (пустой вывод, exit code 0).
- `black --check`: `All done! ✨ 🍰 ✨ 5 files would be left unchanged.`

**Результаты второго follow-up (2026-04-16) — после fix total_items/stock race/rollback-тестов:**
- Полная регрессия (apps/orders + order_models + order_serializers + cart_order_integration): `96 passed, 6 warnings in 50.86s`.
- `pytest -m unit tests/unit/test_serializers/test_order_serializers.py`: `31 passed, 9 deselected, 1 warning in 23.86s`.
- `pytest -m integration tests/integration/test_cart_order_integration.py`: `16 passed, 6 warnings in 21.85s`.
- `flake8` по 5 изменённым файлам: пустой вывод, exit code 0.
- `black --check` по 5 изменённым файлам: `All done! ✨ 🍰 ✨ 5 files would be left unchanged.`

### Completion Notes List

- Создан `OrderCreateService` в `backend/apps/orders/services/order_create.py` — вся логика разбивки по VAT-группам с `@transaction.atomic`.
- `OrderCreateSerializer.create()` стал тонкой обёрткой над сервисом.
- `OrderDetailSerializer` переведён на `SerializerMethodField` для `items`, `subtotal`, `total_items`, `calculated_total` — мастер агрегирует из sub_orders, субзаказ — собственные items.
- `OrderViewSet.get_queryset()` фильтрует `is_master=True` + prefetch `sub_orders__items__product/variant`.
- `cancel()` делает cascade на `sub_orders.update(status="cancelled")`.
- 9 новых unit-тестов в `TestOrderVATSplit`, 6 новых integration-тестов в `VATSplitAPITest`.
- Существующие тесты, создававшие items напрямую на factory-заказе, переведены на `is_master=False`.

**Review Follow-up (2026-04-16) — Changes Requested → Resolved (6/6):**
- ✅ [High] `get_calculated_total()` мастера: добавлен `delivery_cost` в сумму (bugfix AC4/AC11 консистентности с `total_amount`).
- ✅ [High] AC13 маркировка: `@pytest.mark.unit` добавлен на `TestOrderDetailSerializer`, `TestOrderCreateSerializer`, `TestOrderDetailExtended`, `TestOrderIntegration`; `@pytest.mark.django_db` добавлен на `CartOrderIntegrationTest`.
- ✅ [High] Regression-тесты `calculated_total`: 2 unit-теста (`test_master_calculated_total_includes_delivery_cost`, `test_master_calculated_total_homogeneous_cart_with_delivery`) + 1 integration (`test_multi_vat_master_calculated_total_includes_delivery`).
- ✅ [Medium] File List синхронизирован: story-артефакт и sprint-status.yaml включены ниже.
- ✅ [Medium] Debug Log References переформулирован: команды + результаты конкретных запусков.
- ✅ [Low] `OrderViewSet.cancel()`: добавлена явная defensive-проверка `if not order.is_master → 404`.
- Обновлены docstrings и `extend_schema` для `OrderViewSet` (Task 9) с явным указанием мастер-ограничения.

**Third Review Follow-up (2026-04-17) — Changes Requested → Resolved (4/4):**
- ✅ [High] Backward compat legacy master: в `OrderDetailSerializer.get_items/get_subtotal/get_total_items/get_calculated_total` и `OrderListSerializer.get_total_items` добавлен fallback — если `is_master=True`, но `sub_orders` пусты, используются direct `items`/`Order.total_items`/`Order.calculated_total` (сохраняет AC12 для старых master-заказов без VAT-split).
- ✅ [Medium] `test_orders_api.py` синхронизирован: `test_create_order_from_cart_success` проверяет новый VAT-split контракт (`items.count() == 0`, позиции в `sub_orders[0].items`), а API-ответ содержит агрегированные `items`. Добавлен `test_legacy_master_with_direct_items_backward_compat` — regression на legacy master в detail и list endpoint (items/subtotal/total_items/calculated_total).
- ✅ [Medium] `@pytest.mark.unit` добавлен на `TestOrderListSerializer` — `pytest -m unit` теперь покрывает 33 теста (ранее 31).
- ✅ [Low] `OrderViewSet.create()` делает re-fetch мастера через `Order.objects.select_related('user').prefetch_related('items__...', 'sub_orders__items__...')` перед передачей в `OrderDetailSerializer` — устранён N+1 в checkout response. `get_queryset()` также расширен prefetch на `items__product/variant` для legacy master.

**Fourth Follow-up Review (AI)**

#### Review Date

2026-04-17

#### Outcome

Changes Requested

#### Summary

- Найдено 4 issue: 1 High, 2 Medium, 1 Low.
- Базовая реализация VAT-split и предыдущие follow-up fixes остаются валидными, но snapshot всё ещё не готов к `done`: list-contract снова расходится с заявленным AC12.
- Дополнительно выявлены пробелы в атомарности cascade cancel и regression coverage по `vat_group`/guest checkout.

#### Findings

1. **[High] `OrderListSerializer` потерял `vat_group`** — list endpoint больше не возвращает поле `vat_group`, хотя Story 34-1 уже добавила его в клиентский контракт, а AC12 Story 34-2 требует сохранить структуру ответа `OrderListSerializer` за исключением уже введённых полей `is_master`, `vat_group`. [backend/apps/orders/serializers.py:297-327]
2. **[Medium] `cancel()` не атомарен** — мастер переводится в `cancelled` отдельным `save()`, а субзаказы — отдельным `update()`. При сбое между этими операциями система может остаться в частично отменённом состоянии, что противоречит AC10. [backend/apps/orders/views.py:195-197]
3. **[Medium] Тесты не проверяют `vat_group` в API output** — текущий unit/integration suite валидирует `vat_group` только на уровне БД у `sub_orders`, но не в `POST`/`LIST`/`RETRIEVE` payload, поэтому регресс контракта в сериализаторе прошёл незамеченным. [backend/tests/unit/test_serializers/test_order_serializers.py:734-840, backend/tests/integration/test_cart_order_integration.py:339-423, backend/tests/integration/test_orders_api.py:53-105]
4. **[Low] Нет happy-path coverage для guest checkout** — endpoint `create` открыт для гостей, а session-cart ветка `_get_user_cart()` не подтверждена успешным integration тестом после рефакторинга на service layer. [backend/apps/orders/views.py:35-37, backend/apps/orders/serializers.py:224-237, backend/tests/integration/test_orders_api.py:161-179]

#### Action Items

- [ ] [High] Вернуть `vat_group` в `OrderListSerializer` и закрыть regression-тестами list/detail/create response contract.
- [ ] [Medium] Обернуть cascade cancel в атомарную операцию и подтвердить это тестом/проверкой.
- [ ] [Medium] Добавить regression-тесты на `vat_group` в API/serializer output, а не только на БД-состояние субзаказов.
- [ ] [Low] Добавить integration-тест успешного guest checkout через session cart.

## Change Log

| Date | Change |
|------|--------|
| 2026-04-16 | Story создана через create-story workflow по sprint-change-proposal §4.3–4.4. Status → ready-for-dev. |
| 2026-04-16 | Реализация Story 34-2: OrderCreateService (VAT split), фильтр is_master в ViewSet, cascade cancel, SerializerMethodField агрегация, 15 новых тестов. Status → review. |
| 2026-04-16 | Code Review (AI): добавлены 6 Review Follow-ups (3 High, 2 Medium, 1 Low). Status → in-progress. Outcome: Changes Requested. |
| 2026-04-16 | Review follow-ups: resolved 6 items (3 High, 2 Medium, 1 Low). `calculated_total` мастера учитывает `delivery_cost`, добавлены 3 regression-теста, маркеры unit/integration/django_db приведены к project-standard, defensive-check `is_master` в `cancel()`, docstring/extend_schema OrderViewSet (Task 9), Debug Log References и File List синхронизированы. Status → review. |
| 2026-04-16 | Follow-up Code Review (AI): добавлены 4 новых Review Follow-ups (3 High, 1 Medium) по регрессии `total_items` в list endpoint, race condition при списании остатков, преждевременно закрытому Task 6.6 и отсутствию regression-теста list-contract. Status → in-progress. Outcome: Changes Requested. |
| 2026-04-16 | Second review follow-ups: resolved 4 items (3 High, 1 Medium). `OrderListSerializer.total_items` → `SerializerMethodField` с агрегацией, conditional update stock с ValidationError при race, unit+integration rollback-тесты post-validation stock depletion, regression-тест `total_items` в list endpoint. Полная регрессия 96/96 passed, flake8/black чисто. Status → review. |
| 2026-04-17 | Third follow-up code review (AI): добавлены 4 новых Review Follow-ups (1 High, 2 Medium, 1 Low) по backward compatibility legacy master orders, несинхронизированному `test_orders_api.py`, неполному marker-contract для `TestOrderListSerializer` и query-heavy create response. Status → in-progress. Outcome: Changes Requested. |
| 2026-04-17 | Third review follow-ups: resolved 4 items (1 High, 2 Medium, 1 Low). Legacy master fallback в сериализаторах (items/subtotal/total_items/calculated_total читают direct items при пустых sub_orders), `test_orders_api.py` синхронизирован с VAT-split + добавлен `test_legacy_master_with_direct_items_backward_compat`, `@pytest.mark.unit` на `TestOrderListSerializer`, re-fetch мастера с полным prefetch в `create()`. Регрессия 107/107 passed (orders + unit serializers + cart_order_integration + test_orders_api), `pytest -m unit`: 33 passed, `pytest -m integration`: 27 passed, flake8/black чисто. Status → review. |

| 2026-04-17 | Fourth follow-up code review (AI): добавлены 4 новых Review Follow-ups (1 High, 2 Medium, 1 Low) по потере `vat_group` в `OrderListSerializer`, неатомарному cascade cancel, отсутствию regression-тестов на `vat_group` в API output и отсутствию happy-path coverage для guest checkout. Status → in-progress. Outcome: Changes Requested. |



