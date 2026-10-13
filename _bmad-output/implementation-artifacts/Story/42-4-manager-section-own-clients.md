---
baseline_commit: b4fab053
---

# Story 42.4: Раздел менеджера — клиенты своего региона

Status: review
Baseline Revision: b4fab053 (освежено 2026-10-12 по коду 42.2 и 42.3; первая редакция — `9af7c7ed`)

## Story

As a менеджер,
I want видеть и вести только своих клиентов, без служебных полей,
so that я верифицирую, блокирую и помогаю клиентам, не путаясь в чужих записях и данных интеграции.

**Закрывает:** FR-42-12, FR-42-13, FR-42-14, FR-42-17 (клиенты, подтверждение B2B, смена пароля), FR-42-30 (действия над клиентом). **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.4), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-3, Constraints), состав раздела — `section-contents.md`, «Менеджер → Клиенты».

**Предусловия:**
- **Код 42.2 — в `develop`** (PR #300, #301, мёрдж `42d3307d`). 42.4 опирается на поле `User.responsible_manager`, функции `staff_roles.staff_accounts_q()` и `RESPONSIBLE_MANAGER_CHOICES` и хук автоназначения в `User.save()`. На `b4fab053` всё на месте; контрольная проверка: `grep -n "responsible_manager" backend/apps/users/models.py` и `grep -n "def staff_accounts_q" backend/apps/users/staff_roles.py`.
- **Код 42.3 — стори `done`, но на `b4fab053` PR ещё не слит:** коммит `8c6687af` есть только в `origin/feature/42-3-region-directory-recalculation`. Код 42.3 стори 42.4 не использует, но ветку заводить после мёрджа PR 42.3 в `develop`: иначе полный прогон пройдёт без тестов 42.3, а `sprint-status.yaml` и `deferred-work.md` разойдутся при мёрдже. Проверка: `git fetch; git branch -r --contains 8c6687af` показывает `origin/develop`. Не показывает — сообщить Alex.
- **Выкат — после 42.3 и ручного шага эпика** (action_item «После выката 42.3 и до 42.4», на 12.10.2026 `status: open`): учётные записи менеджеров заведены, регионы распределены, пересчёт ответственных выполнен. Без этого раздел на проде открывается пустым. Порядок шагов — `Story/42-3-…md`, Dev Notes, «Выкат».
- Ветка `feature/42-4-manager-section-clients` от `develop`.

**Чего в этой стори нет:**
- заказов и главной страницы со счётчиками — это 42.5 (на главной 42.4 — штатный список моделей);
- раздела маркетинга — 42.6;
- просмотра без фильтра по ответственному, управления сотрудниками, ручного и массового переназначения — 42.7;
- ленты журнала — 42.9 (здесь только записи `AuditLog`).

## Утверждённые решения (не пересматривать)

1. **Раздел — отдельный сайт `/manager/`** (SPEC, Assumptions): экземпляр `ManagerAdminSite(name="manager")`, заголовок «FREESPORT — Менеджер». `SuperuserAdminSite` остаётся сайтом `/admin/` без изменений.
2. **В раздел пускает членство в группе «Менеджеры» или «Руководители»** при `is_active` и `is_staff`, суперпользователь — никогда, даже если состоит в группе. Это ровно `RESPONSIBLE_MANAGER_CHOICES` из `staff_roles.py` (42.2) плюс `is_active`: в раздел входит тот, кого можно назначить ответственным. Суперпользователь, «Маркетинг» и сотрудник без группы получают штатный отказ сайта: 302 на `/manager/login/`. Суперпользователь работает в `/admin/`, у него там то же самое и больше.
3. **Видимость — одна функция `scope_clients(request, queryset)`:** `responsible_manager=request.user`, минус учётные записи сотрудников (`staff_accounts_q()`: `is_staff`, `is_superuser`, `role="admin"` — робот обмена 1С — и члены трёх групп ролей). Руководитель в 42.4 видит тоже только своих: клиентов, у которых он ответственный (на проде это клиенты резервного правила). Снятие фильтра для руководителя — работа 42.7, и правится только эта функция.
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
12. **Ответственный менеджер в карточке — текст без ссылки** (добавлено при освежении 12.10). Readonly-FK Django 5.2 рисует ссылкой на карточку связанного объекта на текущем сайте (`contrib/admin/helpers.py:251-264`, `:296-300`). В разделе это `/manager/users/user/<id менеджера>/change/`, а менеджер — сотрудник, вне `scope_clients`, то есть ссылка ведёт в 404. Поэтому в карточке не поле `responsible_manager`, а display-метод `responsible_manager_display` — ФИО и email без ссылки.
13. **Главная `/manager/` без блока «Последние действия»** (добавлено при освежении 12.10). Боковой блок штатной главной (`{% get_admin_log %}`) строит ссылки через `LogEntry.get_admin_url()`, а тот зовёт `reverse("admin:…")` без `current_app` (`contrib/admin/models.py:235-247`). После первой же правки клиента на главной `/manager/` появилась бы ссылка в закрытую `/admin/`. Журнал действий менеджера — работа 42.9, главная со счётчиками — 42.5; здесь блок просто убирается своим `index_template`.

## Acceptance Criteria

### AC1 — вход в раздел

**Given** менеджер (`is_staff=True`, член «Менеджеры»), руководитель (член «Руководители»), маркетолог (член «Маркетинг»), сотрудник без группы, суперпользователь и аноним
**When** каждый открывает `/manager/` и `/manager/users/user/`
**Then** менеджер и руководитель получают 200, у страницы заголовок «FREESPORT — Менеджер»
**And** маркетолог, сотрудник без группы, суперпользователь и аноним получают 302 на `/manager/login/`
**And** заблокированный (`is_active=False`) член «Менеджеры» в раздел не попадает
**And** суперпользователь с `is_staff=True`, добавленный в группу «Менеджеры», тоже получает 302

### AC2 — список и поиск только по своим клиентам

**Given** менеджер A с клиентами региона 23 и менеджер B с клиентами региона 77
**When** A открывает список клиентов и ищет по email, ИНН, телефону, фамилии, компании и коду клиента клиента B
**Then** в списке и в результатах поиска только клиенты A
**And** записи с `responsible_manager=A`, которые сами учётные записи сотрудников, в список не попадают: `is_staff`, суперпользователь, `role="admin"` и член группы роли без `is_staff`
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
**And** ответственный менеджер выведен текстом (ФИО и email), без ссылки: в HTML нет `href` на `/manager/users/user/<id менеджера>/` (решение 12)
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

**Given** менеджер на главной `/manager/`, на списке, в карточке, на странице подтверждения B2B, на странице привязки к 1С и на странице смены пароля
**When** страница отрисована и после выполнения действия
**Then** ни одна ссылка и ни один редирект не ведут в `/admin/`: в HTML нет `href="/admin/`, редиректы после подтверждения, отказа, смены пароля и сохранения ведут на `/manager/…`
**And** главная проверяется после сохранения карточки клиента, когда у менеджера уже есть `LogEntry`: блока «Последние действия» на ней нет (решение 13)
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

- [x] **Task 0 — GitNexus pre-flight и предусловие** (AGENTS.md)
  - [x] Предусловия 42.2 и 42.3 (см. выше). Нет поля или PR 42.3 не в `develop` — стоп, сообщить Alex.
  - [x] `npx gitnexus status`; при `stale` сравнить `git diff --stat <indexed> HEAD -- backend docker`. Если разница только в тестах или документах, переиндексация не нужна (так было в 42.3 и при освежении этой стори: индекс на `09fad26`, после него изменились только два тестовых файла). Иначе попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по символам: `UserAdmin`, `verify_b2b_view`, `_verify_page_context`, `verify_b2b_link`, `onec_link_candidates`, `_warn_about_1c_candidates`, `link_1c_customer` (метод admin, не сервис — при неоднозначности искать через `cypher` по файлу `backend/apps/users/admin.py`; у `impact` нет `--file`), `block_users`, `send_manager_region_email`. При освежении 12.10 все LOW: 0 прямых вызывающих, у `_verify_page_context` и `_warn_about_1c_candidates` — по 1 (`verify_b2b_view` и `approve_b2b_users`). У `send_manager_region_email` GitNexus не видит вызовов через `.delay`: реальные места — `users/serializers.py:394`, `:440` (через `transaction.on_commit`), `users/views/authentication.py:686`. Сообщить Alex blast radius до правок.

- [x] **Task 1 — сайт `/manager/`** (AC1, AC12)
  - [x] `backend/freesport/admin_site.py`, рядом с `SuperuserAdminSite`:
    ```python
    class ManagerAdminSite(admin.AdminSite):
        site_header = "FREESPORT — Менеджер"
        site_title = "FREESPORT — Менеджер"
        index_title = "Раздел менеджера"
        index_template = "admin/manager/index.html"  # решение 13

        def has_permission(self, request: HttpRequest) -> bool:
            user = request.user
            if not (user.is_active and user.is_staff) or user.is_superuser:
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
    Импорт имён групп — из `apps.users.staff_roles` (модуль без моделей, безопасен на уровне модуля). Docstring класса: кого пускает, что это критерий `RESPONSIBLE_MANAGER_CHOICES` плюс `is_active`, и почему суперпользователя нет (решение 2). **Суперпользователя отсекать явно** (`or user.is_superuser`): ничто не мешает добавить его в группу «Менеджеры», и тогда одно членство пустило бы его в раздел. Тест AC1 это закрепляет. Тип `request.user` — `User | AnonymousUser`; у анонима `is_active=False`, проверка падает на первом условии.
  - [x] Шаблон `backend/templates/admin/manager/index.html` (решение 13): `{% extends "admin/index.html" %}` и пустой `{% block sidebar %}{% endblock %}`. Проектный `templates/admin/index.html` переопределяет только `{% block content %}` и наследует Django-шаблон, поэтому порядок блоков и `_app_block.html` сохраняются. 42.5 заменит или расширит этот шаблон своими счётчиками.
  - [x] `ManagerAdminSite.get_app_list`: у модели `users.User` подменить подпись `name` на «Клиенты». Блок приложения в списке моделей и в боковой навигации должен называться так же. Заголовок списка («Выберите пользователя для изменения») задаётся в `ManagerClientAdmin.changelist_view` через `extra_context["title"] = "Клиенты"`.
  - [x] `backend/freesport/urls.py`: `path("manager/", manager_site.urls)` после `path("admin/", admin.site.urls)` (`:47`).
  - [x] Nginx (решение 11) — локация, копия блока `location /admin/`, в двух конфигах:
    - `docker/nginx/conf.d/default.conf` (прод, HTTPS-сервер, рядом с `location /admin/` на `:204`). Таймауты 120 с и `include /etc/nginx/snippets/app-headers.conf;` — как у `/admin/`;
    - `docker/nginx/conf.d/local.conf` (рядом с `:73`).

    Префикс — `location /manager/`. Запрос `/manager` без слэша уйдёт в Next и получит 404: это допустимо, входная ссылка всегда со слэшем. В комментарии сниппета `docker/nginx/snippets/app-headers.conf:2` дописать `/manager/` в перечень локаций.
  - [x] `robots.ts` не трогать: страница входа Django отдаёт `<meta name="robots" content="NONE,NOARCHIVE">`, фронтенд в эпике не меняется (SPEC, Non-goals).

- [x] **Task 2 — `UserAdmin` готов ко второму сайту** (AC7, AC8, AC9; решения 7, 9)
  - [x] Все Python-`reverse` с литералом `admin:` заменить на `f"{self.admin_site.name}:…"`. В `/admin/` поведение не меняется: имя сайта там `admin`. Места на `b4fab053` (после 42.2 строки сдвинулись на +28):
    - `verify_b2b_view`, `change_url` (`users/admin.py:603`);
    - `_verify_page_context`, `change_url` (`:719`);
    - `verify_b2b_link` (`:801`);
    - `onec_link_candidates`, `changelist_url` (`:830`);
    - `_warn_about_1c_candidates` (`:1001`).

    `user_change_password` (`:528`) уже использует `self.admin_site.name`. Контроль после правки: `grep -nE "reverse\(f?[\"']admin:" backend/apps/users/admin.py` ничего не находит.
  - [x] Перед `render(...)` в `verify_b2b_view` (`:639`) и в действии `link_1c_customer` (`:1066`) поставить `request.current_app = self.admin_site.name`. Шаблоны `templates/admin/users/verify_b2b_application.html` и `link_1c_customer.html` строят хлебные крошки через `{% url 'admin:index' %}` и фильтр `admin_urlname`. Без `current_app` они резолвятся в сайт по умолчанию, то есть в `/admin/`. Штатные вью `ModelAdmin` выставляют `current_app` сами (`django/contrib/admin/options.py:1395`, `:1751`, `:2181`, `:2321`), эти две — нет.
  - [x] `@admin.action(..., permissions=["change"])` у `approve_b2b_users`, `reject_b2b_users`, `block_users` (решение 9).
  - [x] Новое действие сразу после `block_users`:
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
  - [x] Больше в `UserAdmin` ничего не менять: fieldsets (включая блок «Ответственный менеджер» из 42.2), `get_fieldsets` с `PRIVILEGE_FIELDS`, `has_change_permission`/`has_delete_permission` для цели-суперпользователя, `get_deleted_objects` (42.2), AuditLog действий — как есть. Тест `tests/unit/test_users_admin.py` сверяет число блоков fieldsets (`7`) — он должен остаться зелёным без правок.

- [x] **Task 3 — `ManagerClientAdmin`** (AC2–AC7, AC9–AC11; решения 3–6, 8)
  - [x] Новый модуль `backend/apps/users/manager_admin.py`. Регистрация — в нём же: `manager_site.register(User, ManagerClientAdmin)`. Модуль импортировать в `UsersConfig.ready()` (`apps/users/apps.py`) рядом с `import apps.users.signals`: `import apps.users.manager_admin  # noqa: F401 — регистрация на сайте /manager/`. Порядок безопасен: `FreesportAdminConfig` стоит в `DJANGO_APPS` раньше `apps.users`, поэтому `admin.autodiscover()` уже импортировал `apps/users/admin.py`, когда срабатывает `UsersConfig.ready()`. **Не импортировать `manager_admin` из конца `users/admin.py`:** это циклический импорт частично загруженного модуля.
  - [x] Функция видимости (решение 3), в том же модуле, с docstring о 42.7:
    ```python
    def scope_clients(request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        return queryset.filter(responsible_manager=request.user).exclude(staff_accounts_q())
    ```
    Если `exclude` по m2m даст дубли или лишний JOIN в счётчике changelist, заменить на `~Exists(...)` по группам. Проверяется тестом AC11.
  - [x] `class ManagerClientAdmin(UserAdmin)`:
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
          ("1С и ответственный", {"fields": ("linked_to_1c", "onec_price_type_name", "responsible_manager_display")}),
          ("Даты", {"fields": ("created_at", "last_login"), "classes": ("collapse",)}),
      )
      ```
      `password` — `ReadOnlyPasswordHashField` с кнопкой «Сбросить пароль». Ссылка в ней относительная (`../password/`), на втором сайте работает без правок;
    - `readonly_fields = ("customer_code", "role", "verification_status", "is_verified", "linked_to_1c", "onec_price_type_name", "responsible_manager_display", "company_legal_address", "created_at", "last_login")`. `get_readonly_fields` возвращает этот список целиком, без логики `UserAdmin` про `customer_code`: в разделе код всегда только для чтения;
    - `get_fieldsets`: вернуть `self.fieldsets` как есть. Логику `UserAdmin.get_fieldsets` (скрытие `onec_link_candidates`, вычистка привилегий) не звать: в белом списке этих полей нет, а `find_link_candidates` на каждом открытии карточки — лишний запрос;
    - display `linked_to_1c` (`boolean=True`, «Связан с 1С»): `bool(obj.onec_id or obj.onec_guid)`, без запросов;
    - display `responsible_manager_display` («Ответственный менеджер», решение 12): `obj.responsible_manager` → `"<ФИО> (<email>)"` или `"—"`, простой строкой без `format_html` со ссылкой. `User.__str__` (`"<email> (<роль>)"`) не брать: роль сотрудника «Розничный покупатель» в подписи сбивает. Один запрос FK на открытие карточки — допустимо. Поле `responsible_manager` в форму не попадает вовсе, поэтому подделанный POST его не тронет (AC5);
    - `changelist_view`: `extra_context["title"] = "Клиенты"`.
  - [x] `save_model` (решение 8): если `"is_active" in form.changed_data`, после `super().save_model(...)` записать `AuditLog`. Вид действия — `block_user` или `unblock_user`, `changes={"email", "role", "blocked", "source": "card"}`, `ip_address` и `user_agent` — через `self._get_client_ip(request)`, как в действиях.
  - [x] `response_change` (AC10): после сохранения проверить `self.get_queryset(request).filter(pk=obj.pk).exists()`. Если клиент ушёл из видимости (хук 42.2 сменил ответственного по новому ИНН или стране):
    - сообщение уровня warning «Клиент {email} передан менеджеру {obj.responsible_manager.email или «без ответственного»} по правилу региона»;
    - `HttpResponseRedirect(reverse(f"{self.admin_site.name}:users_user_changelist"))`.

    Иначе `super().response_change(...)`.
  - [x] `PortalAccountFilter(admin.SimpleListFilter)`, «Учётная запись на портале», `parameter_name="portal_account"`:
    - без значения (по умолчанию) → `exclude(role=User.ROLE_UNREGISTERED)`;
    - `"no"` → только `unregistered`;
    - `"all"` → всё.

    `choices()` переопределить так, чтобы пункт по умолчанию назывался «Есть» и был выбран без параметра, а штатного «Все» с тем же значением не было. Если в запросе `role__exact=unregistered`, исключение по умолчанию не применять, иначе фильтр роли «Не зарегистрирован» всегда давал бы пустой список. Docstring: почему скрыты (4600+ контрагентов 1С без аккаунта, SPEC, Assumptions).

- [x] **Task 4 — ссылка письма менеджеру** (AC8; решение 10)
  - [x] `apps/users/tasks.py:441` (`send_manager_region_email`): `"admin_url": f"{settings.SITE_URL}{reverse('manager:users_user_verify', args=[user.id])}"`. Ключ контекста `admin_url` не переименовывать: его читают шаблоны.
  - [x] `templates/emails/manager_region_notification.txt:15`: «Открыть в админ-панели» → «Открыть в разделе менеджера». В `.html` (`:79`) поправить подпись кнопки, если она говорит об админке.
  - [x] `send_admin_verification_email` (`tasks.py:75`) не трогать.

- [x] **Task 5 — новые тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [x] Общие фикстуры:
    - autouse `role_groups` — через функцию миграции, как `tests/integration/test_staff_access_lockdown.py:46-53`;
    - autouse `ManagerRoutingRule.objects.all().delete()`: сид `0018` в тестовой БД то есть, то стёрт `flush` транзакционного теста, а хук 42.2 назначает ответственного при создании. Образец — фикстура `team` в `tests/integration/test_responsible_manager_events.py:85`;
    - `make_staff_member(group_name)` — по образцу `test_staff_access_lockdown.py:55-67` или `make_staff` из `test_responsible_manager_events.py:43`.
  - [x] **Тесты транзакционные.** Autouse `clear_db_before_test(transactional_db)` в `tests/conftest.py:671` включает `transactional_db` для всех тестов: обёртки-транзакции нет, после теста БД очищает `flush`. Ревью 42.3 это подтвердило (повторное ревью, вердикт ID 1). Отсюда: правки групп и прав внутри теста не «откатываются», их стирает `flush`, а autouse `role_groups` следующего теста создаёт группу заново с полным набором. Сид `0018` после первого транзакционного теста тоже стёрт.
  - [x] **Ловушка хука 42.2.** `create_user(..., responsible_manager=A)` не сработает: хук в `save()` у новой записи без ручного назначения перезапишет поле результатом правил (без правил — `None`). Два рабочих пути:
    1. без правил — создать клиента, потом закрепить: `User.objects.filter(pk=c.pk).update(responsible_manager=A)`. Хелпер `make_client(manager, **overrides)` по образцу `make_applicant` (`tests/integration/test_admin_link_1c_customer.py:57`) или `make_client` из `test_responsible_manager_events.py:54`;
    2. с правилами — `ManagerRoutingRule.objects.create(match_type="inn_region", match_value="23", manager=A)`: сигнал 42.2 (`users/signals.py`, `post_save` правила) сразу переводит на A всех клиентов ключа `23`, а клиент, созданный после правила, получает A хуком. Так строятся AC2 и AC10.

    Сотрудника и суперпользователя с `responsible_manager=A` — только через `update()`: хук и сигнал сотрудникам ответственного не назначают.
  - [x] `backend/tests/integration/test_manager_clients_section.py` (integration):
    - AC1 — матрица входа: менеджер, руководитель → 200 и заголовок; маркетолог, сотрудник без группы, суперпользователь, суперпользователь в группе «Менеджеры», аноним, заблокированный менеджер → 302, `"/manager/login/" in response.url`.
    - AC2 — список и поиск по шести полям, клиент B не находится. С `responsible_manager=A` через `update()` не видны: `is_staff`, суперпользователь, `role="admin"` без `is_staff` и член группы «Маркетинг» без `is_staff` — по одной записи на каждое условие `staff_accounts_q()`, чтобы удаление любого из них ронял тест. `unregistered` с `responsible_manager=A` виден только с `portal_account=no` или `all`, а с `role__exact=unregistered` виден без `portal_account`.
    - AC3 — GET и POST карточки, `history`, `verify`, `password` клиента B → 404. Массовые действия с `_selected_action=[свой, чужой]` меняют только своего, у чужого состояние и `AuditLog` прежние. Образец POST действия — `post_action` в `test_admin_link_1c_customer.py`.
    - AC4 — разобрать `response.context["adminform"]` и HTML: правимые поля в `form.fields`, только для чтения — в `readonly_fields`. Для каждого поля «Не показывать» нет ни `name="<поле>"`, ни его `verbose_name` в HTML. Нет `addlink` и `deletelink`. У клиента с ответственным A в HTML есть email A и нет `f'/manager/users/user/{A.pk}/'`.
    - AC5 — POST с полным набором разрешённых полей и инлайнов (management form `company-*`, `addresses-*` собрать из GET-контекста) плюс подделанные поля. После `refresh_from_db` подделанные значения не применились, разрешённое (телефон) сохранено.
    - AC6 — разблокировка: заблокированный клиент → активен, `authenticate(email=…, password=…)` возвращает пользователя, одна запись `unblock_user`. Заявка `pending` в выборке не изменена, в сообщениях есть ссылка `/manager/users/user/<id>/verify/`. Суперпользователь в выборке (`_selected_action` с его id) не изменён: он и так вне queryset.
    - AC7 — по каждому действию из AC7 ровно одна запись своего вида, автор — менеджер. Подтверждение с привязкой → `link_1c_customer` и `verify_b2b` по одной. Флаг «активен» в карточке → `block_user` или `unblock_user` с `details["changes"]["source"] == "card"`. Подготовка данных для подтверждения и привязки — `make_1c_record` и `make_applicant` из `test_admin_link_1c_customer.py`: импортировать из этого модуля или скопировать в новый файл. Новый общий модуль хелперов не заводить.
    - AC8 — для главной, списка, карточки, `verify`, страницы привязки и `password` `'href="/admin/' not in html`. Не `"/admin/" not in html`: статика Django лежит в `/static/admin/`. Главную открывать после POST карточки клиента — тогда у менеджера есть `LogEntry`, и без решения 13 в HTML была бы `href="/admin/users/user/<id>/change/"`. Редиректы после подтверждения, отказа, смены пароля и сохранения начинаются с `/manager/`.
    - AC9 — у группы «Менеджеры» в тесте оставить только `view_user` (`group.permissions.set([...])`; после теста группу стирает `flush`, следующий тест получит её заново из `role_groups`). Карточка открывается, в контексте `show_verify_b2b_button is False`. `verify` GET и POST → 403. `password` → 403. Действий в `response.context["action_form"]` нет, подделанный POST `action=block_users` клиента не меняет.
    - AC10 — правила «23 → A», «77 → B» (`ManagerRoutingRule` с `manager`). POST карточки со сменой ИНН и `_continue` → 302 на `/manager/users/user/`, в сообщениях email B, `responsible_manager == B`.
    - AC11 — по образцу `TestChangelistIndicatorCost` (`test_admin_link_1c_customer.py:315`): 5 клиентов → baseline, ещё 45 → `django_assert_num_queries(baseline)`.
  - [x] `backend/tests/unit/test_manager_admin_site.py` (unit, `RequestFactory`):
    - `ManagerAdminSite.has_permission` для каждого случая AC1, у членства — один запрос на запрос (повторный вызов из кэша `request`, `django_assert_num_queries(1)`);
    - `scope_clients` — свой, чужой, сотрудник, суперпользователь;
    - `PortalAccountFilter` — три значения и связка с `role__exact`;
    - `unblock_users` в `UserAdmin` суперпользователя: те же исключения, что в AC6.
  - [x] **Проверка мутациями** (урок ревью 42.3: слой `verification-gap` находил защиты, удаление которых не роняет ни одного теста). По каждой защите временно убрать её, убедиться, что падает названный тест, вернуть. Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | `or user.is_superuser` в `has_permission` | AC1, суперпользователь в группе |
    | `.exclude(staff_accounts_q())` в `scope_clients` | AC2, записи сотрудников |
    | `_get_obj_does_not_exist_redirect` → `Http404` | AC3, карточка/история/`verify` чужого клиента |
    | `permissions=["change"]` у `block_users` | AC9, подделанный POST действия |
    | `raise PermissionDenied` в `verify_b2b_view` | AC9, `verify` → 403 |
    | `request.current_app` в `verify_b2b_view` | AC8, `href="/admin/` на `verify` |
    | `index_template` у `ManagerAdminSite` | AC8, главная после правки |
    | `save_model` с `AuditLog` флага «активен» | AC7, `source: card` |
    | `response_change` с проверкой видимости | AC10 (иначе 404 после `_continue`) |

