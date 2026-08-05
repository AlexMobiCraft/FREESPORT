---
baseline_commit: f8c905a738ab8a7f0ba507abc8f0947397a3f141
---

# Story 40.3: Портал хранит вид цен из 1С, роли не трогая

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

> ✅ **Внешних блокеров нет.** Снимок `backend/data/import_1c/contragents_pricetype/` **второй** редакции патча БУС лежит в основном клоне (10 файлов, 4735 контрагентов: 485 с `ТипЦенId`, 4250 со статусом `НетСоглашения`, без блока — ноль). Обе ветки данных, нужные этой стори, доступны.
> ⚠️ **Работать в основном клоне `C:\Users\1\DEV\FREESPORT`, не в worktree.** Каталог `backend/data/import_1c/` в `.gitignore` и в worktree отсутствует — все `data_dependent`-тесты там молча скипаются, а индекс GitNexus в worktree не существует.
> 🔒 **Роль не меняется ни в одной строке кода этой стори.** Применение роли — стори 40.4. Если по ходу работы появляется `user.role = ...`, это выход за границы стори.

## Story

As a **Ответственный за выкат эпика**,
I want **чтобы портал начал накапливать вид цен из 1С отдельным выкатом, до включения автоприменения роли**,
so that **к моменту выката 40.4 данные уже были накоплены и проверены глазами, а откат автоприменения не тянул за собой откат миграции поля**.

## Acceptance Criteria

1. **AC1 (FR-40-05, NFR-3940-06).** В модель `User` (`backend/apps/users/models.py`) добавлено поле `onec_price_type_id`: `CharField`, `max_length=100` (по образцу `PriceType.onec_id`, `products/models.py:698`), `blank=True`, `default=""`, **без** `null=True` и **без** `unique=True`. Схемная миграция `users` применена на PostgreSQL в Docker.

2. **AC2 (FR-40-05, §5 задания).** `_create_customer` (`processor.py:342`) при создании контрагента с ровно одним GUID в `price_type_ids` записывает его в `onec_price_type_id`. Роль нового контрагента остаётся `IMPORTED_CUSTOMER_ROLE` (`unregistered`) независимо от вида цен.

3. **AC3 (FR-40-05).** `_update_customer` (`processor.py:393`) записывает `onec_price_type_id` **всегда** — и привязанным аккаунтам, и непривязанным записям 1С, независимо от того, известен ли GUID справочнику `PriceType` и несёт ли он роль. Условия «роль применима» здесь нет вовсе.

4. **AC4 (FR-40-05).** Контрагент со статусом `agreement_status == "НетСоглашения"`: `onec_price_type_id` **гасится** в `""`, даже если ранее было сохранено значение. 1С подтвердила снятие соглашения; без гашения привязка (40.5) выдала бы роль по соглашению, снятому месяцы назад, без единой ошибки в логах.

5. **AC5 (FR-40-05, FR-40-10).** Контрагент без блока `<ЗначенияРеквизитов>` (`price_type_ids == []` **и** `agreement_status == ""`): ранее сохранённое `onec_price_type_id` **не затирается**. После второй редакции патча блок обязан приходить у каждого контрагента, поэтому его отсутствие означает поломку выгрузки, а не снятое соглашение; обнуление уничтожило бы данные у всех разом.

6. **AC6 (FR-40-05, следствие правила `ambiguous` из 40.2).** Контрагент с **двумя и более различными** GUID в `price_type_ids`: `onec_price_type_id` **не изменяется** (ни записи, ни гашения). Хранить один GUID из двух нельзя: стори 40.5 разрешает роль по единственному сохранённому значению (`resolve_role_from_price_types([onec_price_type_id])`) и выдала бы роль там, где резолвер обязан ответить `ambiguous`. На текущем снимке таких контрагентов ноль — правило защищает инвариант «сохранённый GUID однозначен», а не исправляет наблюдаемый дефект.

7. **AC7 (FR-40-06).** Карточка пользователя в админке (`backend/apps/users/admin.py`, блок «Интеграция с 1С», `admin.py:257-273`) показывает `onec_price_type_id` и человекочитаемое наименование вида цен. Оба поля **readonly**: значение приходит из 1С, ручная правка разошлась бы с ближайшим импортом.

8. **AC8 (FR-40-06).** Если `onec_price_type_id` пуст **или** GUID отсутствует в справочнике `PriceType`, наименование отображается как `—`, страница открывается без исключения. Сравнение GUID со справочником — регистронезависимое (`onec_id__iexact`): в 40.2 выяснилось, что регистр `onec_id` в справочнике не нормализован.

9. **AC9 (NFR-3940-08, идемпотентность).** Повторный прогон той же выгрузки не меняет `onec_price_type_id` и не создаёт лишних записей `CustomerSyncLog`. Записей `AuditLog` эта стори не создаёт вовсе — журналирование смены роли заводит 40.4.

