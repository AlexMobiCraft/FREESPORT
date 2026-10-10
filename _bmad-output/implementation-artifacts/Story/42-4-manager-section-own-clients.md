---
baseline_commit: 9af7c7ed
---

# Story 42.4: Раздел менеджера — клиенты своего региона

Status: ready-for-dev
Baseline Revision: 9af7c7ed

## Story

As a менеджер,
I want видеть и вести только своих клиентов, без служебных полей,
so that я верифицирую, блокирую и помогаю клиентам, не путаясь в чужих записях и данных интеграции.

**Закрывает:** FR-42-12, FR-42-13, FR-42-14, FR-42-17 (клиенты, подтверждение B2B, смена пароля), FR-42-30 (действия над клиентом). **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.4), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-3, Constraints), состав раздела — `section-contents.md`, «Менеджер → Клиенты».

**Предусловия:**
- **Код — стори 42.2 слита в `develop`.** 42.4 опирается на её поле `User.responsible_manager`, функцию `staff_roles.staff_accounts_q()` и хук автоназначения в `User.save()`. На `9af7c7ed` 42.2 ещё `ready-for-dev`, поля нет. Перед стартом проверить: `grep -n "responsible_manager" backend/apps/users/models.py` и `grep -n "def staff_accounts_q" backend/apps/users/staff_roles.py`. Пусто — остановиться и сообщить Alex.
- **Выкат — после 42.3 и ручного шага эпика** (action_item «После выката 42.3 и до 42.4»): учётные записи менеджеров заведены, регионы распределены, пересчёт ответственных выполнен. Без этого раздел на проде открывается пустым. Код 42.3 стори 42.4 не использует.
- Ветка `feature/42-4-manager-section-clients` от `develop`.

**Чего в этой стори нет:**
- заказов и главной страницы со счётчиками — это 42.5 (на главной 42.4 — штатный список моделей);
- раздела маркетинга — 42.6;
- просмотра без фильтра по ответственному, управления сотрудниками, ручного и массового переназначения — 42.7;
- ленты журнала — 42.9 (здесь только записи `AuditLog`).

## Утверждённые решения (не пересматривать)

1. **Раздел — отдельный сайт `/manager/`** (SPEC, Assumptions): экземпляр `ManagerAdminSite(name="manager")`, заголовок «FREESPORT — Менеджер». `SuperuserAdminSite` остаётся сайтом `/admin/` без изменений.
2. **В раздел пускает членство в группе «Менеджеры» или «Руководители»** при `is_active` и `is_staff`. Суперпользователь, «Маркетинг» и сотрудник без группы получают штатный отказ сайта: 302 на `/manager/login/`. Суперпользователь работает в `/admin/`, у него там то же самое и больше.
3. **Видимость — одна функция `scope_clients(request, queryset)`:** `responsible_manager=request.user`, минус учётные записи сотрудников (`staff_accounts_q()`). Руководитель в 42.4 видит тоже только своих: клиентов, у которых он ответственный (на проде это клиенты резервного правила). Снятие фильтра для руководителя — работа 42.7, и правится только эта функция.
4. **Чужой клиент — 404, а не редирект.** Штатный `ModelAdmin` на несуществующий в queryset объект отвечает 302 на главную с сообщением «не существует». Раздел переопределяет `_get_obj_does_not_exist_redirect` на `raise Http404`. Это покрывает карточку, историю и страницу подтверждения B2B. Смена пароля отвечает 404 уже сейчас: `BaseUserAdmin.user_change_password` сам поднимает `Http404`.
5. **Карточка собирается белым списком полей**, а не вычёркиванием из `UserAdmin.fieldsets`. Новое поле `User` в будущем не попадёт в раздел само собой.
6. **Статус верификации в карточке только для чтения.** Section-contents относит `is_verified` и `verification_status` к «B2B-данным», но их правка в форме обходила бы страницу подтверждения и не писала бы `AuditLog`. Верифицируют и отклоняют только страница подтверждения и действия. Код клиента (`customer_code`) тоже только для чтения: он вшит в номера заказов и сверяется с 1С.
7. **Разблокировка — новое действие `unblock_users` в `UserAdmin`**, рядом с `block_users`. Оно доступно и в `/admin/`, и в `/manager/`. Действие не трогает:
   - суперпользователей;
   - учётные записи сотрудников (`staff_accounts_q()`);
   - B2B-заявки в статусе `pending`. Вход им всё равно закрыт (`account_pending_verification`, `users/views/authentication.py:295`), поэтому «разблокировать» такую заявку значило бы обмануть менеджера. Сообщение отправляет его на страницу подтверждения.
8. **Флаг «активен» в карточке правится** (section-contents), но смена флага пишет `AuditLog`: `block_user` или `unblock_user` с `"source": "card"`. Иначе блокировка из карточки выпала бы из журнала (FR-42-30).
9. **Все изменяющие действия требуют права `change`:** `permissions=["change"]` у одобрения, отказа, блокировки и разблокировки. Сейчас оно есть только у привязки к 1С. В `/admin/` это ничего не меняет (суперпользователь), а в разделе закрывает дыру для сотрудника с одним `view_user`.
10. **Ссылка письма менеджеру региона ведёт в раздел:** `send_manager_region_email` → `/manager/users/user/<id>/verify/`. Получатель этого письма — менеджер или руководитель, в `/admin/` их не пустят. Письмо получателям уведомлений (`send_admin_verification_email`) остаётся на `/admin/`.
11. **Nginx проксирует `/manager/` в Django.** Сейчас проксируются только `/admin/`, `/api/`, `/swagger/`, `/redoc/`. Без новой локации `/manager/` уйдёт в Next.js, в маршрут `(blue)/[slug]`, и ответит 404.

## Acceptance Criteria

### AC1 — вход в раздел

