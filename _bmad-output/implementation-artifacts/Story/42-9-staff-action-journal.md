---
baseline_commit: abf84102
---

# Story 42.9: Журнал действий сотрудников

Status: review
Baseline Revision: abf84102 (`develop` после мёрджа `feature/42-8-supervisor-summary` — стори 42.8 `done`)

## Story

As a руководитель,
I want читать понятную ленту того, что сделали сотрудники,
so that я разбираю спорные случаи («кто заблокировал клиента», «кто переназначил клиента в карточке») без логов и техподдержки. Массовая передача клиентов — стори 42.10, её записей в этой ленте пока нет.

**Закрывает:** FR-42-30 (сверка перечня целиком), FR-42-31. **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.9), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-6, `section-contents.md` → «Перечень действий для журнала (CAP-6)» и «Руководитель» → «Журнал действий»), `_bmad-output/implementation-artifacts/epic-42-context.md` (журнал на существующем `AuditLog`; «дата — сотрудник — действие — объект»; без IP, User-Agent, JSON и служебных операций), отложенное R42.7-D2 (`deferred-work.md`).

**Предусловия:**
- Код 42.1–42.8 в `develop` (`abf84102`): сайт `/supervisor/` (`SupervisorAdminSite`, свой путь `summary/` до `super().get_urls()`), записи `AuditLog` о действиях менеджера (42.4, 42.5) и руководителя (42.7), `scope_clients`/`scope_orders` с веткой руководителя, `manager_label`, `period_presets` сводки.
- Ветка `feature/42-9-staff-action-journal` от `develop`.
- **Модели, миграции и права не меняются.** Лента — страница сайта, а не `ModelAdmin`. Proxy-модель потребовала бы миграцию и выдачу права группе, а сырой `AuditLog` ни одной роли не показывается (`section-contents.md` → «Ни одной из ролей»).

**Сверка перечня на `abf84102` (основа реализации):** каждое действие из перечня `section-contents.md` уже пишет одну запись `AuditLog`, пробелов нет.

| Действие перечня | Где и кто | `action` | `resource_type` | Место в коде |
|---|---|---|---|---|
| Верификация | страница подтверждения B2B — менеджер, руководитель | `verify_b2b` (`mode=decision`) | `User` | `users/services/verify_b2b_application.py:226` |
| Верификация | действие списка «Верифицировать» | `approve_b2b` | `User` | `users/admin.py:992` |
| Отказ | страница подтверждения / действие списка | `reject_b2b` | `User` | `verify_b2b_application.py:304`, `users/admin.py:1206` |
| Блокировка клиента | действие списка / флаг «Активен» в карточке | `block_user` | `User` | `users/admin.py:1259`, `users/manager_admin.py:480` |
| Разблокировка клиента | действие списка / флаг в карточке | `unblock_user` | `User` | `users/admin.py:1333`, `users/manager_admin.py:480` |
| Сброс пароля | клиенту (менеджер), сотруднику (руководитель) | `change_password` | `User` | `users/admin.py:564` |
| Смена роли | только на странице подтверждения (роль в карточке только для чтения) | `verify_b2b`, `role_before` ≠ `role_after` | `User` | `verify_b2b_application.py:226` |
| Привязка к 1С | действие списка; страница подтверждения с кандидатом пишет ещё и `verify_b2b` | `link_1c_customer` | `User` | `users/services/link_1c_customer.py:274` |
| Трек-номер, дата доставки | карточка мастер-заказа | `update_order` | `Order` | `orders/manager_admin.py:446` |
| Назначение и переназначение ответственного | карточка клиента у руководителя (ставится и снимается флаг «вручную») | `assign_responsible_manager` | `User` | `users/manager_admin.py:507` |
| Изменение правила региона | создание, правка (в том числе строкой списка), удаление, «Удалить выбранные» | `change_routing_rule` | `ManagerRoutingRule` | `common/supervisor_admin.py:60` |
| Создание сотрудника | руководитель | `create_staff` | `User` | `users/supervisor_admin.py:306` (`save_related`) |
| Блокировка и разблокировка сотрудника | действия списка руководителя | `block_staff` / `unblock_staff` | `User` | `users/supervisor_admin.py:369`, `:387` |
| Смена группы сотрудника | карточка сотрудника | `change_staff_group` | `User` | `users/supervisor_admin.py:326` |

Служебная запись `role_from_1c` (`users/services/processor.py:665`, `user=None`) — смена роли импортом, а не сотрудником. Массовая передача клиентов и замещение — коды стори 42.10, их здесь нет.

**Чего в этой стори нет:**
- новых видов записей и правок в местах, которые пишут журнал. Исключений два: транзакция у смены пароля (решение 12, R42.7-D2) и запрет удалять автора записей ленты (решение 13);
- массовой передачи и замещения (42.10). Их коды 42.10 добавит в перечень ленты (раздел «Связь с последующими стори»);
- журнала маркетинга: в перечне действий маркетинга нет (42.6, решение 15);
- регистрации `AuditLog` или proxy-модели в разделах, выгрузки ленты, поиска по объекту;
- изменений в моделях, миграциях, правах, API, OpenAPI, фронтенде Next.js, nginx, CI.

## Решения (основа реализации)

1. **Страница `/supervisor/journal/`, имя `supervisor:journal`.** `SupervisorAdminSite.get_urls()` возвращает `[path("summary/", …), path("journal/", self.admin_view(self.journal_view), name="journal"), *super().get_urls()]`. Свой путь ставится **до** родительских, как у сводки: catch-all `AdminSite.get_urls()` перехватил бы путь, добавленный после него.
   - `journal_view(self, request)` устроен как `summary_view`: `request.current_app = self.name`; импорт `from apps.common.staff_journal import build_journal` **внутри метода**, иначе цикл импорта; `TemplateResponse(request, "admin/supervisor/journal.html", {**self.each_context(request), "title": "Журнал действий", **build_journal(request)})`.
   - Доступ — `admin_view` → `has_permission` базового `StaffSectionAdminSite` без изменений. Менеджер, маркетолог, сотрудник без группы, заблокированный руководитель, суперпользователь (в том числе состоящий в «Руководителях») и аноним получают 302 на `/supervisor/login/?next=/supervisor/journal/`. На других сайтах страницы нет: `/manager/journal/` и `/marketing/journal/` отвечают 404 (catch-all).
   - Docstring класса дополнить строкой: журнал действий `/supervisor/journal/` (стори 42.9).
2. **Логика — новый модуль `backend/apps/common/staff_journal.py`.** `AuditLog` лежит в `apps/common`, как и журнал правил `common/supervisor_admin.py`. Модуль ничего не регистрирует, в `CommonConfig.ready()` не импортируется и вызывается только из `journal_view`. Зависимости `common → orders.supervisor_summary` (`period_presets`), `common → orders.manager_admin` (`scope_orders`) и `common → users.manager_admin` (`scope_clients`) цикла не дают: на `staff_journal` не ссылается ни один модуль. Проверка — `check --cycles` (Task 5). Публичные имена, на которые опираются тесты:
   - `JournalFilterForm`, `journal_filter(request)`, `journal_records(form)`, `build_rows(request, records)`, `describe(record, users)`, `build_journal(request)`, `PER_PAGE = 100`, `DEFAULT_DAYS = 30`.

   **Перечень кодов — в отдельном листовом модуле `backend/apps/common/staff_actions.py`:** `STAFF_ACTIONS: dict[str, str]` — код → подпись действия (решение 4), порядок ключей — как в таблице. В модуле нет ни одного импорта. Его читают двое: `staff_journal` и охрана удаления в `users/admin.py` (решение 13). Держать перечень в `staff_journal` нельзя: `users/admin → common/staff_journal → users/manager_admin → users/admin` — цикл импорта. Импорт внутри метода спрятал бы цикл от Python, но не от `gitnexus check --cycles`.

   Docstring модуля объясняет, что попадает в ленту и почему, и как строятся ссылки.
3. **Что попадает в ленту — `journal_records(form)`:** `AuditLog.objects.filter(action__in=STAFF_ACTIONS, user__isnull=False, user__is_superuser=False)`, затем фильтры формы, `.select_related("user").order_by("-created_at", "-pk")`.
   - Код вне `STAFF_ACTIONS` (сегодня `role_from_1c`, в будущем любые служебные) в ленту не попадает. Запись без автора (`user=None`: импорт, синхронизация) — тоже. Автора с записями ленты из админки не удалить (решение 13).
   - **Действия суперпользователя (владельца) в ленту не попадают:** AC эпика требует «только действия сотрудников трёх ролей». Подтверждено Alex 18.10.2026 (п. 1).
   - Автор отбирается по признаку «не суперпользователь», а **не по текущему `is_staff` и не по текущему членству в группе**. Заблокированный менеджер, менеджер, выведенный из групп, и бывший сотрудник, у которого владелец снял `is_staff`, остаются авторами своих записей: ради разбора таких случаев лента и нужна (ответ Alex 18.10.2026, п. 8). Клиента этот критерий не впускает: коды перечня пишут только 14 мест в разделах сотрудников и в `/admin/`, а клиент туда не попадает. Записи до эпика 42, сделанные сотрудниками в `/admin/` (на проде `managermsk3@…`), тоже действия сотрудника — они в ленте.
   - `Meta.ordering` у `AuditLog` уже `-created_at`; явный `order_by` с `-pk` нужен для стабильного порядка записей одной секунды между страницами.
