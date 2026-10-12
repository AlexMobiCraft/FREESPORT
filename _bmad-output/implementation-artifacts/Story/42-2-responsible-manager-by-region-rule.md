---
baseline_commit: 26207161
---

# Story 42.2: Ответственный менеджер клиента по правилу региона

Status: done
Baseline Revision: 26207161

## Story

As a руководитель отдела продаж,
I want чтобы у каждого клиента был ответственный менеджер, назначенный по региону автоматически,
so that заявка нового клиента сразу попадала к нужному менеджеру, а при смене менеджера в регионе его клиенты переходили к преемнику.

**Закрывает:** FR-42-05, FR-42-07, FR-42-08, FR-42-10, FR-42-11. **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.2), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-2, Constraints).

**Предусловие:** стори 42.1 (`feature/42-1-staff-roles-lockdown`, статус review). Эта стори опирается на её `apps/users/staff_roles.py` и миграцию `users/0023_staff_role_groups`. Ветку `feature/42-2-…` создавать от `develop` после мёрджа 42.1. Если 42.1 ещё не слита — от `feature/42-1-staff-roles-lockdown`, а перед PR сделать rebase на `develop`.

**Чего в этой стори нет:**
- справочника названий регионов, списка «Не распределены» и команды разового пересчёта — это 42.3;
- разделов `/manager/` и `/supervisor/`, ручного и массового переназначения руководителем и записей `AuditLog` о переназначении — это 42.4 и 42.7.

После выката 42.2 ответственного получают только новые и изменившиеся клиенты, у существующих поле остаётся пустым до команды 42.3.

## Утверждённые решения (не пересматривать)

1. **Одно активное правило на код региона и одно на страну** (решение Alex 08.10.2026). Ограничение в БД — частичный `UniqueConstraint` по `(match_type, match_value)` для активных правил с `match_type in (inn_region, country)`.
2. **Резервных (`fallback`) правил может быть несколько:** каждое добавляет получателя письма. Так сейчас на проде: `managermsk3@` и `admin@freesportopt.ru`. Тесты `test_region_routing.py` проверяют именно двух получателей резерва, а AC требует, чтобы они прошли без правки ожиданий. Ответственного же даёт **одно** резервное правило — то, у которого задан `manager`. Второе ограничение в БД: не больше одного активного резервного правила с непустым `manager`.
3. **Правило без учётной записи** (`manager` пуст, есть только `manager_email`) остаётся рабочим для писем. Ответственного оно не даёт: клиенты такого региона достаются менеджеру резервного правила, то есть руководителю. Отдельной очереди «без менеджера» нет: её роль играет резервное правило (SPEC, Non-goals).
4. **Адрес письма:** у правила с `manager` письмо уходит на `manager.email` (живой адрес учётной записи), у правила без `manager` — на `manager_email`. Набор правил для письма остаётся прежним: регион или страна, иначе резерв.
5. **Автоназначение срабатывает при создании клиента и при смене его `tax_id` или `country`** — в `User.save()`, на любом пути сохранения. Так покрыты:
   - регистрация;
   - импорт 1С;
   - привязка к 1С;
   - правка в карточке админки;
   - смена ИНН через API профиля.

   Отдельно, явным вызовом, назначение выполняется при верификации, потому что ИНН при ней обычно не меняется (FR-42-08).
6. **«Назначен вручную» не перезаписывает ни одно автоматическое событие**, включая смену правила региона.
7. **Сотрудникам ответственный не назначается.** Сотрудник — это учётная запись, у которой выполнено хотя бы одно из условий:
   - `is_staff`;
   - `is_superuser`;
   - `role == "admin"`;
   - членство в одной из трёх групп ролей.

   `role == "admin"` добавлено сверх AC: у робота обмена 1С (id 17) `is_staff=false`, но `role=admin`, а без этого условия он получил бы ответственного из резервного правила.
8. **При смене правила клиенты региона пересчитываются сразу и одним `UPDATE`**, без Celery. Изменения правил редки, а пересчёт одного кода — один запрос.
9. **Учётная запись менеджера остаётся у клиента, даже если её заблокировали:** блокировка не переводит клиентов. Передача клиентов и замена менеджера в правиле при увольнении — функции руководителя (42.7).

## Acceptance Criteria

### AC1 — миграция связывает правила с учётными записями

**Given** существующие правила, у которых есть только `manager_email`
**When** применяются миграции `common/0022` и `common/0023`
**Then** правило связывается (`manager`) с учётной записью сотрудника (`is_staff=True`, не суперпользователь), у которой email совпадает без учёта регистра
**And** правило без найденной учётной записи остаётся активным, `manager` у него пуст, письма по нему уходят на `manager_email`
**And** из нескольких активных резервных правил связывается не больше одного: первое по `pk`, у которого нашлась учётная запись
**And** повторный прогон функции миграции результат не меняет

### AC2 — одно активное правило на регион

**Given** активное правило для кода региона «23»
**When** создаётся второе активное правило с кодом «23», или второе активное правило для страны, у которой правило уже есть
**Then** `full_clean()` и форма админки отклоняют сохранение с ошибкой на русском, а прямой `save()` падает на `IntegrityError`
**And** неактивное правило с тем же кодом сохранить можно
**And** второе активное резервное правило без `manager` сохранить можно, а второе активное резервное с `manager` — нельзя
**And** правило без `manager` и без `manager_email` не проходит `full_clean()`

### AC3 — назначение при регистрации

**Given** правило «23 → менеджер A» и резервное правило «→ руководитель R»
**When** регистрируется клиент с ИНН `23…`, затем клиент с ИНН `00…` без правила
**Then** первому ответственным назначается A, второму — R
**And** признак «назначен вручную» у обоих снят
**And** клиент региона, у правила которого нет `manager`, получает R

### AC4 — переназначение при смене ИНН или страны

**Given** клиент региона 23 без ручного назначения
**When** его ИНН меняется на `77…` при импорте из 1С (`_update_customer`), при привязке к 1С (`link_1c_customer`), при верификации с привязкой, при правке в карточке админки или через API профиля
**Then** ответственным становится менеджер правила региона 77
**And** смена страны на «Беларусь» даёт менеджера правила по стране
**And** у клиента с признаком «назначен вручную» ответственный не меняется ни при одном из этих событий
**And** сохранение с `update_fields`, в которых есть `tax_id` или `country`, записывает и нового ответственного

### AC5 — назначение при верификации существующей заявки

**Given** заявка, поданная до выката 42.2, ответственного у неё нет
**When** менеджер подтверждает её без привязки к 1С (ИНН не меняется)
**Then** ответственный назначается по правилу региона

### AC6 — смена правила переводит клиентов региона

**Given** правило «23 → менеджер A». У A десять клиентов региона 23, у двух из них ручное назначение, и ещё есть клиенты A из региона 24
**When** в правиле менеджер A заменяется на B
**Then** восемь клиентов без ручного назначения переходят к B, два с ручным остаются у A
**And** клиенты A из региона 24 не затронуты
**And** выключение правила 23 или его удаление переводит его клиентов без ручного назначения к менеджеру резервного правила
**And** смена кода правила с «23» на «24» пересчитывает оба региона
**And** смена `manager` у резервного правила переводит к новому руководителю клиентов, чей регион попадает на резерв, а клиентов с региональным менеджером не трогает

### AC7 — письмо о регистрации по той же таблице

**Given** регистрация B2B-клиента
**When** ставится письмо о регистрации
**Then** получатель — `manager.email` правила региона (либо `manager_email` правила без учётной записи)
**And** существующие тесты `tests/unit/test_region_routing.py` проходят без правки ожиданий

### AC8 — сотрудники не получают ответственного

**Given** учётная запись сотрудника: `is_staff`, суперпользователь, `role="admin"` или член группы «Менеджеры», «Маркетинг» или «Руководители»
**When** срабатывает любое событие автоназначения: создание, смена ИНН или страны, верификация, смена правила
**Then** ответственный ей не назначается и не меняется

### AC9 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `flake8`, `black --check`, `mypy` и `check_openapi_sync`
**Then** всё зелёное, а ожидания существующих тестов не изменены

## Tasks / Subtasks