**Given** менеджер (`is_staff=True`, член «Менеджеры»), руководитель (член «Руководители»), маркетолог (член «Маркетинг»), сотрудник без группы, суперпользователь и аноним
**When** каждый открывает `/manager/` и `/manager/users/user/`
**Then** менеджер и руководитель получают 200, у страницы заголовок «FREESPORT — Менеджер»
**And** маркетолог, сотрудник без группы, суперпользователь и аноним получают 302 на `/manager/login/`
**And** заблокированный (`is_active=False`) член «Менеджеры» в раздел не попадает

### AC2 — список и поиск только по своим клиентам

**Given** менеджер A с клиентами региона 23 и менеджер B с клиентами региона 77
**When** A открывает список клиентов и ищет по email, ИНН, телефону, фамилии, компании и коду клиента клиента B
**Then** в списке и в результатах поиска только клиенты A
**And** сотрудник, суперпользователь и запись с `responsible_manager=A`, которая сама является учётной записью сотрудника, в список не попадают
**And** записи `role="unregistered"` скрыты по умолчанию и видны только с фильтром «Учётная запись на портале: нет» или «все»
**And** колонки и фильтры — по section-contents: email, ФИО, компания, ИНН, код клиента, роль, статус верификации, кандидат 1С, телефон, дата регистрации, активен; фильтры: роль, статус верификации, кандидат 1С, активен, учётная запись на портале

### AC3 — 404 на чужого клиента

**Given** менеджер A
**When** он открывает по прямому URL карточку (`/manager/users/user/<id>/change/`), историю (`…/history/`), страницу подтверждения B2B (`…/verify/`) или смену пароля (`…/password/`) клиента B, в том числе POST
**Then** каждая отвечает 404, данные клиента B не меняются
**And** массовое действие (верифицировать, отклонить, заблокировать, разблокировать, привязать к 1С) с подделанным списком `_selected_action`, где есть клиент B, клиента B не меняет и записи `AuditLog` о нём не создаёт

### AC4 — состав карточки

**Given** менеджер открывает карточку своего клиента
**When** страница отрисована
**Then** правятся: email, имя, фамилия, телефон, название компании, ИНН, страна, флаг «активен», реквизиты компании (`CompanyInline`) и адреса (`AddressInline`)
**And** только для чтения: роль, статус верификации, «Верифицирован», код клиента, «Связан с 1С: да/нет», вид цен из 1С, ответственный менеджер, юридический адрес компании, дата регистрации, последний вход
**And** в HTML формы нет ни поля, ни подписи из блока «Не показывать»: `is_staff`, `is_superuser`, `groups`, `user_permissions`, `onec_id`, `onec_guid`, `onec_price_type_id`, `onec_link_candidates`, `sync_status`, `created_in_1c`, `needs_1c_export`, `last_sync_at`, `last_sync_from_1c`, `sync_error_message`, `responsible_manager_manual`
**And** кнопок «Добавить» и «Удалить» для клиента нет

### AC5 — подделанный POST карточки

**Given** менеджер отправляет форму карточки своего клиента с дополнительными полями `role`, `is_staff`, `is_superuser`, `groups`, `onec_id`, `verification_status`, `is_verified`, `customer_code`, `responsible_manager`, `responsible_manager_manual`
**When** форма сохраняется
**Then** ни одно из этих полей не меняется, разрешённые поля сохранены

### AC6 — разблокировка

**Given** заблокированный клиент менеджера (`is_active=False`, не заявка `pending`)
**When** менеджер применяет действие «Разблокировать»
**Then** клиент снова активен, а `ModelBackend` его аутентифицирует (`authenticate(email=…, password=…)` возвращает пользователя)
**And** пишется одна запись `AuditLog` `unblock_user`
**And** суперпользователь, сотрудник и заявка `pending` в выборке действием не затрагиваются, для `pending` выводится сообщение со ссылкой на страницу подтверждения

### AC7 — журнал действий

**Given** менеджер выполняет верификацию (страница и массовое действие), отказ (страница и массовое действие), блокировку (действие и флаг в карточке), разблокировку (действие и флаг в карточке), сброс пароля или привязку к 1С
**When** действие завершено
**Then** в `AuditLog` есть запись с `user` = менеджер, `resource_type="User"`, `resource_id` = клиент и видом действия: `verify_b2b`, `approve_b2b`, `reject_b2b`, `block_user`, `unblock_user`, `change_password`, `link_1c_customer`
**And** на одно действие одна запись своего вида. Подтверждение с привязкой пишет две разные записи: `link_1c_customer` и `verify_b2b`, как и сейчас. Повторной записи того же вида раздел не добавляет

### AC8 — ссылки раздела ведут в раздел

**Given** менеджер на списке, в карточке, на странице подтверждения B2B, на странице привязки к 1С и на странице смены пароля
**When** страница отрисована и после выполнения действия
**Then** ни одна ссылка и ни один редирект не ведут в `/admin/`: в HTML нет `href="/admin/`, редиректы после подтверждения, отказа, смены пароля и сохранения ведут на `/manager/…`
**And** письмо о новой заявке региона (`send_manager_region_email`) содержит ссылку `/manager/users/user/<id>/verify/`
**And** письмо получателям уведомлений (`send_admin_verification_email`) по-прежнему ссылается на `/admin/users/user/<id>/verify/`

### AC9 — права внутри раздела (долг VG1 из 42.1)

**Given** член «Менеджеры», у группы которого в тесте оставлено только `users.view_user`
**When** он открывает карточку, страницу подтверждения и смену пароля своего клиента и отправляет массовые действия
**Then** карточка открывается только на чтение, без кнопки «Подтвердить заявку»
**And** страница подтверждения и смена пароля отвечают 403, данные не меняются
**And** изменяющих действий в списке нет, подделанный POST действия клиента не меняет и `AuditLog` не пишет

### AC10 — клиент ушёл к другому менеджеру после правки

**Given** правило «23 → A», правило «77 → B», клиент A региона 23 без ручного назначения
**When** A меняет в карточке ИНН клиента на `77…` и жмёт «Сохранить и продолжить»
**Then** клиент сохранён, ответственным стал B (хук 42.2)
**And** A получает редирект на список клиентов с сообщением «Клиент передан менеджеру <email B> по правилу региона», а не 404