4. **Формулировки — `describe(record, users) -> tuple[str, str]` (действие, подробности).** Действие — существительным: «Блокировка клиента», а не «заблокировал». Так не нужно угадывать род сотрудника. Подробности собираются из `details["changes"]` по белому списку ключей; сам JSON, IP и User-Agent не выводятся никогда. Пустое значение — «—». Тексты — литералы тестов (урок R42.5-7):

   | `action` | Действие | Подробности |
   |---|---|---|
   | `approve_b2b` | Верификация клиента | — (пусто) |
   | `verify_b2b`, `mode=decision` | Подтверждение B2B-заявки | части через «; »: `роль: <до> → <после>`, если роль сменилась (подписи из `User.ROLE_CHOICES`, неизвестный код — сам код); `роль по виду цен 1С`, если `role_source == "1c_price_type"`; `с привязкой к 1С`, если `linked_now` |
   | `verify_b2b`, `mode=link_only` | Подтверждение роли при привязке к 1С | те же части |
   | `reject_b2b` | Отказ в верификации | — |
   | `block_user` | Блокировка клиента | — |
   | `unblock_user` | Разблокировка клиента | — |
   | `change_password` | Сброс пароля | `вход по паролю отключён`, если `usable_password is False`, иначе пусто |
   | `link_1c_customer` | Привязка к контрагенту 1С | — |
   | `update_order` | Изменение заказа | по `fields` в порядке `EDITABLE_FIELDS` (`orders/manager_admin.py`) через «; »: `трек-номер: <old> → <new>`, `дата доставки: <ДД.ММ.ГГГГ> → <ДД.ММ.ГГГГ>` (ISO из журнала) |
   | `assign_responsible_manager` | Назначение ответственного менеджера | `<ФИО (email) old> → <ФИО (email) new>`: в журнале лежат почты, подпись — `manager_label` учётной записи с этой почтой из общего запроса (решение 5); почты в базе нет — сама почта; `None` — «—». Если `manual is False` — плюс `; по правилу региона` (ответ Alex 18.10.2026, п. 7) |
   | `change_routing_rule` | Создание / Изменение / Удаление правила региона (по `operation`) | по `fields` в порядке `LOGGED_RULE_FIELDS` через «; »: `тип`, `значение`, `активно`, `менеджер`, `email менеджера` — `<old> → <new>`. Тип — подпись из `ManagerRoutingRule.MATCH_TYPE_CHOICES`; активность — «да»/«нет»; `manager_id` — `manager_label` учётной записи из общего запроса (решение 5), удалённой — `ID <n>` |
   | `create_staff` | Создание сотрудника | `группа: <group>` |
   | `block_staff` / `unblock_staff` | Блокировка / Разблокировка сотрудника | `группа: <group>`, если группа непустая |
   | `change_staff_group` | Смена группы сотрудника | `<old> → <new>` |

   Пример строки: `18.10.2026 14:05 — Анна Менеджерова (anna@…) — Изменение заказа — Заказ 2345-26007 — трек-номер: — → RR123456789RU`. Неожиданная форма `details` (старые записи, пропущенный ключ) не роняет страницу: недостающее — «—», лишнее не выводится.
5. **Объект и ссылка — `build_rows(request, records)`.** Число запросов на страницу постоянное: по одному запросу на вид объекта, а не на строку (NFR-42-04).
   - `resource_type="User"` — один запрос `User.objects.filter(Q(pk__in=<id объектов> ∪ <manager_id из полей правил>) | Q(email__in=<old/new из записей assign_responsible_manager>))`. Подписи менеджеров в назначении берутся из него же, отдельного запроса нет.
     - Подпись — `manager_label(user)` («ФИО (email)»).
     - Ссылка на `reverse("manager:users_user_change", args=[pk])`, если pk есть в `scope_clients(request, User.objects.filter(pk__in=ids)).values_list("pk", flat=True)`: это отдельный запрос, и у руководителя он отсекает учётные записи сотрудников.
     - Иначе, если запись — сотрудник (`is_staff and not is_superuser`, как выборка `SupervisorStaffAdmin`), ссылка на `reverse("supervisor:users_user_change", args=[pk])`.
     - Иначе ссылки нет. Так бывает у суперпользователя и у записи с `role="admin"`, которой нет в `/manager/`.
     - Удалённая запись: подпись — `changes["email"]` или `changes["target_email"]`, а если их нет — `ID <n>`; без ссылки.
   - `resource_type="Order"`:
     - подпись — `Заказ <format_order_number(changes["order_number"])>` (`orders/services/order_numbering.py:72`), без ключа — `Заказ ID <n>`;
     - ссылка на `reverse("manager:orders_order_change", args=[pk])`, если pk есть в `scope_orders(request, Order.objects.filter(pk__in=ids)).values_list("pk", flat=True)` (один запрос).
   - `resource_type="ManagerRoutingRule"`:
     - подпись — `changes["rule"]` (`str(rule)` на момент действия);
     - ссылка на `reverse("supervisor:common_managerroutingrule_change", args=[pk])`, если правило существует (один запрос `values_list("pk")`). Удалённое правило — без ссылки.
   - `resource_id` — строка. Нецифровой id в запросы не идёт, строка выводится без ссылки.
   - Автор — `manager_label(record.user)` из `select_related`.
   - Время — `timezone.localtime(record.created_at)` в формате `ДД.ММ.ГГГГ ЧЧ:ММ`.
   - Запрос вида не выполняется, если на странице нет объектов этого вида. Тест числа запросов (AC7) поэтому держит все виды объектов в обоих наборах.
6. **Фильтры — `JournalFilterForm(forms.Form)`, GET; форму строит `journal_filter(request)` и всегда связывает с данными запроса, дополненными периодом по умолчанию.**
   - `staff` — `ModelChoiceField(required=False, label="Сотрудник", empty_label="Все сотрудники")`:
     - queryset — `User.objects.filter(is_superuser=False).filter(Q(is_staff=True) | Q(pk__in=AuditLog.objects.filter(action__in=STAFF_ACTIONS).values("user"))).order_by("last_name", "first_name", "email")`: все сотрудники вместе с заблокированными плюс бывшие сотрудники, у которых есть записи ленты (решение 3). Клиентов без записей в выборе нет. Подзапрос, один запрос;
     - подпись — `manager_label(user)`; у неактивного плюс « — заблокирован» (тот же текст, что в сводке и в `ResponsibleManagerFilter`); у записи без `is_staff` — « — бывший сотрудник». Если верно оба, сначала « — бывший сотрудник»;
     - фильтр — `user=<staff>`.
   - `date_from`, `date_to` — `DateField(required=False)`, виджет `DateInput(attrs={"type": "date"}, format="%Y-%m-%d")`. Обе даты включительно, часовой пояс проекта.
     - Можно указать одну дату: только «с» или только «по».
     - Границы — `created_at >= make_aware(datetime.combine(date_from, time.min))` и `created_at < make_aware(datetime.combine(date_to + 1 день, time.min))`, как у `Period` сводки.
   - `clean()`: `date_to == date.max` — ошибка поля «Конец периода вне допустимого диапазона.»; `date_from > date_to` — ошибка формы «Начало периода позже его конца.» (тексты — как у `SummaryPeriodForm`). Несуществующий или нецифровой `staff` — штатная ошибка `ModelChoiceField`.
   - **Период по умолчанию — последние 30 дней** (ответ Alex 18.10.2026, п. 2): с `сегодня − 29` по `сегодня` (`timezone.localdate()`), ровно как быстрая ссылка «30 дней».
     - Действует, когда в запросе **нет ни ключа `date_from`, ни ключа `date_to`**: `journal_filter` копирует `request.GET` и дописывает обе даты ISO-строками. Так и при одном `?staff=<pk>`, и при `?page=2` без дат.
     - Ключи есть, но пустые (`?date_from=&date_to=`) — это «Всё время»: период не ограничен. Так быстрая ссылка «Всё время» отличается от умолчания.
     - Форма связана с дополненными данными, поэтому поля дат показывают период по умолчанию, а ссылка «30 дней» выделена.
     - Подпись над таблицей: «Период: 18.09.2026 — 17.10.2026»; при одной дате — «Период: с 13.10.2026» или «Период: по 12.10.2026»; без дат — «Период: всё время».
   - **Неверная форма** — над формой `errornote` «Фильтр указан неверно — записи не показаны.» и ошибки полей, записей нет, страница 200 (ответ Alex 18.10.2026, п. 5). Показать записи под ошибочным фильтром значило бы ввести руководителя в заблуждение.
   - Быстрые ссылки периода:
     - «Всё время» — `?date_from=&date_to=` (пустые ключи, см. выше), `staff` сохраняется; выделена, когда обе даты пустые;
     - пресеты `period_presets(timezone.localdate())` из `apps/orders/supervisor_summary.py`: «Сегодня», «7 дней», «30 дней», «Этот месяц», «Прошлый месяц». Ссылка — `?staff=<pk>&date_from=…&date_to=…`, `staff` только если выбран;
     - выбранная ссылка выделена `<strong>`. `period_presets`, `Period`, `SummaryPeriodForm` не менять.
7. **Страницы — `django.core.paginator.Paginator(records, PER_PAGE)`, `PER_PAGE = 100`, `page = paginator.get_page(request.GET.get("page"))`.** Неверный номер страницы даёт ближайшую существующую, это штатное поведение `get_page`.
   - Внизу — «Страница N из M», ссылки «← Новее» и «Старее →». Ссылка сохраняет `staff`, `date_from`, `date_to`: копия **дополненных** данных `journal_filter` (не голого `request.GET`), `["page"] = n`, `.urlencode()`. Поэтому период по умолчанию попадает в ссылку явно: после полуночи вторая страница не съедет на другие 30 дней.
   - Над таблицей — «Записей: <paginator.count>». Пустая лента — «Записей нет».
8. **Шаблон `backend/templates/admin/supervisor/journal.html`.**
   - Устроен как `summary.html`: `{% extends "admin/base_site.html" %}`, `bodyclass` + ` supervisor-journal`, хлебные крошки «Начало › Журнал действий» (`{% url 'admin:index' %}`), без `sidebar`.
   - Сверху вниз: форма фильтра (`id="journal-filter"`) со ссылками периода; затем таблица `<div class="module" id="journal-records"><table><caption>Журнал действий сотрудников</caption>`.
   - Колонки: «Дата», «Сотрудник», «Действие», «Объект», «Подробности».
   - Строка — `<tr class="journal-row">`. Объект — `<a href="{{ row.object_url }}">{{ row.object_label }}</a>` или текст без ссылки.
   - Все значения выводятся через автоэкранирование, без `|safe`.
   - Комментарий шаблона объясняет, почему нет IP, User-Agent и JSON и почему нет `sidebar`.
9. **Ссылка на журнал — второй в блоке «Разделы» главной `/supervisor/`, после «Сводки»:** `{"url": reverse("supervisor:journal"), "name": "Журнал действий сотрудников"}` в `SupervisorAdminSite.index`. Тест `test_supervisor_summary.py::TestLinks::test_index_links_summary_first` проверяет список ссылок литералом. В его ожидание добавляется вторая пара `("/supervisor/journal/", "Журнал действий сотрудников")`. Это **единственное** изменение ожиданий существующих тестов, его нужно отметить в Completion Notes.
10. **Сверка перечня — один параметризованный тест (FR-42-30, AC2).**
    - Каждый вариант выполняет действие настоящим запросом под своей ролью и проверяет:
      - всего добавилась ровно одна запись `AuditLog` (`AuditLog.objects.count()` до и после — так ловятся и дубли на других объектах);
      - код, автор и объект записи совпадают с ожидаемыми;
      - в ленте у руководителя ровно одна строка с ожидаемыми литералами «Действие» и «Подробности» и ссылкой на объект.
    - `id` варианта и сообщение `assert` — русское название действия из перечня, например `f"«{name}»: записей {delta}, ожидалась одна"`. Провал сразу называет действие.
    - Страница подтверждения с кандидатом 1С — это два действия, и записей две: `verify_b2b` и `link_1c_customer`, по одной каждого вида. Это отдельный вариант с ожиданием «две записи двух видов».
