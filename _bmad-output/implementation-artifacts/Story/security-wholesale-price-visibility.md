---
baseline_commit: 61dfeb88aa8855360e310526331c6411cf2a19b3
---

# Story: Security — Оптовые цены видны только верифицированному B2B

**Story ID:** security-wholesale-price-visibility
**Status:** review
**Priority:** 🔴 High — блокирует стори 39.3 (решение Alex, 2026-08-03)
**Source:** `_bmad-output/planning-artifacts/tech-debt.md` п. 18 · `_bmad-output/planning-artifacts/epics.md` → Epic 39 → «Предшествующая работа»
**Порядок:** выполняется **до** стори `39-3-catalog-admin-api-opt4-price`. Эпика не имеет — правка про политику цен в целом, а не про «Опт 4».

---

## Story

Как **владелец коммерческой политики FREESPORT**,
я хочу **чтобы оптовая ценовая сетка уходила из API только верифицированным B2B-пользователям**,
чтобы **конкурент не снимал её без аутентификации, а неверифицированный B2B не покупал по оптовой цене до проверки менеджером**.

---

## Контекст: что именно сломано

Доменный инвариант `project-context.md` §3 записан, но **не реализован ни одной из двух половин**:

> «Оптовые цены (`opt1/2/3_price`) и B2B-функции доступны **только верифицированным** пользователям с ролью wholesale/trainer/federation_rep. Неверифицированный B2B видит retail-цены.»

| Половина инварианта | Фактическое состояние на `61dfeb88` |
|---|---|
| Оптовые цены — только B2B | `ProductViewSet.permission_classes = [AllowAny]` (`views.py:55`), `ProductListSerializer.Meta.fields` (`serializers.py:511-514`) безусловно отдаёт `retail_price`, `opt1_price`, `opt2_price`, `opt3_price`. `to_representation` (`:575-597`) вырезает **только** `rrp`/`msrp`. Анонимный `GET /api/v1/products/?page_size=100` снимает всю сетку. |
| Неверифицированный B2B → retail | `get_price_for_user` (`models.py:1188-1203`) строит `role_price_mapping` **только по `user.role`**; `is_verified` не читается нигде в `apps/products/` (`grep -rn "is_verified" apps/products/` → пусто). |

Вторая половина утекает дальше каталога: `get_price_for_user` вызывается из `cart/models.py:154` (`CartItem.price_snapshot`) и `cart/views.py:142`, а `orders/services/order_create.py:138` берёт `unit_price = ci.price_snapshot`. То есть **неверифицированный оптовик сегодня и покупает по оптовой цене**.

## Принятые решения (не пересматривать при реализации)

| # | Решение | Кем/когда |
|---|---|---|
| 1 | **Вариант B — отдавать `0.0`,** а не удалять поле из ответа. Поля остаются в `Meta.fields` и в `required` схемы OpenAPI. Обоснование: `get_opt1/2/3_price` **уже** возвращают `0.0` при пустой цене, а на проде `opt1_price` пуст у 52 %, `opt2/opt3` — у 54 % вариантов; ноль давно штатный ответ «цены нет», фронт его переваривает. Ноль правок `openapi.yaml`, ноль правок типов фронта, ноль ломающих изменений. Вариант A (`data.pop` по образцу `rrp`/`msrp`) **отклонён** — требует вынуть поля из `required` и тиражирует уже существующий разрыв контракта с ответом. | Alex, 2026-08-03 |
| 2 | **Обязателен тест-сторож + комментарий в коде:** «нет права» и «цены нет» становятся неразличимы, поэтому в AC входит проверка «анонимный и розничный `GET /api/v1/products/` не содержит ни одного `opt*_price > 0`», а рядом с гейтом стоит комментарий, что `0.0` здесь означает «роль не имеет права», а не «данные не заполнены». Без сторожа гейт снимут обратно как «непонятный». | Sally, принято 2026-08-03 |
| 3 | **Закрываются обе половины инварианта**, включая проверку верификации в `get_price_for_user` — то есть правка достаёт до корзины и заказа. Это и есть коммерческий смысл инварианта. | Alex, 2026-08-03 (сессия 4) |
| 4 | **Верифицированный B2B видит всю оптовую сетку**, а не только своё поле. `wholesale_level2` получает `opt1_price`, `opt3_price` и т. д. как сейчас. Каскад `ProductCard` (`opt3 → opt2 → opt1 → retail`) продолжает работать без правок фронта. Вариант «только свой уровень» отклонён — он менял бы поведение для уже работающих B2B-клиентов. | Alex, 2026-08-03 (сессия 4) |
| 5 | **Стори вне эпика**, имя по образцу `security-*`. Выполняется до 39.3, чтобы `opt4_price` попал в `openapi.yaml` уже с гейтом: одна регенерация контракта и типов фронта вместо двух. | Alex, 2026-08-03 |

### Замер прода (2026-08-03, БД `freesport` на `5.35.124.149`) — риск нулевой

```
 role             | is_verified | created_in_1c | count
 unregistered     | f           | t             |  4606   ← записи 1С, роль не B2B, цены и так retail
 retail           | t           | f             |     5
 wholesale_level1 | f           | f             |     4   ← ЕДИНСТВЕННЫЕ затронутые
 admin            | t           | f             |     3
 wholesale_level2 | t           | f             |     1
 wholesale_level1 | t           | f             |     1
 trainer          | t           | f             |     1
```

Все четыре неверифицированных оптовика (`leonenko70@mail.ru`, `info@masai.ru`, `zakupki@kitezh73.ru`, `bul75@mail.ru`) — `is_active = false`, `verification_status = pending`, **0 заказов**: это необработанные заявки, войти на портал они не могут. Единственный активный оптовик с заказами (`alex.dobrodelo@gmail.com`, 4 заказа) — `is_verified = true`, его цены не меняются. **Ни один живой клиент не теряет оптовую цену.** Все три `admin` — `is_verified = true`.

---

## Acceptance Criteria

1. **AC1. Единый модуль политики.** Появляется `backend/apps/products/pricing_policy.py` — единственный источник истины по видимости цен: `resolve_pricing_role(user) -> str`, `can_see_wholesale_prices(user) -> bool`, `can_see_info_prices(user) -> bool`, константы `WHOLESALE_PRICE_FIELDS` и `INFO_PRICE_FIELDS`. Дублирующиеся литеральные списки `allowed_roles` из `ProductVariantSerializer.to_representation` (`serializers.py:106-112`) и `ProductListSerializer.to_representation` (`:587-593`) удаляются и выражаются через `can_see_info_prices`.

2. **AC2. Гейт сырых оптовых полей.** В ответе `ProductListSerializer` и `ProductDetailSerializer` поля `opt1_price`, `opt2_price`, `opt3_price` равны `0.0` для: анонима, `retail`, `unregistered`, **любой B2B-роли с `is_verified = False`**. Поля остаются в ответе — ключи не удаляются, `required` в OpenAPI не трогается. Гейт действует и во вложенном списке `related_products` (`serializers.py:811` создаёт `ProductListSerializer` с тем же `context`).

3. **AC3. Верифицированный B2B и admin видят сетку целиком.** Для `is_verified = True` с ролью из `User.B2B_ROLES` (`wholesale_level1…4`, `trainer`, `federation_rep`) и для роли `admin` все три поля возвращают фактические значения — поведение не меняется относительно `61dfeb88`.