10. **AC10 (FR-40-05, предохранитель выката).** После прогона импорта контрольной выгрузки роли всех записей не изменились по сравнению с состоянием до прогона. Доказывается тестом: снимок `role` до и после `call_command`, посимвольное сравнение. Стори выкатывается самостоятельно и поведение портала для пользователей не меняет.

11. **AC11 (NFR-3940-01, -02, -03).** Тесты используют реальные XML из `backend/data/import_1c/contragents_pricetype/` (ветки «GUID есть» и `НетСоглашения`) и `contragents/` (ветка «блока нет»). Синтетические XML запрещены. Покрыты: запись при создании, запись при обновлении, гашение при `no_agreement`, отсутствие затирания при `no_data`, неизменность при двух GUID, отображение наименования и `—` в админке, неизменность ролей. Маркеры проставляются автоматически по каталогу; `@pytest.mark.data_dependent` ставится вручную.

12. **AC12 (граница стори).** Файлы `apps/users/services/price_type_role.py`, `apps/users/services/link_1c_customer.py`, `apps/products/**` и `apps/users/serializers.py` **не изменены**. Поле `onec_price_type_id` не появляется ни в одном сериализаторе, `docs/api/openapi.yaml` и типы фронта не трогаются (NFR-3940-07 к эпику 40 неприменим).

## Tasks / Subtasks

- [ ] **Task 1: Поле модели и миграция** (AC: 1, 12)
  - [ ] 1.1: Добавить `onec_price_type_id` в `User` (`backend/apps/users/models.py`) сразу **после** `onec_guid` (`models.py:280-286`) — точный код в Dev Notes. Комментарии и `help_text` на русском
  - [ ] 1.2: Создать схемную миграцию: `python manage.py makemigrations users --name add_user_onec_price_type_id` → ожидаемое имя `apps/users/migrations/0021_add_user_onec_price_type_id.py`, зависимость `("users", "0020_add_wholesale_level4_role")`
  - [ ] 1.3: Применить миграцию в Docker на PostgreSQL, убедиться, что `makemigrations --check --dry-run` после этого чист
  - [ ] 1.4: НЕ добавлять `null=True` — у `CharField` это дало бы третье состояние «NULL vs пустая строка» при одинаковом смысле; `""` — единственное «значения нет» (см. Dev Notes → «Почему не null и не unique»)
  - [ ] 1.5: НЕ добавлять поле в `UserSerializer` и прочие сериализаторы (`apps/users/serializers.py`) — AC12. В `apps/users/serializers.py` все `Meta.fields` заданы явными списками, поэтому поле не протечёт само; проверить это глазами, а не полагаться на догадку

- [ ] **Task 2: Запись вида цен в процессоре** (AC: 2, 3, 4, 5, 6, 9)
  - [ ] 2.1: Добавить в `CustomerDataProcessor` приватный метод `_price_type_id_to_store(customer_data, current) -> str` (полный код — в Dev Notes). Разместить рядом с `_normalize_phone` (`processor.py:302`)
  - [ ] 2.2: Импортировать `AGREEMENT_STATUS_NONE` из `apps.users.services.price_type_role` (модульный импорт безопасен — цикла нет, см. Dev Notes → «Импорт константы»). Литерал `"НетСоглашения"` в `processor.py` **не дублировать**
  - [ ] 2.3: В `_create_customer` (`processor.py:371-383`) добавить `onec_price_type_id=self._price_type_id_to_store(customer_data, "")` в вызов `User.objects.create(...)`
  - [ ] 2.4: В `_update_customer` (перед `user.save()`, `processor.py:419-422`) добавить `user.onec_price_type_id = self._price_type_id_to_store(customer_data, user.onec_price_type_id)`
  - [ ] 2.5: Роль **не трогать**: `_update_customer` по-прежнему не присваивает `user.role`, `role_preserved: True` в `_log_operation` (`processor.py:141-142`) остаётся как есть — его снимает стори 40.4
  - [ ] 2.6: НЕ вызывать `resolve_role_from_price_types` и НЕ читать справочник `PriceType` из процессора — см. Dev Notes → «Почему резолвер здесь не нужен»
  - [ ] 2.7: НЕ добавлять счётчики `roles_*` в `stats` — это 40.4. Счётчики `attributes_block_present` / `attributes_block_missing` из 40.1 не менять
  - [ ] 2.8: Обновить docstring `_update_customer` (`processor.py:394-406`): роль по-прежнему не обновляется, а вид цен — обновляется всегда