11. **Без кэша, без новых индексов.** Индекс `(user, action, created_at)` у `AuditLog` (`common/models.py`) работает при фильтре по сотруднику. Ленту всех сотрудников Postgres сортирует по `created_at` без индекса: отдельного индекса по времени нет. При сегодняшнем объёме журнала это дёшево. Проект ещё не запущен, реальных записей менеджеров нет (Alex 18.10.2026). Индекс по `created_at` заводить, когда объём это потребует.
12. **R42.7-D2 — сброс пароля и журнал в одной транзакции.**
    - Сейчас `UserAdmin.user_change_password` (`users/admin.py:554`) сначала вызывает `super().user_change_password()`, и пароль уже сохранён. Запись `AuditLog` идёт следом, вне транзакции. Сбой журнала оставляет сменённый пароль без записи, и гарантия «каждое действие из перечня пишет запись» нарушена.
    - Правка: тело метода обернуть в `with transaction.atomic():` — и вызов родителя, и `log_action`. Тогда исключение журнала откатывает пароль. Ветки «не POST», «ошибка формы», «не наш редирект» не меняются.
    - **В `/manager/` разрыва уже нет:** `ManagerClientAdmin.user_change_password` (`users/manager_admin.py:404-409`) при POST сам вызывает родителя внутри `transaction.atomic()` под блокировкой строки клиента. Открыт разрыв в `/admin/` и в `/supervisor/`: `SupervisorStaffAdmin` наследует `UserAdmin.user_change_password` без своей обёртки. Правка в `UserAdmin` закрывает оба места. Вложенный `atomic` в `/manager/` становится точкой сохранения, поведение не меняется.
    - В `deferred-work.md` пометить R42.7-D2 закрытым: «закрыто стори 42.9».
13. **Автора записей ленты нельзя удалить (ответ Alex 18.10.2026, п. 6).**
    - Почему: у `AuditLog.user` стоит `SET_NULL`. Удалённый сотрудник оставил бы записи без автора, и они пропали бы из ленты целиком. Спор «кто заблокировал клиента» чаще всего касается сотрудника, который уже ушёл. Его учётку удалили бы первой.
    - Кто может удалить: право `users.delete_user` есть только у суперпользователя (ни одной группе оно не выдано, миграция `users/0023`), а `ManagerClientAdmin.has_delete_permission` — `False`. Значит, охрана нужна только в `/admin/`. `PROTECT` (миграция `users/0025`) держит лишь менеджера, у которого остались клиенты.
    - Где: `UserAdmin.get_deleted_objects` (`users/admin.py:537`) — один хук и на карточку, и на `delete_selected`. Одним запросом `AuditLog.objects.filter(user__in=<pk удаляемых>, user__is_superuser=False, action__in=STAFF_ACTIONS).values_list("user", flat=True).distinct()` найти авторов. На каждого дописать строку в список `protected` из кортежа, который возвращает родитель: `f"Журнал действий сотрудников — записи автора {manager_label(user)}"`. И один раз вызвать `messages.error`: «Учётная запись — автор записей журнала действий сотрудников. Удаление стёрло бы автора: заблокируйте сотрудника вместо удаления.»
    - Непустой `protected` останавливает удаление штатно: `delete_view` не выполняет POST (`if request.POST and not protected`), `delete_selected` не выполняет `post=yes` и снова показывает подтверждение. Модели, миграции и права не меняются: `on_delete=PROTECT` у `AuditLog.user` потребовал бы миграцию и запретил бы удалять суперпользователя, а его записей в ленте нет.
    - Критерий тот же, что у ленты (решение 3): автор не суперпользователь. Текущий `is_staff` и `is_active` не учитываются: заблокированного и бывшего сотрудника с записями тоже не удалить. Суперпользователя с записями удалить можно. Пользователя без записей ленты — тоже, как раньше.
    - Существующее предупреждение про ответственного менеджера и правила регионов не меняется. При обоих условиях показываются оба сообщения.
    - `STAFF_ACTIONS` импортируется из листового `apps/common/staff_actions.py` на уровне модуля (решение 2), без цикла.

## Acceptance Criteria

### AC1 — вход и отказ

**Given** руководитель, менеджер, маркетолог, сотрудник без группы, заблокированный руководитель, суперпользователь, суперпользователь в группе «Руководители» и аноним
**When** каждый открывает `/supervisor/journal/`
**Then** руководитель получает 200, в HTML — «FREESPORT — Руководитель» и заголовок «Журнал действий»
**And** остальные получают 302 ровно на `/supervisor/login/?next=/supervisor/journal/`
**And** руководитель на `/manager/journal/` и `/marketing/journal/` получает 404
**And** просмотр ленты не пишет ни одной записи `AuditLog`

### AC2 — каждое действие перечня пишет ровно одну запись и видно в ленте (FR-42-30)

**Given** перечень действий `section-contents.md` и таблица сверки этой стори
**When** тест выполняет каждое действие настоящим запросом под соответствующей ролью:
- менеджер в `/manager/`:
  - верификация на странице подтверждения, без кандидата, с ролью, отличной от текущей (это и «смена роли»);
  - верификация действием списка;
  - отказ на странице подтверждения и действием списка;
  - блокировка и разблокировка действием списка и флагом «Активен» в карточке;
  - сброс пароля клиенту;
  - привязка к 1С действием списка;
  - правка трек-номера и даты доставки за одно сохранение;
- руководитель:
  - назначение ответственного менеджера вручную, переназначение другому, снятие флага «вручную»;
  - создание, правка и удаление правила региона;
  - создание сотрудника, блокировка и разблокировка, смена группы, сброс пароля сотруднику.

**Then** по каждому действию добавляется ровно одна запись `AuditLog` ожидаемого кода, автор — сотрудник, объект — клиент, заказ, правило или сотрудник
**And** действие, не написавшее запись или написавшее две, — провал теста с русским названием действия в `id` и сообщении
**And** руководитель видит в ленте ровно одну строку этого действия с литералами «Действие» и «Подробности» из решения 4 и ссылкой на объект из решения 5
**And** подтверждение заявки с кандидатом 1С пишет две записи — `verify_b2b` и `link_1c_customer`, по одной каждого вида

### AC3 — вид строки, ссылки, отсутствие технических полей

**Given** записи о клиенте, заказе, правиле региона и сотруднике; запись о клиенте, удалённом после действия; запись об удалённом правиле. У всех записей `ip_address="203.0.113.7"` и `user_agent="JournalAgent/1.0"`
**When** руководитель открывает ленту
**Then** каждая строка читается как «дата — сотрудник — действие — объект»: дата `ДД.ММ.ГГГГ ЧЧ:ММ` по Москве, сотрудник — «ФИО (email)»
**And** объект — ссылка:
- клиент — `/manager/users/user/<pk>/change/`;
- заказ — `/manager/orders/order/<pk>/change/`, подпись «Заказ <номер в формате UI>»;
- правило — `/supervisor/common/managerroutingrule/<pk>/change/`;
- сотрудник — `/supervisor/users/user/<pk>/change/`;
- удалённые клиент и правило — подпись без ссылки (email из записи, `str(rule)` из записи)

**And** в HTML нет `203.0.113.7`, `JournalAgent/1.0`, ключей JSON (`role_before`, `"fields"`, `{"`) и ни одного `href="/admin/`
**And** сотрудник с именем `<b>X</b>` и правило с таким email выводятся экранированными
**And** запись `change_routing_rule` со сменой менеджера показывает «менеджер: <ФИО (email) A> → <ФИО (email) B>», а запись `update_order` — «дата доставки: 20.10.2026 → 25.10.2026»
**And** запись `assign_responsible_manager` показывает «<ФИО (email) A> → <ФИО (email) B>»; запись с почтой, которой в базе нет, — саму почту; запись с `old=None` — «— → <ФИО (email) B>»

### AC4 — фильтры по сотруднику и периоду

**Given** записи менеджера A, менеджера B и руководителя; записи 12.10.2026 в 23:59 по Москве, 13.10.2026 в 00:00 по Москве и 09.10.2026 в 21:30 UTC (10.10 00:30 по Москве); сегодня 17.10.2026 (`patch` `django.utils.timezone.now`)
**When** руководитель выбирает сотрудника A
**Then** остаются только записи A
**When** период 10.10.2026 — 12.10.2026
**Then** записи 12.10 23:59 и 10.10 00:30 по Москве входят, 13.10 00:00 — нет
**When** указан только `date_from=2026-10-13` или только `date_to=2026-10-12`
**Then** лента ограничена с одной стороны
**When** сотрудник и период указаны вместе
**Then** остаются записи этого сотрудника за период
**And** в выборе сотрудника — все сотрудники (`is_staff`, не суперпользователь), заблокированный — с « — заблокирован», бывший сотрудник со снятым `is_staff` и записями ленты — с « — бывший сотрудник»; клиентов без записей и суперпользователя в выборе нет
**And** ссылки периода («Всё время», «Сегодня», «7 дней», «30 дней», «Этот месяц», «Прошлый месяц») сохраняют выбранного сотрудника, выбранная выделена
**When** руководитель открывает ленту без параметров (сегодня 17.10.2026), есть записи 17.09.2026 в 23:59 и 18.09.2026 в 00:00 по Москве
**Then** период — 18.09.2026 — 17.10.2026: запись 18.09 00:00 входит, 17.09 23:59 — нет; поля формы — `2026-09-18` и `2026-10-17`; выделена ссылка «30 дней»; подпись «Период: 18.09.2026 — 17.10.2026»
**And** с одним `?staff=<pk A>` действует тот же период по умолчанию
**When** руководитель открывает «Всё время» (`?date_from=&date_to=`)
**Then** запись 17.09 23:59 в ленте, выделена «Всё время», подпись «Период: всё время»
**When** `date_from` позже `date_to`, `date_to=9999-12-31` или `staff` — несуществующий id или `abc`
**Then** страница 200, над формой «Фильтр указан неверно — записи не показаны.» и ошибка поля или формы («Начало периода позже его конца.» / «Конец периода вне допустимого диапазона.»), строк ленты нет

### AC5 — только действия сотрудников трёх ролей

