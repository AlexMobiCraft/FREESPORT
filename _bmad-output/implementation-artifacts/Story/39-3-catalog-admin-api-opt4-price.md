---
baseline_commit: 67045968e9fe5f9b6742eedc80bc8aff861ca169
---

# Story 39.3: Каталог, админка и API отдают цену уровня 4

Status: review

> ✅ **Координаты Dev Notes освежены 2026-08-03** после закрытия `tech-debt.md` п. 18 стори `security-wholesale-price-visibility`. Номера строк соответствуют рабочему дереву **с реализацией той стори поверх `67045968`** — на момент правки она ещё не была закоммичена, поэтому при расхождении сверять код, а не номера. Предупреждение о невалидных координатах на `61e10805` снято: те координаты больше не актуальны ни в каком виде.
>
> ✅ **Утечка оптовых цен закрыта** — `opt1/2/3_price` больше не уезжают анонимному `GET /api/v1/products/`. Гейт живёт в `backend/apps/products/pricing_policy.py` и применяется в `ProductListSerializer.to_representation`. **Что это меняет для 39.3:** `opt4_price` обязан попасть в `WHOLESALE_PRICE_FIELDS` (Task 2.5), иначе новое поле останется единственным неприкрытым и утечёт анонимам ровно так, как утекали три предыдущих. Литеральных списков `allowed_roles` в сериализаторах больше **нет** — правки ролевых белых списков делаются в `pricing_policy.py`.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Оптовый клиент четвёртого уровня**,
I want **видеть свою цену в каталоге, фильтровать по ней товары и получать её через API**,
so that **я мог работать с порталом так же, как клиенты уровней 1-3**.

## Acceptance Criteria

1. **AC1 (FR-39-06). Фильтры каталога.** В `ProductFilter.filter_min_price` (`backend/apps/products/filters.py:267-286`) и `filter_max_price` (`:301-319`) появляется ветка `wholesale_level4`, отдающая `Q(opt4_price__gte=value) | Q(opt4_price__isnull=True, retail_price__gte=value)` (и `__lte` соответственно) — по образцу ветки `wholesale_level3`. Ветка стоит **между** `wholesale_level3` и `trainer`; `else`-fallback на `retail_price` перестаёт перехватывать эту роль. Роль берётся из `resolve_pricing_role(...)`, а не из `request.user.role` — значит **неверифицированный** `wholesale_level4` в эту ветку не попадёт и отфильтруется по `retail_price`; это требуемое поведение, а не дефект.
2. **AC2 (FR-39-07). Поле `opt4_price` в API товара.** `ProductListSerializer` (`backend/apps/products/serializers.py:439`) объявляет `opt4_price = serializers.SerializerMethodField()` (рядом с `:465`), включает `"opt4_price"` в `Meta.fields` (рядом с `:501`) и реализует `get_opt4_price` по образцу `get_opt3_price` (`:612-617`). `ProductDetailSerializer` наследует `Meta.fields` от списочного и поле получает автоматически — отдельной правки не требует.
3. **AC3 (FR-39-07). Признак наличия цены у варианта.** Товар, у которого из ценовых полей заполнена **только** `opt4_price`, попадает в выдачу: условие `Q(...) | Q(opt4_price__gt=0)` добавлено в **обоих** местах — `ProductListSerializer._get_first_variant` (`serializers.py:531-542`) и `Prefetch` в `ProductViewSet.get_queryset` (`backend/apps/products/views.py:50`, блок `:83-90`). Пропуск любого из двух даёт молчаливый дефект: в детальной карточке цена есть, в списке — нет (или наоборот).
4. **AC4 (FR-39-07). Инфо-цены РРЦ/МРЦ и гейт оптового поля.** Списков `allowed_roles` в сериализаторах больше нет — видимостью управляет `backend/apps/products/pricing_policy.py`. Требуются **две** правки в нём: (а) `"wholesale_level4"` добавлен в `INFO_PRICE_ROLES` — четвёртый уровень оптовый и видит РРЦ/МРЦ наравне с уровнями 1-3; (б) `"opt4_price"` добавлен в `WHOLESALE_PRICE_FIELDS` — иначе новое поле окажется **единственным неприкрытым** и уедет анонимному `GET /api/v1/products/` (ровно тот дефект, который закрыт стори `security-wholesale-price-visibility`). Обе константы несут комментарий «стори 39.3 добавляет сюда …» — он ставился специально под эту правку и после неё снимается.
5. **AC5 (FR-39-08). Админка варианта товара.** В fieldset «Ценообразование» `ProductVariantAdmin` (`backend/apps/products/admin.py:632-646`) поле `opt4_price` стоит сразу после `opt3_price`. `list_display` и `ProductVariantInline` оптовых цен не показывают вовсе — их **не трогать**.
6. **AC6 (FR-39-08). Бейдж роли в админке пользователей.** `UserAdmin.role_display` (`backend/apps/users/admin.py:411-427`) отдаёт для `wholesale_level4` собственный цвет, отличный от всех семи существующих. Без записи в `role_colors` роль молча получает серый дефолт `#6c757d` и визуально сливается с `retail`.
7. **AC7 (FR-39-09). Регистрация с ролью уровня 4.** `UserRegistrationSerializer.SELF_SERVICE_ROLES` (`backend/apps/users/serializers.py:85-95`) содержит `wholesale_level4`, и `validate_role` эту роль принимает. Сегодня роль уже видна в публичном `/api/v1/users/roles/` (список строится из `User.ROLE_CHOICES`), но регистрация с ней падает с 400 «Недопустимая роль для регистрации» — этот промежуточный дефект релизной ветки закрывается здесь.
8. **AC8 (FR-39-10). Баннеры.** `_get_role_filter` (`backend/apps/banners/services.py:116-144`) относит `wholesale_level4` к оптовым: множество на `:138` дополнено, и роль получает `Q(show_to_authenticated=True) | Q(show_to_wholesale=True)`. Без правки роль проваливается в `else` и получает **гостевые** баннеры — авторизованный оптовик видит контент для анонимов.
9. **AC9 (FR-39-07). Фабрики тестовых данных.** `ProductVariantFactory` (`backend/apps/products/factories.py:145-147`) заполняет `opt4_price`, а `ProductFactory._create` (`:91-103`) принимает `opt4_price` в списке `variant_fields` — иначе передать цену уровня 4 через `ProductFactory(...)` невозможно.
10. **AC10 (FR-39-13, NFR-3940-07). API-контракт.** `docs/api/openapi.yaml` перегенерирован: схемы `ProductList` и `ProductDetail` содержат `opt4_price` (в `properties` и в `required`), `RoleEnum` содержит `wholesale_level4` с описанием «Оптовик уровень 4». Файл сегодня отстал от кода — роли `wholesale_level4` в нём нет с момента стори 39.1. `frontend/` в этой стори **не трогается**: регенерация типов — AC1 стори 39.4.
11. **AC11 (NFR-3940-02, -03). Тесты.** Покрыты: фильтр min/max по `opt4_price` для роли `wholesale_level4`; товар только с `opt4_price` виден и в списке, и в детальной карточке; `opt4_price` присутствует в ответе API; РРЦ/МРЦ видны роли уровня 4; регистрация с ролью уровня 4 проходит; баннеры для роли уровня 4 — оптовые; бейдж роли имеет собственный цвет. **Каждый** новый тест-класс несёт явный `@pytest.mark.unit` или `@pytest.mark.integration` — часть затрагиваемых тестовых файлов маркеров не имеет (см. Dev Notes → «Мина: тестовые файлы без маркеров»).

