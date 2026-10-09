---
baseline_commit: 26207161
---

# Story 42.2: Ответственный менеджер клиента по правилу региона

Status: ready-for-dev
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

- [ ] **Task 0 — GitNexus pre-flight** (AGENTS.md)
  - [ ] `npx gitnexus status` (на `26207161` индекс свежий); при `stale` попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [ ] `impact --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по символам: `resolve_manager_recipients`, `send_manager_region_email`, `ManagerRoutingRule`, `ManagerRoutingRuleAdmin`, `verify_b2b_application`, `link_1c_customer`, `_update_customer`, `UserAdmin`.

    Снято на `26207161`:
    - `resolve_manager_recipients` — LOW (1 вызывающий — `send_manager_region_email`);
    - `send_manager_region_email` — LOW;
    - `verify_b2b_application` — LOW;
    - `ManagerRoutingRuleAdmin` — LOW;
    - `ManagerRoutingRule` — **HIGH, но ложно.** 23 «прямых» — это файлы, которые импортируют модуль `apps.common.models` ради других моделей. По grep класс используют только `common/admin.py`, `region_routing.py` и миграции. Сообщить это Alex вместе с blast radius.
  - [ ] **`User.save()` — HIGH по природе:** через него проходит каждое сохранение пользователя. У GitNexus `save` неоднозначен, поэтому вызывающих искать через `cypher` или `context --file backend/apps/users/models.py`. Предупредить Alex до правки. Защита — Task 3: проверка дешёвая и срабатывает только при создании или смене `tax_id`/`country`.

- [ ] **Task 1 — критерий «сотрудник» и выбор менеджера** (AC8)
  - [ ] Дописать в `backend/apps/users/staff_roles.py`, не меняя существующие константы:
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
  - [ ] Предикат на экземпляре `is_staff_account(user) -> bool` положить в сервис Task 3, не в `staff_roles`. Порядок проверок:
    1. `is_staff`, `is_superuser`, `role == "admin"` — по атрибутам, без запроса;
    2. группы — запросом `user.groups.filter(name__in=STAFF_ROLE_GROUPS).exists()`, и только когда у записи есть `pk`. У несохранённой записи групп нет.

- [ ] **Task 2 — модель и миграции правила** (AC1, AC2)
  - [ ] `backend/apps/common/models.py` `ManagerRoutingRule` (`:1040`):
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
  - [ ] `apps/common/migrations/0022_managerroutingrule_manager.py` — **только схема**:
    - `AddField(manager)`;
    - `AlterField(manager_email)`;
    - `AddConstraint` ×2.

    Зависимости:
    - `("common", "0021_newsletter_unsubscribe_token")`;
    - `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`;
    - `("users", "0023_staff_role_groups")` — для `limit_choices_to` по группам.

    Циклов нет: `users/0023` зависит от `common/0021`, а не от `0022`. Миграцию сгенерировать `makemigrations common` в контейнере, затем переименовать.
  - [ ] `apps/common/migrations/0023_link_routing_rules_to_staff.py` — **только данные**. Отдельная миграция, потому что на PostgreSQL смешение `UPDATE` и `ALTER TABLE` с отложенными FK-триггерами в одной транзакции падает на «pending trigger events». Функция `link_rules_to_staff(apps, schema_editor)`:
    - для каждого правила без `manager` с непустым `manager_email` искать `User` по условиям `email__iexact=manager_email`, `is_staff=True`, `is_superuser=False`; из нескольких брать первого по `pk`;
    - резервные правила обходить по возрастанию `pk` и связывать, только пока ни одно активное резервное ещё не связано;
    - обратная функция — `RunPython.noop`.

    Ожидаемый результат на проде описан в Dev Notes, «Прод».
  - [ ] `apps/common/admin.py` `ManagerRoutingRuleAdmin` (`:626`):
    - `list_display` — добавить `"manager"` после `match_value`;
    - `list_select_related = ("manager",)`;
    - fieldset «Менеджер»: `("manager", "manager_name", "manager_email", "federal_district")`, описание «Письма уходят на email выбранного менеджера; email ниже — только пока менеджер не выбран».

    **Не добавлять `manager` в `list_editable`:** выпадающий список в каждой из ~92 строк — запрос на строку.

- [ ] **Task 3 — поле клиента и сервис назначения** (AC3, AC4, AC5, AC8)
  - [ ] `backend/apps/users/models.py` `User`, после блока `verification_status`:
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
  - [ ] **Новый модуль `backend/apps/users/services/responsible_manager.py`** — единственный источник логики назначения. Его переиспользует 42.3, поэтому разрешение возвращает источник:
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
  - [ ] **`User.save()`** (`users/models.py:360`) — хук автоназначения. Существующий запрос `previous` расширить до `.only("customer_code", "tax_id", "country")`: так обходится без лишнего запроса. Ветка `customer_code` остаётся как есть. Затем:
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
  - [ ] **Верификация** (`users/services/verify_b2b_application.py`, ветка `MODE_DECISION`, `:247-251`): перед сохранением вызвать `assign_responsible_manager(target)`; если вернул `True`, добавить `"responsible_manager"` в `update_fields` этого `save`. Сервис привязки не трогать: `link_1c_customer` сохраняет `tax_id` через `update_fields`, хук в `save()` срабатывает сам.
  - [ ] **Регистрация, импорт 1С, API профиля, карточка админки** — кода не добавлять, их покрывает хук `save()`. Это проверяется тестами AC3/AC4. Пути и строки, по которым проходит назначение:

    | путь | где сохраняется |
    |---|---|
    | регистрация | `UserRegistrationSerializer.create` (`serializers.py:360`, `create_user`) |
    | импорт 1С | `processor.py:566` (`_create_customer`), `:624` (`_update_customer`) |
    | привязка к 1С | `link_1c_customer.py:262` |
    | API профиля | `UserProfileSerializer` |
    | карточка админки | `UserAdmin` |

- [ ] **Task 4 — пересчёт при смене правила** (AC6)
  - [ ] Ресиверы в `backend/apps/users/signals.py`, `sender=ManagerRoutingRule`:
    - `pre_save` запоминает старые `(match_type, match_value, is_active, manager_id)` одним `.values(...).first()` по `pk`;
    - `post_save` и `post_delete` вычисляют затронутые ключи и вызывают `reassign_clients_for_key` для каждого.

    Логика в сервисе: `affected_keys(old: dict | None, new: dict | None) -> set[key | None]`.
    - Если старое или новое состояние резервное — затронут резерв (`None`).
    - Иначе затронуты старый и новый ключи, если правило меняло ключ, `is_active` или `manager_id`.
    - Изменение региона или страны **с менеджером** меняет покрытие резерва. Поэтому, если `manager_id` или активность изменились у правила `inn_region`/`country`, добавить и `None`: клиенты, уходившие на резерв, могли получить регионального менеджера, и наоборот.
    - Правка только `manager_name`, `manager_email` или `federal_district` клиентов не пересчитывает: ноль `UPDATE`, проверить `django_assert_num_queries`.
  - [ ] Пересчёт синхронный, внутри транзакции сохранения правила: админка оборачивает `save_model` в `atomic`. Логировать `logger.info` с ключом и числом переведённых клиентов, `extra={"action": "responsible_manager_reassign", ...}` — по образцу `region_routing.py:48`. `AuditLog` за смену правила пишет 42.7.

- [ ] **Task 5 — письмо по той же таблице** (AC7)
  - [ ] `region_routing.resolve_manager_recipients` (`:17`) переписать через `region_key` из Task 3, поведение и docstring сохранить. Адреса брать так: `rule.manager.email if rule.manager_id and rule.manager.email else rule.manager_email`, `select_related("manager")`, пустые значения отбросить, дедупликация как сейчас. Docstring модуля дополнить: таблица правил задаёт и ответственного (`services/responsible_manager.py`).
  - [ ] `send_manager_region_email` (`tasks.py:400`) не менять. Если `resolve_manager_recipients` станет функцией над `region_key`, задача пойдёт той же дорогой.

- [ ] **Task 6 — `/admin/` суперпользователя** (FR-42-07: поле у клиента есть и видно)
  - [ ] `UserAdmin.fieldsets` (`users/admin.py:310`): новый блок «Ответственный менеджер» с полями `("responsible_manager", "responsible_manager_manual")` после «Роль и статус». Редактируемы: `/admin/` теперь только у суперпользователя. Описание блока: «Ответственного назначает правило региона. Отметьте „Назначен вручную“, чтобы правила, смена ИНН и импорт его не меняли».
  - [ ] `list_display`/`list_filter` UserAdmin не трогать. Список клиентов с ответственным — раздел 42.4, а лишняя колонка FK без `list_select_related` сломала бы тест `test_admin_link_1c_customer.py:316` (`TestChangelistIndicatorCost`).
  - [ ] API-сериализаторы пользователя не трогать: поле в API не отдаётся, OpenAPI не меняется. `check_openapi_sync` это подтверждает.

- [ ] **Task 7 — тесты** (NFR-42-01, NFR-42-02). Общие правила для всех файлов:
  - в каждом тесте с правилами autouse-фикстура делает `ManagerRoutingRule.objects.all().delete()`, как в `test_region_routing.py:33`: в тестовой БД лежат правила из `common/0018`;
  - группы ролей — через `Group.objects.get_or_create(name=...)` из `staff_roles`.
  - [ ] `backend/tests/unit/test_responsible_manager.py`:
    - `region_key`: Россия + `23…` → `("inn_region","23")`; пустая страна → как Россия; Беларусь + `77…` → `("country","Беларусь")`; `""`, `"7"`, `"AB…"`, `" 23…"` → `None`.
    - `resolve_responsible`: регион с `manager`; регион без `manager` → резерв; страна; без ключа → резерв; нет резерва с менеджером → `(None, "none")`; неактивное правило игнорируется. Источник (`source`) — в каждом случае.
    - `is_staff_account`: `is_staff`, суперпользователь, `role="admin"`, каждая из трёх групп → `True`; клиент B2B и запись `unregistered` → `False`.
    - `reassign_clients_for_key`: сценарий AC6 целиком (десять клиентов A в регионе 23, двое ручных, клиенты A в 24; замена A→B). Плюс выключение и удаление правила, смена кода 23→24, смена менеджера резерва. В каждом случае — инвариант «массовое = поштучное».
    - Сотрудник в регионе 23 при пересчёте не тронут (AC8).
  - [ ] `backend/tests/unit/test_manager_routing_rule.py`:
    - AC2: второе активное по коду и по стране → `full_clean` с русским сообщением и `IntegrityError` на `save()`; неактивное — можно; два резервных без `manager` — можно; два активных резервных с `manager` — нельзя;
    - `clean()`: без `manager` и email; код «7» и «2a»; страна «Россия»;
    - `__str__` с менеджером и без;
    - сигнал: правка только `manager_email` → ни одного `UPDATE users` (`CaptureQueriesContext`, фильтр по `UPDATE "users"`).
  - [ ] `backend/tests/unit/test_routing_rules_link_migration.py` — AC1. Функцию звать напрямую: `importlib.import_module("apps.common.migrations.0023_link_routing_rules_to_staff").link_rules_to_staff(django.apps.apps, SimpleNamespace(connection=connection))` — образец `tests/unit/test_staff_role_groups_migration.py`. Сценарии:
    - email в другом регистре связывается;
    - клиент (не `is_staff`) с тем же email не связывается;
    - суперпользователь не связывается;
    - два резервных — связывается только первое;
    - повторный вызов ничего не меняет.
  - [ ] `backend/tests/unit/test_region_routing.py` — **ожидания не менять**. Дописать новые тесты:
    - правило с `manager` → адрес учётной записи, даже если `manager_email` другой;
    - правило с `manager`, у которого пустой email → `manager_email`.
  - [ ] `backend/tests/integration/test_responsible_manager_events.py` — сквозные события. Письма и Celery мокать, как в `test_registration_emails.py:118` (`patch("apps.users.serializers.send_manager_region_email.delay")` и соседние). Сценарии:
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
  - [ ] Негативные тесты (NFR-42-02 — здесь это проверка «не назначать»):
    - ручное назначение;
    - сотрудник;
    - неактивное правило;
    - второе активное правило.

- [ ] **Task 8 — проверки и закрытие**
  - [ ] Полный backend-прогон в Docker, один compose-проект, без параллельных прогонов: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest`. Ожидания существующих тестов не меняются (AC9). Если что-то падает из-за лишних запросов при создании пользователя, разобраться и не ослаблять тест молча.
  - [ ] `makemigrations --check --dry-run` в контейнере — новых несгенерированных изменений нет.
  - [ ] Линтеры — навык `backend-lint` или compose-проект `freesport-lint`, не параллельно с зачётным pytest. `check_openapi_sync` — рецепт в Dev Notes; ожидается «синхронен», API не менялся.
  - [ ] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [ ] Completion Notes: шаги выката (Dev Notes, «Прод») и фактический результат миграции связывания на тестовом прогоне.

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
- Редактирование правила 91 в форме админки пройдёт валидацию `limit_choices_to`, только когда id 15 состоит в «Руководителях». Это шаг 4 выката 42.1 (action_item эпика 42, open): без него сохранение формы правила 91 падает с «Выберите корректный вариант». Проверить статус шага перед выкатом 42.2.

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

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
