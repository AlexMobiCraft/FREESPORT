# Story 39.1: Роль wholesale_level4 и цена opt4_price в модели

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Менеджер**,
I want **чтобы на портале существовал четвёртый оптовый уровень с собственной ценой**,
so that **я мог назначить его клиенту с оборотом до 50 тыс. руб. в квартал, а заказ такого клиента уехал в 1С по правильному виду цен**.

## Acceptance Criteria

1. **AC1 (FR-39-01).** В `ProductVariant` (`backend/apps/products/models.py`) добавлено поле `opt4_price` по образцу `opt3_price`, с `help_text="Цена для роли wholesale_level4"`.
2. **AC2 (FR-39-01, NFR-3940-06).** Миграция схемы приложения `products` применена на PostgreSQL в Docker: поле создано, `CheckConstraint` с именем `products_opt4_price_positive` объявлен в `ProductVariant.Meta.constraints` и отклоняет отрицательное значение.
3. **AC3 (FR-39-04).** `PriceType.product_field` содержит choice `("opt4_price", "Оптовая цена уровень 4")`.
4. **AC4 (FR-39-04, NFR-3940-06).** Data-миграция приложения `products` создаёт запись `PriceType` с `onec_id="4c1962d2-f8ed-11eb-81f3-00155d3cae02"`, `onec_name="Опт 4 (до 50 тыс.руб в квартал)"`, `product_field="opt4_price"`, `user_role="wholesale_level4"`. Повторное применение не создаёт дубля; `reverse` удаляет **только** эту запись, не трогая остальные шесть.
5. **AC5 (FR-39-02).** Роль `wholesale_level4` присутствует в `User.ROLE_CHOICES` и в `User.B2B_ROLES`; `is_b2b_user` для неё возвращает `True`; `role_map` в блоке `TYPE_CHECKING` (`users/models.py:140`) её учитывает.
6. **AC6 (FR-39-02).** Миграция приложения `users` синхронизирует `choices` поля `role` со схемой через `AlterField` — по образцу `users/migrations/0017_add_unregistered_role.py`.
7. **AC7 (FR-39-03).** `ProductVariant.get_price_for_user` для пользователя с ролью `wholesale_level4` и заполненным `opt4_price` возвращает `opt4_price`.
8. **AC8 (FR-39-03).** Тот же вызов при пустом `opt4_price` возвращает `retail_price` — fallback как у уровней 1-3 (сразу на retail, без каскада).
9. **AC9 (FR-39-12).** В `ONEC_EXCHANGE` (`backend/freesport/settings/base.py`): `PRICE_TYPE_BY_ROLE["wholesale_level4"] == "Опт 4 (до 50 тыс.руб в квартал)"`, а `PRICE_TYPE_ID_BY_NAME` содержит это наименование с GUID `4c1962d2-f8ed-11eb-81f3-00155d3cae02`.
10. **AC10 (FR-39-12).** Заказ пользователя с ролью `wholesale_level4` уезжает в 1С с видом цен «Опт 4 (до 50 тыс.руб в квартал)» и его GUID. Код `OrderExportService._get_price_type` (`orders/services/order_export.py:550`) при этом **не изменяется** — работает только за счёт настроек.
11. **AC11 (NFR-3940-02, -06).** Все новые тесты помечены `@pytest.mark.unit` либо `@pytest.mark.integration` и проходят в `make test-unit`; `python manage.py makemigrations --check --dry-run` не находит незакоммиченных миграций.

## Tasks / Subtasks

- [ ] Task 1: Поле `ProductVariant.opt4_price` + constraint (AC: 1, 2)
  - [ ] 1.1: Добавить `opt4_price` после `opt3_price` в `products/models.py` (точный код — в Dev Notes)
  - [ ] 1.2: Обновить комментарий-заголовок блока цен: `# Цены для различных ролей (6 типов)` → `(7 типов)`
  - [ ] 1.3: Добавить в `ProductVariant.Meta` **новый** атрибут `constraints` с `CheckConstraint(condition=..., name="products_opt4_price_positive")` — сегодня у `ProductVariant.Meta` нет `constraints` вообще
  - [ ] 1.4: `makemigrations products --name add_opt4_price` → должна получиться `0052_add_opt4_price.py`