### AC11 — число запросов списка (NFR-42-04)

**Given** у менеджера 5 клиентов, затем 50
**When** он открывает список клиентов
**Then** число SQL-запросов в обоих случаях одинаковое

### AC12 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `flake8`, `black --check`, `mypy`, `makemigrations --check` и `check_openapi_sync`, а `nginx -t` проходит на обоих конфигах
**Then** всё зелёное; изменены только ожидания тестов, прямо перечисленные в Task 6
**And** на локальном стенде `http://localhost/manager/` отвечает 302 на `/manager/login/` от Django, а не 404 от Next.js

## Tasks / Subtasks

- [ ] **Task 0 — GitNexus pre-flight и предусловие** (AGENTS.md)
  - [ ] Предусловие 42.2 (см. выше). Нет поля — стоп.
  - [ ] `npx gitnexus status`; при `stale` попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`. После мёрджа 42.2 индекс почти наверняка устареет.
  - [ ] `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по символам: `UserAdmin`, `verify_b2b_view`, `_verify_page_context`, `verify_b2b_link`, `onec_link_candidates`, `_warn_about_1c_candidates`, `link_1c_customer` (метод admin, не сервис — при неоднозначности `context --file backend/apps/users/admin.py`), `block_users`, `send_manager_region_email`. На `9af7c7ed` все LOW, 0–1 прямых вызывающих. У `send_manager_region_email` GitNexus не видит вызовов через `.delay`: реальные места — `users/serializers.py:394`, `:440`, `users/views/authentication.py:686`. Сообщить Alex blast radius до правок.

- [ ] **Task 1 — сайт `/manager/`** (AC1, AC12)
  - [ ] `backend/freesport/admin_site.py`, рядом с `SuperuserAdminSite`:
    ```python
    class ManagerAdminSite(admin.AdminSite):
        site_header = "FREESPORT — Менеджер"
        site_title = "FREESPORT — Менеджер"
        index_title = "Раздел менеджера"

        def has_permission(self, request: HttpRequest) -> bool:
            user = request.user
            if not (user.is_active and user.is_staff):
                return False
            # each_context и admin_view зовут has_permission по нескольку раз
            # за запрос — членство в группах читается один раз.
            cached = getattr(request, "_manager_site_access", None)
            if cached is None:
                cached = user.groups.filter(name__in=(MANAGERS_GROUP, SUPERVISORS_GROUP)).exists()
                request._manager_site_access = cached
            return cached

    manager_site = ManagerAdminSite(name="manager")
    ```
    Импорт имён групп — из `apps.users.staff_roles` (модуль без моделей, безопасен на уровне модуля). Docstring класса: кого пускает и почему суперпользователя нет (решение 2). Суперпользователя явно не пропускать: он не член групп, `exists()` вернёт `False`. Тест это закрепляет.
  - [ ] `ManagerAdminSite.get_app_list`: у модели `users.User` подменить подпись `name` на «Клиенты». Блок приложения в списке моделей и в боковой навигации должен называться так же. Заголовок списка («Выберите пользователя для изменения») задаётся в `ManagerClientAdmin.changelist_view` через `extra_context["title"] = "Клиенты"`.
  - [ ] `backend/freesport/urls.py`: `path("manager/", manager_site.urls)` после `path("admin/", admin.site.urls)`.
  - [ ] Nginx (решение 11) — локация, копия блока `location /admin/`, в двух конфигах:
    - `docker/nginx/conf.d/default.conf` (прод, HTTPS-сервер, рядом с `location /admin/` на `:204`). Таймауты 120 с и `include /etc/nginx/snippets/app-headers.conf;` — как у `/admin/`;
    - `docker/nginx/conf.d/local.conf` (рядом с `:73`).

    Префикс — `location /manager/`. Запрос `/manager` без слэша уйдёт в Next и получит 404: это допустимо, входная ссылка всегда со слэшем. В комментарии сниппета `docker/nginx/snippets/app-headers.conf:2` дописать `/manager/` в перечень локаций.
  - [ ] `robots.ts` не трогать: страница входа Django отдаёт `<meta name="robots" content="NONE,NOARCHIVE">`, фронтенд в эпике не меняется (SPEC, Non-goals).

- [ ] **Task 2 — `UserAdmin` готов ко второму сайту** (AC7, AC8, AC9; решения 7, 9)
  - [ ] Все Python-`reverse` с литералом `admin:` заменить на `f"{self.admin_site.name}:…"`. В `/admin/` поведение не меняется: имя сайта там `admin`. Места на `9af7c7ed`:
    - `verify_b2b_view`, `change_url` (`users/admin.py:575`);
    - `_verify_page_context`, `change_url` (`:691`);
    - `verify_b2b_link` (`:773`);
    - `onec_link_candidates`, `changelist_url` (`:802`);
    - `_warn_about_1c_candidates` (`:973`).

    `user_change_password` (`:500`) уже использует `self.admin_site.name`.
  - [ ] Перед `render(...)` в `verify_b2b_view` (`:611`) и в действии `link_1c_customer` (`:1038`) поставить `request.current_app = self.admin_site.name`. Шаблоны `templates/admin/users/verify_b2b_application.html` и `link_1c_customer.html` строят хлебные крошки через `{% url 'admin:index' %}` и фильтр `admin_urlname`. Без `current_app` они резолвятся в сайт по умолчанию, то есть в `/admin/`. Штатные вью `ModelAdmin` выставляют `current_app` сами (`django/contrib/admin/options.py:1395`, `:1751`, `:2181`, `:2321`), эти две — нет.
  - [ ] `@admin.action(..., permissions=["change"])` у `approve_b2b_users`, `reject_b2b_users`, `block_users` (решение 9).
  - [ ] Новое действие сразу после `block_users`:
    ```python
    @admin.action(description="🔓 Разблокировать выбранных пользователей", permissions=["change"])
    def unblock_users(self, request, queryset): ...
    ```
    Логика:
    1. Кандидаты: `queryset.filter(is_active=False).exclude(is_superuser=True).exclude(staff_accounts_q())`.
    2. Из них отложить заявки `role__in=User.B2B_ROLES, verification_status="pending"` и вывести про них одно предупреждение: «Заявка ждёт решения — откройте страницу подтверждения», со ссылками через `format_html_join`, как в `_warn_about_1c_candidates`.
    3. Остальным `is_active=True`, `save(update_fields=["is_active", "updated_at"])` и `AuditLog.log_action(action="unblock_user", resource_type="User", changes={"email": …, "role": …, "blocked": False})`, по образцу `block_users`.
    4. Пустая выборка — предупреждение «Не выбрано ни одного заблокированного пользователя».

    `exclude(staff_accounts_q())` с m2m по группам Django превращает в подзапрос — проверить, что на каждую строку лишнего запроса нет. Добавить `"unblock_users"` в `UserAdmin.actions`.
  - [ ] Больше в `UserAdmin` ничего не менять: fieldsets, `get_fieldsets` с `PRIVILEGE_FIELDS`, `has_change_permission`/`has_delete_permission` для цели-суперпользователя, AuditLog действий — как есть.

