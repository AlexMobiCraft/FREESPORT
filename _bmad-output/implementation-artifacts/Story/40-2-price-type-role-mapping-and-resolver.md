---
baseline_commit: c549b04ef56f0db518c71708226fa38f899680ac
---

# Story 40.2: Справочник видов цен несёт роль портала и разрешает её

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> ✅ **Внешних блокеров нет.** В отличие от 40.1, эта стори не зависит от патча расширения БУС и от новых выгрузок 1С: она работает со справочником `PriceType` в БД портала и с `settings.ONEC_EXCHANGE`. Реальные XML здесь не нужны — данных выгрузки стори не читает.
> Стори **независима от 40.1** и может выполняться параллельно: общих файлов у них нет.

## Story

As a **Менеджер**,
I want **чтобы соответствие «вид цен 1С → роль портала» хранилось в справочнике и правилось из админки**,
so that **появление нового вида цен в 1С не требовало релиза, а решение о роли принималось по явным и проверяемым правилам**.

## Acceptance Criteria

1. **AC1 (FR-40-03).** Data-миграция приложения `products` заполняет `PriceType.user_role` из `ONEC_EXCHANGE.PRICE_TYPE_BY_ROLE` для пяти ролей: `wholesale_level1…4` → «Опт 1…4», `trainer` → «Тренерская». У записей «РРЦ» и «МРЦ» поле остаётся **пустым** — иначе контрагенты-маркетплейсы на виде цен РРЦ (42 записи в снимке 40.1) уедут в `retail` вопреки решению 1 задания.

2. **AC2 (FR-40-03, NFR-3940-06).** Миграция идемпотентна: повторный прогон не создаёт дублей и **не перезаписывает** уже непустой `user_role` (поле правится менеджером из админки — слепой `update()` затёр бы его ручную настройку). `reverse` очищает `user_role` **только** у записей, которые заполнила эта миграция; запись «Опт 4», засеянную вместе с ролью миграцией `0053_seed_price_type_opt4`, `reverse` не трогает.

3. **AC3 (FR-40-04).** Модель `PriceType` зарегистрирована в админке `products`. `list_display` содержит `onec_name`, `product_field`, `user_role`, `is_active`. Поле `user_role` доступно для редактирования.

4. **AC4 (FR-40-04, защита от опечатки).** Ввод `user_role` в админке ограничен списком существующих ролей (`User.ROLE_CHOICES`) плюс пустое значение. Свободный текст запрещён: опечатка вида `wholesale_level_2` дала бы роль, которой нет в `ROLE_CHOICES`, и стори 40.4 записала бы её живому аккаунту без единой ошибки.

5. **AC5 (FR-40-02).** Создан модуль `backend/apps/users/services/price_type_role.py`, в нём объявлены:
   - `RoleResolution(NamedTuple)` с полями `role: str | None`, `reason: str`, `matched: list[str]`;
   - `resolve_role_from_price_types(price_type_ids: list[str], agreement_status: str = "") -> RoleResolution`.

6. **AC6 (FR-40-02).** `agreement_status == "НетСоглашения"` → `role=None`, `reason="no_agreement"`, `matched=[]`. Причина отличается от `no_data` по смыслу и по последствиям: `no_agreement` — подтверждённое 1С отсутствие соглашения (в 40.3 гасит `onec_price_type_id`), `no_data` — отсутствие данных как таковых (в 40.3 **не** гасит).

7. **AC7 (FR-40-02, решение 4).** Пустой список GUID **без** статуса `НетСоглашения` → `role=None`, `reason="no_data"`, `matched=[]`.

8. **AC8 (FR-40-02, решение 1).** Ни один GUID не найден в `PriceType` → `role=None`, `reason="unknown_price_type"`, `matched=[]`.

9. **AC9 (FR-40-02, решение 1).** GUID **найден** в `PriceType`, но `user_role` записи пуст (РРЦ, МРЦ) → `role=None`, `reason="unknown_price_type"`. «Известен как вид цен, но роли не несёт» трактуется наравне с неизвестным — иначе маркетплейсы поедут в `retail`.

10. **AC10 (FR-40-02, решение 5).** Два и более GUID, каждый с непустым `user_role` → `role=None`, `reason="ambiguous"`, `matched` содержит **все** конфликтующие GUID. Правило действует и когда роли совпадают: два разных вида цен — это два разных соглашения в 1С, а маппинг редактируем и может разойтись завтра.

11. **AC11 (FR-40-02).** Ровно один GUID несёт непустой `user_role` (остальные пустые или неизвестные) → возвращается эта роль, `reason="resolved"`, `matched` содержит сработавший GUID.

12. **AC12 (NFR-3940-09).** Справочник читается **один раз на сессию импорта**: объявлена функция загрузки маппинга, а `resolve_role_from_price_types` принимает готовый маппинг параметром. `functools.lru_cache` на функции и модульный кэш-глобал **запрещены явно** — маппинг правится из админки (AC3), а долгоживущий Celery-воркер продолжил бы отдавать значение, отменённое менеджером час назад. Доказывается тестом на числе SQL-запросов.

13. **AC13 (FR-40-13, сторож согласованности).** Тест-сторож проверяет: для каждой из ролей `wholesale_level1`, `wholesale_level2`, `wholesale_level3`, `wholesale_level4`, `trainer` цепочка `PRICE_TYPE_BY_ROLE → PRICE_TYPE_ID_BY_NAME → PriceType.user_role` возвращает исходную роль. Роли `retail`, `admin`, `federation_rep` исключены **явным списком с комментарием в коде теста**: `retail`/`admin` отображаются на «РРЦ», у которого `user_role` намеренно пуст; вид цен «Партнер» на портал не выгружается и записи `PriceType` не имеет.

14. **AC14 (FR-40-13, регресс).** Код `order_export._get_price_type` / `_get_price_type_id` (`backend/apps/orders/services/order_export.py:550-568`) **не изменён**. Сторож проверяет согласованность прямого и обратного маппинга, но не переводит экспорт заказа на новый источник.

15. **AC15 (NFR-3940-02, -03).** Покрыты тестами все четыре значения `reason`, случай «GUID известен, роль пуста», однократность чтения справочника, идемпотентность и обратимость миграции, состав `PriceTypeAdmin` и сторож. Маркеры проставляются автоматически по каталогу (`tests/unit/` → `unit`); вручную ничего добавлять не нужно.

## Tasks / Subtasks