- [ ] Task 2: Choice `opt4_price` в `PriceType.product_field` (AC: 3)
  - [ ] 2.1: Добавить `("opt4_price", "Оптовая цена уровень 4")` после `opt3_price` в `PriceType.product_field.choices` (`products/models.py:724`)
  - [ ] 2.2: Убедиться, что `AlterField` для `pricetype.product_field` попал в ту же миграцию `0052_*` (не создавать отдельную)
- [ ] Task 3: Data-миграция — запись `PriceType` для «Опт 4» (AC: 4)
  - [ ] 3.1: `makemigrations products --empty --name seed_price_type_opt4` → `0053_seed_price_type_opt4.py`
  - [ ] 3.2: Написать `forwards`/`backwards` через `apps.get_model("products", "PriceType")` (точный код — в Dev Notes)
  - [ ] 3.3: Идемпотентность — `update_or_create(onec_id=GUID, defaults={...})`
  - [ ] 3.4: `reverse` — `filter(onec_id=GUID).delete()`, никаких массовых удалений
- [ ] Task 4: Роль `wholesale_level4` в модели `User` (AC: 5, 6)
  - [ ] 4.1: `ROLE_CHOICES` — вставить `("wholesale_level4", "Оптовик уровень 4")` **после** `wholesale_level3` и **до** `trainer`
  - [ ] 4.2: `B2B_ROLES` — добавить `"wholesale_level4"` после `"wholesale_level3"`
  - [ ] 4.3: `role_map` в блоке `if TYPE_CHECKING` (`users/models.py:140`) — добавить ту же пару
  - [ ] 4.4: `makemigrations users --name add_wholesale_level4_role` → `0020_add_wholesale_level4_role.py`, проверить что это `AlterField` поля `role` с полным списком choices
- [ ] Task 5: `get_price_for_user` (AC: 7, 8)
  - [ ] 5.1: Добавить `"wholesale_level4": self.opt4_price or self.retail_price` в `role_price_mapping` (`products/models.py:1173`) после `wholesale_level3`
- [ ] Task 6: Настройки обмена с 1С (AC: 9, 10)
  - [ ] 6.1: `PRICE_TYPE_BY_ROLE["wholesale_level4"] = "Опт 4 (до 50 тыс.руб в квартал)"` (после `wholesale_level3`)
  - [ ] 6.2: `PRICE_TYPE_ID_BY_NAME["Опт 4 (до 50 тыс.руб в квартал)"] = "4c1962d2-f8ed-11eb-81f3-00155d3cae02"`
  - [ ] 6.3: Убедиться, что `orders/services/order_export.py` **не тронут**
- [ ] Task 7: Применить миграции и проверить схему (AC: 2, 11)
  - [ ] 7.1: `migrate products` и `migrate users` в Docker на PostgreSQL
  - [ ] 7.2: Проверить, что constraint реально отклоняет отрицательное значение
  - [ ] 7.3: `makemigrations --check --dry-run` — пусто
- [ ] Task 8: Тесты (AC: 2, 4, 5, 7, 8, 9, 10, 11)
  - [ ] 8.1: `get_price_for_user` для `wholesale_level4`: цена заполнена → `opt4_price`; цена пустая → `retail_price`
  - [ ] 8.2: Constraint: `ProductVariant` с `opt4_price = Decimal("-1")` → `IntegrityError`
  - [ ] 8.3: Data-миграция: прямой вызов `forwards`/`backwards` (см. Dev Notes — на живую БД в тестах полагаться нельзя)
  - [ ] 8.4: Роль: `"wholesale_level4" in User.B2B_ROLES`, `User(role="wholesale_level4").is_b2b_user is True`, роль есть в `ROLE_CHOICES`
  - [ ] 8.5: Настройки: `settings.ONEC_EXCHANGE["PRICE_TYPE_BY_ROLE"]["wholesale_level4"]` и соответствующий GUID в `PRICE_TYPE_ID_BY_NAME` — тест на **реальных** настройках, без подмены через фикстуру `settings`
  - [ ] 8.6: Экспорт заказа: `_get_price_type(order)` для пользователя `wholesale_level4` на реальных настройках → «Опт 4 (до 50 тыс.руб в квартал)»; `<ВидЦены>/<Ид>` в XML содержит GUID
  - [ ] 8.7: Все новые тесты помечены маркерами