**Given** записи `role_from_1c` без автора (импорт 1С); `block_user` от суперпользователя; запись сотрудника с кодом вне перечня (`sync_customer`); плюс записи заблокированного менеджера, сотрудника, выведенного из групп, и бывшего сотрудника, у которого снят `is_staff`
**When** руководитель открывает ленту
**Then** первых трёх в ленте нет
**And** записи заблокированного, выведенного из групп и бывшего сотрудника в ленте есть, автор — «ФИО (email)»

### AC6 — порядок и страницы

**Given** 230 записей сотрудников
**When** руководитель открывает ленту
**Then** сверху самая новая, при равном времени — с большим pk; «Записей: 230»; на странице 100 строк, «Страница 1 из 3»
**And** ссылка «Старее →» ведёт на `?page=2` с сохранением `staff` и дат; без дат в адресе в ссылке явно стоит период по умолчанию; `?page=99` показывает последнюю страницу

### AC7 — число запросов (NFR-42-04)

**Given** 5 записей всех видов объектов (клиент, сотрудник, заказ, правило со сменой менеджера, удалённый клиент)
**When** руководитель открывает ленту, затем добавляется ещё 195 записей тех же видов от 20 сотрудников, и лента открывается снова (страница 1 — 100 строк, затем страница 2)
**Then** число SQL-запросов одинаковое (`django_assert_num_queries(baseline)`, как `TestQueryCount` стори 42.7)
**And** то же при фильтре по сотруднику и периоду

### AC8 — главная и ссылки раздела

**Given** руководитель
**When** он открывает `/supervisor/`
**Then** блок «Разделы» — ровно: «Сводка — заявки, заказы и выручка» (`/supervisor/summary/`), «Журнал действий сотрудников» (`/supervisor/journal/`), «Клиенты и заказы — без фильтра по менеджеру» (`/manager/`), «Маркетинг» (`/marketing/`)
**When** он открывает ленту с записями всех видов и с фильтром в адресе
**Then** хлебные крошки ведут на `/supervisor/`, «Изменить пароль» и «Выйти» — в `/supervisor/…`, ссылок в `/admin/` нет

### AC9 — сброс пароля и журнал атомарны (R42.7-D2)

**Given** клиент менеджера и управляемый сотрудник руководителя
**When** сброс пароля выполняется прямым вызовом метода админки (без `ATOMIC_REQUESTS` тестовых настроек, как `action_request` в `test_supervisor_section.py`), а `AuditLog.log_action` падает
**Then** исключение проходит наружу, пароль прежний, записи нет — в `/supervisor/` (это исправление) и в `/manager/` (уже атомарно своей обёрткой, тест закрепляет)
**And** без сбоя пароль сменён и запись `change_password` одна, как раньше

### AC10 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `black --check`, `isort --check-only`, `flake8`, `mypy`, `makemigrations --check`
**Then** всё зелёное, миграций нет
**And** из ожиданий существующих тестов меняется только список ссылок главной (решение 9)

### AC11 — автора записей ленты нельзя удалить (решение 13)

**Given** суперпользователь в `/admin/`; менеджер с записью `block_user`; заблокированный менеджер с записью; бывший сотрудник со снятым `is_staff` и записью; менеджер без записей ленты; другой суперпользователь с записью `block_user`
**When** суперпользователь удаляет каждого из карточки (`POST /admin/users/user/<pk>/delete/`, `post=yes`) и действием `delete_selected`
**Then** у трёх авторов записей — страница 200, текст «Учётная запись — автор записей журнала действий сотрудников. Удаление стёрло бы автора: заблокируйте сотрудника вместо удаления.», учётная запись на месте, записи `AuditLog` с прежним автором
**And** при `delete_selected` с автором и менеджером без записей в одной выборке не удаляется никто: подтверждение показывается снова
**And** менеджер без записей ленты и суперпользователь с записью удаляются (302), как раньше
**And** менеджер с клиентами и записями показывает оба предупреждения: про ответственного и про журнал

## Tasks / Subtasks

- [x] **Task 0 — GitNexus pre-flight** (AGENTS.md, `.windsurf/rules/gitnexus.md`)
  - [x] `npx gitnexus status` — при `stale` попросить Alex выполнить `! npx gitnexus analyze --force`. При подготовке стори индекс `up-to-date` на `abf8410`.
  - [x] Сверить таблицу «GitNexus: зона изменений» с текущим индексом (`impact <symbol> --direction upstream --summary-only -r "C:\Users\1\DEV\FREESPORT"`). Сообщить Alex blast radius:
    - меняются `SupervisorAdminSite` (MEDIUM — оценка по импортам модуля), `UserAdmin.user_change_password` (LOW) и `UserAdmin.get_deleted_objects` (UNKNOWN — хук Django, 2 вызова отброшены индексом);
    - `scope_clients` (**CRITICAL**), `scope_orders` (HIGH), `AuditLog`/`log_action` (CRITICAL), `period_presets` (LOW) **только читаются**.

- [x] **Task 1 — страница на сайте руководителя** (AC1, AC8; решения 1, 8, 9)
  - [x] `backend/freesport/admin_site.py`:
    - путь `journal/` в `SupervisorAdminSite.get_urls()` до `super().get_urls()`;
    - `journal_view`;
    - ссылка «Журнал действий сотрудников» второй в `supervisor_sections`;
    - docstring класса.
  - [x] `backend/templates/admin/supervisor/journal.html` (решение 8).

- [x] **Task 2 — модуль ленты** (AC2–AC7; решения 2–7, 11)
  - [x] Новый листовой `backend/apps/common/staff_actions.py`: только `STAFF_ACTIONS`, без импортов (решение 2).
  - [x] Новый `backend/apps/common/staff_journal.py`: `PER_PAGE`, `DEFAULT_DAYS`, `JournalFilterForm`, `journal_filter`, `journal_records`, `describe`, `build_rows`, `build_journal(request) -> dict`. Ключи контекста шаблона: `filter_form`, `period_links`, `period_label`, `page_obj`, `paginator`, `rows`, `newer_url`, `older_url`, `filter_invalid`.
  - [x] Подписи объектов и авторов — по одному запросу на вид объекта на страницу (решение 5), без запроса на строку.

- [x] **Task 3 — R42.7-D2** (AC9; решение 12)
  - [x] `backend/apps/users/admin.py`: `UserAdmin.user_change_password` — вызов родителя и `AuditLog.log_action` в одном `transaction.atomic()`; комментарий — почему.
  - [x] `_bmad-output/implementation-artifacts/deferred-work.md`: R42.7-D2 — «закрыто стори 42.9».

- [x] **Task 3a — запрет удалять автора записей ленты** (AC11; решение 13)
  - [x] `backend/apps/users/admin.py`: импорт `STAFF_ACTIONS` из `apps.common.staff_actions` на уровне модуля; в `UserAdmin.get_deleted_objects` — один запрос авторов, строки в `protected`, `messages.error`; комментарий — почему (`SET_NULL` стёр бы автора).
  - [x] Предупреждение про ответственного и правила регионов не трогать.

- [x] **Task 4 — тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [x] `backend/tests/integration/test_staff_journal.py` (integration, транзакционные: autouse `clear_db_before_test`, группы — `role_groups`, правила — `no_routing_rules`).
    - Хелперы — явным импортом, не `import *`, нового модуля хелперов не заводить (правило 42.4):
      - из `tests.integration.test_manager_clients_section`: `role_groups`, `no_routing_rules`, `verified_email_task`, `make_staff_member`, `make_client`, `make_1c_record`, `region_tax_id`, `get_unique_suffix`, `change_url`, `verify_url`, `password_url`, `post_action`, `form_payload`, `PASSWORD`, `NEW_PASSWORD`, `manager`, `manager_client`, `other_manager`;
      - из `tests.integration.test_manager_orders_section`: `make_master`, `order_change_url`, `card_payload`;
      - из `tests.integration.test_supervisor_section`: `supervisor`, `supervisor_client`, `logged_in`, `superuser_client`, `post_staff_action`, `staff_create_payload`, `staff_change_url`, `staff_password_url`, `client_change_url`, `rule`, `rule_payload`, `rule_change_url`, `RULES_ADD_URL`, `STAFF_ADD_URL`, `action_request`, `count_queries`.
    - Записи для AC3–AC7 создавать `AuditLog.log_action(...)` напрямую (быстро). Время — `AuditLog.objects.filter(pk=…).update(created_at=…)` (`auto_now_add`).
    - AC2 — только настоящими запросами.
    - Строки ленты — из `response.context["rows"]`, а ссылки и отсутствие технических полей — по HTML.
  - [x] AC9 — прямой вызов метода админки с `RequestFactory`-запросом (`request.user`, `request._messages`, `request._dont_enforce_csrf_checks = True` — у `user_change_password` есть `csrf_protect_m`) и `patch.object(AuditLog, "log_action", side_effect=RuntimeError(...))`. Ожидание — `pytest.raises(RuntimeError)`, затем `check_password(PASSWORD)` у цели и отсутствие записи. Варианты: `ManagerClientAdmin(User, manager_site)` и `SupervisorStaffAdmin(User, supervisor_site)`; объекты брать из реестра сайта (`manager_site._registry[User]`).
  - [x] AC11 — класс `TestDeleteGuard` в `test_staff_journal.py`: настоящие запросы `superuser_client` к `admin:users_user_delete` и `delete_selected` (образец — `test_responsible_manager_events.py::test_admin_delete_view`, `test_admin_bulk_delete`). Записи — `AuditLog.log_action(...)` напрямую.
  - [x] `backend/tests/unit/test_staff_journal.py` (unit, `django_db` там, где нужен `User`):
    - `set(STAFF_ACTIONS) ==` литеральный набор из 14 кодов решения 4 (`STAFF_ACTIONS` — из `apps.common.staff_actions`);
    - `describe` на каждом коде, на обоих `mode` у `verify_b2b`, на `details` без ожидаемых ключей (вывод «—», без исключения) и на неизвестной роли;
    - `JournalFilterForm` — пустая, только `date_from`, только `date_to`, перевёрнутая, `date.max`, нецифровой `staff`;
    - `journal_filter` на 17.10.2026: без ключей дат — `2026-09-18`…`2026-10-17`; только `staff` — то же; `date_from=&date_to=` — без периода; одна дата — без подстановки второй;
    - `reverse("supervisor:journal") == "/supervisor/journal/"`, `resolve("/supervisor/journal/").url_name == "journal"`.
  - [x] Правка ожидания `test_supervisor_summary.py::TestLinks::test_index_links_summary_first` (решение 9).
  - [x] **Проверка мутациями** — по каждой защите временно убрать её, убедиться, что падает названный тест, вернуть. Скрипт в контейнере, исходник восстанавливается побайтно в `finally`. Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | свой путь после `super().get_urls()` вместо до | AC1 (руководитель — 404) |
    | `action__in=STAFF_ACTIONS` | AC5 (`role_from_1c` и `sync_customer` в ленте) |
    | `user__is_superuser=False` | AC5 (запись суперпользователя в ленте) |
    | `user__isnull=False` / критерий «не суперпользователь» → `user__is_staff=True` | AC5 (запись бывшего сотрудника со снятым `is_staff` пропала) |
    | подзапрос авторов в queryset выбора сотрудника | AC4 (бывшего сотрудника нет в выборе) |
    | `Q(email__in=…)` в общем запросе пользователей | AC3 (почта вместо «ФИО (email)» в назначении) |
    | строка в `protected` у `get_deleted_objects` | AC11 (автор записей удалён из карточки и через `delete_selected`) |
    | `user__is_superuser=False` в охране удаления | AC11 (суперпользователь с записью не удаляется) |
    | `+ timedelta(days=1)` у конца периода | AC4 (запись 12.10 23:59 не вошла) |
    | `make_aware` по поясу проекта → UTC | AC4 (запись 09.10 21:30 UTC) |
    | `-pk` во втором ключе сортировки | AC6 (порядок записей одной секунды) |
    | проверка `scope_clients` у ссылки клиента (ссылка всем `User`) | AC3 (сотрудник получил ссылку в `/manager/`) |
    | ветка сотрудника у ссылки (`supervisor:users_user_change`) | AC3 (у сотрудника нет ссылки) |
    | общий запрос пользователей → запрос на строку | AC7 |
    | ветка `mode=link_only` в `describe` | unit `describe` |
    | `transaction.atomic()` в `UserAdmin.user_change_password` | AC9, вариант `/supervisor/` (пароль сменён без записи); вариант `/manager/` остаётся зелёным — его держит своя обёртка |
    | неверная форма → «показать всё» вместо «ничего» | AC4 (строки при ошибке фильтра) |
    | период по умолчанию не подставляется | AC4 (запись 17.09 в ленте без параметров) |
    | `- timedelta(days=DEFAULT_DAYS - 1)` → `DEFAULT_DAYS` | AC4 (запись 17.09 23:59 вошла), unit `journal_filter` |
    | умолчание по «нет непустых дат» вместо «нет ключей» | AC4 («Всё время» снова 30 дней) |
    | ссылки страниц из `request.GET` вместо дополненных данных | AC6 (в ссылке нет дат по умолчанию) |
    | `staff` в ссылках периода | AC4 (ссылка периода теряет сотрудника) |
    | ссылка «Журнал» на главной | AC8 |
    | `log_action` в `block_staff` (временно) | AC2 — провал с id «Блокировка сотрудника» |