- [ ] **Task 3 — `ManagerClientAdmin`** (AC2–AC7, AC9–AC11; решения 3–6, 8)
  - [ ] Новый модуль `backend/apps/users/manager_admin.py`. Регистрация — в нём же: `manager_site.register(User, ManagerClientAdmin)`. Модуль импортировать в `UsersConfig.ready()` (`apps/users/apps.py`) рядом с `import apps.users.signals`: `import apps.users.manager_admin  # noqa: F401 — регистрация на сайте /manager/`. Порядок безопасен: `FreesportAdminConfig` стоит в `DJANGO_APPS` раньше `apps.users`, поэтому `admin.autodiscover()` уже импортировал `apps/users/admin.py`, когда срабатывает `UsersConfig.ready()`. **Не импортировать `manager_admin` из конца `users/admin.py`:** это циклический импорт частично загруженного модуля.
  - [ ] Функция видимости (решение 3), в том же модуле, с docstring о 42.7:
    ```python
    def scope_clients(request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        return queryset.filter(responsible_manager=request.user).exclude(staff_accounts_q())
    ```
    Если `exclude` по m2m даст дубли или лишний JOIN в счётчике changelist, заменить на `~Exists(...)` по группам. Проверяется тестом AC11.
  - [ ] `class ManagerClientAdmin(UserAdmin)`:
    - `get_queryset`: `scope_clients(request, super().get_queryset(request))`. Аннотация `_has_1c_candidate` из `UserAdmin.get_queryset` сохраняется: `_is_changelist_request` сверяет `url_name`, а он одинаков на обоих сайтах (`users_user_changelist`);
    - `_get_obj_does_not_exist_redirect(self, request, opts, object_id)` → `raise Http404("Клиент не найден")` (решение 4). Это приватный метод Django 5.2.7 (`options.py:1824`), его зовут `_changeform_view`, `history_view`, `delete_view` и `UserAdmin.verify_b2b_view`. Комментарий: почему 404, а не штатный редирект. Тест AC3 страхует от смены API при обновлении Django;
    - `has_add_permission` → `False`, `has_delete_permission` → `False`;
    - `list_display = ["email", "full_name", "company_name", "tax_id", "customer_code", "role_display", "verification_status_display", "has_1c_candidate", "verify_b2b_link", "phone", "created_at", "is_active"]`;
    - `list_filter = ["role", "verification_status", Has1CCandidateFilter, "is_active", PortalAccountFilter]`;
    - `search_fields` — как у `UserAdmin` (email, имя, фамилия, телефон, код клиента, компания, ИНН);
    - `actions = ["approve_b2b_users", "reject_b2b_users", "link_1c_customer", "block_users", "unblock_users"]`;
    - `filter_horizontal = ()`: полей групп и прав в форме нет;
    - `inlines = [CompanyInline, AddressInline]` — те же классы. Права на них уже есть в группе (`view/change_company`, `view/add/change/delete_address`, миграция `0023`). `add_company` в наборе роли нет: у клиента без `Company` (обычная регистрация её не создаёт; создают привязка к 1С, импорт и личный кабинет) блок реквизитов пуст. Это известное ограничение, вне скоупа, в Completion Notes;
    - `fieldsets` — белый список (решение 5):
      ```python
      fieldsets = (
          ("Контакты", {"fields": ("email", "password", "first_name", "last_name", "phone")}),
          ("B2B данные", {"fields": ("company_name", "tax_id", "country", "company_legal_address", "customer_code")}),
          ("Статус", {"fields": ("role", "verification_status", "is_verified", "is_active")}),
          ("1С и ответственный", {"fields": ("linked_to_1c", "onec_price_type_name", "responsible_manager")}),
          ("Даты", {"fields": ("created_at", "last_login"), "classes": ("collapse",)}),
      )
      ```
      `password` — `ReadOnlyPasswordHashField` с кнопкой «Сбросить пароль». Ссылка в ней относительная (`../password/`), на втором сайте работает без правок;
    - `readonly_fields = ("customer_code", "role", "verification_status", "is_verified", "linked_to_1c", "onec_price_type_name", "responsible_manager", "company_legal_address", "created_at", "last_login")`. `get_readonly_fields` возвращает этот список целиком, без логики `UserAdmin` про `customer_code`: в разделе код всегда только для чтения;
    - `get_fieldsets`: вернуть `self.fieldsets` как есть. Логику `UserAdmin.get_fieldsets` (скрытие `onec_link_candidates`, вычистка привилегий) не звать: в белом списке этих полей нет, а `find_link_candidates` на каждом открытии карточки — лишний запрос;
    - display `linked_to_1c` (`boolean=True`, «Связан с 1С»): `bool(obj.onec_id or obj.onec_guid)`, без запросов;
    - `changelist_view`: `extra_context["title"] = "Клиенты"`.
  - [ ] `save_model` (решение 8): если `"is_active" in form.changed_data`, после `super().save_model(...)` записать `AuditLog`. Вид действия — `block_user` или `unblock_user`, `changes={"email", "role", "blocked", "source": "card"}`, `ip_address` и `user_agent` — через `self._get_client_ip(request)`, как в действиях.
  - [ ] `response_change` (AC10): после сохранения проверить `self.get_queryset(request).filter(pk=obj.pk).exists()`. Если клиент ушёл из видимости (хук 42.2 сменил ответственного по новому ИНН или стране):
    - сообщение уровня warning «Клиент {email} передан менеджеру {obj.responsible_manager.email или «без ответственного»} по правилу региона»;
    - `HttpResponseRedirect(reverse(f"{self.admin_site.name}:users_user_changelist"))`.

    Иначе `super().response_change(...)`.
  - [ ] `PortalAccountFilter(admin.SimpleListFilter)`, «Учётная запись на портале», `parameter_name="portal_account"`:
    - без значения (по умолчанию) → `exclude(role=User.ROLE_UNREGISTERED)`;
    - `"no"` → только `unregistered`;
    - `"all"` → всё.

    `choices()` переопределить так, чтобы пункт по умолчанию назывался «Есть» и был выбран без параметра, а штатного «Все» с тем же значением не было. Если в запросе `role__exact=unregistered`, исключение по умолчанию не применять, иначе фильтр роли «Не зарегистрирован» всегда давал бы пустой список. Docstring: почему скрыты (4600+ контрагентов 1С без аккаунта, SPEC, Assumptions).

