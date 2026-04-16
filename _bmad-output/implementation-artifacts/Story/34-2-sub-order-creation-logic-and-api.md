# Story 34.2: Логика создания субзаказов по VAT-группам и API-фильтрация мастер-заказов

Status: ready-for-dev

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

- [ ] Task 1: Расширить `OrderCreateSerializer.create()` логикой разбивки на мастер + субзаказы (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] 1.1: Извлечь создание мастер-заказа в отдельный блок: `master = Order(**order_data, is_master=True, parent_order=None)`; `master.total_amount` и `delivery_cost` остаются на мастере.
  - [ ] 1.2: Сгруппировать `cart.items` по `variant.vat_rate` (helper `_group_cart_items_by_vat(cart_items)` в сервисе/приватный метод сериализатора; ключ группы — `Decimal | None`).
  - [ ] 1.3: Для каждой VAT-группы создать `sub_order = Order(parent_order=master, is_master=False, vat_group=<rate>, user=master.user, ..., delivery_cost=Decimal("0"), total_amount=<сумма группы>)` и сохранить.
  - [ ] 1.4: `OrderItem` для каждой позиции строить с `order=sub_order` (а не мастер), сохранять через `bulk_create` с вызовом `OrderItem.build_snapshot()` (как в Story 34-1).
  - [ ] 1.5: `master.total_amount` = сумма всех позиций + `delivery_cost`; сохранить мастер после расчёта субзаказов.
  - [ ] 1.6: Логика списания `stock_quantity` и `cart.clear()` остаётся после создания всех субзаказов, внутри общей `@transaction.atomic`.
  - [ ] 1.7: Вернуть `master` из `create()` (а не субзаказ). `to_representation(master)` уже вызывает `OrderDetailSerializer`.
- [ ] Task 2: Выделить создание заказа в сервисный слой (AC: 1, 5) — **опционально, рекомендуется**
  - [ ] 2.1: Создать `backend/apps/orders/services/order_create.py` с классом `OrderCreateService` (метод `create_from_cart(cart, user, validated_data) -> Order`).
  - [ ] 2.2: Перенести туда логику разбивки; `OrderCreateSerializer.create()` становится тонкой обёрткой (соответствие "Service Layer" паттерну, см. `order_export.py`, `order_status_import.py`).
  - [ ] 2.3: Если Task 2 пропущен — оставить логику в сериализаторе, но покрыть комментариями и unit-тестами отдельно.
- [ ] Task 3: Добавить агрегацию `OrderItem` для мастера в API-ответ (AC: 11)
  - [ ] 3.1: Добавить property/метод на `Order` (либо `items_all` в сериализаторе) — при `is_master=True` возвращает `OrderItem.objects.filter(order__in=[self, *self.sub_orders.all()])`.
  - [ ] 3.2: Переопределить `OrderDetailSerializer.items` (через `SerializerMethodField` или кастомный источник), чтобы для мастера показывались позиции всех субзаказов.
  - [ ] 3.3: `total_items`, `subtotal`, `calculated_total` на мастере — считать с учётом позиций субзаказов (не трогая оригинальные property на `Order` для сохранения обратной совместимости; использовать `SerializerMethodField`).
- [ ] Task 4: Обновить `OrderViewSet.get_queryset()` — фильтрация мастер-заказов (AC: 8, 9)
  - [ ] 4.1: Добавить `.filter(is_master=True)` в `get_queryset()`.
  - [ ] 4.2: Обновить `prefetch_related` — добавить `sub_orders__items__product` чтобы детальный endpoint выдавал `items` без N+1.
  - [ ] 4.3: Проверить, что `retrieve(id=<sub_order_id>)` возвращает 404 (за счёт фильтра в queryset).
- [ ] Task 5: Cascade cancel мастера (AC: 10)
  - [ ] 5.1: В `OrderViewSet.cancel()` после `order.status = "cancelled"; order.save()` добавить: `order.sub_orders.update(status="cancelled", updated_at=timezone.now())`.
  - [ ] 5.2: Явно запрещать cancel субзаказа — за счёт фильтра `is_master=True` в queryset это уже даёт 404, но добавить явную проверку `if not order.is_master: return 400/404` для защиты от обходных путей.
