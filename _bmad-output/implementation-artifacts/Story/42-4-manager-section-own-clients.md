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

#### Повторное ревью 2026-10-13 — `b4fab053..6169d186`

Проверено 20 замечаний: `blind-hunter` — 10, `edge-case-hunter` — 8, `acceptance-auditor` — 2. Слой `verification-gap` завершился ошибкой провайдера `Selected model is at capacity`, результатов не дал; ревью этим слоем неполное. GitNexus актуален (`6169d18`); `detect-changes --scope all` — нет незакоммиченных изменений, `--scope compare --base-ref b4fab053` — 21 файл, 62 символа, 11 потоков, общий риск high. `impact UserAdmin` — LOW, 2 прямые зависимости; `impact scope_clients` — LOW, 1 прямой вызывающий.

Проверка в Docker: `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest tests/integration/test_manager_clients_section.py tests/unit/test_manager_admin_site.py --cov=apps.users.manager_admin --cov=freesport.admin_site --cov-report=term-missing --cov-fail-under=0 --override-ini=addopts= -q` из `docker/` — **70 passed**, 6 предупреждений об устаревающих API; покрытие `manager_admin.py` — **99%**, `admin_site.py` — **97%**. Полный регресс в этом ревью не повторялся.

Итог: 0 решений, 3 исправления тестов, 1 отложенное замечание, 16 отклонено. Ни одно из трёх исправлений не означает, что текущая реализация допускает описанную регрессию: это недостающие приёмочные проверки.

Решение Alex 2026-10-13: оставить три [Review][Patch] задачами в story (вариант 2), без исправлений кода и тестов. Статус story и записи спринта — `review` → `in-progress` до закрытия этих задач.

- [x] [Review][Patch] ID 5 (`blind-hunter`, medium): проверить сохранение и изоляцию настоящих `CompanyInline` и `AddressInline` — `TestClientCard` создаёт клиента без Company и Address, проверяет лишь два префикса формсетов и сохраняет телефон пользователя. Создать связанные записи своего и чужого клиентов; проверить изменение реквизитов/адреса своего, добавление и удаление адреса, а также отказ подмены ID инлайна чужого клиента и неизменность его записей. Это закрепляет AC4 и границу «только свои клиенты» на связанных объектах. [backend/tests/integration/test_manager_clients_section.py:459-545]
- [x] [Review][Patch] ID 6 (`blind-hunter`, low): добавить негативный POST самой карточки при одном `users.view_user` — `TestViewOnlyPermissions` проверяет GET карточки и POST других маршрутов, но не попытку сохранить карточку. Проверить 403 и неизменность разрешённых полей клиента и журналов; проверить связанные записи в варианте с инлайнами. Текущий отказ обеспечивает Django, но у этой границы записи нет собственного негативного теста NFR-42-02. [backend/tests/integration/test_manager_clients_section.py:760-814]
- [x] [Review][Patch] ID 7 (`blind-hunter`, medium): увеличивать число строк с кандидатами 1С в тесте стоимости списка — при переходе от 5 к 50 клиентам число pending-строк с кандидатами остаётся пять. Запрос, добавленный только в `has_1c_candidate`/`verify_b2b_link` для этих строк, увеличит оба замера одинаково, и тест останется зелёным. Дополнительные 45 клиентов должны также иметь кандидатов; проверить одинаковое число запросов и 50 строк. Сейчас эти display-методы SQL не выполняют, речь о защите AC11 от будущей регрессии. [backend/tests/integration/test_manager_clients_section.py:852-869]
- [x] [Review][Defer] ID 16 (`edge-case-hunter`, medium): подтверждение с привязкой может замкнуть цикл блокировок с пересчётом ответственных — deferred, существовавший до 42.4 путь: `verify_b2b_application` сначала блокирует target, затем `link_1c_customer` блокирует source/target по возрастанию ID, тогда как команда пересчёта блокирует все назначаемые строки по возрастанию ID. Если `source.pk < target.pk` и обе строки требуют пересчёта, подтверждение может держать target и ждать source, пока команда держит source и ждёт target; PostgreSQL прервёт одну транзакцию. Эти сервисы и команда в рассматриваемом diff не менялись; воспроизводящий конкурентный тест в этом ревью не запускался. Нужна отдельная проверка расписания двумя соединениями и единый порядок блокировок либо общая очередь до захвата target. [backend/apps/users/services/verify_b2b_application.py:156-157; backend/apps/users/services/link_1c_customer.py:149-153; backend/apps/users/management/commands/recalculate_responsible_managers.py:263-266]

##### Отклонено — повторное ревью (16)

- ID 1 (`blind-hunter`): `false` как дефект реализации — исключение для `role__exact=unregistered` прямо задано Task 3 и проверено тестами; противоречие буквальному AC2 уже разобрано первым ревью. Исправление самой спецификации исключается из actionable-замечаний.
- ID 2 (`blind-hunter`): `low` — отдельные save и AuditLog действительно оставляют окно при ошибке INSERT на production, где нет ATOMIC_REQUESTS; риск уже принят первым ревью, а его устранение требует новой транзакционной защиты редкого сбоя.
- ID 3 (`blind-hunter`): `low` — передача клиента или превращение его в сотрудника после чтения выборки может опередить разблокировку; редкая конкурентная гонка уже рассмотрена первым ревью, исправление требует блокировок и повторной авторизации.
- ID 4 (`blind-hunter`): `low` — при переносе ИНН с ведущим пробелом привязка может переназначить клиента на резерв, а редирект дать 404; тот же сценарий принят первым ревью, исправление добавляет отдельную ветку редкого исхода.
- ID 8 (`blind-hunter`): `false` — отсутствие замера не доказывает провал NFR-42-01; текущий Docker-прогон измерил 99% и 97%, оба модуля выше 90%. Требование добавить результаты теперь удовлетворено записью проверки выше.
- ID 9 (`blind-hunter`): `low` — чеклист и Dev Notes сохраняют исходное требование `request.current_app`, но Completion Notes явно фиксируют отказ от него и причину; предлагаемая правка касается story-спецификации, а не рабочего кода, исключена правилами triage.
- ID 10 (`blind-hunter`): `low` — SQL `manager_id IS NULL` сам по себе не проверяет активность и права менеджера, однако это лишь одна часть ручного плана: остальные шаги требуют подходящих учётных записей, пересчёта и проверки входа/письма. Улучшение текста предвыкатной проверки меняет спецификацию, не является новым patch кода.
- ID 11 (`edge-case-hunter`): `low` — полный save устаревшей карточки может перезаписать параллельно изменённого ответственного, если ИНН/страна не менялись; это уже принятое окно гонки первого ревью, не воспроизведённый штатный сценарий, исправление требует новой блокировки границы формы.
- ID 12 (`edge-case-hunter`): `low` — потеря AuditLog после успешного save при ошибке INSERT подтверждается последовательностью операций; тот же редкий риск, что ID 2, уже принят, новая транзакционная защита не вводится этим ревью.
- ID 13 (`edge-case-hunter`): `low` — две конкурентные разблокировки могут дать две записи; гонка принята первым ревью, новая блокировка/повторная проверка ради редкого двойного запроса не предлагается.
- ID 14 (`edge-case-hunter`): `low` — смена ответственного между сохранением пароля и повторным scoped get_object может пропустить AuditLog и дать недоступный редирект; этот редкий конкурентный сценарий уже принят первым ревью, исправление расширяет транзакционный путь пароля.
- ID 15 (`edge-case-hunter`): `low` — редирект после привязки с переносом ИНН может дать 404 при уходе клиента на резерв; тот же редкий исход, что ID 4, уже принят; нужен новый условный редирект, не прямое исправление обычного сценария.
- ID 17 (`edge-case-hunter`): `low` — «Есть» подсвечено одновременно с фильтром роли `unregistered`; косметическое несоответствие известно из первого ревью, исправление добавляет зависимость выбора одного фильтра от другого.
- ID 18 (`edge-case-hunter`): `low` — `unique_digits(5)` не гарантирует отсутствие коллизии в одном тесте; вероятность мала, риск уже разобран первым ревью, замена генератора — дополнительная логика без наблюдённого сбоя.
- ID 19 (`acceptance-auditor`): `false` как дефект реализации — фильтр `unregistered` без параметра портала реализует Task 3; конфликт внутри AC2/Task 3 уже разобран, исправление спецификации исключено из actionable-замечаний.
- ID 20 (`acceptance-auditor`): `false` как дефект реализации — добавление `unblock_users` прямо требуется Task 2, поэтому обновление точного ожидаемого списка неизбежно; отклонение от перечня Task 6 явно записано в Completion Notes. Замечание требует согласовать спецификацию, а не исправлять корректный тест.

#### Третье ревью 2026-10-13 — `b4fab053..a7fef548`

Решение Alex 2026-10-13: вариант 2 — оставить ID 20 и ID 21 открытыми задачами в story, без исправлений кода и тестов. Статус story и записи спринта — `review` → `in-progress` до закрытия этих задач.

Все четыре слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 9, `verification-gap` — 2, `acceptance-auditor` — 2. Проверен сохранённый diff, включавший исправления повторного ревью ещё до их коммита; после коммита `a7fef548` объём тот же: 21 файл, +1910/−114. Итог: 0 решений, 2 исправления тестовых пробелов, 0 новых отложенных замечаний, 21 отклонено. Нового подтверждённого дефекта текущей реализации не выявлено.

GitNexus: индекс на `c2743ed`, HEAD после фиксации тестов — `a7fef548`; отличие — тесты и документы, код раздела не менялся. `detect-changes --scope compare --base-ref b4fab053`: 62 символа, 11 потоков, общий риск high. `impact --direction upstream`: `UserAdmin` — LOW, 2 прямые зависимости; `scope_clients` — LOW, 1 прямой вызывающий; `unblock_users`, `verify_b2b_view`, `send_manager_region_email` — LOW, прямых вызывающих граф не показал. Вызовы Celery через `.delay` этим результатом не исключаются.

Проверка в Docker (один прогон, без параллельных): `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest tests/integration/test_manager_clients_section.py tests/unit/test_manager_admin_site.py tests/integration/test_responsible_manager_events.py --override-ini=addopts= -q` из `docker/` — **129 passed**, 6 предупреждений об устаревающих API. Полный backend-прогон и новые мутации в этом ревью не выполнялись. Наличие существующих тестов общих сервисов подтверждено чтением, эти сервисные файлы в данном прогоне отдельно не запускались.

- [x] [Review][Patch] ID 20 (`verification-gap`, medium): закрепить изоляцию клиентов руководителя, а не только менеджера. `TestEntry::test_manager_and_supervisor_enter` проверяет руководителя без клиентов; проверки списка, поиска и чужих URL используют менеджера. Даже тест сотрудника в двух группах создаёт лишь собственного клиента. Если разрешить группе «Руководители» весь queryset, эти проверки не обнаружат расширение доступа вопреки решению 3. Параметризовать негативные проверки списка, поиска и прямых URL обеими группами, для каждого варианта создать собственного и чужого клиента. Это пробел регрессии, не обнаруженный обход в текущем `scope_clients`. [backend/tests/integration/test_manager_clients_section.py:263-282; backend/apps/users/manager_admin.py:31-41]
- [x] [Review][Patch] ID 21 (`verification-gap`, medium): автоматически проверять назначение маршрута `/manager/` в обоих Nginx-конфигах. `test_known_location_is_covered` проверяет наличие локации и сниппета, но не `proxy_pass`; Django-тесты обходят Nginx, а `nginx -t` принимает синтаксически корректный upstream фронтенда. Замена backend на frontend оставляет эти проверки зелёными и отправляет раздел в Next.js. Добавить проверку `proxy_pass` в блоке `/manager/` для `default.conf` и `local.conf`; HTTP-проверка через Nginx должна ожидать 302 и `Location: /manager/login/?next=/manager/`. Текущий upstream правильный, ручной замер уже записан; не хватает автоматического стража регрессии. [backend/tests/unit/test_nginx_security_headers.py:295-328; docker/nginx/conf.d/default.conf:227; docker/nginx/conf.d/local.conf:83]

##### Отклонено — третье ревью (21)

Каждое замечание получило вердикт до группировки; одинаковые причины ниже не скрывают отдельные исходные замечания.

- ID 1 (`blind-hunter`): `low` — передача клиента или смена его признаков после чтения выборки разблокировки действительно оставляет конкурентное окно; уже принято первым и повторным ревью. Новый повседневный сценарий не показан, исправление требует блокировки и повторной авторизации.
- ID 2 (`blind-hunter`): `low` — сохранение разблокировки и INSERT аудита на production не атомарны; редкий сбой и необходимость новой транзакции уже рассмотрены и приняты. Это не новый исход текущего ревью.
- ID 3 (`blind-hunter`): `low` — полный save карточки может затереть параллельное назначение, если ИНН и страна прежние (`User.save`: назначение пересчитывается только при изменении региона или снятии ручного флага). То же принятое окно гонки; новая блокировка ради редкого конкурентного исхода не предлагается.
- ID 4 (`blind-hunter`): `false` для заявленного несовпадения `manager_email` с назначенным пользователем — `_rule_emails` использует `manager.email`, когда менеджер задан, а не независимый адрес правила (`services/region_routing.py:61-69`). Активность, членство и вход проверяются другими шагами утверждённого плана выката; улучшение SQL этого плана меняет спецификацию и не является patch реализации.
- ID 5 (`blind-hunter`): `low` — новые end-to-end проверки подтверждения действительно используют ручное назначение, но обычное назначение при привязке и подтверждении уже проверяют `test_responsible_manager_events.py:217-259` с реальными правилами. Эти тесты прошли в текущем прогоне. Специфический редирект при переносе ИНН с пробелом уже принят предыдущими ревью; нового дефекта не показано, дополнительные сценарии не являются прямым исправлением кода.
- ID 6 (`blind-hunter`): `false` как отсутствие проверки самой защиты кандидата — общие сервисы имеют `test_source_not_among_candidates`, `test_stale_onec_id_rolls_back`, `test_live_account_as_source_is_rejected`, `test_stale_expected_onec_id_is_rejected`, `test_tax_id_mismatch_is_rejected`. Раздел наследует те же форму и действие, список разрешённых кандидатов проверяется в `admin.py:1096-1103`, затем повторно в сервисах под блокировкой. Отдельных manager-копий этих тестов нет, но это не новая непроверенная защита в diff.
- ID 7 (`blind-hunter`): `false` как дефект реализации — исключение для фильтра роли прямо предписано Task 3 и проверено. Конфликт буквального AC2 с Task 3 уже разобран; требуемое согласование спецификации исключено из actionable-замечаний.
- ID 8 (`blind-hunter`): `false` как нарушение выбранного поведения — редактируемый `is_active` в карточке и пропуск pending массовой разблокировкой прямо заданы решениями 7–8. Вход pending запрещён `UserLoginView.post`; унификация путей изменила бы утверждённые требования.
- ID 9 (`blind-hunter`): `false` как недостоверная проверка AC6 — этот AC явно требует `ModelBackend.authenticate`, что тест и проверяет. Успешный HTTP-login заблокированного пользователя — отдельный pre-existing дефект, уже записанный в deferred-work первым ревью; дублировать его как новую находку не требуется.
- ID 10 (`blind-hunter`): `low` — категоричное объяснение отсутствия deadlock в Dev Notes не учитывает ранее отложенный путь подтверждения с привязкой. Исправление текста меняет рассматриваемую спецификацию и исключено triage; сам конкурентный риск уже записан как deferred ID 16 повторного ревью.
- ID 11 (`edge-case-hunter`): `low` — перезапись скрытых полей полным save при конкурентной записи реальна по последовательности операций; тот же принятый редкий исход, что ID 3. Новая транзакционная блокировка не является прямым исправлением обычного пути.
- ID 12 (`edge-case-hunter`): `low` — изменение принадлежности или eligibility после загрузки candidates может опередить разблокировку; то же принятое окно ID 1, без нового воспроизведённого повседневного сценария.
- ID 13 (`edge-case-hunter`): `low` — два запроса могут прочитать неактивного клиента до первой записи и создать два `unblock_user`. Риск уже принят первым и повторным ревью; устранение требует новой блокировки и повторной проверки состояния.
- ID 14 (`edge-case-hunter`): `low` — ошибка INSERT AuditLog после save оставит разблокировку без журнала на production; тот же редкий риск ID 2, уже принятый, требуется новая атомарная граница.
- ID 15 (`edge-case-hunter`): `low` — сервис подтверждения блокирует цель, но не повторяет manager-scope после чтения карточкой; конкурентная передача клиента оставляет принятое окно авторизации. Новый сценарий не воспроизведён; устранение расширяет контракт общего сервиса.
- ID 16 (`edge-case-hunter`): `low` — после сохранения пароля повторный scoped `get_object` может вернуть None и пропустить аудит при конкурентной передаче. Ветка подтверждена `admin.py:523-544`, уже принята предыдущими ревью; новая общая транзакционная граница не добавляется ради редкого исхода.
- ID 17 (`edge-case-hunter`): `low` — перенос ИНН с ведущим пробелом может сменить регион, а `_apply_verify_b2b` возвращает старый change URL (`admin.py:728-768`). Редкий исход уже принят; исправление требует новой условной ветки редиректа.
- ID 18 (`edge-case-hunter`): `low` — пункт «Есть» оставляет фильтр роли `unregistered` и не меняет результат. Известная косметическая связка фильтров уже рассмотрена; исправление добавляет зависимость одного фильтра от другого.
- ID 19 (`edge-case-hunter`): `low` — генератор пяти цифр не гарантирует отсутствие коллизии, но редкий случай уже разобран. Новый сбой не наблюдался; устранение требует дополнительного распределителя уникальных значений.
- ID 22 (`acceptance-auditor`): `false` как дефект реализации — показ `unregistered` по фильтру роли предписан Task 3, противоречие AC2 известно. Исправление самой спецификации исключено triage.
- ID 23 (`acceptance-auditor`): `false` как дефект реализации — Task 2 требует добавить `unblock_users`, поэтому точное ожидание списка действий должно измениться. Отклонение от перечня Task 6 уже явно записано в Completion Notes; замечание требует согласовать спецификацию, не чинить рабочий тест.

#### Повторное ревью 2026-10-13 — `b4fab053..c2743ed3`

Объём: 21 файл, +1707/−114, 2353 строки diff; режим `full`. Незакоммиченные изменения ускорения тестов исключены из diff. Все четыре слоя завершились: `blind-hunter`, `edge-case-hunter`, `verification-gap`, `acceptance-auditor`. GitNexus актуален на `c2743ed`; impact `scope_clients`, `unblock_users`, `UserAdmin`, `ManagerClientAdmin`, `send_manager_region_email` — LOW. Из 23 исходных замечаний: 3 группы исправлений, 1 группа ранее существовавшего долга, 16 отклонённых замечаний. Код не исправлялся. Решение Alex 2026-10-13: оставить R42.4-1, R42.4-2 и R42.4-3 открытыми задачами; статус `review` → `in-progress` до их закрытия.

- [x] [Review][Patch] **R42.4-1: сохранение устаревшей карточки отменяет передачу клиента другому менеджеру** — `high`; источники: blind-hunter №3, edge-case-hunter №3/№4. `scope_clients` ограничивает чтение, но объект не блокируется до записи. `ManagerClientAdmin.save_model` вызывает полное `obj.save()`: после переназначения A → B между чтением и записью старый объект возвращает `responsible_manager=A`. `User.save()` читает актуальную запись, но при неизменных ИНН/стране не обновляет ответственного в старом объекте. Менеджер A сохраняет контакты уже переданного клиента и отменяет передачу; действия с `update_fields` не отменяют назначение, но тоже могут изменить клиента после выхода из разрешённой выборки. Закрепить проверку принадлежности и запись одной транзакцией с блокировкой строки до чтения изменяемого объекта; добавить проверку переназначения между чтением и записью. [backend/apps/users/manager_admin.py:132-133,175-178; backend/apps/users/admin.py:1281-1283; backend/apps/users/models.py:378-422]
- [x] [Review][Patch] **R42.4-2: нет автоматической HTTP-проверки `/manager/` через nginx** — `medium`; уточнено ревью `b4fab053..7728a9c8` 2026-10-13, источники: blind-hunter №7 и verification-gap №1. Статическая часть исходного замечания уже закрыта: `TestManagerSectionRoute::test_manager_location_proxies_to_backend[default.conf|local.conf]` проверяет `proxy_pass http://backend` в обоих конфигах. Остаётся проверка реально подключённого маршрута: Django client обходит nginx, HTTP-проверки выката проверяют API и главную, но не `/manager/`. Добавить в существующий шаг проверки production запрос `/manager/` с ожиданием 302 и `Location: /manager/login/?next=/manager/`, затем 200 страницы входа Django. Ручной замер не заменяет автоматическую проверку подключения маршрута. [backend/tests/unit/test_nginx_security_headers.py:342-365; .github/workflows/deploy.yml:457-495; docker/nginx/conf.d/default.conf:227; docker/nginx/conf.d/local.conf:83]
- [x] [Review][Patch] **R42.4-3: фильтр показывает выбранное «Есть» для записей без портального аккаунта** — `low`; источник: edge-case-hunter №8. При `role__exact=unregistered` без `portal_account` метод `queryset()` намеренно показывает незарегистрированных контрагентов (Task 3), но `choices()` выделяет «Есть». Исправить выбор пункта фильтра для этого сочетания и закрепить отображение тестом, не меняя утверждённое исключение фильтра роли. [backend/apps/users/manager_admin.py:59-83]
- [x] [Review][Defer] **R42.4-D1: заблокированный клиент получает успешный ответ входа и JWT** — `medium`; источники: blind-hunter №8, verification-gap, дополнительное замечание. Ранее существовавший дефект: `UserLoginSerializer` проверяет пароль неактивного пользователя, `UserLoginView` запрещает только `pending`, затем выдаёт токены. AC6 явно проверяет `ModelBackend.authenticate`, поэтому это не нарушение выбранного критерия стори. Исходная отложенная задача уже есть в `deferred-work.md`; повторное ревью подтверждает её, не создавая второй самостоятельной задачи. [backend/apps/users/serializers.py:538-558; backend/apps/users/views/authentication.py:310-331]

**Проверки повторного ревью:**

- Docker + PostgreSQL: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, `test_responsible_manager_events.py` — **224 passed**, 6 предупреждений о deprecated API Django.
- Детерминированное воспроизведение R42.4-1: временный pytest-плагин в памяти использовал фикстуры `TestClientCard::test_forged_post_changes_only_allowed_fields`; клиент с `manual=False`, перед вызовом настоящего `save_model` строка переназначалась менеджеру B через `QuerySet.update`, POST менял телефон. Ответ 302, телефон сохранён, проверка сохранности `responsible_manager=B` упала: **1 failed** с «Сохранение карточки отменило уже выполненное переназначение клиента». Это моделирование порядка чтение → переназначение → сохранение, не нагрузочный тест двух соединений. Файлы реализации и тестов не менялись.

**Отклонено (16 исходных замечаний; каждое проверено отдельно до группировки):**

- blind-hunter №1 — `low`: при ошибке INSERT аудита разблокировка может сохраниться отдельно, production не использует `ATOMIC_REQUESTS`; редкий сбой без показанного штатного триггера, исправление требует новой транзакционной обвязки. Это не опровергает R42.4-1, где воспроизведена потеря назначения.
- blind-hunter №2 — `low`: две одновременные разблокировки могут записать два события; не два события от одного запроса. Маловероятная коллизия, новая блокировка ради дедупликации не оправдана отдельно.
- blind-hunter №4 — `false`: редактирование `is_active` для `pending` в карточке явно разрешено решениями 7/8 и Dev Notes; реальный вход остаётся запрещён проверкой `pending`.
- blind-hunter №5 — `low`, правка спецификации: буквальный AC2 расходится с явно заданным исключением Task 3; менять реализацию вопреки Task 3 нельзя. Несогласованность выбранного пункта отдельно оставлена R42.4-3.
- blind-hunter №6 — `low`: после переноса ИНН с ведущим пробелом подтверждение действительно может увести на теперь недоступную карточку; узкий ранее описанный сценарий, новая ветка редиректа не оправдана в этом ревью.
- blind-hunter №7 — `false`: ручные назначения в новых фикстурах не оставляют автоматику без проверок: `test_responsible_manager_events.py` проверяет назначение при подтверждении/привязке и сохранность ручного назначения; AC10 нового раздела строится по настоящим правилам. Ошибка редиректа при пробельном ИНН оценена отдельно, а не заменена этим опровержением.
- blind-hunter №9 — `false` как заявленная проблема изоляции инлайнов: переиспользуются штатные CompanyInline/AddressInline, Django привязывает inline formset к родителю; ни обхода этой привязки, ни изменения чужого объекта не показано. Предложение дополнительных тестов само по себе не подтверждает дефект.
- blind-hunter №10 — `false` как заявленный обход права через POST карточки: Django 5.2.7 `_changeform_view` явно проверяет `has_change_permission(request, obj)` и поднимает `PermissionDenied` до обработки формы. У раздела нет переопределения, обходящего проверку; новые тесты проверяют результат той же проверки права.
- edge-case-hunter №1 — `low`: сохранение активности и аудит не объединены транзакцией для действия; тот же редкий сбой INSERT, что в blind-hunter №1, отдельного штатного триггера не показано.
- edge-case-hunter №2 — `low`: два запроса могут создать два события разблокировки; та же редкая коллизия, что в blind-hunter №2, добавление защиты отдельно не оправдано.
- edge-case-hunter №5 — `low`: назначение может смениться после сохранения пароля, до повторного scoped-поиска для аудита; узкое окно, отдельная новая обвязка ради этого сценария не оправдана.
- edge-case-hunter №6 — `low`: перенесённый ИНН с ведущим пробелом может сменить ответственного и дать 404 после подтверждения; то же узкое поведение, что в blind-hunter №6, требует новой ветки.
- edge-case-hunter №7 — `low`: ручная передача заявки до выполнения email-задачи может сделать ссылку региональному получателю недоступной; письмо намеренно региональное, редкий сценарий требует изменения политики получателей, а не прямой коррекции.
- edge-case-hunter №9 — `low`: остаток `time_ns` по модулю 100000 теоретически даёт коллизию двух кодов; в тестах немного таких вызовов, отдельный цикл проверки уникальности ради крайне редкого случая не оправдан.
- acceptance-auditor №1 — `low`, правка спецификации: AC2 буквально строже явно утверждённого исключения Task 3; исправление самого контракта исключено правилами триажа, поведение кода соответствует задаче.
- acceptance-auditor №2 — `low`, правка спецификации: добавление `unblock_users` в ожидание старого теста необходимо по Task 2 и уже объяснено отклонением 2; менять код обратно нельзя, изменение перечня Task 6 — правка спецификации.