- [ ] **Task 4 — ссылка письма менеджеру** (AC8; решение 10)
  - [ ] `apps/users/tasks.py:441` (`send_manager_region_email`): `"admin_url": f"{settings.SITE_URL}{reverse('manager:users_user_verify', args=[user.id])}"`. Ключ контекста `admin_url` не переименовывать: его читают шаблоны.
  - [ ] `templates/emails/manager_region_notification.txt:15`: «Открыть в админ-панели» → «Открыть в разделе менеджера». В `.html` (`:79`) поправить подпись кнопки, если она говорит об админке.
  - [ ] `send_admin_verification_email` (`tasks.py:75`) не трогать.

- [ ] **Task 5 — новые тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [ ] Общие фикстуры:
    - autouse `role_groups` — через функцию миграции, как `tests/integration/test_staff_access_lockdown.py:44-52`;
    - autouse `ManagerRoutingRule.objects.all().delete()`: в тестовой БД сид `0018`, а хук 42.2 назначает ответственного при создании;
    - `make_staff_member(group_name)` — по образцу `test_staff_access_lockdown.py:55-67`.
  - [ ] **Ловушка хука 42.2.** `create_user(..., responsible_manager=A)` не сработает: хук в `save()` у новой записи без ручного назначения перезапишет поле результатом правил (без правил — `None`). Клиента создавать, потом закреплять: `User.objects.filter(pk=c.pk).update(responsible_manager=A)`. Хелпер `make_client(manager, **overrides)` по образцу `make_applicant` (`tests/integration/test_admin_link_1c_customer.py:57`).
  - [ ] `backend/tests/integration/test_manager_clients_section.py` (integration):
    - AC1 — матрица входа: менеджер, руководитель → 200 и заголовок; маркетолог, сотрудник без группы, суперпользователь, аноним, заблокированный менеджер → 302, `"/manager/login/" in response.url`.
    - AC2 — список и поиск по шести полям, клиент B не находится. Сотрудник и суперпользователь с `responsible_manager=A` через `update()` не видны. `unregistered` с `responsible_manager=A` виден только с `portal_account=no` или `all`, а с `role__exact=unregistered` виден без `portal_account`.
    - AC3 — GET и POST карточки, `history`, `verify`, `password` клиента B → 404. Массовые действия с `_selected_action=[свой, чужой]` меняют только своего, у чужого состояние и `AuditLog` прежние. Образец POST действия — `post_action` в `test_admin_link_1c_customer.py`.
    - AC4 — разобрать `response.context["adminform"]` и HTML: правимые поля в `form.fields`, только для чтения — в `readonly_fields`. Для каждого поля «Не показывать» нет ни `name="<поле>"`, ни его `verbose_name` в HTML. Нет `addlink` и `deletelink`.
    - AC5 — POST с полным набором разрешённых полей и инлайнов (management form `company-*`, `addresses-*` собрать из GET-контекста) плюс подделанные поля. После `refresh_from_db` подделанные значения не применились, разрешённое (телефон) сохранено.
    - AC6 — разблокировка: заблокированный клиент → активен, `authenticate(email=…, password=…)` возвращает пользователя, одна запись `unblock_user`. Заявка `pending` в выборке не изменена, в сообщениях есть ссылка `/manager/users/user/<id>/verify/`. Суперпользователь в выборке (`_selected_action` с его id) не изменён: он и так вне queryset.
    - AC7 — по каждому действию из AC7 ровно одна запись своего вида, автор — менеджер. Подтверждение с привязкой → `link_1c_customer` и `verify_b2b` по одной. Флаг «активен» в карточке → `block_user` или `unblock_user` с `details["changes"]["source"] == "card"`. Подготовка данных для подтверждения и привязки — `make_1c_record` и `make_applicant` из `test_admin_link_1c_customer.py`: импортировать из этого модуля или скопировать в новый файл. Новый общий модуль хелперов не заводить.
    - AC8 — для списка, карточки, `verify`, страницы привязки и `password` `'href="/admin/' not in html`. Не `"/admin/" not in html`: статика Django лежит в `/static/admin/`. Редиректы после подтверждения, отказа, смены пароля и сохранения начинаются с `/manager/`.
    - AC9 — у группы «Менеджеры» в тесте оставить только `view_user` (`group.permissions.set([...])`, откатится вместе с транзакцией теста). Карточка открывается, в контексте `show_verify_b2b_button is False`. `verify` GET и POST → 403. `password` → 403. Действий в `response.context["action_form"]` нет, подделанный POST `action=block_users` клиента не меняет.
    - AC10 — правила «23 → A», «77 → B» (`ManagerRoutingRule` с `manager`). POST карточки со сменой ИНН и `_continue` → 302 на `/manager/users/user/`, в сообщениях email B, `responsible_manager == B`.
    - AC11 — по образцу `TestChangelistIndicatorCost` (`test_admin_link_1c_customer.py:315`): 5 клиентов → baseline, ещё 45 → `django_assert_num_queries(baseline)`.
  - [ ] `backend/tests/unit/test_manager_admin_site.py` (unit, `RequestFactory`):
    - `ManagerAdminSite.has_permission` для каждого случая AC1, у членства — один запрос на запрос (повторный вызов из кэша `request`, `django_assert_num_queries(1)`);
    - `scope_clients` — свой, чужой, сотрудник, суперпользователь;
    - `PortalAccountFilter` — три значения и связка с `role__exact`;
    - `unblock_users` в `UserAdmin` суперпользователя: те же исключения, что в AC6.