- [x] **Task 6 — существующие тесты: менять только перечисленное**
  - [x] `tests/unit/test_region_routing.py:174`: `verify_path` → `f"/manager/users/user/{user.id}/verify/"`. Комментарий: решение 10 стори 42.4. Это единственное осознанное изменение ожиданий. `tests/unit/test_email_tasks.py:68` (письмо получателям уведомлений) не меняется.
  - [x] `tests/integration/test_admin_verify_b2b_application.py`: в комментариях `test_staff_is_redirected_to_login` (`:439-441`) и `TestEntryPoints.test_change_form_closed_for_staff` (`:486-488`) ссылку «вернётся тестами раздела менеджера (стори 42.4)» заменить ссылкой на `tests/integration/test_manager_clients_section.py` (AC9). Ожидания не менять.
  - [x] Прогнать без правок и убедиться: `test_admin_link_1c_customer.py` (в т. ч. `TestChangelistIndicatorCost:315` — в `/admin/` добавилось действие, но не колонка), `test_admin_verify_b2b_application.py`, `test_admin_user_password.py`, `tests/unit/test_users_admin.py`, `test_staff_access_lockdown.py`, тесты 42.2 (`tests/unit/test_responsible_manager.py`, `tests/integration/test_responsible_manager_events.py`, `tests/unit/test_region_routing.py`, `tests/unit/test_manager_routing_rule.py`) и 42.3 (`test_recalculate_responsible_managers.py`, `test_admin_manager_routing_rule_regions.py`).