- [x] **Task 0 — GitNexus pre-flight** (AGENTS.md)
  - [x] `npx gitnexus status` (на `26207161` индекс свежий); при `stale` попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] `impact --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по символам: `resolve_manager_recipients`, `send_manager_region_email`, `ManagerRoutingRule`, `ManagerRoutingRuleAdmin`, `verify_b2b_application`, `link_1c_customer`, `_update_customer`, `UserAdmin`.

    Снято на `26207161`:
    - `resolve_manager_recipients` — LOW (1 вызывающий — `send_manager_region_email`);
    - `send_manager_region_email` — LOW;
    - `verify_b2b_application` — LOW;
    - `ManagerRoutingRuleAdmin` — LOW;
    - `ManagerRoutingRule` — **HIGH, но ложно.** 23 «прямых» — это файлы, которые импортируют модуль `apps.common.models` ради других моделей. По grep класс используют только `common/admin.py`, `region_routing.py` и миграции. Сообщить это Alex вместе с blast radius.
  - [x] **`User.save()` — HIGH по природе:** через него проходит каждое сохранение пользователя. У GitNexus `save` неоднозначен, поэтому вызывающих искать через `cypher` или `context --file backend/apps/users/models.py`. Предупредить Alex до правки. Защита — Task 3: проверка дешёвая и срабатывает только при создании или смене `tax_id`/`country`.

- [x] **Task 1 — критерий «сотрудник» и выбор менеджера** (AC8)
  - [x] Дописать в `backend/apps/users/staff_roles.py`, не меняя существующие константы:
    ```python
    from django.db.models import Q

    # Учётные записи, которые не бывают клиентами: им не назначается
    # ответственный, и их не трогает пересчёт по правилам регионов.
    def staff_accounts_q() -> Q:
        return (
            Q(is_staff=True)
            | Q(is_superuser=True)
            | Q(role="admin")
            | Q(groups__name__in=STAFF_ROLE_GROUPS)
        )

    # Кого можно выбрать ответственным менеджером и менеджером правила региона.
    RESPONSIBLE_MANAGER_CHOICES = Q(is_staff=True, is_superuser=False, groups__name__in=(MANAGERS_GROUP, SUPERVISORS_GROUP))
    ```
    Docstring модуля дополнить одной фразой: модуль теперь хранит и критерий «сотрудник», и не только имена групп. Почему условие `role="admin"` — решение 7.
  - [x] Предикат на экземпляре `is_staff_account(user) -> bool` положить в сервис Task 3, не в `staff_roles`. Порядок проверок:
    1. `is_staff`, `is_superuser`, `role == "admin"` — по атрибутам, без запроса;
    2. группы — запросом `user.groups.filter(name__in=STAFF_ROLE_GROUPS).exists()`, и только когда у записи есть `pk`. У несохранённой записи групп нет.

- [x] **Task 2 — модель и миграции правила** (AC1, AC2)
  - [x] `backend/apps/common/models.py` `ManagerRoutingRule` (`:1040`):
    - новое поле:
      ```python
      manager = models.ForeignKey(
          settings.AUTH_USER_MODEL,
          on_delete=models.SET_NULL,
          null=True,
          blank=True,
          related_name="routing_rules",
          limit_choices_to=RESPONSIBLE_MANAGER_CHOICES,
          verbose_name="Менеджер",
          help_text="Учётная запись ответственного менеджера; письма уходят на её email",
      )
      ```
    - `manager_email` → `blank=True`; `help_text` дописать: «Используется, пока менеджер не выбран».
    - `Meta.constraints`, две записи:
      ```python
      models.UniqueConstraint(
          fields=["match_type", "match_value"],
          condition=Q(is_active=True, match_type__in=["inn_region", "country"]),
          name="common_mrr_one_active_per_key",
          violation_error_message="Для этого кода региона или страны уже есть активное правило. Выключите его или измените.",
      ),
      models.UniqueConstraint(
          fields=["match_type"],
          condition=Q(is_active=True, match_type="fallback", manager__isnull=False),
          name="common_mrr_one_fallback_manager",
          violation_error_message="Ответственного по резервному правилу может давать только одно активное правило с менеджером.",
      ),
      ```
      Литералы в `condition` — потому что атрибуты класса `MATCH_*` внутри `Meta` недоступны. Проверить тестом, что `full_clean()` ловит обе ошибки (Django 5.2 проверяет `condition` в `validate_constraints`). Если `manager__isnull` в проверке условия не сработает, продублировать проверку в `clean()` с тем же сообщением.
    - `clean()`, существующую нормализацию сохранить:
      - нет ни `manager`, ни `manager_email` → `ValidationError` «Укажите менеджера или email для писем»;
      - `match_type == inn_region` и `match_value` не две цифры → `ValidationError({"match_value": "Код региона — две цифры, например 23"})`;
      - `match_type == country` и `match_value == User.COUNTRY_RUSSIA` → `ValidationError({"match_value": "Для России правило задаётся кодом региона"})`.

        Страну сравнивать с литералом `"Россия"` из `User.COUNTRY_RUSSIA`. Импортировать `User` в `common/models.py` нельзя, поэтому либо локальный импорт в `clean()`, либо литерал с комментарием.
    - Docstring класса переписать: «несколько активных строк дают несколько получателей» теперь верно **только для резерва**. Добавить, что правило задаёт и ответственного менеджера клиента (эпик 42).
    - `__str__`: показывать `manager.email`, если менеджер задан. Иначе `manager_email`.
  - [x] `apps/common/migrations/0022_managerroutingrule_manager.py` — **только схема**:
    - `AddField(manager)`;
    - `AlterField(manager_email)`;
    - `AddConstraint` ×2.

    Зависимости:
    - `("common", "0021_newsletter_unsubscribe_token")`;
    - `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`;
    - `("users", "0023_staff_role_groups")` — для `limit_choices_to` по группам.

    Циклов нет: `users/0023` зависит от `common/0021`, а не от `0022`. Миграцию сгенерировать `makemigrations common` в контейнере, затем переименовать.
  - [x] `apps/common/migrations/0023_link_routing_rules_to_staff.py` — **только данные**. Отдельная миграция, потому что на PostgreSQL смешение `UPDATE` и `ALTER TABLE` с отложенными FK-триггерами в одной транзакции падает на «pending trigger events». Функция `link_rules_to_staff(apps, schema_editor)`:
    - для каждого правила без `manager` с непустым `manager_email` искать `User` по условиям `email__iexact=manager_email`, `is_staff=True`, `is_superuser=False`; из нескольких брать первого по `pk`;
    - резервные правила обходить по возрастанию `pk` и связывать, только пока ни одно активное резервное ещё не связано;
    - обратная функция — `RunPython.noop`.

    Ожидаемый результат на проде описан в Dev Notes, «Прод».
  - [x] `apps/common/admin.py` `ManagerRoutingRuleAdmin` (`:626`):
    - `list_display` — добавить `"manager"` после `match_value`;
    - `list_select_related = ("manager",)`;
    - fieldset «Менеджер»: `("manager", "manager_name", "manager_email", "federal_district")`, описание «Письма уходят на email выбранного менеджера; email ниже — только пока менеджер не выбран».

    **Не добавлять `manager` в `list_editable`:** выпадающий список в каждой из ~92 строк — запрос на строку.

- [x] **Task 3 — поле клиента и сервис назначения** (AC3, AC4, AC5, AC8)
  - [x] `backend/apps/users/models.py` `User`, после блока `verification_status`:
    ```python
    responsible_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_clients",
        limit_choices_to=RESPONSIBLE_MANAGER_CHOICES,
        verbose_name="Ответственный менеджер",
    )
    responsible_manager_manual = models.BooleanField(
        "Назначен вручную",
        default=False,
        help_text="Ручное назначение не перезаписывают правила регионов, смена ИНН и импорт 1С",
    )
    ```
    Миграция `apps/users/migrations/0024_user_responsible_manager.py` — только схема, зависимость `("users", "0023_staff_role_groups")`. Данных не трогает: существующим клиентам ответственного проставит команда 42.3.
  - [x] **Новый модуль `backend/apps/users/services/responsible_manager.py`** — единственный источник логики назначения. Его переиспользует 42.3, поэтому разрешение возвращает источник:
    ```python
    SOURCE_REGION = "inn_region"; SOURCE_COUNTRY = "country"; SOURCE_FALLBACK = "fallback"; SOURCE_NONE = "none"

    @dataclass(frozen=True)
    class ResponsibleResolution:
        manager: User | None
        source: str  # одна из SOURCE_*

    def region_key(country: str | None, tax_id: str | None) -> tuple[str, str] | None: ...
    def resolve_responsible(country: str | None, tax_id: str | None) -> ResponsibleResolution: ...
    def resolve_responsible_for_key(key: tuple[str, str] | None) -> ResponsibleResolution: ...
    def is_staff_account(user: User) -> bool: ...
    def assign_responsible_manager(user: User) -> bool: ...   # меняет атрибут в памяти, не сохраняет; True — значение изменилось
    def reassign_clients_for_key(key: tuple[str, str] | None) -> int: ...  # key=None — резерв
    ```
    - `region_key` — **ровно** логика `resolve_manager_recipients`:
      - `country` непуст и не Россия → `("country", country)`;
      - иначе `code = (tax_id or "")[:2]`; две цифры → `("inn_region", code)`;
      - иначе `None`.

      Пустая страна считается Россией. ИНН с пробелом в начале не даёт региона: импорт пишет `tax_id` без `strip()`, см. `link_1c_customer.py:74`. Нормализовать ИНН здесь **нельзя**, иначе одиночное и массовое назначение разойдутся.
    - `resolve_responsible_for_key`:
      1. есть ключ → активное правило этого ключа с `manager__isnull=False`, `select_related("manager")`. Нашлось → `(rule.manager, key[0])`;
      2. иначе активное резервное с `manager` → `(manager, SOURCE_FALLBACK)`;
      3. иначе `(None, SOURCE_NONE)`.
    - `assign_responsible_manager(user)`: при `user.responsible_manager_manual` или `is_staff_account(user)` вернуть `False`. Иначе разрешить и присвоить `user.responsible_manager`, вернуть «изменилось ли».
    - `reassign_clients_for_key(key)` — массовый пересчёт одним `UPDATE`. База: `User.objects.filter(responsible_manager_manual=False).exclude(staff_accounts_q())`. Целевой менеджер — `resolve_responsible_for_key(key).manager`. Выборка клиентов по виду ключа:

      | ключ | клиенты |
      |---|---|
      | `("inn_region", code)` | `Q(country__in=["Россия", ""])`, затем `.annotate(region=Substr("tax_id", 1, 2)).filter(region=code)` |
      | `("country", value)` | `filter(country=value)` |
      | `None` (резерв) | клиенты, чей ключ не покрыт активным правилом с `manager`: российские с `region` не из `covered_codes` и зарубежные со страной не из `covered_countries`. Оба множества — одним запросом `values_list("match_type", "match_value")` по активным правилам `inn_region`/`country` с `manager__isnull=False` |

      Затем `.exclude(responsible_manager=target).update(responsible_manager=target)`, вернуть число строк. Если `target is None`, `exclude(responsible_manager=None)` превращается в `responsible_manager__isnull=False` — проверить тестом.
    - Инвариант для тестов: после `reassign_clients_for_key` у каждого затронутого клиента `responsible_manager == resolve_responsible(client.country, client.tax_id).manager`.
  - [x] **`User.save()`** (`users/models.py:360`) — хук автоназначения. Существующий запрос `previous` расширить до `.only("customer_code", "tax_id", "country")`: так обходится без лишнего запроса. Ветка `customer_code` остаётся как есть. Затем:
    ```python
    update_fields = kwargs.get("update_fields")
    region_fields_saved = update_fields is None or {"tax_id", "country"} & set(update_fields)
    if region_fields_saved and (
        previous is None  # новая запись (или pk задан, а строки нет)
        or previous.tax_id != self.tax_id
        or previous.country != self.country
    ):
        from apps.users.services.responsible_manager import assign_responsible_manager
        if assign_responsible_manager(self) and update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "responsible_manager"}
    super().save(*args, **kwargs)
    ```
    Для новой записи (`self.pk is None`) `previous` сейчас не запрашивается — ветку оформить так, чтобы `previous is None` означало «новая». Импорт сервиса — локальный: сервис импортирует `ManagerRoutingRule` из `common.models`. Комментарий над блоком — на русском: почему хук в `save()`, а не в `pre_save` (сигнал не может дописать `update_fields`, а `link_1c_customer` сохраняет `tax_id` через `update_fields`).
  - [x] **Верификация** (`users/services/verify_b2b_application.py`, ветка `MODE_DECISION`, `:247-251`): перед сохранением вызвать `assign_responsible_manager(target)`; если вернул `True`, добавить `"responsible_manager"` в `update_fields` этого `save`. Сервис привязки не трогать: `link_1c_customer` сохраняет `tax_id` через `update_fields`, хук в `save()` срабатывает сам.
  - [x] **Регистрация, импорт 1С, API профиля, карточка админки** — кода не добавлять, их покрывает хук `save()`. Это проверяется тестами AC3/AC4. Пути и строки, по которым проходит назначение:

    | путь | где сохраняется |
    |---|---|
    | регистрация | `UserRegistrationSerializer.create` (`serializers.py:360`, `create_user`) |
    | импорт 1С | `processor.py:566` (`_create_customer`), `:624` (`_update_customer`) |
    | привязка к 1С | `link_1c_customer.py:262` |
    | API профиля | `UserProfileSerializer` |
    | карточка админки | `UserAdmin` |

- [x] **Task 4 — пересчёт при смене правила** (AC6)
  - [x] Ресиверы в `backend/apps/users/signals.py`, `sender=ManagerRoutingRule`:
    - `pre_save` запоминает старые `(match_type, match_value, is_active, manager_id)` одним `.values(...).first()` по `pk`;
    - `post_save` и `post_delete` вычисляют затронутые ключи и вызывают `reassign_clients_for_key` для каждого.

    Логика в сервисе: `affected_keys(old: dict | None, new: dict | None) -> set[key | None]`.
    - Если старое или новое состояние резервное — затронут резерв (`None`).
    - Иначе затронуты старый и новый ключи, если правило меняло ключ, `is_active` или `manager_id`.
    - Изменение региона или страны **с менеджером** меняет покрытие резерва. Поэтому, если `manager_id` или активность изменились у правила `inn_region`/`country`, добавить и `None`: клиенты, уходившие на резерв, могли получить регионального менеджера, и наоборот.
    - Правка только `manager_name`, `manager_email` или `federal_district` клиентов не пересчитывает: ноль `UPDATE`, проверить `django_assert_num_queries`.
  - [x] Пересчёт синхронный, внутри транзакции сохранения правила: админка оборачивает `save_model` в `atomic`. Логировать `logger.info` с ключом и числом переведённых клиентов, `extra={"action": "responsible_manager_reassign", ...}` — по образцу `region_routing.py:48`. `AuditLog` за смену правила пишет 42.7.

- [x] **Task 5 — письмо по той же таблице** (AC7)
  - [x] `region_routing.resolve_manager_recipients` (`:17`) переписать через `region_key` из Task 3, поведение и docstring сохранить. Адреса брать так: `rule.manager.email if rule.manager_id and rule.manager.email else rule.manager_email`, `select_related("manager")`, пустые значения отбросить, дедупликация как сейчас. Docstring модуля дополнить: таблица правил задаёт и ответственного (`services/responsible_manager.py`).
  - [x] `send_manager_region_email` (`tasks.py:400`) не менять. Если `resolve_manager_recipients` станет функцией над `region_key`, задача пойдёт той же дорогой.

- [x] **Task 6 — `/admin/` суперпользователя** (FR-42-07: поле у клиента есть и видно)
  - [x] `UserAdmin.fieldsets` (`users/admin.py:310`): новый блок «Ответственный менеджер» с полями `("responsible_manager", "responsible_manager_manual")` после «Роль и статус». Редактируемы: `/admin/` теперь только у суперпользователя. Описание блока: «Ответственного назначает правило региона. Отметьте „Назначен вручную“, чтобы правила, смена ИНН и импорт его не меняли».
  - [x] `list_display`/`list_filter` UserAdmin не трогать. Список клиентов с ответственным — раздел 42.4, а лишняя колонка FK без `list_select_related` сломала бы тест `test_admin_link_1c_customer.py:316` (`TestChangelistIndicatorCost`).
  - [x] API-сериализаторы пользователя не трогать: поле в API не отдаётся, OpenAPI не меняется. `check_openapi_sync` это подтверждает.

- [x] **Task 7 — тесты** (NFR-42-01, NFR-42-02). Общие правила для всех файлов:
  - в каждом тесте с правилами autouse-фикстура делает `ManagerRoutingRule.objects.all().delete()`, как в `test_region_routing.py:33`: в тестовой БД лежат правила из `common/0018`;
  - группы ролей — через `Group.objects.get_or_create(name=...)` из `staff_roles`.
  - [x] `backend/tests/unit/test_responsible_manager.py`:
    - `region_key`: Россия + `23…` → `("inn_region","23")`; пустая страна → как Россия; Беларусь + `77…` → `("country","Беларусь")`; `""`, `"7"`, `"AB…"`, `" 23…"` → `None`.
    - `resolve_responsible`: регион с `manager`; регион без `manager` → резерв; страна; без ключа → резерв; нет резерва с менеджером → `(None, "none")`; неактивное правило игнорируется. Источник (`source`) — в каждом случае.
    - `is_staff_account`: `is_staff`, суперпользователь, `role="admin"`, каждая из трёх групп → `True`; клиент B2B и запись `unregistered` → `False`.
    - `reassign_clients_for_key`: сценарий AC6 целиком (десять клиентов A в регионе 23, двое ручных, клиенты A в 24; замена A→B). Плюс выключение и удаление правила, смена кода 23→24, смена менеджера резерва. В каждом случае — инвариант «массовое = поштучное».
    - Сотрудник в регионе 23 при пересчёте не тронут (AC8).
  - [x] `backend/tests/unit/test_manager_routing_rule.py`:
    - AC2: второе активное по коду и по стране → `full_clean` с русским сообщением и `IntegrityError` на `save()`; неактивное — можно; два резервных без `manager` — можно; два активных резервных с `manager` — нельзя;
    - `clean()`: без `manager` и email; код «7» и «2a»; страна «Россия»;
    - `__str__` с менеджером и без;
    - сигнал: правка только `manager_email` → ни одного `UPDATE users` (`CaptureQueriesContext`, фильтр по `UPDATE "users"`).
  - [x] `backend/tests/unit/test_routing_rules_link_migration.py` — AC1. Функцию звать напрямую: `importlib.import_module("apps.common.migrations.0023_link_routing_rules_to_staff").link_rules_to_staff(django.apps.apps, SimpleNamespace(connection=connection))` — образец `tests/unit/test_staff_role_groups_migration.py`. Сценарии:
    - email в другом регистре связывается;
    - клиент (не `is_staff`) с тем же email не связывается;
    - суперпользователь не связывается;
    - два резервных — связывается только первое;
    - повторный вызов ничего не меняет.
  - [x] `backend/tests/unit/test_region_routing.py` — **ожидания не менять**. Дописать новые тесты:
    - правило с `manager` → адрес учётной записи, даже если `manager_email` другой;
    - правило с `manager`, у которого пустой email → `manager_email`.
  - [x] `backend/tests/integration/test_responsible_manager_events.py` — сквозные события. Письма и Celery мокать, как в `test_registration_emails.py:118` (`patch("apps.users.serializers.send_manager_region_email.delay")` и соседние). Сценарии:
    - AC3 — регистрация через API `/api/v1/auth/register/` (URL сверить по `test_registration_emails.py`) с ИНН `23…` и `00…`;
    - AC4 — смена ИНН:
      - `UserCustomerProcessor._update_customer` (данные клиента — словарем, как в `tests/unit/test_services/test_customer_processor.py`, без синтетического XML);
      - `link_1c_customer` (образец фикстур — `tests/integration/test_admin_link_1c_customer.py`, там же `make_1c_record`, `make_applicant`);
      - POST карточки `/admin/users/user/<id>/change/` суперпользователем;
      - `PATCH` профиля;
      - ручное назначение у каждого пути не меняется;
    - AC4 — `save(update_fields=["tax_id"])` записывает ответственного в БД (`refresh_from_db`);
    - AC5 — `verify_b2b_application` без привязки (образец — `tests/integration/test_admin_verify_b2b_application.py`);
    - AC6 — смена менеджера правила через POST формы `ManagerRoutingRuleAdmin` суперпользователем (сигнал срабатывает из админки);
    - AC8 — сотрудник с ИНН `23…`, созданный и изменённый, не получает ответственного.
  - [x] Негативные тесты (NFR-42-02 — здесь это проверка «не назначать»):
    - ручное назначение;
    - сотрудник;
    - неактивное правило;
    - второе активное правило.

- [x] **Task 8 — проверки и закрытие**
  - [x] Полный backend-прогон в Docker, один compose-проект, без параллельных прогонов: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest`. Ожидания существующих тестов не меняются (AC9). Если что-то падает из-за лишних запросов при создании пользователя, разобраться и не ослаблять тест молча.
  - [x] `makemigrations --check --dry-run` в контейнере — новых несгенерированных изменений нет.
  - [x] Линтеры — навык `backend-lint` или compose-проект `freesport-lint`, не параллельно с зачётным pytest. `check_openapi_sync` — рецепт в Dev Notes; ожидается «синхронен», API не менялся.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [x] Completion Notes: шаги выката (Dev Notes, «Прод») и фактический результат миграции связывания на тестовом прогоне.

### Review Findings

Код-ревью 10.10.2026, коммит `626f7d79`. Слои: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex, `gpt-6.1-sol`, effort high).