- [ ] **Task 3: Отображение вида цен в админке** (AC: 7, 8)
  - [ ] 3.1: Добавить display-метод `onec_price_type_name` в `UserAdmin` (`backend/apps/users/admin.py`) рядом с `onec_link_candidates` (`admin.py:357`) — точный код в Dev Notes. Импорт `PriceType` — **локальный, внутри метода**
  - [ ] 3.2: Добавить `"onec_price_type_id"` и `"onec_price_type_name"` в `readonly_fields` (`admin.py:196-205`), после `"onec_guid"`
  - [ ] 3.3: Добавить оба поля в fieldset «Интеграция с 1С» (`admin.py:257-273`), после `"onec_guid"` и **до** `"onec_link_candidates"`
  - [ ] 3.4: НЕ добавлять поля в `list_display` и `search_fields` — GUID в списке пользователей не читаем и не ищется; `test_search_fields` (`tests/unit/test_users_admin.py:111`) сверяет список точным равенством и покраснеет
  - [ ] 3.5: НЕ трогать `get_fieldsets` (`admin.py:333`) — он вырезает только `onec_link_candidates`, новые поля проходят насквозь

- [ ] **Task 4: Тесты процессора** (AC: 2, 3, 4, 5, 6, 9, 11)
  - [ ] 4.1: Дописать класс `TestCustomerPriceTypeStorage` в `backend/tests/unit/test_services/test_customer_processor.py` с декораторами `@pytest.mark.django_db`. ⚠️ Фикстуры `session` и `processor` объявлены **методами класса** `TestCustomerDataProcessor` (`test_customer_processor.py:26-38`), а не на уровне модуля — новому классу они не видны. Продублировать их в новом классе (4 строки) либо вынести на уровень модуля; второй вариант затрагивает существующий класс, поэтому предпочтителен первый
  - [ ] 4.2: Тест AC2: создание контрагента с одним GUID → `onec_price_type_id == guid`, `role == "unregistered"`
  - [ ] 4.3: Тест AC3: обновление существующей записи → GUID записан; отдельный случай — **привязанный** аккаунт (`created_in_1c=False` или роль не `unregistered`) тоже получает GUID
  - [ ] 4.4: Тест AC3 (GUID вне справочника): GUID, которого нет в `PriceType`, всё равно записан — справочник процессором не читается
  - [ ] 4.5: Тест AC4: у записи было значение, приходит `agreement_status="НетСоглашения"` → поле стало `""`
  - [ ] 4.6: Тест AC5: у записи было значение, приходит `price_type_ids=[]` и `agreement_status=""` → значение сохранилось
  - [ ] 4.7: Тест AC6: два разных GUID → значение не изменилось (проверить оба случая: было пусто → осталось пусто; было значение → осталось прежним)
  - [ ] 4.8: Тест AC9: два прогона `process_customer` на одних данных → значение то же, число `CustomerSyncLog` выросло ровно на ожидаемое (по одной записи на прогон), `AuditLog` не создан
  - [ ] 4.9: Данные для тестов этого класса собираются из **реальной выгрузки** через `CustomerDataParser` (фикстуры — в Dev Notes → «Откуда брать данные в unit-тестах»), а не из вручную набранных словарей с выдуманными GUID

- [ ] **Task 5: Тест админки** (AC: 7, 8, 11)
  - [ ] 5.1: Дописать тесты в `backend/tests/unit/test_users_admin.py`, класс `TestUserAdmin` или новый `TestUserAdminPriceType` (файл на `TestCase` + `pytestmark = pytest.mark.unit`)
  - [ ] 5.2: Тест AC7: `onec_price_type_id` и `onec_price_type_name` присутствуют в fieldset «Интеграция с 1С» и в `readonly_fields`
  - [ ] 5.3: Тест AC8: пользователь с GUID, для которого создана запись `PriceType` → метод возвращает `onec_name`; пустой GUID → `—`; GUID вне справочника → `—`; GUID в другом регистре, чем в справочнике → `onec_name` (регистронезависимость)
  - [ ] 5.4: ⚠️ **Обновить существующий `test_readonly_fields`** (`tests/unit/test_users_admin.py:124-136`): он сверяет `readonly_fields` **точным равенством списка** и упадёт от Task 3.2. Это ожидаемая правка теста, а не поломка — см. Dev Notes → «Мина: тесты со строгим равенством»
  - [ ] 5.5: `test_fieldsets_structure` (`test_users_admin.py:512`) проверяет только число секций (6) и их названия — правки не требует; убедиться прогоном