- [x] **Task 7 — проверки и закрытие**
  - [x] Полный backend-прогон в Docker, один compose-проект, без параллельных: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest`. Ориентир по 42.3: ≈ 4043 passed, 76 skipped, ~46 минут — запускать в фоне.
  - [x] `makemigrations --check --dry-run` в контейнере. Моделей стори не меняет — миграций нет (последние: `users/0025`, `common/0024`).
  - [x] Линтеры — навык `backend-lint` или контейнер, строго после зачётного pytest. **Проект `freesport-lint` не поднимается, пока живы контейнеры `freesport-test`:** у `freesport-test-redis` и сети фиксированные имена (Debug Log 42.3). Поэтому `black`, `flake8`, `mypy`, `makemigrations` и `check_openapi_sync` гонять в том же `-p freesport-test` после pytest. Базис после 42.3: `black --check .` — 462 unchanged, `flake8` чист, mypy — «no issues found in 615 source files». Любая ошибка — новая.
  - [x] `check_openapi_sync` — рецепт в Dev Notes; ожидается «синхронен» (API не менялся).
  - [x] Nginx: `docker compose --env-file .env -f docker/docker-compose.yml exec nginx nginx -t` и `nginx -s reload` (локальный `local.conf`). Прод-конфиг `default.conf` локально не исполняется — проверить его `nginx -t` по рецепту второго процесса nginx (Dev Notes, «Nginx»). Затем `curl -sI http://localhost/manager/` → 302 с `Location: /manager/login/?next=/manager/`.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [x] `deferred-work.md`: пункт VG1 (`:915-916`, `source_spec: spec-42-1-…`, «Проверки `change_user` в `UserAdmin`… вернуть их тестами раздела менеджера в 42.4») и его подтверждение в разделе ревью 42.1 (`:924`) пометить **ЗАКРЫТО** со ссылкой на тесты AC9.
  - [x] Completion Notes: шаги выката (Dev Notes, «Выкат»), ограничение `add_company`, отклонения от стори с причиной.