- [x] [Review][Patch] Связанный миграцией менеджер вне групп молча теряется при сохранении формы (решение Alex 10.10.2026: код не менять, шаг 4 выката 42.1 — обязательное условие выката 42.2, поправить Dev Notes «Прод») — `common/0023` связывает любого `is_staff` не суперпользователя (AC1), а поля `manager` правила и `responsible_manager` карточки клиента ограничены `RESPONSIBLE_MANAGER_CHOICES` (группы «Менеджеры»/«Руководители»). Текущего значения нет среди `<option>`, браузер отправляет пустой вариант, а `blank=True` его пропускает. Ошибки «Выберите корректный вариант» из Dev Notes в браузере не будет, она возникает только у тестового клиента, который шлёт pk. Пока id 15 не в «Руководителях», сохранение правила 91 в админке обнулит `manager`: сигнал пересчитает резерв, и у клиентов резерва ответственный станет пустым. Сохранение любой карточки клиента, чей ответственный — id 15, тоже обнулит поле. [backend/apps/users/staff_roles.py:30, backend/apps/common/migrations/0023_link_routing_rules_to_staff.py:35]
- [x] [Review][Patch] Удаление учётной записи менеджера обходит пересчёт (решение Alex 10.10.2026: `on_delete=PROTECT`, при попытке удаления админка сообщает, что сначала нужно назначить клиентам нового менеджера) — `on_delete=SET_NULL` у `ManagerRoutingRule.manager` и `User.responsible_manager` выполняется SQL-обновлением без `post_save` правила. В итоге правило без следа становится «только для писем», а клиенты остаются с пустым ответственным вместо менеджера резерва. Решение 9 описывает блокировку, а не удаление. [backend/apps/common/models.py:1086]
- [x] [Review][Patch] Правило страны с пустым `match_value` проходит `clean()` — массовый пересчёт `clients.filter(country="")` отдаст его менеджеру клиентов с пустой страной, а поштучное разрешение считает их Россией и ищет по коду ИНН. [backend/apps/common/models.py:1161]
- [x] [Review][Patch] Нет теста массового пересчёта по правилу страны — смена менеджера правила «Беларусь» переводит клиентов этой страны и не трогает клиентов другой страны. [backend/apps/users/services/responsible_manager.py:137]
- [x] [Review][Patch] Нет теста исключения сотрудника «только по группе» при массовом `UPDATE` — член группы роли с `is_staff=False`, `is_superuser=False`, `role!="admin"` сохраняет ответственного при пересчёте; параметризовать по трём группам. [backend/apps/users/staff_roles.py:25]
- [x] [Review][Patch] Нет отрицательных тестов форм на выбор неподходящего менеджера — клиент, суперпользователь, сотрудник без группы и сотрудник только из «Маркетинга» отклоняются формами правила и карточки клиента, БД не меняется. [backend/apps/users/staff_roles.py:30]
- [x] [Review][Patch] Нет теста перехода на резерв, когда у найденного правила нет адреса — у активного регионального правила менеджер без email и пустой `manager_email`, ожидаются резервные адреса без пустой строки. [backend/apps/users/services/region_routing.py:67]

**Rejected (12):**

- `low` — `save(update_fields=["tax_id"])` при несохраняемой смене `country` в памяти: ни один вызывающий (`link_1c_customer`, `_update_customer`, верификация) страну так не меняет; исправление добавляет ветвление.
- `low` — `update_fields` генератором расходуется в `set(update_fields)`: в коде таких вызовов нет.
- `low` — `update_fields` четвёртым позиционным аргументом: в Django 5.x позиционные аргументы `save()` устарели, вызовов нет.
- `low` — частичное `rule.save(update_fields=...)` с несохраняемым `manager` в памяти: правила меняются только формой админки полным сохранением.
- `low` — менеджер присвоен в памяти и сохранён только `tax_id` → `assign_responsible_manager` вернёт `False`: надуманный путь, вызывающих нет.
- `false` — дубли активных правил уронят `AddConstraint` в `common/0022`: прод-SELECT 09.10.2026 (Dev Notes, «Прод») — дублей нет.
- `low` — `rule.save()` и пересчёт не в одной транзакции: админка (`changeform_view`) работает в `transaction.atomic`, других путей правки правил нет.
- `low` — устаревший экземпляр пользователя перезаписывает результат массового пересчёта или ручное назначение: гонка с редким изменением правила, исправление требует блокировок.
- `low` — гонка между разрешением менеджера и INSERT нового клиента: то же, окно миллисекунды при редкой правке правил.
- `low` — сигналы правил не пропускают `raw=True`: фикстур с `ManagerRoutingRule` в репозитории нет.
- `false` — менеджер, потерявший доступ, продолжает получать клиентов: так задумано решением 9, передача клиентов — 42.7.
- отклонено (правка спеки) — ожидание `test_fieldsets_structure` 6 → 7 противоречит AC9: новый fieldset требует Task 6, отклонение объяснено в Completion Notes.

#### Повторное ревью 10.10.2026

Диапазон `0b1eae0f..e903851e`: реализация `626f7d79` вместе с правками первого ревью. Слои те же — Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex).

- [x] [Review][Patch] Снятие «Назначен вручную» не возвращает автоматику (решение Alex 10.10.2026: при снятии флага назначать по правилу, если в той же форме не выбран другой менеджер) — хук `User.save()` срабатывает только на создание и смену `tax_id`/`country`. Если снять флаг и не трогать ИНН и страну, у клиента остаётся вручную выбранный менеджер до следующей смены региона или правила. Описание fieldset («Отметьте…, чтобы правила… его не меняли») обещает обратное. Неясно, что делать, если в той же форме одновременно снят флаг и выбран другой менеджер: применить правило или оставить выбор. [backend/apps/users/models.py:396]
- [x] [Review][Patch] Привязка к 1С без смены ИНН не назначает ответственного (решение Alex 10.10.2026: назначать в `link_1c_customer` при любой привязке) — FR-42-08 требует назначать «при верификации и привязке к 1С». Решение 5 сводит привязку к смене ИНН, а явный вызов в `verify_b2b_application` есть только для `MODE_DECISION`. Клиент, созданный до выката, при привязке в режиме `MODE_LINK_ONLY` или действием админки «Связать с 1С» с тем же ИНН остаётся без ответственного до команды 42.3. Это совпадает с фразой «у существующих поле остаётся пустым до команды 42.3», но расходится с текстом FR. [backend/apps/users/services/verify_b2b_application.py:246, backend/apps/users/services/link_1c_customer.py:262]
- [x] [Review][Defer] Менеджер, выведенный из групп после выката, молча теряется в формах — deferred: решение Alex 10.10.2026 — до 42.7, где руководитель управляет сотрудниками и передачей клиентов. это общий случай первого пункта первого ревью. Тогда по решению от 10.10.2026 код оставили, а частный случай с id 15 закрыли шагом выката. Механизм тот же: если менеджера потом уберут из «Менеджеров»/«Руководителей» или снимут `is_staff`, его нет среди `<option>`. Тогда сохранение карточки любого его клиента обнулит `responsible_manager`, даже с флагом «вручную». Сохранение его правила обнулит `manager`, и сигнал переведёт клиентов региона на резерв. [backend/apps/users/staff_roles.py:30]
- [x] [Review][Patch] Нет теста массового пересчёта клиента с пустой страной — `RUSSIA_COUNTRY_VALUES` включает `""`, но проверяется только `region_key`. Если убрать `""`, тесты останутся зелёными, а клиент с пустой страной выпадет из регионального `UPDATE`. [backend/apps/users/services/responsible_manager.py:35]
- [x] [Review][Patch] Нет теста: смена резервного менеджера не трогает зарубежного клиента с правилом страны — в `test_change_fallback_manager` единственный зарубежный клиент из Казахстана, а правила для Казахстана нет. Если убрать `~Q(country__in=covered_countries)`, тесты останутся зелёными. [backend/apps/users/services/responsible_manager.py:132]

**Rejected (19):**

- `low` — сотрудник, добавленный в группу роли после назначения, сохраняет ответственного (`groups.add` ничего не пересчитывает): AC8 требует «не назначается и не меняется», а для исправления нужен сигнал `m2m_changed`.
- `low` — гонка двух одновременных правок одного правила в `store_previous_routing_rule_state`: правила правит один человек и редко, исправление требует блокировок.
- `low` — одновременное создание двух активных правил одного ключа даёт `IntegrityError` вместо сообщения формы: целостность обеспечивает БД, сценарий маловероятен.
- `low` (два замечания: Blind Hunter и Verification Gap) — тесты `common/0023` вызывают функцию миграции напрямую, через текущий реестр, мимо `Migration.operations`: регистрация `RunPython` тривиальна, а тест через `MigrationExecutor` — отдельная инфраструктура для разовой миграции.
- `low` — нет сквозного теста создания клиента процессором импорта: `processor.py:559` создаёт клиента через `User.objects.create` → `save()`, этот путь покрыт тестами регистрации.
- `low` — нет тестов «правилу без менеджера добавили менеджера» и «правило активировали»: оба перехода в `_rule_effect` дают тот же `None → (key, m)`, что и `test_new_rule`.
- `false` — клиент может задать `responsible_manager` через API: сериализаторы в `apps/users/serializers.py` перечисляют поля явно, новых полей там нет.
- отклонено (правка спеки) — в Dev Notes нет плана отката миграций.
- `low` — `save(update_fields=["tax_id"])` при несохраняемой смене `country`: повтор отклонённого в первом ревью.
- `low` — `update_fields` генератором: повтор.
- `low` — `update_fields` позиционным аргументом: повтор.
- `low` — менеджер уже присвоен в памяти, сохраняется только `tax_id`: повтор.
- `low` (два замечания Edge Case Hunter) — устаревший экземпляр пользователя перезаписывает массовый пересчёт или ручное назначение: повтор.
- `low` — гонка между разрешением менеджера и INSERT: повтор.
- `low` — частичное `rule.save(update_fields=["is_active"])` с несохраняемым ключом в памяти: повтор.
- `low` — `rule.save()` вне `atomic`: повтор.
- `low` — сигналы правил не пропускают `raw=True`: повтор, фикстур с `ManagerRoutingRule` нет.

#### Третье ревью 10.10.2026

Диапазон `0b1eae0f..` рабочее дерево: `626f7d79`, `e903851e` и незакоммиченные патчи повторного ревью. Слои те же — Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex).

- [x] [Review][Patch] Снятие «Назначен вручную» вместе с выбором другого менеджера и сменой ИНН или страны: правило перезаписывает выбор — нарушено решение Alex 10.10.2026 («если в той же форме выбран другой менеджер, выбор сохраняется»). Условие `previous.responsible_manager_id == self.responsible_manager_id` ограничивает только `manual_released`, а ветка `region_changed` всё равно вызывает `assign_responsible_manager`: флаг уже снят. Тест `test_admin_form_release_with_other_manager_keeps_choice` регион не меняет. Сообщили три слоя: Blind Hunter, Edge Case Hunter, Acceptance Auditor. [backend/apps/users/models.py:414]
- [x] [Review][Patch] Нет теста приоритета email учётной записи для резервного правила — `_rule_emails` в резервной ветке не проверен. У фикстуры `fallback_rules` нет `manager`, а `test_account_email_wins` идёт через `inn_region`. Если вернуть в резерв чтение `manager_email`, тесты останутся зелёными. На проде у резерва `managermsk3@` миграция `common/0023` связывает учётную запись. [backend/tests/unit/test_region_routing.py:112]
- [x] [Review][Patch] `ManagerRoutingRule.__str__` показывает пустой email учётной записи, а письмо уходит на `manager_email`: у `__str__` нет проверки `manager.email`, которая есть в `_rule_emails`. [backend/apps/common/models.py:1147]
- [x] [Review][Patch] `test_model_delete_with_clients` не изолирует `PROTECT` у `User.responsible_manager`: у менеджера A есть правило 23, и `ProtectedError` даёт `ManagerRoutingRule.manager`. Возврат клиентского FK к `SET_NULL` тест не поймает. [backend/tests/integration/test_responsible_manager_events.py:518]
- [x] [Review][Defer] Менеджер, выведенный из групп, молча теряется в формах (Edge Case Hunter) [backend/apps/users/staff_roles.py:30] — deferred: уже отложено до 42.7 повторным ревью и записано в `deferred-work.md`, повторно не добавляется.

**Rejected (17):**

- `low` (Blind Hunter + Edge Case Hunter, три замечания) — флаг «вручную» снят только в памяти, сохраняется `update_fields=["tax_id"]`: ни один вызывающий код не меняет флаг при частичном сохранении. Чтобы учесть сохранённый флаг, нужна ещё одна ветка.
- `low` (Blind Hunter + Edge Case Hunter) — при снятии флага менеджер изменён в памяти, но не входит в `update_fields`: недостижимо. Админка сохраняет форму целиком.
- `low` — `isdigit()` принимает `²³` и `２３`: в коде региона такие символы не встречаются. Для исправления нужна дополнительная проверка.
- `low` — нет теста «неактивный резерв перед активным» для `common/0023`: миграция разовая и обрабатывает этот случай правильно (неактивное правило не выставляет `fallback_linked`).
- `low` (Blind Hunter + Edge Case Hunter) — нет теста отката и `rule.save()` вне `atomic`: changeform админки и так в `transaction.atomic`, сигнал пересчёта выполняется в той же транзакции. Повтор.
- `false` — внутренние поля доступны через API: сериализаторы `apps/users/serializers.py` перечисляют поля явно, `__all__` и `exclude` нет. Повтор.
- отклонено (правка спеки) — в записях о прогонах нет SHA и команды покрытия.
- `low` — `update_fields=["tax_id"]` при несохраняемой смене `country`: повтор.
- `low` — `update_fields` генератором: повтор.
- `low` — `update_fields` позиционным аргументом: повтор.
- `low` — менеджер уже присвоен в памяти, сохраняется только `tax_id`: повтор.
- `low` — устаревший экземпляр перезаписывает массовый пересчёт: повтор.
- `low` — гонка между разрешением менеджера и INSERT: повтор.
- `low` — `rule.save(update_fields=…)` с несохраняемым ключом: повтор.
- `low` — одновременное перемещение одного правила двумя транзакциями: повтор.
- `low` — сигналы правил не пропускают `raw=True`: повтор.
- `false` — `TypeError` в `clean()` при `match_value=None`: поле не `null`, по умолчанию `""`, форма админки передаёт строку. До `None` дойти нельзя.

#### Четвёртое ревью 10.10.2026

Диапазон `626f7d79^..b045f50e` без `_bmad-output/`: реализация и три коммита правок (`e903851e`, `0c1fbfe1`, `b045f50e`). Слои те же — Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex). Все отработали.

- [x] [Review][Patch] Нет теста: массовый пересчёт не трогает учётную запись с `role="admin"` — условие `Q(role="admin")` в `staff_accounts_q()` добавлено ради робота обмена 1С (решение 7). Проверено только поштучное назначение: `TestIsStaffAccount.test_flags` и тест создания/смены ИНН в `test_responsible_manager_events.py`. Массовые тесты используют группы (`test_role_group_member_untouched_by_mass_update`) и `is_staff` (`test_staff_in_region_untouched_by_direct_call`). Если убрать `Q(role="admin")`, тесты останутся зелёными, а робот без ИНН получит менеджера при первой смене резервного правила. Нужен тест в `TestReassignClientsForKey`: аккаунт с `role="admin"`, `is_staff=False`, без групп; после смены менеджера правила его ответственный в БД не меняется. [backend/apps/users/staff_roles.py:25]

**Rejected (33):**