4. **AC4. Вторая половина инварианта: `get_price_for_user`.** `ProductVariant.get_price_for_user` (`models.py:1188-1203`) разрешает роль через `resolve_pricing_role`, поэтому B2B-роль без `is_verified` получает `retail_price`. Следствия покрыты тестами: `current_price` в каталоге, `CartItem.price_snapshot` при добавлении в корзину (`cart/models.py:154`, `cart/views.py:142`) и, через него, `unit_price` заказа (`orders/services/order_create.py:138`).

5. **AC5. Фильтры каталога согласованы с политикой.** `ProductFilter.filter_min_price` (`filters.py:248-288`) и `filter_max_price` (`:290-323`) ветвятся по `resolve_pricing_role(...)`, а не по сырому `request.user.role`. Неверифицированный оптовик фильтруется по `retail_price` — то есть по той цене, которую ему показывают. Без этого фильтр «до 1000 ₽» вернёт товары по оптовой цене, а в карточках будет розничная.

6. **AC6. Инфо-цены РРЦ/МРЦ тоже требуют верификации.** `can_see_info_prices` сохраняет существующий белый список ролей (`wholesale_level1/2/3`, `trainer`, `admin`; `federation_rep` — намеренно **не** входит) и дополнительно требует `is_verified` для B2B-ролей. Неверифицированный оптовик не видит ни оптовых, ни инфо-цен — иначе гейт получается дырявым по соседнему полю.

7. **AC7. Тест-сторож утечки (обязателен, решение Sally).** Интеграционный тест: анонимный `GET /api/v1/products/` и `GET /api/v1/products/{slug}/` не содержат **ни одного** `opt*_price > 0` при заполненных ценах в БД; то же для аутентифицированного `retail` и для B2B с `is_verified = False`. Сторож формулируется по всем `opt*`-ключам ответа (не перечислением трёх имён), чтобы `opt4_price` из 39.3 попал под него автоматически.

8. **AC8. Комментарии, объясняющие `0.0`.** Рядом с гейтом в `to_representation` и в docstring `can_see_wholesale_prices` — комментарий на русском: `0.0` означает «роль не имеет права видеть оптовую цену», а не «цена не заполнена»; удаление гейта откроет всю сетку анонимам (`tech-debt.md` п. 18).

9. **AC9. Контракт API не меняется.** `docs/api/openapi.yaml` после регенерации идентичен закоммиченному (`git diff --exit-code docs/api/openapi.yaml` чист). Это проверка выбора варианта B: если diff непустой — реализация ушла в вариант A и её надо вернуть. Типы фронта (`frontend/`) не трогаются.

10. **AC10. Существующие тесты приведены в соответствие, а не подогнаны.** В тестах, проверяющих оптовую цену, B2B-пользователь создаётся с `is_verified=True` (список файлов — в Dev Notes). Ни один тест не «чинится» ослаблением ассерта или снятием гейта.

11. **AC11. Новые тесты.** Покрыты: предикаты `pricing_policy` по всем ролям × `is_verified`; гейт полей в списке, детали и `related_products`; `get_price_for_user` для неверифицированного B2B; цена корзины для неверифицированного B2B; роль в фильтрах; РРЦ/МРЦ для неверифицированного B2B. Каждый новый класс несёт **явный** `@pytest.mark.unit` или `@pytest.mark.integration` (см. «Мина: тестовые файлы без маркеров»).

12. **AC12. Кросс-документные хвосты закрыты.** (а) В `39-3-catalog-admin-api-opt4-price.md` освежены `baseline_commit` и номера строк Dev Notes, а в его Task 2 добавлен пункт «включить `opt4_price` в `WHOLESALE_PRICE_FIELDS`» вместо правки удалённых списков `allowed_roles`; предупреждение в шапке 39.3 о невалидных координатах снято. (б) В `tech-debt.md` п. 18 помечен закрытым со ссылкой на эту стори.

---

## Tasks / Subtasks

- [x] **Task 1: Модуль политики цен** (AC: 1, 8)
  - [x] 1.1: Создать `backend/apps/products/pricing_policy.py` — точный код в Dev Notes → «Точный код: pricing_policy.py»
  - [x] 1.2: `WHOLESALE_PRICE_FIELDS = ("opt1_price", "opt2_price", "opt3_price")` с комментарием «стори 39.3 добавляет сюда `opt4_price`»
  - [x] 1.3: Импорт `User` — **ленивый, внутри функции** (`from apps.users.models import User`), иначе цикл `products.models → pricing_policy → users.models`

- [x] **Task 2: Гейт в сериализаторах** (AC: 1, 2, 3, 6, 8)
  - [x] 2.1: `serializers.py:93-117` — `ProductVariantSerializer.to_representation`: литеральный `allowed_roles` заменить на `can_see_info_prices(user)`
  - [x] 2.2: `serializers.py:575-597` — `ProductListSerializer.to_representation`: то же для `rrp`/`msrp` + обнуление `WHOLESALE_PRICE_FIELDS` при `not can_see_wholesale_prices(user)`
  - [x] 2.3: Комментарий про смысл `0.0` рядом с обнулением
  - [x] 2.4: `ProductDetailSerializer` (`:709`, `:732-734`) **не править** — делегирует `super().to_representation`
  - [x] 2.5: `serializers_variant.py` **не править** — сырых ценовых полей не отдаёт, `current_price` гейтится через Task 3

- [x] **Task 3: Верификация в `get_price_for_user`** (AC: 4)
  - [x] 3.1: `products/models.py:1188-1203` — роль через `resolve_pricing_role(user)`; ранняя ветка «аноним → retail» убирается как поглощённая
  - [x] 3.2: `cart/`, `orders/` **не править** — они получают гейт транзитом через `price_snapshot`

- [x] **Task 4: Фильтры каталога** (AC: 5)
  - [x] 4.1: `filters.py:248-288` — `filter_min_price` на `resolve_pricing_role`
  - [x] 4.2: `filters.py:290-323` — `filter_max_price` на `resolve_pricing_role`
  - [x] 4.3: Ветку `if not request or not request.user.is_authenticated` убрать — `resolve_pricing_role(None)` даёт `retail`; поведение эквивалентно
  - [x] 4.4: `_variant_filters`, `qs`-property и subquery-оптимизацию **не трогать**

- [x] **Task 5: Обновление существующих тестов** (AC: 10)
  - [x] 5.1: `apps/products/tests/test_product_variant_models.py:105-145` — 5 тестов ролевой цены: добавить `is_verified=True` в `create_user`
  - [x] 5.2: `apps/products/tests/unit/test_price_logic.py:121, :177, :190` — `federation_rep` и два теста «Опт 4»: `is_verified=True`
  - [x] 5.3: `apps/products/tests/test_serializers.py:45, :229, :249` — `is_verified=True`
  - [x] 5.4: `apps/products/tests/test_api_products.py:46` — `is_verified=True` (тест ждёт `current_price == opt1_price` на `:147-150`)
  - [x] 5.5: `tests/integration/base.py:110, :125` — базовый класс интеграционных тестов
  - [x] 5.6: `tests/integration/test_b2b_workflow.py:24` (ассерт `opt1_price == 800` на `:65`), `test_pricing_integration.py:27-37` (ассерт на `:195`), `test_orders_api.py:465`, `test_personal_cabinet_workflow.py:29, :171`, `test_link_then_import_1c.py:77`
  - [x] 5.7: `tests/integration/test_catalog_api.py` — уже ставит `is_verified = True` (`:146`), проверить остальные кейсы файла
  - [x] 5.8: **Не трогать** тесты, где B2B-роль создаётся не ради цены: `test_banners_api.py`, `apps/banners/tests/test_views.py`, `test_portal_registration_1c_link.py`, `test_variant_import_migrated.py`