- [x] **Task 5 — существующие тесты и проверки**
  - [x] Без правок зелёные: `tests/integration/test_responsible_manager_events.py` (удаление менеджера в `/admin/`, в том числе `test_admin_delete_unused_manager`: у менеджера из фабрики нет записей ленты — проверить при реализации, а не на слово), `tests/integration/test_supervisor_section.py`, `test_supervisor_summary.py` (кроме решения 9), `test_manager_clients_section.py`, `test_manager_orders_section.py`, `test_marketing_section.py`, `test_staff_access_lockdown.py`; `tests/unit/test_supervisor_admin_site.py`, `test_supervisor_summary.py`, `test_users_admin.py`, `tests/unit/test_services/test_verify_b2b_application.py`, `test_link_1c_customer.py`.
  - [x] Полный backend-прогон в Docker, один compose-проект, в фоне: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` (~18 мин; ориентир после 42.8 — 4667 passed, 76 skipped, 0 failed).
  - [x] Линтеры — строго после зачётного pytest, в том же `-p freesport-test`: `black --check .`, `isort --check-only .` (вывод не через `tail`), `flake8`, `mypy .`. Базис — ноль ошибок.
  - [x] `makemigrations --check --dry-run` — миграций нет. `check_openapi_sync` не нужен: API не меняется.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [x] `npx gitnexus check --cycles -r "C:\Users\1\DEV\FREESPORT"` — базовый цикл `HomePage.tsx → index.ts → HomePage.tsx` и отложенный R42.7-D1 (`users/models.py → staff_roles.py → users/models.py`), новых нет. В частности, нет `users/admin.py → common/staff_journal.py`: `users/admin.py` импортирует только листовой `staff_actions.py`.
  - [x] Completion Notes: отклонения от стори с причиной, ответы Alex на вопросы ниже, шаги выката.

### Review Findings

Код-ревью 18.10.2026, круг 1 (`759efa2c` → рабочее дерево, только `backend/`; слои через плагин Codex: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor, Graph Impact). Graph Impact находок не дал: несогласованных вызывающих нет, `check --cycles` — только существующие циклы.

- [x] [Review][Patch] R42.9-1 (low) `_int_id` проверяет `isdigit()`, а `int()` принимает не всё, что эта проверка пропускает: для `resource_id="²"` `isdigit()` → `True`, `int()` → `ValueError`, и вся страница отвечает 500 вместо подписи без ссылки (решение 5: «нецифровой id в запросы не идёт»). Заменить на `isdecimal()` и добавить `"²"` в unit-тест неожиданных форм [backend/apps/common/staff_journal.py:367]
- [x] [Review][Patch] R42.9-2 (low) При ошибке фильтра быстрые ссылки периода теряют сотрудника: `build_journal` берёт `staff` из `cleaned` только при `valid`, поэтому после `?staff=<A>&date_from=2026-10-12&date_to=2026-10-10` ссылка «30 дней» откроет ленту всех сотрудников. Брать `staff` из `form.cleaned_data` и при неверной форме (ошибки дат его не убирают; неверный `staff` в `cleaned_data` не попадёт), плюс проверка ссылки в AC4-сценарии неверной формы [backend/apps/common/staff_journal.py:515]
- [x] [Review][Patch] R42.9-3 (low) `TestQueryCount` не ловит запрос на каждый уникальный объект: все 200 записей ссылаются на один и тот же набор клиента, сотрудника, заказа и правила, поэтому запрос на каждый уникальный заказ (или клиента) дал бы одинаковое число запросов в обоих замерах. Во втором наборе раздать записи по разным клиентам, заказам и правилам [backend/tests/integration/test_staff_journal.py:1038]
- [x] [Review][Patch] R42.9-4 (low) Нет сценария заказа, которого руководитель не видит в `/manager/`: все заказы тестов доступны, и удаление условия `if pk in visible_orders` не уронит ни один тест, а историческая запись получит ссылку на 404. Добавить запись `update_order` о заказе клиента, переведённого в сотрудники: подпись «Заказ …» есть, ссылки нет [backend/apps/common/staff_journal.py:465]

**Rejected (8):**

- Повышение сотрудника до суперпользователя скрывает его прошлые записи и снимает охрану удаления (Blind Hunter) — критерий «текущий `is_superuser`» выбран решениями 3 и 13 и AC11 («суперпользователя с записью удалить можно»); фикс — правка стори.
- Гонка между проверкой авторов в `get_deleted_objects` и удалением (Blind Hunter, Edge Case Hunter) — low: нужно, чтобы удаляемый сотрудник сделал первое действие из перечня в миллисекунды между открытием подтверждения и POST; фикс — блокировки строк, лишняя сложность.
- Вложенные `dict`/`list` в значениях `fields` выводятся через `str()` (Blind Hunter, Acceptance Auditor) — low: все 14 мест записи кладут в `old`/`new` скаляры, вложенную структуру программа не создаёт; вывод экранирован; фикс — проверки типов в каждом форматтере.
- Назначение подписывается по текущему владельцу почты: после переиспользования email подпись чужая (Blind Hunter) — так задано решением 4 (в журнале лежат почты, подпись — учётная запись с этой почтой); фикс — изменить запись журнала, а это вне стори.
- Пагинация смещением дублирует строку, если между переходами появилась новая запись (Blind Hunter) — Paginator с `get_page` задан решением 7; поведение штатное для админки Django, вреда для разбора нет.
- Нет авторских действий маркетолога в сценариях (Blind Hunter) — false: в перечне нет действий маркетинга («Чего в этой стори нет», решение 15 стори 42.6).
- Вход через `/supervisor/login/` не проверен, тесты используют `force_login` (Blind Hunter) — low: страница входа — штатный `AdminSite.login` сайта 42.7, AC1 проверяет точный редирект; стори вход не меняет.
- Нет замеров времени и планов запросов на большом журнале (Blind Hunter) — решение 11: без новых индексов, реальных записей нет, индекс по `created_at` — когда объём потребует.

## Dev Notes

### Текущее состояние кода (сверено на `abf84102`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py:157-215` `SupervisorAdminSite` | `get_urls` — `summary/` до родительских; `summary_view`; `index` кладёт `supervisor_sections` (сводка, `/manager/`, `/marketing/`) | + путь `journal/`, `journal_view`, ссылка «Журнал» второй |
| `backend/freesport/admin_site.py:39-66` `StaffSectionAdminSite.has_permission` | активный сотрудник из `section_groups`, не суперпользователь; кэш `request._staff_section_access` | не меняется — им же закрыта лента |
| `backend/apps/common/models.py:321-426` `AuditLog`, `log_action` | `user` (SET_NULL), `action`, `resource_type`, `resource_id` (строка), `details` (`changes` внутри), `ip_address`, `user_agent`, `created_at`; `ordering = ["-created_at"]`; индексы `(user, action, created_at)`, `(resource_type, resource_id, created_at)` | не меняется, лента читает |
| `backend/apps/common/admin.py:36` `AuditLogAdmin` | сырой журнал в `/admin/` (только суперпользователь) | не меняется; в разделах сотрудников не регистрируется |
| `backend/apps/common/supervisor_admin.py:33-48` `LOGGED_RULE_FIELDS`, `_changed_fields` | поля правила в журнале и формат `{имя: {old, new}}` | не меняется; порядок полей в подробностях |
| `backend/apps/orders/manager_admin.py:169-175` `_audit_value`; `EDITABLE_FIELDS` | даты в журнале — ISO, пустое — `None`; правимые поля заказа | не меняется; формат подробностей `update_order` |
| `backend/apps/users/admin.py:554-576` `UserAdmin.user_change_password` | родитель сохраняет пароль, затем вне транзакции `AuditLog` | + `transaction.atomic()` (R42.7-D2) |
| `backend/apps/users/admin.py:537-552` `UserAdmin.get_deleted_objects` | один хук на карточку и `delete_selected`; только `messages.error` про ответственного и правила (удаление блокирует `PROTECT`) | + строки в `protected` и сообщение для автора записей ленты (решение 13) |
| `backend/apps/users/manager_admin.py:404-409` `ManagerClientAdmin.user_change_password` | при POST — `transaction.atomic()` + `_lock_client`, внутри — родитель с журналом | не меняется; в `/manager/` разрыва R42.7-D2 уже нет |
| `backend/apps/users/manager_admin.py:41-52` `scope_clients` | руководителю — все, кроме сотрудников | не меняется; видимость ссылки на клиента |
| `backend/apps/orders/manager_admin.py:82-95` `scope_orders` | мастер-заказы; руководителю — и без клиента | не меняется; видимость ссылки на заказ |
| `backend/apps/users/supervisor_admin.py:241-255` `SupervisorStaffAdmin.get_queryset` | сотрудники `is_staff=True, is_superuser=False` | не меняется; критерий ссылки на сотрудника |
| `backend/apps/users/staff_roles.py:91-94` `manager_label` | «ФИО (email)» | не меняется; подписи авторов, объектов, выбора сотрудника |
| `backend/apps/orders/supervisor_summary.py:89-126` `Period`, `period_presets` | пресеты периода сводки | не меняется; ссылки периода ленты |
| `backend/apps/orders/services/order_numbering.py:72` `format_order_number` | канонический номер → вид UI (мастер `CCCC-YYNNN`) | не меняется; подпись заказа |
| `backend/templates/admin/supervisor/summary.html` | образец формы, ссылок периода и таблиц | не меняется; образец для `journal.html` |