- `false` (Blind Hunter, Edge Case Hunter, Verification Gap) — дубли активных правил уронят `AddConstraint` в `common/0022`: повтор, прод-SELECT 09.10.2026 дублей не нашёл.
- `false` (Blind Hunter) — миграции не назначают ответственного существующим клиентам: так задумано, это команда 42.3 («Чего в этой стори нет»).
- `false` (Blind Hunter, Edge Case Hunter) — `common/0023` связывает любого `is_staff`, а не только членов групп «Менеджеры»/«Руководители»: этого критерия прямо требует AC1. Расхождение с формами разобрано в первом ревью и закрыто шагом 4 выката 42.1.
- `false` (Blind Hunter) — менеджер, потерявший роль, продолжает получать клиентов: повтор, так задумано решением 9, передача клиентов — 42.7.
- `false` (Edge Case Hunter) — `TypeError` в `clean()` при `match_value=None`: повтор.
- `low` (все четыре слоя, 8 замечаний) — `save(update_fields=["tax_id"])` при несохраняемой смене `country` или снятии флага «вручную» в памяти: повтор.
- `low` (Edge Case Hunter, Verification Gap, Acceptance Auditor, 3 замечания) — менеджер присвоен или изменён в памяти, но не попадает в `update_fields`: повтор.
- `low` (все четыре слоя, 4 замечания) — частичное `rule.save(update_fields=…)` с несохраняемым ключом, менеджером или активностью в памяти: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — `rule.save()` и пересчёт не в одной транзакции: повтор, changeform админки работает в `transaction.atomic`.
- `low` (Blind Hunter, Edge Case Hunter) — гонка между разрешением менеджера и INSERT клиента: повтор.
- `low` (Blind Hunter) — клиент, ставший сотрудником, сохраняет ответственного: повтор отклонённого во втором ревью, для исправления нужен `m2m_changed`.
- `low` (Blind Hunter) — тест `common/0023` через текущий реестр, а не `MigrationExecutor`: повтор.
- `low` (Edge Case Hunter) — `update_fields` итератором или четвёртым позиционным аргументом: повтор.
- `low` (Edge Case Hunter) — сигналы правил не пропускают `raw=True`: повтор.
- отклонено (правка спеки, Acceptance Auditor) — ожидание `test_fieldsets_structure` 6 → 7 противоречит AC9: повтор.

#### Пятое ревью 10.10.2026

Диапазон `0b1eae0f..18d0da71`, только `backend/`: реализация и четыре коммита правок (`e903851e`, `0c1fbfe1`, `b045f50e`, `18d0da71`). Слои те же — Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex). Все отработали.

- [x] [Review][Defer] Резервное правило принимает обычного менеджера, а не руководителя (решение Alex 10.10.2026: до 42.7, где руководитель управляет сотрудниками и правилами) — FR-42-05: «Резервное правило указывает на руководителя», SPEC CAP-2: «клиент без подходящего правила достаётся руководителю из резервного правила». У поля `ManagerRoutingRule.manager` общий `limit_choices_to=RESPONSIBLE_MANAGER_CHOICES`, где допустимы обе группы — «Менеджеры» и «Руководители». В `clean()` нет проверки для `fallback`, а `resolve_responsible_for_key()` отдаёт `fallback.manager` без проверки группы. Поэтому форма админки пропустит резерв на сотрудника только из «Менеджеров», и ему уйдут все клиенты без регионального правила. Ни одно AC такой проверки не требует. На проде резерв (правило 91) указывает на id 15, он в «Руководителях». [backend/apps/common/models.py:1094, backend/apps/users/services/responsible_manager.py:72]
- [x] [Review][Patch] Нет отрицательного теста форм на члена разрешённой группы с `is_staff=False` — в `UNSUITABLE_MANAGERS` кандидата отсекает другое условие: группа, `is_superuser` или отсутствие группы. Если убрать `is_staff=True` из `RESPONSIBLE_MANAGER_CHOICES`, все тесты останутся зелёными. Добавить вариант «группа есть, `is_staff=False`» и параметризовать его по «Менеджерам» и «Руководителям». [backend/apps/users/staff_roles.py:30, backend/tests/integration/test_responsible_manager_events.py:475]
- [x] [Review][Patch] Нет теста адреса письма на уровне задачи — `test_send_success` запускает `send_manager_region_email` с правилом без `manager`. Выбор `manager.email` вместо `manager_email` (AC7) проверен только на helper `resolve_manager_recipients`. Нужен тест задачи: правило с менеджером, адреса учётной записи и `manager_email` разные, в `mail.outbox[0].to` (locmem) ожидается адрес учётной записи. [backend/apps/users/services/region_routing.py:61, backend/tests/unit/test_region_routing.py:153]

**Rejected (21):**

- `false` (Blind Hunter, Edge Case Hunter) — дубли активных правил уронят `AddConstraint` в `common/0022`: повтор, прод-SELECT 09.10.2026 дублей не нашёл.
- `false` (Blind Hunter) — `common/0023` связывает любого `is_staff`, а не только членов групп: повтор, так требует AC1, расхождение с формами закрыто шагом 4 выката 42.1.
- `false` (Blind Hunter) — миграции не назначают ответственного существующим клиентам: повтор, это команда 42.3.
- `low` (Blind Hunter, Edge Case Hunter, 5 замечаний) — `save(update_fields=["tax_id"])` при несохраняемой смене `country` или снятии флага «вручную» в памяти: повтор.
- `low` (Blind Hunter, Edge Case Hunter, 4 замечания) — менеджер присвоен или изменён в памяти, но не попадает в `update_fields`: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — частичное `rule.save(update_fields=…)` с несохраняемым состоянием в памяти: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — `rule.save()` и пересчёт не в одной транзакции: повтор, changeform админки работает в `transaction.atomic`.
- `low` (Edge Case Hunter) — гонка между разрешением менеджера и INSERT клиента: повтор.
- `low` (Edge Case Hunter) — `update_fields` генератором: повтор.
- `low` (Edge Case Hunter) — сигналы правил не пропускают `raw=True`: повтор.
- `low` (Blind Hunter) — тест `common/0023` через текущий реестр, а не `MigrationExecutor`: повтор.

#### Шестое ревью 11.10.2026

Диапазон `0b1eae0f..dd461a08`: реализация и пять коммитов правок (`e903851e`, `0c1fbfe1`, `b045f50e`, `18d0da71`, `dd461a08`). Слои те же — Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex). Все отработали. У Acceptance Auditor замечаний нет.

- [x] [Review][Patch] Нет теста: существующее правило без менеджера получает первого менеджера, клиенты региона уходят от резерва к нему (Verification Gap). Именно так пройдёт выкат: 91 правило на проде останется без `manager`, и учётные записи им будут назначать в форме админки. `test_replace_manager_in_rule` меняет менеджера A на B, `test_new_rule` начинает с `old=None`, а `test_rules_without_manager_affect_nobody` менеджера не задаёт. Ранний выход в `affected_keys` при `old is not None and old_effect is None` все тесты пропустят, хотя клиенты региона останутся у резерва. Нужен `TestRuleChangeFromAdmin.test_first_manager_moves_clients_from_fallback`: активное правило региона только с `manager_email`, его клиенты на резервном менеджере. Форма сохраняет правило с менеджером B, после чего клиенты в БД у B, а ручное назначение не тронуто. Во втором ревью этот пункт отклонили: переход `None → (key, m)` в `_rule_effect` такой же, как в `test_new_rule`. Мутация показывает, что тест нового правила не проверяет путь от прежнего состояния правила. [backend/tests/integration/test_responsible_manager_events.py:430, backend/apps/users/services/responsible_manager.py:177]

**Rejected (28):**

- `low` (все три слоя кода, 6 замечаний) — `save(update_fields=["tax_id"])`, а страна, флаг «вручную» или признаки сотрудника изменены только в памяти: повтор.
- `low` (Blind Hunter, Edge Case Hunter, 4 замечания) — менеджер присвоен или выбран в памяти, но не входит в `update_fields`: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — `update_fields` генератором: повтор.
- `low` (Edge Case Hunter) — `update_fields` четвёртым позиционным аргументом: повтор.
- `low` (все три слоя кода, 3 замечания) — частичное `rule.save(update_fields=…)`, а ключ, активность или менеджер изменены только в памяти: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — сигналы правил не пропускают `raw=True`: повтор, фикстур с `ManagerRoutingRule` нет.
- `low` (Blind Hunter, Edge Case Hunter) — гонка между разрешением менеджера и INSERT клиента: повтор.
- `low` (Blind Hunter, Edge Case Hunter) — `rule.save()` вне `atomic` и нет теста совместного отката: повтор, changeform админки работает в `transaction.atomic`.
- `low` (Edge Case Hunter) — устаревший экземпляр пользователя перезаписывает массовый пересчёт: повтор.
- `low` (Edge Case Hunter) — одно правило одновременно переносят две транзакции: повтор.
- `low` (Verification Gap) — нет сквозного теста назначения при создании контрагента процессором импорта: повтор отклонённого во втором ревью. `_create_customer` идёт через `save()` с `previous is None`, этот путь покрыт тестами регистрации. Ранний выход для `created_in_1c` надуман.
- уже отложено до 42.7 (Edge Case Hunter) — менеджер, выведенный из групп, теряется в формах. Пункт уже есть в `deferred-work.md`.
- уже отложено до 42.7 (Edge Case Hunter) — резервное правило принимает обычного менеджера: отложено пятым ревью.
- отклонено (правка спеки, Blind Hunter) — Completion Notes пишет «до 42.3 ответственного получают только новые и изменившиеся клиенты», а привязка к 1С и верификация назначают ответственного и существующим клиентам.

#### Седьмое ревью 11.10.2026

Диапазон `26207161..` рабочее дерево на `dd461a08`, только 21 файл кода и тестов из File List стори 42.2; незакоммиченный тест первого менеджера включён. Diff: 2062 добавления, 34 удаления, 2445 строк. Слои: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (Codex). Все завершились; у Acceptance Auditor новых нарушений нет. Ограничение Blind Hunter: он сообщил, что дополнительно прочитал `SKILL.md`, несмотря на запрет чтения других файлов; его выводы проверены при разборе, как и выводы остальных слоёв. Backend-прогон и мутации в этом ревью не выполнялись.

GitNexus: индекс свежий на `dd461a08`; `detect-changes --scope all` — `No changes detected` для незакоммиченных изменений. `impact` по диапазону реализации: `User.save` — HIGH (5 прямых вызывающих, 3 процесса), `assign_responsible_manager` — HIGH (3 прямых вызывающих, 3 процесса), `link_1c_customer` — LOW (2 прямых вызывающих, 2 процесса), `reassign_clients_for_key` — LOW (1 прямой вызывающий).

- [x] [Review][Patch] Нет теста выключения резервного правила с менеджером [backend/tests/unit/test_responsible_manager.py:268, backend/apps/users/services/responsible_manager.py:63-70] — Verification Gap: `test_inactive_rule_ignored` проверяет только регион, массовые тесты резерва меняют менеджера или снимают его, но не выключают правило. Если резервный поиск перестанет учитывать `is_active`, эти тесты не обнаружат сохранение прежнего ответственного у клиентов выключенного резерва. Добавить `TestReassignClientsForKey.test_deactivate_fallback_clears_responsible`: выключить единственный резерв с менеджером, проверить `responsible_manager=None` в БД у автоматических клиентов резерва и неизменность региональных и ручных назначений. Текущий код фильтрует активность правильно; находка — пробел защиты от регрессии, не воспроизведённый дефект реализации.

Решение Alex 11.10.2026: оставить единственный patch как action item, без правок кода и тестов. Статус стори и sprint-status: `review → in-progress` до добавления теста выключения резерва.

**Rejected (23):**

- `false` (Blind Hunter) — дубли активных правил уронят `common/0022`: условие отсутствует в проверенной целевой базе; Dev Notes «Прод» фиксирует SELECT 09.10.2026 без дублей. Повтор первого ревью.
- `false` (Blind Hunter) — миграция выбирает менеджера без разрешённой группы: выбор по `is_staff` и email прямо задан AC1; допустимость в формах обеспечивается обязательным шагом выката 42.1 для id 15. Последующая утрата группы уже отложена до 42.7.
- `false` (Blind Hunter) — отсутствует первоначальный пересчёт клиентов: это прямо исключено из 42.2 и отнесено к команде 42.3.
- `low` (Blind Hunter) — частичный `User.save` рассчитывает по несохранённой стране или ручному флагу: реальный эффект при таком сочетании, но штатные вызывающие не меняют эти поля вне `update_fields`; админка и импорт сохраняют целиком. Исправление добавляет ветвление. Повтор.
- `low` (Blind Hunter) — заранее присвоенный в памяти менеджер не добавляется в `update_fields`: эффект возможен, но привязка и верификация явно добавляют поле после назначения; показанного штатного вызывающего для ошибочного сочетания нет. Исправление добавляет условие. Повтор.
- `low` (Blind Hunter) — сигнал использует несохранённые поля правила: эффект возможен при частичном сохранении, но формы админки сохраняют правило целиком; миграция работает с исторической моделью без этих ресиверов. Исправление усложняет сбор состояния. Повтор.
- `low` (Blind Hunter) — нет обработки `raw=True` у сигналов правила: фикстур с этой моделью не обнаружено, повседневного пути нет; дополнительный guard не требуется для существующих путей. Повтор.
- `low` (Blind Hunter) — обычный `rule.save` в autocommit может оставить частичный пересчёт: штатная правка правила через админку транзакционна; добавление ещё одной границы транзакции для непоказанного пути не оправдано. Повтор.
- `low` (Blind Hunter) — гонка назначения клиента со сменой правила: возможна в редком конкурентном окне, уже отклонена; механизм согласования существенно усложняет сохранение каждого клиента.
- `false` (Blind Hunter) — после отключения менеджера новые клиенты всё ещё назначаются ему: так прямо предписывает решение 9, передача клиентов относится к 42.7; последующая утрата группы и поведение форм уже отложены.
- `false` (Edge Case Hunter) — дубли перед добавлением ограничения: повтор, проверенные целевые данные не содержат дублей.
- `false` (Edge Case Hunter) — миграция не проверяет разрешённые группы: повтор, критерий AC1 и обязательный шаг выката согласованы владельцем.
- `low` (Edge Case Hunter) — несохранённая страна или ручной флаг влияют на частичный `User.save`: повтор; штатного вызывающего для такого сочетания нет, исправление добавляет ветки.
- `low` (Edge Case Hunter) — менеджер выбран в памяти при снятии флага, но не включён в `update_fields`: штатная форма сохраняет все эти поля; исправление добавляет проверки для непоказанного пути. Повтор.
- `low` (Edge Case Hunter) — правильный менеджер уже в памяти, поэтому `update_fields` его не сохраняет: привязка и верификация добавляют поле явно, остальные штатные пути сохраняют целиком. Повтор.
- `low` (Edge Case Hunter) — одноразовый итератор `update_fields` исчерпывается: эффект реален, но таких вызовов нет; исправление требует дополнительной нормализации. Повтор.
- `low` (Edge Case Hunter) — гонка разрешения менеджера и сохранения клиента: повтор редкого конкурентного окна; согласование требует нового механизма блокировок.
- `low` (Edge Case Hunter) — сигнал пересчитывает по несохранённому менеджеру правила: повтор; штатные формы сохраняют целиком, историческая модель миграции не запускает сигнал.
- `low` (Edge Case Hunter) — `raw=True` перезаписывает назначения при загрузке фикстур: фикстур с правилами не обнаружено; дополнительный guard для непоказанного пути. Повтор.
- `low` (Edge Case Hunter) — ошибка пересчёта после autocommit сохранения правила: повтор; штатный путь админки уже в транзакции.
- `low` (Verification Gap, Other findings) — частичный save устаревшего пользователя оставляет менеджера, записанного массовым пересчётом: реальная разновидность уже отклонённой гонки; требуется редкое конкурентное изменение правила и сохранение старого экземпляра, исправление добавляет условие сравнения с БД.
- `low` (Verification Gap, Other findings) — несохраняемое снятие ручного флага вместе со сменой ИНН перезаписывает ручное назначение: повтор; штатного вызывающего с таким сочетанием нет, исправление добавляет ветвление.
- `low` (Verification Gap, Other findings) — перенос ключа правила при несохраняемом `manager=None` пропускает новый регион: повтор; админка сохраняет весь объект, усложнять сбор состояния для непоказанного пути не требуется.