### Review Findings

Ревью 2026-10-13. Объём — незакоммиченная реализация на `feature/42-4-manager-section-clients` против `baseline_commit: b4fab053`, каталоги `backend/` и `docker/` (17 файлов, +1192/−18). Все четыре слоя завершились: `blind-hunter`, `edge-case-hunter`, `verification-gap`, `acceptance-auditor`. Из 23 исходных замечаний после проверки по коду и группировки по причине: 1 решение, 2 исправления, 1 отложено, 14 отклонено. Индекс GitNexus был `stale` (`b4fab05`), новых символов в нём нет.

- [x] [Review][Decision] Ссылка письма о заявке региона недоступна получателям не из раздела — `send_manager_region_email` теперь шлёт всем получателям `/manager/users/user/<id>/verify/` (`backend/apps/users/tasks.py:444`). Но `resolve_manager_recipients` берёт и `manager_email` правил без `manager` (`services/region_routing.py:60-66`), а в резерве из сида два адреса — CHERNOV и ADMIN (`common/migrations/0018_seed_manager_routing_rules.py:40`). Письмо уходит всем резервным адресам. Суперпользователя `/manager/` не пускает (решение 2), поэтому у него прежняя рабочая ссылка `/admin/…` превратилась в отказ. Если адрес правила без `manager` принадлежит менеджеру, ответственным у клиента он не будет: `resolve_responsible_for_key` берёт только правила с `manager`, клиент уходит на резерв, и ссылка отвечает 404. Решение 10 исходит из того, что получатель — всегда менеджер или руководитель, а это верно только после полной перенастройки правил на выкате. Варианты: (а) оставить как есть и вычистить на выкате правила без `manager` и адрес ADMIN из резерва; (б) в письме обе ссылки, `/manager/` и `/admin/`; (в) для получателей без доступа к разделу отдельное письмо со ссылкой `/admin/`. **Решение Alex 2026-10-13: вариант (а)** — код не меняется, в шаг 1 выката (Completion Notes) добавлена чистка правил.
- [x] [Review][Patch] Маршрут `/manager/` в `default.conf` не охраняется тестом известных локаций: добавить `("default.conf", "/manager/")` в параметры `test_known_location_is_covered` [backend/tests/unit/test_nginx_security_headers.py:296]
- [x] [Review][Patch] `test_member_of_several_groups_is_not_duplicated` ничего не проверяет: менеджер состоит в одной группе, у клиента групп нет. Нужно добавить менеджера и в «Руководители» (или клиента в группу вне ролей) [backend/tests/unit/test_manager_admin_site.py:113]
- [x] [Review][Defer] Заблокированный клиент получает 200 и JWT на `/api/v1/auth/login/` [backend/apps/users/views/authentication.py:314] — deferred, pre-existing: `UserLoginSerializer` намеренно достаёт и неактивных (`serializers.py:538`), а `UserLoginView.post` проверяет только `verification_status == "pending"`, затем выдаёт токены и вызывает `login()`. Последующие запросы, вероятно, отклоняются (SimpleJWT и `ModelBackend.get_user` не пускают `is_active=False`), но вход отвечает «успешно». Тест AC6 проверяет `authenticate()`, а не реальный эндпоинт. Важно для блокировки из раздела менеджера; severity medium.