### GitNexus: зона изменений

Индекс `up-to-date` на `abf8410`. Команды — `npx gitnexus impact <symbol> --direction upstream --summary-only -r "C:\Users\1\DEV\FREESPORT"` и `--include-tests --depth 2`.

| Символ | Изменение | risk | Прямые вызывающие (`byDepth.1`) | Затронутые процессы | Тесты (`--include-tests`) |
|---|---|---|---|---|---|
| `SupervisorAdminSite` (`freesport/admin_site.py`, `--kind Class`) | + путь `journal/`, `journal_view`, ссылка в `index` | MEDIUM (16, lower-bound: 9 прямых — модули, импортирующие `admin_site.py`) | `*/supervisor_admin.py`, `*/marketing_admin.py`, `orders/users manager_admin.py`, `freesport/urls.py` | 0 | `test_supervisor_section.py`, `test_supervisor_summary.py` (int + unit), `test_supervisor_admin_site.py`, `test_manager_*`, `test_marketing_*`, `test_media_url_guards.py` |
| `SupervisorAdminSite.get_urls` | + путь `journal/` | UNKNOWN (вызывает Django, 2 вызова отброшены индексом — ожидаемо) | — | — | `test_supervisor_summary.py` (AC1, `resolve`) |
| `SupervisorAdminSite.index` (`--file freesport/admin_site.py`, неоднозначно — 3 `index`) | + ссылка «Журнал» | UNKNOWN (хук Django) | — | — | `test_supervisor_summary.py::TestLinks::test_index_links_summary_first` (ожидание меняется), `test_supervisor_section.py::TestLinksAndIndex::test_index` |
| `UserAdmin.user_change_password` (`users/admin.py`) | + `transaction.atomic()` | LOW (2, lower-bound: 1 вызов отброшен индексом) | `ManagerClientAdmin.user_change_password`, `SupervisorStaffAdmin` (наследование) | процесс `user_change_password` раздела (9) | граф тестов не нашёл; по факту: `test_manager_clients_section.py::TestAuditLog::test_password_change`, `test_supervisor_section.py` (сброс пароля сотруднику), `tests/unit/test_users_admin.py` |
| `UserAdmin.get_deleted_objects` (`--file backend/apps/users/admin.py`) | + охрана удаления автора записей ленты | UNKNOWN (0 прямых; 2 вызова отброшены индексом — вызывает Django: `delete_view`, `delete_selected`) | — | 0 | граф не нашёл; по факту `test_responsible_manager_events.py` (`test_admin_delete_view`, `test_admin_bulk_delete`, `test_admin_delete_unused_manager`) |
| `scope_clients` (`users/manager_admin.py`) | **не меняется**, только чтение | **CRITICAL** (21; было HIGH на 42.8 — добавились процессы сводки) | `ManagerClientAdmin.get_queryset`, `ResponsibleManagerFilter.lookups`, `scope_orders`, `manager_queue`, функции сводки | `user_change_password`, `change_view`, `verify_b2b_view`, `build_summary` | — |
| `scope_orders` (`orders/manager_admin.py`) | **не меняется**, только чтение | HIGH (8) | `ManagerOrderAdmin.get_queryset`, `ManagerOrderForm.clean`, `manager_queue`, `_period_orders` | `build_summary`, `orders_by_region`, `get_queryset` | — |
| `AuditLog` (`--kind Class`), `AuditLog.log_action` | **не меняются**, только чтение | CRITICAL (68 / 30) | 15 мест записи (таблица сверки) | `verify_b2b_view`, `link_1c_customer`, `user_change_password`, `block_staff`, `unblock_staff` … | `test_verify_b2b_application.py`, `test_link_1c_customer.py`, `test_responsible_manager_events.py`, `test_manager_orders_section.py` и др. |
| `period_presets` (`orders/supervisor_summary.py`) | **не меняется**, переиспользуется | LOW (2) | `build_summary` | `build_summary` | `tests/unit/test_supervisor_summary.py` |
| `manager_label` (`users/staff_roles.py`) | не меняется, подписи | LOW (5) | `ResponsibleManagerFilter.lookups`, `build_summary` | `build_summary` | `test_supervisor_section.py`, `test_supervisor_summary.py` |

Новые символы (`staff_actions.py`, `staff_journal.py`, `SupervisorAdminSite.journal_view`) появятся в индексе после `analyze`. Строка `get_deleted_objects` снята 18.10.2026 на индексе `abf8410`. HEAD `17a99df7` — merge-коммит без изменений файлов относительно `abf84102`.

### Подводные камни

- **Catch-all `AdminSite`.** Путь `journal/` — только перед `super().get_urls()` (как `summary/`, решение 1 стори 42.8).
- **`current_app`.** Присваивание `request.current_app = self.name` обязательно. `reverse("manager:…")` и `reverse("supervisor:…")` с явным пространством имён резолвятся и без него, но `{% url 'admin:index' %}` в шаблоне и `each_context` опираются на него.
- **`resource_id` — строка.** `pk__in` строит из целых: `int(value)` для цифровых, остальные пропустить. Не сравнивать `str(pk)` с `int`.
- **`details["changes"]` у старых записей бывает неполным** (записи до 42.4 без `source`, правила без `manager_email`). `describe` берёт значения через `.get()`, недостающее — «—». В шаблон не уходит ни `details`, ни `changes`.
- **`approve_b2b` и `verify_b2b`** — два кода одного смысла: действие списка и страница подтверждения. В ленте у них разные подписи, «Верификация клиента» и «Подтверждение B2B-заявки». Так руководитель видит, каким путём шло действие.
- **Страница подтверждения с кандидатом** пишет две записи (`verify_b2b` + `link_1c_customer`) — так задумано: это два действия перечня (тест `test_verify_page_with_link_writes_two_kinds` стори 42.4). Не «чинить» в одну.
- **Блокировка сотрудника переводит клиентов его правил на резерв без своих записей** (42.7, решение 12): причина — запись `block_staff`. Смена ИНН в карточке переназначает ответственного хуком 42.2 тоже без записи: это не решение сотрудника о назначении. В ленту ничего не добавлять.
- **`staff_accounts_q()` содержит `groups__name__in`** — через `filter()` даёт JOIN и дубли. Видимость клиента — только через `scope_clients` (там `exclude`, подзапрос).
- **`ModelChoiceField` на `staff` делает свой запрос при валидации (`.get`).** Это постоянная добавка к числу запросов, не на строку.
- **`ATOMIC_REQUESTS=True` в `settings/test.py`.** Через тестовый клиент сбой журнала откатил бы всё и без правки R42.7-D2. Поэтому AC9 — прямым вызовом метода админки (образец — `action_request` и `failing_journal` в `test_supervisor_section.py`). У `user_change_password` — `csrf_protect_m`: запросу `RequestFactory` нужно `_dont_enforce_csrf_checks = True`. `ManagerClientAdmin.user_change_password` сам открывает `atomic` и берёт блокировку строки (`_lock_client`) — прямой вызов идёт внутри `django_db`-транзакции теста, это допустимо; вариант `/manager/` проходит и до правки — он закрепляет уже существующую атомарность.
- **`auto_now_add`.** `created_at` записи журнала в тестах — только `update()` после создания.
- **Хук 42.2 назначает ответственного при создании клиента.** `make_client` ставит ответственного `update()` и флаг «вручную»; правила — autouse `no_routing_rules`. В AC2 действия руководителя с правилами задают правила сами (`rule(...)`).
- **Время в тестах** — `patch("django.utils.timezone.now", return_value=datetime(2026, 10, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")))`, как в сводке. `timezone.localdate()` берёт `now()`.
- **Неразрывных пробелов** в ленте нет (денег нет) — обычные пробелы и «—», «→» литералами.
- **Цикл импорта через перечень.** `STAFF_ACTIONS` нужен и `staff_journal`, и `users/admin.py`. Положить его в `staff_journal` — значит получить цикл `users/admin → common/staff_journal → users/manager_admin → users/admin`. Только листовой `staff_actions.py` (решение 2).
- **`protected` в `get_deleted_objects` — список строк.** Django выводит его в шаблоне подтверждения с автоэкранированием. `manager_label` с `<b>` в имени не ломает страницу.

### Выкат (для Completion Notes и Alex)

