---
baseline_commit: 1ea0fb2c
---

# Story 42.8: Сводка руководителя

Status: in-progress
Baseline Revision: 1ea0fb2c (`develop` после мёрджа PR #321 — стори 42.7 `done`)

## Story

As a руководитель,
I want видеть на одной странице очередь заявок, заказы и выручку по менеджерам и регионам,
so that я вижу загрузку отдела и задержки без выгрузок и ручного подсчёта.

**Закрывает:** FR-42-28. **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.8), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-5 «видит сводку», `section-contents.md` → «Руководитель» → «Сводка»), `_bmad-output/implementation-artifacts/epic-42-context.md` (сводке нужна своя агрегация в БД; выручка по мастер-заказам; число запросов не зависит от числа строк).

**Предусловия:**
- Код 42.1–42.7 в `develop` (`1ea0fb2c`): сайт `/supervisor/` (`SupervisorAdminSite`), руководитель в `/manager/` видит всех клиентов и все мастер-заказы (`scope_clients`/`scope_orders`, ветка `is_supervisor`), фильтр «Ответственный менеджер» (`ResponsibleManagerFilter`, параметр `responsible`), справочник регионов `apps/common/regions.py`, nginx-локация `/supervisor/`.
- Ветка `feature/42-8-supervisor-summary` от `develop`.
- **Права, модели, миграции не меняются.** У «Руководителей» уже есть `users.view_user` и `orders.view_order` (`users/migrations/0023_staff_role_groups.py`, `_MANAGERS_PERMISSIONS`).

**Чего в этой стори нет:**
- ленты журнала (42.9), замещения и массовой передачи (42.10);
- записей `AuditLog`: сводка только читает;
- кэша: числа сводки обязаны совпадать со списками по её ссылкам (решение 10);
- выгрузки сводки в CSV, графиков, сравнения периодов;
- истории назначений: заказы и выручка относятся к **текущему** ответственному менеджеру и **текущему** региону клиента (решение 6);
- изменений во фронтенде Next.js, API, OpenAPI, моделях, правах, nginx, CI.

## Решения (основа реализации)

1. **Страница `/supervisor/summary/`, имя `supervisor:summary`.** `SupervisorAdminSite.get_urls()` возвращает `[path("summary/", self.admin_view(self.summary_view), name="summary"), *super().get_urls()]` — свой путь **до** родительских: `AdminSite.get_urls()` заканчивается catch-all `re_path(r"(?P<url>.*)$", …)` (`final_catch_all_view=True`), и путь, добавленный после него, отвечал бы 404 (пример из docstring `admin_view` — `urls += [...]` — здесь не работает). Доступ — `admin_view` → `has_permission` базового `StaffSectionAdminSite` без изменений: менеджер, маркетолог, сотрудник без группы, заблокированный руководитель, суперпользователь (в том числе в группе) и аноним — 302 на `/supervisor/login/?next=/supervisor/summary/`.
   - `summary_view(self, request)`: `request.current_app = self.name` (как `AdminSite.index` — `reverse()` в Python-коде без `current_app` ведёт в `/admin/`); импорт `from apps.orders.supervisor_summary import build_summary` **внутри метода** (модуль раздела импортирует `freesport.admin_site` через `apps.orders.manager_admin` — импорт на уровне модуля дал бы цикл, как в `ManagerAdminSite.index`); `TemplateResponse(request, "admin/supervisor/summary.html", {**self.each_context(request), "title": "Сводка", **build_summary(request)})`.
   - На других сайтах страницы нет: `/manager/summary/` и `/marketing/summary/` — 404 (catch-all).
2. **Логика — новый модуль `backend/apps/orders/supervisor_summary.py`.** Сводка считает и клиентов, и заказы — как `manager_queue`, который уже лежит в `apps/orders` рядом со `scope_orders`. Модуль ничего не регистрирует и в `OrdersConfig.ready()` не импортируется — только из `summary_view`. Публичные имена (на них опираются тесты): `SummaryPeriodForm`, `Period`, `period_presets(today)`, `resolve_period(request)`, `pending_applications(request)`, `orders_by_manager(request, period)`, `orders_by_region(request, period)`, `client_counts(request, period)`, `region_bucket()`, `format_money(value)`, `build_summary(request)`. Docstring модуля — что считается и почему.
3. **Выборки — только `scope_clients(request, User.objects.all())` и `scope_orders(request, Order.objects.all())`**, своих фильтров по сотрудникам, мастер-заказам и заказам без клиента нет. Для руководителя это «весь отдел без учётных записей сотрудников» и «все мастер-заказы, включая заказы без клиента» (42.7). Поэтому каждое число сводки совпадает со списком `/manager/`, на который ведёт ссылка (так же устроен `manager_queue`). `scope_clients`, `scope_orders`, `region_key` **не меняются** (`HIGH`, `LOW`, `CRITICAL` — таблица GitNexus).
4. **Блок «Заявки на верификацию» — текущая очередь, от периода не зависит.**
   - Выборка — как у счётчика `manager_queue`: `scope_clients(...)`, `.exclude(role=User.ROLE_UNREGISTERED)` (список клиентов по умолчанию их скрывает), `verification_status="pending"`. Один запрос: `.values("responsible_manager").annotate(count=Count("pk"), oldest=Min("created_at")).order_by()`.
   - Строки менеджеров — по старейшей заявке (дольше всех ждёт — выше), при равенстве — по подписи. Подпись — `manager_label(user)` из `apps/users/staff_roles.py` («ФИО (email)»), у заблокированного — `+ " — заблокирован"` (тот же текст, что в `ResponsibleManagerFilter`). Учётные записи менеджеров — одним запросом на страницу, общим для блоков 4 и 6: `User.objects.filter(Q(pk__in=<id из таблиц страницы>) | responsible_manager_candidate_q())` (решение 6 — все действующие менеджеры). В этой таблице менеджеры без заявок не показываются: это очередь; все менеджеры с нулями — в таблице заказов (ответ Alex на вопрос 5).
   - **«Без ответственного» — отдельная строка в конце таблицы, всегда** (при нуле: число `0`, срок «—»), выделена `<strong>` и классом `summary-unassigned`.
   - Срок ожидания старейшей — `waiting_age(oldest)` (решение 12): «сегодня» или «N дней» в календарных днях часового пояса проекта.
   - Число в строке — ссылка на список `/manager/users/user/?verification_status__exact=pending&responsible=<pk>` (у «Без ответственного» — `responsible=none`). Фильтр `responsible` есть только у руководителя (42.7) — страница только для него. Последняя строка — «Итого» (сумма строк, без запроса).
5. **Период — GET-форма `SummaryPeriodForm`: `date_from`, `date_to` (`forms.DateField`, `DateInput(attrs={"type": "date"}, format="%Y-%m-%d")`), обе даты включительно, часовой пояс проекта (`Europe/Moscow`).**
   - Форма связана, только если в запросе есть хотя бы один из параметров; без параметров — период по умолчанию **«Этот месяц»** (с 1-го числа по сегодня, `timezone.localdate()`).
   - Ошибки: дата не указана при указанной второй — штатное «Обязательное поле.»; `date_from > date_to` — ошибка формы «Начало периода позже его конца.» Неверная форма — ошибки над формой, данные считаются за период по умолчанию, и подпись периода это показывает.
   - Границы в БД — полуинтервал `[make_aware(datetime.combine(date_from, time.min)), make_aware(datetime.combine(date_to + 1 день, time.min)))` по `timezone.get_current_timezone()`: заказ в 23:59 последнего дня входит, в 00:00 следующего — нет; заказ в 21:30 UTC накануне `date_from` (00:30 по Москве) входит.
   - Быстрые ссылки `period_presets(today)`: «Сегодня», «7 дней» (сегодня и 6 дней до), «30 дней» (сегодня и 29 до), «Этот месяц», «Прошлый месяц» (с 1-го по последнее число прошлого месяца; в январе — декабрь прошлого года). Ссылка — `?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`, выбранная выделена.
   - Подпись над блоками периода: «Период: 01.10.2026 — 17.10.2026».
6. **Блок «Заказы и выручка за период» — две таблицы, «По менеджерам» и «По регионам»** (FR-42-28, AC эпика).
   - База обеих — `scope_orders(request, Order.objects.all()).filter(created_at__gte=start, created_at__lt=end)`: только мастер-заказы (`is_master=True` внутри `scope_orders`), поэтому **сумма субзаказов второй раз не добавляется**. Выручка — `Sum("total_amount")` мастер-заказа: товары + доставка − скидка (`orders/services/order_create.py`; сумма субзаказов — только товары).
   - Колонки: «Заказов» — мастер-заказы периода **кроме** статусов `cancelled` и `refunded`; «Выручка» — сумма `total_amount` этих же заказов; «Отменено» — заказы периода в `cancelled`/`refunded`. Агрегаты условные: `Count("pk", filter=~Q(status__in=CANCELLED_STATUSES))`, `Sum("total_amount", filter=~Q(...))`, `Count("pk", filter=Q(status__in=...))`; `Sum` пустой группы — `None` → `Decimal("0")`. `CANCELLED_STATUSES = ("cancelled", "refunded")` — константа модуля.
   - **По менеджерам** — один запрос: группировка по `no_client=ExpressionWrapper(Q(user__isnull=True), output_field=BooleanField())` и `user__responsible_manager`, `.order_by()`. Строки:
     - **все действующие менеджеры, в том числе без заказов за период** (ответ Alex 17.10.2026 на вопрос 5): `responsible_manager_candidate_q()` из `apps/users/staff_roles.py` — активный сотрудник в «Менеджерах» или «Руководителях», не суперпользователь. Без заказов — «0», «0,00\xa0₽», «0». Список кандидатов приходит тем же запросом подписей (решение 4) — число запросов не растёт;
     - плюс менеджеры с заказами за период, которые уже не кандидаты (заблокированный — с « — заблокирован», выведенный из групп — просто подписью): их клиентов ещё не передали. Заблокированный или выведенный без заказов за период строки не получает; маркетологи — тоже;
     - порядок — по выручке по убыванию, затем по подписи: менеджеры с нулями внизу, по алфавиту;
     - затем «Без ответственного» (клиент без менеджера) и «Без клиента» (`Order.user` пусто, наследие `order_export`) — эти две только если в них есть заказы.

     Подпись под таблицей: «По текущему ответственному менеджеру клиента». «Итого» — сумма строк. Пустая таблица заказов (решение 13) бывает, только когда нет ни одного действующего менеджера и ни одного заказа.
   - **По регионам** — один запрос: группировка по `region_bucket()` (решение 7). Строки — по выручке по убыванию, затем по подписи; «Итого» совпадает с «Итого» таблицы менеджеров.
   - Ссылок на списки заказов нет: у списка заказов раздела нет фильтров по менеджеру и периоду, а число без совпадающего списка вводило бы в заблуждение.