- [x] **Task 6: Новые тесты** (AC: 7, 11)
  - [x] 6.1: **Новый** `backend/apps/products/tests/unit/test_pricing_policy.py` — предикаты, `pytestmark = [pytest.mark.unit, pytest.mark.django_db]`
  - [x] 6.2: **Новый** `backend/tests/integration/test_catalog_price_visibility.py` — сторож AC7, `pytestmark = pytest.mark.integration`
  - [x] 6.3: В `test_pricing_policy.py` — кейсы `get_price_for_user` для неверифицированного B2B и `related_products`
  - [x] 6.4: Корзина: тест «неверифицированный `wholesale_level1` кладёт товар → `price_snapshot == retail_price`» (`tests/integration/`, рядом с `test_user_cart_integration.py`)
  - [x] 6.5: `tests/unit/test_product_filters.py` — новый класс с `@pytest.mark.unit`: неверифицированный оптовик фильтруется по `retail_price`. **Mock-ловушка:** в `test_all_role_price_mappings` (`:304`) пользователь — `Mock()`, у которого `is_verified` truthy по умолчанию; в новом тесте задавать `mock_user.is_verified = False` **явно**
  - [x] 6.6: Проверить отбор новых тестов по маркерам (команда — в Dev Notes)

- [x] **Task 7: Контракт и прогон** (AC: 9, 11)
  - [x] 7.1: Регенерировать `openapi.yaml` (команда — в Dev Notes) и убедиться, что `git diff --exit-code docs/api/openapi.yaml` чист; временный файл удалить
  - [x] 7.2: Полный unit-прогон. Базовая линия до правок: **1041 passed, 1 skipped**
  - [x] 7.3: Полный integration-прогон (≈ 30 мин, в фоне). Базовая линия: **744 passed, 2 skipped**
  - [x] 7.4: `black --check` + `flake8` по изменённым файлам
  - [x] 7.5: `npx gitnexus detect-changes --scope all` перед коммитом

- [x] **Task 8: Кросс-документные хвосты** (AC: 12) — **последним, после зелёных тестов**
  - [x] 8.1: `Story/39-3-catalog-admin-api-opt4-price.md`: обновить `baseline_commit` на коммит этой стори; сверить и освежить номера строк `serializers.py:109`, `:478`, `:514`, `:549`, `:590`, `views.py:87`
  - [x] 8.2: Там же: Task 2.5 переформулировать — вместо «добавить `wholesale_level4` в два списка `allowed_roles`» указать «добавить `"opt4_price"` в `WHOLESALE_PRICE_FIELDS` и `wholesale_level4` в белый список ролей `can_see_info_prices` (`apps/products/pricing_policy.py`)»; AC4 стори 39.3 привести к тому же
  - [x] 8.3: Там же: снять предупреждение в шапке о невалидных координатах (оно адресовало именно эту стори)
  - [x] 8.4: `_bmad-output/planning-artifacts/tech-debt.md` п. 18 — пометить закрытым: дата, ссылка `Story/security-wholesale-price-visibility.md`, фактическая форма исправления

### Review Findings

- [x] [Review][Patch] Существующие тесты ролевого ценообразования не обновлены для B2B-верификации [backend/tests/unit/test_models/test_product_models.py:185] — AC10 нарушен: тесты создают `wholesale_level1…3`, `trainer` и `federation_rep` через `UserFactory` с `is_verified=False` по умолчанию, но ожидают оптовые цены. Аналогичные неверные ожидания остаются в `backend/tests/unit/test_models/test_order_models.py:285` и `backend/tests/integration/test_product_detail_api.py:53`. Нужно установить `is_verified=True` только в фикстурах, проверяющих оптовую цену или RRP/MSRP, не ослабляя ассерты.
  - **Закрыто 2026-08-03.** Находка подтверждена прогоном (4 падения по трём названным файлам). Исправлено добавлением `is_verified=True` в 4 фикстуры/теста, ассерты не ослаблялись. Сверх находки полным прогоном без фильтра по маркерам найден **пятый** случай — `tests/integration/test_user_cart_integration.py:23` (`test_role_based_pricing_in_cart`, `AssertionError: 100.0 not less than 100.0`), тоже исправлен. Корневая причина промаха разобрана ниже («Корневая причина: 852 теста вне CI-фильтров»).

---

## Dev Notes

### Blast radius (GitNexus pre-flight выполнен)

| Символ | Risk | Прямых вызывающих |
|---|---|---|
| `ProductVariant.get_price_for_user` | **LOW** по индексу (3), **фактически MEDIUM** | Индекс видит 3: `ProductListSerializer.get_current_price`, `ProductVariantSerializer.get_current_price` (оба файла). **Индекс не показал `cart/models.py:154` и `cart/views.py:142`** — проверено grep'ом. Считать реальный радиус = 5, включая корзину и, транзитом через `price_snapshot`, заказы. |
| `ProductFilter.filter_min_price` / `filter_max_price` | **LOW** | 0 — django-filter вызывает по имени метода |
| `ProductListSerializer.get_opt1_price` (и `opt2`/`opt3`) | **LOW** | 0 — DRF вызывает по соглашению `get_<field>` |
| `to_representation` | **UNKNOWN** (имя перегружено в индексе) | Вручную: вызывается DRF; единственный внутренний вызывающий — `ProductDetailSerializer.to_representation` (`serializers.py:732-734`), который делает `super()` |

⚠️ Индекс GitNexus помечен `stale` (проиндексирован `98862f8`, HEAD `61dfeb88`), но дельта — только docs-коммиты в `_bmad-output`, кода они не касались. Ответ `{"error": "Symbol ... not found"}` на существующий символ = устаревший индекс; попросить Alex выполнить `! npx gitnexus analyze`.

### Текущее состояние правимых мест (проверено на `61dfeb88`)

- `ProductVariantSerializer.to_representation` (`serializers.py:93-117`): вычисляет `role` (для анонима — `"retail"`), сравнивает с литеральным `allowed_roles = [wholesale_level1, wholesale_level2, wholesale_level3, trainer, admin]`, при промахе делает `data.pop("rrp")` / `data.pop("msrp")`.
- `ProductListSerializer.to_representation` (`:575-597`): **та же логика, второй копией**. Оптовых полей не касается вовсе — именно поэтому они и утекают.
- `ProductListSerializer.Meta.fields` (`:511-514`): `retail_price`, `opt1_price`, `opt2_price`, `opt3_price` — как `SerializerMethodField` (`:475-478`), значения через `get_optN_price` (`:614-633`), каждый возвращает `0.0` при пустой цене.
- `ProductDetailSerializer` (`:709-734`): наследует `Meta.fields`, `to_representation` делегирует родителю → правок не требует.
- `ProductDetailSerializer.get_related_products` (`:811`): `ProductListSerializer(related_products, many=True, context=self.context)` — `context` пробрасывается, значит гейт применится сам. Это надо **проверить тестом**, а не править код.
- `get_price_for_user` (`models.py:1188-1203`): ранний выход для анонима + `role_price_mapping` по `user.role`; `wholesale_level4` там уже есть (стори 39.1).
- `filters.py:248-323`: две симметричные ветвящиеся конструкции по `request.user.role`.

### Точный код: `pricing_policy.py`

Новый файл `backend/apps/products/pricing_policy.py`:

```python
"""
Политика видимости цен в каталоге.

Единственный источник истины по вопросу «какие ценовые поля видит роль».
Инвариант (`project-context.md` §3): оптовые цены и B2B-инфо-цены доступны
только верифицированным пользователям с B2B-ролью; все остальные, включая
гостей, розницу и контрагентов 1С без портального аккаунта, видят розничную
цену.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.users.models import User

# Сырые оптовые поля ответа каталога. Стори 39.3 добавляет сюда "opt4_price".
WHOLESALE_PRICE_FIELDS = ("opt1_price", "opt2_price", "opt3_price")

# Инфо-цены B2B. Не участвуют в расчётах, но так же закрыты от розницы.
INFO_PRICE_FIELDS = ("rrp", "msrp")

# Роли, которым видны РРЦ/МРЦ. federation_rep исключён намеренно —
# поведение перенесено как есть из литеральных списков сериализаторов.
# Стори 39.3 добавляет сюда "wholesale_level4".
INFO_PRICE_ROLES = frozenset({"wholesale_level1", "wholesale_level2", "wholesale_level3", "trainer", "admin"})


def resolve_pricing_role(user: "User | Any | None") -> str:
    """
    Роль, по которой считается цена для пользователя.

    B2B-роль без верификации понижается до "retail": менеджер ещё не
    подтвердил контрагента, поэтому оптовых условий у него нет.
    """
    from apps.users.models import User

    if user is None or not getattr(user, "is_authenticated", False):
        return "retail"

    role = getattr(user, "role", "retail")
    if role in User.B2B_ROLES and not getattr(user, "is_verified", False):
        return "retail"
    return role


def can_see_wholesale_prices(user: "User | Any | None") -> bool:
    """
    Видит ли пользователь сырые оптовые поля (`WHOLESALE_PRICE_FIELDS`).

    Роль без права получает `0.0` — это означает «нет права видеть оптовую
    цену», а НЕ «цена не заполнена» (пустая цена даёт тот же `0.0` в
    `get_optN_price`). Снятие этой проверки открывает всю оптовую сетку
    анонимным запросам — см. `tech-debt.md` п. 18.
    """
    from apps.users.models import User

    role = resolve_pricing_role(user)
    return role in User.B2B_ROLES or role == "admin"


def can_see_info_prices(user: "User | Any | None") -> bool:
    """Видит ли пользователь инфо-цены РРЦ/МРЦ (`INFO_PRICE_FIELDS`)."""
    return resolve_pricing_role(user) in INFO_PRICE_ROLES
```

Почему ленивый импорт `User` внутри функций: `products/models.py` импортирует `pricing_policy`, а `users/models.py` — нет; импорт `User` на уровне модуля даёт цикл при загрузке приложений. Тот же приём уже применяется в `filters.py:254-256` и `cart/views.py:131`.

### Точный код: сериализаторы

`backend/apps/products/serializers.py`, шапка импортов — добавить:

```python
from .pricing_policy import WHOLESALE_PRICE_FIELDS, can_see_info_prices, can_see_wholesale_prices
```

`ProductVariantSerializer.to_representation` (`:93-117`) целиком становится:

```python
    def to_representation(self, instance: ProductVariant) -> dict[str, Any]:
        """Скрытие инфо-цен РРЦ/МРЦ от ролей без права (см. pricing_policy)"""
        data: dict[str, Any] = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        if not can_see_info_prices(user):
            data.pop("rrp", None)
            data.pop("msrp", None)

        return data
```

`ProductListSerializer.to_representation` (`:575-597`) целиком становится:

```python
    def to_representation(self, instance):
        """Скрытие оптовых и инфо-цен от ролей без права (см. pricing_policy)"""
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        if not can_see_info_prices(user):
            data.pop("rrp", None)
            data.pop("msrp", None)

        if not can_see_wholesale_prices(user):
            # 0.0 здесь означает «роль не имеет права видеть оптовую цену»,
            # а не «цена не заполнена»: пустая цена даёт тот же 0.0 в
            # get_optN_price. Ключи намеренно остаются в ответе — они
            # объявлены required в docs/api/openapi.yaml (tech-debt.md п. 18).
            for field in WHOLESALE_PRICE_FIELDS:
                if field in data:
                    data[field] = 0.0

        return data
```

Локальные переменные `role` и списки `allowed_roles` исчезают из обоих методов — это и есть закрытие дублирования из AC1.

### Точный код: `get_price_for_user`

`backend/apps/products/models.py:1188-1203`:

```python
    def get_price_for_user(self, user: User | None) -> Decimal:
        """Получить цену варианта для конкретного пользователя на основе его роли"""
        from apps.products.pricing_policy import resolve_pricing_role

        # Неверифицированный B2B и гость понижаются до retail (project-context.md §3)
        role = resolve_pricing_role(user)

        role_price_mapping = {
            "retail": self.retail_price,
            "wholesale_level1": self.opt1_price or self.retail_price,
            "wholesale_level2": self.opt2_price or self.retail_price,
            "wholesale_level3": self.opt3_price or self.retail_price,
            "wholesale_level4": self.opt4_price or self.retail_price,
            "trainer": self.trainer_price or self.retail_price,
            "federation_rep": self.federation_price or self.retail_price,
        }

        return role_price_mapping.get(role, self.retail_price)
```

Ранний `if not user or not user.is_authenticated: return self.retail_price` удаляется: `resolve_pricing_role(None)` возвращает `"retail"`, маппинг отдаёт `self.retail_price` — результат тот же. `admin` в маппинге отсутствует и падает в `.get(..., self.retail_price)` — как и до правки.

### Точный код: фильтры

`backend/apps/products/filters.py`, импорт на уровне модуля:

```python
from .pricing_policy import resolve_pricing_role
```

`filter_min_price` (`:266-286`) — блок выбора роли становится:

```python
        request = self.request
        user_role = resolve_pricing_role(getattr(request, "user", None) if request else None)
        if user_role == "wholesale_level1":
            self._variant_filters &= Q(opt1_price__gte=value) | Q(opt1_price__isnull=True, retail_price__gte=value)
        elif user_role == "wholesale_level2":
            ...
```

Остальные ветки (`wholesale_level2`, `wholesale_level3`, `trainer`, `federation_rep`, `else`) — без изменений, только сдвиг на один уровень отступа, так как внешний `if not request or not request.user.is_authenticated` / `else` убирается. То же в `filter_max_price` (`:301-321`) с `__lte`.

⚠️ Отступы: ветки внутри `else` были на 12 пробелах, после снятия обёртки становятся на 8. Проверить `black --check` — переформатирования быть не должно, длины строк не меняются (лимит 120, `backend/pyproject.toml`).

Ветку `wholesale_level4` **не добавлять** — это AC1 стори 39.3.

### Тесты, которые упадут без правки (проверено grep'ом)

`is_verified` по умолчанию `False` и в `tests/conftest.py` (`UserFactory`, `:59`), и в `User.is_verified` (`users/models.py:249`). Фикстуры `wholesale_user`, `trainer_user`, `admin_user` (`conftest.py:541-561`) уже ставят `is_verified=True` — они не пострадают. Пострадают тесты, создающие пользователя напрямую:

| Файл | Строки | Что ждёт |
|---|---|---|
| `apps/products/tests/test_product_variant_models.py` | 105-145 | `get_price_for_user` == `opt1/opt2/opt3/trainer/federation` цена |
| `apps/products/tests/unit/test_price_logic.py` | 121, 177, 190 | fallback `federation_rep`, два теста «Опт 4» из 39.1 |
| `apps/products/tests/test_serializers.py` | 45, 229, 249 | `current_price` == оптовая |
| `apps/products/tests/test_api_products.py` | 46 (ассерт 147-150) | все `current_price` == `opt1_price` |
| `tests/integration/base.py` | 110, 125 | базовый класс — тянет за собой наследников |
| `tests/integration/test_b2b_workflow.py` | 24 (ассерт 65) | `opt1_price == 800.00` в теле ответа |
| `tests/integration/test_pricing_integration.py` | 27-37 (ассерт 195) | `product_price == 750.00` (`opt2_price`) |
| `tests/integration/test_orders_api.py` | 465 | цена позиции заказа |
| `tests/integration/test_personal_cabinet_workflow.py` | 29, 171 | сценарии B2B-кабинета |
| `tests/integration/test_link_then_import_1c.py` | 77 | сценарий привязки 1С |