- [ ] **Task 6: Интеграционный тест на реальной выгрузке** (AC: 10, 11)
  - [ ] 6.1: Создать `backend/tests/integration/test_import_customers_price_type.py`, маркеры: каталог даёт `integration` автоматически, добавить `@pytest.mark.data_dependent` и `@pytest.mark.django_db`
  - [ ] 6.2: Тест AC10: прогнать `call_command("import_customers_from_1c", data_dir=<tmp>)` **дважды**; снять `{onec_id: role}` до второго прогона и после → словари равны. Один файл снимка, не весь (см. Dev Notes → «Мина: объём данных»)
  - [ ] 6.3: Тест «поле реально заполняется на живых данных»: после прогона существует хотя бы один `User` с непустым `onec_price_type_id`, и все непустые значения — в нижнем регистре, без пробелов
  - [ ] 6.4: Тест AC4 на реальных данных: у контрагента со статусом `НетСоглашения` после прогона `onec_price_type_id == ""`
  - [ ] 6.5: Собирать временный каталог по образцу `tests/integration/test_customers_price_type_detector.py` (40.1): команда требует подкаталог именно **`contragents/`**

- [ ] **Task 7: Прогон, регресс, линтеры, pre-commit** (AC: 11, 12)
  - [ ] 7.1: Прогон новых тестов в тест-контейнере (команда — в Dev Notes → «Тестирование: как запускать»)
  - [ ] 7.2: Регресс: `tests/unit/test_services/test_customer_processor.py`, `tests/unit/test_users_admin.py`, `tests/unit/test_services/test_customer_parser.py`, `tests/integration/test_customers_price_type_detector.py`, `tests/integration/test_management_commands/test_import_customers.py`, `tests/integration/test_link_then_import_1c.py`, `tests/unit/test_services/test_link_1c_customer.py`
  - [ ] 7.3: `manage.py makemigrations --check --dry-run` → `No changes detected` (доказывает, что кроме `0021` модель не менялась)
  - [ ] 7.4: `black` + `flake8` на изменённых файлах
  - [ ] 7.5: `git diff HEAD --stat` — убедиться, что `apps/users/services/price_type_role.py`, `apps/users/services/link_1c_customer.py`, `apps/users/serializers.py`, `docs/api/openapi.yaml` и `frontend/` в диффе отсутствуют (AC12)
  - [ ] 7.6: `npx gitnexus detect-changes --scope all` — ожидаемые символы: `_create_customer`, `_update_customer`, новый `_price_type_id_to_store`, `UserAdmin`. Выполнять из основного клона

## Dev Notes

### Что уже есть и переиспользуется (не изобретать)

| Нужное | Где уже есть |
|---|---|
| `price_type_ids` (GUID, нижний регистр, дедуплицированы) и `agreement_status` в `customer_data` | `CustomerDataParser._extract_attribute_values` (`apps/users/services/parser.py`, стори 40.1). Парсер **не трогать** |
| Константа `"НетСоглашения"` | `AGREEMENT_STATUS_NONE` в `apps/users/services/price_type_role.py` (стори 40.2) |
| Длина и семантика GUID вида цен | `PriceType.onec_id` — `CharField(max_length=100, unique=True)` (`apps/products/models.py:698`) |
| Образец readonly display-метода в карточке пользователя | `UserAdmin.onec_link_candidates` (`apps/users/admin.py:357`) — `@admin.display(description=...)`, возврат строки |
| Образец теста админки users | `backend/tests/unit/test_users_admin.py` (`TestCase` + `AdminSite()` + `pytestmark = pytest.mark.unit`) |
| Образец интеграционного теста импорта на реальной выгрузке | `backend/tests/integration/test_customers_price_type_detector.py` (стори 40.1) — сборка tmp-каталога, `call_command` |
| Путь к реальным выгрузкам в тестах | фикстура `onec_data_dir` (`backend/tests/conftest.py:419`) — `Path(settings.BASE_DIR)/"data"/"import_1c"` |
| Фикстура `processor` (сессия импорта + `CustomerDataProcessor`) | `backend/tests/unit/test_services/test_customer_processor.py:23` |

### Почему резолвер здесь не нужен — и вызывать его нельзя

Соблазн: AC эпика сформулированы через `reason` (`no_agreement`, `no_data`), а резолвер из 40.2 эти причины и возвращает. **Вызывать его в 40.3 неправильно по существу.**

FR-40-05 требует записывать GUID **всегда**, независимо от того, применима ли роль. А резолвер отвечает `unknown_price_type` для видов цен, известных 1С, но не несущих роли: на текущем снимке это 42 контрагента на РРЦ и 2 на «Детский мир Залоговая». Ветвление по `reason` в 40.3 привело бы к тому, что этим 44 контрагентам вид цен не записался бы — прямое нарушение FR-40-05 и потеря ровно тех данных, ради накопления которых стори и выкатывается отдельно.

Решение принимается по **сырым данным парсера**, справочник `PriceType` процессором не читается вовсе:

| Вход из `customer_data` | Что делаем с `onec_price_type_id` | Соответствие |
|---|---|---|
| `agreement_status == "НетСоглашения"` | `= ""` (гасим) | AC4 |
| ровно один различный GUID в `price_type_ids` | `= guid` | AC2, AC3 |
| два и более различных GUID | не трогаем | AC6 |
| пусто и статуса нет | не трогаем | AC5 |