- [ ] Task 6: Unit-тесты (AC: 13)
  - [ ] 6.1: `test_order_create_service.py` (или `test_order_serializers.py`): тест разбивки корзины с 2 ставками НДС (5% и 22%) → 1 мастер + 2 субзаказа, корректные `vat_group` и `total_amount`.
  - [ ] 6.2: Тест однородной корзины (1 ставка) → 1 мастер + 1 субзаказ.
  - [ ] 6.3: Тест корзины со смесью `vat_rate=None` и `vat_rate=5` → 2 субзаказа (`vat_group=None` и `vat_group=5`).
  - [ ] 6.4: Тест: `master.items.count() == 0`, а позиции живут в субзаказах.
  - [ ] 6.5: Тест: `delivery_cost` только на мастере, у субзаказов = 0; `master.total_amount` = сумма по субзаказам + delivery_cost.
  - [ ] 6.6: Тест атомарности: при искусственной ошибке (например, `variant.stock_quantity < quantity` после валидации) — ни мастер, ни субзаказы не сохраняются.
  - [ ] 6.7: Тест snapshot `OrderItem.vat_rate`: заполняется через `build_snapshot` во всех субзаказах.
  - [ ] 6.8: Все тесты файла помечены `@pytest.mark.unit` и `@pytest.mark.django_db`.
- [ ] Task 7: Integration/API-тесты (AC: 8, 9, 10, 11, 12, 13)
  - [ ] 7.1: В `backend/tests/integration/test_cart_order_integration.py` добавить тест: `POST /api/v1/orders/` с мульти-VAT корзиной → 201, в БД 1 master + 2 sub, ответ содержит все позиции в `items`.
  - [ ] 7.2: Тест `GET /api/v1/orders/` возвращает только мастера (субзаказов нет в списке).
  - [ ] 7.3: Тест `GET /api/v1/orders/<sub_order_id>/` → 404.
  - [ ] 7.4: Тест `POST /api/v1/orders/<master_id>/cancel/` → мастер и все субзаказы в статусе `cancelled`.
  - [ ] 7.5: Тест `POST /api/v1/orders/<sub_order_id>/cancel/` → 404.
  - [ ] 7.6: Регрессионный тест: существующий сценарий однородной корзины продолжает работать без изменений в клиентском контракте.
  - [ ] 7.7: Все тесты помечены `@pytest.mark.integration` и `@pytest.mark.django_db`.
- [ ] Task 8: Обновление сериализатора ответа (AC: 11, 12)
  - [ ] 8.1: В `OrderDetailSerializer` — переопределить источник `items` через `SerializerMethodField` `get_items(self, obj)`, который для `obj.is_master=True` агрегирует позиции из `sub_orders`.
  - [ ] 8.2: Для субзаказа (если каким-то образом попадёт в сериализатор, например во внутренней админке) — отдавать свои `items` как раньше.
  - [ ] 8.3: `total_items`, `subtotal`, `calculated_total` — также через `SerializerMethodField` с учётом агрегации для мастера.
- [ ] Task 9: Проверка/обновление документации API (опционально)
  - [ ] 9.1: Обновить docstring `OrderViewSet` и `extend_schema` description: отметить, что клиенту видны только мастер-заказы, а субзаказы — внутренняя структура для 1С.

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

### Точка входа: текущий `OrderCreateSerializer.create()` (до изменений)

См. @/Users/1/DEV/FREESPORT/backend/apps/orders/serializers.py:205-282 — `@transaction.atomic`, создаёт один `Order`, `bulk_create(order_items)`, списывает остатки, чистит корзину. Сейчас **всегда `is_master=True` по умолчанию**, но на нём живут `OrderItem` — это нужно изменить (позиции должны жить на субзаказах).

### Рекомендуемая структура логики разбивки (псевдокод)