**Правило правки:** добавлять `is_verified=True` там, где тест проверяет **цену**. Там, где B2B-роль нужна для другого (баннеры, регистрация, импорт) — не трогать: `apps/banners/tests/test_views.py:221, 247`, `tests/integration/test_banners_api.py`, `test_portal_registration_1c_link.py`, `apps/products/tests/unit/test_variant_import_migrated.py:163`.

**Не ослаблять ассерты.** Если тест после добавления `is_verified=True` всё равно падает — это находка, а не повод править ожидание: остановиться и разобрать.

### Мина: `Mock()` всегда верифицирован

`tests/unit/test_product_filters.py:304-340` (`test_all_role_price_mappings`) подставляет `Mock()` в `request.user`. У Mock **любой** атрибут truthy, поэтому `getattr(user, "is_verified", False)` вернёт Mock-объект и роль не понизится — существующий тест пройдёт как есть. В новом тесте на неверифицированного оптовика `mock_user.is_verified = False` задавать **явно**, иначе тест молча проверит не то.

### Мина: тестовые файлы без маркеров

Стори 39.2 нашла случай, когда 13 тестов не попадали ни в `-m unit`, ни в `-m integration`. Среди затрагиваемых сейчас файлов:

| Файл | Состояние |
|---|---|
| `tests/unit/test_product_filters.py` | ✅ `pytestmark = pytest.mark.django_db` + `@pytest.mark.unit` на каждом классе |
| `apps/products/tests/unit/test_price_logic.py` | ✅ маркеры на классах |
| `apps/products/tests/test_api_products.py` | ⚠️ только `@pytest.mark.django_db` — **новый класс без явного `@pytest.mark.unit` CI не увидит** |
| `apps/products/tests/test_serializers.py` | ⚠️ то же |
| `apps/products/tests/test_product_variant_models.py` | ⚠️ то же |

На каждом новом классе ставить маркер явно. Предсуществующие классы **не чинить** — отдельный долг; при желании закрыть — вынести отдельным пунктом в Completion Notes на решение Alex (как сделано в 39.2).

Контроль отбора:

```bash
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q -m unit --collect-only apps/products/tests/unit/test_pricing_policy.py
```

### Структура новых тестовых модулей

`backend/apps/products/tests/unit/test_pricing_policy.py`:

```python
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory

from apps.products.factories import ProductFactory, ProductVariantFactory
from apps.products.pricing_policy import can_see_info_prices, can_see_wholesale_prices, resolve_pricing_role
from apps.products.serializers import ProductListSerializer

pytestmark = [pytest.mark.unit, pytest.mark.django_db]
```

| Тест | AC | Суть |
|---|---|---|
| `test_anonymous_resolves_to_retail` | 1 | `resolve_pricing_role(None)` и `AnonymousUser` → `"retail"` |
| `test_unverified_b2b_resolves_to_retail` | 1, 4 | Все шесть ролей из `B2B_ROLES` с `is_verified=False` → `"retail"` |
| `test_verified_b2b_keeps_role` | 1, 3 | Те же роли с `is_verified=True` → сама роль |
| `test_unregistered_never_sees_wholesale` | 2 | `role="unregistered"` → `can_see_wholesale_prices` False |
| `test_admin_sees_wholesale_and_info` | 3, 6 | `role="admin"` → оба предиката True |
| `test_federation_rep_sees_wholesale_but_not_info` | 3, 6 | Верифицированный `federation_rep`: опт — да, РРЦ/МРЦ — нет |
| `test_serializer_zeroes_wholesale_for_anonymous` | 2, 8 | Все `WHOLESALE_PRICE_FIELDS` == `0.0`, **ключи присутствуют** |
| `test_serializer_keeps_wholesale_for_verified` | 3 | Фактические значения варианта |
| `test_unverified_b2b_gets_retail_price` | 4 | `variant.get_price_for_user(user) == variant.retail_price` при заполненной `opt1_price` |
| `test_related_products_are_gated` | 2 | `ProductDetailSerializer(...).data["related_products"][0]["opt1_price"] == 0.0` для анонима |

`backend/tests/integration/test_catalog_price_visibility.py` (`pytestmark = pytest.mark.integration`) — сторож AC7:

```python
def _wholesale_values(payload: dict) -> list[float]:
    """Все значения полей вида opt*_price — включая те, что появятся позже (opt4_price)."""
    return [value for key, value in payload.items() if key.startswith("opt") and key.endswith("_price")]
```

| Тест | Суть |
|---|---|
| `test_anonymous_list_has_no_wholesale_prices` | `GET /api/v1/products/` без токена → у каждого товара все `opt*_price == 0` |
| `test_anonymous_detail_has_no_wholesale_prices` | `GET /api/v1/products/{slug}/` → то же, ключи на месте |
| `test_retail_user_has_no_wholesale_prices` | Аутентифицированная розница → то же |
| `test_unverified_wholesale_user_has_no_wholesale_prices` | `wholesale_level1`, `is_verified=False` → то же + `current_price == retail_price` |
| `test_verified_wholesale_user_sees_wholesale_prices` | Обратная сторона: значения не нулевые |
| `test_unverified_b2b_cart_price_is_retail` | `POST /api/v1/cart/items/` → `price_snapshot == retail_price` (AC4) |

Уникальные строковые данные (SKU, slug, `onec_id`) — через `get_unique_suffix()` из `backend/tests/conftest.py`. Автофикстура `clear_db_before_test` (`conftest.py:671-672`) делает тесты в `backend/tests/` транзакционными с последующим flush — на данные из data-миграций не рассчитывать. Образец сборки request-контекста для unit-тестов сериализаторов — `apps/products/tests/test_serializers.py:63-90`.

### Кеш ответов каталога — проверено, отсутствует

`ProductViewSet` не обёрнут ни в `cache_page`, ни в `CacheResponseMixin`; `CACHE_MIDDLEWARE`/`UpdateCacheMiddleware` в настройках не подключены (`grep` по `apps/products/views.py` и `freesport/settings/`). Единственный `cache.set` в модуле — `FEATURED_BRANDS_CACHE_KEY` (`views.py:470`), цен не содержит. Значит ролевой гейт не может протечь через общий кеш и **ключ кеша по роли добавлять не нужно**. Если в будущем на каталог поставят кеш — он обязан включать в ключ результат `resolve_pricing_role`, иначе ответ верифицированного оптовика уедет анониму.

### Контракт API: почему diff должен быть пустым

Вариант B не меняет ни `Meta.fields`, ни типы `SerializerMethodField`, поэтому drf-spectacular обязан выдать байт-в-байт тот же файл. Непустой diff = реализация уехала в вариант A (удаление ключей) либо в контейнере другая версия drf-spectacular.

```bash
# 1. Сгенерировать во временный файл внутри примонтированного /app (= backend/)
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  python manage.py spectacular --file /app/openapi.generated.yaml

# 2. Сравнить с закоммиченным контрактом (из корня репозитория)
diff backend/openapi.generated.yaml docs/api/openapi.yaml && echo "контракт не изменился"

# 3. Удалить временный файл
rm backend/openapi.generated.yaml
```