#### Ревью актуального состояния 2026-10-13 — `b4fab053..7728a9c8`

Решение Alex 2026-10-14: вариант 2 — оставить R42.4-1, R42.4-2 и R42.4-3 открытыми задачами в истории, без исправлений кода и тестов. Статус истории и запись `42-4-manager-section-own-clients` в трекере спринта остаются `in-progress` до закрытия этих задач.

Режим `full`: 18 файлов в `backend/` и `docker/`, +1689/−18, 1993 строки diff. Изменения ускорения тестов (`backend/freesport/settings/test.py`, `backend/pytest.ini` и файлы вне этих каталогов) исключены. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 6, `verification-gap` — 3 (включая дополнительное), `acceptance-auditor` — 4. Каждое из 23 замечаний классифицировано отдельно до группировки; итог — 0 решений, 3 группы исправлений, 2 группы отложенных вопросов, 11 отклонённых замечаний.

**Исправления — существующие задачи, без дублей:**

- **R42.4-1 остаётся открытой (`high`; ID 3, 11, 20):** проверка принадлежности при чтении не защищает последующую запись. Карточка возвращает устаревшего ответственного после передачи A → B; действие может изменить клиента после выхода из своей выборки. В `User.save()` при неизменных ИНН/стране свежий ответственный не копируется в сохраняемый объект. Нужны блокировка строки до чтения изменяемого объекта и проверка разрешённой выборки в той же транзакции, охватывающей запись. Воспроизведение ниже подтверждает потерю назначения, а не только отсутствие теста. [`backend/apps/users/manager_admin.py:132-133,175-178`; `backend/apps/users/admin.py:1281-1283`; `backend/apps/users/models.py:378-422`]
- **R42.4-2 уточнена (`medium`; ID 7, 17):** статический страж upstream уже есть и прошёл; открытая часть — автоматическая HTTP-проверка маршрута через nginx в существующем шаге проверки production. Не создавать второй тест чтения конфигов. [`backend/tests/unit/test_nginx_security_headers.py:342-365`; `.github/workflows/deploy.yml:457-495`]
- **R42.4-3 остаётся открытой (`low`; ID 4, 22):** `choices()` выделяет «Есть», а `queryset()` показывает `unregistered` при явном фильтре роли. Исправить отображение выбранного значения и закрепить тестом, сохранив утверждённое исключение Task 3. [`backend/apps/users/manager_admin.py:59-83`]

**Отложено:**

- [x] [Review][Defer] **Нет автоматической проверки доступности ссылки регионального письма для получателя** — `medium`; ID 9, 15, 16, 18. Ссылка всегда ведёт в `/manager/`, но существующие правила допускают `manager_email` без `manager` и резервные адреса без доступа. Суперпользователь получает отказ во входе, получатель без назначения — 404; ручная передача также может сделать уже отправленную ссылку недоступной. Решение Alex от 2026-10-13 — очистка правил при выкате, без изменения политики писем; это решение не пересматривается. Отложен пробел автоматической проверки уже существующего конфигурационного предусловия: проверить региональное и резервное правило, связанного сотрудника и доступ по извлечённой из письма ссылке. [`backend/apps/users/tasks.py:421-444`; `backend/apps/users/services/region_routing.py:61-69`; `backend/freesport/admin_site.py:56-66`; `backend/apps/users/manager_admin.py:41`]
- [x] [Review][Defer] **Повторно подтверждён R42.4-D1: успешный HTTP-вход заблокированного клиента** — `medium`; ID 19. Сериализатор принимает пароль неактивного клиента, view проверяет только `pending`, затем выдаёт JWT. Это ранее существовавший дефект, уже записанный в `deferred-work.md`; отдельная задача не создаётся. Тест AC6 корректно проверяет именно `ModelBackend.authenticate`. Последующий доступ по выданному JWT в этом ревью не проверялся. [`backend/apps/users/serializers.py:538-558`; `backend/apps/users/views/authentication.py:310-331`]

**Проверки:**

- Docker + PostgreSQL, один прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, `test_responsible_manager_events.py` — **232 passed**, 6 предупреждений об устаревающих API, 284,50 с. Полный backend-прогон, линтеры и новые мутации в этом ревью не запускались.
- R42.4-1 воспроизведён временным pytest-плагином только в памяти: перед вызовом настоящего `ManagerClientAdmin.save_model` строка переназначалась `other_manager` через `QuerySet.update`. Существующий `TestClientCard::test_forged_post_changes_only_allowed_fields` прошёл свои проверки (включая ответ 302), дополнительная проверка после запроса упала: **1 failed**, `expected responsible_manager=2, actual=1`. Это детерминированная последовательность чтение → передача → сохранение на PostgreSQL, не проверка двумя конкурентными соединениями. Файлы реализации и тестов не менялись.
- Текущая HTTP-проверка dev-стенда: `/manager/` и `/manager/login/` — **502**, поэтому живой приёмочный критерий сейчас не подтверждён. Nginx обращается к текущему IP backend; лог backend содержит `OperationalError: could not translate host name "db" to address`. Dev-БД отсутствует среди работающих контейнеров. Это блокировка стенда, не доказанный дефект рассматриваемого diff; сервисы не перезапускались.
- GitNexus актуален на `7728a9c8`; `detect-changes --scope all` до записи результатов — нет изменений. `--scope compare --base-ref b4fab053` считает весь диапазон, включая исключённое ускорение тестов: 27 файлов, 71 символ, 11 потоков, риск `high`. Отдельные upstream-impact: `scope_clients` — LOW, 1 прямой вызывающий (`get_queryset`); `UserAdmin` — LOW, 2 прямые зависимости (импорт и наследник `ManagerClientAdmin`); `unblock_users` и `send_manager_region_email` — LOW, граф прямых вызывающих не показал. Динамические вызовы Django/Celery этим не исключаются.

##### Отклонено — актуальное ревью (11)

- **ID 1, blind-hunter — `false`:** включение `is_active` у `pending` в карточке разрешено решениями 7–8; это не обход подтверждения: `UserLoginView.post` по-прежнему запрещает вход по `pending`. Утверждение о необходимости единого запрета противоречит выбранному поведению.
- **ID 2, blind-hunter — `low`:** save разблокировки и INSERT AuditLog вне общей транзакции на production реальны (`admin.py:1281-1297`, `AuditLog.log_action` делает обычный INSERT). Редкий сбой записи аудита уже принят предыдущими ревью; отдельная новая транзакционная обвязка ради этого исхода отклонена. Не относится к воспроизведённой потере назначения R42.4-1.
- **ID 5, blind-hunter — `false` как нарушение AC6:** тест проверяет отказ и восстановление `authenticate()` ровно по AC6. Отсутствие HTTP-проверки не делает этот тест неверным; ранее существовавший дефект реального входа отдельно сохранён как ID 19 / R42.4-D1.
- **ID 6, blind-hunter — `low`:** новый набор не проверяет весь парольный вход, `next` и выход; это расширение проверок штатной формы Django, которая здесь не переопределяется. Конкретного сломанного сценария не показано, дополнительная тестовая обвязка отклонена.
- **ID 8, blind-hunter — `false` как отсутствие проверок автоматического назначения:** `test_responsible_manager_events.py:217-259` проверяет пересчёт при привязке и подтверждении по реальным правилам; эти тесты прошли в текущем прогоне. AC10 раздела тоже использует реальные правила. Редкий редирект после переноса пробельного ИНН оценён отдельно (ID 14).
- **ID 10, blind-hunter — `false` как недостаточность проверки AC11:** критерий явно требует равного числа SQL-запросов для 5 и 50 клиентов. Тест выполняет оба замера и проверяет кандидатов у всех 50 строк; он прошёл. Конкретного чрезмерного бюджета или медленного запроса не показано; абсолютный бюджет и нагрузочный тест не следуют из этого AC.
- **ID 12, edge-case-hunter — `low`:** ошибка INSERT после сохранения оставляет разблокировку без аудита; тот же проверенный редкий исход, что ID 2, ранее принят. Новая транзакционная обвязка отдельно ради него не предлагается.
- **ID 13, edge-case-hunter — `false`:** карточка с `is_active=True` для `pending` соответствует решениям 7–8; запрет входа ожидающей заявки сохраняется. Массовое действие намеренно имеет другое сообщение и отбор.
- **ID 14, edge-case-hunter — `low`:** перенос ИНН с пробелом действительно может изменить регион и ответственного, а `_apply_verify_b2b` возвращает прежний `change_url` (`admin.py:728-768`; `link_1c_customer.py:232-235`). Узкий уже принятый сценарий требует новой ветки редиректа; отдельное исправление отклонено.
- **ID 21, acceptance-auditor — `low`, правка спецификации:** буквальный AC2 расходится с Task 3, прямо разрешающим `role__exact=unregistered`; код и тест реализуют Task 3. Исправление текста спецификации исключено из исправлений реализации. Неверно выделенный пункт фильтра отдельно сохранён как R42.4-3.
- **ID 23, acceptance-auditor — `low`, правка спецификации:** изменение ожидания `test_admin_actions_list` неизбежно по Task 2 и объяснено отклонением 2 в Completion Notes. Согласование перечня Task 6/AC12 требует правки спецификации, а не возврата неправильного ожидания теста.

#### Ревью исправлений 2026-10-14 — `b4fab053..220766c3`

Согласованный объём: 19 файлов реализации 42.4, +1871/−18; режим `full`. Исключены отдельное ускорение тестов и документы как содержимое diff; история и предыдущие решения использованы как контекст. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 13, `verification-gap` — 3, `acceptance-auditor` — 3. Каждое из 29 замечаний получило вердикт до группировки. Итог: 0 решений, 5 групп исправлений, 3 отложенных вопроса (два уже зарегистрированы), 9 отклонённых замечаний. Реализация и постоянные тесты в этом ревью не менялись. Решение Alex 2026-10-14: вариант 2 — оставить все пять групп R42.4-4…R42.4-8 открытыми задачами, без исправлений кода и тестов. Статус истории и записи спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления:**

- [x] [Review][Patch] **R42.4-4: второе поле `action` отключает защиту фактически выполняемого действия** — `high`; ID 1, 11, 25, 27. `response_action` пропускает транзакцию и блокировку при наличии `link_1c_customer` в любом значении `action`, тогда как Django выбирает значение по `index`. POST `action=[block_users, link_1c_customer]`, `index=0` выполняет `block_users` без блокировки строки. На PostgreSQL отдельное соединение передало клиента B перед `User.save`: действие A завершилось 200, клиент остался у B, но стал неактивным и получил `block_user` от A. Исключение должно проверять фактически исполняемое действие с той же обработкой `index`, что у Django; добавить регрессию с двумя полями `action`. [backend/apps/users/manager_admin.py:186-196]
- [x] [Review][Patch] **R42.4-5: проверка принадлежности не защищает скрытые поля от устаревшего сохранения карточки** — `high`; ID 3, 15. `save_model` блокирует строку через `exists()`, но затем сохраняет прежний `obj` целиком. Если импорт обновил `onec_id` между чтением формы и блокировкой, а ответственный прежний, проверка проходит и старый объект затирает импорт. Воспроизведено: второе соединение записало `onec_id=REVIEW-IMPORTED-1C-ID`, POST изменил телефон, ответ 302, итоговый `onec_id=None`. Та же последовательность опасна для роли, пароля и других скрытых полей; отдельно они не воспроизводились. Сохранять разрешённые изменения на свежем объекте, прочитанном под блокировкой, либо ограничить запись разрешёнными полями с учётом хука назначения; закрепить сохранность конкурентно обновлённого `onec_id`. [backend/apps/users/manager_admin.py:198-208]
- [x] [Review][Patch] **R42.4-6: смена пароля, подтверждение, отказ и привязка не перепроверяют принадлежность перед записью** — `high`; ID 7, 12, 13, 14, 23. Фильтр применяется до вызова изменяющего пути, но запись не связана с проверкой текущего ответственного под блокировкой. Воспроизведены четыре расписания двумя соединениями: передача A → B перед `AdminPasswordChangeForm.save` закончилась 302, новым паролем и возвратом `responsible_manager=A`; передача перед вызовом каждого из `verify_b2b_application`, `reject_b2b_application`, `link_1c_customer_service` не остановила операцию A и создала соответственно `verify_b2b`, `reject_b2b`, `link_1c_customer` для клиента B. Собственная блокировка сервисов не проверяет manager-scope. Объединить актуальную проверку принадлежности с записью в каждом пути, сохранив порядок блокировки source/target при привязке; добавить конкурентные регрессии. Ранее эти окна были отклонены как маловероятные; теперь последствия воспроизведены, включая потерю назначения через пароль, поэтому прежний вердикт не применяется. [backend/apps/users/admin.py:523-544,589-632,728-777,1108-1116; backend/apps/users/manager_admin.py:193-194]
- [x] [Review][Patch] **R42.4-7: ссылка пункта «Есть» снова выбирает «Все» при фильтре роли `unregistered`** — `low`; ID 4, 18. `choices()` удаляет только `portal_account`, сохраняя `role__exact=unregistered`; следующий запрос получает `effective_value() == all`. Воспроизведён настоящий переход по ссылке: `?role__exact=unregistered`, выбранные пункты — `Есть=False`, `Нет=False`, `Все=True`. Исправить ссылку или явно кодировать выбор «Есть», не отменяя утверждённое исключение Task 3; тест должен переходить по ссылке, а не только проверять исходное выделение. Это обычное действие интерфейса, поэтому замечание сохраняется несмотря на `low`. [backend/apps/users/manager_admin.py:63-94]
- [x] [Review][Patch] **R42.4-8: новые HTTP-проверки раздела не имеют таймаута запроса** — `low`; ID 10, 22. Оба новых вызова `curl` не ограничивают время соединения и ответа. При остановившем передачу upstream проверка ждёт вплоть до общего `timeout-minutes: 30` задания. Добавить `--connect-timeout` и `--max-time` к обоим вызовам; это прямая коррекция параметров без нового поведения приложения. Зависание в этом ревью не моделировалось. [.github/workflows/deploy.yml:508-515]

**Отложено:**

- [x] [Review][Defer] **Повторно подтверждён долг доступности ссылки регионального письма** — `medium`; ID 19, 24. Проверка адресата и строки URL не доказывает доступ адресата к конкретной заявке. Решение Alex о ручной очистке правил перед выкатом сохранено; пробел автоматической проверки уже зарегистрирован в начале `deferred-work.md`, второй самостоятельной задачи не создавать. [backend/apps/users/tasks.py:442-446]
- [x] [Review][Defer] **Повторно подтверждён R42.4-D1: успешный HTTP-вход заблокированного клиента** — `medium`; ID 6, 26. Сериализатор достаёт неактивного пользователя напрямую, view запрещает только `pending`, затем создаёт JWT. Это pre-existing; AC6 корректно проверяет `ModelBackend.authenticate`. В этом ревью подтверждено чтением кода, HTTP-вход отдельно не воспроизводился; исходная задача остаётся единственной. [backend/apps/users/serializers.py:537-558; backend/apps/users/views/authentication.py:310-331]
- [x] [Review][Defer] **Предварительные `exists()` не сохраняют порядок блокировки массового действия** — `maybe-false`, возможный `medium`, **не подтверждено**; ID 16. Runtime-исходник установленного Django подтверждает `Query.exists(): clear_ordering(force=True); LIMIT 1`, а действия вызывают `exists()` до итерации отсортированного queryset. Таким образом, комментарий о порядке pk не гарантирует порядок самой первой блокировки. Конкретное взаимное ожидание двух запросов не воспроизведено, поэтому дефект deadlock не заявляется подтверждённым. Для решения нужен тест двух пересекающихся действий с зафиксированным порядком первых блокировок и фактическим циклом ожидания PostgreSQL; это отдельный вопрос от ранее отложенного source/target-порядка сервисов. [backend/apps/users/manager_admin.py:195-196; backend/apps/users/admin.py:931-940,1196-1207,1251-1261]

**Проверки:**

- Docker + PostgreSQL, один последовательный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, `test_responsible_manager_events.py`, `--override-ini=addopts= -q -p no:sugar` — **239 passed**, 6 предупреждений об устаревающих API, 322,45 с. Полный backend-прогон, линтеры и новые мутации не выполнялись.
- Дополнительные проверки запускались временными pytest-плагинами **в памяти**, без правок файлов тестов или реализации, с `ATOMIC_REQUESTS=False` и отдельным соединением в потоке для конкурентной записи. Первый прогон — **3 failed**: пароль отменил передачу, карточка затёрла импортированный `onec_id`, два поля `action` оставили строку без блокировки. Второй — **2 failed**: переход по ссылке «Есть» снова выделил «Все», действие A заблокировало уже переданного B клиента и записало аудит. Третий окончательный прогон — **3 failed**: подтверждение, отказ и привязка выполнились от прежнего менеджера после передачи.
- В первом запуске сервисных проверок слишком широкий `-k test_link_action` также выбрал чужой тест и вызвал `KeyError` в временном плагине: эта ошибка не считается дефектом приложения. Повтор с тремя точными nodeid дал три ожидаемых падения проверок принадлежности, без ошибки плагина.
- Эти расписания детерминированно размещают конкурентную запись между чтением и записью настоящего обработчика; это не нагрузочный стресс-тест. Существующие утверждения трёх сервисных тестов выполнились, дополнительные утверждения об отсутствии действий прежнего менеджера упали.
- Живой dev-nginx: `http://localhost/manager/` — **302**, `Location: /manager/login/?next=/manager/`; `/manager/login/` — **200**. Production не проверялся, сервисы не перезапускались.
- GitNexus актуален на `220766c3`; `detect-changes --scope all` перед записью отчёта — нет изменений. `--scope compare --base-ref b4fab053` для всего диапазона (включая исключённые файлы) — 28 файлов, 74 символа, 11 процессов, риск `high`. Upstream-impact: `ManagerClientAdmin` — LOW, 1 импорт; `UserAdmin` — LOW, 2 прямые зависимости; `scope_clients` — LOW, прямой `get_queryset` и далее `save_model`/`response_change`; `unblock_users` — LOW, прямых вызовов граф не показал. Динамические вызовы Django/Celery этим не исключаются.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | high | Два `action` обошли строковую блокировку; переданный B клиент заблокирован A. R42.4-4. |
| 2 | blind-hunter №2 | false | Правка `is_active` у pending прямо разрешена решениями 7–8; вход pending остаётся запрещён. |
| 3 | blind-hunter №3 | high | Конкурентный `onec_id` затёрт полным сохранением карточки, ответ 302. R42.4-5. |
| 4 | blind-hunter №4 | low | Настоящий переход по «Есть» снова выделил «Все». Прямое исправление R42.4-7. |
| 5 | blind-hunter №5 | low | POST-матрицы штатного login нет, но сломанный сценарий формы не показан; расширение тестов не является коррекцией доказанного дефекта. |
| 6 | blind-hunter №6 | medium | Реальный API обходит ModelBackend и не проверяет активность; это уже зарегистрированный R42.4-D1, не нарушение выбранного AC6. |
| 7 | blind-hunter №7 | high | Четыре непроверенных пути воспроизведены: пароль, подтверждение, отказ, привязка после передачи. R42.4-6. |
| 8 | blind-hunter №8 | low | `DatabaseError` действительно шире конфликта NOWAIT, но ложноположительный зелёный прогон не показан; исправление вводит обработку редкого нового состояния. |
| 9 | blind-hunter №9 | low | В `/admin/` save и аудит не атомарны; это тот же ранее принятый редкий сбой INSERT, нужна новая транзакционная обвязка. |
| 10 | blind-hunter №10 | low | У новых curl нет временных ограничений; прямое добавление параметров R42.4-8. |
| 11 | edge-case-hunter №1 | high | Выбранный по index `block_users` выполняется без защиты из-за другого поля action. R42.4-4. |
| 12 | edge-case-hunter №2 | high | Настоящая привязка после передачи создала `link_1c_customer` от A для клиента B. R42.4-6. |
| 13 | edge-case-hunter №3 | high | Настоящие подтверждение и отказ после передачи создали аудит от A для клиента B. R42.4-6. |
| 14 | edge-case-hunter №4 | high | Смена пароля после передачи вернула A и изменила пароль. R42.4-6. |
| 15 | edge-case-hunter №5 | high | Импортированный другим соединением `onec_id` потерян при полном save. R42.4-5. |
| 16 | edge-case-hunter №6 | maybe-false | Снятие ORDER BY в exists подтверждено runtime-исходником; цикл ожидания не показан, отдельная проверка отложена. |
| 17 | edge-case-hunter №7 | low | Редирект после переноса пробельного ИНН может дать 404; этот редкий исход уже принят, новая условная ветка отклонена. |
| 18 | edge-case-hunter №8 | low | Ссылка «Есть» сохраняет конфликтующую роль и снова выбирает all. R42.4-7. |
| 19 | edge-case-hunter №9 | medium | Несовместимый адресат регионального письма не откроет заявку; существующий конфигурационный долг, ручной план сохранён. |
| 20 | edge-case-hunter №10 | low | Сбой INSERT в `/admin/` может оставить разблокировку без аудита; тот же ранее принятый редкий исход, что ID 9. |
| 21 | edge-case-hunter №11 | low | Любой DatabaseError принимается за NOWAIT-конфликт; конкретный ложноположительный исход не воспроизведён, как ID 8. |
| 22 | edge-case-hunter №12 | low | curl может ждать до тайм-аута задания; прямая коррекция R42.4-8. |
| 23 | edge-case-hunter №13 | high | Заявленное закрытие гонки не охватывает воспроизведённые парольный и сервисные пути; результат кода, не предложение менять сообщение коммита. R42.4-6. |
| 24 | verification-gap №1 | medium | Проверки адреса и URL не открывают заявку от имени получателя; уже зарегистрированный пробел проверки конфигурационного предусловия. |
| 25 | verification-gap №2 | high | Тест отправляет только одно action; вариант с двумя воспроизвёл изменение уже чужого клиента. R42.4-4. |
| 26 | verification-gap №3 | medium | Отсутствие проверки активного состояния API подтверждено сериализатором/view; R42.4-D1 существовал до стори, AC6 корректен. |
| 27 | acceptance-auditor №1 | high | Обход защиты двумя action нарушает manager-scope на записи; воспроизведён. R42.4-4. |
| 28 | acceptance-auditor №2 | low | Буквальный AC2 конфликтует с исключением Task 3; код реализует утверждённую задачу, исправление касается спецификации. |
| 29 | acceptance-auditor №3 | low | Task 2 требует unblock_users, поэтому точный expected_actions надо изменить; отклонение уже записано, исправление касается спецификации. |

##### Отклонено — ревью исправлений (9)

- ID 2 — `false`: активация pending в карточке предусмотрена решениями 7–8 и не снимает запрет входа по pending; новая общая проверка изменила бы утверждённое поведение.
- ID 5 — `low`: не показан дефект непереопределённой формы входа Django; дополнительная POST-матрица расширяет проверки штатного механизма без конкретного сломанного сценария.
- ID 8 — `low`: слишком широкий except реален, но не показано ошибочно зелёного теста; усложнение обработки редкого SQL/connection-сбоя не оправдано этим результатом.
- ID 9 — `low`: отдельные save и AuditLog в `/admin/` оставляют уже принятый редкий риск сбоя INSERT; новая атомарная обвязка ради этого исхода отклонена.
- ID 17 — `low`: редирект при переносе пробельного ИНН — ранее принятый редкий исход; отдельная новая ветка не является прямой коррекцией обычного пути.
- ID 20 — `low`: тот же редкий неатомарный save/аудит в `/admin/`, что ID 9, проверен отдельно и ранее принят.
- ID 21 — `low`: тот же широкий DatabaseError, что ID 8; конкретный ложноположительный исход отсутствует, новая обработка редкого состояния отклонена.
- ID 28 — `low`, правка спецификации: Task 3 прямо задаёт исключение unregistered; менять корректную реализацию вопреки задаче нельзя.
- ID 29 — `low`, правка спецификации: новое действие требует нового точного ожидания; отклонение 2 уже объясняет изменение, возврат старого теста был бы неверным.

#### Ревью 2026-10-14 — `b4fab053..63cd2959`

Согласованный объём: 19 файлов реализации, +2153/−18, 2468 строк diff; режим `full`. Отдельное ускорение тестов и документы исключены из diff реализации. Контекст — эта стори, `project-context.md` и правила проекта. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 8, `verification-gap` — 3, `acceptance-auditor` — 2. Каждое из 23 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 1 исправление, 4 отложенные группы (повторы существующего долга, без новых самостоятельных задач), 14 отклонено. Реализация и постоянные тесты не менялись. PR #307 уже слит в `develop`; проверенный HEAD — `63cd2959`. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-9 открытой задачей, без исправления кода и тестов. Статус стори и записи спринта: `review` → `in-progress` до закрытия задачи.

**Исправление:**

- [x] [Review][Patch] **R42.4-9: чужая строка блокируется до проверки доступа** — `medium`, ID 4. POST карточки, пароля и подтверждения вызывает `_lock_rows` через общий `User.objects` до scoped-чтения и проверки права изменения. Воспроизведены три настоящих POST на клиента другого менеджера: все ответили 404, но перед этим держали строковую блокировку чужой записи, что подтвердило второе соединение (`FOR UPDATE NOWAIT`, SQLSTATE `55P03`). При уже занятой чужой строке такой запрещённый запрос ждёт её освобождения вместо отказа; граница изоляции не должна вовлекать чужую запись в блокировки. До захвата проверить доступ к изменяющему пути и ограничить цель разрешённой клиентской выборкой; после захвата сохранить актуальную scoped-проверку, защищающую от переназначения. Не ограничивать тем же правилом источник 1С: он может законно находиться вне клиентской выборки. Добавить негативную конкурентную проверку чужой строки и права `view_user`, не ослабляя существующие проверки передачи и импорта. [backend/apps/users/manager_admin.py:203-214,235-262]