**Отклонено (14):**

- `false` — «Маркетолог и суперпользователь входят через форму `/manager/login/` без объяснения отказа» (blind): штатный `admin/login.html` для аутентифицированного пользователя без `has_permission` показывает errornote «вы вошли как …, но у вас нет доступа к этой странице». Отказ 302 на логин закреплён решением 2.
- `false` — «AC11 не ловит N+1 на строках заявок с кандидатами 1С» (blind): `has_1c_candidate` и `verify_b2b_link` строятся по полям строки и аннотации `_has_1c_candidate` (`admin.py:788-806`), запросов на строку нет.
- `false` — «Чужой `candidate` при привязке» (blind): `_apply_link_1c_customer` сверяет `candidate` с `eligible_link_candidates(target)` (`admin.py:1096-1103`), а это записи `unregistered` с тем же ИНН, то есть того же региона. Что кандидаты — не клиенты менеджера, сказано в Dev Notes, «Подводные камни».
- `low` — Флаг «активен» в карточке включает и заявку `pending`, а `unblock_users` её пропускает (blind+edge): вход заявке всё равно закрыт проверкой `pending` в `UserLoginView`, флаг в карточке правится по решению 8, исправление — новая проверка в форме.
- `low` — `unblock_users` сохраняет пользователя и пишет `AuditLog` без общей транзакции (blind+edge): тот же шаблон, что у существующего `block_users`; отказ простого INSERT маловероятен.
- `low` — Гонка двух параллельных разблокировок даёт две записи журнала (blind): маловероятно, исправление — блокировка строк.
- `low` — Ответственный меняется между чтением queryset и сохранением карточки или действия (blind+edge): окно в миллисекунды, исправление — `select_for_update` по всем путям.
- `low` — Пароль сменён, а запись `change_password` пропущена, если ответственный сменился посреди запроса (edge): та же гонка.
- `low` — «Есть» в фильтре портала подсвечено при `role__exact=unregistered` (blind): косметика; связка с фильтром роли прописана в Task 3.
- `low` — После подтверждения с привязкой клиент может уйти к другому менеджеру, и редирект на карточку даст 404 (blind+edge): так бывает только при ИНН 1С с пробелом в начале, когда `region_key` уводит клиента в резерв. Исправление — новая ветка во `verify_b2b_view`.
- `low` — Коллизия `unique_digits(5)` в тестах (edge): вероятность около 1e-5 на пару значений.
- Отклонено (правка спецификации) — `role__exact=unregistered` показывает `unregistered` без «нет»/«все», а AC2 буквально это запрещает (auditor): поведение прямо задано Task 3, противоречие внутри стори.
- Отклонено (правка спецификации) — ожидание `test_admin_actions_list` изменено вне перечня Task 6 (auditor): правку вынуждает Task 2 (`unblock_users`), она описана как отклонение 2.
- `low` — Полный прогон после последних правок не повторён (auditor): после зелёного полного прогона менялись только ожидание одного теста и аннотации типов; изменённые файлы прогнаны, полный набор пройдёт PR-гейт CI.

## Dev Notes