Порядок проверок именно такой: ветка статуса приоритетна (так же, как в резолвере 40.2), иначе противоречивый вход «`НетСоглашения` + непустой GUID» записал бы вид цен по снятому соглашению.

Из этого же следует, что **дополнительных SQL-запросов на контрагента не появляется** — NFR-3940-09 в этой стори выполняется автоматически, специальных мер не требуется.

### Точный код: поле модели

`backend/apps/users/models.py`, сразу после `onec_guid` (`models.py:280-286`):

```python
    onec_price_type_id = models.CharField(
        "GUID вида цен в 1С",
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Вид цен из соглашения об условиях продаж (реквизит ТипЦенId выгрузки "
            "контрагентов). Заполняется импортом 1С; роль портала по нему выдаётся "
            "отдельно. Пустое значение означает «соглашения нет» либо «GUID неоднозначен»."
        ),
    )
```

### Почему не null и не unique

- **Без `null=True`.** У `CharField` `NULL` и `""` означали бы одно и то же, но требовали бы двух проверок в каждом условии (`if not user.onec_price_type_id` перестало бы быть достаточным). Django-конвенция для текстовых полей — `blank=True` без `null`.
- **Без `unique=True`.** Один вид цен разделяют сотни контрагентов: на снимке 176 контрагентов на «Опт 3», 123 на «Опт 4». `unique` завалил бы импорт на втором же контрагенте.
- **Без `db_index`.** Поле читается по одному пользователю (карточка админки, привязка в 40.5), выборок «все с этим GUID» в эпике нет. Индекс на 4600 строк ради этого не нужен; если 40.4/40.5 понадобится обратный поиск — индекс заводится там.

### Точный код: метод процессора

`backend/apps/users/services/processor.py`. Импорт константы — на уровне модуля, рядом с существующими (`processor.py:17-18`):

```python
from apps.users.services.price_type_role import AGREEMENT_STATUS_NONE
```

Метод разместить после `_normalize_phone` (`processor.py:302-340`):

```python
    def _price_type_id_to_store(self, customer_data: dict[str, Any], current: str) -> str:
        """
        Определяет, каким должно стать поле onec_price_type_id.

        Роль здесь НЕ разрешается и справочник PriceType НЕ читается: поле
        обязано заполняться и для видов цен, роли не несущих (РРЦ, «Детский
        мир Залоговая»), — иначе накопление данных, ради которого стори
        выкатывается отдельно, потеряет часть контрагентов.

        Args:
            customer_data: словарь из парсера (ключи price_type_ids и
                agreement_status кладёт _extract_attribute_values, стори 40.1).
            current: сохранённое значение поля; возвращается без изменений,
                когда данных для решения нет.

        Returns:
            str: новое значение поля.
        """
        agreement_status = str(customer_data.get("agreement_status") or "")
        if agreement_status.strip().casefold() == AGREEMENT_STATUS_NONE.casefold():
            # 1С подтвердила, что действующего соглашения нет. Прежний вид цен
            # хранить нельзя: по нему привязка (стори 40.5) выдала бы роль по
            # соглашению, снятому в 1С месяцы назад, без единой ошибки в логах.
            return ""

        guids = {str(guid).strip().lower() for guid in (customer_data.get("price_type_ids") or []) if str(guid).strip()}

        if len(guids) == 1:
            return next(iter(guids))

        # Два и более различных вида цен — два разных соглашения. Сохранить один
        # из них означает солгать: стори 40.5 разрешает роль по единственному
        # сохранённому GUID и выдала бы роль там, где резолвер обязан ответить
        # ambiguous. Пустой список без статуса — признак поломки выгрузки
        # (после второй редакции патча блок приходит у каждого контрагента),
        # и обнуление уничтожило бы данные у всех разом.
        return current
```

**Чего не делать:**
- НЕ присваивать `user.role` — это 40.4, здесь роль неприкосновенна.
- НЕ вызывать `resolve_role_from_price_types` / `load_price_type_role_map`.
- НЕ писать `AuditLog` — журнал смены роли заводит 40.4.
- НЕ логировать в этом методе: вызывается на каждого из тысяч контрагентов.
- НЕ приводить GUID к другому регистру, чем нижний: парсер уже отдаёт нижний, справочник сравнивается через `iexact`.

Встраивание — две строки. В `_create_customer` (`processor.py:371-383`), в вызов `User.objects.create(...)`, после `onec_id=onec_id`:

```python
            onec_price_type_id=self._price_type_id_to_store(customer_data, ""),
```

В `_update_customer`, перед `user.save()` (`processor.py:419-422`):