7. **Регион заказа — регион его клиента сейчас, тем же правилом, что `region_key` (`users/services/responsible_manager.py`), но выражением SQL.** `region_bucket()` возвращает `Case`:
   - `user` пусто → «Без клиента»;
   - `~Q(user__country__in=RUSSIA_COUNTRY_VALUES)` (константа из `responsible_manager.py`: пустая страна = Россия) → страна;
   - `Q(user__tax_id__regex=r"^[0-9]{2}")` → первые две цифры (`Substr("user__tax_id", 1, 2)`);
   - иначе → «Регион не определён» (Россия без ИНН, ИНН с пробелом или буквой в начале — `region_key` даёт `None`).

   Ключ и подпись разделены: значение `Case` — служебный ключ (например `("country", "Беларусь")` двумя аннотациями `region_type`/`region_value` или строкой с префиксом — на выбор исполнителя), подпись строится в Python: код из `REGION_NAMES` — «23 — Краснодарский край», код вне справочника — сам код («96», как `region_name`), страна — её название. **`region_key` не менять (CRITICAL):** паритет выражения и функции закрепляет unit-тест на наборе ИНН и стран (Task 4). Не-ASCII цифры (`"٢٣"` — `isdigit()` да, регулярка нет) в ИНН не встречаются; в тест не включать.
8. **Блок «Клиенты».**
   - **«Новые регистрации за период: N»** — `scope_clients(...)`, `.exclude(role=User.ROLE_UNREGISTERED)`, `created_at` в периоде. Входят все регистрации портала: заявки в ожидании, верифицированные, отклонённые, розничные. Записи 1С без аккаунта (`unregistered`, на проде их 4600+) — не регистрации. Ссылки нет: у списка клиентов нет фильтра по произвольному периоду.
   - **«Верифицированы, но без заказов: M»** — от периода не зависит («без единого заказа» — за всё время): `scope_clients(...)`, `.exclude(role=User.ROLE_UNREGISTERED)`, `verification_status="verified"`, `is_active=True` (заблокированный заказать не может, руководителю он не нужен в этом списке), `~client_has_orders()`. Число — ссылка на `/manager/users/user/?verification_status__exact=verified&is_active__exact=1&has_orders=no`; список по ней показывает ровно M клиентов.
   - Оба числа — один запрос `aggregate(...)` с условными `Count`.
9. **Фильтр «Заказы» в списке клиентов `/manager/` — только руководителю** (нужен ссылке решения 8). В `apps/users/manager_admin.py`:
   - `client_has_orders() -> Exists` — `Exists(Order.objects.filter(user=OuterRef("pk")))`, любой заказ (мастер и его субзаказы принадлежат одному клиенту). Импорт `from apps.orders.models import Order` на уровне модуля безопасен: `orders/models.py` берёт пользователя через `get_user_model()` и `apps.users.manager_admin` не импортирует. Одно выражение на фильтр и на сводку — числа не разойдутся.
   - `ClientOrdersFilter(admin.SimpleListFilter)`: `title = "Заказы"`, `parameter_name = "has_orders"`, варианты `("yes", "Есть")`, `("no", "Нет")`; `queryset` — `filter(client_has_orders())` / `filter(~client_has_orders())`; неизвестное значение — `IncorrectLookupParameters` (как `ResponsibleManagerFilter`).
   - `ManagerClientAdmin.get_list_filter` у руководителя дописывает `ClientOrdersFilter` после `ResponsibleManagerFilter`. У менеджера фильтра нет, состав фильтров менеджера прежний (`test_manager_clients_section.py` проверяет его литералом); подделанный `?has_orders=no` в его списке не показывает чужих клиентов — штатный отказ Django на неизвестный параметр, точный ответ зафиксировать в тесте по факту (у `responsible` это 302 на `?e=1`).
10. **Без кэша.** `CustomerSyncMonitor.get_business_metrics` (`common/services/customer_sync_monitor.py:154`) кэширует метрики синхронизации — сводке это не подходит: числа должны совпадать со списками по ссылкам сразу после действия менеджера, а пять агрегирующих запросов по индексированным таблицам дешевле инвалидации. Образцом агрегации он тоже не служит — считает в цикле Python.
11. **Ссылка на сводку — первой в блоке «Разделы» главной `/supervisor/`:** `{"url": reverse("supervisor:summary"), "name": "Сводка — заявки, заказы и выручка"}` в `SupervisorAdminSite.index`. Остальные ссылки и блоки главной не меняются.
12. **Срок ожидания — одна функция на очередь менеджера и сводку.** В `apps/orders/manager_admin.py` рядом с `days_ru`: `waiting_age(oldest: datetime) -> str` — `(timezone.localdate() - timezone.localtime(oldest).date()).days`, «сегодня» при `<= 0`, иначе `days_ru(n)`. `manager_queue` переходит на неё без изменения текста (тесты `TestQueue`, `TestManagerQueue`, `test_index_counts_whole_department` — без правок).
13. **Шаблон `backend/templates/admin/supervisor/summary.html`** — `{% extends "admin/base_site.html" %}`, `bodyclass` + ` supervisor-summary`, хлебные крошки «Начало › Сводка» (`{% url 'admin:index' %}` — резолвится в `/supervisor/` по `current_app`), без `sidebar`. Блоки сверху вниз: форма периода с быстрыми ссылками и подписью периода; «Заявки на верификацию»; «Заказы и выручка за период» (две таблицы); «Клиенты». Таблицы — `<div class="module"><table><caption>…</caption>`, как `admin/manager/index.html`. Все значения — через автоэкранирование, без `|safe`. Таблица заказов по менеджерам без строк (решение 6) — строка «Заказов за период нет».
14. **Деньги — `format_money(value) -> str`:** `Decimal` с двумя знаками, группы по три через неразрывный пробел, запятая, затем неразрывный пробел и «₽»: `Decimal("1234567.8")` → `"1\xa0234\xa0567,80\xa0₽"`, `None`/`0` → `"0,00\xa0₽"`. Реализация без локали (`f"{value:,.2f}"` с заменой разделителей): результат не зависит от активного языка теста.

## Acceptance Criteria

### AC1 — вход и отказ

**Given** руководитель, менеджер, маркетолог, сотрудник без группы, заблокированный руководитель, суперпользователь, суперпользователь в группе «Руководители» и аноним
**When** каждый открывает `/supervisor/summary/`
**Then** руководитель получает 200, в HTML — «FREESPORT — Руководитель» и заголовок «Сводка»
**And** остальные получают 302 ровно на `/supervisor/login/?next=/supervisor/summary/`
**And** руководитель на `/manager/summary/` и `/marketing/summary/` получает 404
**And** просмотр сводки не пишет ни одной записи `AuditLog`

### AC2 — заявки на верификацию по менеджерам

**Given** заявки в ожидании (`verification_status="pending"`): у менеджера A — три (старейшей 5 дней), у менеджера B — одна (сегодня), у заблокированного менеджера C — одна (2 дня), без ответственного — две; плюс запись 1С `unregistered` в `pending` у A, верифицированный клиент A и сотрудник в `pending` с ответственным A
**When** руководитель открывает сводку
**Then** строки по порядку: A «3», «5 дней»; C «1», «2 дня», подпись с « — заблокирован»; B «1», «сегодня»; затем выделенная строка «Без ответственного» «2»; «Итого» — 7
**And** запись `unregistered`, верифицированный клиент и сотрудник не посчитаны
**And** ссылка в строке A ведёт на `/manager/users/user/?verification_status__exact=pending&responsible=<pk A>`, «Без ответственного» — на `…&responsible=none`; список по каждой ссылке у руководителя содержит ровно столько клиентов, сколько в строке
**And** без заявок без ответственного строка «Без ответственного» есть, число «0», срок «—»

### AC3 — период

**Given** сегодня 17.10.2026 (в тесте — `patch` `django.utils.timezone.now`)
**When** руководитель открывает сводку без параметров
**Then** период — 01.10.2026 — 17.10.2026, подпись «Период: 01.10.2026 — 17.10.2026», поля формы заполнены этими датами
**And** быстрые ссылки: «Сегодня» (17.10–17.10), «7 дней» (11.10–17.10), «30 дней» (18.09–17.10), «Этот месяц» (01.10–17.10), «Прошлый месяц» (01.09–30.09); в январе «Прошлый месяц» — декабрь прошлого года
**When** период 10.10.2026 — 12.10.2026
**Then** заказ, созданный 12.10 в 23:59 по Москве, входит; 13.10 в 00:00 по Москве — нет; 09.10 в 21:30 UTC (10.10 00:30 по Москве) — входит
**When** `date_from` позже `date_to` или указана только одна дата
**Then** над формой ошибка («Начало периода позже его конца.» / «Обязательное поле.»), страница 200, данные — за период по умолчанию, и подпись показывает его

### AC4 — заказы и выручка по менеджерам

**Given** в периоде: у клиентов A — мастер-заказ 1000 ₽ с двумя субзаказами по 500 ₽, legacy-мастер без субзаказов 300 ₽ и отменённый мастер 700 ₽; у клиентов B — мастер 2000 ₽ в статусе «Возвращен» и мастер 400 ₽; у клиента без ответственного — 150 ₽; заказ без клиента — 50 ₽; вне периода — заказ A 9999 ₽
**When** руководитель открывает сводку за период
**Then** A: «Заказов» 2, «Выручка» «1\xa0300,00\xa0₽», «Отменено» 1; B: 1, «400,00\xa0₽», 1; «Без ответственного»: 1, «150,00\xa0₽»; «Без клиента»: 1, «50,00\xa0₽»; «Итого»: 5, «1\xa0900,00\xa0₽», 2
**And** субзаказы не добавлены второй раз (выручка A не 2300), заказ вне периода не учтён
**When** руководитель меняет период так, что в него попадает заказ A 9999 ₽
**Then** число заказов и выручка A пересчитаны
**And** клиент A, переданный B в карточке, переносит свои заказы в строку B (по текущему ответственному)

**Given** отдельный набор данных (не вместе с предыдущим сценарием): у менеджера A один заказ 500 ₽ в периоде, активный менеджер D и руководитель R без заказов за период, маркетолог M, заблокированный менеджер E без заказов и заблокированный менеджер F, у клиента которого заказ 200 ₽ в периоде
**When** руководитель открывает сводку
**Then** строки по порядку: A «1», «500,00\xa0₽»; F «1», «200,00\xa0₽», подпись с « — заблокирован»; затем D и R с «0», «0,00\xa0₽», «0» — по подписи
**And** «Итого»: 2, «700,00\xa0₽», 0
**And** строк M и E нет

### AC5 — заказы и выручка по регионам

**Given** заказы периода клиентов с ИНН региона 23, региона 77, с ИНН кода вне справочника «96», клиента из Беларуси (ИНН любой), клиента России без ИНН, клиента с ИНН « 23…» (пробел в начале) и заказ без клиента
**When** руководитель открывает сводку
**Then** строки: «23 — Краснодарский край», «77 — г. Москва» (название — из `REGION_NAMES`), «96», «Беларусь», «Регион не определён» (без ИНН и с пробелом — одна строка), «Без клиента»
**And** «Итого» по регионам равно «Итого» по менеджерам (число заказов, выручка, отменённые)
**And** регион каждой строки совпадает с `region_key(country, tax_id)` клиента (unit-тест паритета)

### AC6 — регистрации и верифицированные без заказов