### Текущее состояние кода (сверено на `b4fab053`, после 42.2 и 42.3)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py` | только `SuperuserAdminSite` (42.1) | + `ManagerAdminSite`, `manager_site` |
| `backend/freesport/urls.py:40-47` | `/admin/monitoring/`, `/admin/` | + `/manager/` |
| `backend/apps/users/apps.py` `UsersConfig.ready` | импорт `signals` (в нём с 42.2 и сигналы правил региона), переименование `AuthConfig` | + импорт `manager_admin` |
| `backend/apps/users/admin.py:236-1239` `UserAdmin` | `list_select_related=["company"]`; блок fieldsets «Ответственный менеджер» (`:351-361`, 42.2); `get_deleted_objects` (`:504`, 42.2); действия `approve_b2b_users` (`:917`), `reject_b2b_users` (`:1137`), `block_users` (`:1184`) без `permissions`, `link_1c_customer` (`:1019`) с `permissions=["change"]`; `change_view` (`:559`, `show_verify_b2b_button`), `verify_b2b_view` (`:587`, `_get_obj_does_not_exist_redirect` на `:596`), `user_change_password` (`:521`, пишет `change_password`); захардкоженный `admin:` в пяти `reverse` | namespace, `current_app`, `permissions`, `unblock_users` |
| `backend/apps/users/admin.py:48,83` `CompanyInline`, `AddressInline` | инлайны компании и адресов | переиспользуются как есть |
| `backend/apps/users/admin.py:161` `Has1CCandidateFilter` | уже страхуется от «второй AdminSite» без аннотации (комментарий `:179-182`) | переиспользуется |
| `backend/apps/users/models.py` `User` | `responsible_manager` (FK на себя, `PROTECT`, `limit_choices_to=RESPONSIBLE_MANAGER_CHOICES`), `responsible_manager_manual`; хук автоназначения в `save()` (`:378-422`); `__str__` → `"<email> (<роль>)"` | не меняется |
| `backend/apps/users/staff_roles.py` | имена групп, `staff_accounts_q()`, `RESPONSIBLE_MANAGER_CHOICES` (42.2) | не меняется, импортируется |
| `backend/apps/users/services/responsible_manager.py` | `assign_responsible_manager`, `is_staff_account`, `reassign_clients_for_key` (42.2) | не меняется |
| `backend/apps/users/services/verify_b2b_application.py:226,304` | пишет `verify_b2b`, `reject_b2b`; при подтверждении явно назначает ответственного (42.2); при привязке зовёт `link_1c_customer` → `link_1c_customer` (`link_1c_customer.py:274`) | не меняется |
| `backend/apps/users/management/commands/recalculate_responsible_managers.py` (42.3) | одна транзакция: advisory-блокировка с импортом 1С, `LOCK TABLE` правил, `SELECT … FOR UPDATE` клиентов по возрастанию id | не меняется; см. «Подводные камни» |
| `backend/apps/users/tasks.py:441` `send_manager_region_email` | ссылка `/admin/users/user/<id>/verify/` | → `/manager/…` |
| `backend/templates/admin/users/verify_b2b_application.html:6-12`, `link_1c_customer.html:6-10` | хлебные крошки через `{% url 'admin:index' %}`, `admin_urlname` | не меняются (лечится `current_app`) |
| `backend/templates/admin/index.html`, `_app_block.html` | главная: `{% extends "admin/index.html" %}` с переопределением только `{% block content %}`; боковой `{% block sidebar %}` («Последние действия») — штатный Django; ссылка импорта только для `integrations` | не меняются; главная `/manager/` — `admin/manager/index.html` поверх них с пустым `sidebar`, блок «Пользователи» → «Клиенты» через `get_app_list` |
| `backend/templates/admin/users/user/change_form.html` | кнопка «Подтверждение заявки» через `opts\|admin_urlname:'verify'` при `show_verify_b2b_button` | не меняется: штатный `change_view` ставит `current_app` |
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
| `verify_b2b_view` | 302 (`users/admin.py:596`) | 404 |
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
- **Ссылки, которые Django строит сам, без `current_app`** (найдено при освежении 12.10): `LogEntry.get_admin_url()` (блок «Последние действия» главной) — `reverse("admin:…")` без `current_app`, отсюда решение 13. Readonly-FK, наоборот, берёт `current_app` и ведёт в `/manager/…`, но на объект вне видимости — отсюда решение 12. Новое readonly-поле FK в карточке раздела — только display-методом.
- **Хук 42.2 в карточке раздела.** Форма сохраняет без `update_fields`, поэтому смена ИНН или страны в карточке переназначает ответственного (AC10). У клиента с `responsible_manager_manual=True` хук ничего не меняет, клиент остаётся у менеджера. Флаг «Назначен вручную» в разделе не показывается и не правится — это работа руководителя в 42.7.
- **Сигналы правил 42.2 в тестах.** `ManagerRoutingRule.objects.create/save/delete` синхронно переназначает клиентов ключа (`users/signals.py`, `reassign_clients_for_key`). Создание правила после клиентов меняет их ответственного — не удивляться в AC2 и AC10. `ManagerRoutingRule.objects.all().delete()` в autouse-фикстуре шлёт `post_delete` на каждое правило, но у правил сида `manager` пуст, поэтому пересчёта нет.
- **Карточка во время пересчёта 42.3.** Команда `recalculate_responsible_managers` держит одну транзакцию и `SELECT … FOR UPDATE` на назначаемых клиентах. Сохранение такой карточки подождёт конца прогона (на проде ~4,7 тыс. клиентов — секунды). Блокировку импорта (`acquire_bulk_clients_lock`) раздел не берёт: правка одной карточки и действие над выбранными строками не массовая запись, цикла ожидания с командой по возрастанию id не образуют.
- **`ATOMIC_REQUESTS=True` только в `settings/test.py`.** В тестах каждый запрос — транзакция, на проде нет: цикл `unblock_users` сохраняет клиентов по одному. Ошибка посреди цикла оставит часть клиентов разблокированными с записями `AuditLog` — так же ведёт себя `block_users`, менять не нужно.
- **`role="admin"` в `staff_accounts_q()`.** Робот обмена 1С — `role="admin"` без `is_staff`. Он исключён из видимости тем же `scope_clients`, отдельной проверки не нужно.

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
- `check_openapi_sync` (тестовый контейнер монтирует только `backend/`; проект `freesport-test`, после зачётного pytest — см. Task 7):
  ```bash
  cd docker
  MSYS_NO_PATHCONV=1 docker compose -p freesport-test -f docker-compose.test.yml run --rm --no-deps -T \
    -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
    python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml
  ```

### Уроки 42.1, 42.2 и 42.3

- Сверять «было/стало» по прод-данным и маршрутам, а не только по коду. В 42.1 так нашёлся открытый `/admin/monitoring/`. Здесь так же нашлись: `/manager/` в nginx нет, ссылка письма ведёт в закрытую для менеджера `/admin/`, а Python-`reverse("admin:…")` тихо уводит со второго сайта.
- Тесты 42.1 переписали проверки `change_user` на «302 на вход» сайта и потеряли внутренние отказы `UserAdmin` (VG1). В разделе они снова единственная защита — AC9 возвращает их.
- Ревью 42.2 прошло семь кругов, 42.3 — несколько (R1–R22). Основные находки — тесты, которые остаются зелёными при удалении защиты, и гонки между записью и чтением. Для 42.4 гонок почти нет (одна карточка, нет кэшей), поэтому главная страховка — таблица мутаций в Task 5.
- Тестовые хелперы 42.2/42.3 сделаны через `User.objects.create_user` с `get_unique_suffix()`, роль, ИНН и страна задаются явно (отклонение 1 в Completion Notes 42.3). Тот же подход здесь.
- Отклонения от стори записывать в Completion Notes с причиной, не молча.
- Базис линтеров — ноль ошибок: после 42.3 `black` 462 unchanged, mypy 615 файлов без ошибок.