## Tasks / Subtasks

- [x] **Task 1: Фильтры каталога** (AC: 1)
  - [x] 1.1: `filters.py` — ветка `wholesale_level4` в `filter_min_price` после ветки `wholesale_level3` (`:275-276`)
  - [x] 1.2: `filters.py` — то же в `filter_max_price` (`:308-309`), с `__lte`
  - [x] 1.3: Ничего больше в файле не менять — `_variant_filters`, `qs`-property, subquery-оптимизация и вызов `resolve_pricing_role` правок не требуют

- [x] **Task 2: Сериализаторы товаров и политика цен** (AC: 2, 3, 4)
  - [x] 2.1: `serializers.py:465` — объявить `opt4_price = serializers.SerializerMethodField()` после `opt3_price`
  - [x] 2.2: `serializers.py:501` — добавить `"opt4_price"` в `Meta.fields` после `"opt3_price"`
  - [x] 2.3: `serializers.py:617` — реализовать `get_opt4_price` по образцу `get_opt3_price` (точный код — в Dev Notes)
  - [x] 2.4: `serializers.py:536` — добавить `| Q(opt4_price__gt=0)` в фильтр `_get_first_variant`
  - [x] 2.5: `apps/products/pricing_policy.py` — добавить `"opt4_price"` в `WHOLESALE_PRICE_FIELDS` (гейт нового поля) **и** `"wholesale_level4"` в `INFO_PRICE_ROLES` (РРЦ/МРЦ); снять комментарии-подсказки «стори 39.3 добавляет сюда …». Списков `allowed_roles` в сериализаторах больше нет — искать их бессмысленно
  - [x] 2.6: `serializers.py:449` — обновить docstring («…opt3_price, opt4_price»)
  - [x] 2.7: `ProductDetailSerializer` **не править** — наследует `Meta.fields`
  - [x] 2.8: `to_representation` обоих сериализаторов (`:94`, `:562`) **не править** — они уже выражены через предикаты `pricing_policy`, новое поле подхватится из константы

- [x] **Task 3: Prefetch во вью каталога** (AC: 3)
  - [x] 3.1: `views.py:87` — добавить `| Q(opt4_price__gt=0)` в `Prefetch` `first_variant_list`
  - [x] 3.2: Аннотации `min_retail_price` / `total_stock` / `has_stock` **не трогать** — сортировка по цене осталась розничной осознанно (вне объёма эпика)

- [x] **Task 4: Админка** (AC: 5, 6)
  - [x] 4.1: `products/admin.py:641` — `"opt4_price"` в fieldset «Ценообразование» после `"opt3_price"`
  - [x] 4.2: `users/admin.py:417` — `"wholesale_level4": "#d63384",  # розовый` в `role_colors` после `wholesale_level3`

- [x] **Task 5: Роль в пользовательском API и баннерах** (AC: 7, 8)
  - [x] 5.1: `users/serializers.py:90` — `"wholesale_level4"` в `SELF_SERVICE_ROLES` после `"wholesale_level3"`
  - [x] 5.2: `banners/services.py:138` — `"wholesale_level4"` в множество оптовых ролей
  - [x] 5.3: `banners/services.py:_ALL_ROLE_KEYS` (`:32`) **не трогать** — строится из `User.ROLE_CHOICES`, роль там уже есть

- [x] **Task 6: Фабрики** (AC: 9)
  - [x] 6.1: `factories.py:95` — `"opt4_price"` в список `variant_fields` метода `ProductFactory._create`
  - [x] 6.2: `factories.py:146` — `opt4_price = fuzzy.FuzzyDecimal(90.0, 9000.0, 2)` с комментарием (обоснование диапазона — в Dev Notes)

- [x] **Task 7: Тесты** (AC: 11, покрывают 1-9)
  - [x] 7.1: `backend/tests/unit/test_product_filters.py` — добавить `"wholesale_level4"` в `roles_to_test` (`:313`) и новый класс `TestOpt4PriceFilter` с `@pytest.mark.unit`: min/max-фильтр для роли даёт `Q` по `opt4_price`
  - [x] 7.2: **Новый** `backend/apps/products/tests/unit/test_opt4_catalog_api.py`, `pytestmark = [pytest.mark.unit, pytest.mark.django_db]` — AC2, AC3, AC4, AC5 (структура — в Dev Notes)
  - [x] 7.3: `backend/tests/unit/test_serializers/test_user_serializers.py` — новый класс с явным `@pytest.mark.unit`: регистрация с `role="wholesale_level4"` валидна (AC7)
  - [x] 7.4: `backend/apps/banners/tests/test_services.py` — новый класс с `@pytest.mark.unit`: `_get_role_filter("wholesale_level4")` даёт оптовый `Q`, а не гостевой (AC8)
  - [x] 7.5: `backend/tests/unit/test_users_admin.py` (файл целиком `pytestmark = pytest.mark.unit`) — цвет бейджа для роли уровня 4 существует и уникален (AC6)
  - [x] 7.6: Проверить, что новые тесты действительно попадают в `-m unit` (см. «Мина: тестовые файлы без маркеров»)

- [x] **Task 8: API-контракт** (AC: 10)
  - [x] 8.1: Перегенерировать `docs/api/openapi.yaml` (точная команда — в Dev Notes)
  - [x] 8.2: Проверить diff: должны появиться `opt4_price` в двух схемах товара и `wholesale_level4` в `RoleEnum`
  - [x] 8.3: Если в diff есть посторонние ханки — оценить их по Dev Notes → «Дрейф openapi.yaml»; при структурном расхождении остановиться и спросить Alex
  - [x] 8.4: `frontend/` **не трогать** — `npm run generate:types` выполняется в стори 39.4