1. Миграций, ручных шагов в БД и правок nginx нет: локация `/supervisor/` (42.7) уже проксирует `/supervisor/journal/`.
2. После выката: `curl -sI https://optisport.ru/supervisor/journal/` → 302 на `/supervisor/login/?next=/supervisor/journal/`. Если 404 от Next — `docker compose exec nginx nginx -s reload` (memory: nginx держит старый IP upstream).
3. На проде в ленте сразу появятся старые записи сотрудников: `approve_b2b`, `block_user`, `change_password` и т. п. из `/admin/` до эпика 42, в частности `managermsk3@…`. Это ожидаемо (решение 3).
4. Сказать владельцу: с выката сотрудника, у которого есть записи ленты, в `/admin/` не удалить — только заблокировать (решение 13).

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет.
- `AdminSite.get_urls`/`admin_view`/`each_context`, `Paginator.get_page`, `ModelChoiceField`, `QueryDict.copy()/urlencode()` сверять по исходникам 5.2.7 в `backend/venv/Lib/site-packages/django/`. Веб-исследование версий не требуется: стек не меняется.
- Число запросов страницы не зависит от числа строк (NFR-42-04): постраничная выборка с `select_related("user")` и по одному запросу на вид объекта.
- Миграции, API, OpenAPI, фронтенд, nginx, CI не меняются.
- Язык: интерфейс, сообщения, комментарии, docstrings — русский (NFR-42-03).

### Тестирование

- Только Docker + PostgreSQL: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`; `--env-file` не передаётся; параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры по каталогу: `tests/unit/` → `unit`, `tests/integration/` → `integration`.
- Проверки доступа — критический модуль, покрытие ≥ 90 % (NFR-42-01): `freesport/admin_site.py`, `apps/common/staff_journal.py`.
- Ожидаемые подписи, тексты ошибок и URL — литералами, не из констант реализации (урок R42.5-7). `STAFF_ACTIONS` в тестах не импортировать для построения ожиданий — только для сверки набора кодов с литералом.
- Список действий AC2 — `pytest.mark.parametrize` с `ids` на русском. Тело варианта — функция-сценарий, которая возвращает `(автор, resource_type, resource_id)`. Таблицу сценариев держать в начале файла, рядом с ожидаемыми литералами.

### Уроки 42.4–42.8

- Главный риск ревью 42.7–42.8: защита есть, а теста, который упадёт без неё, нет. Здесь это фильтр ленты (служебные, суперпользователь, клиент), границы периода и атомарность пароля. Отсюда таблица мутаций.
- Ссылки раздела в закрытую `/admin/` или в 404 другого раздела — класс ошибок 42.4–42.8: AC3 и AC8.
- Восемь кругов ревью 42.8 ушли на тесты с недостаточно точными ожиданиями. Сразу закладывать литералы, точные множества (`==`, не `in`/`issubset`), границы с обеих сторон и проверку «список ровно такой».
- Отклонения от стори — в Completion Notes с причиной, не молча.
- Вывод `isort` не смотреть через `tail` (R42.5-D3); линтеры — после зачётного pytest, в `-p freesport-test` (memory).

### Связь с последующими стори

- **42.10** — массовая передача и замещение пишут новые коды (передача, начало и конец замещения; 42.7, «Связь»). Стори 42.10 обязана:
  - добавить их в `STAFF_ACTIONS` (`apps/common/staff_actions.py`) с подписями — тогда и охрана удаления (решение 13) учтёт их сама;
  - добавить ветки в `describe`;
  - добавить варианты в параметризацию AC2 `test_staff_journal.py`;
  - дополнить литеральный набор кодов в unit-тесте.

  Иначе записи молча не попадут в ленту.

### Project Structure Notes

- Новые файлы:
  - `backend/apps/common/staff_actions.py` (листовой, только перечень);
  - `backend/apps/common/staff_journal.py`;
  - `backend/templates/admin/supervisor/journal.html`;
  - `backend/tests/integration/test_staff_journal.py`;
  - `backend/tests/unit/test_staff_journal.py`.
- Изменяемые:
  - `backend/freesport/admin_site.py`;
  - `backend/apps/users/admin.py` (`user_change_password`, R42.7-D2; `get_deleted_objects`, решение 13);
  - `backend/tests/integration/test_supervisor_summary.py` (одно ожидание, решение 9);
  - `_bmad-output/implementation-artifacts/deferred-work.md` (R42.7-D2);
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`, этот файл.
- Модуль ленты — в `apps/common` рядом с `AuditLog` и журналом правил. Из `apps/orders` и `apps/users` он только импортирует; обратных импортов нет, `check --cycles` это подтверждает. `users/admin.py` импортирует только листовой `staff_actions.py`.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.9, FR-42-30, FR-42-31, NFR-42-01…04, UX Design Requirements (отдельные страницы по образцу `verify_b2b_view`, заголовок раздела).
- Контекст эпика: `_bmad-output/implementation-artifacts/epic-42-context.md` (журнал на `AuditLog`, «дата — сотрудник — действие — объект», без технических полей и служебных операций, число запросов).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-6, Constraints «Журнал строится на существующем `AuditLog`»), `section-contents.md` («Перечень действий для журнала (CAP-6)», «Руководитель» → «Журнал действий», «Ни одной из ролей»), `affected-code.md` (строка «Журнал»).
- Предыдущие стори:
  - `Story/42-3-…md` (решение 7: команда пересчёта записей не пишет);
  - `Story/42-4-…md` (AC7, коды менеджера, `test_verify_page_with_link_writes_two_kinds`);
  - `Story/42-5-…md` (решение 7: формат `update_order`);
  - `Story/42-6-…md` (решение 15: журнала маркетинга нет);
  - `Story/42-7-…md` (решение 12: коды и формат записей руководителя, «Связь» → 42.9);
  - `Story/42-8-…md` (образец страницы на `supervisor_site`, `period_presets`, «Связь» → 42.9).
- Отложенное: `_bmad-output/implementation-artifacts/deferred-work.md` → R42.7-D2.
- Код:
  - `backend/freesport/admin_site.py`;
  - `backend/apps/common/{models,admin,supervisor_admin}.py`;
  - `backend/apps/users/{admin,manager_admin,supervisor_admin,staff_roles}.py`;
  - `backend/apps/users/services/{verify_b2b_application,link_1c_customer,processor}.py`;
  - `backend/apps/orders/{manager_admin,supervisor_summary}.py`, `backend/apps/orders/services/order_numbering.py`;
  - `backend/templates/admin/supervisor/{index,summary}.html`.
- Правила: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `AGENTS.md` (GitNexus, Docker), `.windsurf/rules/gitnexus.md`, `.windsurf/rules/production-operations.md` (restart nginx).

## Вопросы к Alex — закрыты 18.10.2026

1. **Действия владельца (суперпользователя) в ленте не показываются** — да (решение 3).
2. **Период по умолчанию** — **последние 30 дней** (решение 6): с сегодня − 29 по сегодня, как быстрая ссылка «30 дней»; «Всё время» — отдельной ссылкой. 100 записей на страницу (решение 7).
3. **Старые записи сотрудников из `/admin/` до эпика 42** попадают в ленту — да (решение 3, «Выкат», п. 3).
4. **R42.7-D2 закрывается в этой стори** — да (решение 12, Task 3, AC9).
5. **Неверный фильтр — ошибка и пустая лента** — да (решение 6).
6. **Удалённый автор пропадал бы из ленты (`SET_NULL`)** — запретить удаление сотрудника, у которого есть записи журнала (решение 13, AC11, Task 3a). Варианты «показывать сироты» и «только регламент» отклонены.
7. **Назначение ответственного — «ФИО (email)» вместо почты** — да (решение 4, решение 5, AC3).
8. **Бывший сотрудник со снятым `is_staff` остаётся в ленте** — да: критерий автора — «не суперпользователь» (решения 3 и 6, AC4, AC5).
9. **Замер журнала на проде** — не нужен: проект не запущен, реальных записей менеджеров нет (решение 11 переписан без цифры).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code, `bmad-dev-story`.

### Debug Log References

- GitNexus pre-flight: индекс `stale` на `abf8410`; после `analyze --force` у Alex — `up-to-date` на `759efa2`. Таблица «GitNexus: зона изменений» сверена: `SupervisorAdminSite` MEDIUM (16, 9 прямых), `UserAdmin.user_change_password` LOW (2), `get_deleted_objects` UNKNOWN (хук Django), `scope_clients` CRITICAL (21), `scope_orders` HIGH (8), `period_presets` LOW (2), `manager_label` LOW (5) — совпадает со стори, последние четыре только читаются.
- Первый прогон новых тестов: 134 passed (61 unit + 73 integration).
- Круг 1 ревью (исправления): RED — упали `test_unusual_resource_ids_do_not_break_page[²]` и оба `test_period_links_keep_staff`; тесты R42.9-3/4 закрывают пробелы покрытия и были зелёными на старом коде, поэтому проверены мутациями: «ссылка на заказ без проверки видимости» — убита `test_order_not_visible_in_manager_has_no_link`; «запрос на каждый уникальный заказ» — убита `TestQueryCount::test_constant[all]` и `[staff-and-period]`. Исходник восстановлен побайтно.
- Круг 1 ревью, итоговые проверки: журнальные тесты 143 passed (134 + 9 новых); полный backend-прогон (`-n 4`, `not performance and not slow`) **4810 passed, 76 skipped, 0 failed**; `black`, `isort`, `flake8`, `mypy` (647 файлов) без замечаний; `makemigrations --check --dry-run` — «No changes detected». `detect-changes`: `_int_id`, `build_journal` и тесты; `check --cycles` — только базовые `users/models.py ↔ staff_roles.py` и `HomePage.tsx ↔ index.ts`. `impact`: `_int_id` LOW (1 прямой), `build_journal` LOW (1 прямой, `journal_view`).
- Проверка мутациями (скрипт в контейнере `freesport-test`, исходник восстанавливается побайтно в `finally`, после прогона `git status` без посторонних изменений): **24 из 24 убиты**. Две мутации (запрос на строку, ссылки страниц из `request.GET`) повторены после правки `mypy` на итоговом коде — убиты.

  | № | Убрано | Упал |
  |---|---|---|
  | 1 | свой путь после `super().get_urls()` | `TestEntry::test_supervisor_opens_journal` |
  | 2 | `action__in=STAFF_ACTIONS` | `TestOnlyStaffActions` |
  | 3 | `user__is_superuser=False` | `TestOnlyStaffActions` |
  | 4 | критерий автора → `user__is_staff=True` | `TestOnlyStaffActions` |
  | 5 | подзапрос авторов в выборе сотрудника | `TestFilters::test_staff_choices` |
  | 6 | `Q(email__in=…)` в общем запросе | `TestRows::test_responsible_assignment_labels` |
  | 7 | строка в `protected` | `TestDeleteGuard::test_author_card_delete_is_refused[*]`, `test_author_bulk_delete_is_refused[*]` |
  | 8 | `user__is_superuser=False` в охране удаления | `TestDeleteGuard::test_superuser_author_is_deleted` |
  | 9 | `+ timedelta(days=1)` у конца периода | `TestFilters::test_period_bounds` |
  | 10 | границы суток по UTC | `TestFilters::test_period_bounds` |
  | 11 | `-pk` в сортировке | `TestPages::test_order_and_pages` |
  | 12 | проверка `scope_clients` у ссылки клиента | `TestRows::test_staff_has_no_manager_link` |
  | 13 | ветка сотрудника у ссылки | `TestRows::test_staff_has_no_manager_link` |
  | 14 | общий запрос пользователей → запрос на строку | `TestQueryCount::test_constant[all]`, `[staff-and-period]` |
  | 15 | ветка `mode=link_only` | unit `test_describe[verify_b2b-link_only]` |
  | 16 | `transaction.atomic()` в `UserAdmin.user_change_password` | `TestPasswordAtomic::test_failed_journal_keeps_password[supervisor]`; вариант `[manager]` зелёный (своя обёртка) |
  | 17 | неверная форма → все записи | `TestInvalidFilter::test_error_and_no_rows[date-max, missing-staff, non-numeric-staff]` |
  | 18 | период по умолчанию не подставляется | `TestDefaultPeriod::test_without_params` |
  | 19 | `DEFAULT_DAYS - 1` → `DEFAULT_DAYS` | `TestDefaultPeriod::test_without_params`, unit `TestJournalFilterDefaults` (3) |
  | 20 | умолчание по «нет непустых дат» | `TestDefaultPeriod::test_all_time` |
  | 21 | ссылки страниц из `request.GET` | `TestPages::test_order_and_pages` |
  | 22 | `staff` в ссылках периода | `TestFilters::test_period_links_keep_staff_and_mark_selected` |
  | 23 | ссылка «Журнал» на главной | `TestLinks::test_index_sections` |
  | 24 | `log_action` в `block_staff` | `TestEveryActionIsJournaled` — «Блокировка сотрудника»: записей 0, ожидалась одна |