- [ ] Task 9: Прогон и регресс (AC: 11)
  - [ ] 9.1: `make test-unit` целиком (не только новые файлы) — новая роль автоматически попадает в параметризованные регресс-тесты, см. Dev Notes
  - [ ] 9.2: `make lint` / Black + Flake8

## Dev Notes

### Релизное правило эпика

Стори эпика 39 **на прод по одной не выкатываются** (решение Alex, 2026-08-02): релиз собирается после реализации 39.1 → 39.2 → 39.3 → 39.4 целиком. Поэтому промежуточные несогласованности между стори (перетирание `product_field` импортом до 39.2, роль в публичном списке без приёма в сериализаторе до 39.3) — состояния релизной ветки, а не продуктивные дефекты. Чинить их внутри 39.1 не нужно; знать о них нужно, чтобы не диагностировать их как собственные баги при локальном прогоне.

### Blast radius (перед правкой)

`npx gitnexus impact get_price_for_user --direction upstream` → risk **LOW**, 3 прямых вызывающих, 0 затронутых процессов:

- `products/serializers.py: ProductVariantSerializer.get_current_price`
- `products/serializers.py: ProductListSerializer.get_current_price`
- `products/serializers_variant.py: ProductVariantSerializer.get_current_price`

**Индекс GitNexus устарел** (проиндексирован `ee99542`, HEAD `2f6f9f7`) и пропускает ещё два вызывающих, найденных прямым поиском:

- `cart/models.py:154` — `self.price_snapshot = self.variant.get_price_for_user(user)`
- `cart/views.py:142` — `price = variant.get_price_for_user(user)`

Изменение аддитивное (новый ключ в словаре), поэтому все пять точек продолжают работать без правок. Перед коммитом — `npx gitnexus detect-changes --scope all`; если индекс всё ещё stale, попроси Alex выполнить `! npx gitnexus analyze`.

### Точный код: поле `ProductVariant.opt4_price`

Вставить в `backend/apps/products/models.py` **сразу после** `opt3_price` (строка ~910), перед `trainer_price`:

```python
opt4_price = cast(
    Decimal | None,
    models.DecimalField(
        "Оптовая цена уровень 4",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Цена для роли wholesale_level4",
    ),
)
```

Комментарий-заголовок блока (строка 864) — `# Цены для различных ролей (6 типов)` → `# Цены для различных ролей (7 типов)`.

### Точный код: CheckConstraint

Constraint вешается на **`ProductVariant`** — там, где живут ценовые поля. Историческая справка, чтобы не искать образец не в том месте: ценовые `CheckConstraint` из `0003_add_constraints.py` относились к модели `Product`, были сняты миграцией `0004_remove_brand_brands_unique_active_name_and_more.py:32`, а сами поля переехали на `ProductVariant` миграцией `0024_add_productvariant_colormapping.py`. **Сегодня у `ProductVariant` нет ни одного `CheckConstraint`** — в `Meta` только `indexes`.

Добавить в `ProductVariant.Meta` (`products/models.py:1076`, после списка `indexes`) новый атрибут:

```python
constraints = [
    models.CheckConstraint(
        condition=models.Q(opt4_price__gte=0) | models.Q(opt4_price__isnull=True),
        name="products_opt4_price_positive",
    ),
]
```

- `Q` в `products/models.py` **не импортируется** отдельно — файл использует `models.Q(...)`. Живой образец `Meta.constraints` в этом же файле: `ImportSession.Meta` (строка 665).
- **Django 5.2.7:** аргумент называется `condition`, а не `check`. `check=` устарел и даёт ошибку конфигурации — именно на неё натыкались в story 34.1 (`CheckConstraint(..., check=...)` в `apps/cart/models.py`).
- Имя `products_opt4_price_positive` сохраняем как задано в AC, хотя таблица — `product_variants`. Имена constraint'ов уникальны в пределах БД, коллизии нет: старый одноимённый объект удалён миграцией 0004.