```python
        # Вид цен пишется всегда — и привязанным аккаунтам, и записям 1С.
        # Роль по нему выдаёт стори 40.4, здесь она не трогается.
        user.onec_price_type_id = self._price_type_id_to_store(customer_data, user.onec_price_type_id)
```

### Точный код: админка

`backend/apps/users/admin.py`, метод рядом с `onec_link_candidates` (`admin.py:357`):

```python
    @admin.display(description="Вид цен из 1С")
    def onec_price_type_name(self, obj: User) -> str:
        """
        Человекочитаемое наименование вида цен по сохранённому GUID.

        Импорт PriceType локальный: приложение users не зависит от products
        на уровне модуля, и заводить эту связь ради одной подписи не нужно.
        Сравнение регистронезависимое — регистр onec_id в справочнике не
        нормализован (обнаружено в стори 40.2).
        """
        from apps.products.models import PriceType

        guid = (obj.onec_price_type_id or "").strip()
        if not guid:
            return "—"

        price_type = PriceType.objects.filter(onec_id__iexact=guid).values_list("onec_name", flat=True).first()
        return price_type or "—"
```

`readonly_fields` (`admin.py:196-205`) — добавить после `"onec_guid"`:

```python
        "onec_price_type_id",
        "onec_price_type_name",
```

Fieldset «Интеграция с 1С» (`admin.py:257-273`) — те же два имени после `"onec_guid"`, **до** `"onec_link_candidates"`.

### Мина: тесты со строгим равенством

`backend/tests/unit/test_users_admin.py` сверяет конфигурацию админки через `assertEqual` на полных списках:

| Тест | Строка | Реакция на эту стори |
|---|---|---|
| `test_readonly_fields` | `:124` | **Упадёт** — обязателен к обновлению (Task 5.4) |
| `test_search_fields` | `:111` | Упадёт, **если** добавить поле в `search_fields` — поэтому не добавляем (Task 3.4) |
| `test_fieldsets_structure` | `:512` | Проверяет только число секций и названия — не упадёт |
| `test_admin_actions_list` | `:502` | Не затрагивается |

Падение `test_readonly_fields` — ожидаемое следствие AC7, а не регресс. Обновить список в тесте, не ослабляя проверку до `assertIn`.

### Импорт константы: цикла нет

`processor.py` сегодня избегает модульного импорта `apps.products` (`ImportSession` тянется локально внутри `__init__`, `processor.py:50`). Новый импорт `from apps.users.services.price_type_role import AGREEMENT_STATUS_NONE` этот запрет **не нарушает по существу**, хотя и тянет `apps.products.models` транзитивно: `price_type_role.py` импортирует `PriceType` на уровне модуля, а `apps/products/models.py` импортирует `apps.users.models` только под `TYPE_CHECKING` (`products/models.py:24`). Цикла в рантайме нет — проверено.

Если при прогоне всё же всплывёт `ImportError` (например, из-за порядка загрузки приложений), запасной вариант — объявить константу локально в методе через тот же импорт **внутри функции**; дублировать строковый литерал `"НетСоглашения"` в двух модулях **запрещено**: разъезд значений при третьей редакции патча БУС будет тихим.

### Откуда брать данные в unit-тестах

NFR-3940-01 запрещает синтетические XML, но **не** запрещает конструировать словарь `customer_data` — он не является выгрузкой. Тем не менее GUID и статусы для тестов брать из реального снимка, а не выдумывать: так тест сломается, если формат данных 1С изменится.

Рабочий паттерн для `tests/unit/test_services/test_customer_processor.py`:

```python
@pytest.fixture(scope="module")
def real_customers():
    """Контрагенты из реального снимка второй редакции патча БУС."""
    from pathlib import Path

    from django.conf import settings

    from apps.users.services.parser import CustomerDataParser

    snapshot = Path(settings.BASE_DIR) / "data" / "import_1c" / "contragents_pricetype"
    files = sorted(snapshot.glob("contragents*.xml"))
    if not files:
        pytest.skip(f"Нет снимка выгрузки контрагентов: {snapshot}")

    # parse(file_path) → list[dict], БД не трогает (parser.py:55-85)
    return CustomerDataParser().parse(str(files[0]))


@pytest.fixture(scope="module")
def customer_with_price_type(real_customers):
    """Контрагент ровно с одним видом цен."""
    for data in real_customers:
        if len(set(data.get("price_type_ids") or [])) == 1:
            return data
    pytest.skip("В снимке нет контрагента с одним ТипЦенId")
```

⚠️ Путь считается напрямую из `settings.BASE_DIR`, **а не через фикстуру `onec_data_dir`**: та зависит от фикстуры `settings` (pytest-django), которая function-scoped, и `scope="module"` дал бы `ScopeMismatch`. В интеграционных тестах (Task 6), где фикстуры function-scoped, `onec_data_dir` использовать штатно.