- [ ] **Task 6 — существующие тесты: менять только перечисленное**
  - [ ] `tests/unit/test_region_routing.py:132`: `verify_path` → `f"/manager/users/user/{user.id}/verify/"`. Комментарий: решение 10 стори 42.4. Это единственное осознанное изменение ожиданий. `tests/unit/test_email_tasks.py:68` (письмо получателям уведомлений) не меняется.
  - [ ] `tests/integration/test_admin_verify_b2b_application.py`: в комментариях тестов `:442` и `TestEntryPoints.test_change_form_closed_for_staff` ссылку «вернётся тестами раздела менеджера (стори 42.4)» заменить ссылкой на `tests/integration/test_manager_clients_section.py` (AC9). Ожидания не менять.
  - [ ] Прогнать без правок и убедиться: `test_admin_link_1c_customer.py` (в т. ч. `TestChangelistIndicatorCost` — в `/admin/` добавилось действие, но не колонка), `test_admin_verify_b2b_application.py`, `test_admin_user_password.py`, `tests/unit/test_users_admin.py`, `test_staff_access_lockdown.py`, тесты 42.2 `test_responsible_manager*.py`.

- [ ] **Task 7 — проверки и закрытие**
  - [ ] Полный backend-прогон в Docker, один compose-проект, без параллельных: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest`.
  - [ ] `makemigrations --check --dry-run` в контейнере. Моделей стори не меняет — миграций нет.
  - [ ] Линтеры — навык `backend-lint` или compose-проект `freesport-lint`, не параллельно с зачётным pytest. Базис после `spec-42-1-black-mypy-debt` (09.10.2026): `black --check .` чисто, mypy — 0 ошибок. Любая ошибка — новая.
  - [ ] `check_openapi_sync` — рецепт в Dev Notes; ожидается «синхронен» (API не менялся).
  - [ ] Nginx: `docker compose --env-file .env -f docker/docker-compose.yml exec nginx nginx -t` и `nginx -s reload` (локальный `local.conf`). Прод-конфиг `default.conf` локально не исполняется — проверить его `nginx -t` по рецепту второго процесса nginx (Dev Notes, «Nginx»). Затем `curl -sI http://localhost/manager/` → 302 с `Location: /manager/login/?next=/manager/`.
  - [ ] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [ ] `deferred-work.md`: пункт VG1 (`source_spec: spec-42-1-…`, «Проверки `change_user` в `UserAdmin`… вернуть их тестами раздела менеджера в 42.4») и его подтверждение в разделе ревью 42.1 пометить **ЗАКРЫТО** со ссылкой на тесты AC9.
  - [ ] Completion Notes: шаги выката (Dev Notes, «Выкат»), ограничение `add_company`, отклонения от стори с причиной.

## Dev Notes

### Текущее состояние кода (сверено на `9af7c7ed`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py` | только `SuperuserAdminSite` (42.1) | + `ManagerAdminSite`, `manager_site` |
| `backend/freesport/urls.py:41-46` | `/admin/monitoring/`, `/admin/` | + `/manager/` |
| `backend/apps/users/apps.py` `UsersConfig.ready` | импорт `signals`, переименование `AuthConfig` | + импорт `manager_admin` |
| `backend/apps/users/admin.py:235-1210` `UserAdmin` | `list_select_related=["company"]`; действия `approve_b2b_users` (`:889`), `reject_b2b_users` (`:1109`), `block_users` (`:1156`) без `permissions`, `link_1c_customer` (`:991`) с `permissions=["change"]`; `verify_b2b_view` (`:559`), `user_change_password` (`:493`, пишет `change_password`); захардкоженный `admin:` в пяти `reverse` | namespace, `current_app`, `permissions`, `unblock_users` |
| `backend/apps/users/admin.py:48,83` `CompanyInline`, `AddressInline` | инлайны компании и адресов | переиспользуются как есть |
| `backend/apps/users/admin.py:161` `Has1CCandidateFilter` | уже страхуется от «второй AdminSite» без аннотации (комментарий `:179-182`) | переиспользуется |
| `backend/apps/users/services/verify_b2b_application.py:225,298` | пишет `verify_b2b`, `reject_b2b`; при привязке зовёт `link_1c_customer` → `link_1c_customer` (`link_1c_customer.py:268`) | не меняется |
| `backend/apps/users/tasks.py:441` `send_manager_region_email` | ссылка `/admin/users/user/<id>/verify/` | → `/manager/…` |
| `backend/templates/admin/users/verify_b2b_application.html:6-12`, `link_1c_customer.html:6-10` | хлебные крошки через `{% url 'admin:index' %}`, `admin_urlname` | не меняются (лечится `current_app`) |
| `backend/templates/admin/index.html`, `_app_block.html` | главная с порядком блоков по `app_label`; ссылка импорта только для `integrations` | не меняются; главная `/manager/` берёт этот же шаблон, блок «Пользователи» → «Клиенты» через `get_app_list` |
| `docker/nginx/conf.d/default.conf:204`, `local.conf:73` | `location /admin/` → backend; `/manager/` нет | + `location /manager/` |
| `frontend/src/app/(blue)/[slug]/` | ловит любой одноуровневый путь | не меняется (поэтому нужен nginx) |