**Отложено — повторы существующих задач:**

- [x] [Review][Defer] **Разный порядок source/target при подтверждении и привязке** — `medium`, ID 5, 14; deferred, pre-existing. Подтверждение держит target и далее запрашивает source, а привязка при `source.pk < target.pk` захватывает source перед target. Возможное расписание: подтверждение держит target, действие привязки держит source и ждёт target, подтверждение ждёт source. Эта причина существовала в общих сервисах до 42.4 и уже записана как долг подтверждения/пересчёта. Дополнительный участник — действие привязки — не создаёт отдельной задачи. Конкурентное воспроизведение deadlock в этом запуске не выполнялось; нужна проверка двух запросов и единый порядок захвата в общей задаче. [backend/apps/users/manager_admin.py:256-277; backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153]
- [x] [Review][Defer] **Первая блокировка массового действия через `exists()` не гарантирует порядок pk** — `maybe-false`, возможный `medium`, ID 13; deferred, повтор существующего неподтверждённого вопроса. Runtime-исходник установленного Django повторно подтвердил `clear_ordering(force=True)` и `LIMIT 1` в `Query.exists()`. Действия вызывают `exists()` до итерации, но фактический цикл ожидания не показан. Для подтверждения нужны две транзакции с наблюдаемыми первыми блокировками и deadlock; не смешивать с source/target-порядком сервисов. [backend/apps/users/manager_admin.py:279-289; backend/apps/users/admin.py:1196-1207,1251-1261]
- [x] [Review][Defer] **Региональное письмо: доступ адресата и полный URL не проверены сквозным тестом** — `medium`, ID 9, 16, 19, 20; deferred, повтор существующего конфигурационного долга. Проверки подстроки URL пропустят добавленный неверный суффикс, а независимо построенный `verify_url()` не проверяет письмо. Несвязанный адрес, суперпользователь или второй резервный получатель не обязательно имеют доступ к конкретной заявке. Решение Alex о ручной очистке правил перед выкатом сохранено; ранее зарегистрированная задача уже требует открытия извлечённого URL от имени получателя. Новую самостоятельную задачу не создавать. [backend/apps/users/tasks.py:421-454; backend/tests/unit/test_region_routing.py:153-179]
- [x] [Review][Defer] **R42.4-D1: HTTP-вход неактивного клиента** — `medium`, ID 8; deferred, pre-existing. Сериализатор проверяет пароль неактивного пользователя напрямую; view запрещает `pending`, но до JWT не проверяет активность. AC6 намеренно проверяет `ModelBackend.authenticate`, поэтому это не нарушение выбранного AC6. Исходная задача остаётся единственной; HTTP-вход в этом запуске отдельно не воспроизводился. [backend/apps/users/serializers.py:537-558; backend/apps/users/views/authentication.py:310-331]

**Проверки:**

- GitNexus: индекс свежий, HEAD и индекс `63cd2959`; `detect-changes --scope all` — нет изменений. Для полного диапазона `--scope compare --base-ref b4fab053` — 28 файлов, 86 символов, 12 потоков, общий риск high; этот результат включает исключённые файлы. `impact UserAdmin` — LOW, 2 прямые зависимости; `ManagerClientAdmin` — LOW, 1 импорт; `_lock_rows` — HIGH, 4 прямых вызывающих (карточка, пароль, подтверждение, привязка). Предупреждение передано пользователю; код не правился. `impact row_is_locked` символ не нашёл даже на свежем индексе, поэтому вывод о зависимостях тестового helper по графу не сделан.
- Docker + PostgreSQL, один последовательный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, `test_responsible_manager_events.py`, `--override-ini=addopts= -q -p no:sugar`: **247 постоянных тестов прошли**. Дополнительно внедрённая в память проверка не запустилась из-за привязки pytest-функции к классу вместо модуля (`TypeError`, пропущен аргумент фикстуры). Эта ошибка диагностической обвязки не считается дефектом приложения.
- После коррекции плагина отдельный прогон одного существующего теста и временной проверки — **2 passed**, 23,26 с. Проверка с `ATOMIC_REQUESTS=False` показала блокировку чужой строки перед 404 во всех трёх POST-путях. Второе соединение проверяло именно `55P03`, без `row_is_locked`. Плагин существовал только в памяти; новых тестовых файлов не создавалось.
- Отдельная runtime-проверка в Docker: подмена проверочного SQL-вызова на посторонний `DatabaseError` приводит к `row_is_locked(1) == True`. Широкий перехват подтверждён, но обычный ложноположительный зелёный прогон из-за такого сбоя не показан; индивидуальный вердикт low, отклонён по критерию редкого исхода и дополнительной ветки обработки.
- Полный backend-набор, линтеры, мутационные проверки и production в этом запуске не проверялись.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | Активация pending через карточку разрешена решениями 7–8; статус pending и запрет входа сохраняются. |
| 2 | blind-hunter №2 | low | В `/admin/` save предшествует аудиту без общей транзакции; ранее принятый редкий сбой INSERT, нужна новая обвязка. |
| 3 | blind-hunter №3 | low | В `/admin/` признаки сотрудника/pending могут измениться после чтения кандидатов; редкая гонка, устранение требует новой блокировки и перепроверки. |
| 4 | blind-hunter №4 | medium | Три запрещённых POST держат чужую строку перед 404, подтверждено вторым соединением с 55P03. R42.4-9. |
| 5 | blind-hunter №5 | medium | Target-first подтверждения и source-first привязки допускают цикл ожидания; общий порядок сервисов существовал до 42.4, отдельный runtime-deadlock не запускался. |
| 6 | blind-hunter №6 | low | Ручной флаг фабрики намеренный; автоматическое назначение проверяют тесты 42.2. Редкий редирект после ухода клиента уже принят. |
| 7 | blind-hunter №7 | low | Штатная форма принимает staff, но has_permission не даёт доступ к разделу и штатная страница объясняет отказ; отдельная проверка группы в форме изменит утверждённый механизм. |
| 8 | blind-hunter №8 | medium | HTTP-вход обходит ModelBackend и не проверяет активность до JWT; существующий R42.4-D1. |
| 9 | blind-hunter №9 | medium | Ссылка письма не гарантирует доступ каждого адресата; существующее предусловие и сквозной тест уже отложены. |
| 10 | blind-hunter №10 | low | Посторонний DatabaseError воспроизведён как True; это редкий ложный индикатор, дополнительная ветка обработки не исправляет показанный повседневный прогон. |
| 11 | edge-case-hunter №1 | low | Неатомарность save/аудита в `/admin/` реальна, но редкий сбой уже принят; новая транзакционная защита. |
| 12 | edge-case-hunter №2 | low | Устаревшие условия разблокировки в `/admin/` возможны при конкурентном изменении; новая строковая блокировка ради редкого исхода. |
| 13 | edge-case-hunter №3 | maybe-false | exists снимает сортировку, подтверждено runtime-исходником; конкретное взаимное ожидание не воспроизведено, существующий отложенный вопрос. |
| 14 | edge-case-hunter №4 | medium | Два пути могут держать разные первые строки и ждать друг друга; тот же существующий source/target-долг, что ID 5. |
| 15 | edge-case-hunter №5 | low | Подтверждение после переназначения возвращает старый change_url; редкий исход уже принят, отдельная условная ветка отклонена. |
| 16 | edge-case-hunter №6 | medium | Несколько резервных адресатов не означают нескольких ответственных; существующий конфигурационный долг письма. |
| 17 | edge-case-hunter №7 | low | source_code прочитан до блокировки и может устареть для предупреждения; перенос в сервисе читает свежую строку. Редкая косметическая гонка требует нового перечитывания. |
| 18 | edge-case-hunter №8 | low | Любой DatabaseError трактуется как блокировка, подтверждено; тот же редкий диагностический исход, что ID 10. |
| 19 | verification-gap №1 | medium | Проверка подстроки не обнаружит неверный суффикс полного URL; ранее зарегистрированный долг уже требует перехода по извлечённой ссылке. |
| 20 | verification-gap №2 | medium | Состав резервных адресатов шире manager-scope; решение о ручной очистке сохранено, повтор существующего долга. |
| 21 | verification-gap №3 | low | В `/admin/` возможен save без аудита при сбое INSERT; тот же ранее принятый редкий риск. |
| 22 | acceptance-auditor №1 | low | Буквальный AC2 конфликтует с исключением Task 3; код реализует Task 3, исправление касается спецификации. |
| 23 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового expected_actions; отклонение 2 уже объясняет изменение, исправление касается спецификации. |

##### Отклонено — ревью на `63cd2959` (14)

- ID 1 — false: разрешённая активация pending не подтверждает заявку и не снимает запрет входа по pending.
- ID 2 — low: редкий сбой аудита в `/admin/` уже принят; новая транзакционная обвязка не предлагается.
- ID 3 — low: редкая гонка признаков клиента в `/admin/`; новая блокировка и повторная проверка не являются прямой коррекцией обычного пути.
- ID 6 — low: автоматическое назначение проверяют смежные сервисные тесты; фабрика намеренно изолирует проверки раздела, а редкий недоступный редирект уже принят.
- ID 7 — low: успешная аутентификация staff не означает доступа к разделу; штатный отказ сайта и пояснение сохраняются, новая политика формы не требуется.
- ID 10 — low: широкий перехват подтверждён, но посторонний SQL-сбой — редкое состояние; новая ветка распознавания исключений не оправдана обычным сломанным прогоном.
- ID 11 — low: редкая неатомарность аудита в `/admin/`, как ID 2; новая защита ранее отклонена.
- ID 12 — low: редкая конкурентная смена признаков в `/admin/`, как ID 3; новая блокировка ранее отклонена.
- ID 15 — low: редирект после ухода по правилу региона — ранее принятый редкий исход; нужна новая условная ветка.
- ID 17 — low: устаревший source_code влияет только на предупреждение при конкурентной смене кода; данные переноса читаются под блокировкой, новое перечитывание ради редкого исхода отклонено.
- ID 18 — low: тот же редкий ложный индикатор DatabaseError, что ID 10; новая обработка исключений отклонена.
- ID 21 — low: тот же редкий сбой save/аудита в `/admin/`, что ID 2 и 11; ранее принятый риск.
- ID 22 — low, правка спецификации: исключение роли прямо задано Task 3; менять корректный код вопреки задаче нельзя.
- ID 23 — low, правка спецификации: добавление действия требует корректировки точного ожидаемого списка; отклонение уже документировано.

#### Ревью 2026-10-14 — `b4fab053..ac631c09`

Согласованный объём: 19 файлов реализации story 42.4, +2269/−18; режим `full`. Ускорение тестов и документационные изменения исключены из проверяемого diff. Контекст: эта story, `project-context.md`, `AGENTS.md` и `backend/AGENTS.md`. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 7, `verification-gap` — 4 (два пробела проверки и два дополнительных замечания), `acceptance-auditor` — 2. Каждое из 23 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 4 группы исправлений (2 воспроизведённых дефекта и 2 пробела регрессии), 2 отложенные группы (повторы существующего долга), 13 отклонённых замечаний. Реализация и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-10…R42.4-13 открытыми задачами, без исправлений кода и тестов. Статус story и записи спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления:**

- [x] [Review][Patch] **R42.4-10: пустая scoped-блокировка допускает последующее чтение клиента без блокировки** — `high`, ID 11 и 17 (`edge-case-hunter`). `_lock_client` выполняет scoped `SELECT FOR UPDATE`, но игнорирует пустой результат и продолжает вью. Если после этого клиента назначили текущему менеджеру, повторный `get_object` видит его, хотя строка не была заблокирована. Воспроизведено на PostgreSQL двумя соединениями: при блокировке клиент ещё чужой (`initial_scope_count=0`), после неё передан менеджеру запроса; во время обработки формы второе соединение записало `onec_id` без ожидания. Карточка ответила 302, телефон сохранён, импортированный `onec_id` затёрт в `None`. Пустой результат должен завершать изменяющий путь отказом, а не разрешать позднее чтение без блокировки; сохранить 403 при отсутствии права change и 404 без блокировки чужой строки. Добавить регрессию появления клиента в scope между попыткой блокировки и чтением. Подтверждён дефект карточки; общий helper также используется паролем и подтверждением, но эти два исхода отдельно не воспроизводились. [backend/apps/users/manager_admin.py:217-231,252-279]
- [x] [Review][Patch] **R42.4-11: привязка к 1С ждёт блокировку уже переданного чужого клиента до проверки принадлежности** — `medium`, ID 4 (`blind-hunter`). `_apply_link_1c_customer` вызывает `_lock_rows(target.pk, ...)` через общий `User.objects`, а scope проверяет лишь после захвата. Воспроизведён настоящий HTTP POST: после чтения заявки второе соединение передало её другому менеджеру, затем удержало её строку. Запрос привязки вместо 404 дождался диагностического `lock_timeout=2s` и завершился `OperationalError`, SQLSTATE `55P03`. Данные клиента и аудит не изменились, но недоступная цель вовлекается в ожидание блокировок, которое R42.4-9 убрал для остальных путей. Отсечь уже чужую цель до общей блокировки; сохранить повторную scoped-проверку после захвата и совместный порядок source/target по pk. Источник 1С может законно находиться вне клиентской выборки, его этим фильтром не ограничивать. Добавить негативный двухсоединительный тест привязки после передачи при занятой строке цели. [backend/apps/users/manager_admin.py:281-294]
- [x] [Review][Patch] **R42.4-12: порядок source/target при привязке раздела не защищён конкурентным тестом** — `medium`, ID 18 (`verification-gap`, пробел регрессии). Текущая совместная блокировка по pk корректна, но тесты `test_link_action` и `test_link_after_transfer_answers_404` не обнаружат её замены предварительной блокировкой одной цели: источник в успешном тесте создаётся позже заявки, а конкурирующей транзакции нет. Добавить HTTP-проверку с `source.pk < target.pk` и вторым соединением, захватывающим обе строки по возрастанию pk; проверить завершение обеих операций и сохранённые результаты. Это страж корректного порядка нового wrapper, а не утверждение о воспроизведённом deadlock текущей реализации и не дубль долга общего сервиса подтверждения. Доказательства слоя verification-gap приняты по правилам workflow; новая мутация в этом запуске не выполнялась. [backend/apps/users/manager_admin.py:211-215,281-294; backend/tests/integration/test_manager_clients_section.py:815-823,1271-1296]
- [x] [Review][Patch] **R42.4-13: локальный маршрут `/manager/` не имеет автоматической HTTP-проверки через nginx** — `medium`, ID 19 (`verification-gap`, пробел проверки). Статический тест сравнивает `proxy_pass`, Django client обходит nginx, а новый smoke test деплоя обращается к production с другим конфигом. Добавление ошибочного `rewrite` в `local.conf` оставит эти автоматические проверки зелёными, но сломает маршрут разработчика. Закрепить Docker HTTP smoke test локального nginx: 302, точный `Location: /manager/login/?next=/manager/`, затем 200 и форма входа Django. Ручные замеры этого запуска успешны, дефект текущего маршрута не заявляется. Доказательства слоя verification-gap приняты по правилам workflow; конфиги для мутации в этом запуске не менялись. [docker/nginx/conf.d/local.conf:83; backend/tests/unit/test_nginx_security_headers.py:352-365; .github/workflows/deploy.yml:508-519]

**Отложено — повторы существующего долга:**

- [x] [Review][Defer] **Разный порядок source/target у подтверждения и привязки** — `medium`, ID 5 и 14. Общий сервис подтверждения сначала блокирует target, затем вызывает сервис привязки, который захватывает source/target по pk. При source.pk < target.pk это допускает цикл с отдельной привязкой, держащей source и ожидающей target. Порядок существовал до 42.4; исходная задача в `deferred-work.md` остаётся единственной. Для закрытия нужен двухсоединительный тест фактического цикла и единый порядок общих сервисов. Deadlock в этом запуске не воспроизводился. [backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153; backend/apps/users/manager_admin.py:273-294]
- [x] [Review][Defer] **Региональное письмо не гарантирует доступ адресата к заявке** — `medium`, ID 8, 15 и 21. `resolve_manager_recipients` допускает `manager_email` без связанной учётной записи, а scope требует фактического ответственного; суперпользователя раздел не пускает. Тест текста URL не подтверждает доступ получателя. Решение Alex о ручной очистке правил на выкате сохранено, существующая задача сквозной проверки ссылки остаётся единственной. В этом запуске письмо от имени получателя не открывалось. [backend/apps/users/tasks.py:421-454; backend/apps/users/services/region_routing.py:61-69; backend/freesport/admin_site.py:56-66]

**Проверки:**

- GitNexus актуален: индекс и HEAD `ac631c09`; до записи отчёта `detect-changes --scope all` — нет изменений. Полный диапазон `--scope compare --base-ref b4fab053`: 28 файлов, 88 символов, 15 процессов, риск high; этот результат включает исключённые файлы. `impact _lock_client --direction upstream` — HIGH, 3 прямых вызывающих (`change_view`, `user_change_password`, `verify_b2b_view`); `_lock_rows` — LOW, 1 вызывающий (`_apply_link_1c_customer`); `UserAdmin` — LOW, 2 прямые зависимости (импорт и наследник). Предупреждение передано Alex, код не правился.
- Docker + PostgreSQL, последовательный профильный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, `test_responsible_manager_events.py`, `--override-ini=addopts= -q -p no:sugar` — **255 passed**, 6 предупреждений об устаревающих API, 375,98 с.
- Отдельный pytest-плагин только в памяти, `ATOMIC_REQUESTS=False`: контрольный `test_card_save_holds_row_lock` прошёл, две дополнительные проверки безопасного поведения упали — **2 failed, 1 passed**, 31,96 с. R42.4-10: `initial_scope_count=0`, импорт не ждал блокировку, POST 302, `onec_id=None` вместо импортированного значения. R42.4-11: чужую цель держало второе соединение, HTTP POST получил SQLSTATE `55P03` вместо 404. Порядок событий фиксировался подменой границ вызовов без изменения их штатной реализации; записи и блокировки выполнялись настоящими соединениями PostgreSQL. Постоянных тестовых файлов не создавалось.
- Живой dev-nginx: `/manager/` — **302**, `Location: /manager/login/?next=/manager/`; `/manager/login/` — **200**. Сервисы не перезапускались. Production, полный backend-набор, линтеры и новые мутации в этом запуске не проверялись.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | Активация pending через карточку прямо разрешена решениями 7–8; запрет входа по pending сохраняется. |
| 2 | blind-hunter №2 | low | Save и INSERT аудита в `/admin/` не атомарны; ранее принятый редкий сбой, новая транзакционная обвязка отклонена. |
| 3 | blind-hunter №3 | low | В `/admin/` eligibility может смениться после чтения; ранее рассмотренная редкая гонка, новая блокировка отклонена. |
| 4 | blind-hunter №4 | medium | Привязка ждала строку переданного клиента и получила 55P03 вместо 404; R42.4-11. |
| 5 | blind-hunter №5 | medium | Target-first подтверждения и pk-order привязки допускают цикл; существующий долг общих сервисов. |
| 6 | blind-hunter №6 | false | AC6 явно требует ModelBackend.authenticate; HTTP-вход — отдельный существующий R42.4-D1, не ошибка выбранного теста. |
| 7 | blind-hunter №7 | low | Дополнительной POST-матрицы штатной формы нет, но конкретного сломанного входа не показано; новая тестовая обвязка отклонена. |
| 8 | blind-hunter №8 | medium | Адресат письма не обязательно имеет manager-scope; существующий конфигурационный долг. |
| 9 | blind-hunter №9 | low | Пересчёт по обычным правилам покрыт тестами 42.2; 404 после переноса пробельного ИНН — ранее принятый редкий исход, новая ветка редиректа отклонена. |
| 10 | blind-hunter №10 | false | Раздел нужен на основном HTTPS-vhost и local; внутренний Host nginx намеренно обслуживает только media/static, остальные vhost перенаправляют либо возвращают 410. Требование маршрута в каждом server-блоке не следует из контракта. |
| 11 | edge-case-hunter №1 | high | Пустая scoped-блокировка, последующее назначение и полный save реально затёрли конкурентный импорт; R42.4-10. |
| 12 | edge-case-hunter №2 | low | Неатомарный save/аудит в `/admin/` оставляет ранее принятый редкий сбой; новая обвязка отклонена. |
| 13 | edge-case-hunter №3 | low | Признаки сотрудника/суперпользователя могут смениться после отбора в `/admin/`; редкая гонка, новая блокировка отклонена. |
| 14 | edge-case-hunter №4 | medium | Тот же существующий source/target-долг; фактический runtime-deadlock в этом запуске не проверялся. |
| 15 | edge-case-hunter №5 | medium | Резервный либо несвязанный получатель может не открыть заявку; существующий долг письма. |
| 16 | edge-case-hunter №6 | low | Подтверждение возвращает прежний change_url после редкого ухода по пробельному ИНН; ранее принятая новая условная ветка отклонена. |
| 17 | edge-case-hunter №7 | high | Заявленная блокировка до чтения не соблюдается при появлении клиента в scope; тот же воспроизведённый дефект R42.4-10, а не правка текста коммита. |
| 18 | verification-gap №1 | medium | Корректный порядок нового wrapper не защищён тестом при более старом источнике и конкурентной записи; R42.4-12. |
| 19 | verification-gap №2 | medium | Статический proxy_pass и production smoke не ловят неверный local rewrite; R42.4-13. |
| 20 | verification-gap, дополнительное №1 | low | Save/аудит в `/admin/` не атомарны; ранее принятый редкий сбой INSERT, новая обвязка отклонена. |
| 21 | verification-gap, дополнительное №2 | medium | Региональные адресаты могут быть без доступа к разделу; существующая задача сквозной проверки письма. |
| 22 | acceptance-auditor №1 | low | Буквальный AC2 конфликтует с явно заданным исключением Task 3; исправление касается спецификации и исключено из patch. |
| 23 | acceptance-auditor №2 | low | Task 2 требует unblock_users и изменения expected_actions; отклонение 2 это фиксирует, согласование Task 6/AC12 — правка спецификации. |

##### Отклонено — ревью на `ac631c09` (13)

- ID 1 — false: разрешённая активация pending не подтверждает заявку и не снимает запрет входа.
- ID 2 — low: редкий сбой аудита в `/admin/` уже принят, новая транзакционная обвязка не предлагается.
- ID 3 — low: ранее рассмотренная редкая гонка eligibility в `/admin/`; новая блокировка и перепроверка не являются прямой коррекцией обычного пути.
- ID 6 — false: тест соответствует явному AC6; существующий HTTP-дефект R42.4-D1 не делает ModelBackend-проверку ошибочной.
- ID 7 — low: конкретного сломанного штатного login не показано; дополнительная матрица требует новой тестовой обвязки без доказанного регрессионного сценария.
- ID 9 — low: автоматическое назначение покрыто смежными тестами, которые прошли; редкий недоступный редирект уже принят и требует новой ветки.
- ID 10 — false: внутренний vhost не обслуживает клиентский раздел по назначению; нужные основной и локальный маршруты существуют и закреплены отдельно.
- ID 12 — low: ранее принятый редкий сбой INSERT аудита; новая атомарная обвязка отклонена.
- ID 13 — low: ранее рассмотренная редкая конкурентная смена признаков в `/admin/`; новая блокировка отклонена.
- ID 16 — low: недоступный редирект после редкого ухода по правилу региона уже принят; отдельная новая ветка отклонена.
- ID 20 — low: тот же ранее принятый редкий сбой save/аудита, индивидуально проверен; новая обвязка отклонена.
- ID 22 — low, правка спецификации: реализация соответствует Task 3; изменение AC2 не является исправлением кода.
- ID 23 — low, правка спецификации: новое действие требует нового точного ожидания; отклонение объяснено, согласование Task 6/AC12 не является исправлением кода.

#### Ревью 2026-10-14 — `b4fab053..741ce342`

Подтверждён полный диапазон: 30 файлов, +3234/−113, включая накопленные исправления, ускорение тестов, CI и документы. Режим `full`; контекст — эта стори, `project-context.md`, `AGENTS.md` и `backend/AGENTS.md`. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 13, `verification-gap` — 3 (два пробела и дополнительное замечание), `acceptance-auditor` — 3. Каждое из 29 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 3 группы исправлений, 4 отложенные группы (повторы существующего долга), 16 отклонённых замечаний. Код и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-14…R42.4-16 открытыми задачами в стори, без исправлений кода и тестов. Статус стори и записи спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления:**

- [x] [Review][Patch] **R42.4-14: привязка всё ещё ждёт чужую цель при передаче между проверкой и блокировкой** — `medium`, ID 13 и 23 (`edge-case-hunter`). Предварительный `scope.exists()` закрывает передачу до проверки, но `_lock_rows` затем выбирает обе строки через общий `User.objects`. Передача, завершённая после проверки и до SELECT FOR UPDATE, оставляет уже чужую цель в блокируемом наборе. Воспроизведён настоящий HTTP POST на PostgreSQL с `ATOMIC_REQUESTS=False`: после проверки второе соединение передало заявку другому менеджеру, затем отдельная транзакция удержала её строку; запрос привязки получил `OperationalError`, SQLSTATE `55P03`, при `lock_timeout=2s` вместо 404. Контрольный постоянный тест передачи до проверки прошёл. Ограничить цель разрешённой выборкой непосредственно в запросе захвата строк, сохранив совместный порядок по pk, законно внешний источник 1С и повторную проверку после захвата; добавить конкурентный тест этого промежутка. Это ожидание чужой строки, не доказанное изменение чужого клиента: транзакция откатилась. [backend/apps/users/manager_admin.py:295-305,211-215]
- [x] [Review][Patch] **R42.4-15: проверка маршрута сообщает успех при неполном ответе или 302 страницы входа** — `medium`, ID 6 и 22 (`blind-hunter`, `edge-case-hunter`). В конвейере `curl -f ... | grep -q` результат curl теряется; кроме того, `-f` не требует именно 200. Воспроизведено с настоящим локальным HTTP-сервером: страница входа объявляет Content-Length 9999 и отдаёт только форму — curl сообщает ошибку 18, но скрипт завершается 0; вариант с HTTP 302 и телом `id="login-form"` тоже завершается 0. Этот скрипт определяет успех и CI, и проверки после production-деплоя. Проверять код завершения curl независимо от поиска формы, отдельно требовать HTTP 200 и анализировать полностью полученное тело; закрепить оба отрицательных случая и положительный ответ тестом скрипта. Добавление только pipefail не заменяет проверку 200 и полного тела. [scripts/deploy/check-manager-route.sh:17-28; .github/workflows/main.yml:227; .github/workflows/deploy.yml]
- [x] [Review][Patch] **R42.4-16: авторизованный доступ через nginx не защищён сквозной проверкой** — `medium`, ID 24 (`verification-gap`, пробел регрессии). HTTP-скрипт проверяет только анонимный редирект и страницу входа; тесты авторизованного списка используют Django Client и обходят nginx; статический страж проверяет upstream. Добавление `proxy_set_header Cookie "";` в новую location сохранит зелёными все эти проверки, но менеджер с действующей сессией получит редирект на вход вместо списка клиентов. Добавить Docker HTTP-проверку `/manager/users/user/` через настоящий nginx с действующей сессией менеджера: 200, собственный клиент виден, чужой отсутствует. Текущий конфиг cookie не удаляет; дефект текущей передачи сессии не заявляется. Доказательства слоя verification-gap приняты по правилам workflow; мутация конфигов в этом запуске не выполнялась. [docker/nginx/conf.d/default.conf:227; docker/nginx/conf.d/local.conf:83; scripts/deploy/check-manager-route.sh:17-28; .github/workflows/main.yml:210-231]