### Миграции: точные номера

| Приложение | Последняя существующая | Новая |
|---|---|---|
| `products` | `0051_alter_productvariant_vat_rate.py` | `0052_add_opt4_price.py` (схема) → `0053_seed_price_type_opt4.py` (данные) |
| `users` | `0019_add_users_tax_id_index.py` | `0020_add_wholesale_level4_role.py` |

`0052` должна содержать три операции: `AddField` (`productvariant.opt4_price`), `AlterField` (`pricetype.product_field` — новые choices), `AddConstraint` (`productvariant`).

### Точный код: data-миграция `0053_seed_price_type_opt4.py`

```python
# Справочник видов цен: «Опт 4» для роли wholesale_level4

from django.db import migrations

OPT4_ONEC_ID = "4c1962d2-f8ed-11eb-81f3-00155d3cae02"
OPT4_ONEC_NAME = "Опт 4 (до 50 тыс.руб в квартал)"


def seed_opt4_price_type(apps, schema_editor):
    """Заводит вид цен «Опт 4». Идемпотентно: повторный прогон обновляет запись."""
    PriceType = apps.get_model("products", "PriceType")
    PriceType.objects.update_or_create(
        onec_id=OPT4_ONEC_ID,
        defaults={
            "onec_name": OPT4_ONEC_NAME,
            "product_field": "opt4_price",
            "user_role": "wholesale_level4",
            "is_active": True,
        },
    )


def remove_opt4_price_type(apps, schema_editor):
    """Удаляет только запись «Опт 4», остальные шесть видов цен не трогает."""
    PriceType = apps.get_model("products", "PriceType")
    PriceType.objects.filter(onec_id=OPT4_ONEC_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0052_add_opt4_price"),
    ]

    operations = [
        migrations.RunPython(seed_opt4_price_type, reverse_code=remove_opt4_price_type),
    ]
```

Образец обратимой data-миграции по `PriceType` — `products/migrations/0038_update_pricetype_codes.py`.

### Почему `product_field` нельзя считать декоративной колонкой

**Релизное правило (решение Alex, 2026-08-02): стори эпика 39 на прод по одной не уезжают — релиз собирается после реализации всех четырёх.** Описанное ниже состояние живёт только внутри релизной ветки и до продуктива не доходит. Знать о нём всё равно нужно: оно объясняет, почему data-миграция 39.1 без парсера 39.2 неполна, и что проверять при локальном прогоне импорта.

`PriceType.product_field` — **источник маршрутизации цен при импорте**:

- `variant_import.py:1078` находит `PriceType` по `onec_id` из выгрузки и пишет цену в поле `price_type.product_field`;
- `variant_import.py:1536` (`process_price_types`) на каждом импорте делает `update_or_create(onec_id=..., defaults={"onec_name", "product_field", "is_active"})`, где `product_field` берётся из `XMLDataParser._map_price_type_to_field` (`parser.py:537`);
- сегодня этот маппер не знает «Опт 4» и возвращает fallback `"retail_price"`.

Отсюда два следствия:

1. Значение `product_field="opt4_price"`, записанное нашей data-миграцией, **будет перетёрто на `"retail_price"`** первым же импортом цен, пока в кодовой базе нет ветки из стори 39.2.
2. С перетёртым значением цены «Опт 4» из 1С поедут в **`retail_price`** — розничная цена будет заменена оптовой.

Практические выводы для 39.1:

- **Не запускать импорт цен из 1С на локальной/тестовой базе** между реализацией 39.1 и 39.2 — иначе получишь испорченные `retail_price` и seeded-запись со сбитым `product_field`, и будешь искать несуществующий баг в своей миграции. Если это уже случилось — повторный `migrate products 0052` не поможет, запись чинится повторным прогоном `seed_opt4_price_type` (она идемпотентна).
- Стори 39.2 (ветка `"опт 4"/"опт4"` в `_map_price_type_to_field`) закрывает дыру окончательно: парсер начнёт возвращать то же значение, что записала миграция.