**Given** в периоде зарегистрированы: заявка B2B в ожидании, верифицированный оптовик, отклонённая заявка, розничный покупатель; вне периода — ещё один клиент; в периоде импортирована запись 1С `unregistered` и создан сотрудник
**When** руководитель открывает сводку
**Then** «Новые регистрации за период: 4»
**Given** верифицированные активные клиенты: без заказов — двое, с мастер-заказом — один, только с отменённым заказом — один; плюс верифицированный заблокированный без заказов, заявка в ожидании без заказов, запись `unregistered`, сотрудник
**When** руководитель открывает сводку
**Then** «Верифицированы, но без заказов: 2», число — ссылка `/manager/users/user/?verification_status__exact=verified&is_active__exact=1&has_orders=no`
**And** список по ссылке у руководителя содержит ровно этих двух клиентов
**And** в списке клиентов руководителя есть фильтр «Заказы» («Есть» / «Нет»), `has_orders=yes` показывает только клиентов с заказами
**And** у менеджера фильтра «Заказы» нет, состав его фильтров прежний; подделанный `?has_orders=no` в его списке не показывает чужих клиентов (ответ зафиксировать по факту)

### AC7 — ссылки и главная

**Given** руководитель
**When** он открывает главную `/supervisor/`
**Then** первая ссылка блока «Разделы» — `href="/supervisor/summary/"` «Сводка — заявки, заказы и выручка»; ссылки на `/manager/` и `/marketing/` и блоки главной прежние
**When** он открывает сводку с данными во всех блоках и с периодом в адресе
**Then** в HTML нет `href="/admin/`; хлебные крошки ведут на `/supervisor/`; ссылки «Изменить пароль» и «Выйти» — в `/supervisor/…`; ссылки строк ведут в `/manager/users/user/`
**And** подписи менеджеров и регионов выведены с экранированием (менеджер с именем `<b>X</b>` не даёт тега в HTML)

### AC8 — число запросов (NFR-42-04)

**Given** 2 менеджера, 5 клиентов (часть — заявки), 6 мастер-заказов в двух регионах
**When** руководитель открывает сводку, затем добавляются ещё 28 менеджеров, 60 клиентов и 90 мастер-заказов с субзаказами в 15 регионах и странах, и сводка открывается снова
**Then** число SQL-запросов одинаковое (`django_assert_num_queries(baseline)`, как `TestQueryCount` стори 42.7); среди добавленных менеджеров есть и без заказов — строки с нулями запросов не добавляют
**And** то же для списка клиентов руководителя с `has_orders=no` (5 и 50 клиентов)

### AC9 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `black --check`, `isort --check-only`, `flake8`, `mypy`, `makemigrations --check`
**Then** всё зелёное, миграций нет
**And** ожидания существующих тестов не меняются

## Tasks / Subtasks

- [x] **Task 0 — GitNexus pre-flight** (AGENTS.md, `.windsurf/rules/gitnexus.md`)
  - [x] `npx gitnexus status` — при `stale` попросить Alex выполнить `! npx gitnexus analyze --force`. При подготовке стори индекс `up-to-date` на `88ffba3` (дерево совпадает с `develop` @ `1ea0fb2c`), FTS-индексы есть (`query` отвечает).
  - [x] Сверить таблицу «GitNexus: зона изменений» с текущим индексом (`impact <symbol> --direction upstream --summary-only -r "C:\Users\1\DEV\FREESPORT"`). Сообщить Alex: меняются только `SupervisorAdminSite` (MEDIUM — оценка по импортам модуля `admin_site.py`), `manager_queue` (LOW), `ManagerClientAdmin.get_list_filter` (хук Django); `scope_clients` (HIGH) и `region_key` (CRITICAL) **только читаются**.

- [x] **Task 1 — страница на сайте руководителя** (AC1, AC7; решения 1, 11, 13)
  - [x] `backend/freesport/admin_site.py`: `SupervisorAdminSite.get_urls()` (свой путь до `super().get_urls()`), `summary_view`, ссылка «Сводка» первой в `supervisor_sections`; docstring класса — + сводка (стори 42.8).
  - [x] `backend/templates/admin/supervisor/summary.html` (решение 13); комментарий шаблона — что показано и почему без `sidebar`.

- [x] **Task 2 — расчёт сводки** (AC2–AC6; решения 2–8, 10, 14)
  - [x] Новый `backend/apps/orders/supervisor_summary.py`: `SummaryPeriodForm`, `Period` (`date_from`, `date_to`, `start`, `end`, подпись), `period_presets(today)`, `resolve_period(request) -> tuple[SummaryPeriodForm, Period]`, `pending_applications`, `orders_by_manager`, `orders_by_region`, `region_bucket`, `client_counts`, `format_money`, `build_summary(request) -> dict` (ключи контекста шаблона: `period_form`, `period`, `presets`, `pending`, `orders_by_manager`, `orders_by_region`, `clients`).
  - [x] Подписи менеджеров и список действующих менеджеров для строк с нулями — одним запросом на страницу (решения 4, 6), без запроса на строку.

- [x] **Task 3 — правки соседних модулей** (AC2, AC6; решения 9, 12)
  - [x] `backend/apps/orders/manager_admin.py`: `waiting_age(oldest)`; `manager_queue` использует её, текст счётчика прежний.
  - [x] `backend/apps/users/manager_admin.py`: `client_has_orders()`, `ClientOrdersFilter`, ветка руководителя в `ManagerClientAdmin.get_list_filter`; docstring модуля — + фильтр «Заказы» руководителя (42.8).

- [x] **Task 4 — тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [x] `backend/tests/integration/test_supervisor_summary.py` (integration, транзакционные: autouse `clear_db_before_test`, группы — `role_groups`, правила — `no_routing_rules`). Хелперы — явным импортом: из `tests.integration.test_manager_clients_section` — `role_groups`, `no_routing_rules`, `verified_email_task`, `make_staff_member`, `make_client`, `make_1c_record`, `region_tax_id`, `get_unique_suffix`, `PASSWORD`, `manager`, `other_manager`; из `tests.integration.test_manager_orders_section` — `make_master`, `make_applicant`, `set_created_at`, `local_noon`; из `tests.integration.test_supervisor_section` — `supervisor`, `supervisor_client`, `logged_in`, `listed_pks`, `count_queries`. Не `import *`, нового модуля хелперов не заводить (правило 42.4). Дату заказа — `Order.objects.filter(pk=…).update(created_at=…)` (`auto_now_add`), клиенту — `set_created_at`. Сценарии AC1–AC8; ожидаемые подписи, суммы, тексты ошибок и ссылки — литералами (урок R42.5-7).
  - [x] `backend/tests/unit/test_supervisor_summary.py` (unit): паритет `region_bucket()` и `region_key()` — клиенты с `country` `"Россия"`, `""`, `"Беларусь"`, `"Казахстан"` и ИНН `"2300000000"`, `"7700000000"`, `"9600000000"`, `" 2300000000"`, `"2a00000000"`, `"2"`, `""`; `period_presets` на 17.10.2026, 01.10.2026 и 15.01.2026; `SummaryPeriodForm` — пустая, полная, перевёрнутая, с одной датой; `format_money` — `Decimal("1234567.8")`, `Decimal("0")`, `None`, `Decimal("999.999")` (округление — до `"1\xa0000,00\xa0₽"`); `waiting_age` — сегодня, 1 день через полночь, 5 дней; `reverse("supervisor:summary") == "/supervisor/summary/"` и `resolve("/supervisor/summary/").url_name == "summary"`.
  - [x] **Проверка мутациями** — по каждой защите временно убрать её, убедиться, что падает названный тест, вернуть (скрипт в контейнере, исходник восстанавливается побайтно в `finally`). Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | свой путь после `super().get_urls()` вместо до | AC1 (руководитель — 404) |
    | `.exclude(role=User.ROLE_UNREGISTERED)` в заявках | AC2 (запись 1С посчитана у A) |
    | строка «Без ответственного» только при ненулевом числе | AC2 (строки нет при нуле) |
    | сортировка заявок по старейшей → по подписи | AC2 (порядок строк) |
    | `+ timedelta(days=1)` у конца периода | AC3 (заказ 12.10 23:59 не вошёл) |
    | `make_aware` по часовому поясу проекта → UTC | AC3 (заказ 21:30 UTC накануне) |
    | `filter=~Q(status__in=CANCELLED_STATUSES)` у выручки | AC4 (отменённый в выручке) |
    | `scope_orders(...)` → `Order.objects.filter(user__in=scope_clients(...))` | AC4 (выручка A 2300, «Без клиента» пропал) |
    | ветка страны в `region_bucket` | AC5, unit паритет (Беларусь — «Регион не определён») |
    | регулярка `^[0-9]{2}` → `Substr` без проверки | unit паритет (`"2a…"`, `" 23…"`) |
    | `is_active=True` у верифицированных без заказов | AC6 (заблокированный посчитан) |
    | `~client_has_orders()` → `~Exists` только мастер-заказов со статусом не «Отменен» | AC6 (клиент с отменённым заказом посчитан) |
    | условие `is_supervisor` у `ClientOrdersFilter` | AC6 (у менеджера фильтр, состав фильтров менеджера) |
    | ссылка «Сводка» на главной | AC7 |
    | `\| responsible_manager_candidate_q()` в запросе подписей | AC4 (строк D и R с нулями нет) |
    | строки только кандидатов (без менеджеров с заказами вне кандидатов) | AC4 (строки заблокированного F нет, «Итого» не сходится) |
    | общий запрос подписей → запрос на строку | AC8 |