- Полный backend-прогон в Docker (`-n 4 -m "not performance and not slow"`): **4801 passed, 76 skipped, 0 failed** (19 мин 56 с; до стори — 4667 passed, +134 новых).
- Линтеры после зачётного прогона, `-p freesport-test`: `black --check .`, `isort --check-only .`, `flake8 .`, `mypy .` (647 файлов) — без замечаний. `makemigrations --check --dry-run` — «No changes detected».
- `npx gitnexus detect-changes --scope all`: 6 файлов, 9 символов — `UserAdmin`, `get_deleted_objects`, `user_change_password`, `SupervisorAdminSite`, `get_urls`, `journal_view`, `index`, `TestLinks`, `test_index_links_summary_first`; процессы `user_change_password` (2); risk medium. Новые файлы (`staff_actions.py`, `staff_journal.py`) git ещё не отслеживает, в отчёт они не входят.
- `npx gitnexus check --cycles`: только базовые `users/models.py → staff_roles.py → users/models.py` (R42.7-D1) и `HomePage.tsx → index.ts → HomePage.tsx`. Новых циклов нет, `users/admin.py` импортирует только листовой `staff_actions.py`.

### Completion Notes List

- ✅ Resolved review finding [low] R42.9-1: `_int_id` принимает только ASCII-десятичные цифры (`isascii() and isdecimal()`). Строже, чем предлагало ревью (`isdecimal()`): `int()` принял бы арабские цифры «١٢» и подпись сослалась бы на pk 12.
- ✅ Resolved review finding [low] R42.9-2: `build_journal` берёт `staff` и даты из `form.cleaned_data` и при неверной форме; ссылки периода сохраняют верно выбранного сотрудника, неверный `staff` в ссылки не попадает. «Выбрана» и подпись периода по-прежнему только при верной форме.
- ✅ Resolved review finding [low] R42.9-3: `TestQueryCount` держит по 4 различных клиента, сотрудника, заказа, правила и удалённого клиента; в замере 5 записей — по одному объекту, в замере 200 — по четыре. Мутация «запрос на каждый уникальный заказ» роняет оба варианта.
- ✅ Resolved review finding [low] R42.9-4: `TestRows::test_order_not_visible_in_manager_has_no_link` — заказ клиента, переведённого в сотрудники, без ссылки; заказ без клиента — со ссылкой. Мутация «ссылка на заказ всегда» роняет тест.
- Тест неожиданных форм `resource_id` вынесен в интеграционный `test_unusual_resource_ids_do_not_break_page` (`²`, `abc`, `-1`, `١٢`, 30 девяток) по всем трём видам объектов: unit-теста на `resource_id` в стори не было, а страница-целиком — то, что ломалось.

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Реализовано: лента `/supervisor/journal/` (`supervisor:journal`) — путь до catch-all, `journal_view`, ссылка «Журнал действий сотрудников» второй в «Разделах»; листовой перечень `apps/common/staff_actions.py` (14 кодов); модуль `apps/common/staff_journal.py` (`JournalFilterForm`, `journal_filter`, `journal_records`, `describe`, `build_rows`, `build_journal`, `PER_PAGE = 100`, `DEFAULT_DAYS = 30`); шаблон `admin/supervisor/journal.html`; R42.7-D2 — `transaction.atomic()` в `UserAdmin.user_change_password`; охрана удаления автора записей ленты в `UserAdmin.get_deleted_objects`.
- Тесты: `tests/unit/test_staff_journal.py` (61) и `tests/integration/test_staff_journal.py` (73) — AC1–AC9, AC11; AC10 — прогоны выше. Сверка перечня (AC2) — 22 действия настоящими запросами плюс отдельный тест страницы подтверждения с кандидатом 1С (две записи двух видов).
- **Единственное изменение ожиданий существующих тестов** — `test_supervisor_summary.py::TestLinks::test_index_links_summary_first`: добавлена пара `("/supervisor/journal/", "Журнал действий сотрудников")` (решение 9). `test_responsible_manager_events.py::test_admin_delete_unused_manager` прошёл без правок: `make_staff` этого файла записей ленты не создаёт.
- **Отклонения и уточнения:**
  1. `describe` у `change_routing_rule` пропускает поле, у которого «было» и «стало» выглядят одинаково. Журнал правил различает `""` и `None` у `manager_email` при создании и удалении, и без пропуска в подробностях стояло бы «email менеджера: — → —». Решение 4 этот случай не описывало.
  2. Второй аргумент `describe(record, users)` — `KnownUsers` (учётные записи страницы по pk и по email из одного запроса). Добавлены служебные `staff_choices`, `staff_choice_label`, `default_period`.
  3. «Записей нет» показывается и при неверном фильтре; «Страница N из M» — всегда, в том числе на одной странице.
  4. AC9: `action_request` стори 42.7 не подошёл — Django после смены пароля вызывает `update_session_auth_hash`, которому нужна `request.session`. В тесте свой `password_request` с `SessionStore` (signed cookies), `_messages` и `_dont_enforce_csrf_checks`.
  5. AC2 и AC8 входят в разделы двумя клиентами `logged_in(...)`, а не фикстурами `manager_client`/`supervisor_client`: обе построены на одном `client`. Импорт хелперов дополнен `order_emails` (autouse, письма заказов) и `failing_journal`.
  6. `id` вариантов AC2 русские, но pytest в выводе экранирует не-ASCII (`Б…`). Название действия читается в сообщении `assert`: «Блокировка сотрудника»: записей 0, ожидалась одна.
  7. Мутацию «неверная форма → все записи» вариант с перевёрнутым периодом не ловит: в `cleaned_data` остаются обе даты, и пустой полуинтервал сам даёт ноль строк. Мутацию убивают три других варианта.
- **Ответы Alex** (18.10.2026): все 9 вопросов закрыты при подготовке стори (раздел «Вопросы к Alex»); новых вопросов при реализации не возникло.
- **Выкат:**
  1. Миграций, ручных шагов в БД и правок nginx нет: локация `/supervisor/` уже проксирует `/supervisor/journal/`.
  2. После выката: `curl -sI https://optisport.ru/supervisor/journal/` → 302 на `/supervisor/login/?next=/supervisor/journal/`. Если 404 от Next — `docker compose exec nginx nginx -s reload`.
  3. В ленте сразу появятся старые записи сотрудников из `/admin/` до эпика 42 (`managermsk3@…` и др.) — это ожидаемо.
  4. Владельцу: с выката сотрудника с записями ленты в `/admin/` удалить нельзя, только заблокировать.

### File List

- `backend/apps/common/staff_actions.py` (новый)
- `backend/apps/common/staff_journal.py` (новый)
- `backend/templates/admin/supervisor/journal.html` (новый)
- `backend/freesport/admin_site.py`
- `backend/apps/users/admin.py`
- `backend/tests/integration/test_staff_journal.py` (новый)
- `backend/tests/unit/test_staff_journal.py` (новый)
- `backend/tests/integration/test_supervisor_summary.py`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/42-9-staff-action-journal.md`

### Change Log

- 2026-10-18: стори создана (`bmad-create-story`) на `abf84102`, статус `ready-for-dev`.
- 2026-10-18: ответы Alex на вопросы 1–5; период по умолчанию — последние 30 дней (решение 6, AC4, AC6, мутации).
- 2026-10-18: разбор стори в party mode, ответы Alex на вопросы 6–9. Добавлены решение 13 (запрет удалять автора записей ленты), AC11 и Task 3a. `STAFF_ACTIONS` вынесен в листовой `staff_actions.py`, чтобы не было цикла импорта. Критерий автора — «не суперпользователь» (решение 3, выбор сотрудника в решении 6, AC4, AC5). Назначение ответственного выводится как «ФИО (email)» (решения 4 и 5, AC3). Решение 11 переписано честно про индекс. В шапке уточнено «переназначил в карточке». Обновлены мутации, GitNexus, Dev Notes, выкат, «Связь» с 42.10.
- 2026-10-18: реализация (`bmad-dev-story`, ветка `feature/42-9-staff-action-journal`): лента `/supervisor/journal/`, перечень `staff_actions.py`, модуль `staff_journal.py`, шаблон, R42.7-D2, охрана удаления автора. 134 новых теста, мутации 24 из 24 убиты; полный прогон 4801 passed, 76 skipped, 0 failed; линтеры и `makemigrations --check` чисто. Статус `review`.
- 2026-10-18: исправления кода-ревью круга 1 (`bmad-dev-story`): R42.9-1 (`_int_id`), R42.9-2 (ссылки периода при неверной форме), R42.9-3 (разные объекты в `TestQueryCount`), R42.9-4 (заказ без ссылки). 9 новых тестов, 2 мутации убиты; полный прогон 4810 passed, 76 skipped, 0 failed; линтеры чисто. Статус `review`.