Что при этом безопасно: `user_role` **отсутствует** в `defaults` у `process_price_types`, поэтому значение `"wholesale_level4"`, записанное миграцией, импорт не затирает никогда.

### Точный код: роль в `users/models.py`

`ROLE_CHOICES` (строка 153) — вставить между `wholesale_level3` и `trainer`:

```python
("wholesale_level4", "Оптовик уровень 4"),
```

`B2B_ROLES` (строка 176) — добавить после `"wholesale_level3"`:

```python
"wholesale_level4",
```

`role_map` внутри `if TYPE_CHECKING` (строка 140) — та же пара `"wholesale_level4": "Оптовик уровень 4"` после `wholesale_level3`.

Порядок вставки важен: он определяет порядок в выпадающем списке админки и в публичном ответе `user_roles_view`. `role` объявлен как `max_length=20`, `"wholesale_level4"` — 16 символов, менять длину не нужно.

`is_b2b_user` (строка 365) — `return self.role in self.B2B_ROLES`, отдельной правки не требует, `True` появится автоматически.

Миграция `users` пишется по образцу `0017_add_unregistered_role.py`: один `AlterField` с **полным** списком choices, включая новую роль.

### Точный код: `get_price_for_user`

`products/models.py:1173`, в `role_price_mapping` после `wholesale_level3`:

```python
"wholesale_level4": self.opt4_price or self.retail_price,
```

Fallback — сразу `retail_price`, без каскада `opt3 → opt2 → opt1`. Фронтенд использует каскад; расхождение существует для уровней 1-3 и в этом эпике **не чинится** (см. epics.md, «Вне объёма»).

### Точный код: настройки обмена

`backend/freesport/settings/base.py`, блок `ONEC_EXCHANGE`:

```python
"PRICE_TYPE_BY_ROLE": {
    ...
    "wholesale_level3": "Опт 3 (50-150 тыс.руб в квартал)",
    "wholesale_level4": "Опт 4 (до 50 тыс.руб в квартал)",
    ...
},
"PRICE_TYPE_ID_BY_NAME": {
    ...
    "Опт 3 (50-150 тыс.руб в квартал)": "c05f0e2b-b3f2-11ea-81c3-00155d3cae02",
    "Опт 4 (до 50 тыс.руб в квартал)": "4c1962d2-f8ed-11eb-81f3-00155d3cae02",
    ...
},
```

Наименование должно совпадать **посимвольно** в трёх местах: `PRICE_TYPE_BY_ROLE`, ключ `PRICE_TYPE_ID_BY_NAME` и `onec_name` в data-миграции. `_get_price_type_id` ищет GUID по строке-наименованию (`order_export.py:563`) — опечатка даст `<ВидЦены>` без `<Ид>` молча, без исключения.

### Побочные эффекты новой роли (проверено, править НЕ нужно)

| Место | Что произойдёт | Действие |
|---|---|---|
| `banners/services.py:32` `_ALL_ROLE_KEYS` | Собирается из `User.ROLE_CHOICES` — новая роль подхватится сама, инвалидация кеша баннеров продолжит работать | Ничего |
| `banners/services.py:138` | Множество оптовых ролей захардкожено, `wholesale_level4` баннеров `show_to_wholesale` не увидит | **Стори 39.3**, не здесь |
| `users/admin.py:422` `role_display` | `role_colors.get(obj.role, "#6c757d")` — безопасный fallback на серый цвет | Собственный цвет — **стори 39.3** |
| `users/views/misc.py:48` `user_roles_view` | Роль автоматически появится в публичном списке ролей регистрации, но `UserRegistrationSerializer.SELF_SERVICE_ROLES` (`users/serializers.py:85`) её пока не принимает → регистрация с ней вернёт 400 | Ничего. Расходится только внутри релизной ветки, чинится **стори 39.3**. Не «исправлять» здесь фильтрацией `hidden_roles` — уровни 1-3 в публичном списке есть, четвёртый должен вести себя так же |
| `users/admin.py` форма пользователя | Менеджер сразу увидит «Оптовик уровень 4» в выпадающем списке; до 39.2/39.3 назначенный клиент получит retail-цены | Ничего, состояние промежуточное |