- [x] **Task 5 — существующие тесты и проверки**
  - [x] Без правок зелёные: `tests/integration/test_supervisor_section.py`, `test_manager_clients_section.py`, `test_manager_orders_section.py`, `test_marketing_section.py`, `test_staff_access_lockdown.py`; `tests/unit/test_supervisor_admin_site.py`, `test_manager_admin_site.py`, `test_manager_orders_admin.py`, `test_regions.py`, `test_responsible_manager.py`.
  - [x] Полный backend-прогон в Docker, один compose-проект, в фоне: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` (~18 мин; ориентир после 42.7 — 4609 passed, 76 skipped, 0 failed).
  - [x] Линтеры строго после зачётного pytest, в том же `-p freesport-test`: `black --check .`, `isort --check-only .` (вывод не через `tail`), `flake8`, `mypy .` — базис ноль ошибок (после 42.7: black 487 файлов без изменений, mypy 640 файлов).
  - [x] `makemigrations --check --dry-run` — миграций нет. `check_openapi_sync` не нужен: API не меняется.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори; `npx gitnexus check --cycles -r "C:\Users\1\DEV\FREESPORT"` — базовый цикл `HomePage.tsx → index.ts → HomePage.tsx` и отложенный R42.7-D1 (`users/models.py → staff_roles.py → users/models.py`), новых нет (`users/manager_admin.py → orders/models.py` цикла не даёт).
  - [x] Completion Notes: отклонения от стори с причиной, ответы Alex на вопросы ниже, шаги выката.

### Review Findings

Код-ревью 17.10.2026, круг 1 (`1ea0fb2c..2d27b38e`, слои через плагин Codex: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor, Graph Impact). Acceptance Auditor и Graph Impact находок не дали: нарушений AC нет, несогласованных вызывающих и новых циклов импорта нет.

- [x] [Review][Patch] R42.8-1 (medium) Нет сценария группы только с отменёнными заказами — удаление `or Decimal("0")` в `_sales_row()` не уронит ни один тест, а на живых данных (регион или менеджер, у которого за «Сегодня» только отменённый заказ) `Sum` вернёт `None` и сортировка `-row.revenue` упадёт в 500. Добавить менеджера и регион, у которых в периоде только `cancelled`/`refunded`: строка «0», «0,00 ₽», отмены > 0, «Итого» сходится [backend/apps/orders/supervisor_summary.py:297]
- [x] [Review][Patch] R42.8-2 (low) `date_to=9999-12-31` даёт 500 — форма принимает дату, `Period.end` прибавляет день к `date.max` → `OverflowError`. Ошибка формы в `SummaryPeriodForm.clean()` вместо 500, плюс параметр в `test_invalid_period_falls_back_to_default` [backend/apps/orders/supervisor_summary.py:99]
- [x] [Review][Patch] R42.8-3 (low) Период таблицы регионов не проверен — в `TestOrdersByRegion` все заказы внутри периода, смену периода проверяет только таблица менеджеров; `orders_by_region()` без фильтра периода прошёл бы тесты. Добавить заказ вне периода в региональный сценарий [backend/tests/integration/test_supervisor_summary.py:403]
- [x] [Review][Patch] R42.8-4 (low) В сценариях заказов нет заказа сотрудника — замена `scope_orders(...)` на все мастер-заказы (`Order.objects.filter(is_master=True)`) прошла бы тесты и добавила служебные аккаунты в выручку. Добавить мастер-заказ учётной записи сотрудника в `test_rows_totals_and_period` и проверить, что строки и «Итого» не изменились [backend/tests/integration/test_supervisor_summary.py:335]
- [x] [Review][Patch] R42.8-5 (low) «Без заказов за всё время» не закреплено историческим заказом — все заказы тестов `has_orders` созданы сейчас, ограничение `client_has_orders()` периодом осталось бы незамеченным. Перенести заказ клиента `with_order` за пределы периода по умолчанию [backend/tests/integration/test_supervisor_summary.py:449]
- [x] [Review][Patch] R42.8-6 (low) Страница не говорит, что заявки и «Верифицированы, но без заказов» от периода не зависят — оба блока стоят под формой периода, руководитель ждёт пересчёта. Подписи из решений 4 и 8: «Текущая очередь, от периода не зависит» под таблицей заявок и «за всё время» у числа клиентов без заказов [backend/templates/admin/supervisor/summary.html:44]

**Rejected (8):**

- `managers[manager_id]` → `KeyError`, если менеджера удалили между агрегацией и `load_managers` (Edge Case Hunter, Blind Hunter) — low: окно в миллисекунды, сотрудников не удаляют (блокируют); фикс — дополнительная защита.
- Таблицы одной страницы могут разойтись при параллельном изменении заказа, нужен `REPEATABLE READ` (Edge Case Hunter, Blind Hunter) — low: расхождение на один запрос, следующее открытие верное; изоляция транзакции — лишняя сложность, решение 10 требует совпадения со списками, а не снимка.
- Колонки «Заказов»/«Выручка»/«Отменено» не объясняют правила расчёта (Blind Hunter) — low: подписи страницы зафиксированы решением 6, расшифровка — продуктовая формулировка, вреда нет.
- Нет клиента только с субзаказом в тестах `client_has_orders` (Blind Hunter) — false: субзаказ принадлежит тому же клиенту, что и мастер (решение 9), клиента с субзаказом без мастера не бывает.
- Нет менеджера, выведенного из групп, с заказами и без (Blind Hunter) — low: та же ветка `not is_candidate`, что у заблокированного F, её закрывает `test_all_current_managers_are_listed`.
- Нет проверки переноса заказа между регионами после смены страны/ИНН (Blind Hunter) — low: регион считается из полей клиента в каждом запросе, хранимого региона нет — регрессия возможна только сменой схемы.
- Нет свидетельства покрытия ≥ 90 % в Debug Log (Blind Hunter) — правка стори, а не кода.
- Runbook выката проверяет только анонимный 302 (Blind Hunter) — правка стори, а не кода.

Код-ревью 17.10.2026, круг 2 (`1ea0fb2c` → рабочее дерево с исправлениями круга 1, только `backend/`; слои через плагин Codex). Acceptance Auditor и Graph Impact находок не дали: нарушений AC нет, несогласованных вызывающих нет, `check --cycles` — только существующие циклы.

- [x] [Review][Patch] R42.8-7 (medium) Защита «субзаказы второй раз не складываются» не закреплена тестом — `master_in_period()` переносит в период только мастер, субзаказы `make_master(..., subs=2)` остаются с датой создания (вне `PERIOD`) и отсекаются фильтром даты, а не `is_master`. Снятие `is_master=True` из выборки сводки (или замена `scope_orders` на выборку без него) не уронит `test_rows_totals_and_period`, а на живых данных выручка удвоится. Переносить в период мастер вместе с его субзаказами (`Q(pk=…) | Q(parent_order=…)`) [backend/tests/integration/test_supervisor_summary.py:139]
- [x] [Review][Patch] R42.8-8 (low) Верхняя граница периода регистраций не проверена — в `test_registrations_in_period` единственный клиент вне периода создан до его начала; удаление `created_at__lt=period.end` в `client_counts()` прошло бы тест. Добавить клиента, созданного в начале дня после периода (13.10.2026 00:00 МСК), число остаётся «4» [backend/tests/integration/test_supervisor_summary.py:475]
- [x] [Review][Patch] R42.8-9 (low) Независимость очереди заявок от периода проверена только подписью — все сценарии `TestPending` открывают сводку без параметров периода; фильтр заявок по `created_at` при заданном `date_from`/`date_to` прошёл бы тесты. Сравнить строки и ссылки таблицы заявок для двух непересекающихся периодов при заявках разных дат [backend/tests/integration/test_supervisor_summary.py:200]

**Rejected круга 2 (12):**

- Таблицы по менеджерам и регионам — разные запросы без общего снимка (Blind Hunter) — low: повтор отклонённой в круге 1 находки; расхождение возможно только при заказе между двумя запросами одной страницы, изоляция транзакции — лишняя сложность.
- То же со стороны граничных случаев: заказ создан или отменён между `orders_by_manager()` и `orders_by_region()`, предложен `REPEATABLE READ` (Edge Case Hunter) — low: по той же причине.
- `managers[manager_id]` → `KeyError` при удалении менеджера между запросами (Edge Case Hunter) — low: повтор круга 1, окно в миллисекунды, сотрудников блокируют, а не удаляют.
- `Period.start/end` зависят от активного часового пояса, а не от пояса проекта (Blind Hunter) — false: `timezone.activate` в проекте нигде не вызывается, активный пояс всегда `TIME_ZONE = "Europe/Moscow"`; границы закреплены `TestPeriod::test_day_boundaries`.
- Срок ожидания считается от `User.created_at`, а не от подачи заявки (Blind Hunter) — правило задано стори (блок 4: `oldest=Min("created_at")`, как у `manager_queue`), поля даты заявки в модели нет; изменение — правка спеки и модели.
- Форма принимает `10.10.2026`, поле `type="date"` покажет пустое значение (Blind Hunter) — low: браузер отправляет `type="date"` только в ISO, такой URL — только ручной; фикс — дополнительный параметр формы.
- Подписи «Выручка»/«Отменено» не объясняют расчёт (Blind Hunter) — повтор круга 1, подписи заданы решением 6.
- Подпись «Верифицированы, но без заказов» не упоминает `is_active` (Blind Hunter) — текст задан AC6 литералом; изменение — правка спеки.
- «Заказов за период нет» не показывается при нулевых строках менеджеров (Blind Hunter) — false: так задано решением 6 и блоком 13 — действующие менеджеры с нулями показываются всегда, сообщение — только для таблицы без строк.
- Нет ссылок от числа заказов и выручки на список заказов (Blind Hunter) — вне объёма стори: ссылки заданы только для заявок и клиентов без заказов (AC2, AC6, AC7).
- ИНН с Unicode-цифрами: `region_key()` (`isdigit`) и SQL `^[0-9]{2}` расходятся (Edge Case Hunter) — low: ИНН из 1С и регистрации — ASCII-цифры, паритет на реальных значениях закреплён `test_region_bucket_matches_region_key`; фикс — лишняя ветка.
- Сводка не проверяет `view_user`/`view_order`, только членство в «Руководителях» (Edge Case Hunter) — low: права группы задаёт миграция `users/0023`, стори права не меняет; расхождение требует ручной правки прав группы, фикс — новая защита.

Код-ревью 18.10.2026, круг 3 (`develop...5d2287fe`, слои через плагин Codex). Acceptance Auditor и Graph Impact находок не дали: нарушений AC нет; индекс GitNexus на `5d2287f` = HEAD, несогласованных вызывающих, непокрытых символов и новых циклов импорта нет.

- [x] [Review][Patch] R42.8-10 (low) Региональное «Итого» не закреплено против субзаказов и заказов сотрудников — сценарий с двумя субзаказами в периоде и заказом маркетолога (`test_rows_totals_and_period`) проверяет только таблицу менеджеров, а `TestOrdersByRegion` строит мастера без субзаказов и без сотрудников. Замена `_period_orders()` в `orders_by_region()` выборкой всех `Order` за период не уронит тесты, региональный итог станет «8», «7 900,00 ₽». Добавить в `test_rows_totals_and_period` проверку `page.rows["summary-orders-by-region"][-1] == ("Итого", "5", "1 900,00 ₽", "2")` (Verification Gap, Blind Hunter) [backend/tests/integration/test_supervisor_summary.py:401]
- [x] [Review][Patch] R42.8-11 (low) Нижняя граница периода проверена на 00:30, а не на 00:00 — `utc-evening` в `test_day_boundaries` — это 09.10 21:30 UTC = 10.10 00:30 МСК, поэтому замена `created_at__gte` на `created_at__gt` в `_period_orders()` пройдёт тест. Перенести заказ на 09.10 21:00 UTC (ровно 10.10 00:00 МСК): ожидание «2», «350,00 ₽» не меняется (Blind Hunter) [backend/tests/integration/test_supervisor_summary.py:322]
- [x] [Review][Patch] R42.8-12 (low) «Верифицированы, но без заказов» не закреплено против фильтра по дате регистрации — оба клиента `idle` в `test_verified_without_orders` созданы сейчас, внутри периода по умолчанию; фильтр `created_at` в `verified_without_orders` (`client_counts()`) пройдёт тест. Перенести регистрацию одного из `idle` на 15.01.2025 через `set_created_at`: число остаётся «2» (Blind Hunter) [backend/tests/integration/test_supervisor_summary.py:520]
- [x] [Review][Patch] R42.8-13 (low) `make_applicant(manager: User)` вызывается с `None` — новые сценарии сводки (`TestPending`) передают `None`, а аннотация хелпера это исключает; `make_client` принимает `User | None`. Аннотация `manager: User | None` (Edge Case Hunter) [backend/tests/integration/test_manager_orders_section.py:1226]

**Rejected круга 3 (12):**

- Форма принимает `10.10.2026`, поле `type="date"` покажет пустое значение (Blind Hunter, Edge Case Hunter — две находки) — low: повтор круга 2; браузер отправляет `type="date"` только в ISO, локализованный URL — только ручной.
- `managers[manager_id]` → `KeyError` при удалении менеджера между запросами (Edge Case Hunter) — low: повтор кругов 1–2.
- Таблицы одной страницы без общего снимка, предложен `REPEATABLE READ` (Edge Case Hunter) — low: повтор кругов 1–2.
- ИНН с Unicode-цифрами: `region_key()` и SQL расходятся (Edge Case Hunter) — low: повтор круга 2; `region_key` стори не меняет.
- Экранирование проверено только для имени менеджера, не для страны (Blind Hunter) — low: шаблон без `|safe` и `mark_safe`, автоэкранирование Django общее для всех подписей; регрессия требует явного `|safe`.
- Нет отказа руководителю с `is_staff=False` (Blind Hunter) — false: доступ идёт через `admin_view` → `has_permission` базового сайта без изменений, случай закреплён `test_supervisor_section.py:258` (`supervisor-without-staff`).
- Порядок строк при равных старейшей заявке и выручке не проверен (Blind Hunter) — low: вторичный ключ по подписи — косметика порядка, вреда для чисел нет.
- `TestQueryCount::test_summary` и `TestPending::test_rows_order_and_links` зависят от реальных часов — смена месяца или московская полночь посреди теста (Blind Hunter, Edge Case Hunter — две находки) — low: окно в секунды раз в сутки/месяц; фикс — обёртки `patch(timezone.now)` во всех фабриках сценария.
- Проверка после выката — только анонимный 302 (Blind Hunter) — правка стори, а не кода (повтор круга 1).
- В File List стори нет `.windsurf/rules/gitnexus.md` (Blind Hunter) — правка стори; файл пришёл отдельным docs-коммитом `82b8608f`, к сводке не относится.

Код-ревью 18.10.2026, круг 4 (`1ea0fb2c..51b5faad`, только `backend/`; слои через плагин Codex). Acceptance Auditor и Graph Impact находок не дали: нарушений AC нет; индекс GitNexus на `51b5faa` = HEAD, несогласованных вызывающих и новых циклов импорта нет.

- [ ] [Review][Patch] R42.8-14 (low) Включение в продажи заказов в статусах кроме `pending` не закреплено — все учитываемые заказы сценариев сводки в `pending` (`make_master` по умолчанию), остальные — `cancelled`/`refunded`. Замена `filter=~cancelled` на `filter=Q(status="pending")` в `_sales()` не уронит тесты, а обработанные и доставленные заказы исчезнут из «Заказов» и «Выручки». Параметризованный сценарий по `confirmed`, `processing`, `shipped`, `delivered`: заказ входит в «Заказов» и «Выручку» обеих таблиц и в их «Итого», «Отменено» — 0 (Verification Gap) [backend/tests/integration/test_supervisor_summary.py:372]
- [ ] [Review][Patch] R42.8-15 (low) Условие `verification_status="verified"` в «Верифицированы, но без заказов» не проверено отдельно от `is_active` — единственный неверифицированный клиент `test_verified_without_orders` создан `make_applicant`, а он ставит `is_active=False`. Удаление `verification_status="verified"` из агрегата `client_counts()` оставит число «2». Добавить активных клиентов без заказов в `pending` и `unverified`: число остаётся «2», состав списка по ссылке прежний (Verification Gap) [backend/tests/integration/test_supervisor_summary.py:522]

**Rejected круга 4 (12):**

- Таблицы одной страницы без общего снимка, предложен `REPEATABLE READ` (Blind Hunter, Edge Case Hunter — две находки) — low: повтор кругов 1–3.
- `managers[manager_id]` → `KeyError` при удалении менеджера между запросами (Blind Hunter, Edge Case Hunter — две находки) — low: повтор кругов 1–3.
- ИНН с Unicode-цифрами: `region_key()` и SQL `^[0-9]{2}` расходятся (Blind Hunter, Edge Case Hunter — две находки) — low: повтор кругов 2–3; решение 7 прямо исключает такие ИНН из теста паритета.
- Подпись «Верифицированы, но без заказов» не упоминает `is_active` (Blind Hunter) — повтор круга 2: текст задан AC6 литералом, изменение — правка спеки.
- Колонки «Выручка»/«Отменено» не объясняют расчёт, «Отменено» — переименовать в «Отменено / возвращено» (Blind Hunter) — повтор кругов 1–2: подписи заданы решением 6.
- Под таблицей регионов нет подписи «по текущему региону клиента» (Blind Hunter) — low: заголовок колонки «Регион клиента», подпись под таблицей решение 6 задаёт только для менеджеров; страна и ИНН клиента меняются редко.
- Нет ссылок от чисел продаж и регистраций на исходные списки (Blind Hunter) — повтор круга 2: вне объёма стори, для регистраций решение 8 прямо говорит «Ссылки нет».
- Форма принимает `10.10.2026`, поле `type="date"` покажет пустое значение (Blind Hunter) — low: повтор кругов 2–3.
- В матрице отказов сводки нет `supervisor-without-staff` (Blind Hunter) — low: проверка `is_staff` — в общем `has_permission` сайта, закреплена для `/supervisor/` в `test_supervisor_section.py:258`; остальные отказы матрицы сводки доказывают, что `summary_view` идёт через `admin_view`.

## Dev Notes

### Текущее состояние кода (сверено на `1ea0fb2c`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py:157-201` `SupervisorAdminSite` | вход — группа «Руководители»; `index` кладёт в контекст `supervisor_sections` (ссылки на `/manager/`, `/marketing/`); `get_app_list` переименовывает блоки | + `get_urls`, `summary_view`; первая ссылка «Сводка» |
| `backend/freesport/admin_site.py:39-66` `StaffSectionAdminSite.has_permission` | активный сотрудник из `section_groups`, не суперпользователь; кэш `request._staff_section_access` | не меняется — им же закрыта сводка |
| `backend/freesport/urls.py:54` | `path("supervisor/", supervisor_site.urls)` | не меняется: новый путь приходит из `get_urls` сайта |
| `backend/templates/admin/supervisor/index.html` | блок «Разделы» по `supervisor_sections`, пустой `sidebar` | не меняется (ссылка приходит из контекста) |
| `backend/apps/users/manager_admin.py:38-48` `scope_clients` | руководителю — все, кроме сотрудников (`staff_accounts_q()`); менеджеру — свои | не меняется, сводка читает |
| `backend/apps/users/manager_admin.py:110-147` `ResponsibleManagerFilter` | `responsible=<pk>` / `none`, варианты — менеджеры с клиентами в выборке | не меняется, на него ведут ссылки блока заявок |
| `backend/apps/users/manager_admin.py:150-229` `ManagerClientAdmin` | `list_filter` менеджера: `role`, `verification_status`, `Has1CCandidateFilter`, `is_active`, `PortalAccountFilter`; руководителю `get_list_filter` добавляет `ResponsibleManagerFilter` | + `ClientOrdersFilter` у руководителя |
| `backend/apps/orders/manager_admin.py:82-95` `scope_orders` | мастер-заказы клиентов `scope_clients`; руководителю — и заказы без клиента | не меняется, сводка читает |
| `backend/apps/orders/manager_admin.py:98-157` `days_ru`, `manager_queue` | срок старейшей заявки считается внутри `manager_queue` | `waiting_age` выносится, `manager_queue` её вызывает |
| `backend/apps/users/services/responsible_manager.py:37`, `:48-60` `RUSSIA_COUNTRY_VALUES`, `region_key` | ключ региона: страна не Россия → страна; иначе две цифры ИНН; иначе `None` | не меняется; сводка повторяет правило выражением SQL |
| `backend/apps/common/regions.py` | `REGION_NAMES`, `region_name` (код вне справочника — как есть) | не меняется, подписи регионов |
| `backend/apps/users/staff_roles.py:91-94` `manager_label` | «ФИО (email)» | не меняется, подписи менеджеров |
| `backend/apps/users/staff_roles.py:73-82` `responsible_manager_candidate_q` | активный сотрудник в «Менеджерах»/«Руководителях», не суперпользователь; членство через `Exists` | не меняется; состав строк с нулями в таблице заказов |
| `backend/apps/users/models.py:132-421` `User` | `created_at`, `verification_status` (`unverified`/`pending`/`verified`), `is_active`, `role`, `responsible_manager` (`related_name="managed_clients"`), `country`, `tax_id`; `Meta` без `ordering` | не меняется |
| `backend/apps/orders/models.py:30-368` `Order` | `user` (`null=True`, `related_name="orders"`), `is_master`, `parent_order`, `status` (`orders/constants.py:49`), `total_amount`, `created_at` (`auto_now_add`); `Meta.ordering = ["-created_at"]`; индексы `(user, status)`, `(status, created_at)` | не меняется |
| `backend/apps/orders/services/order_create.py:85-125` | мастер: `total_amount` = товары + доставка − скидка; субзаказ: сумма своих товаров | не меняется; основа «выручки по мастер-заказам» |