**Отложено — повторы существующих задач, без новых самостоятельных пунктов:**

- [x] [Review][Defer] **Первая блокировка массового действия через exists не гарантирует порядок pk** — `maybe-false`, возможный `medium`, ID 3 и 14. Действия вызывают exists до итерации; Django снимает сортировку и добавляет LIMIT 1. Конкретный цикл ожидания двух пересекающихся действий в этом запуске не воспроизводился. Существующая задача на `220766c3` в deferred-work остаётся единственной; для закрытия наблюдать первые блокировки и фактический deadlock либо исключить такое расписание. [backend/apps/users/manager_admin.py:307-318; backend/apps/users/admin.py:1196-1207,1251-1261]
- [x] [Review][Defer] **Подтверждение и привязка используют разный порядок source/target** — `medium`, ID 4 и 15. Общий сервис подтверждения блокирует target перед обращением к сервису привязки с порядком pk. При более старом source возможен цикл с отдельной привязкой. Этот порядок существовал до 42.4; исходная задача общих сервисов остаётся единственной. Runtime-deadlock в этом запуске не воспроизводился; нужна двухсоединительная проверка фактического цикла и единый порядок захвата. [backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153; backend/apps/users/manager_admin.py:277-305]
- [x] [Review][Defer] **Доступ адресата по полному URL регионального письма не проверен** — `medium`, ID 8, 17 и 25. Несвязанный адрес, суперпользователь в резерве либо прежний региональный адресат после ручной передачи могут не открыть заявку. Решение Alex о ручной очистке правил перед выкатом и существующая задача сквозной проверки регионального и резервного получателя сохранены. В этом запуске ссылка из письма от имени адресата не открывалась. [backend/apps/users/tasks.py:442-446; backend/tests/unit/test_region_routing.py:153-179; backend/freesport/admin_site.py:56-66]
- [x] [Review][Defer] **R42.4-D1: заблокированный клиент получает JWT при HTTP-входе** — `medium`, ID 9. Код UserLoginView перед созданием токенов запрещает pending, но не проверяет is_active. Это ранее существовавший дефект; AC6 корректно требует ModelBackend.authenticate. Исходная задача остаётся единственной; HTTP-вход в этом запуске отдельно не воспроизводился. [backend/apps/users/views/authentication.py:310-330]

**Проверки:**

- GitNexus актуален: индекс и HEAD `741ce342`; до записи отчёта рабочее дерево чистое и `detect-changes --scope all` — нет изменений. `--scope compare --base-ref b4fab053`: 30 файлов, 89 символов, 15 потоков, риск high. `impact scope_clients` — HIGH, прямой вызывающий get_queryset, далее три изменяющих потока; `_lock_client` — HIGH, три прямых вызывающих: change_view, user_change_password и verify_b2b_view. `UserAdmin` — LOW, две прямые зависимости. Предупреждение передано Alex; символы не правились.
- Docker + PostgreSQL, один последовательный профильный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_nginx_security_headers.py`, `--override-ini=addopts= -q -p no:sugar` — **137 passed**, 6 предупреждений об устаревающих API, 226,50 с.
- Дополнительная pytest-функция внедрена только в память существующего тестового модуля, без файлов реализации или постоянных тестов. Прогон новой проверки R42.4-14 и контрольного `test_link_to_transferred_client_answers_404_without_lock` — **1 failed, 1 passed**, 29,67 с. Новая проверка получила LockNotAvailable / OperationalError вместо 404; захват и передача выполнялись настоящими соединениями PostgreSQL. Подмена границы `_lock_rows` лишь фиксировала расписание и вызывала штатную реализацию.
- R42.4-15 воспроизведён сначала подстановкой curl, затем настоящим HTTP-сервером в памяти: неполное тело с curl exit 18 и HTTP 302 с формой оба дали скрипту exit 0. `bash -n` скрипта прошёл. Сервер остановлен после проверки; файлы не создавались.
- Runtime-проверка row_is_locked в Docker: посторонний DatabaseError даёт True. Это уже рассмотренный диагностический риск, не доказательство ошибочно зелёного полного прогона; ID 7 и 20 отклонены как low.
- Полный backend-набор, линтеры, production и новая мутация Cookie в nginx в этом запуске не проверялись. Существующие dev/test-сервисы не перезапускались.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | low | В /admin/ save и аудит не атомарны; ранее принятый редкий сбой INSERT, новая транзакционная обвязка отклонена. |
| 2 | blind-hunter №2 | low | Eligibility в /admin/ может смениться после чтения; ранее рассмотренная редкая гонка, новая блокировка отклонена. |
| 3 | blind-hunter №3 | maybe-false | exists не гарантирует первый pk; конкретный цикл не показан, повтор существующего отложенного вопроса. |
| 4 | blind-hunter №4 | medium | Target-first подтверждения отличается от pk-order привязки; существующий долг общих сервисов. |
| 5 | blind-hunter №5 | low | Ожидание Django не гарантирует готовность nginx; сбой медленного запуска возможен, но не воспроизведён, новая повторная проверка ради редкого тайминга отклонена. |
| 6 | blind-hunter №6 | medium | Настоящий сервер с неполным телом и отдельно с 302 дал скрипту exit 0; R42.4-15. |
| 7 | blind-hunter №7 | low | Широкий DatabaseError воспроизведён как True; обычный ложноположительный прогон не показан, ранее принятое расширение обработки отклонено. |
| 8 | blind-hunter №8 | medium | Подстрока URL не подтверждает доступ адресата; существующий конфигурационный долг письма. |
| 9 | blind-hunter №9 | medium | UserLoginView до JWT не проверяет is_active; ранее существовавший R42.4-D1, AC6 не меняется. |
| 10 | blind-hunter №10 | low | AC2 конфликтует с исключением Task 3; исправление рассматриваемой спецификации исключено. |
| 11 | edge-case-hunter №1 | low | Неатомарность save/аудита в /admin/ реальна, но редкий исход уже принят; новая обвязка отклонена. |
| 12 | edge-case-hunter №2 | low | Конкурентное изменение допустимости разблокировки в /admin/ возможно; новая блокировка ради ранее принятой редкой гонки отклонена. |
| 13 | edge-case-hunter №3 | medium | Передача после exists и удержание чужой цели реально дали 55P03 вместо 404; R42.4-14. |
| 14 | edge-case-hunter №4 | maybe-false | Снятие порядка первым exists подтверждается кодом, но runtime-deadlock не показан; повтор отложенной задачи. |
| 15 | edge-case-hunter №5 | medium | Общий target-first сервис допускает цикл с pk-order привязкой; ранее зарегистрированный source/target-долг. |
| 16 | edge-case-hunter №6 | low | Пробельный ИНН может увести клиента и дать 404 после успешного подтверждения; ранее принятая новая ветка редиректа отклонена. |
| 17 | edge-case-hunter №7 | medium | Ручная передача до email-задачи может лишить регионального адресата доступа; существующая задача письма охватывает этот исход. |
| 18 | edge-case-hunter №8 | low | При нестандартной стартовой БД Redis диапазон воркеров может выйти за пределы; поддерживаемый compose использует БД 1 и n ≤ 15, новый ограничитель конфигурации ради неподтверждённого штатного сбоя отклонён. |
| 19 | edge-case-hunter №9 | low | Остаток unique_digits может совпасть; редкая коллизия уже рассмотрена, дополнительный распределитель отклонён. |
| 20 | edge-case-hunter №10 | low | Посторонний DatabaseError принимается за NOWAIT-конфликт; повтор ранее принятого диагностического риска, как ID 7. |
| 21 | edge-case-hunter №11 | low | При исключении POST вызов join пропускается; редкий аварийный путь тестовой обвязки, живой поток при штатном прогоне не показан, новая ветка очистки отклонена. |
| 22 | edge-case-hunter №12 | medium | Ошибка curl 18 скрыта успешным grep в настоящем HTTP-сценарии; R42.4-15. |
| 23 | edge-case-hunter №13, claim | medium | Заявленное исключение ожидания чужой цели не охватывает передачу между проверкой и захватом; тот же воспроизведённый R42.4-14, не предложение менять текст коммита. |
| 24 | verification-gap №1 | medium | Cookie-мутация не ловится анонимным smoke и прямыми Django-тестами; принятый пробел регрессии R42.4-16. |
| 25 | verification-gap №2 | medium | Доступ адресата по извлечённой ссылке не проверяется; существующая отложенная задача, ручное решение сохранено. |
| 26 | verification-gap, дополнительное | low | В /admin/ save предшествует INSERT аудита без общей транзакции; тот же ранее принятый редкий риск, что ID 1 и 11. |
| 27 | acceptance-auditor №1 | low | AC2 расходится с явно утверждённым Task 3; исправление самой спецификации исключено. |
| 28 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового expected_actions; отклонение 2 фиксирует причину, согласование Task 6/AC12 — правка спецификации. |
| 29 | acceptance-auditor №3 | low | Новый CI-шаг запускает Django на раннере, вопреки буквальному Docker-ограничению; существующие check и pytest этого job уже работают так же, Completion Notes описывают выбранную схему. Конкретный сбой из-за этого не показан; перенос всей среды smoke в Compose — дополнительная инфраструктура, не прямая коррекция наблюдённого дефекта. |

##### Отклонено — ревью на `741ce342` (16)

- ID 1 — low: ранее принятый редкий сбой INSERT аудита в /admin/; новая транзакционная обвязка отклонена.
- ID 2 — low: ранее рассмотренная редкая гонка eligibility в /admin/; новая блокировка отклонена.
- ID 5 — low: сбой медленной готовности nginx не воспроизведён; новая retry-логика ради редкого тайминга отклонена.
- ID 7 — low: широкий except подтверждён, но обычный ошибочно зелёный прогон не показан; ранее принятая дополнительная обработка редких SQL-сбоев отклонена.
- ID 10 — low, правка спецификации: код выполняет исключение Task 3; согласование AC2 не исправляет реализацию.
- ID 11 — low: тот же редкий принятый сбой save/аудита в /admin/, индивидуально проверен; новая обвязка отклонена.
- ID 12 — low: редкая конкурентная смена признаков при разблокировке в /admin/; новая блокировка ранее отклонена.
- ID 16 — low: редкий недоступный редирект по пробельному ИНН уже принят; отдельная новая ветка отклонена.
- ID 18 — low: штатные compose и документированный предел воркеров помещаются в Redis; новая проверка нестандартной конфигурации без наблюдённого штатного сбоя отклонена.
- ID 19 — low: крайне редкая коллизия генератора уже рассмотрена; новый распределитель не оправдан показанным прогоном.
- ID 20 — low: тот же ранее принятый широкий перехват DatabaseError, что ID 7; новая обработка редкого диагностического состояния отклонена.
- ID 21 — low: аварийный POST может обойти join; новый сценарий живого потока при штатной работе не показан, дополнительная ветка cleanup отклонена.
- ID 26 — low: тот же ранее принятый редкий save/аудит в /admin/, что ID 1 и 11; новая защита отклонена.
- ID 27 — low, правка спецификации: Task 3 прямо разрешает выбранное поведение фильтра роли.
- ID 28 — low, правка спецификации: новое действие требует нового точного ожидания, причина записана в отклонении 2.
- ID 29 — low: runner-схема CI явно описана и используется существующим job; конкретный дефект среды не показан, новое Compose-окружение ради буквального ограничения отклонено.

#### Ревью 2026-10-14 — `b4fab053..d9f21c20`

Подтверждён весь диапазон: 33 файла, +3637/−113, 4419 строк diff, включая реализацию, накопленные исправления, ускорение тестов, CI и документы. Режим `full`; контекст — эта история, `project-context.md`, `AGENTS.md` и `backend/AGENTS.md`. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 12, `verification-gap` — 5 (три пробела и два дополнительных замечания), `acceptance-auditor` — 3. Каждое из 30 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 2 группы исправлений проверок, 5 отложенных групп (четыре повтора существующих задач и один ранее существовавший дефект писем), 17 отклонённых замечаний. Код и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-17 и R42.4-18 открытыми задачами, без исправлений кода и тестов. Статус истории и записи `42-4-manager-section-own-clients` в трекере спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления — пробелы регрессионных проверок, не обнаруженные дефекты текущих конфигов:**

- [x] [Review][Patch] **R42.4-17: вход менеджера не проверяется через production-конфиг nginx** — `medium`, ID 7 и 24. `check-manager-session.sh` исполняется только с `local.conf`; проверка production выполняет только анонимный `check-manager-route.sh`. Мутация `proxy_hide_header Set-Cookie;` только в `/manager/` файла `default.conf` оставляет эти проверки и статический страж upstream зелёными, хотя вход менеджера перестанет работать. Расширить CI smoke-проверку запуском production-конфига на изолированном стенде с тестовыми аккаунтами и проверкой сессии, собственного и чужого клиентов; production-учётные записи не создавать. Доказательства слоя verification-gap приняты по workflow; новая мутация конфигов в этом запуске не выполнялась. Текущий `default.conf` Cookie/Set-Cookie не удаляет. [docker/nginx/conf.d/default.conf:227-239; .github/workflows/main.yml:242-254; .github/workflows/deploy.yml:508; scripts/deploy/check-manager-session.sh:35-73]
- [x] [Review][Patch] **R42.4-18: изоляция Redis между воркерами не защищена обязательной проверкой** — `medium`, ID 25. Настройки разводят Redis DB по `PYTEST_XDIST_WORKER`, но обязательный CI-прогон последовательный; поиск слоя verification-gap не обнаружил теста межпроцессной изоляции. Замена `_WORKER_INDEX` на постоянный 0 не изменит этот прогон, а `cache.clear()` одного воркера параллельного запуска сможет удалить кэш и локи другого. Добавить Docker-проверку двух процессов с настройками `gw0` и `gw1`: разные DB, контрольные значения обоих, очистка первого и сохранность значения второго. Это пробел регрессии корректных текущих настроек, не наблюдённое взаимное удаление данных. Доказательства слоя verification-gap приняты по workflow; мутация настроек в этом запуске не выполнялась. [backend/freesport/settings/test.py:91-98; backend/tests/conftest.py:682; .github/workflows/main.yml:197-200]

**Отложено:**

- [x] [Review][Defer] **Разный порядок source/target у подтверждения и привязки** — `medium`, ID 2 и 14; повтор существующей задачи общих сервисов. Подтверждение держит target перед вызовом привязки, отдельная привязка при меньшем pk источника начинает с source. Такой порядок существовал до baseline; фактический deadlock в этом запуске не воспроизводился. Нужны двухсоединительная проверка цикла и единый порядок захвата. [backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153; backend/apps/users/manager_admin.py:277-313]
- [x] [Review][Defer] **Первая блокировка массового действия через exists не гарантирует порядок pk** — `maybe-false`, возможный `medium`, ID 3 и 15; повтор существующего неподтверждённого вопроса. Runtime-исходник Django снова показал `clear_ordering(force=True)` и LIMIT 1; конкретный цикл двух действий не показан. Для закрытия наблюдать первые захваченные строки и реальный deadlock либо исключить расписание. [backend/apps/users/manager_admin.py:315-325; backend/apps/users/admin.py:931-940,1196-1207,1251-1261]
- [x] [Review][Defer] **Полный URL и доступ адресата регионального письма не проверены** — `medium`, ID 5, 18 и 23; повтор существующей задачи. Подстрока пути не защищает полный URL; после передачи либо при несвязанном/резервном адресате доступ к заявке может отсутствовать. Решение Alex о ручной очистке правил перед выкатом сохранено; не менять политику писем в этой истории. Исходная задача уже требует открытия извлечённой ссылки региональным и резервным адресатом. В этом запуске переход из письма не выполнялся. [backend/apps/users/tasks.py:421-444; backend/tests/unit/test_region_routing.py:153-191]
- [x] [Review][Defer] **R42.4-D1: успешный HTTP-вход заблокированного клиента** — `medium`, ID 6 и 27; повтор существующего дефекта API. Сериализатор проверяет пароль неактивного пользователя напрямую, view запрещает pending, но не проверяет is_active перед JWT. AC6 корректно требует ModelBackend.authenticate. HTTP-вход в этом запуске отдельно не воспроизводился, исходная задача остаётся единственной. [backend/apps/users/serializers.py:537-558; backend/apps/users/views/authentication.py:310-331]
- [x] [Review][Defer] **Письмо об одобрении публикуется до коммита и переживает откат заявки** — `medium`, ID 16; ранее существовавший дефект общего сигнала, впервые зарегистрирован в этом запуске. `check_verification_status_change` вызывает `.delay()` сразу после save, а task отправляет письмо без проверки текущего статуса. Временная HTTP-проверка массового одобрения с `ATOMIC_REQUESTS=False` и ошибкой AuditLog показала: задача опубликована внутри транзакции, после отката статус pending и is_verified=False; выполнение настоящего task после отката вызвало замоканный send_mail один раз. Общий сигнал и транзакционное подтверждение B2B присутствовали до baseline, поэтому это отдельный долг, а не patch manager-wrapper. Публиковать через transaction.on_commit и закрепить отсутствие постановки/отправки при откате, а также однократную отправку после успешного коммита. [backend/apps/users/signals.py:31-47; backend/apps/users/tasks.py:498-526; backend/apps/users/admin.py:958-961; backend/apps/users/manager_admin.py:324-325]

**Проверки:**

- Docker + PostgreSQL, один последовательный профильный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_check_manager_route_script.py`, `test_nginx_security_headers.py`, `--override-ini=addopts= -q -p no:sugar` — **145 passed**, 6 предупреждений об устаревающих API, 238,95 с.
- Проверка отката письма внедрена pytest-плагином только в память существующего модуля: **1 failed**, 28,58 с, ожидаемое падение требования «при откате нет опубликованной задачи». Вывод: `rolled_back_status=pending`, `queued=[(2, True)]`, `sent_after_rollback=1`. Broker-вызов перехвачен, внешняя отправка замокана; настоящее тело task исполнилось после отката. Файлов тестов/реализации не создавалось. `git show b4fab053:backend/apps/users/signals.py` и `git blame b4fab053` сервиса подтверждения установили ранее существовавшую причину.
- Runtime-исходник `Query.exists` в тестовом контейнере подтвердил снятие ORDER BY и LIMIT 1; взаимная блокировка массовых действий не воспроизводилась.
- `bash -n` обоих HTTP-скриптов — успешно. Живой dev-nginx: `/manager/` — 302 на `/manager/login/?next=/manager/`, страница входа — 200. Production, HTTPS-вход, новые nginx/Redis-мутации, полный backend-набор и линтеры в этом запуске не проверялись. Сервисы не перезапускались.
- GitNexus актуален, индекс и HEAD `d9f21c20`. До записи результатов `detect-changes --scope all` — нет изменений символов. Анализ диапазона: 34 файла, 90 символов, 15 потоков, риск high (в отличие от зафиксированного diff, инструмент учитывает и состояние рабочего дерева). `impact scope_clients` — HIGH, прямой get_queryset, три изменяющих потока; `_lock_client` — HIGH, прямые change_view, user_change_password, verify_b2b_view. Предупреждение передано Alex, символы не правились. Пользовательские изменения `_bmad/custom/bmad-code-review.toml` и `_bmad/custom/bmad-review.toml` не трогались.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | low | В /admin/ save и аудит не атомарны; ранее принятый редкий сбой INSERT, новая обвязка отклонена. |
| 2 | blind-hunter №2 | medium | Target-first подтверждения и source-first привязки допускают цикл; существующий долг общих сервисов. |
| 3 | blind-hunter №3 | maybe-false | exists снимает порядок, подтверждено runtime; конкретный цикл не показан, повтор отложенного вопроса. |
| 4 | blind-hunter №4 | low | Обычное назначение проверяют тесты 42.2; 404 после пробельного ИНН — ранее принятый редкий исход. |
| 5 | blind-hunter №5 | medium | Тест подстроки не проверяет доступ получателя по полному URL; существующий конфигурационный долг. |
| 6 | blind-hunter №6 | medium | HTTP-view не проверяет активность до JWT; существующий R42.4-D1, а не неверный тест AC6. |
| 7 | blind-hunter №7 | medium | Сессионный smoke работает только с local.conf; production-мутация потери cookie не обнаруживается, R42.4-17. |
| 8 | blind-hunter №8 | low | Ожидание Django не означает готовность nginx; редкий тайминг, ранее принятая новая retry-обвязка отклонена. |
| 9 | blind-hunter №9 | low | Любой DatabaseError трактуется как NOWAIT-конфликт; ранее принятый диагностический риск, обычный ложноположительный прогон не показан. |
| 10 | blind-hunter №10 | low | Буквальный AC2 конфликтует с Task 3; исправление самой спецификации исключено. |
| 11 | edge-case-hunter №1 | low | Неатомарность save/аудита в /admin/ реальна; тот же принятый редкий сбой INSERT. |
| 12 | edge-case-hunter №2 | low | Eligibility в /admin/ может смениться после чтения; ранее рассмотренная редкая гонка, новая блокировка отклонена. |
| 13 | edge-case-hunter №3 | low | Две конкурентные разблокировки /admin/ могут создать два события; ранее принятая редкая коллизия. |
| 14 | edge-case-hunter №4 | medium | Тот же существующий source/target-долг; фактический deadlock в этом запуске не проверялся. |
| 15 | edge-case-hunter №5 | maybe-false | Первый exists снимает порядок; цикл ожидания не воспроизведён, повтор существующего вопроса. |
| 16 | edge-case-hunter №6 | medium | HTTP-одобрение откатилось, опубликованный task вызвал send_mail после отката; причина общего сигнала существовала до baseline. |
| 17 | edge-case-hunter №7 | low | Пробельный ИНН может увести клиента и дать 404 после успешного подтверждения; ранее принятый редкий редирект. |
| 18 | edge-case-hunter №8 | medium | Региональный адресат после ручной передачи может потерять доступ; существующая задача писем. |
| 19 | edge-case-hunter №9 | low | Остаток unique_digits теоретически повторяется; редкая коллизия уже принята, дополнительный распределитель отклонён. |
| 20 | edge-case-hunter №10 | low | Широкий DatabaseError подтверждён кодом; тот же ранее принятый диагностический риск. |
| 21 | edge-case-hunter №11 | low | Исключение POST пропускает join; ранее рассмотренный аварийный путь тестовой обвязки, новая cleanup-ветка отклонена. |
| 22 | edge-case-hunter №12 | low | Однократный smoke может опередить nginx; тот же принятый редкий стартовый тайминг. |
| 23 | verification-gap №1 | medium | Полный извлечённый URL и доступ адресата не проверяются; повтор существующей задачи. |
| 24 | verification-gap №2 | medium | Set-Cookie-мутация только default.conf не ловится прочитанными проверками; принятый пробел R42.4-17. |
| 25 | verification-gap №3 | medium | Константный индекс воркера не обнаружит последовательный CI; принятый пробел R42.4-18. |
| 26 | verification-gap, дополнительное №1 | low | В /admin/ save предшествует INSERT аудита без общей транзакции; ранее принятый редкий риск. |
| 27 | verification-gap, дополнительное №2 | medium | API выдаёт JWT неактивному клиенту; ранее существовавший R42.4-D1, AC6 корректен. |
| 28 | acceptance-auditor №1 | low | AC2 противоречит утверждённому Task 3; исправление спецификации исключено из patch. |
| 29 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового expected_actions; отклонение 2 описано, согласование AC12/Task 6 — правка спецификации. |
| 30 | acceptance-auditor №3 | low | CI запускает Django на раннере: схема явно описана и используется существующим job; нового сбоя не показано, перенос в Compose — новая инфраструктура. |

##### Отклонено — ревью на `d9f21c20` (17)

- ID 1 — low: ранее принятый редкий сбой аудита в /admin/; новая атомарная обвязка отклонена.
- ID 4 — low: автоматическое назначение покрыто смежными тестами; редкий недоступный редирект уже принят и требует новой ветки.
- ID 8 — low: редкий стартовый тайминг nginx ранее принят; новая retry-обвязка без наблюдённого штатного сбоя отклонена.
- ID 9 — low: широкий DatabaseError реален, но обычный ошибочно зелёный прогон не показан; ранее принятая дополнительная обработка отклонена.
- ID 10 — low, правка спецификации: код выполняет явно утверждённое исключение Task 3.
- ID 11 — low: тот же принятый редкий save/аудит /admin/, индивидуально проверен.
- ID 12 — low: ранее рассмотренная редкая гонка признаков /admin/; новая блокировка отклонена.
- ID 13 — low: два запроса могут записать два события; редкая коллизия уже принята, новая дедупликационная блокировка отклонена.
- ID 17 — low: 404 после переноса пробельного ИНН уже принят; отдельная новая ветка редиректа отклонена.
- ID 19 — low: редкая коллизия тестового генератора ранее принята; новый распределитель отклонён.
- ID 20 — low: тот же ранее принятый диагностический риск, что ID 9; дополнительная обработка отклонена.
- ID 21 — low: аварийный POST может обойти join; ранее рассмотренная новая cleanup-ветка отклонена.
- ID 22 — low: тот же редкий стартовый тайминг, что ID 8; новая retry-обвязка отклонена.
- ID 26 — low: тот же принятый редкий сбой INSERT аудита /admin/, что ID 1 и 11.
- ID 28 — low, правка спецификации: Task 3 прямо разрешает поведение фильтра роли.
- ID 29 — low, правка спецификации: добавление требуемого действия вынуждает новое ожидание; отклонение 2 объясняет причину.
- ID 30 — low: runner-схема CI описана и соответствует существующему job; перенести весь smoke в Compose ради буквального ограничения — новая инфраструктура без показанного сбоя.