#### Восьмое ревью 11.10.2026

Диапазон `26207161..` рабочее дерево на `dd461a08`, только 21 файл кода и тестов стори 42.2. Включены незакоммиченные тесты первого менеджера и выключения резерва. Diff: 2078 добавлений, 34 удаления, 2461 строка. Все четыре слоя (Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor) завершились. Acceptance Auditor новых нарушений AC не обнаружил. Проверка статическая: backend-тесты и мутации в этом запуске не выполнялись; результаты прогонов в Debug Log и Change Log относятся к предыдущим доработкам.

GitNexus: индекс свежий на `dd461a08`, `detect-changes --scope all` — `No changes detected`; diff рабочего дерева по `backend/apps/users` и `backend/apps/common` пуст. `assign_responsible_manager` — HIGH (3 прямых вызывающих: `User.save`, верификация, привязка к 1С; 3 затронутых процесса), `reassign_clients_for_key` — LOW (1 прямой вызывающий, 0 процессов).

- [x] [Review][Patch] Нет теста повторного включения существующего неактивного правила [backend/apps/users/services/responsible_manager.py:177, backend/tests/integration/test_responsible_manager_events.py:455] — Verification Gap: тесты покрывают выключение, создание и добавление менеджера активному правилу, но не переход существующего правила `is_active=False → True`. Если в `affected_keys` появится ранний выход для `old is not None and not old["is_active"]`, эти проверки не обнаружат пропуск пересчёта: новые клиенты будут назначаться по включённому правилу, а существующие останутся у резерва. Добавить `TestRuleChangeFromAdmin.test_reactivate_rule_moves_clients_from_fallback`: включить существующее правило с менеджером через форму, проверить ответственного в БД у обычных клиентов региона и неизменность ручных назначений. Текущий код переход обрабатывает правильно; это пробел защиты от регрессии. Мутация приведена как мысленный пример, не как выполненная проверка.

**Rejected (23):**

- `false` (Blind Hunter) — дубли активных правил уронят миграцию: Dev Notes фиксирует проверку целевой базы без дублей, условие отсутствует. Повтор.
- `false` (Blind Hunter) — критерий миграции шире критериев формы: это утверждённый AC1; совместимость текущего менеджера с формой обеспечена обязательным шагом выката, последующая утрата группы уже отложена.
- `false` (Blind Hunter) — нет первоначального назначения и проверки такого перехода миграций: первоначальное назначение прямо исключено из 42.2 и относится к 42.3; требование такого поведения при миграции не установлено.
- `low` (Blind Hunter) — несохраняемая страна влияет на частичный save: эффект реален при таком сочетании, но штатного вызывающего нет; исправление добавляет ветви для сборки сохраняемого состояния. Повтор.
- `low` (Blind Hunter) — несохраняемый или устаревший ручной флаг допускает перезапись: повтор редкого сочетания частичного сохранения с несохранённым либо конкурентно изменённым состоянием; исправление усложняет общий save.
- `low` (Blind Hunter) — менеджер в старом объекте совпадает с новым правилом, а в БД уже другой: разновидность ранее отклонённой гонки с массовым пересчётом; сравнение с БД добавляет условие для редкого конкурентного пути.
- `low` (Blind Hunter) — выбор менеджера вне update_fields подавляет автоматику: штатная форма сохраняет весь выбор, показанного вызывающего для комбинации нет; исправление добавляет проверки. Повтор.
- `low` (Blind Hunter) — сигнал использует несохранённое состояние правила: штатная админка сохраняет целиком, исторические модели миграций не запускают эти ресиверы; исправление усложняет сбор состояния. Повтор.
- `low` (Blind Hunter) — нет обработки raw=True: фикстур с правилами не обнаружено, повседневного пути нет; дополнительный guard для непоказанного сценария. Повтор.
- `low` (Blind Hunter) — обычное сохранение правила не атомарно с пересчётом: штатный путь через админку уже транзакционен; новая граница транзакции для непоказанного вызывающего не оправдана. Повтор.
- `false` (Blind Hunter) — не определено поведение при блокировке или утрате роли менеджером: поведение определено решением 9, передача клиентов — 42.7; потеря значения в форме после утраты группы уже отложена.
- `false` (Edge Case Hunter) — дубли старых активных правил: целевые данные проверены, дублей нет. Повтор.
- `low` (Edge Case Hunter) — несохранённая страна влияет на менеджера: повтор, штатные частичные сохранения её так не меняют; исправление добавляет ветви.
- `low` (Edge Case Hunter) — несохранённое снятие ручного флага перезаписывает ручное назначение: повтор, штатного вызывающего нет; исправление добавляет ветви.
- `low` (Edge Case Hunter) — менеджер в памяти совпадает с правилом, а поле исключено из update_fields: повтор; привязка и верификация добавляют поле явно, остальные штатные пути сохраняют целиком.
- `low` (Edge Case Hunter) — несохраняемый выбор подавляет назначение при снятии флага: повтор, админка сохраняет все поля; исправление добавляет проверки для непоказанного пути.
- `low` (Edge Case Hunter) — назначение менеджера правилу при несохраняемой смене ключа пересчитывает другой регион: повтор, штатная форма сохраняет целиком; исправление усложняет сбор состояния.
- `low` (Edge Case Hunter) — удаление активного правила после несохранённого is_active=False пропускает пересчёт: эффект возможен, но штатная страница удаления и массовое удаление используют экземпляры с сохранённым состоянием; нового pre_delete для непоказанного пути не требуется.
- `low` (Edge Case Hunter) — raw=True запускает пересчёт до загрузки связей: фикстур с правилами не обнаружено, штатного пути нет; дополнительный guard. Повтор.
- `low` (Edge Case Hunter) — ошибка пересчёта после autocommit сохранения: повтор, штатная админка обеспечивает atomic; добавлять новую транзакционную границу для непоказанного пути не требуется.
- `low` (Edge Case Hunter) — гонка регистрации со сменой правила: повтор редкого конкурентного окна; исправление требует механизма согласования и блокировок.
- `low` (Edge Case Hunter) — полное сохранение старого пользователя возвращает менеджера до пересчёта: повтор редкого конкурентного изменения; исправление требует отслеживания исходного состояния и дополнительных ветвей.
- `low` (Edge Case Hunter) — старое правило country=Россия получает менеджера через save в обход clean: эффект возможен для некорректного правила, но сид и проверенные прод-правила содержат только Беларусь и Казахстан, форма отклоняет Россию; guard усложняет сервис для непоказанного пути.

#### Девятое ревью 11.10.2026

Диапазон `26207161..` рабочее дерево на `dd461a08`, 21 файл кода и тестов из File List: 2078 добавлений, 34 удаления. Включены незакоммиченные тесты первого менеджера и выключения резерва. Все четыре слоя (Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor) завершились через Codex Companion. Команды запущены с запрошенным foreground timeout 600000; инструмент терминала автоматически вернул фоновые идентификаторы, после чего результаты всех четырёх дождались в том же ходе workflow. Проверка статическая: Docker/pytest, линтеры и мутации в этом запуске не выполнялись. `git diff --check` для backend-изменений прошёл.

GitNexus: индекс актуален на `dd461a08`; `detect-changes --scope all` — `No changes detected` только для незакоммиченной дельты, не для всего диапазона стори. `assign_responsible_manager` — HIGH: 3 прямых вызывающих (`User.save`, `verify_b2b_application`, `link_1c_customer`), 3 процесса; `reassign_clients_for_key` — LOW: 1 прямой вызывающий (`_reassign_affected`), 0 процессов в графе.

Новых `decision-needed`, `patch` и `defer` нет; отклонено 34 замечания. Единственный открытый action item восьмого ревью — тест повторного включения существующего неактивного правила — сохраняется без изменения и без дублирования. В текущих тестах есть выключение, создание и первый менеджер у активного правила, но нет перехода существующего правила `is_active=False → True`. Статус стори и sprint-status: `review → in-progress` из-за этого незакрытого пункта, а не из-за нового дефекта реализации.

**Rejected (34):**

- R1 — `false` (Blind Hunter): миграцию остановят старые дубли активных ключей. Условие отсутствует в целевых данных, проверенных SELECT 09.10.2026 (Dev Notes «Прод»); новая схема намеренно запрещает дубли. Повтор.
- R2 — `false` (Blind Hunter): миграция выбирает недопустимого менеджера. Критерий `is_staff=True`, не суперпользователь, прямо установлен AC1; для единственного связываемого прод-аккаунта id 15 совместимость с формами обеспечена обязательным шагом выката. Последующая утрата группы уже отложена до 42.7.
- R3 — `false` (Blind Hunter): не выполнено первоначальное назначение существующим клиентам. Это прямо исключено из 42.2 и отнесено к команде 42.3; отсутствие пересчёта в миграции соответствует объёму.
- R4 — `low` (Blind Hunter): частичный save использует несохранённую страну или ручной флаг. Эффект возможен, но проверенные вызывающие не создают сочетание: форма и импорт сохраняют целиком, привязка не меняет эти поля, профиль компании меняет только сохраняемые реквизиты. Исправление требует дополнительных ветвей сборки состояния. Повтор.
- R5 — `low` (Blind Hunter): устаревший экземпляр после массового пересчёта не записывает менеджера при частичном save. Реальный эффект в редком конкурентном окне; уже разобранная гонка требует дополнительного сравнения с БД. Повтор.
- R6 — `low` (Blind Hunter): сигнал правила использует несохранённые атрибуты. Возможен при специально составленном частичном save; штатные формы сохраняют правило целиком, data-миграция использует исторические модели без этих сигналов. Исправление усложняет сбор состояния. Повтор.
- R7 — `low` (Blind Hunter): сигналы не пропускают `raw=True`. Фикстур маршрутизации в проверенном каталоге фикстур нет; дополнительный guard закрывает непоказанный штатный путь. Повтор.
- R8 — `low` (Blind Hunter): правило и пересчёт не атомарны при обычном save вне внешней транзакции. Штатная правка через Django Admin транзакционна; для непоказанного вызывающего потребуется новая граница транзакции. Повтор.
- R9 — `low` (Blind Hunter): регистрация гоняется со сменой правила. Возможное редкое конкурентное окно уже отклонено; исправление требует общего механизма синхронизации сохранения клиентов и правил. Повтор.
- R10 — `low` (Blind Hunter): сотрудник, добавленный в группу после создания, сохраняет ответственного. В момент INSERT членства ещё нет; AC8 требует не менять назначение при последующих автоматических событиях, а не очищать его при смене группы. Для нового поведения нужен `m2m_changed`; сценарий уже разобран во втором ревью.
- R11 — `false` (Edge Case Hunter): старые дубли остановят миграцию. В проверенных целевых данных дублей нет (Dev Notes «Прод»). Повтор R1.
- R12 — `false` (Edge Case Hunter): миграция обязана фильтровать разрешённые группы. Это противоречит утверждённому критерию AC1; целевой аккаунт включён в «Руководителей» обязательным шагом выката. Повтор R2.
- R13 — `low` (Edge Case Hunter): несохранённая страна влияет на частичный save ИНН. Эффект реален при таком сочетании, но проверенные штатные вызывающие его не создают; исправление добавляет сборку сохраняемого состояния. Повтор R4.
- R14 — `low` (Edge Case Hunter): несохранённое снятие ручного флага допускает его перезапись. Эффект реален при таком сочетании, но штатного вызывающего нет; исправление требует дополнительных ветвей. Повтор R4.
- R15 — `low` (Edge Case Hunter): выбор менеджера вне `update_fields` подавляет возврат к правилу. Штатная форма сохраняет выбранного менеджера и ручной флаг вместе; исправление добавляет проверки для непоказанного сочетания. Повтор третьего ревью.
- R16 — `low` (Edge Case Hunter): устаревший менеджер в экземпляре совпадает с новым разрешением. Разновидность уже отклонённой гонки с массовым пересчётом; исправление требует сравнения с БД. Повтор R5.
- R17 — `low` (Edge Case Hunter): одноразовый итератор `update_fields` исчерпывается. Возможный эффект, но в проверенных вызывающих используются списки; дополнительная нормализация защищает непоказанный путь. Повтор.
- R18 — `low` (Edge Case Hunter): позиционный `update_fields` игнорируется хуком. Таких вызовов в проверенных путях нет; позиционные аргументы save устарели в Django 5.x. Исправление требует нового разбора аргументов. Повтор.
- R19 — `low` (Edge Case Hunter): частичная активация правила с несохранённым ключом пересчитывает другой регион. Штатная форма сохраняет состояние целиком; исправление усложняет получение нового состояния для непоказанного вызывающего. Повтор R6.
- R20 — `low` (Edge Case Hunter): `raw=True` запускает преждевременный пересчёт. Фикстур с правилами в проверенном каталоге нет; требуется дополнительный guard для непоказанного пути. Повтор R7.
- R21 — `low` (Edge Case Hunter): удаление устаревшего экземпляра правила пересчитывает прежний ключ. Эффект возможен при конкурентном перемещении правила; штатные страницы удаления получают сохранённый экземпляр, исправление требует захвата состояния в новом pre_delete. Разновидность ранее разобранной гонки.
- R22 — `low` (Edge Case Hunter): autocommit сохраняет правило до сбоя пересчёта. Штатный путь админки обеспечивает atomic; новая транзакционная граница для непоказанного вызывающего не оправдана. Повтор R8.
- R23 — `low` (Edge Case Hunter): правило меняется между разрешением и сохранением клиента или массовым UPDATE. Реальное редкое конкурентное окно; общий механизм блокировок уже отклонён. Повтор R9.
- R24 — `low` (Edge Case Hunter, проверка claims): возврат к правилу при снятии ручного флага не работает для выбора менеджера вне `update_fields`. Штатная форма сохраняет поля совместно; новая проверка защищает непоказанное сочетание. Повтор R15.
- R25 — `low` (Verification Gap): прямой тест функции data-миграции не проверяет регистрацию RunPython через MigrationExecutor. Пробел подтверждён слоем и принят как факт: удаление operations не поймают прямые тесты. Сейчас RunPython зарегистрирован корректно, Task 7 явно задаёт прямой вызов функции, а замечание уже отклонено во втором ревью. Новый исторический тест обновления требует отдельной миграционной инфраструктуры для разовой тривиальной регистрации; повторно не открывается.
- R26 — `low` (Verification Gap, прочие находки): вычисленный менеджер уже в памяти и не включается в `update_fields`. Эффект возможен, но привязка и верификация явно добавляют поле после назначения, прочие штатные пути сохраняют целиком; исправление добавляет условие для непоказанного вызывающего. Повтор.
- R27 — `low` (Verification Gap, прочие находки): частичный save использует несохранённую страну или ручной флаг. Проверенные штатные вызывающие этого сочетания не создают; исправление добавляет ветви. Повтор R4.
- R28 — `low` (Verification Gap, прочие находки): сигнал читает несохранённый ключ при сохранении только manager. Штатная форма сохраняет целиком, историческая data-миграция не вызывает эти ресиверы; исправление усложняет сбор состояния. Повтор R6.
- R29 — `false` (Verification Gap, прочие находки): миграцию остановят разрешённые старой схемой дубли. В проверенных целевых данных условие отсутствует (Dev Notes «Прод»). Повтор R1.
- R30 — `low` (Acceptance Auditor): назначение по несохранённой стране при частичном save. Возможный эффект, но нет проверенного штатного вызывающего; для исправления нужна дополнительная сборка состояния. Повтор R4.
- R31 — `low` (Acceptance Auditor): менеджер заранее выбран в памяти и не сохраняется вместе с ИНН. Штатные привязка и верификация включают поле явно, остальные формы и импорт сохраняют целиком; исправление добавляет условие для непоказанного сочетания. Повтор R26.
- R32 — `low` (Acceptance Auditor): несохранённое снятие ручного флага позволяет перезапись. Штатная форма сохраняет флаг вместе с ИНН; проверенные частичные сохранения его не меняют. Дополнительные ветви для непоказанного вызывающего. Повтор R4.
- R33 — `low` (Acceptance Auditor): частичное сохранение кода правила пропускает новый регион из-за несохранённого manager. Штатная форма сохраняет поля целиком; исправление усложняет сбор состояния. Повтор R6.
- R34 — отклонено (Acceptance Auditor, правка спеки): счётчик fieldsets существующего теста изменён 6 → 7 вопреки буквальному AC9. Это верный факт, но необходимый седьмой блок предписан Task 6, а отклонение явно согласовано в Completion Notes (отклонение 2); исправление было бы правкой спеки, а не кода. Повтор первого ревью.