### Связь с последующими стори

- **42.5** регистрирует `Order` на том же `manager_site` и делает главную со счётчиками, расширяя `admin/manager/index.html` этой стори (без блока «Последние действия»). Видимость заказов строит от того же правила: заказы клиентов из `scope_clients`.
- **42.7** меняет только `scope_clients`: руководитель без фильтра, с заказами без клиента. В нём же — `responsible_manager` в карточке правит руководитель, ставится `responsible_manager_manual`.
- **42.9** строит ленту по видам действий AC7 плюс `unblock_user`.

### Project Structure Notes

- Новые файлы:
  - `backend/apps/users/manager_admin.py`;
  - `backend/templates/admin/manager/index.html`;
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
- Предыдущие стори: `Story/42-1-staff-roles-and-service-access-lockdown.md` (сайт `/admin/`, `PRIVILEGE_FIELDS`, наборы прав, VG1), `Story/42-2-responsible-manager-by-region-rule.md` (`responsible_manager`, `staff_accounts_q`, хук `save()`, «Связь с последующими стори» → 42.4), `Story/42-3-region-directory-and-responsible-recalculation.md` («Выкат» — шаги до 42.4, Review Findings R1–R22, Debug Log про `freesport-lint`).
- Тестовые образцы 42.2: `tests/integration/test_responsible_manager_events.py` (`make_staff`, `make_client`, фикстура `team`), `tests/unit/test_responsible_manager.py`.
- Django 5.2.7 (исходники в `backend/venv/Lib/site-packages/django/`): `contrib/admin/options.py:1824` (`_get_obj_does_not_exist_redirect`), `contrib/admin/helpers.py:251-264` (`AdminReadonlyField.get_admin_url`), `contrib/admin/models.py:235-247` (`LogEntry.get_admin_url`), `contrib/admin/templates/admin/index.html:20` (`{% block sidebar %}`), `contrib/auth/templates/auth/widgets/read_only_password_hash.html:7` (`../password/`).
- Долг: `_bmad-output/implementation-artifacts/deferred-work.md:915-916`, `:924` (VG1).
- Стандарты: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), Claude Code — 2026-10-13.

### Debug Log References

- **Task 0.** `git branch -r --contains 8c6687af` → `origin/develop` (PR 42.3 слит). Индекс GitNexus `stale` (`b4fab05` против `ec3308d`), но `git diff --stat b4fab05 HEAD -- backend docker` пуст — переиндексация не нужна. `impact --direction upstream`: `UserAdmin`, `verify_b2b_view`, `verify_b2b_link`, `onec_link_candidates`, `block_users`, `send_manager_region_email` — LOW, 0 прямых; `_verify_page_context`, `_warn_about_1c_candidates` — LOW, по 1 прямому; admin-метод `link_1c_customer` (`cypher` по `users/admin.py`) — вызывающих нет.
- **Мутации (Task 5).** Скрипт по очереди убирал защиту, гонял названный тест в `freesport-test` и возвращал файл:

  | Убрано | Результат |
  |---|---|
  | `or user.is_superuser` в `has_permission` | упал `TestEntry::test_others_are_redirected_to_login[superuser-in-managers-group]` |
  | `.exclude(staff_accounts_q())` в `scope_clients` | упал `TestChangelist::test_staff_accounts_are_hidden` |
  | `_get_obj_does_not_exist_redirect` → `Http404` | упал `TestForeignClient::test_direct_urls_answer_404` |
  | `permissions=["change"]` у `block_users` | упали 5 параметров `TestViewOnlyPermissions::test_actions_are_unavailable` (`action_form` перестаёт быть пустым) |
  | `raise PermissionDenied` в `verify_b2b_view` | упал `TestViewOnlyPermissions::test_verify_and_password_are_forbidden` |
  | `request.current_app` в `verify_b2b_view` | **выжила** — см. отклонение 1 |
  | `index_template` у `ManagerAdminSite` | упал `TestLinksStayInSection::test_pages_have_no_admin_links` |
  | `save_model` с `AuditLog` флага | упали оба параметра `TestAuditLog::test_card_active_flag` |
  | `response_change` с проверкой видимости | упал `TestClientMovedAway::test_redirect_to_changelist_with_message` |