- [x] **Task 1: Data-миграция `products` — заполнить `user_role`** (AC: 1, 2)
  - [x] 1.1: Создать `backend/apps/products/migrations/0054_price_type_user_role.py`, зависимость — `("products", "0053_seed_price_type_opt4")`
  - [x] 1.2: Объявить в модуле миграции константу `ROLES_WITH_PRICE_TYPE` (пять ролей) с комментарием, почему исключены `retail`, `admin`, `federation_rep` — точный код в Dev Notes
  - [x] 1.3: `forwards`: для каждой роли получить наименование из `settings.ONEC_EXCHANGE["PRICE_TYPE_BY_ROLE"]`, GUID — из `PRICE_TYPE_ID_BY_NAME`; искать запись по `onec_id=GUID`, при промахе — по `onec_name`; обновлять **только** записи с `user_role == ""`
  - [x] 1.4: `reverse`: очищать `user_role` только у записей, где он равен ожидаемой роли **и** GUID входит в список миграции, **исключая** GUID «Опт 4» (его роль поставила `0053`)
  - [x] 1.5: НЕ создавать отсутствующие записи `PriceType` — справочник наполняет импорт `priceLists` (см. Dev Notes → «Миграция — no-op на чистой БД»)
  - [x] 1.6: НЕ добавлять `choices` в поле модели `PriceType.user_role` — ограничение ввода делается формой админки (Task 2), схемной миграции в этой стори быть не должно

- [x] **Task 2: Админка справочника видов цен** (AC: 3, 4)
  - [x] 2.1: Добавить `PriceTypeAdminForm` в `backend/apps/products/forms.py` — `ChoiceField` с пустым вариантом + `User.ROLE_CHOICES`, `required=False` (точный код в Dev Notes)
  - [x] 2.2: Зарегистрировать `PriceTypeAdmin` в `backend/apps/products/admin.py` рядом с `ColorMappingAdmin` (`admin.py:571`), добавить `PriceType` в импорт из `.models` (список импорта алфавитный — вставить между `HomepageCategory` и `Product`)
  - [x] 2.3: `list_display = ("onec_name", "onec_id", "product_field", "user_role", "is_active")`, `search_fields = ("onec_name", "onec_id")`, `list_filter = ("is_active",)`, `readonly_fields = ("created_at",)`, `ordering = ("onec_name",)`. `list_editable` **не задавать** — см. Dev Notes → «Мина: `list_editable` обходит `form`»
  - [x] 2.4: `onec_id` и `onec_name` **не** делать readonly в форме: значения приходят из 1С, но ручное заведение вида цен до первого импорта — легитимный сценарий

- [x] **Task 3: Модуль разрешения роли** (AC: 5, 6, 7, 8, 9, 10, 11, 12)
  - [x] 3.1: Создать `backend/apps/users/services/price_type_role.py` (полный код — в Dev Notes). Docstring и комментарии на русском
  - [x] 3.2: Объявить `RoleResolution(NamedTuple)`, константы причин (`REASON_RESOLVED`, `REASON_NO_DATA`, `REASON_NO_AGREEMENT`, `REASON_UNKNOWN`, `REASON_AMBIGUOUS`) и `AGREEMENT_STATUS_NONE = "НетСоглашения"`
  - [x] 3.3: `load_price_type_role_map() -> dict[str, str]` — один запрос `PriceType.objects.filter(is_active=True).exclude(user_role="")`, ключ — `onec_id` в нижнем регистре
  - [x] 3.4: `resolve_role_from_price_types(price_type_ids, agreement_status="", *, role_map=None)`; при `role_map is None` вызывает загрузчик сам
  - [x] 3.5: Порядок ветвления строго: `no_agreement` → `no_data` → фильтр по маппингу → `unknown_price_type` / `ambiguous` / `resolved`
  - [x] 3.6: НЕ вешать `@lru_cache`, не заводить модульный глобал под маппинг (AC12)
  - [x] 3.7: НЕ импортировать `apps.users.models` в этот модуль — роль здесь строка, валидация роли живёт в 40.4/40.5

- [x] **Task 4: Тесты резолвера и сторож** (AC: 6-13, 15)
  - [x] 4.1: Создать `backend/tests/unit/test_services/test_price_type_role.py`, `pytestmark = [pytest.mark.django_db]` (маркер `unit` проставится по каталогу)
  - [x] 4.2: Тесты на все четыре `reason` + AC9 («GUID известен, роль пуста») + AC10 на двух GUID с одинаковой ролью
  - [x] 4.3: Тест противоречивого входа: `agreement_status="НетСоглашения"` **и** непустой `price_type_ids` → `no_agreement` (ветка статуса безусловно приоритетна)
  - [x] 4.4: Тест регистра: GUID в верхнем регистре на входе разрешается так же, как в нижнем
  - [x] 4.5: Тест AC12: `django_assert_num_queries(1)` на `load_price_type_role_map()`; `django_assert_num_queries(0)` на 3 вызова `resolve_role_from_price_types(..., role_map=m)`; и `assert not hasattr(resolve_role_from_price_types, "cache_clear")` — прямой запрет `lru_cache`
  - [x] 4.6: Тест-сторож AC13 в отдельном классе: локальный `ROLES_WITH_PRICE_TYPE` с комментарием об исключённых ролях, посев `PriceType` из настроек с `user_role=""`, прогон `forwards` миграции, затем `resolve_role_from_price_types([guid]).role == role` для каждой из пяти ролей
  - [x] 4.7: Тест AC14: `order_export.py:550-568` не менялся — доказывается прогоном существующего `backend/tests/unit/test_order_export_service.py` без правок (Task 6.2), отдельного теста не писать

- [x] **Task 5: Тесты миграции и админки** (AC: 1, 2, 3, 4, 15)
  - [x] 5.1: Создать `backend/tests/unit/test_migration_price_type_user_role.py` по образцу `backend/tests/unit/test_migration_unregistered_role.py` — функции миграции вызываются напрямую через `importlib` (тестовая БД строится с `--nomigrations`, посеянное миграциями вычищается)
  - [x] 5.2: Тест AC1: пять записей получают роли, «РРЦ» и «МРЦ» остаются с пустым `user_role`
  - [x] 5.3: Тест AC2 (идемпотентность): два прогона подряд → те же значения, число записей не изменилось
  - [x] 5.4: Тест AC2 (не перезаписывает): запись «Опт 3» с `user_role="trainer"` (ручная правка менеджера) после прогона сохраняет `trainer`
  - [x] 5.5: Тест AC2 (reverse): после `forwards` + `reverse` роли пяти записей пусты, а роль «Опт 4» (выставленная до прогона, как это делает `0053`) сохранена
  - [x] 5.6: Тест «no-op на пустом справочнике»: `forwards` на пустой таблице не создаёт записей и не падает
  - [x] 5.7: Тесты админки — дописать класс `TestPriceTypeAdmin` в `backend/tests/unit/test_admin/test_products_admin.py`: модель зарегистрирована (`admin.site.is_registered(PriceType)`), состав `list_display`, `user_role` не в `readonly_fields`, форма отдаёт `ChoiceField` и отвергает несуществующую роль