#### Десятое ревью 11.10.2026

Диапазон `26207161..` рабочее дерево на `dd461a08`: 21 файл кода и тестов из File List, 2105 добавлений, 34 удаления, 2488 строк diff. Включены незакоммиченные тесты первого менеджера, выключения резерва и повторного включения правила. Все четыре слоя (Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor) завершились через Codex Companion. Терминалу передан foreground timeout 600000; инструмент автоматически перевёл команды в фон, после чего результаты всех слоёв дождались в том же ходе workflow. Acceptance Auditor новых нарушений AC и согласованных ограничений не обнаружил.

Проверка статическая: Docker/pytest, линтеры, проверки AC9 и мутации в этом запуске не выполнялись. `git diff --check` по проверяемым backend-файлам прошёл. Числа прогонов в Debug Log и Change Log относятся к предыдущим доработкам, не к этому ревью. При проверке результатов прочитаны текущие модели, сигналы, сервисы, миграции, формы и штатные вызывающие частичных сохранений: привязка, верификация, реквизиты компании, синхронизация клиентов и сериализатор профиля.

GitNexus: индекс актуален на `dd461a08`; `detect-changes --scope all` — `No changes detected` для незакоммиченной дельты, не для всего диапазона стори. `assign_responsible_manager` — HIGH: 3 прямых вызывающих (`User.save`, `verify_b2b_application`, `link_1c_customer`), 3 процесса; `reassign_clients_for_key` — LOW: 1 прямой вызывающий (`_reassign_affected`), 0 процессов в графе.

Новых `decision-needed`, `patch` и `defer` нет; 31 замечание отклонено после индивидуального разбора. Пробел проверки выполнения `RunPython` признан реальным, но повторно не открывается: алгоритм проверяется прямыми тестами по Task 7, операция зарегистрирована, историческая миграционная проверка потребует отдельной инфраструктуры. Редкие сочетания частичных сохранений и гонки не объявляются невозможными: они отклонены как `low` для проверенных штатных путей, потому что исправление добавляет дополнительные ветви или механизм блокировок. Уже согласованные отложения до 42.7 сохраняются без дублирования.

Последний прежний action item закрыт в текущем дереве: `TestRuleChangeFromAdmin.test_reactivate_rule_moves_clients_from_fallback` включает существующее неактивное правило через форму и проверяет в БД переход обычных клиентов от резерва и сохранность ручного назначения. Незакрытых `[Review]` action items нет. По результату workflow статус стори и `development_status` синхронизированы: `review → done`. Это результат статического ревью, не новый прогон AC9 и не подтверждение production-выката.

**Rejected (31):**

- R1 — `false` (Blind Hunter): миграцию остановят старые дубли активных ключей. Для целевой базы условие отсутствует: Dev Notes «Прод» фиксирует SELECT 09.10.2026 без дублей, сид `common/0018` также задаёт уникальные ключи. Общая возможность ошибки на другой базе с дублями не оспаривается.
- R2 — `false` (Blind Hunter): критерий связывания обязан совпадать с ограничением групп в формах. Более широкий критерий прямо установлен AC1; совместимость единственного связываемого прод-аккаунта обеспечивается обязательным шагом выката. Последующая утрата группы уже отложена до 42.7; изменение критерия нарушило бы контракт.
- R3 — `low` (Blind Hunter): несохраняемая страна или ручной флаг влияет на частичный `User.save`. Эффект возможен при таком сочетании, но проверенные штатные вызывающие его не создают: импорт и форма сохраняют целиком, реквизиты компании меняют только записываемые поля, привязка и верификация включают ответственного явно. Исправление добавляет сборку сохраняемого состояния.
- R4 — `low` (Blind Hunter): несохраняемый выбор менеджера подавляет возврат к автоматике. Штатная форма сохраняет выбор и флаг совместно; частичные вызывающие этого выбора не делают. Исправление добавляет проверки для непоказанного повседневного пути.
- R5 — `low` (Blind Hunter): полное сохранение старого экземпляра возвращает менеджера после массового пересчёта. Реальное редкое конкурентное окно с правкой правила уже разобрано; исправление требует отслеживания исходного состояния либо механизма согласования записей.
- R6 — `low` (Blind Hunter): сигнал использует несохраняемый ключ правила. Эффект возможен при специально составленном частичном сохранении; штатная форма сохраняет модель целиком, а data-миграция использует историческую модель без этих сигналов. Исправление усложняет сбор нового состояния.
- R7 — `low` (Blind Hunter): сохранение правила вне внешней транзакции допускает частичный пересчёт. Штатная правка через Django Admin транзакционна; новая транзакционная граница защищала бы непоказанного вызывающего. Возможность сбоя в autocommit не отрицается.
- R8 — `low` (Blind Hunter): сигналы не пропускают `raw=True`. Fixtures с `ManagerRoutingRule` в проверенном дереве не обнаружены; дополнительный guard закрывает непоказанный повседневный путь.
- R9 — `false` (Blind Hunter): отсутствует первоначальный пересчёт клиентов. Такое поведение прямо исключено из 42.2 и отнесено к команде 42.3; миграции выполняют предусмотренный объём.
- R10 — `low` (Blind Hunter): прямой тест функции миграции не проверяет историческое обновление. Факт верен, но Task 7 явно задаёт прямой вызов, регистрация `RunPython` корректна, а исторический тест требует отдельной инфраструктуры; повтор ранее отклонённого замечания.
- R11 — `false` (Edge Case Hunter): существующие дубли остановят ограничение. В целевой базе их отсутствие зафиксировано SELECT в Dev Notes; сид также не содержит дублей. Повтор R1.
- R12 — `false` (Edge Case Hunter): миграция должна фильтровать группы менеджеров. Это противоречит критерию AC1; целевой аккаунт включается в «Руководителей» обязательным шагом выката. Повтор R2.
- R13 — `low` (Edge Case Hunter): несохраняемая страна влияет на назначение при сохранении ИНН. Эффект возможен, но проверенные частичные вызывающие страну так не меняют; исправление добавляет ветви сборки состояния. Повтор R3.
- R14 — `low` (Edge Case Hunter): несохраняемое снятие ручного флага позволяет перезаписать ручного менеджера. Проверенные штатные частичные сохранения флаг так не меняют; форма сохраняет совместно. Исправление добавляет ветви. Повтор R3.
- R15 — `low` (Edge Case Hunter): менеджер вне `update_fields` подавляет снятие ручного назначения. Штатная форма сохраняет поля совместно; дополнительная проверка защищает непоказанное повседневное сочетание. Повтор R4.
- R16 — `low` (Edge Case Hunter): старый экземпляр совпадает с вычисленным менеджером, но не с БД после пересчёта. Эффект возможен при редком конкурентном изменении правила; исправление требует дополнительного сравнения с БД. Разновидность уже отклонённой гонки.
- R17 — `low` (Edge Case Hunter): одноразовый итератор `update_fields` исчерпывается. Проверенные вызывающие передают списки; дополнительная нормализация защищает непоказанный путь. Возможность эффекта с генератором не отрицается.
- R18 — `low` (Edge Case Hunter): позиционный `update_fields` игнорируется хуком. В проверенных вызывающих такие вызовы отсутствуют, позиционная форма устарела в Django 5.x; исправление требует разбора аргументов для непоказанного пути.
- R19 — `low` (Edge Case Hunter): частичное включение правила с несохраняемым ключом пересчитывает другой регион. Штатная форма сохраняет состояние целиком; исправление усложняет получение нового состояния. Повтор R6.
- R20 — `low` (Edge Case Hunter): `raw=True` запускает пересчёт по неполным связям fixture. Fixtures с правилами не обнаружены; новый guard закрывает непоказанный повседневный путь. Повтор R8.
- R21 — `low` (Edge Case Hunter): ошибка пересчёта после autocommit оставляет новое правило. Штатная админка обеспечивает внешнюю транзакцию; дополнительная граница нужна для непоказанного вызывающего. Повтор R7.
- R22 — `low` (Edge Case Hunter): два конкурентных пересчёта записывают устаревшего менеджера. Реальное редкое окно при изменении правил уже разобрано; исправление требует общего механизма блокировок.
- R23 — `low` (Edge Case Hunter): правило с невалидным кодом `AB` нарушает равенство массового и поштучного назначения. На искусственно внесённой некорректной строке эффект возможен, но сид и зафиксированные целевые данные содержат цифровые коды, а текущая форма отклоняет такой ключ через `clean()`. Новые guards для обхода валидации не требуются проверенными штатными путями.
- R24 — `low` (Edge Case Hunter): `match_value=None` даёт `TypeError` при `full_clean()`. Эффект возможен при прямом создании некорректного экземпляра в Python; поле не nullable, форма передаёт строку, такого штатного вызывающего нет. Дополнительный guard защищает непоказанный повседневный путь.
- R25 — `false` (Edge Case Hunter, claims): обещание назначить каждому клиенту требует пересчёта в миграции 42.2. Граница стори прямо оставляет первоначальное назначение до команды 42.3; общий intent не отменяет указанное исключение. Повтор R9.
- R26 — `low` (Edge Case Hunter, claims): возврат к правилу не работает при несохраняемом выборе менеджера. Повтор R15: форма сохраняет выбранного менеджера и флаг совместно, а исправление требует дополнительной проверки для непоказанного пути.
- R27 — `low` (Verification Gap): тесты не проверяют исполнение `RunPython` через историческое обновление схемы. Пробел принят по доказательствам слоя: удаление операции оставит прямые тесты зелёными. Сейчас операция зарегистрирована правильно; Task 7 предписывает прямые тесты алгоритма, дополнительный исторический тест требует инфраструктуры. Предложенная слоем маршрутизация `defer` учтена, но по правилам разбора замечание отклонено как ранее согласованное `low`, а не записано новым отложением.
- R28 — `low` (Verification Gap, прочие находки): частичный save учитывает несохраняемую страну или ручной флаг. Эффект возможен, но проверенные штатные вызывающие такого сочетания не создают; исправление добавляет ветви. Повтор R3.
- R29 — `low` (Verification Gap, прочие находки): устаревший объект не сохраняет ответственного, уже совпавшего в памяти с разрешением. Реальная разновидность редкой гонки с пересчётом правила; исправление требует дополнительного сравнения с БД. Повтор R16.
- R30 — `low` (Verification Gap, прочие находки): частичное сохранение менеджера с несохраняемой неактивностью пропускает пересчёт. Штатная форма сохраняет правило целиком, исторические модели миграции не запускают ресиверы; дополнительный сбор сохранённого состояния защищает непоказанный вызывающий. Повтор R6.
- R31 — `false` (Verification Gap, прочие находки): старые дубли остановят миграцию. Условие отсутствует в целевой базе по зафиксированному SELECT и в сиде; новая уникальность намеренно запрещает дубли. Повтор R1.

## Dev Notes

### Текущее состояние кода (сверено на `26207161`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/apps/common/models.py:1040-1114` `ManagerRoutingRule` | `match_type` (`inn_region`/`country`/`fallback`), `match_value`, `manager_name`, `manager_email` (обязателен), `federal_district`, `is_active`, индекс `common_mrr_type_val_act_idx`. Docstring: несколько активных строк с одним ключом дают несколько получателей. `clean()` нормализует email и значение | FK `manager`, `manager_email` необязателен, два ограничения, валидация, docstring |
| `backend/apps/common/migrations/0018_seed_manager_routing_rules.py` | сид: 88 кодов `inn_region`, 2 страны (Беларусь, Казахстан → Лопатина), 2 резерва (`managermsk3@`, `admin@freesportopt.ru`) | не меняется |
| `backend/apps/common/admin.py:625-685` `ManagerRoutingRuleAdmin` | `list_editable = ["manager_email", "is_active"]`, fieldsets «Правило»/«Менеджер»/«Метаданные» | колонка и поле `manager`, `list_select_related` |
| `backend/apps/users/services/region_routing.py:17-61` `resolve_manager_recipients` | страна не Россия → правило страны; иначе `tax_id[:2]`, две цифры → регион; ничего → все резервные адреса; дедупликация | через `region_key`, адрес `manager.email` или `manager_email` |
| `backend/apps/users/tasks.py:400-484` `send_manager_region_email` | получатели — `resolve_manager_recipients(user.country, user.tax_id)`; ссылка — `/admin/users/user/<id>/verify/` | не меняется |
| `backend/apps/users/models.py:360-371` `User.save` | нормализует `customer_code`, у существующей записи читает `previous` (`only("customer_code")`) и запрещает смену кода после заказов | расширить `previous`, хук назначения |
| `backend/apps/users/signals.py` | `pre_save`/`post_save` `User` для письма о верификации (полный `User.objects.get`) | добавить ресиверы `ManagerRoutingRule` |
| `backend/apps/users/serializers.py:360,384,394` | регистрация: `create_user` → `save()` → письма `on_commit` | не меняется (хук в `save`) |
| `backend/apps/users/serializers.py:437,440` `_link_matched_1c_customer` | **мёртвый путь** — автопривязка отключена 2026-07-26 | не трогать |
| `backend/apps/users/views/authentication.py:677,686` `PortalLinkConfirmView` | сохраняет `email`, `password`, `verification_status`; ИНН не меняет | не меняется |
| `backend/apps/users/services/processor.py:566` `_create_customer`, `:610,624` `_update_customer` | `User.objects.create(...)`; `user.tax_id = customer_data.get("tax_id", user.tax_id)` **без strip** → `user.save()` полный | не меняется (хук) |
| `backend/apps/users/services/link_1c_customer.py:231-262` | переносит `tax_id` с источника на цель → `target.save(update_fields=target_fields)` | не меняется (хук дописывает `update_fields`) |
| `backend/apps/users/services/verify_b2b_application.py:247-251` | `MODE_DECISION`: `save(update_fields=["is_verified","verification_status","is_active","updated_at"])` | явный `assign_responsible_manager` |
| `backend/apps/users/admin.py:310-394` `UserAdmin.fieldsets` | без ответственного; `get_fieldsets` вычищает `PRIVILEGE_FIELDS` у не-суперпользователя (42.1) | новый блок |
| `backend/apps/users/staff_roles.py` | имена трёх групп и `STAFF_ROLE_GROUPS` (42.1) | `staff_accounts_q`, `RESPONSIBLE_MANAGER_CHOICES` |

### Прод (read-only SELECT, 09.10.2026)