#### Ревью 2026-10-14 — `b4fab053..46ff9a6e`

Подтверждён весь диапазон: 36 файлов, +3876/−113, 4679 строк diff; режим `full`, включая реализацию, тестовую инфраструктуру, CI и документы. Контекст — эта история целиком, `project-context.md`, `AGENTS.md`, `backend/AGENTS.md` и предыдущие решения. Все четыре настроенных слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 13, `verification-gap` — 4 (два пробела и два дополнительных замечания), `acceptance-auditor` — 2. Каждое из 29 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 2 группы исправлений, 4 отложенные группы (повторы существующего долга), 19 отклонённых замечаний. Реализация и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-19 и R42.4-20 открытыми задачами в story, без исправления кода и тестов. Статус story и записи `42-4-manager-section-own-clients` в трекере спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления:**

- [x] [Review][Patch] **R42.4-19: тест изоляции Redis очищает базы живых воркеров при разрешённом `-n 12…15`** — `medium`, ID 2, 11 и 27 (`blind-hunter`, `edge-case-hunter`, дополнительное замечание `verification-gap`). Дочерние процессы теста используют базу 12 и индексы `gw0`/`gw1`, поэтому очищают DB 12 и 13. Основной прогон с базовой DB 1 назначает те же базы `gw11` и `gw12`; документированный предел допускает 15 воркеров. Четыре настоящих процесса с текущими настройками подтвердили совпадение: `active_gw11=/12`, `probe_gw0=/12`, `active_gw12=/13`, `probe_gw1=/13`. Очистка теста может удалить кэш и локи других тестов; диагностика не выполняла записей или очистки Redis. Исключить пересечение с активным диапазоном воркеров либо использовать отдельный Redis для пробы; закрепить безопасное поведение для разрешённого большого числа воркеров. [backend/tests/unit/test_xdist_redis_isolation.py:29,55-63,80-96; backend/freesport/settings/test.py:91-98; .agents/skills/docker-test-run/SKILL.md:33]
- [x] [Review][Patch] **R42.4-20: отказ сессионного smoke-скрипта на чужом клиенте не защищён автоматическим негативным тестом** — `medium`, ID 25 (`verification-gap`, пробел регрессии). CI запускает `check-manager-session.sh` только на корректно разделённых клиентах; тест HTTP-скрипта запускает только `check-manager-route.sh`. Удаление проверки `FOREIGN_EMAIL` оставит эти проверки зелёными: при исправном приложении чужой клиент отсутствует. Добавить автоматический сценарий успешного входа и HTTP 200 списка с обоими email, требующий ненулевого кода скрипта, и положительный контроль с одним своим клиентом. Это страж текущей корректной проверки скрипта, а не обнаруженная утечка в разделе. Доказательства слоя verification-gap приняты по workflow; новая мутация и отдельный HTTP-сценарий в этом запуске не выполнялись. [scripts/deploy/check-manager-session.sh:68-74; .github/workflows/main.yml:269-275; backend/tests/unit/test_check_manager_route_script.py]

**Отложено — повторы существующих задач, без новых самостоятельных пунктов:**

- [x] [Review][Defer] **Первая блокировка массового действия через `exists()` не гарантирует порядок pk** — `maybe-false`, возможный `medium`, ID 6 и 15. Runtime-исходник установленного Django подтвердил `clear_ordering(force=True)` и `set_limits(high=1)`; фактический цикл ожидания не воспроизводился. Исходная задача на `220766c3` остаётся единственной: наблюдать первые захваченные строки и реальный deadlock либо исключить расписание. [backend/apps/users/manager_admin.py:324-325; backend/apps/users/admin.py:1251-1261]
- [x] [Review][Defer] **Разный порядок source/target у подтверждения и привязки** — `medium`, ID 14. Подтверждение удерживает target до общей привязки, а отдельная привязка при меньшем pk источника начинает с source. Общие сервисы существовали до baseline, порядок не изменён; runtime-deadlock в этом запуске не проверялся. Исходная задача согласования порядка общих сервисов сохранена. [backend/apps/users/manager_admin.py:277-283; backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153]
- [x] [Review][Defer] **Письмо об одобрении может пережить откат заявки** — `medium`, ID 16. Общий сигнал вызывает `.delay()` сразу после сохранения статуса, до коммита внешней транзакции; дефект уже зарегистрирован и ранее воспроизведён. В этом запуске подтверждён чтением, отправка письма и новый rollback-сценарий не выполнялись. Исходная задача `transaction.on_commit` остаётся единственной. [backend/apps/users/signals.py:31-47; backend/apps/users/manager_admin.py:324-325]
- [x] [Review][Defer] **Полный URL и доступ адресата регионального письма не проверены сквозным тестом** — `medium`, ID 18 и 24. Слой verification-gap подтвердил, что удаление `SITE_URL` не обнаружат проверки подстроки пути; региональный адресат также не обязательно имеет доступ к уже переданной заявке. Решение Alex о ручной очистке правил перед выкатом и существующая задача извлечения полного URL и перехода от имени получателя сохранены. Переход из письма в этом запуске не выполнялся. [backend/apps/users/tasks.py:444; backend/tests/unit/test_region_routing.py:153-191]

**Проверки:**