### GitNexus: зона изменений

Индекс `up-to-date` на `88ffba3` (дерево = `develop` @ `1ea0fb2c`), FTS есть. Команды — `npx gitnexus impact <symbol> --direction upstream --summary-only -r "C:\Users\1\DEV\FREESPORT"` и `--include-tests --depth 2`.

| Символ | Изменение | risk | Прямые вызывающие (`byDepth.1`) | Затронутые процессы | Тесты (`--include-tests`) |
|---|---|---|---|---|---|
| `SupervisorAdminSite` (`freesport/admin_site.py`, `--kind Class`) | + `get_urls`, `summary_view`, ссылка в `index` | MEDIUM (15, lower-bound: 9 прямых — модули, импортирующие `admin_site.py`) | `bonuses/common/users supervisor_admin.py`, `*/marketing_admin.py`, `orders|users manager_admin.py`, `freesport/urls.py` | 0 | `test_supervisor_section.py`, `test_supervisor_admin_site.py`, `test_manager_orders_section.py`, `test_marketing_section.py`, `test_manager_admin_site.py`, `test_manager_orders_admin.py`, `test_marketing_admin_site.py` |
| `SupervisorAdminSite.index` | + ссылка «Сводка» | UNKNOWN (хук Django — вызывающих в графе нет, ожидаемо) | — | — | `test_supervisor_section.py::TestLinksAndIndex::test_index` |
| `manager_queue` (`orders/manager_admin.py`) | срок — через `waiting_age` | LOW (1) | `ManagerAdminSite.index` | 0 | `test_manager_orders_section.py::TestQueue`, `test_manager_orders_admin.py::TestManagerQueue`, `test_supervisor_section.py::test_index_counts_whole_department` |
| `days_ru` (`orders/manager_admin.py`) | не меняется, зовёт `waiting_age` | LOW (2) | `manager_queue` | 0 | `test_manager_orders_admin.py::test_days_ru` |
| `ManagerClientAdmin.get_list_filter` (`users/manager_admin.py`) | + `ClientOrdersFilter` руководителю | UNKNOWN (хук Django) | — | — | `test_supervisor_section.py::TestResponsibleColumnAndFilter`, `test_manager_clients_section.py` (состав фильтров менеджера литералом) |
| `ManagerClientAdmin` (`--kind Class`) | см. выше | MEDIUM (10, по импортам) | `users/apps.py`, `orders/manager_admin.py` | 0 | `test_manager_clients_section.py`, `test_supervisor_section.py`, `test_manager_admin_site.py` |
| `scope_clients` (`users/manager_admin.py`) | **не меняется**, только чтение | HIGH (14) | `ManagerClientAdmin.get_queryset`, `ResponsibleManagerFilter.lookups`, `scope_orders`, `manager_queue` | `user_change_password`, `change_view`, `verify_b2b_view` раздела (по 9 процессов) | — |
| `scope_orders` (`orders/manager_admin.py`) | **не меняется**, только чтение | LOW (4) | `ManagerOrderAdmin.get_queryset`, `ManagerOrderForm.clean`, `manager_queue` | `get_queryset` (2) | — |
| `region_key` (`users/services/responsible_manager.py`) | **не меняется**; паритет с `region_bucket` — unit-тест | CRITICAL (9) | `resolve_responsible`, `resolve_manager_recipients`, `recalculate_responsible_managers` | `handle` команды пересчёта (7), `verify_b2b_view` и др. | `test_responsible_manager.py`, `test_region_routing.py` |
| `region_name` (`common/regions.py`) | не меняется, подписи | MEDIUM (8) | `region_display`, `_write_report` команды пересчёта | `handle` | `test_regions.py` |
| `manager_label` (`users/staff_roles.py`) | не меняется, подписи | LOW (1) | `ResponsibleManagerFilter.lookups` | 0 | `test_supervisor_section.py::TestResponsibleColumnAndFilter` |
| `responsible_manager_candidate_q` (`users/staff_roles.py`) | не меняется, состав строк с нулями | LOW (7) | `responsible_manager_candidates`, `limit_manager_field` | 0 | `test_supervisor_admin_site.py::TestResponsibleManagerCandidates` |