### Регресс-тесты, которые новая роль затрагивает автоматически

Прогнать весь `make test-unit`, а не только новые файлы:

- `backend/tests/unit/test_models/test_unlinked_1c_predicate.py:81` — параметризован по `User.ROLE_CHOICES`, получит новый кейс. Ожидание `in_queryset is (role == User.ROLE_UNREGISTERED)` для новой роли выполняется.
- `backend/apps/banners/tests/test_services.py:188-206` — проверяет, что `_ALL_ROLE_KEYS` == `ROLE_CHOICES` + `guest`. Проходит, потому что список выводится из модели.
- `backend/tests/integration/test_management_commands/test_import_customers.py:181` — валидирует роли из `ROLE_CHOICES`.

### ⚠️ Тестирование data-миграции: не полагаться на живую БД

Автоиспользуемая фикстура `clear_db_before_test` (`backend/tests/conftest.py:671`) запрашивает `transactional_db`, поэтому **каждый** тест в `backend/tests/` транзакционный, и pytest-django после него делает `flush` всей базы. Данные, засеянные data-миграциями, из тестовой БД пропадают. Проверять AC4 запросом `PriceType.objects.get(onec_id=...)` — значит написать тест, зависящий от порядка прогона.

Так же поступают существующие тесты: `apps/products/tests/test_api_products.py:169` создаёт `ColorMapping` через `get_or_create`, не рассчитывая на записи из миграции `0025_load_basic_colors`.

Правильный способ — вызвать функции миграции напрямую:

```python
import importlib

import pytest
from django.apps import apps as django_apps

migration = importlib.import_module("apps.products.migrations.0053_seed_price_type_opt4")


@pytest.mark.unit
@pytest.mark.django_db
class TestSeedOpt4PriceType:
    ...
```

Имя модуля начинается с цифры, поэтому только `importlib.import_module`, не `from ... import`. Далее:

- вызвать `seed_opt4_price_type(django_apps, None)` дважды → `PriceType.objects.filter(onec_id=GUID).count() == 1`;
- проверить `product_field == "opt4_price"`, `user_role == "wholesale_level4"`, `onec_name` посимвольно;
- создать перед этим пару контрольных `PriceType` (например, «Опт 3» и «РРЦ»), вызвать `remove_opt4_price_type(django_apps, None)` → запись «Опт 4» удалена, контрольные на месте.

### Куда класть тесты

| Что | Файл |
|---|---|
| `get_price_for_user` для новой роли, constraint на `opt4_price` | `backend/apps/products/tests/unit/test_price_logic.py` (есть фикстуры `product`, `variant`) либо `backend/apps/products/tests/test_product_variant_models.py` |
| Data-миграция `PriceType` | `backend/apps/products/tests/unit/test_price_logic.py` (новый класс) |
| Роль в `ROLE_CHOICES` / `B2B_ROLES` / `is_b2b_user` | `backend/tests/unit/test_models/` |
| `_get_price_type` и `<ВидЦены>` в XML | `backend/tests/unit/test_order_export_service.py` — класс с тестами `_get_price_type` начинается на строке ~1742, паттерн XML-проверки — `test_vid_tseny_in_item` (строка ~1966) |

Паттерны проекта: маркеры ставятся **над** классом (`@pytest.mark.unit` + `@pytest.mark.django_db`, см. `test_order_export_service.py:27`). Уникальные строковые данные — `get_unique_suffix()` из `tests/conftest.py`.

⚠️ Существующие тесты в `test_order_export_service.py` подменяют `settings.ONEC_EXCHANGE` фикстурой `settings`, то есть реальных значений из `base.py` не проверяют. Для AC9/AC10 нужен хотя бы один тест **без** подмены — иначе опечатка в наименовании или GUID пройдёт мимо всех тестов.

### Docker-команды

```bash
# Миграции
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py migrate products
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py migrate users
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py makemigrations --check --dry-run

# Тесты
make test-unit
docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend \
  pytest -xvs apps/products/tests/unit/test_price_logic.py
```