- Docker + PostgreSQL, один последовательный прогон: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_check_manager_route_script.py`, `test_nginx_security_headers.py`, `test_xdist_redis_isolation.py`, `--override-ini=addopts= -q -p no:sugar` — **146 passed**, 6 предупреждений об устаревающих API, 277,92 с. Полный backend-набор, линтеры, новые мутации nginx и production не проверялись.
- Безопасная диагностика Redis в Docker: четыре отдельных процесса только загрузили настройки и вывели номера DB, без подключения для записи или очистки. Совпадение активных и проверочных DB 12/13 подтверждено. В той же команде runtime-исходник `Query.exists` подтвердил снятие ORDER BY и LIMIT 1. Последующая дополнительная проверка `RequestFactory` не исполнилась из-за неинициализированных настроек внутри `override_settings`; ошибка диагностики не считается дефектом приложения. Отдельный исправленный запуск с настоящими `freesport.settings.development` показал `SECURE_PROXY_SSL_HEADER=None`, `is_secure=False` даже с `X-Forwarded-Proto: https`: заявленное падение текущего smoke по HTTPS-CSRF не подтверждается. Production-настройки этим результатом не проверены.
- GitNexus актуален: индекс и HEAD `46ff9a6e`; `detect-changes --scope all` до записи отчёта — нет изменений. Для диапазона `--scope compare --base-ref b4fab053`: 36 файлов, 90 символов, 15 потоков, риск high. `impact _lock_client` — HIGH, прямые `change_view`, `user_change_password`, `verify_b2b_view`; `impact scope_clients` — HIGH, прямой `get_queryset`, далее три изменяющих потока. Предупреждение передано Alex; символы не правились.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | В текущем development-smoke Django не распознаёт HTTPS по proxy-заголовку; runtime `is_secure=False`, отказ по отсутствующему Referer здесь не возникает. |
| 2 | blind-hunter №2 | medium | Проверочные DB 12/13 совпадают с активными gw11/gw12 при разрешённом числе воркеров; R42.4-19. |
| 3 | blind-hunter №3 | low | Предел 15 в документации прямо обусловлен базовой DB 1 штатного compose; новая проверка нестандартной базы без штатного сбоя отклонена. |
| 4 | blind-hunter №4 | low | Проверка готовности только Django и curl без таймаута реальны; ранее принятый редкий стартовый тайминг, новое ожидание nginx отклонено. |
| 5 | blind-hunter №5 | low | Любой DatabaseError принимается за NOWAIT-конфликт; ранее рассмотренный диагностический риск, обычный ложноположительный прогон не показан. |
| 6 | blind-hunter №6 | maybe-false | Runtime exists снимает сортировку, но реальный цикл ожидания не показан; повтор существующего отложенного вопроса. |
| 7 | blind-hunter №7 | low | Save и аудит в /admin/ не атомарны; ранее принятый редкий сбой INSERT, новая обвязка отклонена. |
| 8 | blind-hunter №8 | low | AC2 конфликтует с утверждённым исключением Task 3; исправление рассматриваемой спецификации исключено. |
| 9 | blind-hunter №9 | low | Task 2 требует нового expected_actions, отклонение 2 объясняет правку; согласование Task 6 — правка спецификации. |
| 10 | blind-hunter №10 | low | Task 0 допускает stale только при тестовых/документальных изменениях вопреки AGENTS; индекс текущего запуска свежий, исправление самой story исключено. |
| 11 | edge-case-hunter №1 | medium | FLUSHDB нового теста пересекается с DB живых gw11/gw12; R42.4-19. |
| 12 | edge-case-hunter №2 | low | Ранее принятый редкий save без аудита в /admin/; новая атомарная обвязка отклонена. |
| 13 | edge-case-hunter №3 | low | Eligibility в /admin/ может смениться после чтения; ранее рассмотренная редкая гонка, новая блокировка отклонена. |
| 14 | edge-case-hunter №4 | medium | Target-first подтверждения и source-first привязки допускают цикл; существующий долг общих сервисов, новое воспроизведение не выполнялось. |
| 15 | edge-case-hunter №5 | maybe-false | exists снимает ORDER BY; конкретный deadlock с пересчётом не показан, повтор существующей задачи. |
| 16 | edge-case-hunter №6 | medium | Общий сигнал публикует задачу до коммита; ранее зарегистрированный дефект rollback-письма. |
| 17 | edge-case-hunter №7 | low | Перенос пробельного ИНН может дать недоступный редирект; ранее принятый редкий исход, новая условная ветка отклонена. |
| 18 | edge-case-hunter №8 | medium | Адресат может не иметь доступа к разделу или переданной заявке; существующий конфигурационный долг письма. |
| 19 | edge-case-hunter №9 | low | Остаток unique_digits может повториться; ранее принятая редкая коллизия, новый распределитель отклонён. |
| 20 | edge-case-hunter №10 | low | Широкий DatabaseError реален; повтор ранее принятого диагностического риска, как ID 5. |
| 21 | edge-case-hunter №11 | low | Исключение POST может пропустить join; ранее рассмотренный аварийный путь тестовой обвязки, новая cleanup-ветка отклонена. |
| 22 | edge-case-hunter №12 | low | Curl ожидания backend не ограничен по времени; ранее принятый редкий стартовый сбой, новые параметры отклонены. |
| 23 | edge-case-hunter №13 | low | Готовность Django не гарантирует готовность nginx; тот же ранее принятый редкий тайминг, что ID 4. |
| 24 | verification-gap №1 | medium | Удаление SITE_URL выживет в проверках подстроки; существующая задача полного URL и перехода получателя. |
| 25 | verification-gap №2 | medium | Удаление проверки FOREIGN_EMAIL не обнаружат корректный CI-сценарий и тест другого shell-скрипта; R42.4-20. |
| 26 | verification-gap, дополнительное №1 | low | Неатомарный save/аудит /admin/ — тот же ранее принятый редкий сбой INSERT. |
| 27 | verification-gap, дополнительное №2 | medium | Разрешённый -n 12…15 использует DB 12/13, которые очищает новый тест; R42.4-19. |
| 28 | acceptance-auditor №1 | low | Буквальный AC2 противоречит Task 3; реализация следует утверждённому исключению, правка спецификации исключена. |
| 29 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового ожидания; отклонение документировано, согласование AC12/Task 6 — правка спецификации. |

##### Отклонено — ревью на `46ff9a6e` (19)

- ID 1 — false: runtime development-настроек не считает запрос защищённым; заявленный текущий HTTPS-CSRF отказ не возникает. Проверка с production-настройками — другой объём.
- ID 3 — low: документированный предел относится к DB 1; новая проверка нестандартной базы без штатного сбоя отклонена.
- ID 4 — low: редкий тайминг готовности nginx ранее принят; новая ожидательная обвязка отклонена.
- ID 5 — low: широкий DatabaseError реален, обычный ошибочно зелёный прогон не показан; новая обработка редкого диагностического сбоя ранее отклонена.
- ID 7 — low: редкий сбой аудита /admin/ ранее принят; новая атомарная обвязка отклонена.
- ID 8 — low, правка спецификации: Task 3 прямо разрешает поведение, менять рабочий код вопреки задаче нельзя.
- ID 9 — low, правка спецификации: добавление требуемого действия вынуждает новое ожидание, причина уже записана.
- ID 10 — low, правка спецификации: текущий индекс свежий, исправление Task 0 самой story исключено из patch.
- ID 12 — low: тот же принятый редкий save без аудита /admin/, индивидуально проверен.
- ID 13 — low: редкая конкурентная смена eligibility /admin/ ранее принята; новая блокировка отклонена.
- ID 17 — low: редкий недоступный редирект после переноса ИНН ранее принят; новая условная ветка отклонена.
- ID 19 — low: редкая коллизия генератора ранее принята; дополнительный распределитель отклонён.
- ID 20 — low: тот же ранее принятый широкий DatabaseError, что ID 5; новая обработка отклонена.
- ID 21 — low: аварийный POST может обойти join; дополнительная cleanup-ветка ранее отклонена.
- ID 22 — low: зависание ожидания backend в этом запуске не наблюдалось; новые параметры ради ранее принятого редкого стартового состояния отклонены.
- ID 23 — low: тот же принятый редкий стартовый тайминг, что ID 4; новое ожидание nginx отклонено.
- ID 26 — low: тот же принятый редкий сбой INSERT аудита /admin/, что ID 7 и 12; новая защита отклонена.
- ID 28 — low, правка спецификации: реализация соответствует утверждённому Task 3, согласование AC2 не исправляет код.
- ID 29 — low, правка спецификации: новое действие требует корректного expected_actions; согласование Task 6/AC12 не исправляет реализацию.

#### Ревью 2026-10-14 — `b4fab053..956bb9c5`

Проверен весь согласованный диапазон: 36 файлов, +4113/−113, 4916 строк diff; режим `full`. Все четыре слоя завершились: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 17, `verification-gap` — два пробела и одно дополнительное замечание, `acceptance-auditor` — 3. Каждое из 33 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 2 группы исправлений, 6 отложенных групп (повторы существующего долга), 18 отклонённых замечаний. Реализация и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-21 и R42.4-22 открытыми задачами, без исправления кода и тестов. Статус story и записи `42-4-manager-section-own-clients` в трекере спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления:**

- [x] [Review][Patch] **R42.4-21: привязка к уже переданному клиенту ждёт занятый источник с меньшим pk вместо отказа** — `medium`, ID 17 (`edge-case-hunter` №7). В `_lock_link_rows` проверка scoped-цели находится внутри общего цикла по pk. Если `source.pk < target.pk`, источник захватывается раньше проверки принадлежности цели. Воспроизведено HTTP POST в Docker + PostgreSQL без `ATOMIC_REQUESTS`: создать источник раньше заявки, передать заявку другому менеджеру непосредственно перед `_lock_link_rows`, удерживать источник вторым соединением. Вместо 404 запрос пытается блокировать источник, исчерпывает `lock_timeout=2s` и выбрасывает `OperationalError` (`55P03`); без тестового таймаута будет ждать освобождения строки. Данные не утекли и чужой клиент не изменён, дефект — ожидание и ошибочный ответ на запрос без доступа. Добавить предварительную проверку принадлежности цели без блокировки до захвата источника, сохранив существующую scoped-проверку при блокировке цели и общий порядок pk; закрепить конкурентным тестом с меньшим pk занятого источника. Не смешивать с ранее зарегистрированным source/target-deadlock общих сервисов. [backend/apps/users/manager_admin.py:298-313; backend/tests/integration/test_manager_clients_section.py:1585-1620]
- [x] [Review][Patch] **R42.4-22: проверка наличия блокировки принимает постороннюю ошибку SQL за успех** — `medium`, ID 10 и 23 (`blind-hunter` №10 + `edge-case-hunter` №13). `row_is_locked` возвращает True при любом `DatabaseError`, а фикстура `locked_at_save` использует этот результат как доказательство защиты записи. В диагностике в памяти процесса pytest ошибка `DatabaseError("review non-lock SQL error")` из пробного `QuerySet.exists` без NOWAIT-конфликта дала True. Это не показанный обычный сбой PostgreSQL, а воспроизведённая ложноположительная ветка проверочного предиката: отдельное соединение может сломаться независимо от основного запроса и подтвердить отсутствующую блокировку. Ранее замечание оценивалось low без демонстрации ошибочного True; здесь переоценено по воспроизведению. Принимать только SQLSTATE `55P03` от причины исключения PostgreSQL (для установленного psycopg2 — `pgcode`), остальные ошибки пробрасывать; добавить отрицательную проверку постороннего исключения и положительный контроль настоящего NOWAIT-конфликта. [backend/tests/integration/test_manager_clients_section.py:1072-1106]

**Отложено — повторы существующих задач, без новых самостоятельных пунктов:**

- [x] [Review][Defer] **Разный порядок source/target у подтверждения и привязки** — `medium`, ID 3 и 14. Общий сервис подтверждения сначала удерживает target, затем вызывает привязку с порядком pk; отдельная привязка при меньшем source начинает с него. Общие сервисы не изменены диапазоном; новый runtime-deadlock не воспроизводился. Исходная задача согласования порядка сохранена. [backend/apps/users/manager_admin.py:277-283; backend/apps/users/services/verify_b2b_application.py:156-198; backend/apps/users/services/link_1c_customer.py:149-153]
- [x] [Review][Defer] **Порядок первой блокировки массового действия через `exists()`** — `maybe-false`, возможный `medium`, ID 4 и 15. Действия проверяют exists до итерации; снятие ORDER BY уже подтверждено предыдущей runtime-проверкой Django. Конкретный цикл ожидания не показан в этом запуске. Для закрытия исходного долга наблюдать фактические первые захваты и deadlock либо исключить расписание. [backend/apps/users/manager_admin.py:324-325; backend/apps/users/admin.py:1196-1207,1251-1261]
- [x] [Review][Defer] **Письмо об одобрении переживает откат заявки** — `medium`, ID 5, 16 и 30. Сигнал публикует `.delay()` до коммита; задача не перепроверяет статус. Повтор существовавшего до baseline и ранее воспроизведённого дефекта, без нового rollback-сценария и отправки писем здесь. Исходная задача `transaction.on_commit` сохранена. [backend/apps/users/signals.py:31-47; backend/apps/users/tasks.py:498-526]
- [x] [Review][Defer] **Неактивный клиент получает JWT от HTTP-входа** — `medium`, ID 6. Сериализатор принимает пароль неактивного клиента, view до JWT проверяет pending, но не is_active. Повтор R42.4-D1; AC6 требует именно ModelBackend.authenticate. HTTP-вход в этом запуске не воспроизводился, самостоятельной новой задачи нет. [backend/apps/users/serializers.py:537-558; backend/apps/users/views/authentication.py:310-331]
- [x] [Review][Defer] **Полный URL регионального письма не защищён проверкой** — `medium`, ID 28 (`verification-gap` №1). Принято доказательство слоя: удаление SITE_URL оставляет проверяемую подстроку пути, поэтому тесты не заметят относительный href. Существующая задача полного извлечённого URL сохранена без дублирования. [backend/apps/users/tasks.py:444; backend/tests/unit/test_region_routing.py:153-191]
- [x] [Review][Defer] **Доступ адресата регионального письма к заявке не проверен сквозным сценарием** — `medium`, ID 7, 20 и 29. Получатель регионального/резервного письма может не иметь доступа к разделу или не отвечать за переданную заявку; тесты отправки и scoped-доступа независимы. Доказательства verification-gap приняты; решение Alex о ручной очистке правил перед выкатом и исходная задача перехода от имени фактического получателя сохранены. [backend/apps/users/tasks.py:421-446; backend/freesport/admin_site.py:56-66; backend/apps/users/manager_admin.py:34-44]

**Проверки и границы:**

- Docker + PostgreSQL, последовательный штатный прогон семи файлов: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_check_manager_route_script.py`, `test_xdist_redis_isolation.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, с `--override-ini=addopts= -q -p no:sugar` — **237 passed**, 6 предупреждений об устаревающих API, 244,02 с. Полный backend-набор, линтеры, реальный nginx и production повторно не проверялись.
- Пять дополнительных диагностических тестов добавлены только в память процесса pytest, без создания файлов: **5 ожидаемых failed**. Подтверждены R42.4-21 и ошибочный True предиката R42.4-22. Также перепроверены ранее принятые редкие риски /admin/: после искусственного отказа AuditLog настоящий HTTP POST ответил 500, но клиент остался активным; изменение is_staff через второе соединение между чтением и save оставило сотрудника активным. Эти два результата не превращены в новые задачи вопреки прежнему low-триажу.
- Изолированный CSRF-контроль для запроса с `secure=True` дал 403 без Referer и пропуск middleware с Referer. Это не запуск сессионного скрипта через nginx и не доказательство падения текущего CI: `main.yml` использует development-настройки без SECURE_PROXY_SSL_HEADER, а скрипт на production не запускается. Вывод слоёв о текущем HTTPS-CSRF сбое отклонён на фактическом caller-контексте.
- GitNexus свежий на `956bb9c5`; `detect-changes --scope all` до запуска — нет изменений, для диапазона `--scope compare --base-ref b4fab053` — 36 файлов, 90 символов, 15 процессов, риск high. `impact unblock_users` — LOW, граф не показывает прямых вызывающих динамического admin-action; `impact _lock_link_rows` — LOW, прямой вызывающий `_apply_link_1c_customer`. Символы не правились.
- После проверок обнаружена внешняя незакоммиченная правка `AGENTS.md` о разрешении субагентов; её не создавал и не изменял этот запуск. Объём ревью остаётся зафиксированным коммитным диапазоном.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | Настоящий caller скрипта — CI development без распознавания HTTPS; secure-CSRF-контроль не доказывает отказ этого caller. |
| 2 | blind-hunter №2 | low | HTTP-ошибка аудита оставляет активного клиента без события; редкий риск /admin/ уже рассмотрен, новая обвязка отклонена. |
| 3 | blind-hunter №3 | medium | Target-before-source у общего подтверждения против source-before-target отдельной привязки; повтор существующего долга. |
| 4 | blind-hunter №4 | maybe-false | Exists снимает порядок, но реальный цикл пересекающихся действий не показан; существующий отложенный вопрос. |
| 5 | blind-hunter №5 | medium | Общий сигнал публикует task до коммита; существующий долг. |
| 6 | blind-hunter №6 | medium | Нет проверки is_active до выдачи JWT; повтор R42.4-D1, не нарушение AC6. |
| 7 | blind-hunter №7 | medium | Получатель из правил не обязательно отвечает за заявку; повтор долга конфигурации и сквозного теста. |
| 8 | blind-hunter №8 | false | Стандартный run --rm удаляет контейнер вместе с /tmp; повторные имена gwN в разных контейнерах не сохраняют прежние файлы. |
| 9 | blind-hunter №9 | low | Штатный compose задаёт базу 1, которой обусловлен предел 15; добавление защиты нестандартной базы без штатного сбоя отклонено. |
| 10 | blind-hunter №10 | medium | Посторонний DatabaseError дал ошибочный True пробного предиката; R42.4-22. |
| 11 | edge-case-hunter №1 | low | Индивидуально проверен тот же редкий неатомарный save/аудит в /admin/, что ID 2. |
| 12 | edge-case-hunter №2 | low | Конкурентное превращение клиента в сотрудника воспроизведено вторым соединением; ранее принятый редкий /admin/-риск, новая блокировка отклонена. |
| 13 | edge-case-hunter №3 | low | Без блокировки два запроса могут прочитать неактивного клиента и записать два события; ранее принятая редкая гонка, новый конкурентный прогон не выполнялся. |
| 14 | edge-case-hunter №4 | medium | Удерживаемый target и меньший source захватываются несовместимо; тот же существующий долг ID 3. |
| 15 | edge-case-hunter №5 | maybe-false | Отсутствие гарантированного первого порядка не доказывает deadlock; повтор долга ID 4. |
| 16 | edge-case-hunter №6 | medium | Одобрение публикует task до возможного отката аудита; тот же существующий долг ID 5. |
| 17 | edge-case-hunter №7 | medium | HTTP POST к переданной цели при меньшем занятом source получил lock_timeout вместо 404; R42.4-21. |
| 18 | edge-case-hunter №8 | low | Source.customer_code прочитан до блокировки, предупреждение может сравнить старое значение; редкая диагностика неизменённого общего метода, новая перечитка отклонена. |
| 19 | edge-case-hunter №9 | low | Пробельный ИНН источника может увести цель на резерв и сделать редирект недоступным; ранее принятый редкий исход, новая ветка отклонена. |
| 20 | edge-case-hunter №10 | medium | Доступ адресата к заявке не гарантирован; повтор существующего предусловия ID 7. |
| 21 | edge-case-hunter №11 | low | Выход Redis за диапазон требует отличной от штатной базовой DB при том же n; новый guard нестандартного запуска отклонён. |
| 22 | edge-case-hunter №12 | low | Модульный генератор допускает редкую коллизию; прежний риск, нового падения не наблюдалось. |
| 23 | edge-case-hunter №13 | medium | Предикат подтвердил блокировку на искусственной ошибке, не имеющей SQLSTATE NOWAIT; R42.4-22. |
| 24 | edge-case-hunter №14 | low | Исключение HTTP POST может обойти join; ранее рассмотренный редкий аварийный cleanup, новая обвязка отклонена. |
| 25 | edge-case-hunter №15 | low | У readiness-curl нет таймаута; зависший отвечающий backend в этом запуске не показан, дополнительные параметры ради редкого старта отклонены. |
| 26 | edge-case-hunter №16 | low | Backend может быть готов раньше nginx; ранее рассмотренный редкий стартовый тайминг, retry-обвязка без наблюдённого сбоя отклонена. |
| 27 | edge-case-hunter №17 | false | Secure-запрос без Referer действительно получает 403, но текущий CI caller использует development и не считает proxy-запрос secure; текущий сбой не возникает. |
| 28 | verification-gap №1 | medium | Тесты подстроки не защищают абсолютный href; filed evidence принят, defer существующего долга. |
| 29 | verification-gap №2 | medium | Тесты адресата письма и scoped-страницы не связаны; filed evidence принят, defer существующего долга. |
| 30 | verification-gap, дополнительное №1 | medium | Сигнал отправляет task до коммита внешней транзакции; подтверждено чтением, повтор ID 5 и 16. |
| 31 | acceptance-auditor №1 | low | Буквальный AC2 противоречит утверждённому исключению Task 3; реализация следует Task 3, исправление спецификации исключено. |
| 32 | acceptance-auditor №2 | low | Task 2 требует нового действия и expected_actions; отклонение описано, согласование AC12/Task 6 меняет спецификацию. |
| 33 | acceptance-auditor №3 | low | Runner-схема CI прямо описана и продолжает существующий job; перенос smoke в Compose ради буквального ограничения требует новой инфраструктуры без показанного сбоя. |

##### Отклонено — ревью на `956bb9c5` (18)

- ID 1 — false: текущий caller скрипта не распознаёт HTTPS на backend; middleware-контроль secure-запроса не доказывает падение development-smoke.
- ID 2 — low: воспроизведён ранее принятый редкий отказ аудита /admin/; не добавляется повторная атомарная обвязка.
- ID 8 — false: штатный run --rm не сохраняет /tmp между контейнерами; повторный dev-exec в одном контейнере не является доказанным дефектом стандартного запуска.
- ID 9 — low: предел n15 прямо обусловлен DB1; новая защита нестандартной конфигурации без штатного сбоя отклонена.
- ID 11 — low: тот же редкий неатомарный аудит /admin/, что ID 2; индивидуально проверен.
- ID 12 — low: ранее принятую редкую смену eligibility /admin/ перепроверили; дополнительная блокировка не превращена в новую задачу.
- ID 13 — low: ранее принятая редкая конкурентная разблокировка требует нового захвата и перечитки; повторная задача не создаётся.
- ID 18 — low: редкое устаревшее диагностическое предупреждение общего метода требует новой перечитки; не влияет на корректность переноса идентификаторов.
- ID 19 — low: ранее принятый редкий 404 после пробельного ИНН требует отдельной ветки редиректа.
- ID 21 — low: нестандартная Redis-база не соответствует основанию документированного предела; новый guard без наблюдённого штатного сбоя отклонён.
- ID 22 — low: редкая коллизия генератора уже рассмотрена, дополнительный распределитель без наблюдённого падения отклонён.
- ID 24 — low: редкий cleanup после аварийного POST уже рассмотрен; дополнительная ветка finally/join отклонена.
- ID 25 — low: зависание readiness-curl на ответе Django не наблюдалось; новые параметры для ранее принятого редкого стартового состояния отклонены.
- ID 26 — low: редкая гонка готовности nginx уже рассмотрена; новая retry-обвязка отклонена.
- ID 27 — false: воспроизведён отказ secure-CSRF, но фактический CI caller — development без SECURE_PROXY_SSL_HEADER; скрипт на production не запускается.
- ID 31 — low, правка спецификации: Task 3 явно требует исключения для роли unregistered; исправление AC2 не является patch кода.
- ID 32 — low, правка спецификации: добавление unblock_users требует корректного ожидания теста, отклонение уже объяснено.
- ID 33 — low: runner-схема описана и соответствует существующему job; новая Docker-инфраструктура без показанного runtime-сбоя не предлагается этим ревью.

#### Ревью 2026-10-14 — `b4fab053..35f8cc29`

Подтверждён весь диапазон: 36 файлов, +4286/−113, 5096 строк diff; режим `full`, включая реализацию, тесты, CI, инфраструктуру и документы. Текущие незакоммиченные правки этой истории и `sprint-status.yaml` исключены из diff, но текущая история использована как контекст. Все четыре настроенных слоя вернули результаты: `blind-hunter` — 10 замечаний, `edge-case-hunter` — 7, `verification-gap` — 3, `acceptance-auditor` — 3. У edge-case-hunter отсутствовали дополнительные reference-файлы проверки удалений и claims; слой использовал инструкции из доступного объединённого навыка. Каждое из 23 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 2 исправления пробелов регрессионных тестов, 4 отложенные группы (повторы существующего долга), 14 отклонённых замечаний. Дефект текущей реализации двумя новыми пунктами не заявляется. Код и постоянные тесты не менялись. Решение Alex 2026-10-14: вариант 2 — оставить R42.4-23 и R42.4-24 открытыми задачами в story, без исправлений тестов. Статус story и записи спринта: `review` → `in-progress` до закрытия этих задач.

**Исправления — пробелы проверок:**

- [x] [Review][Patch] **R42.4-23: повторная проверка принадлежности при блокировке цели привязки больше не защищена тестом** — `medium`, ID 18 (`verification-gap` №1). После исправления R42.4-21 `_lock_link_rows` проверяет цель предварительным `exists()`, затем scoped-запросом при захвате строки. В `test_link_rechecks_scope_under_lock`, `test_link_target_transferred_right_before_lock_answers_404_without_lock` и `test_link_to_transferred_client_skips_held_source_with_lower_pk` передача выполняется до входа в оригинальный `_lock_link_rows`: все три теперь получают 404 уже на предварительной проверке. Подмена scoped-захвата общим `User.objects.select_for_update(...)` оставит их зелёными, но разрешит привязку клиента, переданного между успешным `exists()` и блокировкой цели. Добавить двухсоединительную HTTP-проверку этого интервала с `prod_like_requests`: 404, назначение нового менеджера сохранено, привязки и AuditLog нет. Принято доказательство слоя verification-gap; новая мутация в этом запуске не выполнялась. [backend/apps/users/manager_admin.py:312-319; backend/tests/integration/test_manager_clients_section.py:1312-1336,1594-1670]
- [x] [Review][Patch] **R42.4-24: файловая изоляция воркеров xdist не защищена обязательной межпроцессной проверкой** — `medium`, ID 19 (`verification-gap` №2). Настройки разводят `MEDIA_ROOT`, `ONEC_PRIVATE_DIR`, каталоги обмена и логов по имени воркера, но существующий subprocess-тест наблюдает только Redis; тесты изоляции обмена подменяют каталоги через `tmp_path`. Замена сегмента `(_XDIST_WORKER or "main")` постоянным `"main"` оставляет последовательный CI и Redis-проверку зелёными, а параллельные воркеры смогут перезаписывать файлы друг друга. Добавить subprocess-проверку двух воркеров с настоящими тестовыми настройками: разные файловые корни, запись одинакового относительного имени через `FileStreamService` и сохранность содержимого каждого. Принято доказательство слоя verification-gap; мутация файловых настроек в этом запуске не выполнялась. [backend/freesport/settings/test.py:103-114; backend/tests/unit/test_xdist_redis_isolation.py:36-53,145-152; backend/apps/integrations/onec_exchange/file_service.py:158]

**Отложено — повторы существующих задач:**

- [x] [Review][Defer] **Разный порядок source/target у подтверждения и отдельной привязки** — `medium`, ID 3 и 11. Подтверждение держит target до запроса source, отдельная привязка с меньшим pk источника начинает с source. Порядок существовал в общих сервисах до baseline; новый runtime-deadlock здесь не воспроизводился. Сохранена исходная задача единого порядка и двухсоединительной проверки фактического цикла, без новой самостоятельной задачи. [backend/apps/users/manager_admin.py:277-283; backend/apps/users/services/verify_b2b_application.py:156-198]
- [x] [Review][Defer] **Порядок первой блокировки массового действия через exists** — `maybe-false`, возможный `medium`, ID 4. Действия вызывают exists до итерации упорядоченного queryset; снятие ORDER BY подтверждено предыдущей диагностикой, но реальный цикл двух действий здесь не показан. Сохранена исходная задача наблюдения первых захватов и deadlock либо исключения расписания. [backend/apps/users/manager_admin.py:321-331; backend/apps/users/admin.py:1196-1207,1251-1261]
- [x] [Review][Defer] **R42.4-D1: успешный HTTP-вход неактивного клиента** — `medium`, ID 7. Сериализатор принимает пароль неактивного клиента, view до JWT проверяет pending, но не is_active. Это существовавший до стори дефект; AC6 намеренно требует ModelBackend.authenticate. HTTP-вход здесь не воспроизводился, исходная задача остаётся единственной. [backend/apps/users/serializers.py:537-558; backend/apps/users/views/authentication.py:310-331]
- [x] [Review][Defer] **Полный URL и доступ фактического адресата регионального письма** — `medium`, ID 8, 15 и 20. Тесты проверяют подстроку пути либо только получателя, а задача выбирает адресата по региону, не текущему ручному назначению. Принято доказательство verification-gap отсутствия сквозной проверки фактической ссылки регионального и резервного получателя. Решение Alex о ручной очистке правил перед выкатом сохранено, новую самостоятельную задачу не создавать. Переход из письма здесь не выполнялся. [backend/apps/users/tasks.py:421-444; backend/tests/unit/test_region_routing.py:153-191]

**Проверки и ограничения:**

- Docker + PostgreSQL, один профильный прогон семи файлов: `test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_check_manager_route_script.py`, `test_xdist_redis_isolation.py`, `test_nginx_security_headers.py`, `test_region_routing.py`, `test_users_admin.py`, с `--override-ini=addopts= -q -p no:sugar` — **241 passed**, 6 предупреждений об устаревающих API, 258,90 с.
- Runtime-проверка development-настроек в Docker: `SECURE_PROXY_SSL_HEADER=None`, `RequestFactory().post(..., HTTP_X_FORWARDED_PROTO="https").is_secure() == False`. Поэтому отсутствие Referer не доказывает отказ текущего CI caller сессионного скрипта; production-настройки и production-вход этим не проверены.
- GitNexus остаётся `stale`: индекс `956bb9c5`, HEAD `35f8cc29`; после индекса менялись код и тесты. Пользователю предложено `! npx gitnexus analyze --skip-agents-md`. `detect-changes --scope all` — нет изменённых символов рабочего дерева; `--scope compare --base-ref b4fab053` — 36 файлов, 90 символов, 15 процессов, риск high; upstream `_lock_link_rows` — LOW, один вызывающий `_apply_link_1c_customer`. Результаты графа ограничены устаревшим индексом, не являются подтверждением актуального полного blast radius.
- Полный backend-набор, линтеры, новые мутации, живой nginx и production в этом запуске не проверялись. Код и постоянные тесты не правились; внешние письма не отправлялись.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | Фактический CI caller использует development без распознавания proxy-HTTPS; runtime is_secure=False, заявленный текущий CSRF-отказ не возникает. |
| 2 | blind-hunter №2 | low | Неатомарность save/аудита и гонка eligibility в /admin/ реальны, но ранее приняты как редкие; новая транзакционная обвязка отклонена. |
| 3 | blind-hunter №3 | medium | Target-first подтверждения против source-first отдельной привязки; существующий долг общих сервисов. |
| 4 | blind-hunter №4 | maybe-false | Предварительный exists не гарантирует первый pk; фактический deadlock не показан, существующий отложенный вопрос. |
| 5 | blind-hunter №5 | low | Изоляция учитывает один прогон; одновременные прогоны в том же compose-проекте запрещены, новая межзапусковая резервация Redis отклонена. |
| 6 | blind-hunter №6 | low | Корни постоянны в пределах контейнера; штатный run --rm не сохраняет /tmp между запусками, новая изоляция нестандартного повторного exec отклонена. |
| 7 | blind-hunter №7 | medium | API не проверяет is_active до JWT; повтор существующего R42.4-D1, AC6 корректен. |
| 8 | blind-hunter №8 | medium | Подстрока пути не подтверждает полный URL и доступ адресата; существующая задача письма. |
| 9 | blind-hunter №9 | false | Замечание относится к зафиксированному отчёту прошлого ревью; текущие незакоммиченные документы уже отмечают R42.4-21/22 закрытыми и статус review. |
| 10 | blind-hunter №10 | low | Дополнительных негативов самого session-скрипта нет; Cookie/Set-Cookie проверяет nginx-smoke, текущий обход не показан, расширение матрицы отклонено. |
| 11 | edge-case-hunter №1 | medium | Тот же существующий source/target-долг, что ID 3; новый runtime-deadlock не выполнялся. |
| 12 | edge-case-hunter №2 | low | Save до AuditLog в /admin/ допускает ранее принятый редкий сбой INSERT; новая обвязка отклонена. |
| 13 | edge-case-hunter №3 | low | Два конкурентных запроса /admin/ могут дать два события; ранее принятая редкая гонка, новая блокировка отклонена. |
| 14 | edge-case-hunter №4 | low | Подтверждение после редкого ухода по пробельному ИНН может дать недоступный редирект; ранее принятая новая условная ветка отклонена. |
| 15 | edge-case-hunter №5 | medium | Региональный получатель может не отвечать за вручную переданную заявку; существующий долг писем, политика не пересматривается. |
| 16 | edge-case-hunter №6 | low | Остаток unique_digits допускает редкую коллизию; нового падения не наблюдалось, дополнительный распределитель отклонён. |
| 17 | edge-case-hunter №7 | low | DB16 требует нестандартной базовой DB15; штатный compose использует DB1, которой обусловлен предел n15; новый конфигурационный guard отклонён. |
| 18 | verification-gap №1 | medium | Успешный предварительный exists и последующая передача не покрыты; filed evidence принят, R42.4-23. |
| 19 | verification-gap №2 | medium | Постоянный файловый сегмент воркера не обнаружит Redis-тест и последовательный CI; filed evidence принят, R42.4-24. |
| 20 | verification-gap №3 | medium | Фактический полный URL и переход адресата не проверяются; filed evidence принят, существующий defer. |
| 21 | acceptance-auditor №1 | low | Буквальный AC2 расходится с явным исключением Task 3; исправление самой спецификации исключено. |
| 22 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового expected_actions; отклонение описано, согласование AC12/Task 6 — правка спецификации. |
| 23 | acceptance-auditor №3 | low | Runner-схема CI описана и продолжает существующий job; новая Compose-инфраструктура без показанного сбоя отклонена. |

##### Отклонено — ревью на `35f8cc29` (14)

- ID 1 — false: фактические development-настройки не считают proxy-запрос HTTPS; отказ текущего caller не подтверждается.
- ID 2 — low: редкие неатомарный аудит и конкурентная смена eligibility /admin/ ранее приняты; новая обвязка отклонена.
- ID 5 — low: одновременные прогоны в одном compose-проекте запрещены; новая межзапусковая резервация не исправляет штатный сценарий.
- ID 6 — low: run --rm удаляет файловую среду контейнера; дополнительная изоляция повторного exec не требуется показанным штатным запуском.
- ID 9 — false: текущие пользовательские правки уже фиксируют закрытие R42.4-21/22 и review; не заменять их историческим коммитным отчётом.
- ID 10 — low: конкретного ошибочно успешного session-скрипта не показано; дополнительная матрица расширяет проверки без доказанного дефекта.
- ID 12 — low: ранее принятый редкий save без аудита /admin/; новая транзакционная обвязка отклонена.
- ID 13 — low: ранее принятая редкая конкурентная разблокировка /admin/; новая дедупликационная блокировка отклонена.
- ID 14 — low: ранее принятый редкий недоступный редирект после переноса пробельного ИНН; отдельная новая ветка отклонена.
- ID 16 — low: ранее принятая редкая коллизия генератора; дополнительный распределитель без наблюдённого сбоя отклонён.
- ID 17 — low: нестандартная базовая DB15 не соответствует основанию документированного предела; новый guard без штатного сбоя отклонён.
- ID 21 — low, правка спецификации: реализация выполняет исключение Task 3; согласование AC2 не является patch кода.
- ID 22 — low, правка спецификации: новое действие требует корректного expected_actions; причина уже документирована.
- ID 23 — low: новая Compose-инфраструктура ради буквального ограничения не является коррекцией показанного runtime-сбоя существующей runner-схемы.

#### Ревью 2026-10-14 — `b4fab053..baa78940`, код раздела и deployment-проверки

Решение Alex 2026-10-14: вариант 2 — оставить R42.4-25 открытой задачей в истории, без исправлений кода и тестов. Статус истории и запись `42-4-manager-section-own-clients` в трекере спринта: `review` → `in-progress` до закрытия этой задачи.

Согласованный первый проход: 22 файла, +2890/−18, режим `full`. Включены код раздела менеджера, его тесты, Nginx и `scripts/deploy/`, подключение анонимной проверки в `deploy.yml`. Ускорение тестов/CI и документы/настройки исключены из самостоятельного ревью; `main.yml` прочитан как фактический caller HTTP-скриптов. Эти оставшиеся группы требуют отдельных проходов, данное ревью их не закрывает.

Все четыре настроенных слоя завершились: blind-hunter — 10 замечаний, edge-case-hunter — 7, verification-gap — один пробел и два дополнительных замечания, acceptance-auditor — 2. Каждое из 22 замечаний получило индивидуальный вердикт до группировки. Итог: 0 решений, 1 исправление тестового пробела, 4 отложенные группы (повторы существующего долга), 12 отклонённых замечаний. Новый подтверждённый дефект реализации не выявлен; найден незакреплённый потребитель нового действия.

**Исправление:**

- [x] [Review][Patch] **R42.4-25: разблокировка не проверена вместе с API-входом портала** — `medium`, ID 9 и 18 (blind-hunter №9 + verification-gap №1). `TestUnblock.test_unblock_restores_login` проверяет Django `authenticate()`, но `/api/v1/auth/login/` использует `UserLoginSerializer` и отдельную проверку `verification_status="pending"`, а не этот backend. Filed evidence verification-gap принят: если новое действие начнёт сохранять pending вместе с активностью, существующие проверки активности, пароля и аудита пройдут, а вход того же клиента на портал ответит 403. Дополнить текущий тест HTTP-входом после действия с проверкой успешного ответа, access/refresh и сохранённого статуса верификации. Это пробел регрессии связки нового действия с потребителем, не нарушение явно выбранного AC6 и не новая задача запрета входа неактивному клиенту (существующий R42.4-D1). Мутация и API-вход в этом запуске не выполнялись. [backend/tests/integration/test_manager_clients_section.py:720-730; backend/apps/users/admin.py:1281-1283; backend/apps/users/views/authentication.py:305-331]

**Отложено — повторы существующих задач, без новых самостоятельных пунктов:**

- [x] [Review][Defer] **Порядок блокировок смешанной массовой разблокировки** — `maybe-false`, возможный `medium`, ID 3 и 11. До итерации непредварительных заявок действие выполняет exists и отдельную выборку pending; один ORDER BY переданного queryset не устанавливает общий порядок всех захватов. Возможное расписание: первый запрос держит pending с большим pk, второй держит непредварительного клиента меньшего pk и ждёт pending, первый ждёт меньший pk. Фактический цикл двух запросов в этом запуске не воспроизводился; это уточнение существующей задачи первых блокировок массового действия. Для подтверждения наблюдать первые захваты и цикл ожидания PostgreSQL, для исправления оценить материализацию всего разрешённого выбранного набора в одном порядке. [backend/apps/users/manager_admin.py:321-331; backend/apps/users/admin.py:1251-1281]
- [x] [Review][Defer] **Разный порядок source/target у подтверждения и привязки** — `medium`, ID 4 и 12. Общий сервис подтверждения удерживает target, затем вызывает привязку по pk; отдельная привязка при меньшем source начинает с source. Причина существовала до baseline, конкурентный deadlock здесь не запускался. Исходная задача единого порядка общих сервисов сохранена. [backend/apps/users/manager_admin.py:277-283,285-319; backend/apps/users/services/verify_b2b_application.py:156-198]
- [x] [Review][Defer] **Письмо об одобрении переживает откат заявки** — `medium`, ID 15. Общий сигнал вызывает send_user_verified_email.delay до коммита внешней транзакции, поэтому ошибка аудита после save может отменить подтверждение, но не публикацию письма. Причина существовала до baseline; это повтор уже воспроизведённого ранее долга transaction.on_commit. В данном запуске публикация и внешняя отправка не выполнялись. [backend/apps/users/signals.py:31-47; backend/apps/users/manager_admin.py:330-331]
- [x] [Review][Defer] **Региональный адресат может не открыть ссылку письма** — `medium`, ID 10, 16 и 19. Правила поддерживают manager_email без связанной учётной записи; получатель может быть суперпользователем либо не отвечать за заявку. Письмо ведёт в раздел, где нужны членство и scoped-доступ. Повтор существующего конфигурационного долга; решение Alex о ручной очистке правил перед выкатом и исходная задача сквозного перехода фактического адресата сохранены. Переход здесь не выполнялся. [backend/apps/users/services/region_routing.py:61-69; backend/apps/users/tasks.py:440-444; backend/apps/users/manager_admin.py:34-44]

**Проверки и границы:**

- Docker + PostgreSQL, последовательный прогон шести файлов: test_manager_clients_section.py, test_manager_admin_site.py, test_check_manager_route_script.py, test_nginx_security_headers.py, test_region_routing.py, test_users_admin.py; `--override-ini=addopts= -q -p no:sugar` — **221 passed**, 6 предупреждений об устаревающих API, 246,17 с. Полный backend-прогон, линтеры и реальный nginx в этом ревью не запускались.
- GitNexus актуален на baa78940. `detect-changes --scope all` — нет незакоммиченных изменений; `--scope compare --base-ref b4fab053` — 37 файлов, 90 символов, 15 процессов, риск high для полного диапазона (не только согласованной группы). `impact response_action` и impact manager-реализации verify_b2b_view — LOW, прямых вызывающих граф не показывает; динамические admin-вызовы этим не исключаются.
- Код приложения и постоянные тесты не менялись. Записаны только результаты ревью в story и deferred-work. Статус до решения Alex не изменён.

**Индивидуальные вердикты до группировки:**

| ID | Источник | Вердикт | Доказательство / исход |
|---|---|---|---|
| 1 | blind-hunter №1 | false | Редактируемый is_active для pending прямо разрешён решениями 7/8; ограничение действия не относится к карточке, API отдельно запрещает pending. |
| 2 | blind-hunter №2 | low | Неатомарный save/аудит в /admin/ реален, но редкий отказ INSERT ранее принят; новая транзакционная обвязка отклонена. |
| 3 | blind-hunter №3 | maybe-false | Pending читаются перед остальными клиентами, глобальный порядок не гарантирован; фактический цикл не показан, defer существующего вопроса. |
| 4 | blind-hunter №4 | medium | Общие сервисы удерживают source/target в несовместимом порядке; повтор существующего долга, нового deadlock-прогона нет. |
| 5 | blind-hunter №5 | low | Перенос нормализованного ИНН может сделать редирект недоступным; ранее принятый редкий исход, новая условная ветка отклонена. |
| 6 | blind-hunter №6 | false | Caller — main.yml с development без SECURE_PROXY_SSL_HEADER; Django за nginx не считает запрос secure, заявленный текущий CSRF-отказ не возникает. |
| 7 | blind-hunter №7 | false | main.yml:269-275 реально вызывает оба скрипта для http и https; отсутствие caller в суженном diff не доказывает отсутствия подключения. |
| 8 | blind-hunter №8 | false | При отсутствующих скриптах/bash/curl обязательный CI напрямую вызывает оба shell-скрипта и падает; skip модульного теста не делает весь CI ошибочно зелёным. |
| 9 | blind-hunter №9 | medium | Authenticate не исполняет реальный API-потребитель нового действия; R42.4-25. |
| 10 | blind-hunter №10 | medium | Правило может адресовать письмо сотруднику вне scope либо адресу без доступа; повтор долга конфигурации/сквозного теста. |
| 11 | edge-case-hunter №1 | maybe-false | Mixed pending/non-pending допускают несовместимые предварительные захваты, фактический deadlock не воспроизведён; тот же долг ID 3. |
| 12 | edge-case-hunter №2 | medium | Target-first подтверждения и source-first отдельной привязки — тот же существующий долг ID 4. |
| 13 | edge-case-hunter №3 | low | Eligibility в /admin/ может измениться между чтением и save; ранее принятая редкая гонка, новая блокировка отклонена. |
| 14 | edge-case-hunter №4 | low | Save может сохраниться без аудита в /admin/ при отказе INSERT; тот же ранее принятый редкий исход ID 2. |
| 15 | edge-case-hunter №5 | medium | Сигнал публикует task до возможного rollback внешней транзакции; повтор существующего долга. |
| 16 | edge-case-hunter №6 | medium | manager_email/региональный адресат не гарантирует вход и scope; тот же существующий долг ID 10. |
| 17 | edge-case-hunter №7 | low | Пробельный ИНН при подтверждении может переназначить цель и дать 404 после редиректа; тот же ранее принятый редкий исход ID 5. |
| 18 | verification-gap №1 | medium | Filed evidence принят: изменение verification_status действием сломает API-вход, но не текущий authenticate-тест; R42.4-25. |
| 19 | verification-gap, дополнительное №1 | medium | Суперпользователь по адресу резервного правила не войдёт в manager_site; повтор исходного конфигурационного долга ID 10/16. |
| 20 | verification-gap, дополнительное №2 | low | /admin/ не объединяет save и аудит транзакцией; тот же принятый редкий риск ID 2/14. |
| 21 | acceptance-auditor №1 | low | Буквальный AC2 расходится с утверждённым исключением Task 3; реализация следует Task 3, правка спецификации исключена. |
| 22 | acceptance-auditor №2 | low | Task 2 требует unblock_users и нового expected_actions; отклонение документировано, исправление AC12/Task 6 меняет спецификацию. |

**Отклонено (12):**

- ID 1 — false: карточка намеренно разрешает правку активности независимо от ограничения массового действия.
- ID 2 — low: редкий сбой аудита /admin/ уже принят; новая атомарная граница отклонена.
- ID 5 — low: ранее принятый редкий редирект после переноса ИНН; новая ветка отклонена.
- ID 6 — false: фактический CI caller использует development и не распознаёт secure proxy-запрос.
- ID 7 — false: оба скрипта подключены в main.yml для обоих конфигов nginx.
- ID 8 — false: отсутствие зависимости не скрывается всем CI — обязательный прямой запуск скриптов завершается ошибкой.
- ID 13 — low: ранее принятая редкая гонка eligibility /admin/, дополнительная блокировка отклонена.
- ID 14 — low: ранее принятый редкий INSERT-аудит, как ID 2.
- ID 17 — low: ранее принятый узкий редирект на уже недоступного клиента, как ID 5.
- ID 20 — low: ранее принятый редкий неатомарный save/аудит, как ID 2/14.
- ID 21 — low, правка спецификации: код соответствует утверждённому Task 3.
- ID 22 — low, правка спецификации: корректное ожидание нового действия обязательно по Task 2.

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
- **Исправления повторного ревью (2026-10-13, ID 5–7).** В `test_manager_clients_section.py` добавлены хелперы `make_company`, `make_address`, `related_snapshot`, `inline_prefixes`, `form_index` и тесты: `TestClientInlines::test_own_company_and_addresses_are_saved` (правка реквизитов и адреса, удаление и добавление адреса своего клиента), `TestClientInlines::test_forged_foreign_inline_ids_change_nothing[change|delete]` (ID записей чужого клиента в формах своего: правка даёт 200 с ошибкой формы, удаление — пропуск; записи чужого не меняются), `TestViewOnlyPermissions::test_card_post_is_forbidden` (форма снята при полных правах, POST при одном `view_user` — 403, клиент, Company, адреса, `AuditLog` и `LogEntry` без изменений). В `TestChangelistQueryCount` все 50 строк — заявки с кандидатом 1С, плюс проверка `_has_1c_candidate` у каждой строки. Фикстура `view_only_group` теперь возвращает группу и оба набора прав. Мутации (файл восстанавливался `git checkout`): `has_change_permission` → `True` в `ManagerClientAdmin` — упал `test_card_post_is_forbidden`; запрос `User.objects…exists()` в `has_1c_candidate` для строк с кандидатом — упал `TestChangelistQueryCount`; `inlines = [CompanyInline]` — упали 3 теста `TestClientInlines`. Отказ подмены ID инлайна обеспечивает queryset формсета Django (`BaseInlineFormSet` фильтрует по родителю), отдельной защиты в коде раздела нет, поэтому для этого теста мутации нет. Тесты карточки, инлайнов, прав и списка — 15 passed; `black --check`, `flake8`, `mypy` по файлу чисты. Полный прогон после исправлений (`freesport-test`, без параллельных): `4143 passed, 76 skipped` за 42:05.
- **Исправления третьего ревью (2026-10-13, ID 20–21).** В `test_manager_clients_section.py` — фикстуры `section_member` (параметр по группам «Менеджеры» и «Руководители», id `manager`/`supervisor`) и `section_client`; на них переведены `TestChangelist::test_search_finds_only_own_clients` и `TestForeignClient::test_direct_urls_answer_404`. Во втором добавлен свой клиент-заявка: его карточка, история, `verify` и `password` отвечают 200 — контроль, что 404 у чужого не от отказа во входе. В `test_nginx_security_headers.py` — `TestManagerSectionRoute::test_manager_location_proxies_to_backend[default.conf|local.conf]`: каждый экземпляр `location /manager/` вне исключённых vhost'ов проксирует ровно в `http://backend`. Мутации (файлы восстановлены копией): в `scope_clients` руководителю весь queryset (`if groups.filter(name="Руководители").exists(): return queryset.exclude(staff_accounts_q())`) — упали `test_search_finds_only_own_clients[supervisor]` и `test_direct_urls_answer_404[supervisor]`, варианты `manager` прошли; `proxy_pass http://frontend` в `/manager/` обоих конфигов — упали оба параметра нового nginx-теста. Файлы тестов раздела и nginx — 88 passed; `black --check`, `flake8`, `mypy` по двум файлам чисты. Живая проверка через dev-nginx: сначала 502 — nginx держал старый IP upstream после перезапуска backend (memory), после `restart nginx` `curl -sI http://localhost/manager/` → `302`, `Location: /manager/login/?next=/manager/`, `/manager/login/` → 200. Полный прогон (`freesport-test`, без параллельных): `4147 passed, 76 skipped` за 52:30. GitNexus: индекс `c2743ed` (stale на тестовый коммит), тестовые классы в графе отсутствуют, `detect-changes --scope all` — изменённых символов нет; продакшен-код не менялся.
- **Исправления ревью `b4fab053..7728a9c8` (2026-10-14, R42.4-1…3).** Ветка `fix/42-4-review-r1-r3` от `develop` (`7728a9c8`). GitNexus актуален на `7728a9c`; `impact --direction upstream`: `ManagerClientAdmin` и `PortalAccountFilter` — LOW, по 1 прямому (импорт в `apps.py`); `UserAdmin` не менялся. RED: 7 новых тестов падали на исходном коде (карточка после передачи отвечала 302 и возвращала ответственного A; строка ни в карточке, ни в действиях не заблокирована; фильтр выделял «Есть»). Тесты R42.4-1 идут с фикстурой `prod_like_requests` (`ATOMIC_REQUESTS=False`, как на production; в `settings/test.py` он `True`), передачу клиента и пробу блокировки (`FOR UPDATE NOWAIT`) выполняют из второго соединения в отдельном потоке. Мутации (файл восстанавливался копией):

  | Убрано | Результат |
  |---|---|
  | `select_for_update` в проверке `save_model` | упал `test_card_save_holds_row_lock` |
  | проверка принадлежности в `save_model` | упали `test_card_save_after_transfer_answers_404` и `test_card_save_holds_row_lock` |
  | `select_for_update` в `response_action` | упали 4 параметра `test_actions_hold_row_lock` |
  | `transaction.atomic()` в `response_action` | 500 `TransactionManagementError`, упали 4 параметра `test_actions_hold_row_lock` |
  | `effective_value()` в `choices` | упал `test_role_filter_unregistered_selects_all` |

  Обход блокировки для `link_1c_customer` тестом не закреплён: порядок блокировок проверяется только конкурентным расписанием (см. отложенный ID 16). Файлы раздела — 83 passed. HTTP-проверка `deploy.yml` выполнена фрагментом из YAML локально: `PRODUCTION_URL=http://localhost` (dev-nginx) — ✅, `http://localhost:3000` (Next напрямую) — exit 1, «получено 308 /manager». Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4119 passed, 76 skipped` за 13:26. После него: `black --check .` — 466 unchanged (до этого black переформатировал одну длинную строку нового теста), `flake8` чист, `mypy` — «no issues found in 619 source files», `makemigrations --check` — No changes detected. `detect-changes --scope all`: 7 символов, все в `manager_admin.py` (`list_display` и `response_change` — сдвиг строк), риск low, затронутых процессов 0.
- **Исправления ревью `b4fab053..220766c3` (2026-10-14, R42.4-4…8).** Ветка `fix/42-4-review-r1-r3` (коммит `220766c3` ещё не в `develop`). GitNexus актуален на `220766c`; `impact --direction upstream`: `ManagerClientAdmin` и `PortalAccountFilter` — LOW, по 1 прямому (импорт в `apps.py`). Общий `UserAdmin` и сервисы не менялись. RED: 7 новых проверок падали на исходном коде — запись из второго соединения не ждала блокировку (карточка, пароль, подтверждение, отказ), привязка после передачи ответила 302 и выполнилась, при двух полях `action` строка не заблокирована, переход по «Есть» выделил «Все». Конкурентные тесты (`BackgroundWrite`) запускают запись из второго соединения посреди запроса раздела и ждут, пока она завершится или встанет в очередь на блокировку (`pg_stat_activity.wait_event_type = 'Lock'`), без задержек по времени. `test_card_save_after_transfer_answers_404` переписан: передача теперь до отправки формы — посреди записи она ждёт блокировку. Мутации (файл восстанавливался копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | `_lock_rows` в `change_view` | упали `test_card_keeps_concurrent_import`, `test_card_save_holds_row_lock` |
  | `_lock_rows` в `user_change_password` | упал `test_password_change_does_not_undo_transfer` |
  | `_lock_rows` в `verify_b2b_view` | упали оба параметра `test_verify_page_waits_for_transfer` |
  | проверка принадлежности в `_apply_link_1c_customer` | упал `test_link_after_transfer_answers_404` |
  | `_executed_action` → `in getlist("action")` | упал `test_second_action_field_does_not_skip_lock` |
  | явное `portal_account=yes` у «Есть» | упал `test_have_account_link_keeps_its_choice` |

  Файлы раздела и смежные (`test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_users_admin.py`, `test_admin_link_1c_customer.py`, `test_admin_verify_b2b_application.py`, `test_admin_user_password.py`, `test_responsible_manager_events.py`) — 249 passed.
- **Исправление ревью `b4fab053..63cd2959` (2026-10-14, R42.4-9).** Ветка `fix/42-4-review-r1-r3` (HEAD `63cd2959`). GitNexus актуален на `63cd295`; `impact _lock_rows --direction upstream` — **HIGH**: 4 прямых вызывающих (`change_view`, `user_change_password`, `verify_b2b_view`, `_apply_link_1c_customer`), 3 процесса, все в `manager_admin.py`. Сам `_lock_rows` по смыслу не менялся, три пути переведены на новый `_lock_client`, `/admin/` не затронут. RED: 8 новых проверок `TestNoLockWithoutAccess` (строку клиента держит второе соединение, у соединения теста `lock_timeout = 2s`) — все 8 упали с «canceling statement due to lock timeout». Мутации (файл восстанавливался копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | выборка раздела в `_lock_client` (`User.objects` вместо `get_queryset`) | упали 4 параметра `test_foreign_client_answers_404_without_lock` |
  | проверка `has_change_permission` в `_lock_client` | упали 4 параметра `test_view_only_answers_403_without_lock` |
  | блокировка в `_lock_client` целиком | упали `test_card_keeps_concurrent_import`, `test_password_change_does_not_undo_transfer`, оба `test_verify_page_waits_for_transfer`, `test_card_save_holds_row_lock` |

  Файлы раздела и смежные (`test_manager_clients_section.py`, `test_manager_admin_site.py`, `test_users_admin.py`, `test_admin_link_1c_customer.py`) — 164 passed. Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4135 passed, 76 skipped` за 14:57. После него в `freesport-test`: `black --check .` — 466 unchanged, `flake8` чист, `mypy` — «no issues found in 619 source files», `makemigrations --check` — No changes detected. `detect-changes --scope all`: 9 символов, все в `manager_admin.py` (`response_action`, `_executed_action`, `_apply_link_1c_customer` — сдвиг строк), риск low, затронутых процессов 0.