Контейнер бэкенда монтирует только `../backend:/app`, каталога `docs/` внутри нет — писать напрямую в него из контейнера нельзя.

Замечание на будущее (не задача этой стори): `rrp` и `msrp` стоят в `required` схем `ProductList`/`ProductDetail`, хотя фактически вырезаются для розницы и гостей — контракт уже расходится с ответом. Вариант B выбран в том числе для того, чтобы **не тиражировать** этот разрыв на оптовые поля.

### Что эта стори НЕ трогает

- **`frontend/`** — типы не меняются (`0.0` — валидное `number`), каскад `getProductPrice` в `ProductCard` (`opt3 → opt2 → opt1 → retail`, `ProductCard.tsx:111-130`) продолжает работать. Фронт ветвится по роли из стора и **не знает про `is_verified`** — но и не должен: у неверифицированного оптовика все `opt*_price` придут нулями, каскад сам упадёт на `retail_price`, что совпадёт с `current_price` от бэкенда. `npm run generate:types` не запускать.
- **`opt4_price`** — поля ещё нет в сериализаторе, его добавляет 39.3. Комментарии в `pricing_policy.py` подсказывают, куда его дописать.
- **`trainer_price` / `federation_price`** — сырыми полями не отдаются вовсе (в `Meta.fields` их нет), гейтить нечего.
- **Роль `wholesale_level4` в белых списках** — AC4 стори 39.3.
- **Сортировка каталога и аннотация `min_retail_price`** (`views.py:94-103`) — розничная осознанно, вне объёма.
- **Расхождение «каскад фронта против fallback бэка»** для уровней 1-3 — зафиксировано в `epics.md`, чинится (или нет) отдельно.
- **Существующие корзины** — `price_snapshot` уже записан и не пересчитывается. На проде затронутых корзин нет (все четыре неверифицированных оптовика неактивны, 0 заказов).

### Антипаттерны (НЕ ДЕЛАТЬ)

- **НЕ** удалять оптовые поля из ответа (`data.pop`) — это вариант A, отклонён решением 1; он ломает `required` в OpenAPI и требует правки типов фронта.
- **НЕ** вынимать `opt*_price` / `rrp` / `msrp` из `Meta.fields` и **не** править `openapi.yaml` руками.
- **НЕ** ставить проверку прав внутрь `get_opt1_price` / `get_opt2_price` / `get_opt3_price` — гейт должен быть в одном месте (`to_representation`), иначе стори 39.3 обязана будет продублировать его в четвёртом методе.
- **НЕ** оставлять литеральные списки ролей в сериализаторах — единственный источник истины `pricing_policy.py` (AC1).
- **НЕ** использовать `verification_status == "verified"` вместо `is_verified`: канонический флаг в коде — `is_verified` (`bonuses/views.py:57`, `bonuses/services/accrual.py:158`, `users/views/authentication.py:183`). `users/admin.py:432` читает оба через `or` — это отображение бейджа в админке, не право доступа.
- **НЕ** добавлять `permission_classes = [IsAuthenticated]` на `ProductViewSet` — каталог обязан оставаться публичным (`views.py:55`), закрывается только ценовое поле.
- **НЕ** править `cart/`, `orders/` — они получают корректную цену транзитом.
- **НЕ** править `serializers_variant.py` — второй `ProductVariantSerializer` сырых цен не отдаёт.
- **НЕ** добавлять `wholesale_level4` куда-либо — это стори 39.3.
- **НЕ** «чинить» падающие тесты ослаблением ассертов (AC10).
- **НЕ** чинить маркеры у предсуществующих тест-классов без отдельного решения Alex.

### Project Structure Notes

- Комментарии и docstrings нового кода — на русском (`project-context.md` §6).
- Типизация как в окружающем коде; `mypy.ini` в проекте активен, `warn_unused_ignores = True` — лишних `# type: ignore` не оставлять.
- Покрытие: `products` — критический модуль, ≥ 90 %; общее ≥ 70 %.
- Django 5.2.7, Python 3.14, DRF + drf-spectacular 0.28.0. Новых зависимостей стори не вводит. Миграций нет — `makemigrations --check` должен остаться чистым.
- `black` / `flake8`: `line-length = 120` (`backend/pyproject.toml`, `backend/setup.cfg`).
- Backend в Docker: `8001` снаружи / `8000` внутри; тестовый профиль — `docker-compose.test.yml`, проект `freesport-test`.

### Команды

```bash
# Точечный прогон новых тестов
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/unit/test_pricing_policy.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs tests/integration/test_catalog_price_visibility.py

# Эквивалент make test-unit (make в оболочке недоступен, таргеты ищут несуществующий docker/.env)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m unit
# Эквивалент make test-integration (≈30 мин — запускать в фоне)
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend pytest -q -m integration
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down

# Линтеры — в dev-контейнере, из корня репозитория
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  flake8 apps/products/pricing_policy.py apps/products/serializers.py apps/products/models.py apps/products/filters.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black --check apps/products/pricing_policy.py apps/products/serializers.py apps/products/models.py apps/products/filters.py
```

Ориентиры длительности: unit ≈ 7 мин, integration ≈ 30 мин. PostgreSQL обязателен, SQLite не поддерживается. Известный предсуществующий долг `black`: `apps/products/tests/unit/test_variant_import_migrated.py` (строки 521+, 549+, 646+) — не исправлять.

### References

- [Source: _bmad-output/planning-artifacts/tech-debt.md#18 — формулировка долга, вариант B, условие принятия, побочный эффект для 39.3]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 39 — «Предшествующая работа (решение Alex, 2026-08-03)»]
- [Source: _bmad-output/implementation-artifacts/Story/39-3-catalog-admin-api-opt4-price.md — шапка с предупреждением о координатах, AC2-AC4, Task 2]
- [Source: project-context.md §3 — Role-based pricing и B2B verification]
- [Source: project-context.md §4 — маркеры pytest, команды прогона, API-контракт sync]
- [Source: backend/apps/products/serializers.py:93-117 — ProductVariantSerializer.to_representation, литеральный allowed_roles]
- [Source: backend/apps/products/serializers.py:452-531 — объявления полей и Meta.fields ProductListSerializer]
- [Source: backend/apps/products/serializers.py:575-597 — ProductListSerializer.to_representation]
- [Source: backend/apps/products/serializers.py:614-633 — get_opt1/2/3_price, возврат 0.0 при пустой цене]
- [Source: backend/apps/products/serializers.py:709-734, :789-811 — ProductDetailSerializer и related_products]
- [Source: backend/apps/products/models.py:1188-1203 — get_price_for_user]
- [Source: backend/apps/products/filters.py:248-323 — filter_min_price / filter_max_price]
- [Source: backend/apps/products/views.py:50-104 — ProductViewSet, AllowAny, Prefetch first_variant_list]
- [Source: backend/apps/cart/models.py:149-158 — CartItem.save, price_snapshot]
- [Source: backend/apps/cart/views.py:129-158 — perform_create, цена по роли]
- [Source: backend/apps/orders/services/order_create.py:138 — unit_price из price_snapshot]
- [Source: backend/apps/users/models.py:153-186, :249-252, :321-327 — ROLE_CHOICES, B2B_ROLES, is_verified, verification_status]
- [Source: backend/tests/conftest.py:46-64, :533-561, :671 — UserFactory (is_verified=False), фикстуры ролей, clear_db_before_test]
- [Source: backend/tests/unit/test_product_filters.py:304-340 — test_all_role_price_mappings, Mock-ловушка]
- [Source: frontend/src/components/business/ProductCard/ProductCard.tsx:110-125 — каскад opt3→opt2→opt1→retail]
- [Source: frontend/src/utils/pricing.ts — isB2BRole, getPriceForRole]

---

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, workflow `bmad-dev-story`), 2026-08-03.