- **Полный прогон** (`freesport-test`, без параллельных): `1 failed, 4137 passed, 76 skipped` за 43:57. Упал `tests/unit/test_users_admin.py::TestUserAdmin::test_admin_actions_list` — сверяет точный список `UserAdmin.actions`, куда Task 2 добавляет `unblock_users` (отклонение 2). После правки ожидания файл — 51 passed; новые тесты раздела вместе с `test_users_admin.py` после правок типов — 121 passed.
- **Проверки в `freesport-test` после pytest:** `black --check .` — 466 unchanged; `flake8 .` — чисто; `mypy --config-file=mypy.ini .` — сначала 9 ошибок в `manager_admin.py` (переопределения атрибутов и методов `UserAdmin`, типизированного под `auth.User`), исправлены аннотациями `Any` и `type: ignore[override|arg-type]` по образцу `users/admin.py`, итог «no issues found in 619 source files»; `makemigrations --check --dry-run` — No changes detected; `check_openapi_sync` — «Контракт синхронен с кодом».
- **Nginx.** `nginx -t` и `nginx -s reload` в dev-контейнере (`local.conf`) — ok. Прод-`default.conf` — вторым процессом nginx по рецепту Dev Notes (`/tmp/ngx`, порты 443/80 → 8080–8083, без `ssl_*`): `nginx -t -c /tmp/ngx/nginx.conf` — successful, `location /manager/` на месте. `curl -sI http://localhost/manager/` → `302`, `Location: /manager/login/?next=/manager/`; `/manager/login/` → 200 от Django.
- **Стенд.** На момент проверки `freesport-db` и `freesport-redis` dev-стека стояли в `Exited (255)` (упали при перезапуске Docker 13.10, к стори не относится) — подняты `docker start`, затем `restart backend` и `nginx -s reload`.
- **Исправления ревью (2026-10-13).** `test_known_location_is_covered` получил параметр `("default.conf", "/manager/")`. В `test_member_of_several_groups_is_not_duplicated` менеджер теперь в «Менеджерах» и «Руководителях», клиент — в двух группах вне ролей. Мутация: в `scope_clients` добавлен `.filter(Q(groups__isnull=True) | Q(groups__isnull=False))` (JOIN по m2m групп) — тест упал с `assert 2 == 1`, файл восстановлен. `black --check` и `flake8` по двум файлам чисты; файлы тестов стори (`test_manager_clients_section.py`, `test_users_admin.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`) — 169 passed. Полный прогон после исправлений (`freesport-test`, без параллельных): `4139 passed, 76 skipped` за 44:41.
- **`detect-changes --scope all`:** символы `UserAdmin` (namespace, `permissions`, `unblock_users`), `UsersConfig.ready`, `send_manager_region_email`, `admin_site.py`. `CompanyAdmin`, `AddressAdmin`, `FavoriteAdmin`, `_apply_verify_b2b` в списке из-за сдвига строк на устаревшем индексе — не менялись; «Risk: high» — артефакт того же индекса, impact каждого символа до правок — LOW.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-10-12 — стори освежена на `b4fab053` (первая редакция `9af7c7ed` писалась до кода 42.2 и 42.3). Эпик и спецификация с тех пор не менялись, AC сохранены. Изменено: предусловия (42.2 в `develop`, PR 42.3 ещё не слит), координаты `users/admin.py` (+28 строк после 42.2), тестов и `deferred-work.md`; решение 2 — явный отказ суперпользователю в группе; новые решения 12 (ответственный без ссылки) и 13 (главная без «Последних действий») с правками AC1, AC2, AC4, AC8; транзакционный режим тестов и сигналы правил 42.2 в Task 5; таблица мутаций; рецепт линтеров в `freesport-test`; подводные камни 42.2/42.3. GitNexus impact по всем символам Task 0 — LOW.
- 2026-10-13 — реализация. Сайт `/manager/` (`ManagerAdminSite`, `manager_site`) с кэшем членства на `request`, своей главной без «Последних действий» и подписью «Клиенты» у блока и модели. `ManagerClientAdmin` в `apps/users/manager_admin.py`: видимость `scope_clients`, 404 на чужого клиента, белый список полей карточки, ответственный текстом, журнал флага «активен» (`source: card`), редирект на список с сообщением, когда клиент ушёл к другому менеджеру, фильтр «Учётная запись на портале». В `UserAdmin`: пять `reverse("admin:…")` → `self.admin_site.name`, `permissions=["change"]` у одобрения, отказа и блокировки, новое действие `unblock_users`. Письмо менеджеру региона ведёт на `/manager/users/user/<id>/verify/`. Nginx проксирует `/manager/` в обоих конфигах. Долг VG1 закрыт в `deferred-work.md`.
- Тесты: `tests/integration/test_manager_clients_section.py` (AC1–AC11) и `tests/unit/test_manager_admin_site.py` (доступ к сайту, один запрос членства, `scope_clients`, `PortalAccountFilter`, `unblock_users` в `/admin/`) — 70 тестов.
- **Отклонение 1 — `request.current_app` в `verify_b2b_view` и `link_1c_customer` не добавлен.** Мутация показала, что строка ничего не защищает: `{% url %}` без `request.current_app` берёт `request.resolver_match.namespace` (`django/template/defaulttags.py:470-475`), а обе страницы маршрутизируются в пространстве `manager`. Хлебные крошки и так ведут в `/manager/` — это закреплено тестом AC8 (`href="/admin/` нет на страницах подтверждения и привязки). Строку с неверным обоснованием в комментарии добавлять не стал.
- **Отклонение 2 — изменено ожидание вне перечня Task 6:** `tests/unit/test_users_admin.py::test_admin_actions_list` сверяет точный список действий `UserAdmin`; `unblock_users` в нём — прямое требование Task 2. Добавлена одна строка списка с комментарием.
- **Отклонение 3 — тестовый `make_client` по умолчанию ставит `responsible_manager_manual=True`.** Иначе подтверждение заявки и привязка к 1С (явный вызов 42.2 в сервисе) пересчитывали бы ответственного по пустым в тесте правилам, и клиент уходил бы из раздела до проверки. AC10 строится без флага, через правила «23 → A», «77 → B».
- **Ограничение (вне скоупа):** права `add_company` у роли нет, поэтому у клиента без `Company` блок реквизитов в карточке пуст и добавить его менеджер не может. Company создают привязка к 1С, импорт и личный кабинет.
- **Выкат (для Alex):**
  1. До выката — action_item эпика «После выката 42.3 и до 42.4»: учётные записи менеджеров (`is_staff`, группа «Менеджеры»), правила регионов с `manager`, резервное правило на руководителя, пересчёт ответственных (сначала `--dry-run`). Проверка — SQL из Dev Notes, «Выкат», шаг 1: у каждого менеджера клиентов больше нуля. Там же: у активных правил без `manager` проставить `manager` или выключить их, адрес ADMIN из резерва убрать — письмо о заявке региона ведёт в `/manager/`, и получатель без доступа к разделу (суперпользователь, адрес правила без `manager`) по ссылке не попадёт. Проверка: `SELECT id, match_type, match_value, manager_email FROM common_managerroutingrule WHERE is_active AND manager_id IS NULL;` — пусто (решение ревью 2026-10-13).
  2. После выката: `curl -sI https://optisport.ru/manager/` → 302 на `/manager/login/?next=/manager/`. 404 от Next означает, что nginx не перечитал конфиг: `docker compose exec nginx nginx -s reload`.
  3. Вход тестовым менеджером: список своих клиентов, чужая карточка по URL — 404.
  4. Письмо о новой B2B-заявке ведёт на `/manager/users/user/<id>/verify/`.
  5. После рестарта backend — `restart nginx` (деплой делает сам).

### File List

- `backend/freesport/admin_site.py` — `ManagerAdminSite`, `manager_site`
- `backend/freesport/urls.py` — маршрут `manager/`
- `backend/apps/users/apps.py` — импорт `manager_admin` в `ready()`
- `backend/apps/users/manager_admin.py` — новый: `scope_clients`, `PortalAccountFilter`, `ManagerClientAdmin`
- `backend/apps/users/admin.py` — namespace сайта в `reverse`, `permissions=["change"]`, `unblock_users`
- `backend/apps/users/tasks.py` — ссылка письма менеджеру региона
- `backend/templates/admin/manager/index.html` — новый: главная без «Последних действий»
- `backend/templates/emails/manager_region_notification.txt`, `backend/templates/emails/manager_region_notification.html` — подпись ссылки
- `docker/nginx/conf.d/default.conf`, `docker/nginx/conf.d/local.conf` — `location /manager/`
- `docker/nginx/snippets/app-headers.conf` — комментарий
- `backend/tests/integration/test_manager_clients_section.py` — новый
- `backend/tests/unit/test_manager_admin_site.py` — новый
- `backend/tests/unit/test_region_routing.py` — ожидание ссылки письма
- `backend/tests/unit/test_users_admin.py` — список действий (отклонение 2)
- `backend/tests/unit/test_nginx_security_headers.py` — локация `/manager/` в перечне известных (ревью)
- `backend/tests/integration/test_admin_verify_b2b_application.py` — комментарии
- `_bmad-output/implementation-artifacts/deferred-work.md` — VG1 закрыт
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — статус стори
- `_bmad-output/implementation-artifacts/Story/42-4-manager-section-own-clients.md` — этот файл

### Change Log

- 2026-10-13 — реализация стори 42.4: раздел менеджера `/manager/` с клиентами своего региона, действие «Разблокировать», ссылка письма менеджеру в раздел, nginx-локация; 70 новых тестов, мутационная проверка защит; статус → review.
- 2026-10-13 — исправления ревью: 2 замечания [Review][Patch] закрыты (страж локации `/manager/` в `test_nginx_security_headers.py`, содержательная проверка дублей в `test_member_of_several_groups_is_not_duplicated`); полный прогон 4139 passed; статус → review.