- **Исправления ревью `b4fab053..ac631c09` (2026-10-14, R42.4-10…13).** Ветка `fix/42-4-review-r10-r13` от `develop` (`a201feb1`, PR #308 слит). GitNexus — индекс `ac631c0`, отстаёт только на merge-коммит без изменений кода, переиндексация не нужна; `impact _lock_client --direction upstream` — **HIGH**: 3 прямых вызывающих (`change_view`, `user_change_password`, `verify_b2b_view`), 3 процесса, все в `manager_admin.py`; `_apply_link_1c_customer` неоднозначен (есть в `UserAdmin` и `ManagerClientAdmin`), версию раздела зовёт только действие `link_1c_customer`. RED: 5 новых проверок падали на исходном коде — `test_client_assigned_after_empty_lock_answers_404` (карточка 200, пароль, подтверждение и отказ 302 по незаблокированной строке) и `test_link_to_transferred_client_answers_404_without_lock` (`canceling statement due to lock timeout`). Стражи `test_link_rechecks_scope_under_lock` и `test_link_locks_source_and_target_in_pk_order` зелёные на исходном коде, как и положено стражам корректной реализации. Мутации (файл восстанавливался копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | 404 на пустую блокировку в `_lock_client` | упали 4 параметра `test_client_assigned_after_empty_lock_answers_404` |
  | проверка принадлежности цели до `_lock_rows` в привязке | упал `test_link_to_transferred_client_answers_404_without_lock` |
  | перепроверка принадлежности под блокировкой в привязке | упал `test_link_rechecks_scope_under_lock` |
  | совместная блокировка → `_lock_rows(target)`, затем `_lock_rows(source)` | упал `test_link_locks_source_and_target_in_pk_order` — `DeadlockDetected` |
  | исключение привязки в `response_action` (цель блокируется действием заранее) | упал `test_link_locks_source_and_target_in_pk_order` |

  R42.4-13: шаг `main.yml` воспроизведён локально тем же способом — Django с `freesport.settings.development` в `freesport-test` на порту 8000, `nginx:alpine` с `local.conf` и `--add-host backend:host-gateway` → `✅ Раздел менеджера проксируется в Django`. Мутации копии `local.conf`: `rewrite ^/manager/(.*)$ /admin/$1 break;` — скрипт упал «получено 302 /admin/login/?next=/admin/»; `proxy_pass http://frontend` — «получено 308 /manager». Файлы раздела — 106 passed. Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4142 passed, 76 skipped` за 15:33. После него в `freesport-test`: `black --check .` — 466 unchanged (black убрал одну лишнюю пустую строку нового теста), `flake8` чист, `mypy` — «no issues found in 619 source files», `makemigrations --check` — No changes detected; `bash -n` скрипта и разбор YAML обоих workflow — ok. `detect-changes --scope all`: 6 символов, все в `manager_admin.py` (`_executed_action`, `response_action`, `pk` — сдвиг строк), риск medium, 5 процессов через `_lock_client`.
- **Исправления ревью `b4fab053..741ce342` (2026-10-14, R42.4-14…16).** Ветка `fix/42-4-review-r10-r13` (HEAD `741ce342`, ещё не опубликован). GitNexus актуален на `741ce34`; у `ManagerClientAdmin._apply_link_1c_customer` прямых вызывающих в графе нет (его зовёт действие `link_1c_customer` через `self`), риск LOW, `/admin/` не затронут. R42.4-14: захват строк привязки вынесен в `_lock_link_rows` (сначала без смены поведения — шов для теста). RED: `TestNoLockWithoutAccess::test_link_target_transferred_right_before_lock_answers_404_without_lock` (передача прямо перед захватом, строку цели держит второе соединение) упал с `LockNotAvailable: canceling statement due to lock timeout`. R42.4-15: RED — `test_check_manager_route_script.py` против локального `ThreadingHTTPServer`: на `login-body-truncated`, `login-302-with-form` и `redirect-truncated` скрипт завершался с exit 0. Мутации (файл восстанавливался копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | захват цели выборкой раздела → `_lock_rows(target, …)` и перепроверка после (поведение до исправления) | упал `test_link_target_transferred_right_before_lock_answers_404_without_lock` — lock timeout |
  | 404 на пустой захват цели в `_lock_link_rows` | упали `test_link_rechecks_scope_under_lock` и новый тест R42.4-14 |
  | порядок по pk → цель раньше источника | упал `test_link_locks_source_and_target_in_pk_order` — `DeadlockDetected` |
  | `proxy_set_header Cookie "";` в `location /manager/` копии `local.conf` | `check-manager-route.sh` — ✅, `check-manager-session.sh` — «Вход в /manager/: ожидался 302 на /manager/, получено 403» |
  | `proxy_hide_header Set-Cookie;` там же | то же: анонимная проверка ✅, вход — 403 |

  R42.4-16 воспроизведён по шагу `main.yml`: база `smoke_manager` в `freesport-test-db`, `migrate` (26 с), засев — тот же Python-фрагмент, извлечённый из YAML шага, Django с `freesport.settings.development` на порту 8000, `nginx:alpine` с настоящим `local.conf` и `--add-host backend:host-gateway`. Скрипты запускались из образа `freesport-test-backend` в сетевом пространстве nginx (`--network container:nginx-smoke`, `http://localhost`). Из Git Bash под Windows так нельзя: MSYS переписывает аргумент `next=/manager/` в путь `C:/Program Files/Git/manager/` (Django отбрасывает его как небезопасный и уводит на `/accounts/profile/`), а с `MSYS_NO_PATHCONV=1` `curl.exe` не может писать в POSIX-путь от `mktemp`. На Linux-раннере нет ни того, ни другого. Итог: обе проверки ✅; негативы скрипта — переставленные свой и чужой клиент, неверный пароль — exit 1. Стенд и база `smoke_manager` удалены. Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4150 passed, 76 skipped` за 17:15. Первые линтеры после него подхватили `scripts/docs/*.py` через новое монтирование `../scripts:/app/scripts` (black — 5 файлов, flake8 и mypy — ошибки только в `scripts/docs/`), поэтому монтирование сужено до `../scripts/deploy`. После этого в `freesport-test`: `black --check .` — 467 unchanged, `flake8` чист, `mypy` — «no issues found in 620 source files», `makemigrations --check` — No changes detected; сторожа compose и workflow (`test_check_manager_route_script.py`, `test_nginx_security_headers.py`, `test_pytest_marker_autotagging.py`, `test_pages_performance.py`) — 158 passed; `bash -n` обоих скриптов и разбор YAML `main.yml` — ok. `detect-changes --scope all`: 3 символа в `manager_admin.py` (`ManagerClientAdmin`, `_apply_link_1c_customer`, `response_action` — сдвиг строк), риск low, затронутых процессов 0.
- **Исправления ревью `b4fab053..d9f21c20` (2026-10-14, R42.4-17…18).** Ветка `fix/42-4-review-r10-r13` (HEAD `d9f21c20`, не опубликован). GitNexus актуален на `d9f21c2`; продакшен-код не менялся, `detect-changes --scope all` — изменённых символов нет. R42.4-17: шаг `main.yml` «Маршрут /manager/ через nginx (local.conf и default.conf)» поднимает второй nginx с production `default.conf` без правок (порт 8443:443); по пути Let's Encrypt лежит самоподписанный сертификат на localhost (`openssl req -x509`, SAN `DNS:localhost`), curl доверяет ему через `CURL_CA_BUNDLE`. Обе проверки (`check-manager-route.sh` и `check-manager-session.sh`) идут по `http://localhost:8080` и `https://localhost:8443`, при провале — логи runserver и обоих nginx. Воспроизведено локально тем же способом, что R42.4-16: база `smoke_manager` в `freesport-test-db`, засев — Python-фрагмент, извлечённый из YAML шага, Django с `freesport.settings.development` на порту 8000, `nginx:alpine` с настоящим `default.conf` и сертификатом, скрипты — из образа `freesport-test-backend` в сетевом пространстве nginx с `CURL_CA_BUNDLE`. Итог на `default.conf`: обе проверки ✅, переставленные свой и чужой клиент — exit 1; без `CURL_CA_BUNDLE` — `curl: (60) self-signed certificate`, то есть запрос шёл по TLS. `local.conf` с новым монтированием — обе ✅. Мутации копии `default.conf` (только `location /manager/`):

  | Убрано / добавлено | Результат |
  |---|---|
  | `proxy_hide_header Set-Cookie;` | `check-manager-route.sh` — ✅, `check-manager-session.sh` — «Вход в /manager/: ожидался 302 на /manager/, получено 403» |
  | `proxy_set_header Cookie "";` | то же: анонимная проверка ✅, вход — 403 |

  YAML `main.yml` разобран, `bash -n` блока шага и обоих скриптов — ok. Стенд и база удалены. R42.4-18: `tests/unit/test_xdist_redis_isolation.py` запускает три дочерних процесса с `freesport.settings.test` и `PYTEST_XDIST_WORKER=gw0`/`gw1`, `REDIS_URL` с базой 12 (не база текущего прогона: очистка `gw0` с настоящей базой стёрла бы данные живого воркера параллельного прогона). Проверяет БД 12 и 13, контрольные значения обоих, очистку `gw0` и сохранность значения `gw1`; в `finally` чистит базу 13. Мутации `settings/test.py` (восстановлен копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | `_WORKER_INDEX = 0` | упал `test_workers_do_not_clear_each_other` — `assert 12 == (12 + 1)` |
  | переопределение `CACHES["default"]["LOCATION"]` | то же |
  | `_WORKER_INDEX = 0` и в тесте убраны проверки номеров БД | упал на «cache.clear() воркера gw0 удалил значение воркера gw1» — проверка очистки ловит общую БД сама |

  Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4151 passed, 76 skipped` за 15:55. После него в `freesport-test`: `black --check .` — 468 unchanged, `flake8` чист, `mypy` — «no issues found in 621 source files».
- **Исправления ревью `b4fab053..46ff9a6e` (2026-10-14, R42.4-19…20).** Ветка `fix/42-4-review-r10-r13` (HEAD `46ff9a6e`). GitNexus актуален на `46ff9a6`; менялись только два тестовых файла, `detect-changes --scope all` — изменённых символов нет. R42.4-19, RED: текущий выбор DB 12/13 вынесен в `probe_dbs` без смены поведения, новый `test_probe_never_touches_active_workers` упал на 14 базовых номерах из 16, включая штатную базу 1 (при `-n` 12…15 проба задевает живых воркеров). GREEN: `active_dbs()` + `probe_dbs()` — две старшие свободные БД. Под xdist: `-n 14` — 17 passed (проба на DB 0 и 15, второй воркер пробы `gw15`), `-n 15` — тест пропущен с причиной «воркеры занимают range(1, 16)», FLUSHDB не выполнялся. R42.4-20: страж корректной проверки скрипта, на исходном скрипте оба новых теста зелёные. Мутации (файл восстанавливался копией, сверка `cmp`):

  | Убрано | Результат |
  |---|---|
  | проверка `FOREIGN_EMAIL` в `check-manager-session.sh` | упал `test_session_with_foreign_client_fails` |
  | `_WORKER_INDEX = 0` в `settings/test.py` | упал `test_workers_do_not_clear_each_other` |
  | число воркеров в `active_dbs` (всегда одна БД) | упали `test_active_dbs_cover_all_workers[gw0-of-4|gw3-of-12]` |
  | `probe_dbs` → фиксированные `(12, 13)` | упали 14 параметров `test_probe_never_touches_active_workers` |

  Оба файла — 29 passed. Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4172 passed, 76 skipped` за 15:16. После него в `freesport-test`: `black --check .` — 468 unchanged, `flake8` чист, `mypy` — «no issues found in 621 source files», `makemigrations --check` — No changes detected.
- **Исправление ревью `b4fab053..baa78940` (2026-10-14, R42.4-25).** Ветка `fix/42-4-review-r10-r13`. Менялся только `test_manager_clients_section.py`; `detect-changes --scope all` — «No changes detected», `impact` не требовался. Мутация `unblock_users`: вместе с `is_active=True` сохранялось `verification_status="pending"` (`admin.py` возвращён `git checkout`, `git diff` пуст):

  | Состав теста | Результат на мутации |
  |---|---|
  | полный тест | упал на `assert blocked.verification_status == "verified"` (`pending`) |
  | без проверки статуса — остаётся только HTTP-вход | упал на `assert response.status_code == 200`: 403 `account_pending_verification` |

  `TestUnblock` на исходном коде — 3 passed. Полный прогон (`freesport-test`, `-n 4 -m "not performance and not slow"`): `4178 passed, 76 skipped` за 16:09. После него в `freesport-test` по изменённому файлу: `black --check`, `isort --check-only`, `flake8`, `mypy` — чисто.
- **`detect-changes --scope all`:** символы `UserAdmin` (namespace, `permissions`, `unblock_users`), `UsersConfig.ready`, `send_manager_region_email`, `admin_site.py`. `CompanyAdmin`, `AddressAdmin`, `FavoriteAdmin`, `_apply_verify_b2b` в списке из-за сдвига строк на устаревшем индексе — не менялись; «Risk: high» — артефакт того же индекса, impact каждого символа до правок — LOW.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-10-12 — стори освежена на `b4fab053` (первая редакция `9af7c7ed` писалась до кода 42.2 и 42.3). Эпик и спецификация с тех пор не менялись, AC сохранены. Изменено: предусловия (42.2 в `develop`, PR 42.3 ещё не слит), координаты `users/admin.py` (+28 строк после 42.2), тестов и `deferred-work.md`; решение 2 — явный отказ суперпользователю в группе; новые решения 12 (ответственный без ссылки) и 13 (главная без «Последних действий») с правками AC1, AC2, AC4, AC8; транзакционный режим тестов и сигналы правил 42.2 в Task 5; таблица мутаций; рецепт линтеров в `freesport-test`; подводные камни 42.2/42.3. GitNexus impact по всем символам Task 0 — LOW.
- 2026-10-13 — реализация. Сайт `/manager/` (`ManagerAdminSite`, `manager_site`) с кэшем членства на `request`, своей главной без «Последних действий» и подписью «Клиенты» у блока и модели. `ManagerClientAdmin` в `apps/users/manager_admin.py`: видимость `scope_clients`, 404 на чужого клиента, белый список полей карточки, ответственный текстом, журнал флага «активен» (`source: card`), редирект на список с сообщением, когда клиент ушёл к другому менеджеру, фильтр «Учётная запись на портале». В `UserAdmin`: пять `reverse("admin:…")` → `self.admin_site.name`, `permissions=["change"]` у одобрения, отказа и блокировки, новое действие `unblock_users`. Письмо менеджеру региона ведёт на `/manager/users/user/<id>/verify/`. Nginx проксирует `/manager/` в обоих конфигах. Долг VG1 закрыт в `deferred-work.md`.
- Тесты: `tests/integration/test_manager_clients_section.py` (AC1–AC11) и `tests/unit/test_manager_admin_site.py` (доступ к сайту, один запрос членства, `scope_clients`, `PortalAccountFilter`, `unblock_users` в `/admin/`) — 70 тестов.
- ✅ Resolved review finding [medium]: ID 5 — сохранение и изоляция `CompanyInline`/`AddressInline` (`TestClientInlines`).
- ✅ Resolved review finding [low]: ID 6 — POST карточки при одном `users.view_user` → 403 без изменений (`TestViewOnlyPermissions::test_card_post_is_forbidden`).
- ✅ Resolved review finding [medium]: ID 7 — у всех 50 строк замера AC11 есть кандидат 1С (`TestChangelistQueryCount`).
- ✅ Resolved review finding [medium]: ID 20 (третье ревью) — негативные проверки списка, поиска и прямых URL параметризованы группами «Менеджеры» и «Руководители», у каждого варианта свой и чужой клиент (`section_member`).
- ✅ Resolved review finding [medium]: ID 21 (третье ревью) — `proxy_pass http://backend` в `/manager/` обоих nginx-конфигов закреплён тестом `TestManagerSectionRoute`; HTTP-проверка через nginx — 302 на `/manager/login/?next=/manager/` (ручной замер, Debug Log).
- ✅ Resolved review finding [high]: R42.4-1 — `ManagerClientAdmin.save_model` перед записью проверяет принадлежность клиента под `select_for_update` в транзакции `changeform_view`: клиент, переданный другому менеджеру после открытия карточки, получает 404, передача не откатывается. `response_action` читает выбранные строки под блокировкой (`FOR UPDATE OF users`, по возрастанию pk) в `transaction.atomic()`. Исключение — `link_1c_customer`: сервис блокирует source и target по возрастанию pk, внешняя блокировка target перевернула бы порядок. Страница подтверждения B2B и смена пароля не менялись: их запись идёт через сервисы со своей блокировкой, гонка там ранее отклонена как `low` (edge-case-hunter №5). Тесты `TestTransferDuringWrite`.
- ✅ Resolved review finding [medium]: R42.4-2 — шаг «Health check production» в `.github/workflows/deploy.yml` проверяет `/manager/`: 302 с `Location: /manager/login/?next=/manager/`, затем страница входа Django (`id="login-form"`). Иначе деплой падает.
- ✅ Resolved review finding [low]: R42.4-3 — `PortalAccountFilter.effective_value()`: при `role__exact=unregistered` без `portal_account` выделено «Все», `queryset()` и `choices()` читают одно значение; исключение Task 3 сохранено (`test_role_filter_unregistered_selects_all`).
- ✅ Resolved review finding [high]: R42.4-4 — исключение привязки к 1С в `response_action` проверяет действие, которое реально выполнит Django (`_executed_action`: значение `action` по `index`, при выходе за границы — последнее, как читает `QueryDict`). Тест `test_second_action_field_does_not_skip_lock`.
- ✅ Resolved review finding [high]: R42.4-5 — POST карточки блокирует строку клиента до чтения объекта (`ManagerClientAdmin.change_view` → `_lock_rows` в `transaction.atomic`). Django читает свежий объект под блокировкой, поэтому полное `save()` не затирает конкурентный импорт `onec_id` и другие скрытые поля, а клиент, переданный до отправки, получает 404 из `get_object`. Проверка принадлежности в `save_model` (R42.4-1) стала лишней и удалена: её закрывает чтение под блокировкой. Тест `test_card_keeps_concurrent_import`.
- ✅ Resolved review finding [high]: R42.4-6 — то же для смены пароля (`user_change_password`) и страницы подтверждения (подтверждение и отказ, `verify_b2b_view`): строка блокируется до `get_object`, передача посреди записи ждёт и применяется после, прежнего ответственного не возвращает. Порядок блокировок не меняется: сервис подтверждения и так сначала блокирует заявку. Привязка (`_apply_link_1c_customer`) блокирует цель вместе с выбранным кандидатом по возрастанию pk, как сервис, и под блокировкой перепроверяет принадлежность → 404. Источник блокируется только из показанных кандидатов. Изменения — в `ManagerClientAdmin`, `/admin/` не затронут. Тесты `test_password_change_does_not_undo_transfer`, `test_verify_page_waits_for_transfer[verify|reject]`, `test_link_after_transfer_answers_404`.
- ✅ Resolved review finding [low]: R42.4-7 — при фильтре роли «Не зарегистрирован» ссылка «Есть» передаёт явное `portal_account=yes` (без параметра в такой связке действует «Все»). Значение `yes` вычитает `unregistered` и при фильтре роли: список пуст, это честное пересечение. Тесты `test_have_account_link_keeps_its_choice` (переход по ссылке) и `test_explicit_yes_hides_unregistered_even_with_role_filter`.
- ✅ Resolved review finding [medium]: R42.4-9 — POST карточки, смены пароля и страницы подтверждения (подтверждение и отказ) блокирует строку клиента через `_lock_client`. Без права `change` блокировки нет, вью отвечает 403. Цель берётся только из выборки раздела (`get_queryset(request).select_for_update(of=("self",))`): строку чужого клиента запрос не трогает и не ждёт, вью отвечает 404. Scoped-чтение `get_object` под блокировкой сохранено: передача клиента посреди записи по-прежнему ждёт конца транзакции. Привязка к 1С осталась на `_lock_rows` (цель и источник по возрастанию pk): источник может законно лежать вне выборки, а цель перепроверяется под блокировкой. Тесты `TestNoLockWithoutAccess` (чужой клиент → 404 и право `view_user` → 403 при занятой строке, по 4 пути).
- ✅ Resolved review finding [low]: R42.4-8 — у обоих `curl` проверки `/manager/` в `deploy.yml` стоят `--connect-timeout 10 --max-time 30`.
- ✅ Resolved review finding [high]: R42.4-10 — `_lock_client` при пустой scoped-блокировке (клиента нет в выборке раздела или id невалиден) сразу отвечает 404. Клиента, переданного менеджеру после попытки блокировки, вью больше не читает и не пишет без блокировки строки. 403 без права change и 404 без блокировки чужой строки сохранены. Тест `TestNoLockWithoutAccess::test_client_assigned_after_empty_lock_answers_404` (карточка, пароль, подтверждение, отказ).
- ✅ Resolved review finding [medium]: R42.4-11 — `_apply_link_1c_customer` проверяет принадлежность цели выборке раздела до общей блокировки: уже переданная цель — 404 без ожидания её строки. Перепроверка под блокировкой и совместный порядок source/target по pk сохранены; источник выборкой не ограничен. Тесты `test_link_to_transferred_client_answers_404_without_lock` (строку держит второе соединение) и `test_link_rechecks_scope_under_lock` (передача между проверкой и блокировкой).
- ✅ Resolved review finding [medium]: R42.4-12 — `TestTransferDuringWrite::test_link_locks_source_and_target_in_pk_order`: `source.pk < target.pk`, вторая транзакция держит источник и, когда привязка встаёт за ним в очередь, пишет цель. Обе операции завершаются, результаты обеих сохранены; замена совместной блокировки предварительной блокировкой цели даёт `DeadlockDetected`. Ожидание очереди вынесено в хелпер `waits_for_lock`, им пользуется и `BackgroundWrite`.
- ✅ Resolved review finding [medium]: R42.4-13 — проверка `/manager/` вынесена из `deploy.yml` в `scripts/deploy/check-manager-route.sh` (302 ровно на `/manager/login/?next=/manager/`, затем 200 и `id="login-form"`). Её зовут `deploy.yml` на проде и новый шаг `main.yml` «Маршрут /manager/ через локальный nginx»: Django на раннере с настройками development, `nginx:alpine` с настоящим `local.conf`. Шаг входит в обязательный job `build`.
- ✅ Resolved review finding [medium]: R42.4-14 — `ManagerClientAdmin._lock_link_rows` захватывает строки привязки по возрастанию pk: цель — выборкой раздела прямо в `SELECT … FOR UPDATE` (как `_lock_client`), источник 1С — через `User.objects`. Уже переданную цель запрос не трогает и её строку, занятую чужой транзакцией, не ждёт — 404; пустой захват цели — тоже 404. Предварительная проверка `exists()` и перепроверка после блокировки стали лишними и удалены: передачу, завершённую до захвата, отсекает тот же запрос, а начатая после ждёт конца транзакции. Тест `test_link_target_transferred_right_before_lock_answers_404_without_lock`; `test_link_rechecks_scope_under_lock` переведён на шов `_lock_link_rows`.
- ✅ Resolved review finding [medium]: R42.4-15 — `scripts/deploy/check-manager-route.sh` проверяет код завершения `curl` у обоих запросов отдельно от разбора ответа, требует от страницы входа HTTP 200 и ищет форму в полностью полученном теле (временный файл). Тест `tests/unit/test_check_manager_route_script.py` запускает скрипт против локального HTTP-сервера: один успешный сценарий и шесть провальных (оборванная страница входа, 302 с формой, страница без формы, оборванный редирект, редирект не туда, 404). В тестовый контейнер смонтирован `scripts/deploy/`.
- ✅ Resolved review finding [medium]: R42.4-16 — `scripts/deploy/check-manager-session.sh`: вход менеджера формой через nginx (302 на `/manager/`), затем `/manager/users/user/` — 200, свой клиент в списке, чужого нет. Шаг `main.yml` «Маршрут /manager/ через локальный nginx» мигрирует пустую `test_db`, создаёт двух менеджеров группы «Менеджеры» и по клиенту каждому, затем запускает обе проверки. На production новая проверка не запускается: тестовой учётной записи там нет.
- ✅ Resolved review finding [medium]: R42.4-17 — шаг `main.yml` проверяет вход менеджера, свой и чужой клиент и через production `default.conf`: второй nginx на изолированном стенде раннера с самоподписанным сертификатом по пути Let's Encrypt, конфиг монтируется без правок. Production-учётные записи не создаются. Мутации `proxy_hide_header Set-Cookie;` и `proxy_set_header Cookie "";` в `/manager/` файла `default.conf` роняют проверку входа.
- ✅ Resolved review finding [medium]: R42.4-18 — `tests/unit/test_xdist_redis_isolation.py`: настройки воркеров `gw0` и `gw1` в отдельных процессах получают разные БД Redis, `cache.clear()` первого не удаляет значение второго. Тест входит в обязательный последовательный CI-прогон; `_WORKER_INDEX = 0` его роняет.
- ✅ Resolved review finding [medium]: R42.4-19 — проба изоляции Redis больше не берёт фиксированные DB 12/13. `active_dbs()` считает занятые БД текущего прогона: от базовой (своя БД минус индекс воркера) по `PYTEST_XDIST_WORKER_COUNT` штук, без xdist — одна. `probe_dbs()` берёт две старшие свободные БД; второй воркер пробы получает индекс, равный их разнице, поэтому базы не обязаны идти подряд. Если свободных БД меньше двух (база 1 и `-n 15`), проба пропускается с причиной, FLUSHDB живых баз не делается. Тесты: `test_probe_never_touches_active_workers` (все базы 0…15 и всё допустимое число воркеров) и `test_active_dbs_cover_all_workers`.
- ✅ Resolved review finding [medium]: R42.4-20 — `tests/unit/test_check_manager_route_script.py` запускает и `check-manager-session.sh` против локального HTTP-сервера, повторяющего вход Django: форма с CSRF, POST ставит cookie сессии, список без cookie уводит на вход. Положительный контроль — в списке только свой клиент, exit 0. Негатив — вход и HTTP 200 списка с обоими email: скрипт обязан завершиться ненулевым кодом с сообщением о чужом клиенте. Сервер теста принимает POST и ответы, вычисляемые по Cookie и полям формы; тесты маршрута не менялись.
- ✅ Resolved review finding [medium]: R42.4-21 — `_lock_link_rows` до захвата строк проверяет принадлежность цели выборке раздела без блокировки (`exists()`), затем захватывает строки по возрастанию pk с прежней scoped-перепроверкой цели. Переданная цель с занятым источником меньшего pk — сразу 404, без очереди за источником. Тест `TestNoLockWithoutAccess::test_link_to_transferred_client_skips_held_source_with_lower_pk`: `source.pk < target.pk`, передача перед `_lock_link_rows`, источник держит второе соединение; до правки — `OperationalError` по `lock_timeout` (RED), после — 404, источник и цель не изменены, `AuditLog` пуст.
- ✅ Resolved review finding [medium]: R42.4-22 — `row_is_locked` признаёт блокировкой только SQLSTATE `55P03` (`psycopg2.errorcodes.LOCK_NOT_AVAILABLE` из `exc.__cause__.pgcode`), остальные `DatabaseError` пробрасывает. `TestRowLockProbe`: свободная строка — False, строка под `row_held_elsewhere` — True (положительный контроль настоящего NOWAIT-конфликта), посторонний `DatabaseError` пробного запроса — исключение (до правки — True, RED).
- Проверки R42.4-21/22 (2026-10-14): `test_manager_clients_section.py` — 90 passed; полный backend-прогон `-n 4 -m "not performance and not slow"` — 4176 passed, 76 skipped, 15:30; `black`, `isort`, `flake8`, `mypy` по изменённым файлам — чисто. Модели и API не менялись — `makemigrations --check` и `check_openapi_sync` не повторялись. GitNexus: `impact _lock_link_rows` — LOW (один вызывающий `_apply_link_1c_customer`), `detect-changes --scope compare --base-ref 956bb9c5` — 2 символа, 0 процессов, риск low.
- ✅ Resolved review finding [medium]: R42.4-23 — `TestTransferDuringWrite::test_link_rechecks_scope_under_lock` переписан под заявленный интервал: на время вызова `_lock_link_rows` `QuerySet.exists` обёрнут так, что сразу после первой (предварительной) проверки принадлежности второе соединение передаёт клиента другому менеджеру. Тест требует, чтобы предварительная проверка своего клиента пропустила (`prechecked == [True]`), иначе он не проверял бы интервал. Ожидание: 404, ответственный — новый менеджер, `onec_id` цели пуст, источник не изменён, `AuditLog` пуст. Прежняя версия теста передавала клиента до входа в `_lock_link_rows` и дублировала `test_link_target_transferred_right_before_lock_answers_404_without_lock` — переписана, а не добавлена рядом: имя и комментарий теста и так описывали этот интервал. Мутация: захват цели в `_lock_link_rows` через `User.objects.select_for_update(...)` вместо выборки раздела — тест падает (302 вместо 404), три теста из замечания остаются зелёными.
- ✅ Resolved review finding [medium]: R42.4-24 — `tests/unit/test_xdist_file_isolation.py`: настройки `freesport.settings.test` воркеров `gw0` и `gw1` поднимаются в отдельных процессах, `TMPDIR` дочерних процессов — `tmp_path` теста (каталоги воркеров текущего прогона не задеваются). `test_workers_have_separate_file_roots`: `MEDIA_ROOT`, `ONEC_PRIVATE_DIR`, `TEMP_DIR`, `IMPORT_DIR`, `EXCHANGE_LOG_DIR` у воркеров попарно различны и лежат во временном каталоге. `test_same_relative_file_is_not_shared`: оба воркера пишут через `FileStreamService.append_chunk` один `import.zip` одной сессии, каждый читает своё, первый после записи второго — по-прежнему `first`. Тест в `tests/unit/` — входит в обязательный прогон `main.yml`. Мутация: сегмент `(_XDIST_WORKER or "main")` → `"main"` — оба теста падают, `test_xdist_redis_isolation.py` остаётся зелёным.
- Проверки R42.4-23/24 (2026-10-14): мутации выше — новые тесты красные, код возвращён из копий; полный backend-прогон `-n 4 -m "not performance and not slow"` — 4178 passed, 76 skipped, 22:07; `black`, `isort`, `flake8`, `mypy` по изменённым файлам — чисто. Менялись только тесты: `makemigrations --check` и `check_openapi_sync` не повторялись. GitNexus: индекс `stale` (`956bb9c` при HEAD `35f8cc2`), `detect-changes --scope all` — «No changes detected»; символы кода приложения не менялись, `impact` не требовался.
- ✅ Resolved review finding [medium]: R42.4-25 — `TestUnblock::test_unblock_restores_login` после действия входит в портал через `POST /api/v1/auth/login/` (`reverse("users:login")`, отдельный `APIClient`) и ждёт 200 с непустыми `access` и `refresh` и `user.id` клиента; статус верификации после действия — `verified`. Мутация «действие сохраняет `pending`» ловится обеими проверками: статусом и самим HTTP-входом (403 `account_pending_verification`). Код раздела не менялся.
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
- `backend/apps/users/manager_admin.py` — новый (R42.4-21: проверка цели без блокировки до захвата строк в `_lock_link_rows`; R42.4-14: `_lock_link_rows` — захват цели привязки выборкой раздела; R42.4-10: 404 на пустую блокировку в `_lock_client`; R42.4-11: проверка цели до блокировки в `_apply_link_1c_customer`): `scope_clients`, `PortalAccountFilter`, `ManagerClientAdmin`; блокировка строк в `save_model` и `response_action` (R42.4-1), `effective_value` фильтра (R42.4-3); блокировка до чтения в карточке, пароле, подтверждении и привязке, `_executed_action`, явное `portal_account=yes` (R42.4-4…7); `_lock_client` — блокировка только при праве change и только в выборке раздела (R42.4-9)
- `backend/apps/users/admin.py` — namespace сайта в `reverse`, `permissions=["change"]`, `unblock_users`
- `backend/apps/users/tasks.py` — ссылка письма менеджеру региона
- `backend/templates/admin/manager/index.html` — новый: главная без «Последних действий»
- `backend/templates/emails/manager_region_notification.txt`, `backend/templates/emails/manager_region_notification.html` — подпись ссылки
- `docker/nginx/conf.d/default.conf`, `docker/nginx/conf.d/local.conf` — `location /manager/`
- `docker/nginx/snippets/app-headers.conf` — комментарий
- `backend/tests/integration/test_manager_clients_section.py` — новый; вход в портал через API после разблокировки (R42.4-25); передача цели между предварительной проверкой и захватом в `test_link_rechecks_scope_under_lock` (R42.4-23), занятый источник меньшего pk при переданной цели (R42.4-21), `row_is_locked` только по SQLSTATE 55P03 и `TestRowLockProbe` (R42.4-22); передача цели привязки прямо перед захватом при занятой строке, шов `_lock_link_rows` (R42.4-14); параметризация по группам раздела (третье ревью); `TestTransferDuringWrite` (R42.4-1, конкурентные записи `BackgroundWrite` — R42.4-4…6), переход по «Есть» (R42.4-7); `TestNoLockWithoutAccess` с хелпером `row_held_elsewhere` (R42.4-9); пустая блокировка, привязка к переданному клиенту, перепроверка под блокировкой, порядок source/target, хелпер `waits_for_lock` (R42.4-10…12)
- `backend/tests/unit/test_manager_admin_site.py` — новый; выделение пункта фильтра при роли «Не зарегистрирован» (R42.4-3), значение `yes` (R42.4-7)
- `.github/workflows/deploy.yml` — HTTP-проверка `/manager/` после деплоя (R42.4-2), таймауты `curl` (R42.4-8); проверка вынесена в скрипт (R42.4-13)
- `.github/workflows/main.yml` — шаг «Маршрут /manager/ через nginx (local.conf и default.conf)» (R42.4-13; миграции, засев и вход менеджера — R42.4-16; production `default.conf` с самоподписанным сертификатом — R42.4-17)
- `scripts/deploy/check-manager-route.sh` — новый: HTTP-проверка маршрута `/manager/` (R42.4-13); код завершения curl, HTTP 200 и полное тело страницы входа (R42.4-15); комментарий о двух конфигах (R42.4-17)
- `scripts/deploy/check-manager-session.sh` — новый: вход менеджера и список клиентов через nginx (R42.4-16); комментарий о двух конфигах (R42.4-17)
- `backend/tests/unit/test_check_manager_route_script.py` — новый: скрипт проверки маршрута против локального HTTP-сервера (R42.4-15); вход менеджера скриптом `check-manager-session.sh`, отказ на чужом клиенте и положительный контроль (R42.4-20)
- `docker/docker-compose.test.yml` — монтирование `scripts/deploy/` (R42.4-15)
- `backend/tests/unit/test_xdist_redis_isolation.py` — новый: изоляция Redis между воркерами xdist (R42.4-18); проба только на БД вне занятых воркерами, пропуск при одной свободной (R42.4-19)
- `backend/tests/unit/test_xdist_file_isolation.py` — новый: файловые корни воркеров xdist в отдельных процессах и запись одного относительного имени через `FileStreamService` (R42.4-24)
- `backend/tests/unit/test_region_routing.py` — ожидание ссылки письма
- `backend/tests/unit/test_users_admin.py` — список действий (отклонение 2)
- `backend/tests/unit/test_nginx_security_headers.py` — локация `/manager/` в перечне известных (ревью), `TestManagerSectionRoute` (третье ревью); ссылка на скрипт живой проверки (R42.4-13); ссылка на проверку входа (R42.4-16); обе проверки на двух конфигах (R42.4-17)
- `backend/tests/integration/test_admin_verify_b2b_application.py` — комментарии
- `_bmad-output/implementation-artifacts/deferred-work.md` — VG1 закрыт; отложенное из ревью на `d9f21c20` и `46ff9a6e`
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — статус стори
- `_bmad-output/implementation-artifacts/Story/42-4-manager-section-own-clients.md` — этот файл

### Change Log

- 2026-10-13 — реализация стори 42.4: раздел менеджера `/manager/` с клиентами своего региона, действие «Разблокировать», ссылка письма менеджеру в раздел, nginx-локация; 70 новых тестов, мутационная проверка защит; статус → review.
- 2026-10-13 — исправления ревью: 2 замечания [Review][Patch] закрыты (страж локации `/manager/` в `test_nginx_security_headers.py`, содержательная проверка дублей в `test_member_of_several_groups_is_not_duplicated`); полный прогон 4139 passed; статус → review.
- 2026-10-13 — исправления повторного ревью: 3 замечания [Review][Patch] закрыты (ID 5 — инлайны Company/Address своего и чужого клиента, ID 6 — POST карточки при одном `view_user`, ID 7 — кандидаты 1С у всех строк замера AC11); только тесты, код раздела не менялся; полный прогон 4143 passed; статус → review.
- 2026-10-13 — исправления третьего ревью: 2 замечания [Review][Patch] закрыты (ID 20 — изоляция клиентов руководителя в проверках списка, поиска и прямых URL; ID 21 — страж `proxy_pass` маршрута `/manager/` в обоих nginx-конфигах); только тесты, код раздела не менялся; полный прогон 4147 passed; статус → review.
- 2026-10-13 — повторное ревью `b4fab053..c2743ed3`: по решению Alex три исправления R42.4-1/R42.4-2/R42.4-3 оставлены открытыми задачами, код не менялся; 224 профильных теста прошли, отдельное воспроизведение подтвердило потерю переназначения; статус `review` → `in-progress`.
- 2026-10-14 — исправления ревью `b4fab053..7728a9c8`: закрыты R42.4-1 (блокировка строки клиента при записи карточки и массовых действий), R42.4-2 (HTTP-проверка `/manager/` в `deploy.yml`), R42.4-3 (выделение «Все» в фильтре портала); 3 замечания, 7 новых тестов, мутационная проверка; полный прогон 4119 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..220766c3`: закрыты R42.4-4 (исключение привязки по фактически выполняемому действию), R42.4-5 и R42.4-6 (строка клиента блокируется до чтения в карточке, смене пароля, подтверждении и отказе; привязка перепроверяет принадлежность под блокировкой цели и источника), R42.4-7 (явное `portal_account=yes` у «Есть»), R42.4-8 (таймауты `curl` в `deploy.yml`); 5 замечаний, 8 новых проверок, мутационная проверка; полный прогон 4127 passed; статус → review.
- 2026-10-14 — исправление ревью `b4fab053..63cd2959`: закрыт R42.4-9 (запрос без права change или к чужому клиенту не блокирует его строку — `_lock_client` по выборке раздела); 1 замечание, 8 новых проверок, мутационная проверка; полный прогон 4135 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..ac631c09`: закрыты R42.4-10 (пустая блокировка клиента → 404), R42.4-11 (привязка отсекает переданную цель до блокировки), R42.4-12 (конкурентный страж порядка source/target), R42.4-13 (HTTP-проверка `/manager/` через локальный nginx в `main.yml`, общий скрипт с `deploy.yml`); 4 замечания, 9 новых проверок, мутационная проверка кода и конфига; полный прогон 4142 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..741ce342`: закрыты R42.4-14 (цель привязки захватывается выборкой раздела в самом запросе блокировки — переданную цель запрос не ждёт), R42.4-15 (скрипт проверки маршрута проверяет код curl, HTTP 200 и полное тело; тест скрипта на локальном HTTP-сервере), R42.4-16 (вход менеджера и список клиентов через настоящий nginx в `main.yml`); 3 замечания, 8 новых проверок, мутационная проверка кода и конфига nginx; полный прогон 4150 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..d9f21c20`: закрыты R42.4-17 (вход менеджера и список клиентов через production `default.conf` на изолированном стенде `main.yml`), R42.4-18 (тест изоляции Redis между воркерами xdist в двух процессах); 2 замечания, 1 новый тест, мутационная проверка конфига nginx и настроек; полный прогон 4151 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..46ff9a6e`: закрыты R42.4-19 (проба изоляции Redis берёт только БД вне занятых воркерами текущего прогона, при одной свободной пропускается) и R42.4-20 (негативный тест `check-manager-session.sh` на чужом клиенте с положительным контролем); 2 замечания, 21 новая проверка, мутационная проверка; только тесты; полный прогон 4172 passed; статус → review.
- 2026-10-14 — исправления ревью `b4fab053..956bb9c5`: закрыты R42.4-21 (привязка к переданной цели не ждёт занятый источник меньшего pk — проверка цели до захвата строк) и R42.4-22 (проверка блокировки в тестах принимает только SQLSTATE 55P03); 2 замечания, 4 новых теста; полный прогон 4176 passed; статус → review.
- 2026-10-14 — ревью `b4fab053..35f8cc29`: по решению Alex два пробела регрессионных проверок R42.4-23 и R42.4-24 оставлены открытыми задачами; код и тесты не менялись, 241 профильный тест прошёл в Docker; статус story и спринта `review` → `in-progress`.
- 2026-10-14 — исправления ревью `b4fab053..35f8cc29`: закрыты R42.4-23 (интервал между предварительной проверкой цели и её захватом покрыт HTTP-тестом с двумя соединениями) и R42.4-24 (межпроцессная проверка файловых корней воркеров xdist); 2 замечания, 1 тест переписан, 2 новых, мутационная проверка; только тесты; полный прогон 4178 passed; статус → review.
- 2026-10-14 — ревью `b4fab053..baa78940`: по решению Alex пробел регрессионной проверки R42.4-25 оставлен открытой задачей; 4 группы отложены как повторы существующего долга; статус story и спринта `review` → `in-progress`.
- 2026-10-14 — исправление ревью `b4fab053..baa78940`: закрыт R42.4-25 (разблокировка проверяется вместе с API-входом портала: 200, `access`/`refresh`, сохранённый статус `verified`); 1 замечание, дополнен 1 тест, мутационная проверка; только тесты; полный прогон 4178 passed; статус → review.