### Состав прав группы «Менеджеры» (миграция `users/0023`, 42.1)

`users.view_user`, `users.change_user`, `users.view_company`, `users.change_company`, `users.view_address`, `users.add_address`, `users.change_address`, `users.delete_address`, `orders.view_order`, `orders.change_order`, `orders.view_orderitem`. «Руководители» — надмножество. Своей миграции прав стори не добавляет. Если понадобится право сверх этого набора — отдельная миграция, `0023` после выката не правится.

### Как Django резолвит URL второго сайта (почему Task 2)

- `AdminSite.urls` возвращает `(patterns, "admin", self.name)`: пространство имён приложения — всегда `admin`, экземпляра — имя сайта (`manager`).
- `reverse("admin:…")` **без** `current_app` берёт экземпляр по умолчанию, у которого имя совпадает с `app_name`. Это `/admin/`. Отсюда пять Python-мест в Task 2.
- `{% url 'admin:…' %}` в шаблоне берёт `request.current_app`. Штатные вью `ModelAdmin` его ставят, `verify_b2b_view` и промежуточная страница действия `link_1c_customer` — нет. Отсюда `request.current_app` в Task 2.
- Фильтр `admin_urlname` возвращает строку `admin:<app>_<model>_<action>` и потом идёт в тот же `{% url %}`, поэтому лечится тем же `current_app`.
- `BaseUserAdmin.get_urls` называет смену пароля `auth_user_password_change` при любой модели: `reverse("manager:auth_user_password_change", args=[pk])`.

### Почему 404 работает именно так

| Вью | Без переопределения | С `_get_obj_does_not_exist_redirect` → `Http404` |
|---|---|---|
| `change_view` (GET и POST) | 302 на главную + «не существует» | 404 |
| `history_view` | 302 | 404 |
| `verify_b2b_view` | 302 (`users/admin.py:567`) | 404 |
| `user_change_password` | 404 (`has_change_permission(request, None)` → `True` по праву модели, затем `Http404`) | 404 |
| `delete_view` | 403 (`has_delete_permission` → `False` раньше поиска) | 403 — допустимо: удаления в разделе нет |
| массовое действие | чужой id отсекается `cl.get_queryset()` → `get_queryset` | то же |

### Подводные камни

- **Хук 42.2 при создании клиента в тестах** — см. Task 5. Он же срабатывает в карточке при смене ИНН или страны (AC10).
- **`exclude(staff_accounts_q())` с m2m.** Django строит подзапрос `NOT IN (… users_groups …)`. Счётчик changelist (`COUNT`) и список — по одному запросу на страницу, это проверяет тест AC11. Дубли строк возможны только при `filter` по m2m, не при `exclude`.
- **`has_permission` зовут несколько раз за запрос** (`admin_view`, `each_context`, `index`). Без кэша на `request` — 2–3 одинаковых запроса к группам. На NFR-42-04 это не влияет (от числа строк не зависит), но кэш дешёвый.
- **`UserChangeForm` (`BaseUserAdmin.form`) объявляет `fields = "__all__"`**, но `ModelAdmin.get_form` передаёт в `modelform_factory` явный `fields` из fieldsets минус readonly. Поэтому подделанный POST не меняет поля вне белого списка. Не переопределять `get_form` так, чтобы этот список потерялся.
- **Флаг «активен» у заявки `pending`.** Через карточку его можно поставить (решение 8), но вход заявке всё равно закрыт до подтверждения. Запись в журнале при этом будет. Действие «Разблокировать» такие заявки пропускает (решение 7).
- **Кандидаты привязки к 1С — не клиенты менеджера.** Страница привязки и страница подтверждения показывают записи `unregistered` с тем же ИНН. Ответственный у них может быть пуст, это ожидаемо (section-contents: `onec_link_candidates` виден «кроме страницы подтверждения»). Регион у них тот же — ИНН тот же.
- **Массовое одобрение (`approve_b2b_users`) ответственного не пересчитывает**: явный вызов 42.2 есть только в сервисе `verify_b2b_application`. Клиент в списке менеджера уже его, так что на 42.4 это не влияет.
- **Сессия общая для `/admin/` и `/manager/`.** Суперпользователь, вошедший в `/admin/`, на `/manager/` увидит страницу входа с «у вас нет доступа». Это штатно (решение 2).

### Nginx

- Деплой (`.github/workflows/deploy.yml:457-460`) после выката сам выполняет `nginx -t` и `nginx -s reload`. Новая локация уходит с релизом, отдельного шага нет.
- Прод-конфиг `default.conf` локально не исполняется: dev-nginx монтирует `local.conf` как `default.conf`. Проверка прод-конфига — второй процесс nginx в том же контейнере. `docker cp default.conf` во `/tmp/ngx/conf.d/`, `sed` портов `443 ssl`→`8080`, `80`→`8081/8082`, удалить `ssl_*`, своя копия `nginx.conf` с `include /tmp/ngx/conf.d/*.conf`, затем `nginx -t -c /tmp/ngx/nginx.conf`. Рецепт отработан в 41.5. Запросы проверять `curl` через Bash, не `Invoke-WebRequest`: PowerShell 5.1 не умеет `-SkipHttpErrorCheck`.

### Выкат (для Completion Notes и Alex)