- [x] **Task 9: Прогон и регресс** (AC: 11)
  - [x] 9.1: Полный unit-прогон (эквивалент `make test-unit`, команды — в Dev Notes). Базовая линия после 39.2: **1041 passed, 1 skipped**
  - [x] 9.2: Полный integration-прогон (≈ 30 мин, запускать в фоне). Базовая линия: **744 passed, 2 skipped**
  - [x] 9.3: `black --check` + `flake8` по изменённым файлам
  - [x] 9.4: `npx gitnexus detect-changes --scope all` перед коммитом

## Dev Notes

### Что уже сделано в 39.1 и 39.2 — переделывать НЕ нужно

Проверено по коду на `61e1080`:

| Слой | Состояние |
|---|---|
| `ProductVariant.opt4_price` (`products/models.py:912-923`) + `CheckConstraint products_opt4_price_positive` | ✅ 39.1 |
| `get_price_for_user` → `"wholesale_level4": self.opt4_price or self.retail_price` (`models.py:1198`) | ✅ 39.1 |
| `PriceType.product_field` choice `("opt4_price", …)` (`models.py:724`) + data-миграция `0053_seed_price_type_opt4` | ✅ 39.1 |
| `User.ROLE_CHOICES`, `B2B_ROLES`, `role_map`, `is_wholesale_user`, `wholesale_level` | ✅ 39.1 (все содержат уровень 4) |
| `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE` / `PRICE_TYPE_ID_BY_NAME` | ✅ 39.1 |
| Маппинг «Опт 4» в парсере 1С + `opt4_price=None` в конструкторах варианта | ✅ 39.2 |

**Следствия для этой стори:**

- `current_price` в сериализаторах вызывает `variant.get_price_for_user(user)` — цену уровня 4 он отдаёт **уже сейчас**, править не нужно.
- `User.wholesale_level` парсит цифру из имени роли и для `wholesale_level4` возвращает `4` без правок. Docstring `«(1, 2, 3)»` (`users/models.py:399`) неточен, но это косметика вне объёма — не трогать.
- `banners/services.py:_ALL_ROLE_KEYS` строится из `ROLE_CHOICES` — ключ кэша для роли уже есть; ломается только фильтр.
- `user_roles_view` (`users/views/misc.py:41`) строит список из `ROLE_CHOICES` за вычетом `admin`/`unregistered` — роль уже публикуется. Именно поэтому AC7 обязателен: витрина роль предлагает, регистрация её отвергает.

### Blast radius (обязательный GitNexus pre-flight выполнен)

| Символ | Risk | Прямых вызывающих |
|---|---|---|
| `ProductFilter.filter_min_price` | **LOW** | 0 (вызывается django-filter по имени метода) |
| `ProductFilter.filter_max_price` | **LOW** | 0 (то же) |
| `ProductListSerializer._get_first_variant` (`serializers.py:520`) | **MEDIUM** | **9**, все внутри модуля Products: `get_retail_price`, `get_current_price`, `get_sku`, `get_rrp`, `get_msrp`, `get_opt1_price`, `get_opt2_price`, `get_opt3_price`, `get_stock_quantity` |
| `banners.services._get_role_filter` | **LOW** | 2 — `get_active_banners_queryset`, `compute_cache_ttl` |
| `UserRegistrationSerializer.validate_role` | **LOW** | 0 (вызывается DRF по соглашению об именах) |

⚠️ **MEDIUM у `_get_first_variant`** — единственная точка стори с нетривиальным радиусом. Правка **строго аддитивная**: один дизъюнкт `| Q(opt4_price__gt=0)` в фильтре fallback-запроса. Сигнатура, возвращаемый тип и порядок `order_by("retail_price")` не меняются, поэтому все девять вызывающих продолжают работать как прежде. Расширение отбора может добавить в выдачу варианты, которые раньше отсеивались (ровно те, у которых заполнена только `opt4_price`) — это и есть требование AC3, а не регресс.

⚠️ Индекс GitNexus на `67045968` был `up-to-date`, но **реализация стори `security-wholesale-price-visibility` в него не попала** — модуль `pricing_policy.py` и его функции (`resolve_pricing_role`, `can_see_wholesale_prices`, `can_see_info_prices`) индексу неизвестны. `context`/`impact` по ним вернёт `{"error": "Symbol ... not found"}` — это устаревший индекс, а не отсутствие кода. Попроси Alex выполнить `! npx gitnexus analyze` до pre-flight.

### Точный код: фильтры

`backend/apps/products/filters.py`, `filter_min_price` — вставить **после** ветки `wholesale_level3` (`:275-276`) и **до** `trainer`:

```python
            elif user_role == "wholesale_level4":
                self._variant_filters &= Q(opt4_price__gte=value) | Q(opt4_price__isnull=True, retail_price__gte=value)
```

`filter_max_price` (`:310-311`) — то же с `__lte`:

```python
            elif user_role == "wholesale_level4":
                self._variant_filters &= Q(opt4_price__lte=value) | Q(opt4_price__isnull=True, retail_price__lte=value)
```

Обе строки — 118 символов при `line-length = 120` (`backend/pyproject.toml`), длина совпадает с существующими строками `opt3`. Не переносить и не переписывать соседние ветки на словарь: правка однострочная, по образцу.

Семантика `Q(opt4_price__isnull=True, retail_price__gte=value)` — это фильтровый аналог бэкендового fallback «пустая цена уровня → сравниваем розничную», согласованный с `get_price_for_user`. Каскада `opt4 → opt3 → …` здесь нет и быть не должно (см. «Каскад фронта против fallback бэка»).

### Точный код: сериализаторы

`backend/apps/products/serializers.py`.

1. Объявление поля (после `:465`):

```python
    opt4_price = serializers.SerializerMethodField()
```

2. `Meta.fields` (после `"opt3_price",`, `:501`):

```python
            "opt4_price",
```

3. Метод (после `get_opt3_price`, `:617`):

```python
    def get_opt4_price(self, obj: Product) -> float:
        """Получить оптовую цену уровня 4 из первого варианта"""
        variant = self._get_first_variant(obj)
        if variant and variant.opt4_price:
            return float(variant.opt4_price)
        return 0.0
```

4. Фильтр в `_get_first_variant` (после `| Q(opt3_price__gt=0)`, `:536`):

```python
                | Q(opt4_price__gt=0)
```

5. `backend/apps/products/pricing_policy.py` — **две** константы, обе с комментарием-подсказкой, оставленным специально под эту стори:

```python
# Сырые оптовые поля ответа каталога. Стори 39.3 добавляет сюда "opt4_price".
WHOLESALE_PRICE_FIELDS = ("opt1_price", "opt2_price", "opt3_price", "opt4_price")

INFO_PRICE_ROLES = frozenset(
    {"wholesale_level1", "wholesale_level2", "wholesale_level3", "wholesale_level4", "trainer", "admin"}
)
```

Комментарии «Стори 39.3 добавляет сюда …» после правки снять — они выполнили роль.

**Почему `opt4_price` обязан попасть в `WHOLESALE_PRICE_FIELDS`.** Константа — единственное место, где перечислены поля, обнуляемые для ролей без права. Поле, добавленное в `Meta.fields` мимо константы, вернётся анонимному запросу с фактическим значением: три предыдущих оптовых поля так и утекали (`tech-debt.md` п. 18). Сторож `backend/tests/integration/test_catalog_price_visibility.py` сформулирован по всем ключам `opt*_price`, поэтому пропуск этой правки **упадёт тестом**, а не уедет на прод молча — но чинить надо константу, а не тест.

**Почему РРЦ/МРЦ доступны уровню 4.** `INFO_PRICE_ROLES` управляет видимостью инфо-цен: их видят оптовики 1-3, тренеры, админы; розница, гости и `federation_rep` — нет. Четвёртый уровень — оптовый (`B2B_ROLES`), и задание (`dev-task-role-from-1c-agreement.md` §B2) прямо относит эту правку к стори. Пропуск даст неотличимый от бага перекос: оптовик уровня 4 в карточке товара не увидит РРЦ, которую видит уровень 3.

**`ProductDetailSerializer` (`:693`) правок не требует** — `class Meta(ProductListSerializer.Meta)` строит `fields` как `ProductListSerializer.Meta.fields + [...]`, а `to_representation` делегирует родителю. Поле и роль подхватятся сами. Не дублировать.

**⚠️ Мина для тестов этой стори: `is_verified`.** После закрытия `tech-debt.md` п. 18 B2B-роль без `is_verified=True` понижается до `retail` — и в ценах, и в фильтрах, и в видимости РРЦ/МРЦ. Любой пользователь `wholesale_level4`, создаваемый в тестах **ради проверки цены или инфо-цен** (AC2, AC4, кейсы `test_wholesale_level4_sees_rrp_and_msrp`, фильтры по `opt4_price`), обязан создаваться с `is_verified=True`, иначе тест проверит розничную ветку и «докажет» отсутствие фичи. Фикстуры `wholesale_user` / `trainer_user` / `admin_user` из `backend/tests/conftest.py` флаг уже ставят. В `test_all_role_price_mappings` (`tests/unit/test_product_filters.py`) пользователь — `Mock()`, у которого любой атрибут truthy, поэтому добавление роли в `roles_to_test` (Task 7.1) работает как есть.

### Точный код: вью каталога

`backend/apps/products/views.py`, `ProductViewSet.get_queryset` (класс объявлен на `:50`), внутри `Prefetch("variants", …)` после `| Q(opt3_price__gt=0)` (`:87`):

```python
                        | Q(opt4_price__gt=0)
```

Это второй из двух обязательных по AC3 экземпляров одного и того же условия. Они **намеренно продублированы** в коде (`Prefetch` для списка + fallback-запрос в сериализаторе для случая без prefetch) — не пытаться вынести в общую константу: это рефакторинг вне объёма стори, затрагивающий горячий путь каталога.

### Точный код: админка

`backend/apps/products/admin.py`, fieldset «Ценообразование» `ProductVariantAdmin` (`:632-646`) — после `"opt3_price",` (`:641`):

```python
                    "opt4_price",
```

`backend/apps/users/admin.py`, `role_display` (`:411-427`) — после строки `wholesale_level3`:

```python
            "wholesale_level4": "#d63384",  # розовый
```

Палитра — Bootstrap 5. Занятые цвета: `#6c757d` серый (retail и дефолт), `#0dcaf0` голубой (l1), `#0d6efd` синий (l2), `#6610f2` фиолетовый (l3), `#198754` зелёный (trainer), `#fd7e14` оранжевый (federation_rep), `#dc3545` красный (admin). `#d63384` (pink) — единственный незанятый цвет базовой палитры, визуально отделим от всех семи. Роль `unregistered` цвета не имеет намеренно (падает в серый дефолт) — не добавлять.

### Точный код: роль в пользовательском API и баннерах

`backend/apps/users/serializers.py`, `SELF_SERVICE_ROLES` (`:85-95`) — после `"wholesale_level3",`:

```python
            "wholesale_level4",
```

Комментарий над списком объясняет, что это именно **белый список** самостоятельно выбираемых ролей, а не запрет отдельных, — сохранить его как есть.

`backend/apps/banners/services.py:138`:

```python
    elif role_key in {"wholesale_level1", "wholesale_level2", "wholesale_level3", "wholesale_level4"}:
```

98 символов — в лимит 120 укладывается, перенос не нужен.

### Точный код: фабрики

`backend/apps/products/factories.py`.

1. `ProductFactory._create`, список `variant_fields` (после `"opt3_price",`, `:95`):

```python
            "opt4_price",
```

2. `ProductVariantFactory` (после `opt3_price`, `:146`):

```python
    # Опт 4 — наименьший объём закупки (до 50 тыс. руб./квартал), поэтому
    # скидка наименьшая: диапазон лежит между розницей и первым уровнем
    opt4_price = fuzzy.FuzzyDecimal(90.0, 9000.0, 2)
```

**Про диапазон — осознанное решение, не опечатка.** Существующие значения убывают по номеру уровня (`retail` 100-10000 → `opt1` 80-8000 → `opt2` 60-6000 → `opt3` 50-5000), и механическое продолжение дало бы уровню 4 самую низкую цену. Это противоречит домену: «Опт 4 (до 50 тыс.руб в квартал)» — тариф для **самого малого** оборота, то есть наименее выгодный из оптовых. Диапазоны в фабрике и так не строго упорядочены (`federation` 45-4500 > `trainer` 40-4000), ни один тест на их относительный порядок не опирается — проверено grep'ом по `backend/tests` и `backend/apps/*/tests`. Комментарий обязателен: без него следующий читатель «поправит» значение обратно.