- Правила на проде совпадают с сидом `0018`: 88 активных `inn_region`, 2 активных `country`, 2 активных `fallback`. **Дублей активных правил по коду и стране нет** — `AddConstraint` в `common/0022` пройдёт.
- 11 кодов без правила: `80, 81, 82, 84, 85, 88, 95, 96, 97, 98, 99`. Выводить их — работа 42.3.
- Учётные записи для email правил:

  | email | правил | учётная запись |
  |---|---|---|
  | `1managermsk@freesportopt.ru` (Гусев) | 32 | нет |
  | `d.lopatina@freesportopt.ru` | 26 (из них 2 страны) | нет |
  | `manager5@freesportopt.ru` (Исакова) | 25 | нет |
  | `manager3@freesportopt.ru` (Милованов) | 7 | нет |
  | `admin@freesportopt.ru` | 1 (резерв) | нет |
  | `managermsk3@freesportopt.ru` (Чернов) | 1 (резерв, id 91) | **id 15**, `is_staff=t`, `is_superuser=f`, `role=admin` |

- **После выката 42.2** миграция `common/0023` свяжет только правило 91 (резерв) с id 15. Следствия до 42.3:
  - все новые клиенты получают ответственным Чернова;
  - письма идут как сейчас;
  - у 4630 существующих записей `users` ответственный пуст. 4173 из них с ИНН вида `NN…`, 456 без ИНН, 1 с некорректным ИНН. Всех их, кроме сотрудников, назначит команда 42.3.
- Учётная запись id 15 сама — сотрудник (`is_staff`, `role=admin`), поэтому ответственного не получит.
- **Обязательное условие выката 42.2 — шаг 4 выката 42.1:** id 15 состоит в группе «Руководители» (решение Alex 10.10.2026, код не меняется). По sprint-status шаг выполнен 09.10.2026; перед выкатом перепроверить:
  ```sql
  SELECT g.name FROM users_groups ug JOIN auth_group g ON g.id = ug.group_id WHERE ug.user_id = 15;
  ```
  Ожидается строка «Руководители». Без неё ошибки не будет, данные пропадут молча. Поля `manager` правила и `responsible_manager` карточки клиента предлагают только `RESPONSIBLE_MANAGER_CHOICES`, а `common/0023` связывает любого `is_staff` не суперпользователя. Текущего значения среди `<option>` нет, браузер отправляет пустой вариант, `blank=True` его пропускает. Поэтому:
  - сохранение правила 91 в админке обнулит `manager`, сигнал пересчитает резерв, и у клиентов резерва ответственный станет пустым;
  - сохранение любой карточки клиента, чей ответственный — id 15, обнулит поле.

  Ошибка «Выберите корректный вариант» бывает только у тестового клиента, который шлёт pk.

### Почему назначение в `User.save()`, а не в местах вызова

- Мест, где меняется `tax_id`, больше, чем названо в эпике: API профиля (`UserProfileSerializer`) и `conflict_resolution.py:133,184` тоже сохраняют пользователя. Точечные вызовы гарантированно пропустят какое-то из них.
- Сигнал `pre_save` не может дописать `update_fields`. А `link_1c_customer` сохраняет новый ИНН именно через `update_fields`, и ответственный остался бы только в памяти.
- `User.save()` уже читает `previous` из БД, поэтому проверка смены ИНН запросов не добавляет. Новые запросы (правило региона, резерв, группы) появляются только при создании или смене ИНН/страны.
- `QuerySet.update()` и `bulk_update` хук обходят. Сейчас ими `tax_id`/`country` пользователей не меняют (grep на `26207161`). Новый код, который так сделает, обязан вызвать `reassign_clients_for_key` сам.

### Подводные камни

- **ИНН без `strip()`.** Импорт пишет ИНН как есть. Регион берётся из `tax_id[:2]` без нормализации — так же, как в письме. Не «чинить» это только в одном месте.
- **`Company.tax_id` ≠ `User.tax_id`.** Регион определяется по `User.tax_id`, как и письмо. Правка ИНН в инлайне компании ответственного не меняет. Это не дефект стори: `CompanyInline` правит реквизиты, а ИНН клиента — поле `User`.
- **Пустая страна** приравнивается к России и в `region_key`, и в массовом пересчёте (`country__in=["Россия", ""]`).
- **Тестовая БД содержит сид `0018`.** Транзакционные тесты его стирают, обычные — нет. Тест с правилами начинает с `ManagerRoutingRule.objects.all().delete()`. В остальных тестах сид без `manager` даёт ответственного `None`, побочных эффектов нет.
- **`exclude` с m2m** (`groups__name__in` в `staff_accounts_q`) Django превращает в подзапрос. Проверить, что запрос массового пересчёта один (`CaptureQueriesContext`), а не по клиенту.
- **`limit_choices_to` с join по группам:** начиная с Django 3.2, `ModelChoiceField` и автодополнение применяют его без дублей. Проверять это не нужно, но если в выпадающем списке появятся дубли, причина здесь.

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет.
- `UniqueConstraint(condition=..., violation_error_message=...)` и проверка ограничений в `Model.full_clean()` (`validate_constraints`) — штатные возможности Django 4.1+. Форма админки показывает `violation_error_message` как ошибку формы.
- `Substr` — `django.db.models.functions.Substr(expression, pos, length)`, позиция с 1.
- Язык: комментарии, docstrings, `verbose_name`, сообщения ошибок — на русском (NFR-42-03).
- Критические операции и `select_for_update` не затрагиваются: назначение пишет только два поля пользователя.

### Тестирование

- Только Docker + PostgreSQL. Конкретный тест: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`. `--env-file` не передаётся. Параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры по каталогу (`tests/unit/` → `unit`, `tests/integration/` → `integration`). Новый каталог под `tests/` не заводить.
- Уникальные данные — `get_unique_suffix()`; фабрика `tests.factories.UserFactory`.
- Проверки доступа здесь нет, но назначение ответственного — фундамент видимости менеджера в 42.4. Покрытие нового сервиса ≥ 90 % (NFR-42-01).
- `check_openapi_sync` (тестовый контейнер монтирует только `backend/`):
  ```bash
  cd docker
  MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
    -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
    python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml
  ```
- Базис mypy после 42.1: 16 ошибок, все в нетронутых `apps/products/tests/unit/test_variant_import_{admission,error_paths}.py`. Любая другая — новая.

### Уроки 42.1

- Сравнивать «было/стало» по прод-данным до миграции. В 42.1 так нашёлся открытый `/admin/monitoring/`, здесь — два резервных правила, из-за которых «одно правило на регион» не распространяется на резерв.
- Функцию data-миграции тест вызывает напрямую. Состояние БД после миграций ненадёжно: `flush` транзакционных тестов стирает данные.
- Отклонения от стори записывать в Completion Notes с причиной, не молча.

### Связь с последующими стори

- **42.3:**
  - команда пересчёта — цикл по клиентам с `assign_responsible_manager` и подсчётом по `ResponsibleResolution.source`, либо `reassign_clients_for_key` по всем ключам плюс `None`;
  - отчёт «назначено по региону / ушло на резерв» берёт числа из `source`;
  - список «Не распределены» — коды справочника без активного правила **с `manager`** (правило без учётной записи ответственного не даёт).
- **42.4:** видимость менеджера — `User.objects.filter(responsible_manager=request.user)`; поле в карточке только для чтения.
- **42.7:**
  - ручное назначение руководителем ставит `responsible_manager_manual=True` и пишет `AuditLog`;
  - таблица регионов редактирует `ManagerRoutingRule.manager`, сигнал Task 4 переводит клиентов;
  - блокировка уволенного менеджера клиентов не переводит (решение 9) — это делает руководитель.

### Project Structure Notes

- Новые файлы:
  - `backend/apps/users/services/responsible_manager.py`;
  - `backend/apps/common/migrations/0022_managerroutingrule_manager.py`;
  - `backend/apps/common/migrations/0023_link_routing_rules_to_staff.py`;
  - `backend/apps/users/migrations/0024_user_responsible_manager.py`;
  - `backend/tests/unit/test_responsible_manager.py`;
  - `backend/tests/unit/test_manager_routing_rule.py`;
  - `backend/tests/unit/test_routing_rules_link_migration.py`;
  - `backend/tests/integration/test_responsible_manager_events.py`.
- Изменяемые:
  - `backend/apps/users/staff_roles.py`;
  - `backend/apps/common/models.py`;
  - `backend/apps/common/admin.py`;
  - `backend/apps/users/models.py`;
  - `backend/apps/users/signals.py`;
  - `backend/apps/users/services/region_routing.py`;
  - `backend/apps/users/services/verify_b2b_application.py`;
  - `backend/apps/users/admin.py`;
  - `backend/tests/unit/test_region_routing.py` — только новые тесты.
- Фронтенд, OpenAPI и шаблоны писем не затрагиваются.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md`, разделы Story 42.2, FR-42-05/07/08/10/11, «Additional Requirements» (правила с `manager_email`, пересчёт командой).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-2, Constraints «Регион клиента», «Ровно один ответственный», «Учётные записи сотрудников»; Non-goals), `affected-code.md` («Регионы»).
- Предыдущая стори: `_bmad-output/implementation-artifacts/Story/42-1-staff-roles-and-service-access-lockdown.md` (staff_roles, прод-учётки, шаг выката 4).
- Стандарты: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), Claude Code, 10.10.2026.

### Debug Log References

- GitNexus на `0b1eae0` (индекс свежий): `resolve_manager_recipients`, `send_manager_region_email`, `verify_b2b_application`, `ManagerRoutingRuleAdmin`, `_update_customer`, `UserAdmin` — LOW; `ManagerRoutingRule` — HIGH, ложное (23 импорта модуля `apps.common.models`); `User.save()` — HIGH по природе, Alex предупреждён до правки. `detect-changes --scope all`: 12 файлов, процессов 0, риск low.
- Первый полный прогон: `1 failed, 3937 passed, 76 skipped` — упал `tests/unit/test_users_admin.py::TestUserAdmin::test_fieldsets_structure` (ожидал 6 блоков карточки), см. отклонение 2.
- Ревью-фиксы (10.10.2026): RED — 8 падений (7 ожидаемых: страна, удаление; 1 — ошибка теста о порядке адресов резерва, исправлен тест). GREEN — 121/121 тест стори. mypy: 1 новая ошибка `arg-type` в `UserAdmin.get_deleted_objects` (stubs ждут `auth.User`) — `# type: ignore[arg-type]`, как у соседних `super()`-вызовов. GitNexus `impact`: `ManagerRoutingRule` HIGH — ложное (импорты модуля, процессов 0), `UserAdmin` LOW; `detect-changes`: 9 файлов, процессов 0, риск low (`user_change_password` — сдвиг строк).
- mypy нашёл 2 новые ошибки в `responsible_manager.py` (`pk is None` — unreachable) и `region_routing.py` (типизация `_rule_emails`) — исправлены, итог `Success: no issues found in 608 source files`.
- Повторное ревью (10.10.2026): RED — 3 ожидаемых падения (снятие флага: форма и `update_fields`; привязка с тем же ИНН), тесты патчей 3 и 4 зелёные на верном коде; мутационная проверка (убрать `""` из `RUSSIA_COUNTRY_VALUES`, убрать `~Q(country__in=covered_countries)`) роняет оба. GREEN — 156/156 в наборах стори, привязки и верификации. GitNexus: `link_1c_customer` — LOW (2 прямых, 2 процесса); `User.save()` — HIGH по природе; `detect-changes`: 7 файлов, изменены `User.save` и `link_1c_customer` (`full_name`, `is_b2b_user`, `logger` — сдвиг строк), риск high из-за `save()`, затронутые потоки — только ветки назначения ответственного.
- Третье ревью (10.10.2026): GitNexus на `0c1fbfe` (индекс свежий): `ManagerRoutingRule.__str__` — вызывающих в графе нет, LOW; `User.save()` — HIGH по природе. RED — 3 ожидаемых падения: `__str__` с пустым email учётной записи, снятие флага с выбором другого менеджера и сменой ИНН (форма и `save()`). Тесты патчей 2 и 4 зелёные на верном коде, они сторожат регрессию: при чтении `manager_email` в резервной ветке или возврате `SET_NULL` у клиентского FK они падают по построению. Первая версия теста формы параметризовала и смену страны, но `country` в карточке админки нет, параметр игнорировался. Страна перенесена в тест `save()`. GREEN — 178/178 в наборах стори, привязки и верификации. После прогона black переформатировал `User.save()`, а `__str__` переписан короче под лимит flake8 (120). Повторно прогнаны тесты правила и `TestManualFlagReleased` — 27/27. `detect-changes`: 6 файлов. `clean` попал в список из-за сдвига строк. Риск high из-за `save()`, затронутые потоки — только ветки назначения ответственного.
- Четвёртое ревью (10.10.2026): изменён только тест. Мутация «убрать `Q(role="admin")` из `staff_accounts_q()`» роняет оба случая нового теста (резерв и регион 23), на верном коде — 50/50 в `test_responsible_manager.py`. black и flake8 по файлу — чисто. GitNexus не нужен: символы приложения не менялись.
- Пятое ревью (10.10.2026): изменены только тесты. Оба новых теста зелёные на верном коде (31/31 в `TestUnsuitableManagerRejected` и `test_region_routing.py`). Мутации «убрать `is_staff=True` из `RESPONSIBLE_MANAGER_CHOICES`» и «`_rule_emails` берёт только `manager_email`» роняют ровно новые тесты: 4 случая форм и тест задачи, остальные 11 зелёные. black и flake8 по двум файлам — чисто. GitNexus не нужен: символы приложения не менялись.
- Седьмое ревью (11.10.2026): изменён только тест. Новый тест зелёный на верном коде (51/51 в `test_responsible_manager.py`). Мутация «резервный поиск не фильтрует `is_active`» роняет ровно его, остальные 50 зелёные; код восстановлен. GitNexus не нужен: символы приложения не менялись.
- Восьмое ревью (11.10.2026): изменён только тест. Новый тест зелёный на верном коде (4/4 в `TestRuleChangeFromAdmin`). Мутация «`affected_keys` выходит раньше, если старое правило неактивно» роняет ровно его, остальные 3 зелёные; код восстановлен (`git status` по `backend/apps` чист). black и flake8 по файлу — чисто. GitNexus не нужен: символы приложения не менялись.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Реализовано: FK `ManagerRoutingRule.manager` и два частичных `UniqueConstraint` (`common/0022`), data-миграция связывания правил с сотрудниками (`common/0023`), поля `User.responsible_manager` / `responsible_manager_manual` (`users/0024`), сервис `apps/users/services/responsible_manager.py` (единый источник логики, `ResponsibleResolution.source` для 42.3), хук в `User.save()`, явное назначение при верификации, сигналы `pre_save`/`post_save`/`post_delete` правила с пересчётом одним `UPDATE`, письмо через общий `region_key` с адресом учётной записи, блок «Ответственный менеджер» в `/admin/`.
- Проверки: полный backend-прогон в Docker (итог — в Change Log), `makemigrations --check` — «No changes detected», `black --check` (457 unchanged), `flake8` чист, `mypy --config-file=mypy.ini` — без ошибок, `check_openapi_sync` — «Контракт синхронен с кодом». Покрытие `responsible_manager.py` и `region_routing.py` — 100 %.
- Ограничения `full_clean()` ловит штатно (Django 5.2 проверяет `condition` с `manager__isnull`), дублировать проверку в `clean()` не понадобилось.
- **Отклонение 1 — `affected_keys` точнее, чем в Task 4.** Стори предлагала добавлять резерв (`None`) при любой смене `manager_id`/активности регионального правила. Пересчёт ключа и так охватывает всех клиентов ключа, включая ушедших на резерв: целевой менеджер для ключа без правила — менеджер резерва. Поэтому резерв пересчитывается только при изменении резервного правила с менеджером, а правило без `manager` (ни до, ни после) не пересчитывает никого. Инвариант «массовое = поштучное» проверен тестами на всех сценариях AC6.
- **Отклонение 2 — ожидание существующего теста изменено.** `test_users_admin.py::test_fieldsets_structure` проверял ровно 6 блоков карточки пользователя; Task 6 требует седьмой блок «Ответственный менеджер». Требования стори противоречат друг другу (Task 6 и AC9), поэтому счётчик поднят до 7 и добавлена проверка нового блока по имени. Других ожиданий не менял.
- **Отклонение 3 — сценарий привязки к 1С в тестах AC4.** `link_1c_customer` отклоняет источник с другим ИНН (сверка по `strip()`), поэтому ИНН при привязке меняется только пробелами. Тест: заявка с ` 7701234567` (региона нет, ответственный — резерв) → привязка к записи 1С с `7701234567` → ответственный — менеджер региона 77; хук дописал `responsible_manager` в `update_fields`.
- Результат миграции связывания на тестовом прогоне: в тестовой БД на момент миграции учётных записей нет — связано 0 правил, сид `0018` остался без `manager`, `AddConstraint` прошли на сиде. Логика проверена прямыми вызовами функции (8 сценариев AC1).
- **Ревью 10.10.2026 (7 пунктов), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: менеджер вне групп теряется при сохранении формы — по решению Alex код не менялся; Dev Notes «Прод» переписаны (шаг 4 выката 42.1 — обязательное условие, реальное поведение формы, SELECT для проверки), шаг 1 выката ниже обновлён.
  - ✅ Resolved review finding [Patch]: удаление менеджера обходит пересчёт — `on_delete=PROTECT` у `ManagerRoutingRule.manager` и `User.responsible_manager` (миграции `common/0024`, `users/0025`). `UserAdmin.get_deleted_objects` при наличии клиентов или правил у удаляемой записи выводит «Сначала назначьте клиентам нового менеджера и замените менеджера в правилах регионов» — один хук на карточку и массовое `delete_selected`. Тесты: `ProtectedError` на модели (клиенты; только правило), страница удаления и массовое действие показывают сообщение и не удаляют, менеджер без клиентов и правил удаляется.
  - ✅ Resolved review finding [Patch]: правило страны с пустым `match_value` — `clean()` отклоняет с «Укажите страну» (после `strip()`, так что пробелы тоже), тест на `""` и `"   "`.
  - ✅ Resolved review finding [Patch]: тест массового пересчёта по правилу страны — `test_change_country_rule_manager`: клиенты «Беларусь» с ИНН `23…` переходят к B, клиент «Казахстан» остаётся на резерве, регион 23 не тронут, инвариант «массовое = поштучное».
  - ✅ Resolved review finding [Patch]: тест исключения сотрудника «только по группе» — `test_role_group_member_untouched_by_mass_update`, параметризован по трём группам.
  - ✅ Resolved review finding [Patch]: отрицательные тесты форм — `TestUnsuitableManagerRejected`: клиент, суперпользователь в «Руководителях», сотрудник без группы, сотрудник только из «Маркетинга»; форма правила и карточка клиента дают ошибку поля, БД не меняется.
  - ✅ Resolved review finding [Patch]: тест резерва при правиле без адреса — `test_rule_without_any_address_falls_back`. Код уже работал верно, порядок адресов задаёт `Meta.ordering`, поэтому сравнение по отсортированному списку.