Новые символы (`supervisor_summary.py`, `waiting_age`, `client_has_orders`, `ClientOrdersFilter`, `SupervisorAdminSite.get_urls`/`summary_view`) в индексе появятся после `analyze`.

### Подводные камни

- **Catch-all `AdminSite`.** `get_urls()` родителя заканчивается `re_path(r"(?P<url>.*)$", wrap(self.catch_all_view))` (`django/contrib/admin/sites.py:317-318`, Django 5.2.7). Путь сводки — только перед `super().get_urls()`.
- **`current_app`.** Шаблонный `{% url 'admin:…' %}` берёт `request.current_app`, иначе `resolver_match.namespace` — на `/supervisor/summary/` это `supervisor`, поэтому крошки сработают и без присваивания. Но `reverse("admin:…")` в Python без `current_app` уводит в `/admin/` (экземпляр по умолчанию). Присваивание `request.current_app = self.name` — как в `AdminSite.index`; мутацией не проверяется (шаблон резолвится и так), это не повод его убирать.
- **Группировка и `Meta.ordering`.** У `Order` `ordering = ["-created_at"]`. С Django 3.1 `Meta.ordering` в `GROUP BY` не попадает, но `.order_by()` перед `values().annotate()` писать явно — запрос читается однозначно.
- **`staff_accounts_q()` содержит `groups__name__in`.** В `exclude()` Django делает из него подзапрос, строки не множатся; в `filter()` — JOIN и дубли. Выборки брать только через `scope_clients`.
- **Порядок веток `region_bucket` значим.** Ветка «`user` пусто» — первой: у заказа без клиента LEFT JOIN даёт `country = NULL`, и отрицание `~Q(user__country__in=…)` Django разворачивает с проверкой `IS NOT NULL` — такой заказ попал бы в ветку страны с пустым названием.
- **`Q(pk__in=…) | responsible_manager_candidate_q()`.** В кандидате членство — `Exists`, а не JOIN по `groups`: объединение через `|` даёт одну строку на сотрудника. Не заменять на `RESPONSIBLE_MANAGER_CHOICES` (JOIN — дубли строк менеджера в двух группах).
- **`Sum` пустой группы — `None`.** Приводить к `Decimal("0")` до сложения «Итого» и форматирования.
- **`ExpressionWrapper(Q(user__isnull=True), output_field=BooleanField())` в `values()`** — штатный способ сгруппировать по условию. Отдельный запрос для «Без клиента» не нужен.
- **`auto_now_add`.** `created_at` заказа и клиента в тестах — только `update()` после создания (`set_created_at` для клиента).
- **Хук 42.2 назначает ответственного при создании клиента.** `make_client` ставит ответственного `update()` и флаг «вручную»; клиент без ответственного — `make_client(None)`; правила — autouse `no_routing_rules`.
- **`verification_status` и `is_verified`.** Верифицированный — `verification_status="verified"`; розничная регистрация ставит его сразу (`users/serializers.py:374-377`), но розница отключена (`REGISTRATION_ALLOW_RETAIL`). Записи 1С `unregistered` — `unverified` (`UserManager`, `users/models.py:93`).
- **Связанная с 1С заявка сохраняет свой `created_at`.** `link_1c_customer` переносит идентичность 1С на аккаунт заявителя (`users/services/link_1c_customer.py:225`), запись 1С остаётся `unregistered` — регистрации считаются верно.
- **Фильтр `has_orders` у менеджера отсутствует** — `lookup_allowed` отклонит параметр. Не делать фильтр общим «для удобства»: состав фильтров менеджера задан `section-contents.md` и закреплён тестом литералом.
- **Ссылка на список фильтра `responsible`** открывается и для pk менеджера, которого нет среди вариантов фильтра (`SimpleListFilter` значения не сверяет) — ссылки сводки всегда на менеджеров с клиентами, расхождений нет.
- **Неразрывные пробелы в суммах.** В тестах — `"\xa0"` литералом, не обычный пробел.

### Выкат (для Completion Notes и Alex)

1. Миграций, ручных шагов в БД и правок nginx нет: локация `/supervisor/` (42.7) уже проксирует `/supervisor/summary/`.
2. После выката: `curl -sI https://optisport.ru/supervisor/summary/` → 302 на `/supervisor/login/?next=/supervisor/summary/`. 404 от Next — `docker compose exec nginx nginx -s reload` (memory: nginx держит старый IP upstream).
3. На проде правил регионов пока нет (ответ Alex 16.10.2026): пока руководитель не завёл резервное правило и правила регионов, почти все заявки и заказы будут в строках «Без ответственного» — это ожидаемо, а не ошибка сводки.

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет. `AdminSite.get_urls`/`admin_view`/`each_context`, условные агрегаты (`filter=`), `ExpressionWrapper(Q(...))`, `Exists`/`OuterRef`, `Case`/`When`, `Substr`, `__regex` — сверять по исходникам 5.2.7 в `backend/venv/Lib/site-packages/django/`. Веб-исследование версий не требуется: стек не меняется.
- Агрегация — в БД (`epic-42-context.md`): ни одной выборки строк заказов или клиентов в Python, только сгруппированные значения.
- Миграции, API, OpenAPI, фронтенд, nginx, CI не меняются.
- Язык: интерфейс, сообщения, комментарии, docstrings — русский (NFR-42-03).

### Тестирование