**Регресс от заполнения `opt4_price` в фабрике — проверено, отсутствует.** Тесты 39.1, зависящие от пустой `opt4_price` (`apps/products/tests/unit/test_price_logic.py:185-199`, `test_wholesale_level4_falls_back_to_retail`), создают вариант напрямую через `ProductVariant.objects.create(...)` и выставляют `variant.opt4_price = None` явно — фабрику они не используют. Тестов, сверяющих точный набор ключей ответа API (`assert set(data.keys()) == {...}`), в проекте нет: `test_serializers.py:63` и `test_blog_api.py:192` используют `in` / `issubset`. Добавление поля в `Meta.fields` их не ломает.

### Дрейф `openapi.yaml` и команда регенерации

Файл генерируется drf-spectacular (`SPECTACULAR_SETTINGS`, `backend/freesport/settings/base.py:375`), не пишется руками. Последний коммит, обновлявший его, — `73992820`; после него сериализаторы правились дважды (`c34d9199`, `ffee94d5`), плюс 39.1 добавила роль в `ROLE_CHOICES`. Поэтому `RoleEnum` (`docs/api/openapi.yaml:4447-4466`) сегодня **не содержит** `wholesale_level4` — это ожидаемая часть diff, а не побочный эффект.

Контейнер бэкенда монтирует только `../backend:/app`; каталога `docs/` внутри нет, писать напрямую в него из контейнера нельзя. Порядок:

```bash
# 1. Сгенерировать во временный файл внутри примонтированного /app (= backend/)
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  python manage.py spectacular --file /app/openapi.generated.yaml

# 2. Заменить контракт и убрать временный файл (из корня репозитория)
mv backend/openapi.generated.yaml docs/api/openapi.yaml

# 3. Оценить diff
git diff --stat docs/api/openapi.yaml
git diff docs/api/openapi.yaml | head -200
```

**Ожидаемый diff:** `opt4_price` в `properties` и `required` схем `ProductList` (`:3957`, `:4055`) и `ProductDetail` (`:4207`, `:4276`), плюс `wholesale_level4` в `enum` и в текстовом описании `RoleEnum`.

⚠️ **Дрейф измерен 2026-08-03 (стори `security-wholesale-price-visibility`, Task 7.1) — он больше, чем предполагалось, и diff будет шумным:**

1. **Закоммиченный файл разошёлся с генерацией целиком**, а не точечно: 4913 строк генерации против 4826 закоммиченных. Ожидать аккуратного diff из двух-трёх ханков не нужно.
2. **Сам генератор недетерминирован.** Два прогона `manage.py spectacular` на *неизменном* коде дают ~275 строк diff: HTTP-методы (`post` / `patch` / `delete`) переставляются местами внутри путей `/users/addresses/`, `/users/favorites/`, `/orders/`, `/cart/items/`. Поэтому **побайтовое сравнение регенерации бессмысленно** — ни с коммитом, ни между прогонами.
3. **Как проверять на самом деле:** сравнивать `components.schemas` и множество пар «путь → метод», а не текст файла. Рабочий приём (им доказан AC9 предыдущей стори):

```python
import yaml
b = yaml.safe_load(open("before.yaml", encoding="utf-8"))
a = yaml.safe_load(open("after.yaml", encoding="utf-8"))
print(b["components"]["schemas"]["ProductList"] == a["components"]["schemas"]["ProductList"])
print({(p, m) for p, ops in b["paths"].items() for m in ops} == {(p, m) for p, ops in a["paths"].items() for m in ops})
```

**Что считать успехом AC10:** в `components.schemas.ProductList` и `.ProductDetail` появились `opt4_price` (в `properties` и `required`), в `RoleEnum` — `wholesale_level4`; множество операций путей не изменилось. Прочий шум в тексте файла — следствие пунктов 1-2, он законен. **Останавливаться и спрашивать Alex** нужно при смене версии OpenAPI, исчезновении путей или массовом переименовании `operationId` — то есть при расхождении по *множеству операций*, а не по порядку строк.

### Мина: тестовые файлы без маркеров

Стори 39.2 нашла и починила случай, когда 13 тестов не попадали ни в `-m unit`, ни в `-m integration` из-за отсутствующего маркера на классе. Мина **не единичная** — среди затрагиваемых сейчас файлов:

| Файл | Состояние |
|---|---|
| `backend/tests/unit/test_product_filters.py` | ✅ `pytestmark = pytest.mark.django_db` + `@pytest.mark.unit` на каждом классе |
| `backend/tests/unit/test_users_admin.py` | ✅ `pytestmark = pytest.mark.unit` на модуле |
| `backend/apps/banners/tests/test_services.py` | ✅ `@pytest.mark.unit` / `@pytest.mark.integration` на классах |
| `backend/tests/unit/test_serializers/test_user_serializers.py` | ⚠️ у классов только `@pytest.mark.django_db` — **нового класса без явного `@pytest.mark.unit` CI не увидит** |
| `backend/apps/products/tests/test_api_products.py` | ⚠️ то же — только `@pytest.mark.django_db` |

Действие дева: на каждом новом классе ставить маркер **явно**, даже если соседние классы его не имеют. Предсуществующие классы **не чинить** — это отдельный долг; если хочешь его закрыть, вынеси в Completion Notes отдельным пунктом на решение Alex, как это сделано в 39.2.

Контроль после написания тестов — убедиться, что новые тесты реально отобрались:

```bash
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q -m unit --collect-only apps/products/tests/unit/test_opt4_catalog_api.py
```

### Структура нового тестового модуля

`backend/apps/products/tests/unit/test_opt4_catalog_api.py` — **новый** файл, шапка:

```python
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory

from apps.products.admin import ProductVariantAdmin
from apps.products.factories import ProductFactory, ProductVariantFactory
from apps.products.serializers import ProductListSerializer
from apps.products.views import ProductViewSet

pytestmark = [pytest.mark.unit, pytest.mark.django_db]
```

Кейсы:

| Тест | AC | Суть |
|---|---|---|
| `test_serializer_exposes_opt4_price` | 2 | `ProductListSerializer(product).data["opt4_price"]` равен значению варианта |
| `test_get_opt4_price_returns_zero_when_empty` | 2 | Пустая `opt4_price` → `0.0` (поведение как у `get_opt3_price`, не `None`) |
| `test_variant_with_only_opt4_price_is_found` | 3 | Вариант, где `retail_price=0` и заполнена **только** `opt4_price`, возвращается `_get_first_variant` |
| `test_catalog_queryset_prefetches_opt4_only_variant` | 3 | Тот же вариант попадает в `first_variant_list` после `ProductViewSet().get_queryset()` |
| `test_wholesale_level4_sees_rrp_and_msrp` | 4 | В ответе для пользователя с ролью уровня 4 есть `rrp` и `msrp` |
| `test_retail_user_still_hides_rrp` | 4 | Сторож обратной стороны: розница по-прежнему `rrp`/`msrp` не видит |
| `test_admin_price_fieldset_contains_opt4` | 5 | `opt4_price` присутствует в fieldset «Ценообразование» `ProductVariantAdmin` |