- [x] **Task 6: Прогон, регресс, линтеры, pre-commit** (AC: 14, 15)
  - [x] 6.1: Прогон новых тестов в тест-контейнере (команда — в Dev Notes → «Тестирование: как запускать»)
  - [x] 6.2: Регресс: `tests/unit/test_order_export_service.py`, `tests/unit/test_settings_onec.py`, `apps/products/tests/unit/test_price_logic.py`, `tests/unit/test_admin/test_products_admin.py`, `tests/integration/test_onec_export.py`
  - [x] 6.3: Проверить, что `python manage.py makemigrations --check --dry-run` не предлагает новых миграций (доказывает, что модель не менялась — Task 1.6)
  - [x] 6.4: `black` + `flake8` на изменённых файлах
  - [x] 6.5: `npx gitnexus detect-changes --scope all` — ожидаемые затронутые символы: новый модуль `price_type_role`, `PriceTypeAdmin`, `PriceTypeAdminForm`, новая миграция. `_get_price_type` в списке быть не должно

### Review Findings

- [x] [AI-Review][Med] Case-colliding GUID дают произвольную роль [`backend/apps/users/services/price_type_role.py:47`](../../../backend/apps/users/services/price_type_role.py#L47) — **закрыто 2026-08-05** (решение Alex: «загрузчик + нормализация в форме»). `load_price_type_role_map()` выявляет регистровых двойников с расходящимися ролями и исключает такой GUID из маппинга целиком — резолвер отвечает по нему `unknown_price_type`, роль не применяется. `PriceTypeAdminForm.clean_onec_id()` приводит GUID к нижнему регистру и отвергает ввод, если запись с тем же GUID в другом регистре уже есть. Существующие данные не мигрируются (схемных и data-миграций не добавлено). 4 новых теста.
- [x] [AI-Review][Low] Reverse-миграция не различает роль миграции и такую же ручную роль [`backend/apps/products/migrations/0054_price_type_user_role.py:62`](../../../backend/apps/products/migrations/0054_price_type_user_role.py#L62) — **закрыто 2026-08-05** (решение Alex: «явно ослабить контракт + тест»). Поведение оставлено прежним, ограничение зафиксировано в docstring `clear_user_roles()` и характеризующим тестом `test_clears_manual_role_that_matches_expected_value`. Хранить происхождение значения означало бы схемную миграцию, запрещённую Task 1.6.

## Dev Notes

### Что уже есть и переиспользуется (не изобретать)

| Нужное | Где уже есть |
|---|---|
| Поле `PriceType.user_role` | `backend/apps/products/models.py:740` — объявлено, `blank=True`, `max_length=50`, **пусто у всех записей и нигде не читается**. Заводить новое поле не нужно |
| Маппинг роль → наименование вида цен | `settings.ONEC_EXCHANGE["PRICE_TYPE_BY_ROLE"]` (`backend/freesport/settings/base.py:348-357`) |
| Маппинг наименование → GUID | `settings.ONEC_EXCHANGE["PRICE_TYPE_ID_BY_NAME"]` (`base.py:359-367`) |
| Образец идемпотентной data-миграции по `PriceType` | `backend/apps/products/migrations/0053_seed_price_type_opt4.py` (стори 39.1) |
| Образец теста data-миграции через `importlib` | `backend/tests/unit/test_migration_unregistered_role.py` и `TestSeedOpt4PriceType` (`apps/products/tests/unit/test_price_logic.py:257`) |
| Образец сервиса, читающего редактируемый из админки справочник | `backend/apps/users/services/region_routing.py` (`resolve_manager_recipients`) |
| Образец простого `ModelAdmin` справочника | `ColorMappingAdmin` (`apps/products/admin.py:571`), `Attribute1CMappingAdmin` (`admin.py:997`) |
| Образец форм админки приложения | `backend/apps/products/forms.py` (`MergeBrandsActionForm` и др.) |
| Образец теста админки | `backend/tests/unit/test_admin/test_products_admin.py` |

**Похожее имя, другая ответственность:** `apps/products/pricing_policy.resolve_pricing_role(user)` отвечает на вопрос «по какой роли считать цену этому пользователю» (видимость цен, понижение неверифицированного B2B до `retail`). Наш `resolve_role_from_price_types(guids)` отвечает на вопрос «какую роль портала означает этот вид цен из 1С». Пересечения нет, вызывать одно из другого не нужно.

### Точный код: `backend/apps/users/services/price_type_role.py`

```python
"""
Разрешение роли портала по виду цен из соглашения 1С.

Источник маппинга — редактируемый из админки справочник ``PriceType``
(поле ``user_role``). Обратное направление (роль → вид цен при экспорте
заказа) живёт в ``settings.ONEC_EXCHANGE["PRICE_TYPE_BY_ROLE"]`` и этим
модулем не затрагивается; согласованность двух направлений держит
тест-сторож (FR-40-13).
"""

from __future__ import annotations

from typing import Mapping, NamedTuple

from apps.products.models import PriceType

# Значение реквизита СоглашениеСтатус, которым 1С сообщает об отсутствии
# действующего соглашения (вторая редакция патча расширения БУС).
AGREEMENT_STATUS_NONE = "НетСоглашения"

REASON_RESOLVED = "resolved"
REASON_NO_DATA = "no_data"
REASON_NO_AGREEMENT = "no_agreement"
REASON_UNKNOWN = "unknown_price_type"
REASON_AMBIGUOUS = "ambiguous"


class RoleResolution(NamedTuple):
    """Результат разрешения роли. ``role is None`` → роль не менять."""

    role: str | None
    reason: str
    matched: list[str]


def load_price_type_role_map() -> dict[str, str]:
    """
    Читает справочник видов цен одним запросом.

    Вызывается один раз на сессию импорта, результат передаётся в
    ``resolve_role_from_price_types`` параметром ``role_map``.

    Кэшировать результат на уровне модуля или через ``lru_cache``
    ЗАПРЕЩЕНО: маппинг правится менеджером из админки, а Celery-воркер
    живёт долго и продолжил бы отдавать отменённое значение.
    """
    rows = PriceType.objects.filter(is_active=True).exclude(user_role="").values_list("onec_id", "user_role")
    return {str(onec_id).strip().lower(): user_role for onec_id, user_role in rows}


def resolve_role_from_price_types(
    price_type_ids: list[str],
    agreement_status: str = "",
    *,
    role_map: Mapping[str, str] | None = None,
) -> RoleResolution:
    """
    Определяет роль портала по списку GUID видов цен контрагента.

    Args:
        price_type_ids: GUID видов цен из выгрузки (уже дедуплицированы
            парсером, стори 40.1).
        agreement_status: значение реквизита СоглашениеСтатус как есть.
        role_map: готовый маппинг GUID → роль. Если не передан, читается
            из БД — по запросу на вызов.

    Returns:
        RoleResolution: ``role=None`` во всех случаях, кроме ``resolved``.
    """
    # Ветка статуса безусловно приоритетна: 1С прямо сообщила, что
    # действующего соглашения нет. Комбинация «НетСоглашения + непустой
    # GUID» второй редакцией патча не порождается; если она всё же
    # придёт, это дефект выгрузки, и молчаливо выдавать по ней роль
    # опаснее, чем не выдавать никакой.
    if agreement_status.strip().casefold() == AGREEMENT_STATUS_NONE.casefold():
        return RoleResolution(None, REASON_NO_AGREEMENT, [])

    normalized = [str(guid).strip().lower() for guid in price_type_ids if str(guid).strip()]
    if not normalized:
        return RoleResolution(None, REASON_NO_DATA, [])

    mapping = load_price_type_role_map() if role_map is None else role_map

    # Вид цен, известный порталу, но с пустым user_role (РРЦ, МРЦ), в
    # маппинг не попадает вовсе — он трактуется наравне с неизвестным
    # (решение 1 задания): иначе маркетплейсы на РРЦ уехали бы в retail.
    matched = [guid for guid in normalized if mapping.get(guid)]

    if not matched:
        return RoleResolution(None, REASON_UNKNOWN, [])

    if len(matched) > 1:
        # Два разных вида цен — два разных соглашения в 1С. Совпадение
        # ролей сегодня не делает ситуацию однозначной: маппинг
        # редактируем и может разойтись завтра.
        return RoleResolution(None, REASON_AMBIGUOUS, matched)

    return RoleResolution(mapping[matched[0]], REASON_RESOLVED, matched)
```

**Чего не делать:**
- НЕ вешать `@lru_cache` / `@cache` и не заводить модульный глобал под маппинг (AC12).
- НЕ импортировать `apps.users.models` — роль здесь строка; проверка «роль входит в `B2B_ROLES`» относится к 40.5, применение роли — к 40.4.
- НЕ проверять форму GUID регуляркой: значение приходит из 1С как есть, фильтр по форме молча съест данные при изменении формата.
- НЕ логировать в этом модуле — вызывается тысячи раз за прогон; логи и счётчики причин заводит вызывающий (40.4).

### Точный код: миграция `0054_price_type_user_role.py`

```python
# Справочник видов цен: роль портала для оптовых видов цен и «Тренерской»

from django.conf import settings
from django.db import migrations

# Роли, у которых на портале есть собственный вид цен.
# Исключены намеренно:
#   retail, admin      — оба отображаются на «РРЦ»; user_role у РРЦ обязан
#                        остаться пустым, иначе контрагенты-маркетплейсы на
#                        этом виде цен уедут в retail (решение 1 задания);
#   federation_rep     — вид цен «Партнер» на портал не выгружается, записи
#                        PriceType не имеет; роль остаётся ручной.
ROLES_WITH_PRICE_TYPE = (
    "wholesale_level1",
    "wholesale_level2",
    "wholesale_level3",
    "wholesale_level4",
    "trainer",
)

# GUID «Опт 4»: роль этой записи выставила миграция 0053 вместе с самой
# записью, поэтому reverse здесь её не гасит.
OPT4_ONEC_ID = "4c1962d2-f8ed-11eb-81f3-00155d3cae02"


def _targets():
    """[(guid, onec_name, role)] по настройкам ONEC_EXCHANGE."""
    cfg = getattr(settings, "ONEC_EXCHANGE", {})
    by_role = cfg.get("PRICE_TYPE_BY_ROLE", {})
    id_by_name = cfg.get("PRICE_TYPE_ID_BY_NAME", {})

    targets = []
    for role in ROLES_WITH_PRICE_TYPE:
        onec_name = by_role.get(role)
        if not onec_name:
            continue
        guid = str(id_by_name.get(onec_name, "")).strip().lower()
        targets.append((guid, onec_name, role))
    return targets


def set_user_roles(apps, schema_editor):
    """
    Проставляет user_role оптовым видам цен и «Тренерской».

    Обновляются только записи с ПУСТЫМ user_role: поле редактируется
    менеджером из админки, и слепой update() затёр бы ручную настройку.
    Отсутствующие записи НЕ создаются — справочник наполняет импорт
    priceLists из 1С.
    """
    PriceType = apps.get_model("products", "PriceType")

    for guid, onec_name, role in _targets():
        # Основной ключ поиска — GUID: наименование вида цен в 1С могут
        # переименовать, и запись в БД разойдётся с настройками.
        qs = PriceType.objects.filter(onec_id__iexact=guid) if guid else PriceType.objects.none()
        if not qs.exists():
            qs = PriceType.objects.filter(onec_name=onec_name)
        qs.filter(user_role="").update(user_role=role)


def clear_user_roles(apps, schema_editor):
    """Гасит только то, что проставила эта миграция."""
    PriceType = apps.get_model("products", "PriceType")

    for guid, onec_name, role in _targets():
        if guid == OPT4_ONEC_ID:
            continue
        qs = PriceType.objects.filter(onec_id__iexact=guid) if guid else PriceType.objects.none()
        if not qs.exists():
            qs = PriceType.objects.filter(onec_name=onec_name)
        qs.filter(user_role=role).update(user_role="")


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0053_seed_price_type_opt4"),
    ]

    operations = [
        migrations.RunPython(set_user_roles, reverse_code=clear_user_roles),
    ]
```

### Миграция — no-op на чистой БД, и это нормально

Записи `PriceType` **ни одной миграцией не засеиваются** (кроме «Опт 4» в `0053`): справочник наполняет импорт `priceLists` из 1С — `VariantImportProcessor.process_price_types` (`apps/products/services/variant_import.py:1534`). Отсюда:

- на **проде** записи есть (шесть исходных + «Опт 4»), миграция отработает по существующим строкам;
- на **чистой dev-БД** без импорта таблица пуста, миграция ничего не сделает — не дефект. Тест 5.6 фиксирует это как ожидаемое поведение;
- в **тестах** полагаться на данные, засеянные миграциями, нельзя вообще: `--nomigrations` + autouse-фикстура `TRUNCATE CASCADE` (`backend/CLAUDE.md`). Отсюда паттерн «создать записи руками → вызвать функцию миграции напрямую».

### Мина, которую НЕ надо чинить, но надо знать

`process_price_types` (`variant_import.py:1552-1569`) кладёт в `defaults` только `onec_name`, `is_active` и (при непустом значении) `product_field`. **`user_role` в `defaults` отсутствует — импорт `priceLists` роль не затирает.** Это уже правильно; трогать не нужно.

А вот `apps/products/management/commands/clear_catalog.py:48` делает `PriceType.objects.all().delete()` — после такой чистки маппинг ролей исчезает целиком, и (начиная с 40.4) роли молча перестанут обновляться: всё уедет в `unknown_price_type`. **В объём 40.2 это не входит** — зафиксировать наблюдение в Completion Notes, чинить в рамках эпика не нужно.

### Точный код: форма и админка

`backend/apps/products/forms.py` — добавить в конец:

```python
class PriceTypeAdminForm(forms.ModelForm):
    """
    Форма справочника видов цен.

    user_role ограничен списком существующих ролей: свободный текст
    позволил бы опечатку («wholesale_level_2»), которую импорт (стори
    40.4) записал бы живому аккаунту без единой ошибки.
    """

    class Meta:
        model = PriceType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.users.models import User

        self.fields["user_role"] = forms.ChoiceField(
            choices=[("", "— роль не назначается —"), *User.ROLE_CHOICES],
            required=False,
            label="Роль пользователя",
            help_text=(
                "Роль портала, которую получит клиент на этом виде цен. "
                "У «РРЦ» и «МРЦ» поле обязано остаться пустым."
            ),
        )
```

Импорт `User` — локальный, внутри `__init__`: `forms.py` импортируется из `admin.py` на старте приложения, а модель пользователя тянуть на уровне модуля в приложении `products` не нужно. `PriceType` добавить в существующий `from .models import Attribute, Brand`.

`backend/apps/products/admin.py` — после `ColorMappingAdmin` (`admin.py:577`):

```python
@admin.register(PriceType)
class PriceTypeAdmin(admin.ModelAdmin):
    """Справочник видов цен 1С: поле товара и роль портала."""

    form = PriceTypeAdminForm
    list_display = ("onec_name", "onec_id", "product_field", "user_role", "is_active")
    list_filter = ("is_active",)
    search_fields = ("onec_name", "onec_id")
    readonly_fields = ("created_at",)
    ordering = ("onec_name",)
```

### Мина: `list_editable` обходит `form`

Соблазн добавить `list_editable = ("user_role",)` — редактирование маппинга прямо в списке выглядит удобнее. **Не добавлять.** `ModelAdmin.get_changelist_form` строит форму списка через `modelform_factory(self.model, ...)` и `self.form` **не использует**: в changelist `user_role` вернулся бы свободным текстовым полем, и AC4 был бы обойдён в самом частом сценарии работы менеджера. Редактирование через форму объекта AC3 полностью удовлетворяет.

### Порядок ветвления резолвера — фиксирован ACs, менять нельзя

| Вход | `reason` | Кто это потребляет дальше |
|---|---|---|
| `agreement_status == "НетСоглашения"` | `no_agreement` | 40.3 **гасит** `onec_price_type_id`; 40.4 считает `roles_skipped_no_agreement` |
| GUID нет и статуса нет | `no_data` | 40.3 **не гасит** сохранённое значение (это признак поломки выгрузки); 40.4 считает `roles_skipped_no_data` |
| GUID есть, роли нет ни у одного | `unknown_price_type` | 40.4 считает `roles_skipped_unknown_price_type` |
| Роль у двух и более GUID | `ambiguous` | 40.4 считает `roles_skipped_ambiguous` |
| Роль ровно у одного GUID | `resolved` | 40.4 применяет роль привязанным аккаунтам, 40.5 — при привязке |

Различие `no_agreement` / `no_data` — не косметика: в 40.3 они дают **противоположные** действия с сохранённым видом цен. Схлопывание их в одну причину сломает следующую стори.

### Тестирование: как запускать

`make` на машине недоступен, а таргеты `test-*` ищут несуществующий `docker/.env`.

⚠️ **В worktree `FREESPORT-40-2` нет файла `.env`** (в `.gitignore`), а compose-файлы монтируют `../backend` относительно каталога `docker/`. Чтобы прогон шёл по коду **этой** ветки:

```bash
cp /c/Users/1/DEV/FREESPORT/.env /c/Users/1/DEV/FREESPORT-40-2/.env
cd /c/Users/1/DEV/FREESPORT-40-2/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q tests/unit/test_services/test_price_type_role.py \
            tests/unit/test_migration_price_type_user_role.py \
            tests/unit/test_admin/test_products_admin.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down
```

`container_name` в `docker-compose.test.yml` зашит жёстко (`freesport-backend-test` и др.) — параллельно поднятый тест-стек из основного репозитория даст конфликт имён. Перед прогоном убедиться, что чужой тест-стек погашен.

Линтеры — в dev-контейнере из корня worktree:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black apps/users/services/price_type_role.py apps/products/admin.py apps/products/forms.py \
        apps/products/migrations/0054_price_type_user_role.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend flake8 apps/users/ apps/products/
```

Маркеры `unit`/`integration` проставляются **автоматически по каталогу** теста (`backend/conftest.py`). Все тесты этой стори лежат в `tests/unit/` → маркер `unit`. `@pytest.mark.data_dependent` здесь не нужен: реальных XML стори не читает.

### Blast radius (обязательный pre-flight выполнен)

Индекс GitNexus живёт в основном репозитории `C:\Users\1\DEV\FREESPORT` (worktree `FREESPORT-40-2` не проиндексирован), коммит индекса `c549b04` совпадает с HEAD ветки — данные актуальны. Команды выполнять из `/c/Users/1/DEV/FREESPORT`.

```
npx gitnexus impact PriceType       --direction upstream → risk: CRITICAL, impacted: 63, direct: 36
npx gitnexus impact _get_price_type --direction upstream → risk: LOW, impacted: 3
```

**Предупреждение о CRITICAL и почему он здесь не срабатывает:** 63 зависимости `PriceType` — это импорты класса (views, tasks, signals, сериализаторы, `variant_import`). Стори **не меняет модель**: ни полей, ни `Meta`, ни `choices`. Изменяются только *данные* в колонке `user_role`, которую до этой стори **никто не читал** (подтверждено: единственное упоминание вне миграций — объявление поля в `models.py:740`). Реальный blast radius — нулевой. Если по ходу работы возникнет соблазн изменить само поле (например добавить `choices`), это выводит правку в зону CRITICAL — остановиться и согласовать с Alex (Task 1.6 запрещает такую правку).

`_get_price_type` (`order_export.py:550`) читается только сторожем, код не меняется (AC14).

### Границы стори (что делают соседние стори — здесь НЕ делать)

- **40.1** (параллельно) — парсер `<ЗначенияРеквизитов>`, `price_type_ids` / `price_type_meta` / `agreement_status`, детектор регресса выгрузки. Файлы `apps/users/services/parser.py`, `processor.py`, `import_customers_from_1c.py` в 40.2 **не трогаются вовсе** — конфликтов при параллельной работе не будет.
- **40.3** — поле `User.onec_price_type_id`, запись вида цен, отображение в карточке пользователя. Миграций `users` здесь нет.
- **40.4** — вызов резолвера из `processor.py`, применение роли, `AuditLog`, счётчики `roles_*`. В 40.2 у резолвера **нет ни одного вызывающего** — это нормально и ожидаемо.
- **40.5** — перенос вида цен при привязке заявки.

Экспорт заказа не меняется (AC14). API-контракт не меняется: `docs/api/openapi.yaml` и типы фронта не трогаются, `npm run generate:types` не запускается. Frontend не затрагивается.

### Project Structure Notes

| Файл | Статус | Что |
|---|---|---|
| `backend/apps/users/services/price_type_role.py` | **NEW** | `RoleResolution`, `load_price_type_role_map`, `resolve_role_from_price_types` |
| `backend/apps/products/migrations/0054_price_type_user_role.py` | **NEW** | Data-миграция заполнения `user_role` |
| `backend/apps/products/forms.py` | UPDATE | `PriceTypeAdminForm` + `PriceType` в импорт моделей |
| `backend/apps/products/admin.py` | UPDATE | `PriceTypeAdmin` + `PriceType` в импорт из `.models` |
| `backend/tests/unit/test_services/test_price_type_role.py` | **NEW** | Резолвер + сторож FR-40-13 |
| `backend/tests/unit/test_migration_price_type_user_role.py` | **NEW** | Миграция: заполнение, идемпотентность, reverse, no-op |
| `backend/tests/unit/test_admin/test_products_admin.py` | UPDATE | Класс `TestPriceTypeAdmin` |

Схемных миграций нет — модель `PriceType` не меняется (Task 6.3 это доказывает). Новых зависимостей нет: `NamedTuple` — стандартная библиотека, `requirements.txt` не трогается.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 40.2`] — AC в BDD-форме, FR-40-02, FR-40-03, FR-40-04, FR-40-13, NFR-3940-09
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic 40`] — порядок стори, независимость 40.1 и 40.2, точки промежуточного выката
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` §2.3, §2.5, §4, §8 C2, §8 C6, §9] — таблица видов цен с GUID, состояние `PriceType.user_role`, решения 1/2/3/5, сигнатура резолвера, сторож согласованности
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-bus-agreement-status.md` §7] — `no_agreement` как отдельная причина, отличная от `no_data`
- [Source: `_bmad-output/implementation-artifacts/Story/39-1-wholesale-level4-role-and-opt4-price-model.md`] — миграция `0053`, роль `wholesale_level4`, образец идемпотентной data-миграции по `PriceType`
- [Source: `_bmad-output/implementation-artifacts/Story/40-1-parser-price-type-and-export-regression-detector.md`] — формат блока `<ЗначенияРеквизитов>`, дедупликация GUID в парсере, распределение GUID по контрагентам (42 маркетплейса на РРЦ)
- [Source: `project-context.md` §3, §4, §6] — role-based pricing, автоматическая разметка маркеров, покрытие, русский язык комментариев
- [Source: `backend/CLAUDE.md`] — изоляция тестов: `--nomigrations` + `TRUNCATE CASCADE`, отсюда прямой вызов функций миграции в тестах
- [Source: `backend/docs/testing-standards.md`] — стандарты тестирования, маркеры pytest

## Dev Agent Record

### Agent Model Used

claude-opus-5 (Claude Code, dev-story workflow)

### Debug Log References

Прогоны в тест-контейнере из `docker/` этой ветки (`docker compose -f docker-compose.test.yml run --rm -T backend ...`):

| Прогон | Результат |
|---|---|
| Новые тесты 40.2 (резолвер + миграция + админка) | 55 passed |
| RED-проверка AC4: `ChoiceField` временно отключён | 3 failed (`test_form_limits_user_role_to_choice_field`, `test_form_offers_empty_choice`, `test_form_rejects_typo_in_role`), затем восстановлено |
| `manage.py makemigrations --check --dry-run` | `No changes detected`, exit 0 |
| Регресс Task 6.2 (`test_order_export_service`, `test_settings_onec`, `test_price_logic`, `test_onec_export`) | 133 passed |
| `black` / `flake8` по изменённым файлам | `7 files left unchanged` / exit 0 |
| Полный набор `pytest -q` (без `-m`) | 2837 passed, 10 failed, 24 skipped (28:39) |
| Перепроверка 10 падений после копирования снимка 1С | 12 passed (8:30) |

**Прогон закрытия review-находок (2026-08-05, основной клон `C:\Users\1\DEV\FREESPORT`, ветка `feature/40-2-review-findings`).**
В отличие от первой итерации работа шла в основном клоне, а не в worktree, поэтому снимки 1С из `data/import_1c/` на месте
и полный набор проходит без падений импорта контрагентов.

| Прогон | Результат |
|---|---|
| RED: новые тесты до правок кода | 4 failed, 60 passed — ровно ожидаемые: 2 на коллизию GUID в резолвере, 2 на нормализацию GUID в форме |
| GREEN: `test_price_type_role.py` + `test_products_admin.py` + `test_migration_price_type_user_role.py` | 64 passed |
| Регресс: `test_order_export_service`, `test_settings_onec`, `test_price_logic`, `test_onec_export`, `test_clear_catalog` | 139 passed |
| `manage.py makemigrations --check --dry-run` | `No changes detected`, exit 0 |
| `black --check` / `flake8 apps/users/ apps/products/ tests/unit/` | 6 files unchanged / exit 0 |
| `npx gitnexus detect-changes --scope all` | risk **low**, 0 затронутых процессов, 3 символа — все в `price_type_role.py`. `_get_price_type` в списке нет |
| `git diff HEAD -- backend/apps/orders/services/order_export.py` | 0 строк — AC14 держится |
| Полный набор `pytest -q` (без `-m`, чтобы обойти пробел в маркерах) | **2938 passed, 6 skipped, 0 failed**, 19 subtests (37:53) |

**Разбор 10 падений полного прогона (первая итерация, worktree).** Все десять — в `tests/integration/test_management_commands/test_import_customers.py`,
причина одна: `CommandError: Поддиректория contragents не найдена в /app/data/import_1c`. Каталог `data` в `.gitignore`,
поэтому снимки 1С в worktree `FREESPORT-40-2` не попали. К стори отношения не имеют: 40.2 не трогает ни одного файла
импорта контрагентов. Доказано прямо: после `cp -r` каталога `contragents/` из основного клона тот же файл даёт 12 passed.
Скопированный снимок оставлен в worktree (он gitignored и в коммит не попадёт).

### Completion Notes List

**Что реализовано**

- **AC1-AC2** — data-миграция `products/0054_price_type_user_role.py`. Пять ролей (`wholesale_level1…4`, `trainer`)
  получают `user_role`; «РРЦ» и «МРЦ» остаются пустыми. Поиск записи по `onec_id__iexact`, при промахе — по `onec_name`.
  Обновляются только записи с `user_role == ""`, поэтому ручная правка менеджера не затирается. `reverse` гасит только
  роли, совпадающие с ожидаемыми, и пропускает GUID «Опт 4» (его роль поставила `0053`).
- **AC3-AC4** — `PriceTypeAdmin` в `apps/products/admin.py` и `PriceTypeAdminForm` в `apps/products/forms.py`.
  `user_role` — `ChoiceField` из `User.ROLE_CHOICES` плюс пустой вариант. `list_editable` намеренно не задан.
- **AC5-AC12** — модуль `apps/users/services/price_type_role.py`: `RoleResolution`, `load_price_type_role_map`,
  `resolve_role_from_price_types`. Порядок ветвления `no_agreement → no_data → unknown_price_type / ambiguous / resolved`.
  Кэша нет ни в каком виде — проверяется тестом на `cache_clear` и на числе SQL-запросов.
- **AC13** — сторож согласованности в `TestForwardBackwardMappingConsistency`: посев справочника из настроек с пустой
  ролью, прогон `set_user_roles`, затем round-trip `PRICE_TYPE_BY_ROLE → PRICE_TYPE_ID_BY_NAME → PriceType.user_role`.
- **AC14** — `order_export.py` не изменён (`git diff` по файлу пуст), `test_order_export_service.py` зелёный.
- **AC15** — покрыты все четыре `reason`, AC9, однократность чтения справочника, идемпотентность и обратимость миграции,
  состав `PriceTypeAdmin` и сторож. Маркер `unit` проставился автоматически по каталогу.

**Отклонение от Dev Notes (важно для 40.3-40.5).** Dev Notes утверждали, что тестовая БД строится с `--nomigrations` и
данные миграций в тестах не видны. Это верно только для таргетов `make`, которых на машине нет: в `backend/pytest.ini`
нет `addopts`, поэтому прямой прогон в тест-контейнере строит БД **с миграциями**, и запись «Опт 4» из `0053` уже лежит
в `price_types`. Первый прогон дал 12 падений именно по этой причине (`duplicate key ... price_types_onec_id_key`).
Решено autouse-фикстурой `clean_price_types`, чистящей справочник в начале каждого теста, — тесты теперь не зависят от
способа сборки БД. Автоочистка в `tests/conftest.py` `PriceType` не покрывает (модели нет в списке `model_order`),
расширять её в рамках 40.2 не стал: это общий инструмент, правка тянет за собой регресс всего набора.

**Наблюдение вне объёма стори — по решению Alex исправлено отдельным коммитом `70089a92`.**
`apps/products/management/commands/clear_catalog.py:48` делал `PriceType.objects.all().delete()`. После такой чистки
маппинг ролей исчезал целиком, и начиная с 40.4 роли молча перестали бы обновляться — всё уехало бы в
`unknown_price_type`. Удаление убрано, добавлены регресс-тесты команды (`apps/products/tests/unit/test_clear_catalog.py`,
6 тестов, у команды не было ни одного), из `docs/deploy/LOCAL_DOCKER_SETUP.md` убрана рекомендация нерабочей обёртки
`scripts/inport_from_1C/clear_catalog.ps1`. Коммит не входит в объём 40.2 и не пересекается с её файлами.
В `deferred-work.md` записаны два следствия: канарейка на пустой маппинг для стори 40.4 и разбор сломанного `.ps1`.

**Закрытие review-находок (2026-08-05).** Обе находки были помечены `[Defer]` предыдущей сессией и выполнены здесь.

✅ Resolved review finding [Med]: **Case-colliding GUID дают произвольную роль.** Решение Alex — «загрузчик + нормализация
в форме», обе половины сделаны.
- `load_price_type_role_map()` собирает маппинг в цикле по той же единственной выборке и запоминает ключи, у которых
  регистровые двойники несут **разные** роли; такие GUID выбрасываются из маппинга целиком. Резолвер отвечает по ним
  `unknown_price_type` — то есть роль молча не применяется, вместо того чтобы выдать произвольную. Одинаковая роль у
  двойников конфликтом не считается: какой бы записью GUID ни разрешился, ответ один. AC12 не нарушен — запрос
  по-прежнему ровно один (доказано `django_assert_num_queries(1)` на данных с коллизией).
- `PriceTypeAdminForm.clean_onec_id()` приводит GUID к нижнему регистру и отвергает ввод, если запись с тем же GUID в
  другом регистре уже существует (`onec_id__iexact`, с исключением самой редактируемой записи по `pk`).
- Существующие данные **не** нормализуются: data-миграция `UPDATE onec_id = lower(onec_id)` упала бы на
  `UniqueViolation`, если коллизия в БД уже есть, а защита в загрузчике делает такую нормализацию необязательной.
- Тестов добавлено 8: 4 в `test_price_type_role.py` (конфликт гасит только свой GUID, одинаковая роль по-прежнему
  разрешается, однократность запроса), 4 в `test_products_admin.py` (нижний регистр, обрезка пробелов, отказ двойнику,
  повторное сохранение той же записи).

✅ Resolved review finding [Low]: **Reverse-миграция не различает роль миграции и такую же ручную роль.** Решение Alex —
«явно ослабить контракт». Поведение `clear_user_roles()` не менялось; ограничение зафиксировано в docstring функции и
характеризующим тестом `test_clears_manual_role_that_matches_expected_value`. Обоснование: происхождение значения хранить
негде — поля-маркера у `PriceType` нет, заводить его означало бы схемную миграцию, прямо запрещённую Task 1.6. Цена
ошибки мала: reverse запускается только при откате на `0053`, а повторное применение `0054` вернёт то же значение. Роль,
**отличную** от ожидаемой, reverse по-прежнему не трогает (`test_does_not_touch_manual_role`).

⚠️ **Расхождение с буквой AC2.** AC2 обещает, что `reverse` очищает `user_role` только у записей, которые заполнила эта
миграция. Принятое решение это обещание осознанно ослабляет: без хранения происхождения отличить «поставила миграция» от
«менеджер выставил ровно то же самое» невозможно. Текст AC не правился (раздел вне зоны правок dev-агента) — расхождение
зафиксировано здесь и в docstring миграции для ревьюера.

Две записи, заведённые предыдущей сессией в `deferred-work.md` под эти находки, удалены: работа выполнена, отложенной
больше нет.

**GitNexus (закрытие находок).** `impact load_price_type_role_map --direction upstream` → `risk: LOW`, 1 вызывающий
(`resolve_role_from_price_types`); `impact PriceTypeAdminForm --direction upstream` → `risk: LOW`, 1 импорт (`admin.py`);
`clear_user_roles` в графе нет — функции миграций не индексируются. `detect-changes --scope all` в основном клоне
отработал штатно (в отличие от worktree первой итерации): `risk: low`, 0 затронутых процессов, 3 символа, все в
`price_type_role.py`; `_get_price_type` в списке отсутствует.

**GitNexus (первая итерация).** `impact PriceType --direction upstream` → `risk: CRITICAL`, 63 зависимости, 36 прямых — предупреждение
выдано пользователю до правок. Все 63 — импорты класса; модель не менялась (доказано `makemigrations --check`), меняются
только данные в колонке `user_role`, которую до этой стори никто не читал. Реальный blast radius нулевой.
`detect-changes --scope all` в worktree отработать не может: индекс GitNexus лежит только в основном клоне
(`C:\Users\1\DEV\FREESPORT\.gitnexus`), в worktree его нет, и команда возвращает `No changes detected` независимо от
содержимого рабочей копии. Вместо неё выполнена ручная проверка объёма правок по `git status` / `git diff --stat`:
затронуты ровно четыре файла кода и три тестовых, `apps/orders/services/order_export.py` — ноль строк диффа.

### File List

- `backend/apps/products/migrations/0054_price_type_user_role.py` — **NEW**
- `backend/apps/users/services/price_type_role.py` — **NEW**
- `backend/tests/unit/test_services/test_price_type_role.py` — **NEW**
- `backend/tests/unit/test_migration_price_type_user_role.py` — **NEW**
- `backend/apps/products/admin.py` — UPDATE (`PriceTypeAdmin`, импорты `PriceType` и `PriceTypeAdminForm`)
- `backend/apps/products/forms.py` — UPDATE (`PriceTypeAdminForm`, импорт `PriceType`)
- `backend/tests/unit/test_admin/test_products_admin.py` — UPDATE (класс `TestPriceTypeAdmin`, импорты)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — UPDATE (статус стори)
- `_bmad-output/implementation-artifacts/Story/40-2-price-type-role-mapping-and-resolver.md` — UPDATE (этот файл)

Закрытие review-находок (2026-08-05) — изменены дополнительно:

- `backend/apps/users/services/price_type_role.py` — UPDATE (`load_price_type_role_map`: выявление регистровых коллизий GUID)
- `backend/apps/products/forms.py` — UPDATE (`PriceTypeAdminForm.clean_onec_id`)
- `backend/apps/products/migrations/0054_price_type_user_role.py` — UPDATE (docstring `clear_user_roles`: ослабленный контракт reverse)
- `backend/tests/unit/test_services/test_price_type_role.py` — UPDATE (класс `TestGuidCaseCollisions`, 4 теста)
- `backend/tests/unit/test_admin/test_products_admin.py` — UPDATE (4 теста нормализации GUID, хелперы `_form_data`/`_create_price_type`)
- `backend/tests/unit/test_migration_price_type_user_role.py` — UPDATE (`test_clears_manual_role_that_matches_expected_value`)
- `_bmad-output/implementation-artifacts/deferred-work.md` — UPDATE (удалён раздел «Deferred from: code review of story 40.2» — работа выполнена)

## Change Log

| Дата | Изменение |
|---|---|
| 2026-08-05 | Закрыты обе review-находки (2 items resolved): защита от регистровых коллизий GUID в `load_price_type_role_map()` + нормализация `onec_id` в `PriceTypeAdminForm`; контракт обратимости `0054` явно ослаблен в docstring и зафиксирован тестом. Тестов добавлено 9, всего по стори 64. Схемных миграций не добавлено (`makemigrations --check` чист). Статус: `in-progress` → `review`. |
| 2026-08-04 | Реализована стори 40.2: data-миграция `0054` заполняет `PriceType.user_role`, справочник видов цен заведён в админку с ограничением роли по `User.ROLE_CHOICES`, добавлен модуль-резолвер `price_type_role` с пятью причинами решения и сторожем согласованности прямого/обратного маппинга. Тестов добавлено 42 (резолвер 20, миграция 12, админка 10). Статус: `ready-for-dev` → `in-progress` → `review`. |