Случай AC6 (два различных GUID) на снимке отсутствует — его собирают из реального словаря, подменив `price_type_ids` на два GUID **из того же снимка** (например «Опт 3» и «Опт 4» из таблицы ниже). Это не синтетический XML, а вариация входа сервиса.

### Реальные данные: что лежит в снимке

`backend/data/import_1c/contragents_pricetype/` — 10 файлов, 4735 контрагентов (замер стори 40.1, вторая редакция патча):

| Показатель | Значение |
|---|---|
| С блоком `<ЗначенияРеквизитов>` | 4735 (все) |
| С непустым `ТипЦенId` | 485 |
| Со статусом `НетСоглашения` | 4250 |
| С повторяющимся GUID внутри блока (дедуп в парсере) | 40 |
| С более чем одним **различным** GUID | **0** |

| GUID | Наименование | Контрагентов |
|---|---|---|
| `c05f0e2b-b3f2-11ea-81c3-00155d3cae02` | Опт 3 (50-150 тыс.руб в квартал) | 176 |
| `4c1962d2-f8ed-11eb-81f3-00155d3cae02` | Опт 4 (до 50 тыс.руб в квартал) | 123 |
| `a91bdb02-b3f2-11ea-81c3-00155d3cae02` | Опт 2 (150-300 тыс.руб в квартал) | 78 |
| `90d2c899-b3f2-11ea-81c3-00155d3cae02` | Опт 1 (300-600 тыс.руб в квартал) | 64 |
| `3d1482c4-bd77-11e4-afc8-20cf3073dde3` | РРЦ | 42 |
| `28049309-b6be-11ec-a301-04421a23d8e8` | Детский мир Залоговая | 2 |

Последние два GUID роли не несут (`PriceType.user_role` у РРЦ пуст, записи «Детский мир Залоговая» в справочнике нет вовсе) — и именно поэтому они хороший тестовый вход для AC3: вид цен обязан записаться и им.

`backend/data/import_1c/contragents/` — старый снимок от 11.04.2026 **без** блока у кого-либо: готовые данные для ветки AC5.

### Мина: объём данных в интеграционном тесте

Прогон команды на всех 10 файлах — это 4735 создаваемых `User` + столько же `CustomerSyncLog`, десятки минут. **Копировать в tmp-каталог один файл**, счётчики и инварианты линейны. Образец сборки каталога — `tests/integration/test_customers_price_type_detector.py` (40.1); команда жёстко требует подкаталог `contragents/` внутри `--data-dir` (`import_customers_from_1c.py:68-73`).

### Blast radius (обязательный pre-flight выполнен)

```
npx gitnexus impact _create_customer --direction upstream → risk: LOW, impacted: 3
npx gitnexus impact _update_customer --direction upstream → risk: LOW, impacted: 3
```

Цепочка одна и та же и полностью внутри импорта контрагентов:
`_create_customer` / `_update_customer` ← `process_customer` ← `process_customers` ← `Command.handle` (`import_customers_from_1c.py`). Затронутых процессов — 0, модулей — 1 (Services).

Единственная точка входа в импорт контрагентов — эта команда; Celery и вью вызывают её же (`apps/integrations/tasks.py:170`, `apps/products/tasks.py:215` → `call_command`). Путей, минующих `process_customer`, нет.

Изменение аддитивное: новое поле модели, новый приватный метод, две строки присваивания. Ни одна существующая сигнатура не меняется, ни один существующий ключ словаря не меняет смысла.

⚠️ **Индекс GitNexus на момент создания стори помечен `stale`** (проиндексирован `c4b4204`, HEAD `f8c905a`). Единственный неиндексированный коммит — docs-only, код в нём не менялся, поэтому цифры выше актуальны. Перед `detect-changes` (Task 7.6) выполнить `npx gitnexus analyze`, иначе новые символы (`_price_type_id_to_store`) в графе не найдутся.

### Границы стори (что делают соседние стори — здесь НЕ делать)

- **40.1** (done) — парсер, `price_type_ids` / `price_type_meta` / `agreement_status`, детектор регресса выгрузки. `parser.py` здесь **не трогается**.
- **40.2** (done) — `PriceType.user_role`, админка справочника, `resolve_role_from_price_types`. `price_type_role.py` здесь **не трогается** (кроме импорта одной константы).
- **40.4** — применение роли привязанным аккаунтам, `AuditLog` `role_from_1c`, счётчики `roles_*`, снятие `role_preserved=True`. Роль в 40.3 не меняется **никогда**.
- **40.5** — перенос `onec_price_type_id` при привязке и применение роли: `TRANSFERRED_USER_FIELDS` (`link_1c_customer.py:27`) в 40.3 **не расширяется**. Следствие, которое надо знать и не «чинить»: до 40.5 привязка заявки к контрагенту вид цен не переносит — сохранённый GUID остаётся на деактивированной записи 1С. Это ожидаемое промежуточное состояние выката.