```python
@transaction.atomic
def create(self, validated_data):
    cart = validated_data.pop("_cart")
    user = self._resolve_user()
    delivery_cost = self.calculate_delivery_cost(validated_data["delivery_method"])

    # 1. Сгруппировать cart_items по variant.vat_rate
    groups: dict[Decimal | None, list[CartItem]] = defaultdict(list)
    total_items_sum = Decimal("0")
    for ci in cart.items.select_related("variant__product"):
        variant = ci.variant
        product = variant.product if variant else None
        if not variant or not product:
            raise serializers.ValidationError("Некорректный товар в корзине...")
        raw_vat = getattr(variant, "vat_rate", None)
        key = Decimal(str(raw_vat)) if raw_vat is not None else None
        groups[key].append(ci)
        total_items_sum += variant.get_price_for_user(user) * ci.quantity

    # 2. Создать мастер
    master = Order(
        user=user,
        is_master=True,
        parent_order=None,
        vat_group=None,
        delivery_cost=Decimal(delivery_cost),
        total_amount=total_items_sum + Decimal(delivery_cost),
        **validated_data,  # delivery_address, delivery_method, payment_method, notes, customer_*
    )
    master.save()

    # 3. Создать субзаказы и их OrderItem
    variant_updates: list[tuple[int, int]] = []
    for vat_key, items in groups.items():
        group_total = sum(
            ci.variant.get_price_for_user(user) * ci.quantity for ci in items
        )
        sub = Order(
            user=user,
            is_master=False,
            parent_order=master,
            vat_group=vat_key,  # может быть None
            delivery_cost=Decimal("0"),
            total_amount=group_total,
            status="pending",
            payment_status="pending",
            # Наследуем клиентские данные от мастера:
            customer_name=master.customer_name,
            customer_email=master.customer_email,
            customer_phone=master.customer_phone,
            delivery_address=master.delivery_address,
            delivery_method=master.delivery_method,
            delivery_date=master.delivery_date,
            payment_method=master.payment_method,
            notes=master.notes,
        )
        sub.save()

        order_items = []
        for ci in items:
            variant = ci.variant
            product = variant.product
            unit_price = variant.get_price_for_user(user)
            snapshot = OrderItem.build_snapshot(product, variant)
            order_items.append(OrderItem(
                order=sub,
                product=product,
                variant=variant,
                quantity=ci.quantity,
                unit_price=unit_price,
                total_price=unit_price * ci.quantity,
                **snapshot,
            ))
            variant_updates.append((variant.pk, ci.quantity))
        OrderItem.objects.bulk_create(order_items)

    # 4. Списать остатки
    for variant_pk, qty in variant_updates:
        ProductVariant.objects.filter(pk=variant_pk).update(
            stock_quantity=F("stock_quantity") - qty
        )

    # 5. Очистить корзину
    cart.clear()

    return master
```

### Агрегация `items` на мастере в `OrderDetailSerializer`

Текущий сериализатор: `items = OrderItemSerializer(many=True, read_only=True)` — берёт `instance.items.all()`. После разбивки `master.items` будет пустым. Нужно:

```python
class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    calculated_total = serializers.SerializerMethodField()

    def get_items(self, obj: Order):
        if obj.is_master:
            qs = OrderItem.objects.filter(order__parent_order=obj).select_related("product", "variant")
            return OrderItemSerializer(qs, many=True).data
        return OrderItemSerializer(obj.items.all(), many=True).data

    def get_subtotal(self, obj):
        if obj.is_master:
            return sum(
                (i.total_price for sub in obj.sub_orders.all() for i in sub.items.all()),
                Decimal("0"),
            )
        return obj.subtotal

    # total_items и calculated_total аналогично
```

Для N+1 — использовать `prefetch_related("sub_orders__items__product", "sub_orders__items__variant")` в `OrderViewSet.get_queryset()`.

### Фильтр мастер-заказов в `get_queryset()`

```python
def get_queryset(self):
    user = self.request.user
    if user.is_authenticated:
        return (
            Order.objects.filter(user=user, is_master=True)
            .select_related("user")
            .prefetch_related(
                "sub_orders__items__product",
                "sub_orders__items__variant",
            )
            .order_by("-created_at")
        )
    return Order.objects.none()
```

### Cascade cancel

```python
@action(detail=True, methods=["post"])
def cancel(self, request, pk=None):
    order = self.get_object()  # уже отфильтровано is_master=True
    ...
    order.status = "cancelled"
    order.save()
    order.sub_orders.update(status="cancelled")  # bulk update субзаказов
    ...
```

### Текущее состояние моделей (актуально после Story 34-1)

См. @/Users/1/DEV/FREESPORT/backend/apps/orders/models.py:29-77 для `Order` TYPE_CHECKING блока (поля `parent_order`, `is_master`, `vat_group`, `sub_orders` уже объявлены). `OrderItem.vat_rate` — @/Users/1/DEV/FREESPORT/backend/apps/orders/models.py:395-405. Helper `build_snapshot` — @/Users/1/DEV/FREESPORT/backend/apps/orders/models.py:421-440.

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

_TBD_

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Change |
|------|--------|
| 2026-04-16 | Story создана через create-story workflow по sprint-change-proposal §4.3–4.4. Status → ready-for-dev. |