- Только Docker + PostgreSQL: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`; `--env-file` не передаётся; параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры по каталогу: `tests/unit/` → `unit`, `tests/integration/` → `integration`.
- Проверки доступа — критический модуль, покрытие ≥ 90 % (NFR-42-01): `freesport/admin_site.py`, `apps/orders/supervisor_summary.py`, изменённые ветки `users/manager_admin.py`.
- Время в тестах периода — `patch("django.utils.timezone.now", return_value=datetime(2026, 10, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")))`, как `test_calendar_day_boundary` (42.5). `timezone.localdate()` берёт `now()` — патч действует на него.
- Ожидаемые подписи, суммы, тексты ошибок и URL — литералами, не из констант реализации (урок R42.5-7).
- Список по ссылке сводки — проверять тем же браузером руководителя: `supervisor_client.get(<href из HTML>).context["cl"].result_count`.

### Уроки 42.4–42.7

- Ревью 42.7 — четыре круга: атомарность действий списка, непокрытые негативные проверки, «защита есть, теста, который упадёт без неё, нет». Здесь записи нет вовсе, поэтому главный риск — числа, не совпадающие со списками, и тесты, которые не падают при удалении защиты: отсюда решение 3 (только `scope_*`), сверка «число = список по ссылке» в AC2/AC6 и таблица мутаций.
- Ссылки раздела в закрытую `/admin/` или в 404 другого раздела — класс ошибок 42.4–42.7: AC7.
- Отклонения от стори — в Completion Notes с причиной, не молча.
- Вывод `isort` не смотреть через `tail` (R42.5-D3); линтеры — после зачётного pytest, в `-p freesport-test` (memory).

### Связь с последующими стори

- **42.9** — лента журнала на `supervisor_site`: отдельная страница по тому же образцу (`get_urls` до `super()`, `admin_view`, `each_context`, `current_app`). Ссылку добавить в блок «Разделы» после «Сводки».
- **42.10** — замещение: при замещении клиенты по правилу у заместителя (`responsible_manager`), значит и в сводке их заявки и заказы — в строке заместителя. Отдельной правки сводки не нужно; если Alex захочет видеть отметку «Замещение» в строке менеджера — это решение 42.10.

### Project Structure Notes

- Новые файлы:
  - `backend/apps/orders/supervisor_summary.py`;
  - `backend/templates/admin/supervisor/summary.html`;
  - `backend/tests/integration/test_supervisor_summary.py`;
  - `backend/tests/unit/test_supervisor_summary.py`.
- Изменяемые:
  - `backend/freesport/admin_site.py`;
  - `backend/apps/orders/manager_admin.py` (`waiting_age`);
  - `backend/apps/users/manager_admin.py` (`client_has_orders`, `ClientOrdersFilter`, `get_list_filter`);
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`, этот файл.
- Модуль сводки — в `apps/orders`, как `manager_queue`: зависимость `orders → users` уже есть (`orders/manager_admin.py` импортирует `users/manager_admin.py`), обратной (`users/manager_admin.py → orders/manager_admin.py`) быть не должно — только `users/manager_admin.py → orders/models.py`. Переносить `manager_queue` к сайту (совет 42.5) не нужно: на главную `/manager/` сводка счётчиков не добавляет.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.8, FR-42-28, NFR-42-01…04, UX Design Requirements (отдельные страницы по образцу `verify_b2b_view`, заголовок раздела).
- Контекст эпика: `_bmad-output/implementation-artifacts/epic-42-context.md` (агрегация продаж в БД, выручка по мастер-заказам, число запросов в сводке).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-5, Constraints «Гостевых заказов нет», «Учётные записи сотрудников»), `section-contents.md` («Руководитель» → «Сводка»), `affected-code.md` (строка «Сводка»).
- Предыдущие стори: `Story/42-3-…md` («Связь»: сводка подписывает коды через `region_name`), `Story/42-5-…md` (`manager_queue`, `days_ru`, календарные дни, совет о переносе очереди), `Story/42-7-…md` (`SupervisorAdminSite`, `scope_*` руководителя, `ResponsibleManagerFilter`, `TestQueryCount`, «Связь с последующими стори» → 42.8).
- Код: `backend/freesport/admin_site.py`, `backend/apps/orders/{manager_admin,models,constants}.py`, `backend/apps/orders/services/order_create.py`, `backend/apps/users/{manager_admin,staff_roles,models}.py`, `backend/apps/users/services/responsible_manager.py`, `backend/apps/common/regions.py`, `backend/apps/common/services/customer_sync_monitor.py:154`, `backend/templates/admin/{supervisor,manager}/index.html`, `backend/templates/admin/users/verify_b2b_application.html`.
- Правила: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `AGENTS.md` (GitNexus, Docker), `.windsurf/rules/gitnexus.md`, `.windsurf/rules/production-operations.md` (restart nginx).

## Вопросы к Alex — закрыты 17.10.2026

1. **Выручка без отменённых** — да: «Заказов» и «Выручка» не учитывают «Отменен» и «Возвращен», они — в колонке «Отменено» (решение 6).
2. **По текущему менеджеру и региону** — да: истории назначений нет, заказы переданного клиента уходят в строку нового менеджера вместе с прошлыми (решения 6, 7).
3. **«Верифицированы, но без заказов»** — да: только активные, за всё время, розничные с автоверификацией тоже (решение 8).
4. **Период по умолчанию — текущий месяц** — да (решение 5).
5. **Менеджеры без заказов за период** — **показывать всех, с нулями** (решение 6, AC4): все действующие менеджеры и руководители плюс менеджеры с заказами вне кандидатов (заблокированные, выведенные из групп). Таблица заявок по-прежнему показывает только менеджеров с заявками — это очередь (решение 4).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code, `bmad-dev-story`.

### Debug Log References

- GitNexus pre-flight: индекс `stale` (индексирован `88ffba3`, HEAD `b7f7031` — разница только в файле стори и `sprint-status.yaml`, вне индекса); по решению Alex («продолжай») без переиндексации. `impact --direction upstream --summary-only`: `SupervisorAdminSite` MEDIUM (15), `manager_queue` LOW (1), `days_ru` LOW (2), `ManagerClientAdmin` **LOW (11)** — в таблице стори MEDIUM (10), `scope_clients` HIGH (14), `scope_orders` LOW (4), `region_key` CRITICAL (9). `scope_clients`, `scope_orders`, `region_key` не менялись.
- Проверка мутациями (скрипт в контейнере через stdin, исходник восстанавливается побайтно в `finally`, после прогона `git status` — только файлы стори): **17 из 17 убиты**.

  | Мутация | Упал |
  |---|---|
  | свой путь после `super().get_urls()` | `TestEntry::test_supervisor_opens_summary` |
  | без `.exclude(role=unregistered)` в заявках | `TestPending::test_rows_order_and_links` |
  | «Без ответственного» только при ненулевом числе | `TestPending::test_unassigned_row_is_always_shown` |
  | сортировка заявок по подписи | `TestPending::test_rows_order_and_links` |
  | конец периода без `+ timedelta(days=1)` | `TestPeriod::test_day_boundaries` |
  | границы периода в UTC | `TestPeriod::test_day_boundaries` |
  | выручка без `filter=~Q(status__in=…)` | `TestOrdersByManager::test_rows_totals_and_period` |
  | `scope_orders` → `Order.objects.filter(user__in=scope_clients(...))` | `TestOrdersByManager::test_rows_totals_and_period` |
  | без ветки страны в `region_bucket` | `TestOrdersByRegion` (запуск с `-x`, до unit-паритета не дошёл) |
  | регулярка `^[0-9]{2}` → `^.{2}` | unit `test_region_bucket_matches_region_key` |
  | без `is_active=True` у верифицированных без заказов | `TestClients::test_verified_without_orders` |
  | `client_has_orders` только по мастер-заказам не «Отменен» | `TestClients::test_verified_without_orders` |
  | `ClientOrdersFilter` без условия `is_supervisor` | `TestClients::test_manager_has_no_orders_filter` |
  | без ссылки «Сводка» на главной | `TestLinks::test_index_links_summary_first` |
  | запрос подписей без `responsible_manager_candidate_q()` | `TestOrdersByManager::test_all_current_managers_are_listed` |
  | строки только кандидатов | `TestOrdersByManager::test_all_current_managers_are_listed` |
  | подпись менеджера запросом на строку | `TestQueryCount::test_summary` |

- Полный прогон в Docker (`-n 4 -m "not performance and not slow"`): **4658 passed, 76 skipped, 0 failed** (после 42.7 — 4609; +49 новых тестов: 30 integration, 19 unit).
- Линтеры после зачётного pytest в `-p freesport-test`: black — 490 файлов без изменений; isort — чисто; flake8 — чисто; `makemigrations --check --dry-run` — «No changes detected». mypy нашёл одну ошибку (`User` без атрибута `is_candidate` — аннотация запроса) → `# type: ignore[attr-defined]` с комментарием; повторно: mypy — 643 файла без ошибок, black/flake8 — чисто, тесты сводки и соседних разделов из Task 5 — 589 passed.
- `npx gitnexus detect-changes --scope all`: 6 файлов, risk low, 0 процессов; символы — `manager_queue`, `ManagerClientAdmin` (переменные класса — сдвиг строк), `SupervisorAdminSite`/`index`. `check --cycles`: только базовые `HomePage.tsx → index.ts → HomePage.tsx` и R42.7-D1 `users/models.py → staff_roles.py → users/models.py`, новых нет.

- Code review круг 1, исправления (17.10.2026). GitNexus: индекс `up-to-date` на `2d27b38` (= HEAD, в дереве только файлы стори); `impact SummaryPeriodForm --direction upstream --summary-only` — LOW, 1 прямой вызывающий (`resolve_period`), 0 процессов. RED: до правок кода и шаблона упали ровно три проверки — `test_invalid_period_falls_back_to_default[date-max]` (`OverflowError` в `Period.end`), `test_empty_queue` и `test_verified_without_orders` (подписи R42.8-6); регрессионные замки R42.8-1/3/4/5 на правильном коде зелёные. Временный тест подтвердил, что `date_from=0001-01-01` даёт 200: переполнение есть только у `date.max`.
- Мутации круга 1 (скрипт через stdin в контейнере, исходник восстанавливается побайтно в `finally`): **7 из 7 убиты**. В первом прогоне R42.8-5 выжила: `make_master` создаёт два субзаказа, а в прошлое ушёл только мастер, и `Exists` с фильтром по периоду находил субзаказы. Тест переносит все заказы клиента — со второго прогона мутация убита.

  | Мутация | Упал |
  |---|---|
  | `_sales_row` без `or Decimal("0")` | `TestOrdersByManager::test_groups_with_only_cancelled_orders` (`TypeError: bad operand type for unary -: 'NoneType'`) |
  | `SummaryPeriodForm.clean` без проверки `date.max` | `TestPeriod::test_invalid_period_falls_back_to_default[date-max]` (`OverflowError`) |
  | `orders_by_region` без фильтра периода | `TestOrdersByRegion::test_rows_and_totals` |
  | `_period_orders`: `scope_orders(...)` → `Order.objects.filter(is_master=True)` | `TestOrdersByManager::test_rows_totals_and_period` (заказ сотрудника в строке A) |
  | «без заказов» — `~Exists` заказов только за период | `TestClients::test_verified_without_orders` |
  | без подписи «Текущая очередь, от периода не зависит» | `TestPending::test_empty_queue` |
  | без «(за всё время)» | `TestClients::test_verified_without_orders` |

- Полный прогон после круга 1 (`-n 4 -m "not performance and not slow"`): **4661 passed, 76 skipped, 0 failed** (+3: `test_groups_with_only_cancelled_orders`, параметр `date-max`, unit `test_last_possible_date`). Линтеры после зачётного pytest в `-p freesport-test`: black — 490 файлов без изменений, isort и flake8 — чисто, mypy — 643 файла без ошибок, `makemigrations --check --dry-run` — «No changes detected».
- `npx gitnexus detect-changes --scope all`: 6 файлов, risk low, 0 процессов; из кода — только `SummaryPeriodForm`/`clean`, остальное — тесты (`test_manager_has_no_orders_filter` — сдвиг строк). `check --cycles`: только базовые `HomePage.tsx → index.ts → HomePage.tsx` и R42.7-D1, новых нет.

- Code review круг 2, исправления (17.10.2026). GitNexus: индекс `up-to-date` на `2d27b38` (= HEAD). Код не менялся — только `tests/integration/test_supervisor_summary.py`. Новые и усиленные проверки на правильном коде зелёные (53 passed в файлах сводки), их силу показывают мутации.
- Мутации круга 2 (скрипт через stdin в контейнере, исходник восстанавливается побайтно в `finally`, после прогона `git status` — только файлы стори): **4 из 4 убиты**.

  | Мутация | Упал |
  |---|---|
  | `scope_orders` без `is_master=True` | `TestOrdersByManager::test_rows_totals_and_period` (A: «4», «2 300,00 ₽») |
  | `_period_orders`: `scope_orders(...)` → клиенты `scope_clients` и заказы без клиента без `is_master` | `TestOrdersByManager::test_rows_totals_and_period` (A: «4», «2 300,00 ₽») |
  | регистрации без `created_at__lt=period.end` | `TestClients::test_registrations_in_period` |
  | заявки фильтруются по периоду | `TestPending::test_queue_does_not_depend_on_period` (A: «1», «6 дней» при 10.10–12.10) |

- Полный прогон после круга 2 (`-n 4 -m "not performance and not slow"`): **4662 passed, 76 skipped, 0 failed** (+1: `test_queue_does_not_depend_on_period`). Линтеры после зачётного pytest в `-p freesport-test`: black — 490 файлов без изменений, isort и flake8 — чисто, mypy — 643 файла без ошибок, `makemigrations --check --dry-run` — «No changes detected».
- `npx gitnexus detect-changes --scope all`: 6 файлов, risk low, 0 процессов; из кода — только `SummaryPeriodForm`/`clean` круга 1, остальное — тесты. `check --cycles`: только базовые `HomePage.tsx → index.ts → HomePage.tsx` и R42.7-D1, новых нет.

- Code review круг 3, исправления (18.10.2026). GitNexus: индекс `up-to-date` на `5d2287f` (= HEAD). Код не менялся — только тесты: `tests/integration/test_supervisor_summary.py` (R42.8-10…12) и аннотация `make_applicant` в `tests/integration/test_manager_orders_section.py` (R42.8-13). `impact make_applicant --direction upstream --summary-only` — 0 вызывающих в графе, `risk UNKNOWN` (тестовый хелпер), правка на исполнение не влияет. Усиленные проверки на правильном коде зелёные (53 passed в файлах сводки), их силу показывают мутации.
- Мутации круга 3 (скрипт через stdin в контейнере, исходник восстанавливается побайтно в `finally`, после прогона `git status` — только тесты и файлы стори): **3 из 3 убиты**.

  | Мутация | Упал |
  |---|---|
  | `orders_by_region`: все `Order` периода вместо `_period_orders()` | `TestOrdersByManager::test_rows_totals_and_period` |
  | `_period_orders`: `created_at__gte` → `created_at__gt` | `TestPeriod::test_day_boundaries` |
  | `verified_without_orders` с фильтром по дате регистрации | `TestClients::test_verified_without_orders` (число «1» вместо «2») |

- Полный прогон после круга 3 (`-n 4 -m "not performance and not slow"`): **4662 passed, 76 skipped, 0 failed** (новых тестов нет — усилены существующие). Линтеры после зачётного pytest в `-p freesport-test`: black — 490 файлов без изменений, isort и flake8 — чисто, mypy — 643 файла без ошибок, `makemigrations --check --dry-run` — «No changes detected».
- `npx gitnexus detect-changes --scope all`: 5 файлов, 7 символов, risk low, 0 процессов; символы — только тесты (`make_applicant`, `test_day_boundaries`, `test_rows_totals_and_period`, `test_verified_without_orders` и их классы). `check --cycles`: только базовые `HomePage.tsx → index.ts → HomePage.tsx` и R42.7-D1, новых нет.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created (`bmad-create-story`, 2026-10-17).
- Реализовано: страница `/supervisor/summary/` (`SupervisorAdminSite.get_urls` до catch-all, `summary_view`, ссылка «Сводка» первой на главной); модуль `apps/orders/supervisor_summary.py` — период (форма, быстрые ссылки, полуинтервал в часовом поясе проекта), заявки по менеджерам, заказы и выручка по менеджерам и регионам, клиенты; `waiting_age` вынесена из `manager_queue` без изменения текста; `client_has_orders` и фильтр «Заказы» только руководителю. Страница делает фиксированное число запросов (AC8): заявки, заказы по менеджерам, по регионам, клиенты и один общий запрос подписей менеджеров.
- Отклонения от стори (с причиной):
  - публичных имён больше, чем перечислено в решении 2: `pending_table`, `manager_sales_table`, `load_managers`, `region_label`, `split_bucket`, `sales_total`, `this_month`, `PendingRow`, `SalesRow` — подписи строятся после общего запроса менеджеров (решение 4), поэтому `pending_applications` и `orders_by_manager` возвращают сгруппированные значения, а строки собирают отдельные функции. `orders_by_region` возвращает таблицу сразу — подписи регионов запросов не требуют;
  - ключ `region_bucket()` — строка «вид:значение», виды страны и региона ИНН совпадают с `ManagerRoutingRule.MATCH_*` (решение 7 оставляло выбор исполнителю);
  - подписи полей периода — «Начало периода» / «Конец периода» (в стори не заданы); ошибки обоих полей и формы выводятся над полями;
  - в integration-тесты дополнительно импортирована autouse-фикстура `order_emails` из `test_manager_orders_section` (письма о заказе без брокера Celery), как в `test_supervisor_section.py`;
  - в AC4 передача клиента B сделана `update()` поля `responsible_manager`, а не формой карточки: проверяется правило «по текущему ответственному», ручное назначение в карточке уже покрыто `TestManualAssignment` стори 42.7.
- Факт для AC6: подделанный `?has_orders=no` у менеджера — 302 на `?e=1` (как у `responsible`), чужих клиентов в списке нет. Неизвестное значение `has_orders` у руководителя — тоже 302 на `?e=1`.
- Ответы Alex на вопросы стори (17.10.2026) учтены: выручка без «Отменен»/«Возвращен»; заказы и регион — по текущему ответственному и текущему региону; «верифицированы, но без заказов» — только активные, за всё время; период по умолчанию — текущий месяц; в таблице заказов все действующие менеджеры с нулями.
- ✅ Resolved review finding [medium]: R42.8-1 — `test_groups_with_only_cancelled_orders`: у менеджера C и региона 77 в периоде только `cancelled`/`refunded` — строки «0», «0,00 ₽», «2», «Итого» обеих таблиц «1», «500,00 ₽», «2». Код не менялся: `or Decimal("0")` уже был, теперь его удаление роняет тест.
- ✅ Resolved review finding [low]: R42.8-2 — `SummaryPeriodForm.clean()` даёт ошибку поля `date_to` «Конец периода вне допустимого диапазона.» при `date_to == date.max` (вместо 500 из `Period.end`); параметр `date-max` в `test_invalid_period_falls_back_to_default`, unit `TestPeriodForm::test_last_possible_date` (31.12.9998 и раньше — форма верна). Текст ошибки в стори не задан — выбран исполнителем.
- ✅ Resolved review finding [low]: R42.8-3 — в `TestOrdersByRegion` два заказа 15.09 (регион 77 и 50, по 9999 ₽): строка 77 не меняется, строки 50 нет.
- ✅ Resolved review finding [low]: R42.8-4 — в `test_rows_totals_and_period` мастер-заказ 5000 ₽ учётной записи маркетолога с ответственным A: строки и «Итого» прежние.
- ✅ Resolved review finding [low]: R42.8-5 — в `test_verified_without_orders` все заказы клиента `with_order` (мастер и субзаказы) перенесены на 15.01.2025, вне периода по умолчанию.
- ✅ Resolved review finding [low]: R42.8-6 — в шаблоне под таблицей заявок `<p class="help">Текущая очередь, от периода не зависит</p>`, у числа клиентов без заказов — « (за всё время)». AC6 «Верифицированы, но без заказов: 2» остаётся началом строки; ожидание `test_verified_without_orders` дополнено, `test_empty_queue` проверяет подпись внутри блока заявок.
- ✅ Resolved review finding [medium]: R42.8-7 — `set_order_created` переносит мастер вместе с субзаказами (`Q(pk=…) | Q(parent_order=…)`): в `test_rows_totals_and_period` два субзаказа по 500 ₽ теперь внутри периода, и выручку A «1 300,00 ₽» держит только `is_master`. Хелпер общий для всех сценариев сводки — остальные ожидания не изменились.
- ✅ Resolved review finding [low]: R42.8-8 — в `test_registrations_in_period` клиент, созданный 13.10.2026 00:00 МСК (начало дня после периода): число остаётся «4».
- ✅ Resolved review finding [low]: R42.8-9 — новый `TestPending::test_queue_does_not_depend_on_period`: заявки A от 11.10 и 15.09, заявка без ответственного от 17.10; при периодах 10.10–12.10, 01.09–30.09 и без параметров строки (A «2», «32 дня»; «Без ответственного» «1», «сегодня»; «Итого» «3») и ссылки одинаковы.
- ✅ Resolved review finding [low]: R42.8-10 — в `test_rows_totals_and_period` проверено региональное «Итого» «5», «1 900,00 ₽», «2»: два субзаказа в периоде и заказ маркетолога в него не входят.
- ✅ Resolved review finding [low]: R42.8-11 — заказ `utc-evening` в `test_day_boundaries` перенесён на 09.10 21:00 UTC (ровно 10.10 00:00 МСК); ожидание «2», «350,00 ₽» прежнее.
- ✅ Resolved review finding [low]: R42.8-12 — в `test_verified_without_orders` регистрация одного из `idle` перенесена на 15.01.2025; число остаётся «2».
- ✅ Resolved review finding [low]: R42.8-13 — аннотация `make_applicant(manager: User | None, ...)`, как у `make_client`.
- Выкат: миграций, ручных шагов в БД и правок nginx нет. После выката: `curl -sI https://optisport.ru/supervisor/summary/` → 302 на `/supervisor/login/?next=/supervisor/summary/`; при 404 от Next — `docker compose exec nginx nginx -s reload`. Пока на проде нет правил регионов, почти все заявки и заказы будут в строках «Без ответственного» — это ожидаемо.

### File List

- `backend/apps/orders/supervisor_summary.py` (новый)
- `backend/templates/admin/supervisor/summary.html` (новый)
- `backend/tests/integration/test_supervisor_summary.py` (новый)
- `backend/tests/unit/test_supervisor_summary.py` (новый)
- `backend/tests/integration/test_manager_orders_section.py` (аннотация `make_applicant`, R42.8-13)
- `backend/freesport/admin_site.py`
- `backend/apps/orders/manager_admin.py`
- `backend/apps/users/manager_admin.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/Story/42-8-supervisor-summary.md`

### Change Log

- 2026-10-17 — стори создана (`bmad-create-story`) на `1ea0fb2c`, статус `ready-for-dev`.
- 2026-10-17 — ответы Alex: вопросы 1–4 — по умолчаниям стори; вопрос 5 — в таблице заказов по менеджерам все действующие менеджеры, в том числе с нулями (решения 4, 6, AC4, AC8, две строки мутаций).
- 2026-10-17 — реализация (`bmad-dev-story`) на `feature/42-8-supervisor-summary`: сводка `/supervisor/summary/`, `waiting_age`, фильтр «Заказы» руководителя; 49 новых тестов, 17 из 17 мутаций убиты; полный прогон 4658 passed, 76 skipped, 0 failed; линтеры и mypy чисто. Статус `review`.
- 2026-10-17 — code review круг 1 (через плагин Codex): 6 patch, 0 defer, 8 отклонено → `in-progress`.
- 2026-10-17 — Addressed code review findings - 6 items resolved: R42.8-1…6 — ошибка формы вместо 500 на `date_to=9999-12-31`, подписи «от периода не зависит» / «за всё время», 3 новых теста и 4 усиленных сценария; 7 из 7 мутаций убиты; полный прогон 4661 passed, 76 skipped, 0 failed; линтеры и mypy чисто. Статус `review`.
- 2026-10-17 — code review круг 2 (через плагин Codex): 3 patch (R42.8-7 medium — субзаказы вне периода, правило `is_master` не закреплено; R42.8-8, R42.8-9 low), 0 defer, 12 отклонено → `in-progress`.
- 2026-10-17 — Addressed code review findings - 3 items resolved: R42.8-7…9 — мастер переносится в период вместе с субзаказами, верхняя граница регистраций, независимость очереди заявок от периода (1 новый тест, 2 усиленных сценария); 4 из 4 мутаций убиты; полный прогон 4662 passed, 76 skipped, 0 failed; линтеры и mypy чисто. Статус `review`.
- 2026-10-18 — code review круг 3 (через плагин Codex): 4 patch (R42.8-10…13 low — региональное «Итого» против субзаказов и сотрудников, граница 00:00, «без заказов» против даты регистрации, аннотация `make_applicant`), 0 defer, 12 отклонено → `in-progress`.
- 2026-10-18 — Addressed code review findings - 4 items resolved: R42.8-10…13 — региональное «Итого» против субзаказов и заказа сотрудника, нижняя граница периода ровно 00:00, «без заказов» против даты регистрации, аннотация `make_applicant` (только тесты, 3 усиленных сценария); 3 из 3 мутаций убиты; полный прогон 4662 passed, 76 skipped, 0 failed; линтеры и mypy чисто. Статус `review`.
- 2026-10-18 — code review круг 4 (через плагин Codex): 2 patch (R42.8-14, R42.8-15 low — продажи в статусах кроме `pending`, условие `verified` отдельно от `is_active`; только тесты), 0 defer, 12 отклонено → `in-progress`.