PostgreSQL обязателен — SQLite в проекте не поддерживается.

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** трогать `products/services/parser.py` и `products/services/variant_import.py` — это **стори 39.2** (маппинг «Опт 4» и сброс цен).
- **НЕ** трогать `products/filters.py`, `products/serializers.py`, `products/views.py`, `products/admin.py`, `products/factories.py`, `users/serializers.py`, `users/admin.py`, `banners/services.py` — это **стори 39.3**.
- **НЕ** трогать `frontend/` и `docs/api/openapi.yaml` — это **стори 39.3 (openapi) и 39.4 (фронт)**.
- **НЕ** изменять `orders/services/order_export.py` — AC10 требует, чтобы поведение появилось только из настроек.
- **НЕ** добавлять `opt4_price` в модель `Product` — ценовые поля живут на `ProductVariant` с миграции 0024.
- **НЕ** заполнять `user_role` у остальных шести записей `PriceType` — это **стори 40.3**.
- **НЕ** использовать `CheckConstraint(check=...)` — в Django 5.2 аргумент называется `condition`.
- **НЕ** чинить расхождение fallback между бэком и фронтом.
- **НЕ** менять `federation_rep`: вид цен «Партнер» на портал не выгружается, записи `PriceType` для него нет и быть не должно.

### Project Structure Notes

- Ценовые поля — только `ProductVariant` (`backend/apps/products/models.py:803`), таблица `product_variants`. У `Product` их нет с миграции `0024`.
- Справочник `PriceType` (`products/models.py:693`, таблица `price_types`) наполняется импортом из 1С (`priceLists.xml`), а не фикстурами. Наша data-миграция — первый случай, когда запись заводится кодом; идемпотентность по `onec_id` обязательна, поле `unique=True`.
- Комментарии и docstrings нового кода — на русском (NFR-3940-10, `project-context.md` §6).
- Типизация полей Django — строго через `cast()` из `typing`, как во всём файле.
- Покрытие: `products` — критический модуль, ≥ 90 %.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 39.1 — AC в BDD-формате]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 39 — порядок стори, релизное решение, «Вне объёма»]
- [Source: _bmad-output/planning-artifacts/epics.md#FR Coverage Map — FR-39-01 … FR-39-04, FR-39-12]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#7. Часть B — B1 таблица файлов]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#2.3. Виды цен — GUID и наименования всех семи видов]
- [Source: backend/apps/products/models.py:693 — PriceType; :875-934 — ценовые поля ProductVariant; :1076 — Meta; :1168 — get_price_for_user]
- [Source: backend/apps/products/models.py:665 — ImportSession.Meta.constraints, живой образец `models.Q(...)` + `condition=`]
- [Source: backend/apps/products/migrations/0003_add_constraints.py:34 — историческая форма CheckConstraint, модель Product]
- [Source: backend/apps/products/migrations/0004_remove_brand_brands_unique_active_name_and_more.py:32 — старый constraint удалён]
- [Source: backend/apps/products/migrations/0024_add_productvariant_colormapping.py:65 — цены переехали на ProductVariant]
- [Source: backend/apps/products/migrations/0038_update_pricetype_codes.py — образец обратимой data-миграции по PriceType]
- [Source: backend/apps/products/services/variant_import.py:1078, :1521 — product_field маршрутизирует цены; process_price_types перетирает его]
- [Source: backend/apps/products/services/parser.py:537 — _map_price_type_to_field, fallback retail_price]
- [Source: backend/apps/users/models.py:136-182 — TYPE_CHECKING role_map, ROLE_CHOICES, B2B_ROLES; :365 — is_b2b_user]
- [Source: backend/apps/users/migrations/0017_add_unregistered_role.py — образец AlterField для role]
- [Source: backend/freesport/settings/base.py:348-366 — ONEC_EXCHANGE]
- [Source: backend/apps/orders/services/order_export.py:550, :563 — _get_price_type, _get_price_type_id]
- [Source: backend/tests/conftest.py:671 — autouse clear_db_before_test на transactional_db]
- [Source: backend/tests/unit/test_order_export_service.py:1742, :1966 — паттерны тестов вида цен]
- [Source: project-context.md §3, §4, §6 — role-based pricing, тестирование, язык кода]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