Экспорт заказа не меняется. API-контракт не меняется: `openapi.yaml` и типы фронта не трогаются, `npm run generate:types` не запускается. Frontend не затрагивается.

### Тестирование: как запускать

`make` на машине недоступен, а таргеты `test-*` ищут несуществующий `docker/.env`. Рабочий эквивалент из основного клона:

```bash
cd /c/Users/1/DEV/FREESPORT/docker
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend \
  pytest -q tests/unit/test_services/test_customer_processor.py \
            tests/unit/test_users_admin.py \
            tests/integration/test_import_customers_price_type.py
docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml down
```

Миграция в dev-контейнере:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py makemigrations users --name add_user_onec_price_type_id
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py migrate users
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py makemigrations --check --dry-run
```

Линтеры:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend \
  black apps/users/models.py apps/users/services/processor.py apps/users/admin.py
docker compose --env-file .env -f docker/docker-compose.yml exec -T backend flake8 apps/users/
```

Маркеры `unit` / `integration` проставляются **автоматически по каталогу** теста (`backend/conftest.py`); `@pytest.mark.data_dependent` ставится вручную. `container_name` в `docker-compose.test.yml` зашит жёстко — параллельно поднятый тест-стек даст конфликт имён.

⚠️ **Тестовая БД строится С миграциями** (в `backend/pytest.ini` нет `addopts` с `--nomigrations`) — это выяснилось в 40.2 и опровергает `backend/CLAUDE.md`. Практическое следствие для этой стори: запись «Опт 4» из миграции `products/0053` в справочнике уже лежит, и тест админки, создающий `PriceType` с тем же `onec_id`, упадёт на `duplicate key`. Использовать в тестах админки **другой** GUID (например РРЦ) либо `get_or_create`.

### Project Structure Notes

| Файл | Статус | Что |
|---|---|---|
| `backend/apps/users/models.py` | UPDATE | Поле `User.onec_price_type_id` |
| `backend/apps/users/migrations/0021_add_user_onec_price_type_id.py` | **NEW** | Схемная миграция |
| `backend/apps/users/services/processor.py` | UPDATE | `_price_type_id_to_store`, две строки присваивания, импорт константы, docstring |
| `backend/apps/users/admin.py` | UPDATE | `onec_price_type_name`, `readonly_fields`, fieldset «Интеграция с 1С» |
| `backend/tests/unit/test_services/test_customer_processor.py` | UPDATE | Класс `TestCustomerPriceTypeStorage` + фикстуры реального снимка |
| `backend/tests/unit/test_users_admin.py` | UPDATE | Тесты отображения вида цен + правка `test_readonly_fields` |
| `backend/tests/integration/test_import_customers_price_type.py` | **NEW** | Прогон на реальной выгрузке: заполнение поля, неизменность ролей, гашение при `НетСоглашения` |

Новых зависимостей нет — `requirements.txt` не трогается. Data-миграций нет: поле заполняет импорт, а не миграция (единственная возможная альтернатива — заполнение из выгрузки на этапе миграции — невозможна: выгрузки в БД нет). Изменений `openapi.yaml`, типов фронта и `frontend/` нет.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 40.3`] — AC в BDD-форме, FR-40-05, FR-40-06
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic 40`] — порядок стори, «40.3 выкатывается сама по себе», отложенный эффект `roles_updated = 0`
- [Source: `_bmad-output/planning-artifacts/epics.md#NonFunctional Requirements`] — NFR-3940-01 (реальные XML), -02 (маркеры), -03 (покрытие ≥ 90 % для users), -06 (миграции на PostgreSQL), -08 (идемпотентность)
- [Source: `_bmad-output/implementation-artifacts/Story/40-1-parser-price-type-and-export-regression-detector.md`] — формат блока `<ЗначенияРеквизитов>`, состав снимка, мины «путь к данным» и «имя подкаталога», работа в основном клоне
- [Source: `_bmad-output/implementation-artifacts/Story/40-2-price-type-role-mapping-and-resolver.md`] — `AGREEMENT_STATUS_NONE`, различие `no_agreement` / `no_data` и его последствия для 40.3, регистр `onec_id` в справочнике, тестовая БД строится с миграциями
- [Source: `_bmad-output/implementation-artifacts/tasks/dev-task-role-from-1c-agreement.md` §5] — роль импортированного контрагента остаётся `unregistered`
- [Source: `project-context.md` §3, §4, §6] — доменные инварианты 1С (`onec_id` immutable), реальные XML в тестах, покрытие, русские комментарии
- [Source: `backend/docs/testing-standards.md`] — стандарты тестирования, маркеры pytest

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