1. **До выката:** action_item эпика 42 «После выката 42.3 и до 42.4» выполнен — учётные записи менеджеров (`is_staff=True`, группа «Менеджеры»), правила регионов с `manager`, резервное правило на руководителя, пересчёт ответственных (сначала `--dry-run`). Проверка:
   ```sql
   SELECT u.email, count(c.id) AS clients
     FROM users u LEFT JOIN users c ON c.responsible_manager_id = u.id
    WHERE u.is_staff AND NOT u.is_superuser
    GROUP BY u.email ORDER BY u.email;
   ```
   У каждого менеджера число клиентов больше нуля — иначе раздел у него пуст.
2. **После выката:** `curl -sI https://optisport.ru/manager/` → 302, `Location: /manager/login/?next=/manager/`. 404 от Next означает, что nginx не перечитал конфиг: `docker compose exec nginx nginx -s reload`.
3. Вход тестовой учётной записью менеджера — список своих клиентов открывается, чужая карточка по URL — 404.
4. Письмо о новой B2B-заявке ведёт на `/manager/users/user/<id>/verify/`.
5. После рестарта backend на проде — `docker compose restart nginx` (memory: nginx держит старый IP upstream). Деплой делает это сам.

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет. Несколько экземпляров `AdminSite` в одном проекте — штатный механизм Django («Multiple admin sites in the same URLconf»). Приватный `_get_obj_does_not_exist_redirect` сверен по исходникам 5.2.7 в `backend/venv`: `options.py:1824`, вызовы на `:1873`, `:2225`, `:2283`.
- Модели, миграции, API и OpenAPI не меняются.
- Язык: интерфейс, сообщения, комментарии, docstrings — русский (NFR-42-03).
- DRF не затрагивается: раздел — Django-админка, а не API.

### Тестирование

- Только Docker + PostgreSQL. Конкретный тест: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`. `--env-file` не передаётся. Параллельные прогоны в одном compose-проекте запрещены: deadlock на TRUNCATE.
- Маркеры по каталогу: `tests/unit/` → `unit`, `tests/integration/` → `integration`. Новый каталог под `tests/` не заводить — оборвёт сбор `UsageError`.
- Проверки доступа — критический модуль, покрытие ≥ 90 % (NFR-42-01): `freesport/admin_site.py`, `apps/users/manager_admin.py`. У каждой проверки — негативный тест (NFR-42-02).
- Уникальные email — `get_unique_suffix()` или `unique_suffix()`; ИНН — `unique_tax_id()` из `test_admin_link_1c_customer.py`.
- Сообщения админки читать через `messages` из `response.context` или `follow=True`; образец — `message_texts` в `test_admin_verify_b2b_application.py`.
- `check_openapi_sync` (тестовый контейнер монтирует только `backend/`):
  ```bash
  cd docker
  MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
    -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
    python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml
  ```

### Уроки 42.1 и 42.2

- Сверять «было/стало» по прод-данным и маршрутам, а не только по коду. В 42.1 так нашёлся открытый `/admin/monitoring/`. Здесь так же нашлись: `/manager/` в nginx нет, ссылка письма ведёт в закрытую для менеджера `/admin/`, а Python-`reverse("admin:…")` тихо уводит со второго сайта.
- Тесты 42.1 переписали проверки `change_user` на «302 на вход» сайта и потеряли внутренние отказы `UserAdmin` (VG1). В разделе они снова единственная защита — AC9 возвращает их.
- Отклонения от стори записывать в Completion Notes с причиной, не молча.
- Базис линтеров после `spec-42-1-black-mypy-debt` — ноль. Старое «16 ошибок mypy» из стори 42.1 и 42.2 больше не действует.

### Связь с последующими стори

- **42.5** регистрирует `Order` на том же `manager_site` и делает главную со счётчиками (`index_template`). Видимость заказов строит от того же правила: заказы клиентов из `scope_clients`.
- **42.7** меняет только `scope_clients`: руководитель без фильтра, с заказами без клиента. В нём же — `responsible_manager` в карточке правит руководитель, ставится `responsible_manager_manual`.
- **42.9** строит ленту по видам действий AC7 плюс `unblock_user`.

### Project Structure Notes

- Новые файлы:
  - `backend/apps/users/manager_admin.py`;
  - `backend/tests/integration/test_manager_clients_section.py`;
  - `backend/tests/unit/test_manager_admin_site.py`.
- Изменяемые:
  - `backend/freesport/admin_site.py`;
  - `backend/freesport/urls.py`;
  - `backend/apps/users/apps.py`;
  - `backend/apps/users/admin.py`;
  - `backend/apps/users/tasks.py`;
  - `backend/templates/emails/manager_region_notification.txt` (и `.html` при необходимости);
  - `docker/nginx/conf.d/default.conf`, `docker/nginx/conf.d/local.conf`, `docker/nginx/snippets/app-headers.conf` (комментарий);
  - `backend/tests/unit/test_region_routing.py` (одно ожидание), `backend/tests/integration/test_admin_verify_b2b_application.py` (комментарии);
  - `_bmad-output/implementation-artifacts/deferred-work.md` (закрытие VG1).
- Фронтенд, модели, миграции, OpenAPI не затрагиваются.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.4, FR-42-12/13/14/17/30, NFR-42-01/02/03/04, «UX Design Requirements» (заголовок раздела называет роль, отдельные страницы по образцу `verify_b2b_view`).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-3, Constraints «Скрытие полей», «Фильтр по региону действует везде», «Роль клиента назначается только при верификации», «Учётные записи сотрудников»; Assumptions), `section-contents.md` («Менеджер → Клиенты», «Перечень действий для журнала»), `affected-code.md` («Права и эскалация»).
- Предыдущие стори: `Story/42-1-staff-roles-and-service-access-lockdown.md` (сайт `/admin/`, `PRIVILEGE_FIELDS`, наборы прав, VG1), `Story/42-2-responsible-manager-by-region-rule.md` (`responsible_manager`, `staff_accounts_q`, хук `save()`, «Связь с последующими стори» → 42.4).
- Долг: `_bmad-output/implementation-artifacts/deferred-work.md:901-903`, `:911` (VG1).
- Стандарты: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker).

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