- **Повторное ревью 10.10.2026 (4 патча, 1 пункт отложен до 42.7), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: снятие «Назначен вручную» не возвращало автоматику — в `User.save()` второй триггер хука: флаг был `True`, стал `False`, поле `responsible_manager_manual` сохраняется (`update_fields` пуст или содержит его), а `responsible_manager_id` не изменился. Если в той же правке выбран другой менеджер — выбор остаётся (решение Alex). `previous` читает ещё два поля в том же запросе, лишних запросов нет. Тесты `TestManualFlagReleased`: форма админки со снятым флагом → менеджер правила; снятый флаг и другой менеджер → выбор сохранён; `save(update_fields=["responsible_manager_manual"])` пишет ответственного; флаг снят только в памяти и не сохраняется → ничего не меняется; установка флага не переназначает.
  - ✅ Resolved review finding [Patch]: привязка к 1С без смены ИНН не назначала ответственного — `link_1c_customer` вызывает `assign_responsible_manager(target)` перед `target.save()` при любой привязке и дописывает `responsible_manager` в `update_fields`; вызов после вывода роли, так как роль входит в критерий «сотрудник». Покрывает `MODE_LINK_ONLY` верификации и действие админки «Связать с 1С»: оба идут через `link_1c_customer`. При смене ИНН хук `save()` повторно разрешает менеджера и получает то же значение. Тесты: привязка с тем же ИНН у клиента без ответственного → менеджер региона; с ручным назначением → не меняется.
  - ✅ Resolved review finding [Patch]: тест пересчёта клиента с пустой страной — `test_empty_country_client_in_region_update`. Мутация «убрать `""` из `RUSSIA_COUNTRY_VALUES`» роняет тест.
  - ✅ Resolved review finding [Patch]: тест резерва и правила страны — `test_change_fallback_manager` дополнен клиентом «Беларусь» с правилом страны: после смены менеджера резерва остаётся у менеджера страны. Мутация «убрать `~Q(country__in=covered_countries)`» роняет тест.
  - [Defer] менеджер, выведенный из групп после выката, — в `deferred-work.md` до 42.7.
- **Третье ревью 10.10.2026 (4 патча), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: снятие флага с выбором другого менеджера и сменой ИНН или страны — в `User.save()` условие «выбран другой менеджер» (`manager_chosen`) теперь блокирует любое автоназначение в этой правке, включая ветку `region_changed`. Тесты: форма админки со снятым флагом, другим менеджером и новым ИНН; `save(update_fields=…)` с тем же набором для ИНН и для страны (страны в карточке нет).
  - ✅ Resolved review finding [Patch]: тест приоритета email учётной записи для резервного правила — `test_fallback_rule_with_manager_uses_account_email`: резерв с учётной записью и другим `manager_email` плюс резерв без учётной записи → адрес учётной записи и `admin@`.
  - ✅ Resolved review finding [Patch]: `__str__` правила с пустым email учётной записи показывает `manager_email` — тот же выбор адреса, что в `_rule_emails`. Тест `test_manager_without_email_shows_manager_email`.
  - ✅ Resolved review finding [Patch]: `test_model_delete_with_clients` изолирует `PROTECT` у `User.responsible_manager`: у удаляемого менеджера нет правил, клиент назначен ему вручную; проверяются `protected_objects` и что ответственный не изменился.
- **Четвёртое ревью 10.10.2026 (1 патч), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: тест массового пересчёта для `role="admin"` — `TestReassignClientsForKey.test_admin_role_untouched_by_mass_update`: учётная запись с `role="admin"`, `is_staff=False`, без групп. Два случая: без ИНН при смене менеджера резерва (как робот обмена 1С) и с ИНН `23…` при смене менеджера правила 23. Ответственный остаётся пустым, а клиенты того же ключа переходят к новому менеджеру, то есть `UPDATE` выполнился.
- **Пятое ревью 10.10.2026 (2 патча, 1 пункт отложен до 42.7), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: отрицательный тест форм на члена разрешённой группы с `is_staff=False` — в `UNSUITABLE_MANAGERS` добавлены `managers_group_not_staff` и `supervisors_group_not_staff`; формы правила и карточки клиента отклоняют кандидата, БД не меняется.
  - ✅ Resolved review finding [Patch]: тест адреса письма на уровне задачи — `TestSendManagerRegionEmail.test_send_to_rule_manager_account_email`: правило 77 с учётной записью и другим `manager_email`, задача `send_manager_region_email` без мока `send_mail`, в `mailoutbox[0].to` — адрес учётной записи.
  - [Defer] резервное правило принимает обычного менеджера — в `deferred-work.md` до 42.7.
- **Шестое ревью 11.10.2026 (1 патч), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: тест первого менеджера у правила без менеджера — `TestRuleChangeFromAdmin.test_first_manager_moves_clients_from_fallback`: правило региона 24 только с `manager_email`, клиенты на резерве; форма назначает менеджера → клиенты у него, ручное назначение остаётся у резерва.
- **Седьмое ревью 11.10.2026 (1 патч), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: тест выключения резервного правила с менеджером — `TestReassignClientsForKey.test_deactivate_fallback_clears_responsible`: клиенты резерва получают `responsible_manager=None`, региональные и ручные назначения (в том числе ручной клиент на резерве) не тронуты, сотрудник пуст, инвариант «массовое = поштучное».
- **Восьмое ревью 11.10.2026 (1 патч), ветка `fix/42-2-review-findings`:**
  - ✅ Resolved review finding [Patch]: тест повторного включения существующего неактивного правила — `TestRuleChangeFromAdmin.test_reactivate_rule_moves_clients_from_fallback`: выключенное правило региона 25 с менеджером, клиенты на резерве; форма включает правило → клиенты у менеджера правила, ручное назначение остаётся у резерва.
- **Выкат (Dev Notes, «Прод»):**
  1. **Обязательное условие:** шаг 4 выката 42.1 выполнен — id 15 (`managermsk3@`) в группе «Руководители» (по sprint-status — 09.10.2026). Перепроверить SELECT из Dev Notes «Прод». Без этого сохранение формы правила 91 или карточки клиента молча обнулит менеджера.
  2. Выкат применяет `common/0022`, `common/0023`, `common/0024`, `users/0024`, `users/0025`. Миграции ревью `common/0024` и `users/0025` (`on_delete=PROTECT`) схему БД не меняют: `on_delete` Django исполняет в Python. Ожидается: правило 91 (резерв) связывается с id 15, остальные 91 правило остаются без `manager`, письма идут как раньше.
  3. Проверка после выката: `SELECT id, match_type, match_value, manager_id FROM common_managerroutingrule WHERE manager_id IS NOT NULL;` — одна строка (91 → 15).
  4. До 42.3 ответственного получают только новые и изменившиеся клиенты (все — Чернов, id 15); существующим назначит команда 42.3.

### File List

Новые:
- `backend/apps/users/services/responsible_manager.py`
- `backend/apps/common/migrations/0022_managerroutingrule_manager.py`
- `backend/apps/common/migrations/0023_link_routing_rules_to_staff.py`
- `backend/apps/users/migrations/0024_user_responsible_manager.py`
- `backend/apps/common/migrations/0024_protect_responsible_manager.py` (ревью)
- `backend/apps/users/migrations/0025_protect_responsible_manager.py` (ревью)
- `backend/tests/unit/test_responsible_manager.py`
- `backend/tests/unit/test_manager_routing_rule.py`
- `backend/tests/unit/test_routing_rules_link_migration.py`
- `backend/tests/integration/test_responsible_manager_events.py`

Изменённые:
- `backend/apps/users/staff_roles.py`
- `backend/apps/common/models.py`
- `backend/apps/common/admin.py`
- `backend/apps/users/models.py`
- `backend/apps/users/signals.py`
- `backend/apps/users/services/region_routing.py`
- `backend/apps/users/services/verify_b2b_application.py`
- `backend/apps/users/services/link_1c_customer.py` (повторное ревью)
- `backend/apps/users/admin.py`
- `backend/tests/unit/test_region_routing.py` (только новые тесты)
- `backend/tests/unit/test_users_admin.py` (счётчик блоков карточки, отклонение 2)
- `backend/tests/unit/test_responsible_manager.py` (новые тесты, включая седьмое ревью)
- `backend/tests/integration/test_responsible_manager_events.py` (тесты первого менеджера и повторного включения правила, шестое и восьмое ревью)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/deferred-work.md` (повторное ревью)
- `_bmad-output/implementation-artifacts/Story/42-2-responsible-manager-by-region-rule.md`

## Change Log

- 10.10.2026 — реализация стори 42.2: ответственный менеджер клиента по правилу региона, связь правил с учётными записями, пересчёт при смене правила, письмо по той же таблице. Финальный полный прогон: 3938 passed, 76 skipped, 0 failed.
- 10.10.2026 — закрыты 7 пунктов код-ревью (ветка `fix/42-2-review-findings`): `on_delete=PROTECT` у менеджера правила и ответственного клиента с пояснением в админке, правило страны без значения отклоняется, 21 новый тест, Dev Notes «Прод» — шаг 4 выката 42.1 обязателен. Полный прогон: 3959 passed, 76 skipped, 0 failed; black, flake8, mypy, `makemigrations --check`, `check_openapi_sync` — чисто.
- 10.10.2026 — повторное ревью: 4 патча закрыты, 1 пункт отложен до 42.7. Снятие «Назначен вручную» возвращает назначение по правилу; `link_1c_customer` назначает ответственного при любой привязке; 2 теста-сторожа массового пересчёта; 9 новых тестов. Полный прогон: 3967 passed, 76 skipped, 0 failed; black, flake8, mypy, `makemigrations --check`, `check_openapi_sync` — чисто.
- 10.10.2026 — Addressed code review findings - 4 items resolved (третье ревью). Выбор другого менеджера при снятии флага сохраняется и при смене ИНН или страны. `__str__` правила выбирает адрес так же, как письмо. Добавлен тест-сторож email учётной записи у резерва, тест `PROTECT` клиентского FK изолирован. 5 новых тестов. Полный прогон: 3972 passed, 76 skipped, 0 failed; black, flake8, mypy, `makemigrations --check`, `check_openapi_sync` — чисто.
- 10.10.2026 — Addressed code review findings - 1 item resolved (четвёртое ревью). Тест-сторож: массовый пересчёт не трогает учётную запись с `role="admin"` (резерв и регион). Полный прогон: 3974 passed, 76 skipped, 0 failed; black и flake8 по изменённому файлу — чисто.
- 10.10.2026 — Addressed code review findings - 2 items resolved (пятое ревью), 1 пункт отложен до 42.7. Тесты-сторожа: формы отклоняют члена «Менеджеров»/«Руководителей» с `is_staff=False`; задача `send_manager_region_email` шлёт письмо на email учётной записи менеджера правила. Полный прогон: 3979 passed, 76 skipped, 0 failed; black и flake8 по изменённым файлам — чисто.
- 11.10.2026 — Addressed code review findings - 1 item resolved (шестое ревью). Тест-сторож: первый менеджер у правила региона без менеджера переводит клиентов с резерва. Полный прогон: 3980 passed, 76 skipped, 0 failed; black и flake8 по изменённому файлу — чисто.
- 11.10.2026 — Addressed code review findings - 1 item resolved (седьмое ревью). Тест-сторож: выключение резервного правила с менеджером оставляет клиентов резерва без ответственного, региональные и ручные назначения не тронуты. Полный прогон: 3981 passed, 76 skipped, 0 failed; black и flake8 по изменённому файлу — чисто.
- 11.10.2026 — Addressed code review findings - 1 item resolved (восьмое ревью). Тест-сторож: повторное включение существующего неактивного правила с менеджером переводит клиентов региона с резерва, ручные назначения не тронуты. Полный прогон: 3982 passed, 76 skipped, 0 failed; black и flake8 по изменённому файлу — чисто.