Вариант «только `opt4_price`» создавать явно, не через дефолты фабрики (она теперь заполняет все цены):

```python
    variant = ProductVariantFactory(
        product=product,
        retail_price=Decimal("0"),
        opt1_price=None,
        opt2_price=None,
        opt3_price=None,
        opt4_price=Decimal("777.00"),
        trainer_price=None,
        federation_price=None,
    )
```

Для ролевых кейсов роль подставляется в `request.user`; образец сборки запроса — `backend/apps/products/tests/test_serializers.py:63-90` (`APIRequestFactory` + `context={"request": request}`).

Тест фильтров (`backend/tests/unit/test_product_filters.py`) проще всего строить на строковом представлении накопленного `Q` — так уже устроен соседний `test_all_role_price_mappings`:

```python
        assert "opt4_price" in str(product_filter._variant_filters)
```

Уникальные строковые данные (SKU, slug, `onec_id`) — через `get_unique_suffix()` из `backend/tests/conftest.py`. Автоиспользуемая фикстура `clear_db_before_test` (`conftest.py:671`) делает тесты в `backend/tests/` транзакционными с последующим flush — на данные из data-миграций не рассчитывать.

### Каскад фронта против fallback бэка

На бэкенде пустая цена уровня даёт **сразу `retail_price`** — и в `get_price_for_user`, и в фильтрах. На фронте в `ProductCard` живёт каскад `opt4 → opt3 → opt2 → opt1 → retail`. Расхождение существует для уровней 1-3, зафиксировано в epics.md (стори 39.4) и **в этой стори не чинится**. Не «выравнивать» фильтры под каскад — это изменило бы выдачу для всех оптовых ролей сразу.

### Релизное правило эпика

Стори эпика 39 **на прод по одной не выкатываются** (решение Alex, 2026-08-02): релиз собирается после 39.1 → 39.2 → 39.3 → 39.4 целиком. Эта стори закрывает второй из двух промежуточных дефектов релизной ветки (регистрация с ролью уровня 4 → 400, AC7). После неё в ветке остаётся единственное расхождение: `openapi.yaml` уже содержит `opt4_price`, а `frontend/src/types/api.generated.ts` — ещё нет. Оно снимается стори 39.4 и на работоспособность бэкенда не влияет.

### Команды

```bash
# Точечный прогон нового теста
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/unit/test_opt4_catalog_api.py

# Эквивалент make test-unit (make в оболочке недоступен, таргеты ищут несуществующий docker/.env)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m unit
# Эквивалент make test-integration (≈30 мин — запускать в фоне)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m integration
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down

# Линтеры — в dev-контейнере, из корня репозитория
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  flake8 apps/products/filters.py apps/products/serializers.py apps/products/views.py \
         apps/products/admin.py apps/products/factories.py \
         apps/users/serializers.py apps/users/admin.py apps/banners/services.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black --check apps/products/filters.py apps/products/serializers.py apps/products/views.py \
                apps/products/admin.py apps/products/factories.py \
                apps/users/serializers.py apps/users/admin.py apps/banners/services.py
```

Известный предсуществующий долг `black`: `apps/products/tests/unit/test_variant_import_migrated.py` (строки 521+, 549+, 646+). Не исправлять — к объёму стори не относится.

Ориентиры длительности: unit ≈ 7 мин, integration ≈ 30 мин. PostgreSQL обязателен, SQLite не поддерживается. Миграций стори не вводит — `makemigrations --check` должен остаться чистым.

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** трогать `frontend/` и **не** запускать `npm run generate:types` — это стори **39.4**.
- **НЕ** трогать `products/models.py`, миграции, `ONEC_EXCHANGE` — сделано в **39.1**.
- **НЕ** трогать `products/services/parser.py` и `variant_import.py` — сделано в **39.2**.
- **НЕ** заполнять `PriceType.user_role` у остальных записей справочника и **не** регистрировать `PriceType` в админке — это стори **40.2**.
- **НЕ** рефакторить списки ролей к единому предикату/константе **на фронте** — сознательно принятый долг эпика (`tech-debt.md` п. 17), рефакторинг в объём **не входит**. На бэкенде такой предикат уже есть (`apps/products/pricing_policy.py`) — им и пользоваться, литеральных списков ролей не заводить.
- **НЕ** выносить дублирующееся условие `Q(retail_price__gt=0) | …` в общую константу — горячий путь каталога, рефакторинг вне объёма.
- **НЕ** править `ProductDetailSerializer` — наследует `Meta.fields`.
- **НЕ** добавлять `opt4_price` в `ProductVariantSerializer.Meta.fields`: этот сериализатор сырых ценовых полей не отдаёт вовсе, только `current_price`. Его `to_representation` гейтит лишь `rrp`/`msrp`, поэтому добавленное поле утекло бы всем ролям, включая гостей.
- **НЕ** ставить проверку прав внутрь `get_opt4_price` — гейт живёт в одном месте (`to_representation` + `WHOLESALE_PRICE_FIELDS`); дублирование в методе разведёт источники истины.
- **НЕ** добавлять `opt4_price` в `list_display`/`ProductVariantInline` админки — там нет ни одной оптовой цены.
- **НЕ** менять сортировку каталога и аннотацию `min_retail_price` — она осталась розничной осознанно.
- **НЕ** чинить маркеры у предсуществующих тест-классов без отдельного решения Alex.
- **НЕ** править `openapi.yaml` руками — только регенерация.

### Project Structure Notes