### Debug Log References

**Прогоны (Docker, PostgreSQL, проект `freesport-test`):**

| Прогон | Результат | Базовая линия | Дельта |
|---|---|---|---|
| `pytest -q -m unit` (финальный) | **1090 passed, 1 skipped** | 1041 passed, 1 skipped | +49 (44 `test_pricing_policy.py` + 5 `TestProductFilterPricingPolicy`) |
| `pytest -q -m integration` (финальный) | **754 passed, 2 skipped** | 744 passed, 2 skipped | +10 (`test_catalog_price_visibility.py`) |
| `black --check` по 16 изменённым файлам | чисто | — | — |
| `flake8` по изменённым файлам | чисто (exit 0) | — | — |
| `makemigrations --check --dry-run` | `No changes detected` | — | — |
| `npx gitnexus detect-changes --scope all` | 18 файлов, 16 символов, **risk low**, 0 затронутых процессов | — | — |

**Прогоны сессии 2 (закрытие находки ревью, 2026-08-03):**

| Прогон | Результат |
|---|---|
| `pytest -q` по трём файлам находки (RED, до правки) | **4 failed, 88 passed** |
| Те же три файла (GREEN, после правки) | **92 passed** |
| `pytest -q` **весь пакет без `-m`** (первый) | **1 failed, 2694 passed, 4 skipped** — падение в `test_user_cart_integration.py` |
| `pytest -q tests/integration/test_user_cart_integration.py` (после правки) | **4 passed** |
| `pytest -q` **весь пакет без `-m`** (финальный, 33 мин) | **2695 passed, 4 skipped, 0 failed** |
| `black --check` + `flake8` по 4 изменённым файлам | чисто (exit 0) |
| `npx gitnexus detect-changes --scope all` | 6 файлов, 2 символа (заголовки `AGENTS.md`/`CLAUDE.md`), **risk low**, 0 затронутых процессов |

**RED-фаза зафиксирована:** первый прогон `apps/products/tests/unit/test_pricing_policy.py` до создания модуля упал с `ModuleNotFoundError: No module named 'apps.products.pricing_policy'` — тесты писались до кода.

**Отбор по маркерам проверен (`--collect-only`):** `-m unit` собирает 44 теста `test_pricing_policy.py` и 5 тестов `TestProductFilterPricingPolicy`; `-m integration` собирает 10 тестов `test_catalog_price_visibility.py`. Ни один новый тест не выпадает из CI-фильтров.

**Единственное падение регрессии и его разбор.** Первый полный integration-прогон дал `1 failed`: `tests/integration/test_search_api.py::SearchAPITest::test_search_role_based_pricing` — `AssertionError: 18999.0 not less than 18999.0`. Тест сравнивает `current_price` тренера с розничной, а `trainer_user` (`:94`) создавался без `is_verified`. Это не регресс, а ровно то поведение, которое стори вводит. Файл **не был перечислен** в Dev Notes → «Тесты, которые упадут без правки» — список оказался неполным на один файл. Починено по правилу стори (`is_verified=True`, тест проверяет цену), ассерт не ослаблялся; после правки — 19 passed.

**Blast radius (GitNexus, индекс `up-to-date` на `6704596`).** `get_price_for_user` — **LOW** по индексу: 3 прямых вызывающих (`ProductListSerializer.get_current_price`, `ProductVariantSerializer.get_current_price` в обоих файлах), 0 затронутых процессов. Предупреждение Dev Notes подтвердилось: индекс **не видит** `cart/models.py:154` и `cart/views.py:142` — фактический радиус 5, включая корзину и транзитом заказы. HIGH/CRITICAL не было ни по одному символу.

### Completion Notes List

**Что сделано по существу.** Обе половины доменного инварианта `project-context.md` §3 закрыты одним источником истины — `backend/apps/products/pricing_policy.py`. Через него выражены: обнуление `opt*_price` в `ProductListSerializer.to_representation`, скрытие `rrp`/`msrp` в обоих сериализаторах, `ProductVariant.get_price_for_user` и ветвление по роли в обоих ценовых фильтрах. Дублирующиеся литеральные списки `allowed_roles` из двух сериализаторов удалены (AC1). `cart/` и `orders/` не правились — цена приходит транзитом через `price_snapshot`, что покрыто тестом `test_unverified_b2b_cart_price_is_retail`.

**AC9 доказан строго, а не «git diff чист».** Буквальная проверка выполнена: `git status` по `docs/api/openapi.yaml` пуст, файл не трогался. Но проверка «регенерация идентична закоммиченному» из Dev Notes **невыполнима по двум предсуществующим причинам**, и это находка стори:

1. Закоммиченный контракт разошёлся с генерацией целиком (4913 строк генерации против 4826 закоммиченных; последний коммит файла — `73992820` от 2026-07-26).
2. `manage.py spectacular` **недетерминирован**: два прогона на неизменном коде дают ~275 строк diff — переставляются HTTP-методы внутри путей `/users/addresses/`, `/users/favorites/`, `/orders/`, `/cart/items/`.

Поэтому AC9 проверен семантически, сравнением генерации **до и после** правки (код откатывался к `HEAD` и генерировался повторно): `components.schemas` идентичны **целиком**, включая `ProductList`, `ProductDetail`, `ProductVariant`; множество пар «путь → метод» идентично; `opt1_price`, `opt2_price`, `opt3_price` остались и в `properties`, и в `required`. Вариант B подтверждён: контракт не изменился, типы фронта не пересобирались. Обе находки записаны в `tech-debt.md` п. 18 и в раздел «Дрейф `openapi.yaml`» стори 39.3 — там Task 8 требует полной регенерации файла и без этого знания упёрся бы в шумный diff.

**Отклонение от Dev Notes — один пункт, осознанный.** Task 5.6 предписывал добавить `is_verified=True` в `tests/integration/test_link_then_import_1c.py:77`. Не сделано: этот тест проверяет привязку записи 1С к портальному аккаунту (`onec_id`, роль, отсутствие дублей), цену не ассертит вовсе, а `verification_status="pending"` в нём — часть моделируемого сценария «необработанная заявка». Правило Dev Notes («добавлять `is_verified=True` там, где тест проверяет **цену**») здесь приоритетнее списка. Тест прошёл без правки — подтверждение, что он к политике цен не чувствителен.

**Список «тестов, которые упадут» оказался неполным.** Не хватало `tests/integration/test_search_api.py:94` (см. Debug Log). Для последующих стори: `grep` по созданию B2B-пользователей стоит вести не только по перечисленным файлам, а по всему `backend/tests/`.

**Проверено и не потребовало правок:**
- `ProductDetailSerializer` — делегирует `super().to_representation`, гейт наследуется (Task 2.4).
- `related_products` — `context` пробрасывается, гейт применяется сам; подтверждено двумя тестами (unit + integration), а не правкой кода.
- `serializers_variant.py` — сырых ценовых полей не отдаёт (Task 2.5).
- Ранняя ветка «аноним → retail» в `get_price_for_user` удалена как поглощённая: `resolve_pricing_role(None)` даёт `"retail"`, маппинг возвращает `retail_price`. Покрыто `test_anonymous_gets_retail_price`.
- Ветка `if not request or not request.user.is_authenticated` в обоих фильтрах снята; эквивалентность покрыта `test_anonymous_request_filters_by_retail_price`.
- Кеша на ответах каталога нет — ключ по роли не требуется (проверено при написании стори, подтверждено при реализации).

**Мина `Mock()` обойдена как предписано:** в новом классе `TestProductFilterPricingPolicy` `mock_user.is_verified` задаётся **явно**, с комментарием почему. Предсуществующий `test_all_role_price_mappings` не трогался — с truthy-Mock он проходит как есть.

**Долг, оставленный на решение Alex (не чинил намеренно).** Маркеры у предсуществующих тест-классов в `apps/products/tests/test_api_products.py`, `test_serializers.py`, `test_product_variant_models.py` — только `@pytest.mark.django_db`, без `@pytest.mark.unit`. Классы этих файлов в CI-фильтр `-m unit` не попадают. Новые классы стори маркеры несут явно; починка старых — отдельное решение, как это было сделано в стори 39.2.

---

### Сессия 2 — закрытие находки ревью (2026-08-03)

**Что исправлено.** Пять мест, где B2B-пользователь создавался без `is_verified=True`, но тест ассертил оптовую цену или РРЦ/МРЦ. Везде добавлен `is_verified=True` с русским комментарием-ссылкой на `pricing_policy.resolve_pricing_role`; **ни один ассерт не ослаблен**, гейт нигде не снимался — то есть AC10 закрыт по букве.

| Файл | Место | Что ассертит |
|---|---|---|
| `tests/unit/test_models/test_product_models.py` | `test_product_pricing_for_different_roles` — 5 B2B-ролей | `get_price_for_user` == opt1/opt2/opt3/trainer/federation |
| `tests/unit/test_models/test_product_models.py` | `test_product_price_fallback_to_retail` — 2 роли | fallback при пустой `opt1_price` |
| `tests/unit/test_models/test_order_models.py` | `test_order_item_with_different_user_role_pricing` | `unit_price` позиции заказа |
| `tests/integration/test_product_detail_api.py` | фикстура `wholesale_client` | наличие `rrp`/`msrp` в ответе |
| `tests/integration/test_user_cart_integration.py` | `setUp` → `b2b_user` | `unit_price` в корзине ниже розничной |

**Не тронуто по правилу «`is_verified=True` только там, где тест проверяет цену»:** `test_order_models.py:141` (`test_order_for_different_user_roles` — ассертит только `user.role`) и фикстура `trainer_client` в `test_product_detail_api.py:117` (`test_discount_calculation` — единственный ценовой ассерт в нём закомментирован). Оба прошли без правки, что это правило и подтверждает.

**Корневая причина: 852 теста вне CI-фильтров.** Измерено `--collect-only`: всего в пакете **2699** тестов, `-m unit` собирает **1091**, `-m integration` — **756**. Итого **852 теста (31 %) не попадают ни в `make test-unit`, ни в `make test-integration`** — именно поэтому финальные прогоны сессии 1 (unit 1090 + integration 754) были зелёными при пяти сломанных тестах. Все пять найденных мест лежат в файлах без маркера: `tests/unit/test_models/test_product_models.py` и `test_order_models.py` несут только `@pytest.mark.django_db`, `test_product_detail_api.py` — только `pytestmark = pytest.mark.django_db`, а `test_user_cart_integration.py` — **вообще ни одного** маркера.

Практический вывод для следующих стори: **прогон по маркерам не является доказательством отсутствия регрессии в этом репозитории.** Финальную проверку вести полным `pytest -q` без `-m` (33 мин против 7+30 по фильтрам — дешевле, а покрытие полное).

**Расширение долга по маркерам (по-прежнему на решение Alex, не чинил).** К трём файлам из сессии 1 добавляются как минимум `tests/unit/test_models/test_product_models.py`, `tests/unit/test_models/test_order_models.py`, `tests/integration/test_product_detail_api.py`, `tests/integration/test_user_cart_integration.py`. Реальный масштаб — 852 теста; это отдельная задача уровня «навести маркеры по всему `backend/tests/`», а не побочная правка ценовой стори. Пока она не сделана, CI-гейт `make test-unit`/`test-integration` даёт ложно-зелёный результат на трети пакета.

**Что стори НЕ трогала (по плану):** `frontend/`, `opt4_price`, `wholesale_level4` в белых списках, `permission_classes` каталога, сортировка и аннотация `min_retail_price`, существующие корзины.

**Кросс-документные хвосты (Task 8) закрыты:** в стори 39.3 обновлён `baseline_commit`, освежены все координаты Dev Notes и References, Task 2.5 и AC4 переформулированы на `pricing_policy.py` (с явным требованием добавить `opt4_price` в `WHOLESALE_PRICE_FIELDS`), добавлена мина про `is_verified` в тестах 39.3, снято предупреждение в шапке, раздел «Дрейф `openapi.yaml`» дополнен измеренными фактами. В `tech-debt.md` п. 18 помечен закрытым с фактической формой исправления.

### File List

**Новые файлы:**

- `backend/apps/products/pricing_policy.py`
- `backend/apps/products/tests/unit/test_pricing_policy.py`
- `backend/tests/integration/test_catalog_price_visibility.py`

**Изменённый код:**

- `backend/apps/products/serializers.py`
- `backend/apps/products/models.py`
- `backend/apps/products/filters.py`

**Изменённые тесты:**

- `backend/apps/products/tests/test_product_variant_models.py`
- `backend/apps/products/tests/test_serializers.py`
- `backend/apps/products/tests/test_api_products.py`
- `backend/apps/products/tests/unit/test_price_logic.py`
- `backend/tests/unit/test_product_filters.py`
- `backend/tests/integration/base.py`
- `backend/tests/integration/test_b2b_workflow.py`
- `backend/tests/integration/test_pricing_integration.py`
- `backend/tests/integration/test_orders_api.py`
- `backend/tests/integration/test_search_api.py`

**Изменённые тесты (сессия 2, закрытие находки ревью):**

- `backend/tests/unit/test_models/test_product_models.py`
- `backend/tests/unit/test_models/test_order_models.py`
- `backend/tests/integration/test_product_detail_api.py`
- `backend/tests/integration/test_user_cart_integration.py`

**Изменённые документы:**

- `_bmad-output/implementation-artifacts/Story/security-wholesale-price-visibility.md` (этот файл)
- `_bmad-output/implementation-artifacts/Story/39-3-catalog-admin-api-opt4-price.md`
- `_bmad-output/planning-artifacts/tech-debt.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

| Дата | Изменение |
|---|---|
| 2026-08-03 | Реализована политика видимости цен: новый модуль `pricing_policy.py`, гейт `opt*_price` в сериализаторах, верификация в `get_price_for_user`, согласованные ценовые фильтры. 3 новых файла, 3 файла кода, 11 тестовых файлов, 4 документа. Прогоны: unit 1090 passed / 1 skipped, integration 754 passed / 2 skipped. Статус → review. |
| 2026-08-03 | Закрыта находка code review — 1 item (AC10): `is_verified=True` добавлен в 5 фикстур/тестов ролевого ценообразования в 4 файлах, ассерты не ослаблялись. Пятый случай (`test_user_cart_integration.py`) найден сверх находки полным прогоном без фильтра по маркерам. Зафиксирована корневая причина: 852 из 2699 тестов не попадают в CI-фильтры `-m unit`/`-m integration`. Финальный прогон всего пакета: **2695 passed, 4 skipped, 0 failed**. Статус → review. |