- Комментарии и docstrings нового кода — на русском (NFR-3940-10, `project-context.md` §6).
- Типизация — как в окружающем коде: `-> float` на `get_*_price`, `cast()` там, где он уже используется.
- Покрытие: `products` и `users` — критические модули, ≥ 90 %; общее ≥ 70 % (NFR-3940-03).
- Django 5.2.7, Python 3.14, DRF + drf-spectacular 0.28.0. Новых зависимостей стори не вводит.
- Backend в Docker слушает `8001` снаружи / `8000` внутри; тестовый профиль — `docker-compose.test.yml`, проект `freesport-test`.
- `black`/`flake8`: `line-length = 120` (`backend/pyproject.toml`, `backend/setup.cfg`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 39.3: Каталог, админка и API отдают цену уровня 4 — AC в BDD-формате]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 39 — порядок стори, атомарность выката, сознательно принятый долг]
- [Source: _bmad-output/planning-artifacts/epics.md#Requirements Inventory — FR-39-06 … FR-39-10, FR-39-13, NFR-3940-02, -03, -07, -10]
- [Source: _bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md#B2 Прикладной код — полный список файлов и строк]
- [Source: _bmad-output/implementation-artifacts/Story/39-2-import-opt4-prices-from-1c.md#Релизное правило эпика — дефект SELF_SERVICE_ROLES передан в 39.3]
- [Source: _bmad-output/implementation-artifacts/Story/39-2-import-opt4-prices-from-1c.md#Мина: маркеры тестов и базовые линии прогонов]
- [Source: backend/apps/products/filters.py:267-286, :301-319 — filter_min_price / filter_max_price, ветки по ролям через resolve_pricing_role]
- [Source: backend/apps/products/pricing_policy.py — WHOLESALE_PRICE_FIELDS, INFO_PRICE_ROLES, предикаты видимости цен]
- [Source: backend/apps/products/serializers.py:94-105 — ProductVariantSerializer.to_representation через can_see_info_prices]
- [Source: backend/apps/products/serializers.py:461-510 — объявления полей и Meta.fields ProductListSerializer]
- [Source: backend/apps/products/serializers.py:520-542 — _get_first_variant, фильтр наличия цены]
- [Source: backend/apps/products/serializers.py:562-581 — to_representation, скрытие rrp/msrp и обнуление оптовых полей]
- [Source: backend/apps/products/serializers.py:598-617 — get_opt1/2/3_price, образец для get_opt4_price]
- [Source: backend/apps/products/serializers.py:693-715 — ProductDetailSerializer наследует Meta.fields]
- [Source: backend/apps/products/views.py:81-93 — Prefetch first_variant_list]
- [Source: backend/apps/products/admin.py:632-646 — fieldset «Ценообразование» ProductVariantAdmin]
- [Source: backend/apps/products/factories.py:91-103, :140-147 — variant_fields и ценовые поля фабрики]
- [Source: backend/apps/users/serializers.py:85-100 — SELF_SERVICE_ROLES и validate_role]
- [Source: backend/apps/users/admin.py:411-427 — role_display, палитра бейджей]
- [Source: backend/apps/users/views/misc.py:41-53 — user_roles_view строит список из ROLE_CHOICES]
- [Source: backend/apps/users/models.py:153-186, :387-404 — ROLE_CHOICES, B2B_ROLES, is_wholesale_user, wholesale_level]
- [Source: backend/apps/banners/services.py:30-33, :116-144 — _ALL_ROLE_KEYS и _get_role_filter]
- [Source: backend/apps/products/models.py:912-923, :1188-1206 — opt4_price и get_price_for_user через resolve_pricing_role]
- [Source: backend/tests/integration/test_catalog_price_visibility.py — сторож утечки по всем ключам opt*_price]
- [Source: backend/apps/products/tests/unit/test_price_logic.py:167-199 — тесты 39.1, зависящие от пустой opt4_price]
- [Source: backend/tests/unit/test_product_filters.py:304-340 — test_all_role_price_mappings, образец]
- [Source: backend/tests/unit/test_users_admin.py:20, :152-160 — pytestmark unit, тест role_display]
- [Source: backend/apps/banners/tests/test_services.py:37, :186-199 — маркеры и тесты ролей]
- [Source: backend/apps/products/tests/test_serializers.py:63-90 — образец сборки request-контекста]
- [Source: docs/api/openapi.yaml:3957, :4055, :4207, :4276, :4447-4466 — точки правки контракта]
- [Source: backend/freesport/settings/base.py:375-401 — SPECTACULAR_SETTINGS]
- [Source: docker/docker-compose.yml:79-84 — бэкенд монтирует только ../backend, docs/ вне контейнера]
- [Source: backend/pyproject.toml, backend/setup.cfg — black/flake8 line-length 120]
- [Source: project-context.md §3, §4, §5, §6 — role-based pricing, тестирование, GitNexus-дисциплина, язык кода]

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, workflow `bmad-dev-story`)

### Debug Log References

| Проверка | Команда | Результат |
|---|---|---|
| RED-прогон новых тестов | `pytest -q apps/products/tests/unit/test_opt4_catalog_api.py tests/unit/test_product_filters.py::TestOpt4PriceFilter` | 9 failed, 4 passed — падения ровно в ожидаемых точках (AC1-AC5) |
| GREEN-прогон затронутых файлов | тот же набор + `tests/unit/test_users_admin.py`, `tests/unit/test_serializers/test_user_serializers.py`, `apps/banners/tests/test_services.py` | 161 passed |
| Маркеры новых тестов (Task 7.6) | `pytest -q -m unit --collect-only <новые классы>` | 21 tests collected — все новые тесты попадают в `-m unit` |
| Полный unit (Task 9.1) | `pytest -q -m unit` | итог: **1851 passed, 4 skipped, 949 deselected** (первый прогон дал 1 failed — см. ниже) |
| Полный integration (Task 9.2) | `pytest -q -m integration` | **920 passed, 2 skipped, 1882 deselected, 15 subtests passed** (28:29) |
| `flake8` (Task 9.3) | 14 изменённых файлов | exit 0 |
| `black --check` (Task 9.3) | те же 14 файлов | 14 files would be left unchanged |
| `makemigrations --check` | dev-контейнер | `No changes detected` — стори миграций не вводит |
| Сверка контракта (AC10) | `manage.py check_openapi_sync --schema-file …` | `Контракт синхронен с кодом` |
| GitNexus (Task 9.4) | `npx gitnexus detect-changes --scope all` | 16 files, 23 symbols, affected processes 0, **risk low** |

Единственное падение полного unit-прогона — `apps/products/tests/unit/test_pricing_policy.py::TestResolvePricingRole::test_field_constants`: сторож предыдущей стори сверял `WHOLESALE_PRICE_FIELDS` с точным кортежем из трёх полей. Константа расширена по Task 2.5, ожидание в тесте обновлено вместе с комментарием, зачем поле там обязано быть.

### Completion Notes List

**Реализовано по ACs**

- **AC1** — ветка `wholesale_level4` добавлена в `filter_min_price` и `filter_max_price` между `wholesale_level3` и `trainer`. Роль берётся из `resolve_pricing_role`, поэтому неверифицированный уровень 4 штатно уходит в розничную ветку (закреплено тестом `test_unverified_level4_filters_by_retail_price`).
- **AC2** — `opt4_price` объявлено `SerializerMethodField`, включено в `Meta.fields`, реализован `get_opt4_price` по образцу `get_opt3_price` (пустая цена → `0.0`, не `None`). `ProductDetailSerializer` не правился — наследует `Meta.fields`.
- **AC3** — `| Q(opt4_price__gt=0)` добавлено в **оба** обязательных места: `ProductListSerializer._get_first_variant` и `Prefetch("variants", …)` в `ProductViewSet.get_queryset`. Оба покрыты отдельными тестами, чтобы пропуск одного не дал молчаливого расхождения «список против карточки».
- **AC4** — в `pricing_policy.py` внесены обе правки: `"opt4_price"` в `WHOLESALE_PRICE_FIELDS` (гейт нового поля) и `"wholesale_level4"` в `INFO_PRICE_ROLES` (РРЦ/МРЦ). Комментарии-подсказки «Стори 39.3 добавляет сюда …» сняты. Утечка нового поля анониму закрыта тестом `test_anonymous_does_not_see_opt4_price`.
- **AC5** — `opt4_price` в fieldset «Ценообразование» `ProductVariantAdmin`, сразу после `opt3_price`. `list_display` и `ProductVariantInline` не тронуты; добавлен сторож `test_admin_list_display_has_no_wholesale_prices`.
- **AC6** — `"wholesale_level4": "#d63384"` в `role_colors`. Уникальность цвета среди всех ролей закреплена тестом (роли, намеренно падающие в серый дефолт — `retail`, `unregistered` — из сравнения исключены).
- **AC7** — `"wholesale_level4"` в `SELF_SERVICE_ROLES`. Промежуточный дефект релизной ветки (роль публикуется в `/api/v1/users/roles/`, но регистрация отдаёт 400) закрыт.
- **AC8** — роль добавлена в множество оптовых в `_get_role_filter`; фильтр совпадает с фильтром уровня 3, гостевой fallback больше не срабатывает.
- **AC9** — `"opt4_price"` в `variant_fields` метода `ProductFactory._create` и `opt4_price = fuzzy.FuzzyDecimal(90.0, 9000.0, 2)` в `ProductVariantFactory` с комментарием об обосновании диапазона.
- **AC10** — `docs/api/openapi.yaml` перегенерирован. Семантическая сверка (структурная, не побайтовая): `opt4_price` появилось в `properties` и `required` схем `ProductList` и `ProductDetail`; множество пар «путь → метод» не изменилось; версия OpenAPI (3.1.0) та же; схем не добавлено и не удалено; изменились ровно две схемы — `ProductList` и `ProductDetail`.
- **AC11** — новые тесты покрывают AC1-AC8; каждый новый класс несёт явный `@pytest.mark.unit`, проверено через `--collect-only -m unit`.

**Расхождения со спекой стори (обнаружены по факту, не дефекты реализации)**

1. **`RoleEnum` уже содержал `wholesale_level4`.** Dev Notes ожидали его появления в diff и описывали дрейф `openapi.yaml` в ~4900 строк. К моменту разработки контракт уже был приведён в соответствие с кодом коммитом `4708dd8a` (тех.долг п. 20), поэтому фактический diff — 154/141 строк, а роль в `RoleEnum` присутствовала до правки. AC10 в части `RoleEnum` выполнен состоянием файла, в части схем товара — этой стори.
2. **Базовые линии прогонов в Task 9.1/9.2 устарели.** Спека называла 1041 passed (unit) и 744 passed (integration); фактические цифры до и после правки — порядка 1851 и 920. Разница не связана со стори: между написанием спеки и разработкой были закрыты тех.долг п. 18 и п. 20 с новыми тестами. Регресс проверялся по составу падений, а не по абсолютному числу.

**⚠️ Требует решения Alex (за рамками объёма стори)**

- **Гейт `api-contract.yml` на этой ветке будет красным.** Workflow `.github/workflows/api-contract.yml` (появился в тех.долге п. 20, коммит `898d971e`, то есть **после** написания спеки 39.3) сверяет два артефакта: `docs/api/openapi.yaml` против кода (шаг `check_openapi_sync` — сейчас **проходит**) и `frontend/src/types/api.generated.ts` против закоммиченного YAML (шаг `npm run generate:types` + `git status --porcelain` — сейчас **упадёт**, т.к. контракт содержит `opt4_price`, а сгенерированные типы — ещё нет). Task 8.4 стори прямо запрещает трогать `frontend/`, регенерация типов — AC1 стори 39.4, поэтому правка сюда не вносилась. Варианты: (а) оставить как есть — гейт станет зелёным после влития 39.4, что согласуется с релизным правилом эпика («стори 39 на прод по одной не выкатываются»); (б) выполнить `cd frontend && npm run generate:types` уже здесь, приняв выход за объём стори. Нужно решение.
- **Предсуществующий долг маркеров не чинился** (в соответствии с антипаттернами стори): у классов в `backend/tests/unit/test_serializers/test_user_serializers.py` и `backend/apps/products/tests/test_api_products.py` стоит только `@pytest.mark.django_db`. Новые классы маркер получили явно.

### File List

**Изменённые — код**

- `backend/apps/products/filters.py`
- `backend/apps/products/serializers.py`
- `backend/apps/products/views.py`
- `backend/apps/products/admin.py`
- `backend/apps/products/factories.py`
- `backend/apps/products/pricing_policy.py`
- `backend/apps/users/serializers.py`
- `backend/apps/users/admin.py`
- `backend/apps/banners/services.py`

**Новые — тесты**

- `backend/apps/products/tests/unit/test_opt4_catalog_api.py`

**Изменённые — тесты**

- `backend/apps/products/tests/unit/test_pricing_policy.py`
- `backend/tests/unit/test_product_filters.py`
- `backend/tests/unit/test_serializers/test_user_serializers.py`
- `backend/tests/unit/test_users_admin.py`
- `backend/apps/banners/tests/test_services.py`

**Изменённые — контракт и артефакты процесса**

- `docs/api/openapi.yaml` (перегенерирован)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/39-3-catalog-admin-api-opt4-price.md`

## Change Log

| Дата | Изменение |
|---|---|
| 2026-08-04 | Реализована стори 39.3: цена уровня 4 в фильтрах каталога, ответе API, политике видимости цен, админке варианта и бейдже роли; роль `wholesale_level4` разрешена при регистрации и отнесена к оптовым в баннерах; фабрики заполняют `opt4_price`; `docs/api/openapi.yaml` перегенерирован. Добавлен модуль `test_opt4_catalog_api.py` (10 тестов) и 11 тестов в четыре существующих файла. Статус → review. |
