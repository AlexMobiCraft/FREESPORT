---
baseline_commit: d53f42a6
---

# Story 42.5: Раздел менеджера — заказы и главная страница

Status: in-progress
Baseline Revision: d53f42a6 (`develop` = `353e33a7` + коммит nginx-фикса в ветке `fix/nginx-prod-stale-bind-mount`; код приложения на обоих одинаковый)

## Story

As a менеджер,
I want видеть заказы своих клиентов, вести трек-номер и дату доставки, а на главной — сколько заявок и заказов ждут меня,
so that я начинаю день с понятной очереди и не правлю то, что принадлежит 1С.

**Закрывает:** FR-42-15, FR-42-16, FR-42-17 (заказы, экспорт), FR-42-30 (действия над заказом). **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.5), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-3, Constraints), состав раздела — `section-contents.md`, «Менеджер → Заказы» и «Главная раздела».

**Предусловия:**
- **Код 42.4 в `develop` и `main`** (PR #309, мёрдж `353e33a7`): сайт `manager_site`, `scope_clients`, `ManagerClientAdmin`, главная `admin/manager/index.html`, nginx-локация `/manager/`. Проверка: `grep -n "def scope_clients" backend/apps/users/manager_admin.py`. Статус 42.4 в `sprint-status.yaml` — `review`; если к началу работы ревью 42.4 вернёт правки в `manager_admin.py`, ветку 42.5 пересадить на свежий `develop`.
- Ветка `feature/42-5-manager-section-orders` от `develop`.
- **Выкат** — после выката 42.4. Ручных шагов на проде у стори нет.

**Чего в этой стори нет:**
- заказов без клиента и снятия фильтра для руководителя — 42.7 (там же правится `scope_clients`, а вслед за ним и `scope_orders`);
- ленты журнала — 42.9 (здесь только записи `AuditLog`);
- смены статуса заказа, состава, оплаты — никогда: статус приходит только из 1С;
- изменений во фронтенде, моделях, миграциях, API.

## Утверждённые решения (не пересматривать)

1. **Заказы регистрируются на том же `manager_site`** из 42.4: `ManagerOrderAdmin(OrderAdmin)` в новом модуле `apps/orders/manager_admin.py`, импорт модуля в `OrdersConfig.ready()`. Доступ к разделу не меняется: `ManagerAdminSite.has_permission` (группы «Менеджеры» и «Руководители», без суперпользователя).
2. **Видимость — одна функция `scope_orders(request, queryset)`:** мастер-заказы (`is_master=True`), у которых `user` — в `scope_clients(request, User.objects.all())`. Своего правила видимости у заказов нет: заказ виден ровно тогда, когда виден его клиент. Заказы без клиента (`user IS NULL`) и заказы учётных записей сотрудников не видны никогда. `scope_clients` (GitNexus: risk HIGH, 3 процесса раздела клиентов) **не меняется**, только вызывается.
3. **Чужой заказ и субзаказ по прямому URL — 404**, как у клиентов: `_get_obj_does_not_exist_redirect` → `raise Http404("Заказ не найден")`. Субзаказ (`is_master=False`) вне `scope_orders`, поэтому его карточка тоже 404 — субзаказы видны только внутри карточки мастера.
4. **Карточка — белый список полей** (как решение 5 стори 42.4). Правятся только `tracking_number` и `delivery_date`. `notes` — комментарий клиента из оформления, он виден клиенту в ЛК, поэтому в разделе только для чтения (решение Alex 15.10.2026, см. «Чей это комментарий»; эпик FR-42-15 и `section-contents.md` поправлены). Всё остальное, что показано, — только чтение. `payment_id`, `parent_order`, `vat_group`, `status_1c`, `sent_to_1c_at`, а также служебные `export_skipped`, `customer_code_snapshot`, `order_year`, `customer_year_sequence`, `suborder_sequence`, `is_master` в форме отсутствуют.
5. **Сохранение — только правимые поля через `save(update_fields=…)`.** `save_model` пишет в БД пересечение `form.changed_data` с двумя правимыми полями плюс `updated_at`. Пустое пересечение — `save()` не вызывается вовсе: ни `post_save`, ни записи журнала. Так:
   - подделанный POST не может изменить другие колонки, даже если белый список формы когда-нибудь расширят по ошибке;
   - правка менеджера не затирает статус, оплату и флаги 1С, которые импорт статусов пишет параллельно (`order_status_import.py:785`, `:914` — тоже `update_fields` под `select_for_update`);
   - `post_save` бонусов (`bonuses/signals.py:18`) срабатывает только при реальной правке и видит статус, прочитанный в этом запросе. Начисление идемпотентно (`accrual.py`, проверка по `order_number_snapshot`), а статус в форме не меняется, поэтому лишнего начисления нет.
6. **Блокировок строк в карточке заказа нет — это осознанно, а не пропуск.** В 42.4 блокировка строки клиента понадобилась потому, что полное `save()` устаревшего объекта возвращало прежнего ответственного (R42.4-1, R42.4-5). Здесь `save()` пишет только два поля и `updated_at`, а их не трогает ни импорт статусов (сверено: `order_status_import.py` не пишет ни `tracking_number`, ни `delivery_date`; единственная запись — копия в субзаказы при создании, `order_create.py:128-130`), ни передача клиента, ни пересчёт ответственных. Передача клиента другому менеджеру меняет строку `users`, а не `orders`: правка, попавшая в миллисекундное окно передачи, записывает трек-номер под автором-менеджером A, и это видно в журнале. Вред — нулевой, а блокировка `users` из карточки заказа добавила бы порядок блокировок `users → orders` против `orders → bonuses` импорта. Ревьюеру: это не повтор R42.4-1.
7. **Журнал правки заказа — одна запись `AuditLog` на сохранение:** `action="update_order"`, `resource_type="Order"`, `resource_id=<pk мастер-заказа>`, `changes={"order_number": <канонический>, "fields": {<поле>: {"old": …, "new": …}}}`. В `fields` — только реально изменённые поля из двух. Даты — строкой ISO, пустые — `None`. Старое значение — из `form.initial`. Django `LogEntry` пишется штатно, отдельно; это не дубль: 42.9 строит ленту по `AuditLog`.
8. **Экспорт CSV — своё действие раздела `export_orders_csv` с русскими заголовками и BOM** (решение Alex 15.10.2026: менеджеры открывают файл двойным кликом в Excel на Windows, без BOM кириллица превращается в кракозябры, а английские заголовки нарушают NFR-42-03). Колонки те же восемь и в том же порядке, что у `OrderAdmin.export_to_csv`, заголовки по-русски: «Номер заказа», «Номер (UI)», «Клиент», «Статус», «Оплата», «Сумма», «Способ доставки», «Дата создания». Файл начинается с `﻿`, `Content-Type: text/csv; charset=utf-8`, имя `orders_export.csv`. `OrderAdmin.export_to_csv` в `/admin/` **не меняется** — поэтому тело своё, а не вызов родителя. Выборка уже ограничена: `response_action` берёт строки из `ChangeList.get_queryset`, то есть из `get_queryset` раздела, и при `_selected_action`, и при `select_across=1`.
9. **«Новые заказы» — мастер-заказы своих клиентов в статусе `pending`** («Ожидает обработки»). Ссылка — `/manager/orders/order/?status__exact=pending`. Статус `pending` у заказа с сайта до решения в 1С, и в него же 1С переводит «Не согласован» и «На согласовании» (`orders/constants.py`, `STATUS_MAPPING`), то есть это заказы, которые ещё ждут обработки. Решение подтверждено замером прода 15.10.2026: мастер-заказ на проде один (`0000026001`, `pending` с 10.07.2026, клиент с ответственным менеджером), копиться счётчику пока не из чего. Вариант «за последние N дней» не нужен.
10. **«Заявки на верификацию» — клиенты из `scope_clients` со статусом `verification_status="pending"` без записей `unregistered`** — ровно то, что покажет список клиентов по ссылке `/manager/users/user/?verification_status__exact=pending`: фильтр «Учётная запись на портале» по умолчанию скрывает `unregistered` (42.4, `PortalAccountFilter`). «Старейшая» считается по `created_at`: заявка подаётся при регистрации (`users/serializers.py:381`). Исключение — устаревший путь привязки по ссылке (`views/authentication.py:675`), где `created_at` — дата импорта записи 1С; путь отключён с 26.07.2026, точность для него не нужна. **Возраст старейшей — в календарных днях**, а не в полных сутках: `(timezone.localdate() - timezone.localtime(oldest).date()).days`. Заявка, поданная вчера в 23:50, в 00:10 — «1 день», а не «0». Возраст 0 — «старейшая — сегодня». На проде 15.10.2026 заявок 13 (все `wholesale_level1`, у всех есть ответственный, сотрудников среди них нет), самая старая — от 26.03.2026: в первый день главная покажет «старейшая — 203 дня». Это не дефект, а очередь, которую раздел и должен показать.
11. **Счётчики главной считает `ManagerAdminSite.index`** через функцию `manager_queue(request, site_name)` из `apps/orders/manager_admin.py`. Импорт — внутри метода: `apps/orders/manager_admin.py` сам импортирует `manager_site` из `freesport/admin_site.py`, импорт на уровне модуля дал бы цикл. Каждый счётчик — один агрегирующий запрос, число запросов главной от числа заявок и заказов не зависит (NFR-42-04).
12. **Клиент в карточке заказа — display-метод со ссылкой в раздел**, не readonly-FK `user` (урок 42.4, решение 12: новое readonly-поле FK в карточке раздела — только display-методом). Ссылка — `reverse(f"{self.admin_site.name}:users_user_change", args=[obj.user_id])`: заказ виден только при видимом клиенте, поэтому ссылка ведёт не в 404.
13. **Подписи раздела — по-русски** (NFR-42-03). Display-методы `OrderAdmin` подписаны по-английски («Customer», «Items Count», «Payment Status», «Display Number»), поэтому `ManagerOrderAdmin` объявляет свои обёртки с русскими `description`. `OrderAdmin` в `/admin/` не меняется.

## Acceptance Criteria

### AC1 — вход в заказы раздела

**Given** менеджер, руководитель, маркетолог, сотрудник без группы, суперпользователь и аноним
**When** каждый открывает `/manager/orders/order/`
**Then** менеджер и руководитель получают 200, заголовок списка — «Заказы»
**And** остальные получают 302 на `/manager/login/`
**And** на главной `/manager/` у менеджера есть блок «Заказы» со ссылкой на `/manager/orders/order/`

### AC2 — список только мастер-заказов своих клиентов

**Given** менеджер A и менеджер B, у каждого клиент с мастер-заказом из двух субзаказов
**When** A открывает список заказов
**Then** в нём только мастер-заказы клиентов A, субзаказов в списке нет
**And** нет заказов: клиента B; учётной записи сотрудника с `responsible_manager=A` (по одной записи на каждое условие `staff_accounts_q()`: `is_staff`, суперпользователь, `role="admin"`, член группы роли без `is_staff`); заказа без клиента (`user=None`)
**And** колонки: номер, клиент, статус, оплата, сумма, число позиций, дата
**And** поиск по шести значениям заказа клиента B — номеру в каноническом формате и в формате UI, email учётной записи (`user__email`), email из заказа (`customer_email`), трек-номеру и названию компании — ничего не находит, а свой заказ по тем же полям находится

### AC3 — 404 на чужой заказ и на субзаказ

**Given** менеджер A
**When** он открывает по прямому URL карточку (`/manager/orders/order/<id>/change/`, GET и POST) или историю (`…/history/`) заказа клиента B, а также карточку субзаказа своего клиента
**Then** каждая отвечает 404, данные заказа B не меняются, записи `AuditLog` не создаются
**And** `/manager/orders/order/add/` и `…/<id>/delete/` своего заказа отвечают 403

### AC4 — состав карточки

**Given** менеджер открывает свой мастер-заказ
**When** страница отрисована
**Then** в форме правятся только `tracking_number` и `delivery_date`
**And** только для чтения: номер (UI и канонический), клиент (ссылка на `/manager/users/user/<id>/change/`), статус, контакты из заказа (`customer_name`, `customer_email`, `customer_phone`), комментарий клиента (`notes`, блок «Комментарий клиента»; в HTML нет `name="notes"`), состав (позиции всех субзаказов: субзаказ, товар, артикул, количество, цена, сумма), суммы (`total_amount`, `discount_amount`, `delivery_cost`), адрес и способ доставки, способ и статус оплаты, даты оплаты и отгрузки, «Передан в 1С: да/нет», даты создания и обновления
**And** субзаказы показаны блоком только для чтения: номер, статус, сумма; без ссылок на их карточки, без добавления и удаления
**And** в HTML нет ни поля (`name="…"`), ни подписи из списка «Не показывать»: `payment_id` («ID платежа (ЮKassa)»), `parent_order` («Мастер-заказ»), `vat_group` («Группа НДС (%)»), `status_1c` («Статус из 1С»), `sent_to_1c_at` («Дата и время отправки в 1С»), `export_skipped` («Пропущен при экспорте») — в том числе в блоке субзаказов
**And** кнопок «Добавить» и «Удалить» нет

### AC5 — подделанный POST заказа

**Given** клиент-тренер (`role="trainer"`, верифицирован), активная бонусная программа с `accrual_status="delivered"` и без отсечки по дате, его мастер-заказ в статусе `processing`
**When** менеджер отправляет карточку с новым трек-номером и подделанными `status=delivered`, `payment_status=paid`, `sent_to_1c`, `total_amount`, `payment_id`, `user`, `parent_order`, `vat_group`, `status_1c`, `notes`
**Then** сохранён только трек-номер, остальные поля прежние (в том числе `notes`)
**And** `BonusTransaction` по заказу не создана
**And** `Order.save` вызван с `update_fields`, состоящим только из изменённых правимых полей и `updated_at` (решение 5)

**Given** тот же клиент-тренер и программа, но его мастер-заказ **уже** в статусе `delivered`, а бонус по нему не начислен (заказ переведён `update()` в обход сигнала)
**When** менеджер дважды подряд меняет трек-номер
**Then** после первой правки по заказу ровно одна `BonusTransaction`, после второй — по-прежнему одна
**And** это закрепляет штатное поведение из «Подводных камней» («Бонус при сохранении»): сигнал `bonuses/signals.py:18` срабатывает на `save(update_fields=…)`. Тест упадёт, если кто-то отсечёт сигнал по `update_fields`, и начисления, отложенные до правки, молча пропадут

### AC6 — экспорт CSV только своих заказов

**Given** менеджер A, его заказы и заказ клиента B
**When** A применяет «Выгрузить выбранные заказы в CSV» со списком `_selected_action`, где подделан id заказа B, и отдельно с `select_across=1` без выбора
**Then** в обоих файлах только заказы клиентов A, номера заказа B нет
**And** файл начинается с BOM (`response.content[:3] == b"\xef\xbb\xbf"`), первая строка — русские заголовки из решения 8, порядок колонок — как у `OrderAdmin.export_to_csv`
**And** экспорт в `/admin/` прежний: без BOM, английские заголовки (`tests/unit/test_orders_admin.py` без правок)
**And** в выпадающем списке действий раздела нет «Удалить выбранные» и нет английских подписей

### AC7 — журнал правки заказа

**Given** менеджер меняет трек-номер или дату доставки своего заказа
**When** заказ сохранён
**Then** в `AuditLog` ровно одна запись `update_order` с `user` = менеджер, `resource_type="Order"`, `resource_id` = заказ и изменёнными полями со старым и новым значением (решение 7)
**And** сохранение без изменений не пишет записи и не меняет `updated_at`
**And** правка одного поля пишет в `fields` только это поле

### AC8 — главная со счётчиками

**Given** у менеджера A три заявки на верификацию (старейшей пять дней), два заказа в статусе `pending` и один в `processing`; у менеджера B — своя заявка и свой новый заказ
**When** A открывает `/manager/`
**Then** видно «Заявки на верификацию: 3, старейшая — 5 дней» и «Новые заказы: 2»
**And** счётчик заявок ведёт на `/manager/users/user/?verification_status__exact=pending`, счётчик заказов — на `/manager/orders/order/?status__exact=pending`
**And** по каждой ссылке список содержит ровно столько строк, сколько в счётчике, и только записи A
**And** без заявок — «Заявки на верификацию: 0» без части про старейшую; склонение дней верное (1 день, 2 дня, 5 дней, 11 дней, 21 день)
**And** заявка, поданная сегодня, — «старейшая — сегодня»; поданная вчера в 23:50 при текущем времени 00:10 — «старейшая — 1 день» (календарные дни в часовом поясе проекта, решение 10)

### AC9 — права внутри раздела

**Given** член «Менеджеры», у группы которого в тесте оставлено только `orders.view_order` (и `users.view_user` — для входа на главную)
**When** он открывает свой заказ, отправляет POST карточки и экспорт
**Then** карточка открывается только для чтения (в форме нет полей ввода `tracking_number`, `delivery_date`)
**And** POST отвечает 403, заказ не меняется, `AuditLog` не пишется
**And** экспорт CSV доступен и выгружает только его заказы

### AC10 — ссылки раздела ведут в раздел

**Given** менеджер на главной, в списке заказов, в карточке и в истории заказа
**When** страница отрисована и после сохранения карточки
**Then** в HTML нет `href="/admin/`, редирект после «Сохранить» ведёт на `/manager/orders/order/`, после «Сохранить и продолжить» — на `/manager/orders/order/<id>/change/`
**And** главная проверяется после сохранения заказа, когда у менеджера уже есть `LogEntry` по заказу: блока «Последние действия» нет

### AC11 — число запросов (NFR-42-04)

**Given** у менеджера 5 мастер-заказов по два субзаказа с позициями, затем 50
**When** он открывает список заказов
**Then** число SQL-запросов в обоих случаях одинаковое
**And** на главной число запросов при 3 и при 30 заявках и заказах одинаковое

### AC12 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `black --check`, `isort --check`, `flake8`, `mypy`, `makemigrations --check`
**Then** всё зелёное; ожидания существующих тестов не меняются (`tests/unit/test_orders_admin.py`, `tests/integration/test_manager_clients_section.py` — без правок)

## Tasks / Subtasks

- [x] **Task 0 — GitNexus pre-flight** (AGENTS.md)
  - [x] `npx gitnexus status`. При `stale` — `git diff --stat <indexed> HEAD -- backend/apps backend/freesport`: пусто — переиндексация не нужна (на `d53f42a6` индекс на `7b169a1`, разница только в CI, deploy-скриптах, nginx и тестах скриптов). Иначе попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [x] `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по `OrderAdmin`, `export_to_csv`, `items_count`, `ManagerAdminSite`. При подготовке стори: `OrderAdmin` — LOW, 0 вызывающих; `ManagerAdminSite` — LOW, 2 прямых импорта (`freesport/urls.py`, `apps/users/manager_admin.py`). `scope_clients` — HIGH, но стори его не меняет. Сообщить Alex blast radius до правок.

- [x] **Task 1 — `ManagerOrderAdmin`** (AC1–AC7, AC9–AC11; решения 1–8, 12, 13)
  - [x] Новый модуль `backend/apps/orders/manager_admin.py`, регистрация в нём же: `manager_site.register(Order, ManagerOrderAdmin)`. Импорт в `OrdersConfig.ready()` (`apps/orders/apps.py`) рядом с `import apps.orders.signals`: `import apps.orders.manager_admin  # noqa: F401 — регистрация на сайте /manager/`. Порядок безопасен, как в 42.4: `FreesportAdminConfig` стоит в `DJANGO_APPS` раньше `apps.users` и `apps.orders`, и `admin.autodiscover()` к этому моменту уже загрузил оба `admin.py`.
  - [x] Функция видимости (решение 2), docstring о 42.7:
    ```python
    def scope_orders(request: HttpRequest, queryset: QuerySet[Order]) -> QuerySet[Order]:
        return queryset.filter(is_master=True, user__in=scope_clients(request, User.objects.all()))
    ```
    `user__in` с подзапросом отсекает и `user IS NULL`. Проверить в тесте AC11, что на строку лишнего запроса нет.
  - [x] `class ManagerOrderAdmin(OrderAdmin)`:
    - `get_queryset`: `scope_orders(request, super().get_queryset(request))` — `select_related("user")` и `prefetch_related("items", "sub_orders__items")` родителя сохраняются;
    - `_get_obj_does_not_exist_redirect(self, request, opts, object_id)` → `raise Http404("Заказ не найден")` (решение 3), с комментарием, как в `ManagerClientAdmin`;
    - `has_add_permission` → `False`, `has_delete_permission` → `False`;
    - `list_display = ["order_number_ui", "customer", "status", "payment_status_ru", "total_amount", "positions", "created_at"]`, `list_display_links = ["order_number_ui"]` — обёртки с русскими подписями (решение 13): `order_number_ui` («Номер», `ordering="order_number"`) → `obj.order_number_display`; `customer` («Клиент», `ordering="user__email"`) → `self.customer_display(obj)`; `payment_status_ru` («Оплата») → `self.payment_status_display(obj)`; `positions` («Позиций») → `self.items_count(obj)`;
    - `list_filter = ["status", "payment_status", "delivery_method"]`, `date_hierarchy = "created_at"` (как у родителя);
    - `search_fields = ["order_number", "user__email", "customer_email", "tracking_number", "user__company_name"]`. `get_search_results` родителя (нормализация UI-номера) наследуется: `base_queryset` в нём — уже выборка раздела, поэтому объединение `queryset | normalized_queryset` чужого не добавляет. Тест AC2 это закрепляет;
    - `actions = ["export_orders_csv"]` и метод `@admin.action(description="Выгрузить выбранные заказы в CSV") def export_orders_csv(self, request, queryset)` (решение 8): своё тело по образцу `OrderAdmin.export_to_csv` (`orders/admin.py`, те же восемь значений строки и `queryset.select_related("user")`), но заголовки русские, а первым в ответ пишется `"﻿"` (`response.write("﻿")` до `csv.writer`). Заголовки — модульная константа `MANAGER_CSV_HEADER`. Родителя не трогать и не звать;
    - `inlines = [SubOrderInline]`;
    - `fieldsets` — белый список (решение 4):
      ```python
      fieldsets = (
          ("Заказ", {"fields": ("order_number_ui", "order_number", "client_link", "status", "created_at", "updated_at")}),
          ("Контакты из заказа", {"fields": ("customer_name", "customer_email", "customer_phone")}),
          ("Состав и суммы", {"fields": ("items_table", "total_amount", "discount_amount", "delivery_cost")}),
          ("Доставка", {"fields": ("delivery_method", "delivery_address", "delivery_date", "tracking_number")}),
          ("Оплата", {"fields": ("payment_method", "payment_status", "paid_at", "shipped_at", "sent_to_1c_ru")}),
          ("Комментарий клиента", {"fields": ("notes",)}),
      )
      ```
    - `readonly_fields` — всё из fieldsets, кроме `delivery_date` и `tracking_number` (`notes` — только чтение, решение 4). `get_readonly_fields` возвращает список целиком, без логики родителя (у родителя он статичен — проверить, что `OrderAdmin` его не переопределяет);
    - `get_fieldsets` → `self.fieldsets` как есть;
    - display-методы: `client_link` («Клиент», решение 12) — `format_html('<a href="{}">{}</a>', reverse(f"{self.admin_site.name}:users_user_change", args=[obj.user_id]), …)`, подпись — email и компания; `items_table` («Состав») — таблица `format_html_join` по позициям: у мастера с субзаказами — позиции всех субзаказов с номером субзаказа, у мастера без субзаказов (legacy) — его собственные. Брать из `obj.sub_orders.all()` и `sub.items.all()` / `obj.items.all()`: `get_object` идёт через `get_queryset`, prefetch родителя уже загрузил их. `_get_order_display_items` (`orders/tasks.py:22`) не использовать: он строит новый запрос с `select_related`, а нужного там нет; `sent_to_1c_ru` («Передан в 1С», `boolean=True`) → `obj.sent_to_1c`;
    - `changelist_view`: `extra_context["title"] = "Заказы"`.
  - [x] `save_model` (решения 5 и 7):
    ```python
    EDITABLE_FIELDS = ("tracking_number", "delivery_date")

    def save_model(self, request, obj, form, change):
        changed = [name for name in EDITABLE_FIELDS if name in form.changed_data]
        if not changed:
            return
        obj.save(update_fields=[*changed, "updated_at"])
        AuditLog.log_action(
            user=request.user,
            action="update_order",
            resource_type="Order",
            resource_id=obj.pk,
            changes={
                "order_number": obj.order_number,
                "fields": {name: {"old": _audit_value(form.initial.get(name)), "new": _audit_value(getattr(obj, name))} for name in changed},
            },
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    ```
    `change` всегда `True` (добавления нет). `_audit_value`: `date` → `isoformat()`, `""`/`None` → `None`, строка — как есть. IP — по образцу `UserAdmin._get_client_ip` (`users/admin.py:1336`): `get_client_ip` из `apps.common.utils.consent_audit`, `"unknown"` → `"0.0.0.0"`. Не наследовать `UserAdmin` ради одного метода — продублировать три строки модульной функцией.
  - [x] `SubOrderInline(admin.TabularInline)`: `model = Order`, `fk_name = "parent_order"`, `fields = readonly_fields = ("sub_number", "status", "total_amount")`, `sub_number` («Субзаказ») → `obj.order_number_display`; `can_delete = False`, `show_change_link = False`, `extra = 0`; `has_add_permission`, `has_change_permission`, `has_delete_permission` → `False`. `verbose_name = "Субзаказ"`, `verbose_name_plural = "Субзаказы"`. Без `vat_group` (решение 4). Убедиться, что view-only инлайн не ломает POST карточки: форма инлайна без изменяемых полей, `has_changed()` ложно — Django ничего не пишет.

- [x] **Task 2 — главная со счётчиками** (AC8, AC10, AC11; решения 9–11)
  - [x] В `apps/orders/manager_admin.py` — `manager_queue(request, site_name) -> list[dict]`:
    - заявки: `scope_clients(request, User.objects.all()).exclude(role=User.ROLE_UNREGISTERED).filter(verification_status="pending").aggregate(count=Count("pk"), oldest=Min("created_at"))` — один запрос;
    - новые заказы: `scope_orders(request, Order.objects.all()).filter(status="pending").count()` — один запрос;
    - ссылки через `reverse(f"{site_name}:users_user_changelist")` и `reverse(f"{site_name}:orders_order_changelist")` с `?verification_status__exact=pending` и `?status__exact=pending`;
    - текст: «Заявки на верификацию: N, старейшая — X <дней>» (при N = 0 — «Заявки на верификацию: 0»), «Новые заказы: N». Дни — календарные (решение 10): `(timezone.localdate() - timezone.localtime(oldest).date()).days`; 0 — «старейшая — сегодня». Склонение — модульная функция `days_ru(n)` (1 день, 2–4 дня, 5–20 дней, 11–14 дней, 21 день, 111 дней). Готовой в проекте нет.
  - [x] `ManagerAdminSite.index` (`freesport/admin_site.py`): `from apps.orders.manager_admin import manager_queue` внутри метода (решение 11), `extra_context = {**(extra_context or {}), "manager_queue": manager_queue(request, self.name)}`, затем `super().index(request, extra_context)`. `index` оборачивается `admin_view` в `get_urls` через `self.index`, поэтому проверка доступа идёт до подсчёта.
  - [x] Шаблон `backend/templates/admin/manager/index.html`: сохранить `{% block sidebar %}{% endblock %}` (решение 13 стори 42.4) и добавить `{% block content %}` — блок очереди (`<div class="module" id="manager-queue">`, таблица со ссылками из `manager_queue`) и затем `{{ block.super }}` (список моделей из проектного `templates/admin/index.html`). Обновить комментарий шаблона: счётчики — 42.5.
  - [x] Подпись блока «Заказы» на главной не трогать: `verbose_name` приложения и модели уже «Заказы». `ManagerAdminSite.get_app_list` не менять.

- [x] **Task 3 — тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [x] `backend/tests/integration/test_manager_orders_section.py` (integration). Хелперы и autouse-фикстуры — явным импортом из `tests.integration.test_manager_clients_section`: `role_groups`, `no_routing_rules`, `verified_email_task`, `make_staff_member`, `make_client`, `form_payload`, `message_texts`, `PASSWORD`, `get_unique_suffix`. **Не `import *`**: тестовые классы модуля собрались бы второй раз. Нового общего модуля хелперов не заводить (правило 42.4). Свои хелперы:
    - `make_master(client, *, status="pending", subs=2, **overrides)` — мастер `Order.objects.create(user=client, is_master=True, …)` с явным каноническим `order_number` (10 цифр: `customer_code` клиента или 5 случайных цифр + `"26"` + 3 цифры; без явного номера `Order.save` ставит UUID, и поиск по UI-номеру не проверить), субзаказы `is_master=False, parent_order=master, user=client, suborder_sequence=i, vat_group=…` и по позиции `OrderItem` в каждом (`ProductFactory` из `tests.factories`, как в `tests/unit/test_orders_admin.py:180`);
    - URL-хелперы `order_change_url`, `order_history_url`, `ORDERS_URL = "/manager/orders/order/"`;
    - `post_order_action(client, action, *orders, **extra)` по образцу `post_action`.
  - [x] Сценарии:
    - AC1 — матрица входа по `/manager/orders/order/` (как `TestEntry` 42.4) и блок «Заказы» в `response.context["app_list"]` главной.
    - AC2 — параметризация группами «Менеджеры» и «Руководители» (фикстура `section_member` из 42.4 — импортировать или повторить). Набор id в `response.context["cl"].result_list` = мастер-заказы своих клиентов. Заказы сотрудников с `responsible_manager=A` — через `User.objects.filter(pk=…).update(responsible_manager=A)`, по одной записи на каждое условие `staff_accounts_q()`. Заказ `user=None`. Поиск по шести значениям заказа B — пусто, по своим — находится. Заголовки колонок — русские (`label_for_field` или HTML `<th>`).
    - AC3 — GET/POST карточки и `history` заказа B → 404, карточка своего субзаказа → 404; `add` и `delete` своего → 403; после POST заказ B без изменений, `AuditLog` пуст.
    - AC4 — `response.context["adminform"].form.fields` = ровно `{tracking_number, delivery_date}`; текст `notes` заказа виден в HTML, а `name="notes"` нет; readonly-поля по fieldsets; для каждого скрытого поля нет `name="<поле>"` и подписи `verbose_name` в HTML; ссылка клиента `href="/manager/users/user/<id>/change/"`; в «Составе» есть артикулы позиций обоих субзаказов; блок субзаказов без `href` на `/manager/orders/order/<sub_id>/`; нет `addlink`/`deletelink`.
    - AC5 — `BonusProgramSettings.load()` с `is_active=True`, `accrual_status="delivered"`, `program_start_at=None`; клиент `role="trainer"`, `is_verified=True`; POST с подделками. Проверка `update_fields` — `patch.object(Order, "save", autospec=True, side_effect=Order.save)` и разбор `call_args.kwargs["update_fields"]`. Второй сценарий AC5: заказ переведён в `delivered` через `Order.objects.filter(pk=…).update(status="delivered")` (сигнал не срабатывает, бонуса нет), две правки трек-номера подряд → `BonusTransaction.objects.filter(…).count() == 1`.
    - AC6 — разобрать CSV (`csv.reader(response.content.decode("utf-8-sig").splitlines())`): номера только своих заказов; отдельно `response.content.startswith(b"\xef\xbb\xbf")` и первая строка = `MANAGER_CSV_HEADER`; `select_across=1` с пустым `_selected_action` — Django требует непустой `_selected_action` в POST даже при `select_across`, передать любой свой id. В контексте списка `response.context["action_form"].fields["action"].choices` — только наше действие с русской подписью.
    - AC7 — правка одного поля, обоих полей, без изменений (`updated_at` прежний, записей нет). Значения `old`/`new`, дата строкой ISO.
    - AC8 — заявки через `make_client(A, verification_status="pending", is_verified=False, is_active=False, role="wholesale_level1")`, `created_at` — `User.objects.filter(pk=…).update(created_at=timezone.now() - timedelta(days=5, hours=1))`. Текст счётчиков в HTML; переход по каждой ссылке, `cl.result_count` = значение счётчика, id — только записи A. Отдельно — `days_ru` параметризованно (unit), «0» без «старейшая», «старейшая — сегодня» и граница суток (`patch("django.utils.timezone.now")` — `freezegun` в `requirements.txt` нет, новую зависимость не заводить; `localdate()`/`localtime()` берут время из `now()`: заявка вчера в 23:50 по `Europe/Moscow` (`TIME_ZONE`, `base.py:282`), сейчас 00:10 → «1 день»).
    - AC9 — `group.permissions.set([view_order, view_user])`: в форме нет полей ввода, POST → 403, экспорт работает.
    - AC10 — `'href="/admin/' not in html` для главной (после POST заказа — есть `LogEntry`), списка, карточки, истории; `response.url` после `_save` и `_continue`.
    - AC11 — `CaptureQueriesContext` / `django_assert_num_queries`: 5 мастер-заказов → baseline, ещё 45 → тот же счёт (образец — `TestChangelistQueryCount` 42.4). Главная — 3 и 30 заявок/заказов.
  - [x] `backend/tests/unit/test_manager_orders_admin.py` (unit, `RequestFactory`): `scope_orders` (свой мастер, свой субзаказ, чужой, без клиента, заказ сотрудника); `days_ru`; `manager_queue` на пустых данных (0 и без «старейшая»); `ManagerOrderAdmin.get_readonly_fields`/`get_fieldsets` не содержат скрытых полей (страж белого списка); регистрация: `manager_site._registry[Order]` — экземпляр `ManagerOrderAdmin`, а `admin.site._registry[Order]` — по-прежнему `OrderAdmin`.
  - [x] **Тесты транзакционные** (как в 42.4): autouse `clear_db_before_test(transactional_db)` в `tests/conftest.py`, после теста `flush`; правки прав группы внутри теста не откатываются, их стирает `flush`, а `role_groups` следующего теста создаёт группы заново. `ATOMIC_REQUESTS=True` только в тестовых настройках.
  - [x] **Проверка мутациями** — по каждой защите временно убрать её, убедиться, что падает названный тест, вернуть. Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | `is_master=True` в `scope_orders` | AC2 (субзаказы в списке), AC3 (карточка субзаказа) |
    | `user__in=scope_clients(...)` → `user__responsible_manager=request.user` | AC2, записи сотрудников |
    | `_get_obj_does_not_exist_redirect` → `Http404` | AC3 |
    | `update_fields` в `save_model` → `super().save_model(...)` | AC5, проверка `update_fields` |
    | `"status"` добавлен в правимые поля (из `readonly_fields` убран) и в `EDITABLE_FIELDS` | AC5, статус и бонус |
    | `"notes"` убран из `readonly_fields` и добавлен в `EDITABLE_FIELDS` | AC4 (`name="notes"` в HTML), AC5 (`notes` прежний) |
    | `response.write("﻿")` в `export_orders_csv` | AC6, BOM |
    | в сигнале бонусов ранний `return` при непустом `update_fields` | AC5, второй сценарий (бонус после правки трека) |
    | возраст заявки через `(timezone.now() - oldest).days` | AC8, граница суток |
    | ранний `return` при пустом `changed` | AC7, сохранение без изменений |
    | `exclude(role=ROLE_UNREGISTERED)` в счётчике заявок | AC8, равенство счётчика и списка (добавить в данные `unregistered` с `pending`) |
    | `index_template`/`block sidebar` в шаблоне | AC10, главная после правки |

- [x] **Task 4 — существующие тесты: без правок**
  - [x] Прогнать и убедиться, что зелёные без изменений: `tests/unit/test_orders_admin.py` (`/admin/` не тронут), `tests/integration/test_manager_clients_section.py` (главная теперь с блоком очереди: `TestLinksStayInSection`, `test_index_names_block_clients`), `tests/unit/test_manager_admin_site.py`, `apps/bonuses/tests/test_admin.py`, тесты импорта статусов (`tests/integration/test_order_status_import_db.py`).
  - [x] Если `test_manager_admin_site.py` проверяет число запросов главной или её контекст — счётчики добавят ровно два запроса; правка ожиданий — только с записью в Completion Notes как отклонение.

- [x] **Task 5 — проверки и закрытие**
  - [x] Полный backend-прогон в Docker, один compose-проект: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` (~16 мин, ориентир после 42.4 — 4201 passed, 76 skipped). Запускать в фоне.
  - [x] Линтеры строго после зачётного pytest, в том же `-p freesport-test` (проект `freesport-lint` не поднимается при живом `freesport-test`): `black --check .`, `isort --check-only .`, `flake8`, `mypy`. Любая ошибка — новая.
  - [x] `makemigrations --check --dry-run` — миграций нет. `check_openapi_sync` не нужен: API не меняется.
  - [x] Nginx не меняется (`/manager/` проксируется с 42.4). Smoke `scripts/deploy/check-manager-*.sh` не меняются.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [x] Completion Notes: отклонения от стори с причиной, ответы Alex на вопросы ниже (если получены до разработки).

### Review Findings

Ревью 15.10.2026: `d53f42a6...8b7ad6a2`, режим `full`, четыре независимых слоя через плагин Codex 1.0.4. Все слои завершились. После проверки 19 исходных замечаний: 1 решение, 6 исправлений, 3 отложенных вопроса, 4 отклонённых замечания. Повторяющиеся замечания объединены только после индивидуальной оценки.

#### Решение владельца

Alex выбрал вариант 1: отклонять устаревшую карточку и просить обновить страницу, без сохранения её изменений. R42.5-1 переведено в исправления; итого 7 исправлений, нерешённых вопросов о политике конфликта нет.

По итогам ревью Alex выбрал оставить все 7 исправлений открытыми задачами, без изменения кода. Статус истории возвращён в `in-progress`; 3 отложенных пункта сохранены в `deferred-work.md`.

#### Исправления

- [x] [Review][Patch] **R42.5-1, medium: вторая открытая карточка молча теряет правку первой** [`backend/apps/orders/manager_admin.py:322-325`]. Две формы читают трек `OLD`; первая сохраняет `NEW`, вторая меняет только дату, но отправляет старый трек. Django сравнивает POST с текущим объектом при обработке второго запроса, поэтому `changed_data` включает и трек, и дату; `update_fields` возвращает трек к `OLD`. Воспроизведено двумя последовательными настоящими POST в Docker + PostgreSQL. **Решение Alex: отклонять устаревшую форму с просьбой обновить страницу; изменения такого POST не сохранять.** Добавить регрессионную проверку двух открытых карточек и отсутствия изменений заказа/журнала при отклонении. Источники: blind-hunter №6, edge-case-hunter №1; оба вердикта `medium`.
- [x] [Review][Patch] **R42.5-2, high: клиентское имя попадает в CSV как Excel-формула** [`backend/apps/orders/manager_admin.py:302-308`]. `customer_display_name` содержит свободно задаваемые имя и фамилию. Для имени `=1+1` экспорт отдаёт ячейку `=1+1` без нейтрализации; `csv.writer` лишь экранирует CSV, а целевой потребитель по решению 8 - Excel. Воспроизведено получение такой ячейки настоящим запросом экспорта. Нейтрализовать формульные текстовые ячейки, в том числе опасные префиксы после пробельных/управляющих символов, и добавить независимые проверки. Источники: blind-hunter №1, edge-case-hunter №3; оба вердикта `high`. Сам Excel не запускался.
- [x] [Review][Patch] **R42.5-3, medium: очередь главной игнорирует модельные права** [`backend/apps/orders/manager_admin.py:76-113`; `backend/freesport/admin_site.py:75`]. После удаления `view_order` и `change_order` у группы менеджер получает 403 на список заказов, но главная по-прежнему показывает количество заказов и ссылку на запрещённый список. Воспроизведено HTTP-запросами; счётчик заявок аналогично не проверяет права `User`. Формировать каждый элемент очереди только при `has_view_or_change_permission` соответствующего зарегистрированного admin-класса; проверить права по моделям раздельно и сохранить доступ при одном `view`. Источники: blind-hunter №5, edge-case-hunter №4; оба вердикта `medium`.
- [x] [Review][Patch] **R42.5-4, medium: дата CSV не совпадает с московской датой карточки** [`backend/apps/orders/manager_admin.py:312`]. `USE_TZ=True`, `TIME_ZONE=Europe/Moscow`, но `strftime` вызывается на UTC-значении из БД. Заказ от `2026-10-14 22:30 UTC` экспортируется как `2026-10-14 22:30`, хотя локально это `2026-10-15 01:30`. Воспроизведено экспортом. Использовать `timezone.localtime` и независимое ожидаемое значение теста. Источник: blind-hunter №3, вердикт `medium`. Аналогичное старое поведение `/admin/` не исправлять в рамках этой задачи.
- [x] [Review][Patch] **R42.5-5, medium: тесты даты доставки проверяют журнал, но не сохранённый заказ** [`backend/tests/integration/test_manager_orders_section.py:586-609`]. После изменения и очистки даты добавить `refresh_from_db()` и проверку `delivery_date`. Исключение даты только из `update_fields` оставит журнал правильным по объекту в памяти и не будет обнаружено текущими проверками. Источник: verification-gap №1, вердикт `medium`; доказательства слоя приняты.
- [x] [Review][Patch] **R42.5-6, low: числовые значения состава карточки не защищены тестом** [`backend/tests/integration/test_manager_orders_section.py:382-395`]. Проверки наличия артикулов не обнаружат замену суммы позиции ценой одной единицы в `items_table`. Проверить количество, цену и сумму по каждой строке с различающимися данными. Источник: verification-gap №2, вердикт `low`; доказательства слоя приняты.
- [x] [Review][Patch] **R42.5-7, low: проверка заголовков CSV использует константу реализации как эталон** [`backend/tests/integration/test_manager_orders_section.py:516-531`]. Изменение русских подписей или порядка в `MANAGER_CSV_HEADER` оставит проверку зелёной. Проверять литеральный список восьми заголовков из решения 8, независимо от импортированной константы. Источник: blind-hunter №9, вердикт `low`.

#### Отложено

- [x] [Review][Defer] **R42.5-D1: сохранность ведущих нулей номера при открытии CSV в Excel** [`backend/apps/orders/manager_admin.py:305`]. Вердикт `maybe-false`, потенциальный `medium`: CSV содержит правильный текст номера, но Excel может автоматически преобразовать `0000026001` в число. В этом прогоне Excel не запускался; для решения открыть итоговый файл двойным кликом в целевой версии Excel и проверить оба номера. Не использовать формулу `="..."` без отдельного рассмотрения безопасности CSV. Источник: blind-hunter №2.
- [x] [Review][Defer] **R42.5-D2: общий бонусный сервис проверяет устаревающие снимки заказа и клиента** [`backend/apps/bonuses/services/accrual.py:139-177`; `backend/apps/orders/manager_admin.py:325`]. Вердикт `medium`: между чтением заказа и сохранением трека другой запрос может отменить доставку либо снять верификацию; `is_eligible` использует прежний `order.status` и закэшированного `order.user`, а `update_fields` не обновляет объект в памяти. Эта логика уже есть в baseline и вызывается также из `/admin/`; новый раздел её не меняет. Последовательный тест идемпотентности не проверяет такое расписание. Отдельно согласовать актуальность/блокировки в общем сервисе и закрепить двумя соединениями. Реальная конкурентная бонусная операция в этом прогоне не воспроизводилась. Источники: blind-hunter №7 и edge-case-hunter №2; индивидуальные вердикты `medium`.
- [x] [Review][Defer] **R42.5-D3: полного зелёного прогона AC12 пока нет** [`_bmad-output/implementation-artifacts/Story/42-5-manager-section-orders-and-home.md`, Debug Log References]. Вердикт `medium`: отчёт реализации содержит 17 ошибок CRLF в существующих shell-тестах и старую ошибку isort, а не успешный итоговый полный прогон. Это ранее существовавшие проблемы окружения/файлов вне diff; не маскировать их правками новых тестов. Для закрытия получить зелёный полный прогон на LF-окружении и результат isort либо явное решение владельца о гейте. В этом ревью выполнен только целевой прогон, он не заменяет полный. Источники: blind-hunter №10, acceptance-auditor №2; оба вердикта `medium`.

#### Проверки ревью

- GitNexus: индекс актуален на `8b7ad6a2`; `detect-changes --scope all` пуст на чистом дереве, `--scope compare --base-ref d53f42a6` показывает 12 файлов, 71 символ, 3 процесса, риск `medium`. `impact scope_orders`: 2 прямых вызывающих, 1 процесс, `LOW`; `impact manager_queue`: 1 прямой вызывающий, `LOW`.
- Docker + PostgreSQL: **93 passed**, 6 предупреждений, 137.77 с. Файлы: `test_manager_orders_section.py`, `test_manager_orders_admin.py`, `test_orders_admin.py`, `test_manager_admin_site.py` и 5 временных воспроизведений.
- Временные проверки подтверждают именно наличие текущего поведения: потерю трека из второй вкладки, формульную ячейку CSV, счётчик при отозванных правах, UTC-дату и штатный отказ действия при пустом выборе. Это не тесты исправленного поведения; файл находится в системном temp, не добавляется в репозиторий.
- Первый запуск двух pytest-процессов ошибочно использовал одну тестовую БД и получил конфликт миграций. Его результаты не учитываются; зачётный повторный прогон выполнен одним процессом. Dev- и production-базы не затрагивались. Код приложения и штатные тесты при ревью не менялись.

#### Отклонённые замечания

- blind-hunter №4, `low`: экспорт материализует выборку и ненужные prefetch, но исчерпание памяти на достижимом рабочем объёме не показано; потоковый ответ и чанки добавляют сложность ради неподтверждённого риска, не задача этого ревью.
- blind-hunter №8, `low`: поддельный inline POST отдельно не проверен, но все поля readonly и штатные `has_add/change/delete_permission=False` исключают записи из формы; отдельного незащищённого пути изменения не показано. Низкоприоритетное расширение проверки Django, не исправление дефекта.
- edge-case-hunter №5, `false` для штатного маршрута: nginx `/manager/` перезаписывает `X-Real-IP` значением `$remote_addr`, а `get_client_ip` отдаёт ему приоритет; адрес с портом из произвольного заголовка не доходит до AuditLog через этот маршрут. Защита иных схем прямого доступа к backend здесь не доказана необходимой.
- acceptance-auditor №1, `medium` для буквального AC6, отклонено как противоречие спецификации: пустой `_selected_action` действительно возвращает HTML вместо CSV (воспроизведено), но Task 3 явно требует штатную проверку Django и передачу своего id при `select_across=1`. Заданный реализационный контракт соблюдён; исправление формулировки самой спецификации не включается в замечания к коду.

### Review Findings (повторный прогон 15.10.2026)

Диапазон `d53f42a6..8c356c14`, режим `full`, плагин Codex 1.0.4. Четыре слоя завершились без ошибок: `blind-hunter`, `edge-case-hunter`, `verification-gap`, `acceptance-auditor`. Получено 18 исходных замечаний. Каждое оценено отдельно до объединения: итог — 0 решений владельца, 4 исправления, 2 повтора отложенных вопросов, 9 отклонённых исходных замечаний. Код приложения при ревью не менялся.

Решение Alex: вариант 2 — оставить R42.5-8…11 открытыми задачами в истории, без исправления кода. Статус истории и sprint-status синхронизированы в `in-progress`.

#### Исправления повторного прогона

- [x] [Review][Patch] **R42.5-8, medium: пробелы в сохранённом треке блокируют свежую карточку** [`backend/apps/orders/manager_admin.py:204`]. В `CharField.has_changed(current[name], seen)` Django нормализует присланную строку, но не исходное значение БД. При `tracking_number="TRK "` или `" TRK"` форма, только что открытая менеджером, отклоняет изменение даты с сообщением об устаревшей карточке; обновление страницы не помогает. `Order.save()` пробелы не удаляет. Воспроизведено настоящими GET/POST в Docker + PostgreSQL для обоих вариантов: ответ 200 с ошибкой, дата остаётся `None`, `AuditLog` пуст. Согласовать нормализацию обеих сторон сравнения, сохранив отказ при реальном конфликте; добавить регрессионные проверки. Источники: ID 1 и 12, `blind-hunter+edge-case-hunter`, оба `medium`.
- [x] [Review][Patch] **R42.5-9, medium: нет проверки конфликта после изменения только даты доставки** [`backend/tests/integration/test_manager_orders_section.py:482-517`]. Оба сценария отказа устаревшей форме меняют трек в первой вкладке. Удаление проверки `delivery_date` из `clean()` оставит их зелёными, но позволит второй вкладке вернуть старую дату. Параметризовать сценарий полем первой правки, включить изменение и очистку даты, проверять итоговый заказ и отсутствие лишних записей обоих журналов. Источник: ID 15, `verification-gap`; доказательства слоя приняты без повторной верификации.
- [x] [Review][Patch] **R42.5-10, medium: SQL-страж не проверяет порядок чтения и блокировки** [`backend/tests/integration/test_manager_orders_section.py:520-528`]. Тест ищет `FOR UPDATE` в одном POST, остальные отправляют формы последовательно. Мутация «прочитать и сравнить без блокировки, захватить блокировку после сравнения» проходит такие проверки, но позволяет двум одновременным POST принять один исходный снимок. Добавить управляемый сценарий двух независимых PostgreSQL-соединений: второй POST ждёт первый, затем видит его правку и отклоняется; сохранение и журналы соответствуют одному успешному запросу. Источники: ID 4 и 16, `blind-hunter+verification-gap`, оба `medium`; это пробел проверки, не утверждение о дефекте текущего порядка блокировок.
- [x] [Review][Patch] **R42.5-11, low: CSV-хелпер тестов теряет переводы строк внутри ячейки** [`backend/tests/integration/test_manager_orders_section.py:190-191`]. `csv.reader(decoded.splitlines())` превращает корректное кавыченное `first\nsecond` в `firstsecond`. Подтверждено отдельным воспроизведением; экспорт приложения при этом не повреждён. Читать через `StringIO(decoded)` и закрепить многострочную ячейку клиента, чтобы тест проверял исходное значение без потерь. Исправление прямое, без нового поведения приложения. Источник: ID 5, `blind-hunter`, `low`.

#### Повторы отложенных вопросов

- [x] [Review][Defer] **Повтор R42.5-D2, medium: устаревшая верификация при бонусном начислении** [`backend/apps/bonuses/services/accrual.py:139-177`; `backend/apps/orders/manager_admin.py:410`]. ID 13, `edge-case-hunter`. `post_save` передаёт объект с закэшированным клиентом, а `is_eligible()` не перечитывает верификацию; параллельное снятие верификации после чтения не учитывается. Общий сервис в baseline `d53f42a6` тот же. Deferred: задача уже существует, нового самостоятельного дубля нет; согласовать актуальность и блокировки в общем сервисе и проверить двумя соединениями. Конкурентное начисление в этом прогоне не выполнялось.
- [x] [Review][Defer] **Повтор R42.5-D3, medium: полный зелёный AC12 не подтверждён** [`_bmad-output/implementation-artifacts/Story/42-5-manager-section-orders-and-home.md`, Debug Log References]. ID 8 и 18, `blind-hunter+acceptance-auditor`, оба `medium`. Последний записанный полный результат — `4278 passed, 76 skipped, 17 failed`, isort сообщает четыре файла вне diff; после него были изменения и только целевые проверки. Deferred: причины вне кода стори, исходная задача сохраняется; получить полный зелёный прогон итоговой ревизии в LF-окружении и isort либо явное исключение владельца. Повтор двух файлов и текущие целевые тесты полного гейта не заменяют.

#### Индивидуальная оценка до объединения

| ID | Источник | Вердикт | Проверенное основание и маршрут |
|---|---|---|---|
| 1 | blind-hunter №1 | medium | Свежие GET/POST с `TRK ` и ` TRK` отклоняются; R42.5-8. |
| 2 | blind-hunter №2 | low | Повторный `.get()` не обрабатывает удаление заказа между чтениями; отклонено как редкая гонка, см. приложение. |
| 3 | blind-hunter №3 | low | При одном `orders.view_order` ссылка клиента есть, её GET даёт 403; отклонено как малозначимое улучшение нестандартной конфигурации прав. |
| 4 | blind-hunter №4 | medium | Последовательные POST и наличие SQL-блокировки не проверяют два конкурирующих соединения; R42.5-10. |
| 5 | blind-hunter №5 | low | CSV с переводом строки читается хелпером с потерей символа; R42.5-11. |
| 6 | blind-hunter №6 | false | No-op действительно создаёт штатный `LogEntry`, но решение 7 явно отделяет его от `AuditLog`; AC7 и проверка относятся к `AuditLog`, который пуст. |
| 7 | blind-hunter №7 | medium | Буквальный AC6 про пустой выбор противоречит Task 3, требующему свой id; отклонено как изменение самой спецификации. |
| 8 | blind-hunter №8 | medium | Полного зелёного результата итоговой ревизии в отчёте нет; повтор R42.5-D3. |
| 9 | blind-hunter №9 | low | Решения 6, 7 и 11 описывают старые варианты; позднейшие отклонения задокументированы в Completion Notes. Отклонено: исправление самой спецификации. |
| 10 | blind-hunter №10 | low | File List не включает все документы диапазона baseline..HEAD; отклонено: исправление самой спецификации. |
| 11 | edge-case-hunter №1 | low | `.get()` после первоначального чтения допускает `DoesNotExist` при конкурентном удалении; та же оценка, что ID 2, отклонено до объединения. |
| 12 | edge-case-hunter №2 | medium | Асимметричная нормализация трека подтверждена HTTP-воспроизведением; R42.5-8. |
| 13 | edge-case-hunter №3 | medium | `is_eligible` читает закэшированного клиента, общий код неизменён относительно baseline; повтор R42.5-D2. |
| 14 | edge-case-hunter №4 | low | HTTP подтвердил ссылку клиента с ответом 403 при отозванных правах; отклонено по той же причине, что ID 3. |
| 15 | verification-gap №1 | medium | Принятые доказательства слоя: пропуск проверки даты не обнаруживается сценариями конфликта трека; R42.5-9. |
| 16 | verification-gap №2 | medium | Принятые доказательства слоя: перенос блокировки после сравнения не обнаруживается текущим SQL-стражем; R42.5-10. |
| 17 | acceptance-auditor №1 | medium | AC6 и Task 3 задают разные условия пустого выбора; отклонено как исправление спецификации, а не реализации согласованного Task 3. |
| 18 | acceptance-auditor №2 | medium | Полный прогон содержит 17 падений, isort не зелёный; причины уже отложены, повтор R42.5-D3. |

#### Проверки повторного прогона

- GitNexus: индекс свежий на `8c356c1`; `detect-changes --scope all` — без изменений, `--scope compare --base-ref d53f42a6` — 13 файлов, 91 символ, 3 процесса, риск `medium`. `impact ManagerOrderForm`: 2 прямые связи импорта, риск `LOW`; `impact manager_queue`: 1 вызывающий (`ManagerAdminSite.index`), риск `LOW`.
- Docker + PostgreSQL: оба штатных модуля `test_manager_orders_section.py` и `test_manager_orders_admin.py` прошли. Совместный запуск с временными воспроизведениями — **98 passed, 1 failed**: единственное падение вызвано ошибкой временной проверки (передан `view_order` вместо `orders.view_order`), а не кодом проекта. После исправления временного сценария отдельный повтор — **5 passed**, 6 предупреждений.
- Временные сценарии подтверждают наличие наблюдаемого поведения, а не исправленную реализацию: отказ свежей форме с пробелами (2 варианта), ссылку клиента с 403, отдельный штатный `LogEntry` при no-op и потерю перевода строки CSV-хелпером. Файл хранится в системном temp; пустой host-файл, созданный Docker для точки монтирования, удалён после прогона. Dev- и production-базы не затрагивались; реальная конкурентная операция с двумя соединениями не выполнялась.
- Полный backend-прогон, линтеры и Excel в этом повторном ревью не запускались.

#### Отклонённые замечания повторного прогона

- ID 2, blind-hunter №2, `low`: конкурентное удаление между двумя чтениями может дать 500, но повседневный сценарий не показан; обработчик исключения добавляет ветку ради редкой гонки. Не относится к гарантированным AC3 запросам уже отсутствующего или чужого заказа.
- ID 3, blind-hunter №3, `low`: ссылка на клиента с 403 подтверждена, но данные не раскрываются, заказ доступен; дефект ожидается только после нестандартного отзыва прав на клиентов. Передача контекста запроса и условная форма ссылки добавляют сложность ради малозначимого улучшения.
- ID 6, blind-hunter №6, `false`: решение 7 явно оставляет `LogEntry` штатным отдельным журналом; no-op не меняет заказ и не пишет `AuditLog`, что подтверждено HTTP-проверкой. Требование подавить штатный `LogEntry` не установлено.
- ID 7, blind-hunter №7, `medium`: Task 3 прямо предписывает непустой id при `select_across=1`; исправление противоречащего ему AC6 меняет саму спецификацию и исключено правилами triage.
- ID 9, blind-hunter №9, `low`: актуализация исходных решений полезна редакционно, но меняет саму спецификацию; позднейшие изменения уже перечислены в Completion Notes.
- ID 10, blind-hunter №10, `low`: дополнение File List документами диапазона меняет саму спецификацию и исключено из исправлений этого ревью.
- ID 11, edge-case-hunter №1, `low`: та же редкая гонка удаления; добавление новой ветки ради неё не оправдано показанным повседневным использованием.
- ID 14, edge-case-hunter №4, `low`: тот же подтверждённый 403 по ссылке в нестандартной конфигурации; контроль доступа исправен, усложнение display-метода не включено в задачи.
- ID 17, acceptance-auditor №1, `medium`: тот же конфликт AC6 с явным Task 3; заданное Task 3 штатное действие Django соблюдено, правка спецификации исключена.

### Review Findings (третий прогон 15.10.2026, HEAD 46125f94)

Диапазон `d53f42a6..46125f94`, режим `full`, плагин Codex 1.0.4. Все четыре слоя завершились: `blind-hunter`, `edge-case-hunter`, `verification-gap`, `acceptance-auditor`. Получено 17 исходных замечаний; каждое оценено до объединения. Итог: 0 решений владельца, 3 исправления, 3 повтора отложенных вопросов, 6 отклонённых исходных замечаний. Код приложения и штатные тесты при ревью не менялись.

Решение Alex: вариант 2 — оставить R42.5-12…14 открытыми задачами в стори, без исправления кода. Статус стори и sprint-status синхронизированы в `in-progress`.

#### Новые задачи

- [x] [Review][Patch] **R42.5-12, medium: конкурентное удаление заказа приводит к 500** [`backend/apps/orders/manager_admin.py:200`]. После первоначального `get_object()` Django вызывает `ManagerOrderForm.clean()`, где повторное чтение через `.select_for_update().values(...).get()` не перехватывает `Order.DoesNotExist`. Суперпользователь может удалить заказ через основную админку между этими чтениями; первоначальное чтение строки не блокирует. Повторный запрос не найдёт строку, и исключение выйдет из валидации как 500 вместо контролируемого 404. Обработать исчезнувший заказ и закрепить HTTP-проверкой удаления между чтениями. Вывод по коду и штатному пути удаления; конкурентное удаление в этом прогоне не выполнялось. Источники: ID 1 и 11, `blind-hunter+edge-case-hunter`, оба `medium`.
- [x] [Review][Patch] **R42.5-13, medium: конкурентный тест не завершает потоки при ошибке ожидания** [`backend/tests/integration/test_manager_orders_section.py:626-639`]. После `first.start()` нет `try/finally`: отказ `first_saved.wait()` либо исключение запроса к `pg_stat_activity` обходит `release.set()` и оба `join()`. Дочерний запрос может продолжаться во время очистки тестовой БД, вызывая вторичные ошибки следующих тестов; ограничение `release.wait(timeout=15)` не гарантирует завершения к началу очистки. Гарантированно освобождать ожидание и завершать запущенные потоки при любом выходе; проверять завершение и передавать исключения работников в основной поток. Источники: ID 4 и 14, `blind-hunter+edge-case-hunter`, оба `medium`.
- [x] [Review][Patch] **R42.5-14, medium: нет проверки отсутствия бонусного начисления при неизменённой карточке** [`backend/tests/integration/test_manager_orders_section.py:875-883`]. `test_save_without_changes_writes_nothing` использует обычного оптовика с заказом `pending`; он проверяет снимок заказа и `AuditLog`, но не отсутствие `save()`/побочного эффекта `post_save`. Мутация перед `return` в `if not changed`: `obj.save(update_fields=["tracking_number", "delivery_date"])` оставляет снимок и журнал прежними, но для верифицированного тренера с `delivered` может создать бонус. Добавить неизменённый POST подходящего для начисления заказа с проверкой отсутствия `BonusTransaction` либо прямой страж отсутствия сохранения; существующий тест реальной правки трека сохранить. Это пробел регрессионной проверки, а не утверждение о текущем лишнем начислении; мутация в этом ревью не запускалась. Источники: ID 5 и 15, `blind-hunter+verification-gap`, оба `medium`; доказательства слоя `verification-gap` приняты по правилам workflow.

#### Повторы отложенных вопросов

- [x] [Review][Defer] **Повтор R42.5-D1, maybe-false, потенциальный medium: открытие CSV в целевом Excel** [`backend/apps/orders/manager_admin.py:386-400`]. ID 7, `blind-hunter`. Сохранность ведущих нулей уже отложена; разделение восьми колонок при двойном клике зависит от локали Excel и также не проверялось. CSV корректен для Python, но это не доказательство поведения Excel. Deferred: проверить конечный файл в целевой версии и локали Excel; самостоятельный дубль задачи не создавать.
- [x] [Review][Defer] **Повтор R42.5-D2, medium: бонусный сигнал использует ранее загруженные статус и клиента** [`backend/apps/orders/manager_admin.py:413`; `backend/apps/bonuses/services/accrual.py:142-177`]. ID 3 и 12, `blind-hunter+edge-case-hunter`, оба `medium`. Блокирующее чтение обновляет только два правимых поля, но не экземпляр `obj` и закэшированного клиента для `is_eligible()`. Deferred: общий сервис существовал до baseline; остаётся прежняя задача актуальности данных и порядка блокировок. Реальное конкурентное начисление в этом прогоне не выполнялось.
- [x] [Review][Defer] **Повтор R42.5-D3, medium: итоговый полный зелёный AC12 не подтверждён** [Debug Log References этой стори]. ID 9 и 17, `blind-hunter+acceptance-auditor`, оба `medium`. Последний записанный полный прогон: `4287 passed, 76 skipped, 17 failed`; ошибки `isort` также записаны для файлов вне diff. Целевые проверки не подтверждают весь гейт. Deferred: исходная задача полного зелёного прогона и линтеров в LF-окружении либо явного исключения владельца остаётся; новой самостоятельной задачи нет.

#### Индивидуальная оценка до объединения

| ID | Источник | Вердикт | Доказательство и маршрут |
|---|---|---|---|
| 1 | blind-hunter | medium | Необработанный `.get()` после неблокирующего чтения; удаление разрешено суперпользователю в основной админке. R42.5-12. |
| 2 | blind-hunter | low | При отозванных правах `User` ссылка действительно даёт 403, данные не раскрываются. Отклонено как редкая нестандартная конфигурация, требующая новой ветки отображения. |
| 3 | blind-hunter | medium | `save()` передаёт сигналу прежний объект; блокировка двух полей не освежает статус/клиента. Повтор D2. |
| 4 | blind-hunter | medium | Исключение до `release.set()` обходит завершение запущенных потоков. R42.5-13. |
| 5 | blind-hunter | medium | Снимок и пустой `AuditLog` не отличают лишний `save()` без `updated_at`; бонусная фикстура здесь отсутствует. R42.5-14. |
| 6 | blind-hunter | low | Отдельного сценария поиска/фильтра при `select_across` нет, но код не подменяет переданный Django queryset. Отклонено как расширение проверки неизменённого механизма Django без обнаруженного дефекта. |
| 7 | blind-hunter | maybe-false | Целевая версия Excel не запускалась; нужны её версия, локаль и открытие файла. Повтор D1, потенциальный medium. |
| 8 | blind-hunter | medium | AC6 противоречит Task 3, который явно предписывает выбранный id и штатную проверку Django. Отклонено: исправление требует правки проверяемой спецификации. |
| 9 | blind-hunter | medium | В отчёте 17 ошибок полного набора и ошибки isort; целевой повтор не заменяет полный. Повтор D3. |
| 10 | blind-hunter | low | Старые решения расходятся с реализацией, но отклонения по блокировке, журналу и аргументу `site` уже записаны в Completion Notes. Отклонено: предложение меняет проверяемую спецификацию. |
| 11 | edge-case-hunter | medium | Тот же достижимый путь исчезновения строки между двумя чтениями. R42.5-12. |
| 12 | edge-case-hunter | medium | `is_eligible()` читает `order.user`, загруженного до снятия верификации. Повтор D2. |
| 13 | edge-case-hunter | low | Тот же 403 по ссылке при отдельно отозванных правах клиентов; защита назначения работает. Отклонено по тем же причинам, что ID 2. |
| 14 | edge-case-hunter | medium | Нет гарантированного освобождения ожидания и join при исключении в основном потоке. R42.5-13. |
| 15 | verification-gap | medium | Принято доказательство слоя: неизменённый POST подходящего для бонуса заказа не проверяется; указанная мутация не меняет проверяемый снимок. R42.5-14. |
| 16 | acceptance-auditor | medium | Буквальное AC6 конфликтует с Task 3; непустой выбор в тесте соответствует явному заданию. Отклонено как правка спецификации, не кода. |
| 17 | acceptance-auditor | medium | Нет полного зелёного результата финальной ревизии. Повтор D3. |

#### Проверки третьего прогона

- Docker + PostgreSQL, оба штатных модуля стори: **103 passed**, 6 предупреждений, 218.00 с. Команда из `docker/`: `docker compose -p freesport-test -f docker-compose.test.yml run --rm --no-deps -T backend pytest tests/integration/test_manager_orders_section.py tests/unit/test_manager_orders_admin.py -q -p no:sugar --tb=short`.
- Полный backend-набор, линтеры, Excel, мутации и дополнительные конкурентные воспроизведения в этом ревью не запускались. Зелёные штатные тесты не опровергают новые замечания о непокрытых путях.
- GitNexus: индекс устарел (`8c356c1`, HEAD `46125f9`), предложено выполнить `! npx gitnexus analyze --skip-agents-md`. `detect-changes --scope all` на чистом дереве не обнаружил изменений. По имеющемуся индексу `impact scope_orders`: 2 прямых вызывающих, 1 процесс, LOW; `impact manager_queue`: 1 прямой вызывающий, LOW. Ограничение свежести сообщено до запуска ревью.

#### Отклонённые замечания третьего прогона

- ID 2 (`blind-hunter`), low: 403 вместо доступной карточки клиента возникает при нестандартном отзыве прав; утечки нет, новая условная ветка отображения не оправдана повседневным сценарием.
- ID 6 (`blind-hunter`), low: дополнительный тест фильтра при массовом действии расширяет проверку неизменённого Django; собственный экспорт уже получает ограниченный queryset, самостоятельный дефект не найден.
- ID 8 (`blind-hunter`), medium: конфликт AC6/Task 3 уже известен; исправление формулировки проверяемой спецификации исключено из задач ревью.
- ID 10 (`blind-hunter`), low: согласовать старый текст решений с уже записанными отклонениями означает редактировать проверяемую спецификацию.
- ID 13 (`edge-case-hunter`), low: тот же защищённый 403 в редкой конфигурации прав, что ID 2; дополнительную ветку отображения не добавляем.
- ID 16 (`acceptance-auditor`), medium: тот же конфликт AC6/Task 3; заданный реализационный контракт соблюдён.

### Review Findings (четвёртый прогон 15.10.2026, HEAD 141aff23)

Диапазон `d53f42a6..141aff23`, режим `full`, исполнитель по выбору Alex — плагин Codex 1.0.4. Все четыре независимых слоя завершились. Из 18 исходных замечаний после индивидуальной оценки: 4 исправления, 3 повтора отложенных вопросов, 8 отклонённых замечаний; три пары объединены по общей причине. Вопросов, требующих решения о поведении, нет. Код приложения и штатные тесты не менялись.

Решение Alex: вариант 2 — оставить R42.5-15…18 открытыми задачами без исправления кода. Статус стори и sprint-status синхронизированы в `in-progress`.

#### Новые задачи

- [x] [Review][Patch] **R42.5-15, medium: блокирующее чтение не проверяет изменившуюся принадлежность заказа** [`backend/apps/orders/manager_admin.py:200-213`]. `get_object()` ограничен `scope_orders`, но повторное чтение в `ManagerOrderForm.clean()` идёт через `Order.objects` только по PK. Если между чтениями суперпользователь изменит `user` заказа на клиента другого менеджера или `is_master=False` (оба поля доступны в основной админке), неизменные трек и дата проходят проверку, а `save_model()` сохраняет правку уже недоступного заказа. Это не ранее согласованное окно смены ответственного в строке клиента: здесь меняются поля самой блокируемой строки заказа. При получении блокировки повторно проверить актуальную строку по правилу раздела и вернуть 404 при выходе из выборки; добавить проверки обоих сценариев. Два временных HTTP-воспроизведения в Docker моделировали изменение строки после `get_object()` в том же соединении: итоговый заказ отсутствовал в `scope_orders`, но POST отвечал 302 и записывал трек. Настоящий конкурентный сценарий двумя соединениями для этого замечания не запускался. Источник: ID 12, `edge-case-hunter`.
- [x] [Review][Patch] **R42.5-16, medium: тест поиска пропускает полностью отключённую фильтрацию** [`backend/tests/integration/test_manager_orders_section.py:282-304`]. Для запросов чужого заказа проверяется только отсутствие чужого PK, для запросов своего — присутствие своего PK. Возврат всей исходной выборки своих заказов удовлетворяет обеим проверкам и не доказывает AC2. Добавить несколько своих заказов с различающимися поисковыми значениями, точное множество результата для каждого поля и пустую выдачу для отсутствующего значения. Временная мутация `get_search_results -> (queryset, False)` оставила оба параметра теста зелёными. Источник: ID 4, `blind-hunter`.
- [x] [Review][Patch] **R42.5-17, medium: поток удаления может пережить тест после таймаута** [`backend/tests/integration/test_manager_orders_section.py:648-685`]. В `get_object_then_delete()` локальный `deleting` запускается и ожидается через `join(timeout=30)`, но завершение не проверяется, а внешнего `finally` со ссылкой на работника нет. Если SQL удаления не завершится за этот срок, основной поток продолжит POST/выход по ошибке, и teardown может начать очистку БД при работающем удалении. Сохранить управление работником за пределами хука, гарантировать его завершение при любом выходе, ограничить ожидание SQL и явно передавать таймаут/исключение в основной поток. Это отдельный тест от исправленного R42.5-13. Вывод по коду; искусственная блокировка удаления в этом прогоне не запускалась. Источники: ID 5 и 16, `blind-hunter+edge-case-hunter`, оба `medium`.
- [x] [Review][Patch] **R42.5-18, medium: тест блока субзаказов не защищает статус и сумму** [`backend/tests/integration/test_manager_orders_section.py:464-481`]. AC4 требует номер, статус и сумму каждого субзаказа, но тест проверяет только номера, отсутствие ссылок и права. Проверки сумм товарных позиций относятся к другой таблице. Задать субзаказам разные статусы и суммы и проверить значения в соответствующих строках inline. Временная мутация `SubOrderInline.fields = ("sub_number",)` оставила этот тест зелёным. Это пробел регрессионной проверки, не отсутствие колонок в текущей реализации. Источник: ID 17, `verification-gap`; доказательства слоя приняты по правилам workflow и дополнительно подтверждены мутацией.

#### Повторы отложенных вопросов

- [x] [Review][Defer] **Повтор R42.5-D1, maybe-false, потенциальный medium: конечный файл в Excel** [`backend/apps/orders/manager_admin.py:386-405`]. ID 7, `blind-hunter`. Python-парсер не доказывает сохранность ведущих нулей и разделение колонок двойным кликом в целевой локали. Отложено: проверить целевую версию и локаль Excel; новой самостоятельной задачи нет.
- [x] [Review][Defer] **Повтор R42.5-D2, medium: устаревшие данные для бонусного сигнала** [`backend/apps/orders/manager_admin.py:417`; `backend/apps/bonuses/services/accrual.py:139-177`]. ID 1 и 13, `blind-hunter+edge-case-hunter`. Блокирующее чтение не освежает статус и закэшированного клиента перед `post_save`; общий бонусный сервис существовал до baseline. Отложено: прежняя задача актуальности данных и порядка блокировок, с конкурентным тестом; новой самостоятельной задачи нет.
- [x] [Review][Defer] **Повтор R42.5-D3, medium: полного зелёного AC12 нет** [Debug Log References этой стори]. ID 9 и 18, `blind-hunter+acceptance-auditor`. Последний записанный полный результат — `4289 passed, 76 skipped, 17 failed`, также остаются ошибки общего isort вне diff. Отложено: полный зелёный прогон и линтеры в LF-окружении либо явное исключение владельца; целевые проверки этого ревью не заменяют гейт, новой самостоятельной задачи нет.

#### Индивидуальная оценка до объединения

| ID | Источник | Вердикт | Доказательство и маршрут |
|---|---|---|---|
| 1 | blind-hunter | medium | Сигнал получает прежний экземпляр заказа и клиента; общий сервис не перечитывает их для `is_eligible`. Повтор D2. |
| 2 | blind-hunter | low | Ссылка клиента даёт защищённый 403 при отдельно отозванных правах User. Отклонено: редкая конфигурация, новая условная ветка без утечки данных. |
| 3 | blind-hunter | low | Отдельный LF без формулы не получает апостроф, вопреки широкой формулировке docstring; CSV writer корректно заключает его в кавычки, а LF перед `=` уже нейтрализуется через `lstrip`. Отклонено: дополнительная защитная ветка для безопасной ячейки не оправдана. |
| 4 | blind-hunter | medium | Возврат всей собственной выборки проходит обе группы утверждений поиска. Воспроизведено мутацией; R42.5-16. |
| 5 | blind-hunter | medium | `join(timeout=30)` без проверки завершения и внешнего управления оставляет живого работника при таймауте. R42.5-17. |
| 6 | blind-hunter | low | Отдельного теста отказа аудита нет, но штатный `changeform_view` охватывает сохранение транзакцией, а `log_action` не подавляет исключение. Отклонено: дополнительная проверка неизменённой атомарности Django без обнаруженного нарушения. |
| 7 | blind-hunter | maybe-false | Для ведущих нулей и разделителя нужен целевой Excel; он не запускался. Повтор D1, потенциальный medium. |
| 8 | blind-hunter | medium | AC6 буквально требует пустой выбор, но Task 3 прямо предписывает выбранный id и штатный отказ Django. Отклонено: исправление проверяемой спецификации, конфликт уже зафиксирован. |
| 9 | blind-hunter | medium | Полный отчёт содержит 17 ошибок и незелёный общий isort. Повтор D3. |
| 10 | blind-hunter | low | Решения 6/7/11 расходятся с кодом, но утверждённые изменения уже объяснены в Completion Notes. Отклонено: редактирование проверяемой спецификации. |
| 11 | blind-hunter | low | File List не покрывает все сопутствующие документы выбранного baseline. Отклонено: расширение отчёта в проверяемой спецификации, не дефект приложения. |
| 12 | edge-case-hunter | medium | Доступные в `/admin/` поля user/is_master могут измениться между чтениями; повторное чтение не ограничено выборкой. Два HTTP-воспроизведения с подстановкой состояния; R42.5-15. |
| 13 | edge-case-hunter | medium | `obj.status` и закэшированный `obj.user` не обновляются перед сигналом. Повтор D2. |
| 14 | edge-case-hunter | low | Тот же защищённый 403 при отозванных правах User, что ID 2. Отклонено: редкая конфигурация не оправдывает дополнительную ветку отображения. |
| 15 | edge-case-hunter | low | `force_login` расположен до try/finally работника; при сбое самой аутентификации исключение не попадает в errors и закрытие соединений обходится. Отклонено: редкий отказ подготовки тестового запроса, без влияния на штатный путь; отдельную защиту не добавляем. |
| 16 | edge-case-hunter | medium | Таймаут локального join не завершает поток удаления до teardown. Та же причина, что ID 5; R42.5-17. |
| 17 | verification-gap | medium | Доказательство слоя принято: колонки статуса/суммы inline не проверяются. Мутация дополнительно прошла; R42.5-18. |
| 18 | acceptance-auditor | medium | Итоговый полный зелёный AC12 не подтверждён отчётом. Повтор D3. |

#### Проверки четвёртого прогона

- GitNexus актуален на `141aff23`; `detect-changes --scope all` на чистом дереве: изменений нет. `detect-changes --scope compare --base-ref d53f42a6`: 13 файлов, 91 символ, 3 процесса, риск `medium`. `impact ManagerOrderAdmin`: 2 прямых импорта, LOW; `impact manager_queue`: 1 прямой вызывающий, LOW; `impact scope_orders`: 2 прямых вызывающих, 1 процесс, LOW.
- Docker + PostgreSQL, оба штатных модуля и два временных воспроизведения: **107 passed**, 6 предупреждений, 186.20 с. Это 105 штатных проверок и два сценария подстановки изменившихся user/is_master после первоначального чтения. Проверки воспроизведения подтверждали наличие текущего сохранения вне выборки, а не исправленное поведение.
- Мутации только в памяти отдельного Python-процесса контейнера: отключённая фильтрация поиска и удалённые статус/сумма inline. Соответствующие штатные проверки: **3 passed, 64 deselected**, 5 предупреждений, 30.93 с. Обе мутации выжили; файлы не изменялись.
- Полный backend-набор, линтеры, Excel, воспроизведение таймаута удаления и настоящий конкурентный сценарий смены принадлежности заказа в этом прогоне не запускались. Ранее поднятые тестовые PostgreSQL/Redis оставлены работающими; контейнеры прогонов удалены через `run --rm`.

#### Отклонённые замечания четвёртого прогона

- ID 2 (`blind-hunter`), low: редкий защищённый 403 по ссылке клиента, новая ветка отображения не оправдана.
- ID 3 (`blind-hunter`), low: отдельный LF безопасно экранируется CSV writer; LF перед формулой уже защищён, дополнительная ветка не нужна.
- ID 6 (`blind-hunter`), low: не обнаружено нарушения штатной атомарности Django; отдельный тест общего механизма не включён.
- ID 8 (`blind-hunter`), medium: известное противоречие AC6/Task 3 требует правки проверяемой спецификации, не кода.
- ID 10 (`blind-hunter`), low: согласование текста решений с уже записанными отклонениями меняет проверяемую спецификацию.
- ID 11 (`blind-hunter`), low: дополнение File List сопутствующими документами меняет проверяемую спецификацию.
- ID 14 (`edge-case-hunter`), low: тот же редкий защищённый 403, что ID 2.
- ID 15 (`edge-case-hunter`), low: дополнительная защита редкого сбоя force_login в подготовке теста не оправдана повседневным сценарием.

### Review Findings — пятый прогон (2026-10-15, Codex, HEAD `4b6e898`)

Область: полный diff `d53f42a6..4b6e898`, 13 файлов, +2820/-17 строк, 3018 строк diff. Четыре слоя Codex завершились без отказов. После индивидуальной оценки 19 исходных замечаний: 4 `patch`, 3 повтора существующих `defer`, 9 отклонённых исходных замечаний. Новых подтверждённых дефектов рабочего кода нет; исправления относятся к надёжности и полноте тестов. По решению Alex R42.5-19…22 оставлены открытыми задачами без исправления кода. Статус истории возвращён в `in-progress`, sprint-status синхронизирован.

#### Исправления

- [ ] [Review][Patch] **R42.5-19, medium: конкурентный тест может отпустить незавершённые POST в очистку БД** [`backend/tests/integration/test_manager_orders_section.py:688-728`]. В отличие от `other_connection`, оба работника `test_concurrent_card_waits_for_lock_and_is_rejected` не ограничивают SQL через `statement_timeout`. `finally` делает только `join(timeout=30)`: это ожидание, а не завершение потока. Если `first_saved.wait()` или запрос проверки блокировки выбросит исключение, проверка `is_alive()` после `finally` вообще не выполнится. При затянувшемся SQL работник может продолжить обращения к тестовой БД после выхода теста. Ограничить SQL работников и обеспечить их завершение на ошибочном пути до teardown; проверку живых потоков выполнять в очистке, а не только на успешном пути. Источники: ID 7 (`blind-hunter`), ID 14 (`edge-case-hunter`); оба вердикта `medium`. Зависший SQL в этом прогоне не воспроизводился; дефект управления завершением установлен по коду.
- [ ] [Review][Patch] **R42.5-20, medium: скрытая исходная дата проверяется не тем путём, которым её отправляет браузер** [`backend/tests/integration/test_manager_orders_section.py:250-258`, `:804-810`]. `card_payload` берёт `initial-delivery_date` из `BoundField.initial`, минуя HTML. Проверка HTML закрепляет лишь имя скрытого поля и использует заказ без даты. Если скрытое значение непустой даты начнёт рендериться пустым, тестовые POST останутся корректными, а браузерная свежая карточка будет отклоняться как устаревшая. Добавить сценарий заказа с установленной датой: извлечь исходные и редактируемые значения из HTML, изменить трек и проверить успешное сохранение без ошибки устаревания. Источник: ID 17 (`verification-gap`), вердикт `medium`; доказательства слоя приняты, мутация в этом прогоне не запускалась.
- [ ] [Review][Patch] **R42.5-21, low: выбранный CSV-экспорт не защищён от выгрузки неотмеченных своих заказов** [`backend/tests/integration/test_manager_orders_section.py:911-935`]. В сценарии выбранного экспорта отмечены оба доступных своих заказа; прочие сценарии также не оставляют доступного, но невыбранного заказа. Замена переданного queryset на `self.get_queryset(request)` внутри `export_orders_csv` проигнорирует выбор, но сохранит эти ожидания. Создать два своих заказа, выбрать только один и проверить точное множество номеров CSV. Источник: ID 16 (`verification-gap`), вердикт `low`; доказательства слоя приняты, мутация в этом прогоне не запускалась.
- [ ] [Review][Patch] **R42.5-22, low: обязательные поля карточки сверяются с самой реализацией** [`backend/tests/integration/test_manager_orders_section.py:440-473`]. Проверка `adminform.readonly_fields == model_admin.readonly_fields` не задаёт независимого состава по AC4. Например, удаление `discount_amount` и `delivery_cost` одновременно из `fieldsets` и `readonly_fields` проходит такую проверку; отдельного утверждения о наличии этих полей и их значениях здесь нет. Закрепить обязательные поля независимым перечнем и проверить отображаемые суммы с различающимися значениями. Это проверка состава карточки мастера, не повтор исправленного R42.5-18 про строки субзаказов. Источник: ID 10 (`blind-hunter`), вердикт `low`; установлено чтением теста, мутация не запускалась.

#### Повторы отложенного долга

- [x] [Review][Defer] **Повтор R42.5-D1, maybe-false, потенциальный medium: открытие CSV в целевом Excel** [`backend/apps/orders/manager_admin.py:405-440`]. ID 3 (`blind-hunter`): сохранность ведущих нулей и разделение колонок не установлены по результату открытия файла в целевой версии и локали Excel. deferred: прежняя задача, без нового самостоятельного пункта; Excel в этом прогоне не запускался.
- [x] [Review][Defer] **Повтор R42.5-D2, medium: бонусный сервис получает устаревающий экземпляр заказа** [`backend/apps/orders/manager_admin.py:207-208`, `:421`; `backend/apps/bonuses/services/accrual.py:139-177`]. ID 1 (`blind-hunter`) и 11 (`edge-case-hunter`): блокировка перечитывает трек и дату, но не обновляет статус и закэшированного клиента экземпляра для `post_save`. deferred: общий сервис существовал до baseline; актуальность и порядок блокировок требуют отдельного исправления и теста двумя соединениями. Оба индивидуальных вердикта `medium`; конкурентное начисление не воспроизводилось.
- [x] [Review][Defer] **Повтор R42.5-D3, medium: полного зелёного AC12 пока нет** [`_bmad-output/implementation-artifacts/Story/42-5-manager-section-orders-and-home.md`, Debug Log References]. ID 4 (`blind-hunter`) и 19 (`acceptance-auditor`): последний записанный полный результат — `4292 passed, 76 skipped, 17 failed`, общий isort также с ошибками. deferred: ранее существовавшие ошибки вне diff; получить полный зелёный набор и линтеры в LF-окружении либо явное решение владельца о гейте. Оба индивидуальных вердикта `medium`; новых прогонов в этом ревью нет.

#### Индивидуальная оценка исходных замечаний

Вердикты вынесены до группировки; повторы сохранены с исходными ID.

| ID | Слой | Вердикт | Проверка и маршрут |
|---|---|---|---|
| 1 | blind-hunter | medium | Сигналу передаётся прежний экземпляр, общий `is_eligible` читает его статус и клиента. Повтор D2. |
| 2 | blind-hunter | low | При отдельно отозванных правах User ссылка действительно даёт защищённый 403. Редкая конфигурация, дополнительная ветка отображения не оправдана; отклонено. |
| 3 | blind-hunter | maybe-false | Для проверки ведущих нулей и колонок нужен целевой Excel, а не CSV-парсер. Потенциальный medium, повтор D1. |
| 4 | blind-hunter | medium | Отчёт не содержит полного зелёного результата; отдельные 20 проверок скриптов его не заменяют. Повтор D3. |
| 5 | blind-hunter | medium | AC6 буквально конфликтует с Task 3, который явно требует выбранный id для стандартного действия Django. Отклонено: исправление проверяемой спецификации. |
| 6 | blind-hunter | low | Исходные решения не обновлены, но изменения явно описаны в Completion Notes. Отклонено: исправление проверяемой спецификации. |
| 7 | blind-hunter | medium | Ограниченный join не завершает поток; исключение до finally обходит последующий assert. R42.5-19. |
| 8 | blind-hunter | maybe-false | Запрос допускает посторонний ожидающий PID, но другой источник блокировки в изолированной БД данного теста не показан; ложный успешный результат не доказан. Потенциальный low, отклонено. |
| 9 | blind-hunter | low | Отдельного сценария смены принадлежности во время ожидания нет; имеющиеся тесты отдельно закрепляют блокировку и ограниченное чтение. Нарушение перепроверки WHERE PostgreSQL не показано. Отклонено как избыточное расширение проверки без установленного дефекта. |
| 10 | blind-hunter | low | Проверка readonly-полей использует саму реализацию как эталон; обязательные суммы можно убрать незаметно. R42.5-22. |
| 11 | edge-case-hunter | medium | Та же передача устаревающего экземпляра бонусному сигналу, что ID 1. Повтор D2. |
| 12 | edge-case-hunter | low | Тот же защищённый 403 по ссылке при нестандартном отзыве прав User, что ID 2. Отклонено. |
| 13 | edge-case-hunter | low | `force_login` действительно стоит до try/finally. Редкий отказ подготовки тестового запроса, не основной путь; отдельное усложнение не оправдано. Отклонено, как в предыдущем прогоне. |
| 14 | edge-case-hunter | medium | После истечения join живой POST не останавливается, возможен переход к очистке БД. Общая причина с ID 7, R42.5-19. |
| 15 | edge-case-hunter | maybe-false | У `other_connection` уже есть SQL-таймаут 10 с и два ожидания по 30 с; конкретное расписание штатных update/delete, переживающее оба, не показано. Для проверки нужен ограниченный воспроизводимый сценарий медленного многооперационного действия. Потенциальный low для этого тестового helper, отклонено. |
| 16 | verification-gap | low | Доказательства слоя приняты: нет доступного, но невыбранного своего заказа, отличающего переданную выборку от полной. R42.5-21. |
| 17 | verification-gap | medium | Доказательства слоя приняты: helper обходит фактическое скрытое HTML-значение непустой даты. R42.5-20. |
| 18 | acceptance-auditor | medium | Буквальное AC6 не совпадает с явным Task 3. Отклонено: исправление проверяемой спецификации, как ID 5. |
| 19 | acceptance-auditor | medium | Последний записанный общий прогон содержит 17 ошибок и ошибки isort вне diff. Повтор D3. |

#### Проверки пятого прогона

- GitNexus актуален на `4b6e898`. `detect-changes --scope all` до появления сторонних правок: изменений нет. `impact ManagerOrderForm`: LOW, 2 прямых импорта; `impact export_orders_csv`: LOW, 0 найденных вызывающих. Динамическое действие Django этот граф полностью не отражает.
- К моменту `detect-changes --scope compare --base-ref d53f42a6` появились сторонние изменения в 7 backend-тестах вне истории: команда показала 20 файлов, 95 символов, 3 процесса, риск medium. Ревьюеры читали неизменный временный diff из 13 файлов, сформированный до этих правок; посторонние изменения не включены в область ревью и не изменялись агентом.
- Docker-тесты и мутации в этом прогоне не запускались: уже работал другой тестовый контейнер с общей тестовой БД. Результаты прежних прогонов не выдаются за новые. Excel и конкурентное начисление бонусов также не запускались.

#### Отклонённые замечания пятого прогона

- ID 2 (`blind-hunter`), low: редкий защищённый 403 при отдельно отозванных правах User; новая ветка отображения не оправдана.
- ID 5 (`blind-hunter`), medium: согласование AC6 и Task 3 меняет проверяемую спецификацию.
- ID 6 (`blind-hunter`), low: согласование исходных решений с уже записанными отклонениями меняет проверяемую спецификацию.
- ID 8 (`blind-hunter`), maybe-false: другой блокирующий участник в изолированной тестовой БД не установлен; потенциальный low, дополнительная привязка PID не обоснована показанным расписанием.
- ID 9 (`blind-hunter`), low: отдельный тест перепроверки WHERE после ожидания расширяет уже имеющиеся проверки блокировки и scope без установленного дефекта.
- ID 12 (`edge-case-hunter`), low: повтор редкого защищённого 403, как ID 2.
- ID 13 (`edge-case-hunter`), low: редкий отказ самого force_login, как в предыдущем ревью; отдельная защита не оправдана.
- ID 15 (`edge-case-hunter`), maybe-false: не показан штатный callback, переживающий SQL-таймаут и оба join; потенциальный low, дополнительное управление отменой потока не обосновано.
- ID 18 (`acceptance-auditor`), medium: тот же конфликт проверяемой спецификации AC6/Task 3, что ID 5.

## Dev Notes

### Текущее состояние кода (сверено на `d53f42a6`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py:36-81` `ManagerAdminSite` | `has_permission` с кэшем членства на `request`, `index_template = "admin/manager/index.html"`, `get_app_list` («Клиенты») | + `index` со счётчиками |
| `backend/templates/admin/manager/index.html` | `{% extends "admin/index.html" %}`, пустой `{% block sidebar %}` | + `{% block content %}` с очередью и `{{ block.super }}` |
| `backend/templates/admin/index.html` | переопределяет только `{% block content %}`: блоки приложений в порядке `products, integrations, common, orders, …` через `_app_block.html` | не меняется |
| `backend/apps/orders/admin.py:38-221` `OrderAdmin` | английские подписи, `get_queryset` с `select_related("user")` и `prefetch_related("items", "sub_orders__items")`, `get_search_results` с нормализацией UI-номера, действие `export_to_csv` без `permissions`, `OrderItemInline` | не меняется, наследуется |
| `backend/apps/orders/apps.py` `OrdersConfig.ready` | импорт `signals` | + импорт `manager_admin` |
| `backend/apps/orders/models.py:30-330` `Order` | `tracking_number`, `delivery_date` (`:187-197`), `notes` (`:270`); `is_master`, `parent_order`, `vat_group`; `order_number` без явного значения — UUID (`:331`) | не меняется |
| `backend/apps/users/manager_admin.py:34` `scope_clients` | `responsible_manager=request.user` минус `staff_accounts_q()` | не меняется, вызывается |
| `backend/apps/bonuses/signals.py:18` | `post_save` любого мастер-заказа → `accrue_for_order` (идемпотентно, `is_eligible` сверяет статус с `accrual_status`) | не меняется |
| `backend/apps/orders/services/order_status_import.py:785`, `:914` | статус, оплата, флаги 1С — `save(update_fields=…)` под `select_for_update` | не меняется; поэтому правка менеджера и импорт не затирают друг друга |
| `backend/apps/orders/tasks.py:203`, `:310` | письмо получателям уведомлений о новом заказе ведёт в `/admin/orders/order/<id>/change/` | не меняется: получатели — `NotificationRecipient`, не менеджеры (как `send_admin_verification_email` в 42.4) |

### Состав прав группы «Менеджеры» (миграция `users/0023`, 42.1)

`orders.view_order`, `orders.change_order`, `orders.view_orderitem` уже в наборе (и у «Руководителей»). `add_order`/`delete_order` нет — кнопки «Добавить» и «Удалить» и так скрыты, явные `has_add_permission`/`has_delete_permission` → `False` страхуют от расширения прав группы. Своей миграции прав стори не добавляет.

### Чей это комментарий

`notes` — **комментарий клиента при оформлении** (`OrderCreateSerializer.Meta.fields`, `orders/serializers.py:183`). Клиент видит его в личном кабинете в карточке «Примечания» (`frontend/src/components/business/OrderDetail/OrderDetail.tsx:249`), туда же уходит `tracking_number` (`:201`). Субзаказы получают копию `notes` и `delivery_date` при создании (`order_create.py:128-130`) и после правки мастера не обновляются — в 1С `notes` и трек-номер не выгружаются (`order_export.py` их не читает). Значит, правка менеджера в `notes` **заменила бы текст клиента и была бы видна клиенту** («звонить после 18:00» превратилось бы во внутреннюю заметку менеджера). **Решение Alex 15.10.2026: `notes` в разделе только для чтения.** Спецификация говорила «комментарий» без уточнения, чей он; эпик (FR-42-15, Story 42.5) и `section-contents.md` («Менеджер → Заказы», «Перечень действий для журнала») поправлены. Внутреннее поле менеджера, если понадобится, — отдельная стори с миграцией. На проде 15.10.2026 у единственного мастер-заказа `notes` пуст.

### Почему 404 работает именно так

Как в 42.4 (`Story/42-4-…md`, Dev Notes): `_get_obj_does_not_exist_redirect` зовут `_changeform_view`, `history_view`, `delete_view` (Django 5.2.7, `options.py:1824`, вызовы `:1873`, `:2225`, `:2283`). `delete_view` раньше поиска объекта проверяет `has_delete_permission` → 403. Массовое действие получает выборку из `ChangeList.get_queryset` → `get_queryset` раздела: чужой id и субзаказ отсекаются.

### Подводные камни

- **Хук 42.2 при создании клиента** — `make_client` из 42.4 ставит ответственного `update()` после создания и по умолчанию `responsible_manager_manual=True`. Заказы создавать после клиента.
- **`Order.objects.create` шлёт письма** (`orders/signals.py:20`, только при `created` и `is_master`). В тестах — `.delay` Celery; в 42.4 и тестах заказов это не мешало. Если очередь упрётся в брокер — замокать `apps.orders.tasks.send_order_confirmation_to_customer` и `send_order_notification_email`.
- **`order_number` без явного значения — UUID** (`models.py:331`), `order_number_display` для него вернёт строку как есть. Для поиска по UI-формату нужен канонический номер (`CCCCCYYNNN`, `.windsurf/rules/order-numbering.md`).
- **View-only инлайн субзаказов в POST.** Формсет инлайна строится и при POST; `form_payload` из 42.4 собирает его management form из GET-контекста. Без неё POST карточки упадёт на `ManagementForm data is missing`.
- **`items_count` родителя** зовёт `obj.sub_orders.exists()` и `sub.items.count()`: на prefetched-выборке Django отвечает из кэша (`QuerySet.exists()`/`count()` при заполненном `_result_cache`), лишних запросов нет. Тест AC11 это закрепляет.
- **`date_hierarchy`** добавляет запросы дат — их число от числа строк не зависит.
- **Бонус при сохранении.** `post_save` срабатывает на каждую правку мастера (решение 5). Если заказ уже в статусе начисления и бонус по нему ещё не начислен, правка трек-номера его начислит — так же, как это сделал бы следующий импорт статуса. Это штатная идемпотентная логика, не дефект стори.
- **Сессия общая для `/admin/` и `/manager/`** — суперпользователь на `/manager/` видит вход (решение 2 стори 42.4).

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет. Веб-исследование версий не требуется: стори использует только штатный `ModelAdmin`/`AdminSite` закреплённой версии.
- Модели, миграции, API, OpenAPI, фронтенд, nginx не меняются.
- Язык: интерфейс, сообщения, комментарии, docstrings — русский (NFR-42-03).

### Тестирование

- Только Docker + PostgreSQL. Конкретный тест: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`. `--env-file` не передаётся. Параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры — по каталогу: `tests/unit/` → `unit`, `tests/integration/` → `integration`. Новый каталог под `tests/` не заводить.
- Проверки доступа — критический модуль, покрытие ≥ 90 % (NFR-42-01): `apps/orders/manager_admin.py`, изменённый `freesport/admin_site.py`.
- Сообщения админки — `message_texts` из 42.4.

### Уроки 42.4

- Ревью 42.4 шло 37 замечаний за десяток кругов. Основные классы: гонки «прочитал — записал полным `save()`» (R42.4-1, -5, -6), тесты, которые не падают при удалении защиты, и выбор действия из второй формы списка (R42.4-4, -34). Для 42.5 первый класс снят решением 5 (`update_fields`), второй — таблицей мутаций. Блокировок в стори нет — решение 6 объясняет почему, ссылаться на него при ответе ревьюеру.
- `_executed_action` и блокировки `response_action` из 42.4 не переносить: единственное действие раздела заказов — экспорт, он ничего не пишет.
- Отклонения от стори — в Completion Notes с причиной, не молча (отклонения 1–3 стори 42.4).
- `.gitattributes` в репозитории нет, `core.autocrlf=true`: новые `.sh` в стори не появляются, но если понадобятся — LF.

### Связь с последующими стори

- **42.7** снимает фильтр для руководителя: меняет `scope_clients` и `scope_orders` (заказы без клиента — только руководителю, FR-42-24). Счётчики главной у руководителя тогда покажут весь отдел — это ожидаемо. Замечание к размещению: `manager_queue` считает и клиентов, и заказы, но лежит в `apps/orders` (рядом со `scope_orders`), отсюда импорт внутри `ManagerAdminSite.index` (решение 11). Если 42.7 или 42.8 добавят на главную счётчики других приложений, перенести `manager_queue` к сайту (`freesport/`), а не множить импорты внутри методов. В 42.5 не переносить.
- **42.8** — сводка; выручка по мастер-заказам, как здесь в списке.
- **42.9** строит ленту, в том числе по `update_order` (поля `changes.fields`).

### Project Structure Notes

- Новые файлы:
  - `backend/apps/orders/manager_admin.py`;
  - `backend/tests/integration/test_manager_orders_section.py`;
  - `backend/tests/unit/test_manager_orders_admin.py`.
- Изменяемые:
  - `backend/apps/orders/apps.py`;
  - `backend/freesport/admin_site.py`;
  - `backend/templates/admin/manager/index.html`;
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`, этот файл.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.5, FR-42-15/16/17/30, NFR-42-01…04, Additional Requirements («Статус заказа приходит только из 1С»), UX Design Requirements (заголовок раздела, главная по образцу `index.html` и `_app_block.html`).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-3; Constraints «Фильтр по региону действует везде», «Статус заказа приходит только из 1С», «Гостевых заказов нет»), `section-contents.md` («Менеджер → Заказы», «Главная раздела», «Перечень действий для журнала»), `affected-code.md` («Модели и admin-классы разделов», «Конфликты с 1С»).
- Предыдущая стори: `_bmad-output/implementation-artifacts/Story/42-4-manager-section-own-clients.md` — решения 1–13, Dev Notes («Как Django резолвит URL второго сайта», «Почему 404 работает именно так», «Подводные камни»), Completion Notes (отклонения, R42.4-1…37).
- Код: `backend/apps/orders/admin.py`, `backend/apps/orders/models.py`, `backend/apps/orders/serializers.py:100-125`, `:175-190`, `backend/apps/orders/services/order_status_import.py:745-815`, `:885-920`, `backend/apps/bonuses/signals.py`, `backend/apps/bonuses/services/accrual.py:139-210`, `backend/apps/users/manager_admin.py`, `backend/freesport/admin_site.py`, `backend/templates/admin/manager/index.html`.
- Правила: `.windsurf/rules/order-numbering.md`, `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker).

## Вопросы к Alex — закрыты 15.10.2026

1. **«Новые заказы» = статус `pending`** — оставлен. Замер прода: мастер-заказ один, копиться нечему (решение 9).
2. **Комментарий заказа** — только для чтения (решение 4, «Чей это комментарий»).
3. **CSV** — русские заголовки и BOM в разделе менеджера, `/admin/` без изменений (решение 8).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code, `bmad-dev-story`.

### Debug Log References

- **GitNexus pre-flight.** Индекс `stale` (`7b169a1`), `git diff --stat 7b169a1 HEAD -- backend/apps backend/freesport` пуст — переиндексация не нужна. `impact --direction upstream`: `OrderAdmin` — LOW, 0 вызывающих; `ManagerAdminSite` — LOW, 2 прямых импорта (`freesport/urls.py`, `apps/users/manager_admin.py`); `export_to_csv` и `items_count` неоднозначны по имени, через `cypher` у методов `orders/admin.py` вызывающих нет. `detect-changes --scope all`: risk low, 0 процессов; `get_app_list` в списке — сдвиг строк на устаревшем индексе, фактически в `admin_site.py` добавлен только `index`.
- **Новые тесты:** `test_manager_orders_section.py` — 41 passed, `test_manager_orders_admin.py` — 18 passed. Покрытие: `apps/orders/manager_admin.py` 99 % (непокрыты две защитные ветки — заказ без клиента в `client_link` и пустой состав в `items_table`; в разделе такие заказы не видны), `freesport/admin_site.py` 100 %.
- **Проверка мутациями** — скрипт по очереди вносил мутацию, гонял названные тесты в контейнере и возвращал файл. Все 12 убиты:

  | Мутация | Упали |
  |---|---|
  | без `is_master=True` в `scope_orders` | `TestChangelist::test_only_own_master_orders`, `TestForeignOrder::test_direct_urls_answer_404` |
  | `user__in=scope_clients(...)` → `user__responsible_manager=request.user` | `TestChangelist::test_only_own_master_orders` |
  | `_get_obj_does_not_exist_redirect` → штатный редирект | `TestForeignOrder::test_direct_urls_answer_404` |
  | `obj.save(update_fields=…)` → `super().save_model(...)` | `TestForgedPost::test_only_tracking_number_is_saved` |
  | `status` правимый | `TestForgedPost::test_only_tracking_number_is_saved` |
  | `notes` правимый | `TestOrderCard::test_read_only_content`, `TestForgedPost::test_only_tracking_number_is_saved` |
  | без записи BOM в `export_orders_csv` | `TestExport::test_selected_forged_foreign_id_is_ignored` |
  | ранний `return` в сигнале бонусов при `update_fields` | `TestForgedPost::test_pending_bonus_is_accrued_once` |
  | возраст через `(timezone.now() - oldest).days` | `TestQueue::test_calendar_day_boundary` |
  | без раннего `return` при пустом `changed` | `TestAuditLog::test_save_without_changes_writes_nothing` |
  | без `exclude(role=ROLE_UNREGISTERED)` | `TestQueue::test_counters_and_links` |
  | без `{% block sidebar %}{% endblock %}` | `TestLinksStayInSection::test_pages_have_no_admin_links` |

- **Полный прогон** (`-n 4 -m "not performance and not slow"`, `freesport-test`): 4243 passed, 76 skipped, 17 failed за 16:08. Все 17 — `tests/unit/test_check_manager_route_script.py` и `tests/unit/test_release_has_manager_route_script.py`: bash в контейнере падает на `$'\r': command not found`. Причина — окружение: в индексе `scripts/deploy/*.sh` с LF, в рабочей копии Windows (`core.autocrlf=true`, `.gitattributes` нет) — CRLF. С рабочими копиями, приведёнными к LF, оба файла — 20 passed; после проверки скрипты возвращены `git checkout`. Код стори их не затрагивает, в CI (Linux) CRLF нет.
- **Линтеры** в `freesport-test` после pytest: `black --check .` — 473 unchanged; `flake8` — чисто; `mypy .` — `Success: no issues found in 626 source files` (до этого — 4 лишних `type: ignore` в новом модуле, убраны); `makemigrations --check --dry-run` — `No changes detected`. `isort --check-only .` — одна ошибка в `tests/unit/test_order_numbering.py` (порядок `OrderNumberingService` / `OrderNumberSequenceExhausted`): файл стори не трогает, ошибка была до неё.

- **Исправления ревью R42.5-1…7 (15.10.2026).** RED: 13 новых и изменённых тестов падали на коде `8b7ad6a2`; GREEN — 93 passed в двух модулях стори.
  - Мутации новых защит — все 11 убиты:

    | Мутация | Упали |
    |---|---|
    | проверка устаревшей карточки отключена | `TestStaleCard::test_second_open_card_is_rejected` |
    | без `select_for_update` | `TestStaleCard::test_check_locks_order_row` |
    | `show_hidden_initial = False` | `TestStaleCard::test_card_carries_values_seen_on_open`, `…::test_second_open_card_is_rejected` |
    | без `csv_cell` | `TestExport::test_formula_in_client_name_is_neutralized` (5) |
    | дата CSV в UTC | `TestExport::test_row_values_follow_admin_export_order` |
    | счётчик заявок без проверки прав | `TestQueuePermissions::test_without_user_permissions_no_applications_counter` |
    | счётчик заказов без проверки прав | `TestQueuePermissions::test_without_order_permissions_no_orders_counter` |
    | `{% if manager_queue %}` → всегда | `TestQueuePermissions::test_without_both_no_queue_block` |
    | `delivery_date` не попадает в `update_fields` | `TestAuditLog::test_both_fields_change`, `…::test_clearing_date_writes_none` |
    | в «Составе» сумма = цена | `TestOrderCard::test_items_table_rows_have_quantity_price_and_sum` |
    | «Статус» и «Оплата» в `MANAGER_CSV_HEADER` переставлены | `TestExport::test_selected_forged_foreign_id_is_ignored` |
  - Полный прогон (`-n 4 -m "not performance and not slow"`, `freesport-test`): **4278 passed, 76 skipped, 17 failed** за 16:24. Все 17 — `test_check_manager_route_script.py` и `test_release_has_manager_route_script.py`: CRLF рабочей копии `scripts/deploy/*.sh`, как и в первом прогоне. Те же два файла со скриптами, приведёнными к LF, — **20 passed**; скрипты возвращены `git checkout`. Это закрывает R42.5-D3 по существу: в LF-окружении (CI) падений нет.
  - После полного прогона — правка под mypy в `manager_admin.py`: `get_model_admin` под `type: ignore[attr-defined]` (метод есть с Django 5.0, в закреплённых django-stubs его нет) и `clean()` возвращает `self.cleaned_data`. Black переформатировал одну строку теста. Затем повторены целевые модули: `test_manager_orders_section.py`, `test_manager_orders_admin.py`, `test_orders_admin.py`, `test_manager_admin_site.py`, `test_manager_clients_section.py` — **222 passed**.
  - Линтеры в `freesport-test`: `black --check .` — 473 unchanged; `flake8` — чисто; `mypy .` — `Success: no issues found in 626 source files`; `makemigrations --check --dry-run` — `No changes detected`. `isort --check-only .` — 4 файла вне ветки: `test_verification_workflow.py`, `regression/test_epic_28_intact.py`, `test_common_throttling.py`, `test_order_numbering.py`. Дифф с `d53f42a6` по ним пуст, ошибки существовали до стори. Файлы стори isort проходят.
  - GitNexus: индекс на `8b7ad6a`, `impact` до правок — `manager_queue` LOW (1 вызывающий — `ManagerAdminSite.index`), `export_orders_csv` LOW (0), `ManagerOrderAdmin` LOW. `detect-changes --scope all`: фактически изменены `csv_cell`, `ManagerOrderForm`, `manager_queue`, `export_orders_csv`, `save_model`, `ManagerAdminSite.index`; остальные символы списка — сдвиг строк.

- **Исправления повторного ревью R42.5-8…11 (15.10.2026).** GitNexus: индекс свежий на `8c356c1`; `impact ManagerOrderForm` — LOW, 2 прямые связи импорта, 0 процессов. RED: 4 новых теста R42.5-8 падали на `8c356c14`; GREEN — 103 passed в двух модулях стори.
  - Мутации — все 4 убиты:

    | Мутация | Упали |
    |---|---|
    | `to_python` убран из сравнения в `clean()` | `TestStaleCard::test_spaces_in_stored_tracking_do_not_make_fresh_card_stale` (3), `…::test_spaces_in_stored_tracking_keep_conflict_check` |
    | `clean()` пропускает `delivery_date` | `TestStaleCard::test_second_open_card_is_rejected[date-then-track, cleared-date-then-track, date-then-date]` |
    | чтение и сравнение без блокировки, `select_for_update` после цикла | `TestStaleCard::test_concurrent_card_waits_for_lock_and_is_rejected` |
    | `csv_rows` через `splitlines()` | `TestExport::test_multiline_client_name_is_kept_in_one_cell` |
  - Конкурентный тест повторён 5 раз подряд — 5 passed (≈22 с каждый).
  - Полный прогон (`-n 4 -m "not performance and not slow"`, `freesport-test`): **4287 passed, 76 skipped, 17 failed** за 16:45. Все 17 — `test_check_manager_route_script.py` и `test_release_has_manager_route_script.py`, `$'\r': command not found`: CRLF рабочей копии `scripts/deploy/*.sh`, как в двух прошлых прогонах. Те же два файла со скриптами, приведёнными к LF, — **20 passed**; скрипты возвращены `git checkout`.
  - Линтеры в `freesport-test`: `black --check .` — 473 unchanged; `flake8` — чисто; `mypy .` — `Success: no issues found in 626 source files`; `makemigrations --check --dry-run` — `No changes detected`; `isort --check-only .` — те же 4 файла вне ветки, файлы стори проходят.
  - `detect-changes --scope all`: 2 символа (`ManagerOrderForm`, `clean`), 0 процессов, риск low.

- **Исправления третьего ревью R42.5-12…14 (15.10.2026).** GitNexus: индекс `8c356c1` при HEAD `46125f9` (устарел на коммит R42.5-8…11, `ManagerOrderForm.clean` в нём есть); `impact ManagerOrderForm` — LOW, 2 прямые связи импорта, 0 процессов. RED: `test_order_deleted_after_open_answers_404` падал на `46125f94` с `Order.DoesNotExist` из `ManagerOrderForm.clean()` (500); GREEN — `TestStaleCard` и новые тесты 15 passed.
  - Мутации и инъекции:

    | Проверка | Результат |
    |---|---|
    | `.first()` + 404 → прежний `.get()` (код `46125f94`) | упал `TestStaleCard::test_order_deleted_after_open_answers_404` (`DoesNotExist`) |
    | при пустом `changed` перед `return` — `obj.save(update_fields=["tracking_number", "delivery_date"])` | упал `TestForgedPost::test_unchanged_card_neither_saves_nor_accrues`; `TestAuditLog::test_save_without_changes_writes_nothing` при этом зелёный — тот самый пробел R42.5-14 |
    | `RuntimeError` в основном потоке сразу после запуска второго потока, новая версия теста | падает только сам тест с инъекцией, `TestStaleCard` + `TestForgedPost` — 16 passed, ошибок teardown нет |
    | та же инъекция в версии теста из `46125f94` | `FAILED` + `ERROR at teardown` того же теста: запрос первого потока переживает тест — это и есть дефект R42.5-13 |
  - Полный прогон (`-n 4 -m "not performance and not slow"`, `freesport-test`): **4289 passed, 76 skipped, 17 failed** за 16:04. Все 17 — `test_check_manager_route_script.py` (13) и `test_release_has_manager_route_script.py` (4): CRLF рабочей копии `scripts/deploy/*.sh`, как в трёх прошлых прогонах. Те же два файла со скриптами, приведёнными к LF, — **20 passed**; скрипты возвращены `git checkout`.
  - Линтеры в `freesport-test` после pytest: `black --check .` — 473 unchanged; `flake8` — чисто; `mypy .` — `Success: no issues found in 626 source files`; `makemigrations --check --dry-run` — `No changes detected`. `isort --check-only .` — 5 файлов вне ветки: `test_pages_api.py`, `test_verification_workflow.py`, `regression/test_epic_28_intact.py`, `test_common_throttling.py`, `test_order_numbering.py`; дифф с `d53f42a6` по ним пуст (`test_pages_api.py` последний раз менялся в `0b797935`, 25.08.2026; в прошлых записях он не был назван). Файлы стори isort проходят.
  - `detect-changes --scope all`: 4 символа в `manager_admin.py` (`ManagerOrderForm`, `clean` и локальные `bound`, `seen` — сдвиг строк), 0 процессов, риск low.

- **Исправления четвёртого ревью R42.5-15…18 (15.10.2026).** GitNexus: индекс свежий на `141aff2`; `impact ManagerOrderForm` и `impact ManagerOrderAdmin` — LOW, по 2 прямых импорта (`freesport/admin_site.py`, `apps/orders/apps.py`), 0 процессов. RED: `test_order_moved_after_open_follows_section_scope[foreign-client, not-master]` падали на коде `141aff23` (2 failed), контроль `[other-own-client]` проходил. Усиленные тесты R42.5-16 и R42.5-18 проходили и на старом коде: это пробелы проверок, их RED — мутации ниже. GREEN — 108 passed в двух модулях стори.
  - Мутации и инъекции:

    | Проверка | Результат |
    |---|---|
    | блокирующее чтение без `scope_orders` (код `141aff23`) | упали `test_order_moved_after_open_follows_section_scope[foreign-client, not-master]` |
    | вместо `scope_orders` — сверка с прежним клиентом (`is_master=True, user_id=instance.user_id`) | упал контроль `[other-own-client]` |
    | `get_search_results` → `(queryset, False)` | упали `test_search_finds_only_own_orders[manager, supervisor]` |
    | `SubOrderInline.fields = ("sub_number",)` | упал `test_sub_orders_block_is_read_only` |
    | статус и сумма переставлены в `SubOrderInline.fields` | тест зелёный, ожидаемо: значения сверяются по имени поля, а порядок колонок дефектом не считается |
    | работник `other_connection` зависает на `SELECT pg_sleep(60)` | через 10 с `statement_timeout` снимает запрос, `QueryCanceled` поднимается в тесте, тест падает; ошибок teardown нет, соседние тесты зелёные |
  - Полный прогон (`-n 4 -m "not performance and not slow"`, `freesport-test`): **4292 passed, 76 skipped, 17 failed** за 15:28. Все 17 — `test_check_manager_route_script.py` (13) и `test_release_has_manager_route_script.py` (4): CRLF рабочей копии `scripts/deploy/*.sh`, как в четырёх прошлых прогонах. Те же два файла со скриптами, приведёнными к LF, — **20 passed**; скрипты возвращены `git checkout`.
  - Линтеры в `freesport-test` после pytest: `black --check .` сначала нашёл один файл — новый тест; переформатирован, после этого 473 unchanged. `flake8` нашёл одну строку длиннее 120 символов в новом тесте; исправлено, теперь чисто. `mypy .` — `Success: no issues found in 626 source files`; `makemigrations --check --dry-run` — `No changes detected`. `isort --check-only .` — 7 файлов вне ветки: `test_auth_registration_consent.py`, `test_onec_export.py`, `test_pages_api.py`, `test_verification_workflow.py`, `regression/test_epic_28_intact.py`, `test_common_throttling.py`, `test_order_numbering.py`. Дифф с `d53f42a6` по ним пуст; первые два в прошлых записях не упоминались, ветка их не меняла. Файлы стори isort проходят.
  - После форматирования повторены модули `test_manager_orders_section.py`, `test_manager_orders_admin.py`, `test_orders_admin.py`, `test_manager_admin_site.py` — **137 passed**.
  - `detect-changes --scope all`: 8 символов, 0 процессов, риск low. По факту изменены `ManagerOrderForm` (`request`, `clean`) и добавлен `ManagerOrderAdmin.get_form` — в устаревшем индексе его ещё нет. Остальные символы списка — сдвиг строк.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Сделано.** `apps/orders/manager_admin.py`: `scope_orders`, `days_ru`, `manager_queue`, `SubOrderInline`, `ManagerOrderAdmin` (белый список полей, правка только `tracking_number`/`delivery_date` через `save(update_fields=…)`, запись `AuditLog` `update_order`, 404 на чужой заказ и субзаказ, экспорт `export_orders_csv` с BOM и русскими заголовками, русские подписи колонок) и регистрация на `manager_site`; импорт модуля в `OrdersConfig.ready()`. `ManagerAdminSite.index` передаёт `manager_queue` в шаблон, главная `admin/manager/index.html` показывает очередь над списком моделей, блока «Последние действия» по-прежнему нет. `OrderAdmin` в `/admin/`, модели, миграции, API, фронтенд и nginx не менялись.
- **Существующие тесты без правок** (Task 4): `tests/unit/test_orders_admin.py`, `tests/integration/test_manager_clients_section.py`, `tests/unit/test_manager_admin_site.py`, `apps/bonuses/tests/test_admin.py`, `tests/integration/test_order_status_import_db.py` зелёные в полном прогоне. `test_manager_admin_site.py` число запросов и контекст главной не проверяет — ожидания не менялись.
- **Отклонения от стори:**
  1. AC8, тест «старейшей пять дней»: дата заявки — полдень пятого календарного дня назад по времени проекта (`local_noon(5)`), а не `now() - 5 дней 1 час`, как в Task 3. Решение 10 считает календарные дни, и `now() - 5д 1ч` между 00:00 и 01:00 по Москве дал бы «6 дней» — тест падал бы в этот час. Граница суток проверена отдельно (`test_calendar_day_boundary`, 23:50 → 00:10).
  2. Из модуля тестов 42.4 импортированы не только перечисленные хелперы, но и фикстуры `manager`, `other_manager`, `manager_client`, `section_member`, `section_client`, а также `unique_digits` и `INDEX_URL`. Task 3 разрешает импорт для `section_member`, остальные взяты так же, чтобы не дублировать. Своя autouse-фикстура `order_emails` мокает задачи писем о новом заказе: без неё каждый `Order.objects.create` ставил бы задачу в брокер.
  3. Тестов больше, чем в перечне Task 3: страж того, что экспорт в `/admin/` прежний (без BOM, английские заголовки, AC6); legacy-мастер без субзаказов показывает свои позиции; очистка даты доставки пишет `new: None` (решение 7); значения строки CSV идут в порядке `OrderAdmin.export_to_csv`.
  4. BOM в экспорте записан экранированной последовательностью `﻿`: первая версия содержала невидимый символ прямо в строковом литерале; заменён до прогона мутаций и полного набора.
- **Не сделано:** нет. Ручных шагов на проде у стори нет, выкат — после выката 42.4.
- **Исправления после ревью (15.10.2026, `bmad-dev-story`):**
  - ✅ Resolved review finding [medium]: R42.5-1 — устаревшая карточка. Новая форма `ManagerOrderForm`: у `tracking_number` и `delivery_date` включён `show_hidden_initial`, поэтому значения на момент открытия уходят в POST скрытыми полями `initial-*`. `changed_data` сравнивает POST с тем, что видел менеджер. `clean()` под `select_for_update` строки заказа сверяет эти значения с текущими. Если трек или дату успели изменить, форма невалидна: «…Изменения не сохранены. Обновите страницу и внесите правку заново.» Ответ 200, без записи заказа, `LogEntry` и `AuditLog`. Повторная отправка той же формы снова отклоняется: Django сохраняет присланное скрытое значение. Правки 1С в другие поля, в том числе `updated_at`, карточку устаревшей не делают. «Старое» значение в журнале — строка под блокировкой (`form.locked_values`), а не `form.initial`. Тесты — `TestStaleCard` (4).
  - ✅ Resolved review finding [high]: R42.5-2 — формулы в CSV. `csv_cell()` ставит апостроф перед значением, если после ведущих пробелов и управляющих/форматных символов (категория Unicode `C*`) идёт `= + - @` или их полноширинный вариант, а также перед значением, начинающимся с табуляции или `\r`. Применяется ко всем ячейкам строки. Тесты: `test_csv_cell` (17 случаев, unit) и `test_formula_in_client_name_is_neutralized` (5, через HTTP).
  - ✅ Resolved review finding [medium]: R42.5-3 — очередь и права моделей. Каждый счётчик строится, только если `has_view_or_change_permission` зарегистрированного на сайте admin-класса модели (`site.get_model_admin`). Без права не выполняется ни запрос, ни вывод ссылки. Без обоих прав в шаблоне нет блока `#manager-queue`. Одного `view` достаточно. Тесты — `TestQueuePermissions` (4) и `test_counter_needs_model_permission` (3, unit).
  - ✅ Resolved review finding [medium]: R42.5-4 — дата в CSV теперь `timezone.localtime(...)`. В тесте эталон литеральный: 22:30 UTC 14.10 → `2026-10-15 01:30`. `/admin/` не тронут.
  - ✅ Resolved review finding [medium]: R42.5-5 — `refresh_from_db()` и проверка `delivery_date` (и трека) в `test_both_fields_change` и `test_clearing_date_writes_none`.
  - ✅ Resolved review finding [low]: R42.5-6 — `test_items_table_rows_have_quantity_price_and_sum`: точные строки таблицы состава с различающимися количеством, ценой и суммой.
  - ✅ Resolved review finding [low]: R42.5-7 — заголовки CSV сверяются с литералом `EXPECTED_CSV_HEADER` в тесте, а не с `MANAGER_CSV_HEADER` из реализации.
- **Отклонения при исправлениях ревью:**
  5. Решение 6 («блокировок строк в карточке нет»): теперь строка **заказа** блокируется `select_for_update` в `ManagerOrderForm.clean()`. Причина — R42.5-1 добавил цепочку «прочитал — сравнил — записал», и без блокировки два одновременных POST оба прошли бы проверку. Решение 6 по сути не нарушено: строка `users` по-прежнему не блокируется. Порядок блокировок тот же, что у импорта статусов: `orders`, затем бонусы через `post_save`. Блокировка держится до конца транзакции `changeform_view`. Страж — `test_check_locks_order_row`.
  6. Решение 11: сигнатура `manager_queue(request, site)` вместо `manager_queue(request, site_name)`. Объект сайта нужен для `get_model_admin` (R42.5-3), имя берётся из `site.name`. Вызывающий один — `ManagerAdminSite.index` (GitNexus impact: LOW).
  7. `card_payload` в тестах дописывает скрытые поля `initial-*`, как их отправляет браузер. `form_payload` из 42.4 не менялся.
  8. R42.5-10: проверка двух соединений держит первый запрос внутри открытой транзакции подменой `ManagerOrderAdmin.save_model` (пауза только в потоке `first`), а ожидание второго определяет по `pg_stat_activity.wait_event_type = 'Lock'` в своей тестовой БД. Без такой паузы порядок двух POST не управляем.
- **Исправления повторного ревью (15.10.2026, `bmad-dev-story`):**
  - ✅ Resolved review finding [medium]: R42.5-8 — пробелы в сохранённом треке. `ManagerOrderForm.clean()` приводит значение строки через `field.to_python()` перед `has_changed`, как Django делает с `initial` в `changed_data`. Свежая карточка с треком `"TRK "`, `" TRK"`, `" TRK "` сохраняет дату, трек в БД не меняется; реальный конфликт по треку с пробелами по-прежнему отклоняется. Тесты — `test_spaces_in_stored_tracking_do_not_make_fresh_card_stale` (3), `test_spaces_in_stored_tracking_keep_conflict_check`.
  - ✅ Resolved review finding [medium]: R42.5-9 — `test_second_open_card_is_rejected` параметризован первой правкой: трек, изменение даты, очистка даты, дата после даты. Проверяются итоговые значения заказа и по одной записи `AuditLog` и `LogEntry` после отказа и повторной отправки.
  - ✅ Resolved review finding [medium]: R42.5-10 — `test_concurrent_card_waits_for_lock_and_is_rejected`: два POST в разных соединениях PostgreSQL, первый держит транзакцию после сохранения, второй подтверждённо ждёт блокировку, затем видит правку первого и получает отказ; в журналах по одной записи.
  - ✅ Resolved review finding [low]: R42.5-11 — `csv_rows` читает ответ через `io.StringIO(..., newline="")`; `test_multiline_client_name_is_kept_in_one_cell` закрепляет ячейку клиента `Первая\nВторая`.
- **Исправления третьего ревью (15.10.2026, `bmad-dev-story`):**
  - ✅ Resolved review finding [medium]: R42.5-12 — заказ удалён между чтением карточки и проверкой под блокировкой. `ManagerOrderForm.clean()` читает строку через `.first()`; нет строки — `Http404("Заказ не найден")`, как на несуществующий заказ (решение 3). `ATOMIC_REQUESTS` откатывает транзакцию запроса, `AuditLog` и `LogEntry` не пишутся. Тест `test_order_deleted_after_open_answers_404`: удаление выполняется в отдельном соединении PostgreSQL и фиксируется после `get_object()` до `clean()`.
  - ✅ Resolved review finding [medium]: R42.5-13 — `test_concurrent_card_waits_for_lock_and_is_rejected`: запуск потоков и ожидание обёрнуты в `try/finally`, где всегда `release.set()` и `join()` каждого запущенного потока; после — проверка, что потоки завершились и что исключений в них нет (исключения работников собираются в `errors` и выводятся основным потоком). Новый тест R42.5-12 построен так же.
  - ✅ Resolved review finding [medium]: R42.5-14 — `test_unchanged_card_neither_saves_nor_accrues`: верифицированный тренер, активная программа, заказ переведён в `delivered` в обход сигнала, POST карточки без изменений → 302, `Order.save` для мастера не вызывался, `BonusTransaction` нет. `test_pending_bonus_is_accrued_once` (реальная правка трека начисляет один раз) сохранён.
- **Исправления четвёртого ревью (15.10.2026, `bmad-dev-story`):**
  - ✅ Resolved review finding [medium]: R42.5-15 — блокирующее чтение в `ManagerOrderForm.clean()` идёт через `scope_orders(self.request, Order.objects.select_for_update())`: заказ, у которого до блокировки сменили клиента на чужого или сняли `is_master`, отвечает 404 (решение 3) без записи заказа, `AuditLog` и `LogEntry`. Запрос форме передаёт новый `ManagerOrderAdmin.get_form`: он ставит `request` на класс формы, который `modelform_factory` строит заново на каждый вызов. Под блокировкой PostgreSQL перепроверяет условие `WHERE` на актуальной версии строки, поэтому правка, зафиксированная во время ожидания блокировки, тоже учитывается. Тест `test_order_moved_after_open_follows_section_scope` (3 параметра): чужой клиент → 404, `is_master=False` → 404, контроль — другой свой клиент → 302 и правка сохранена. Правка строки фиксируется в отдельном соединении PostgreSQL после `get_object()` и до `clean()`.
  - ✅ Resolved review finding [medium]: R42.5-16 — `test_search_finds_only_own_orders`: три своих заказа у разных клиентов с разными значениями всех шести полей поиска. Для каждого значения своего заказа результат — ровно `{этот заказ}`, для значений чужого и для отсутствующего значения — пустое множество; без поиска список — все три своих.
  - ✅ Resolved review finding [medium]: R42.5-17 — работник другого соединения вынесен в фикстуру `other_connection`. В соединении работника стоит `statement_timeout` 10 с, `join` ждёт 30 с. Живой после `join` поток и исключение работника поднимаются в вызывающем потоке. Ссылки на работников держит фикстура, и её teardown дожидается их раньше очистки БД (`clear_db_before_test` — autouse, завершается последним). На фикстуру переведены `test_order_deleted_after_open_answers_404` и новый тест R42.5-15.
  - ✅ Resolved review finding [medium]: R42.5-18 — в `test_sub_orders_block_is_read_only` у субзаказов разные статусы и суммы («В обработке» / 300,00 и «Отправлен» / 700,00). Значения сверяются по строкам инлайна (`field.contents()` по имени поля) литералами.
- **Отклонения при исправлениях четвёртого ревью:**
  9. Решение 6 дополнено: под блокировкой строки заказа проверяется и принадлежность заказа выборке раздела (R42.5-15). Как и раньше, строка `users` не блокируется, поэтому окно передачи клиента другому менеджеру остаётся таким, как описано в решении 6.

- **R42.5-D3 — причины устранены (15.10.2026, решение Alex: вариант «b», отдельный PR).** PR #313 (`chore/isort-and-sh-eol`, merge `0f9f8ab9` в `develop`): `.gitattributes` с `*.sh text eol=lf` и isort во всех 22 файлах backend (только импорты, ветка 42.5 их не меняла; CI isort не запускает). На ветке PR полный прогон — 4260 passed, 76 skipped, 0 failed; black, isort, flake8, mypy — чисто. Прежняя запись «isort — 4–7 файлов вне ветки» была неполной: вывод смотрели через `tail`, на деле файлов было 22. В ветку 42.5 исправления придут при слиянии с `develop`; зачётный полный прогон итоговой ревизии стори — после R42.5-19…22.

### File List

- `backend/apps/orders/manager_admin.py` — новый
- `backend/apps/orders/apps.py` — изменён
- `backend/freesport/admin_site.py` — изменён
- `backend/templates/admin/manager/index.html` — изменён
- `backend/tests/integration/test_manager_orders_section.py` — новый
- `backend/tests/unit/test_manager_orders_admin.py` — новый
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — изменён
- `_bmad-output/implementation-artifacts/deferred-work.md` — изменён (отложенные R42.5-D1…D3, ревью)
- `_bmad-output/implementation-artifacts/Story/42-5-manager-section-orders-and-home.md` — изменён

### Change Log

- 2026-10-15 — стори создана (`bmad-create-story`), статус `ready-for-dev`.
- 2026-10-15 — разбор стори (party mode), решения Alex по трём вопросам:
  1. `notes` — только чтение: решения 4–7, AC4, AC5, AC7, AC9, Task 1 (`EDITABLE_FIELDS`, `readonly_fields`, блок «Комментарий клиента»), «Чей это комментарий»; эпик FR-42-15 и Story 42.5, `section-contents.md` поправлены.
  2. Экспорт CSV — своё тело с русскими заголовками и BOM, `/admin/` не меняется: решение 8, AC6, Task 1, Task 3.
  3. «Новые заказы» = `pending` подтверждено замером прода (решение 9); заявки на верификацию на проде — 13, старейшая от 26.03.2026 (решение 10).
  4. Возраст старейшей заявки — календарные дни, 0 → «сегодня»: решение 10, AC8, Task 2, Task 3.
  5. AC5 — второй сценарий: правка трек-номера начисляет отложенный бонус ровно один раз (страж против отсечения сигнала по `update_fields`).
  6. AC2 — шесть значений поиска перечислены явно (было пять в AC и «шесть» в Task 3); абзац про порядок `ready()` сокращён.
  7. Таблица мутаций — четыре новые строки; размещение `manager_queue` — замечание к 42.7 в «Связи с последующими стори».
- 2026-10-15 — реализация (`bmad-dev-story`): раздел заказов менеджера, очередь главной, 59 новых тестов, 12 мутаций убиты; статус `review`.
- 2026-10-15 — ревью Codex: 7 исправлений, 3 отложено (`deferred-work.md`); статус `in-progress`.
- 2026-10-15 — Addressed code review findings — 7 items resolved (R42.5-1…7): отклонение устаревшей карточки под блокировкой строки заказа, нейтрализация формул в CSV, очередь главной по правам моделей, московское время в CSV, усиление тестов даты доставки, состава и заголовков CSV. Новых тестов 35 (15 integration, 20 unit), 11 мутаций убиты; статус `review`.
- 2026-10-15 — повторное ревью Codex на `8c356c14`: R42.5-8…11 оставлены открытыми задачами по решению Alex; два повтора отложенного долга, девять исходных замечаний отклонено. Код не менялся; статус `in-progress`, sprint-status синхронизирован.
- 2026-10-15 — Addressed code review findings — 4 items resolved (R42.5-8…11): нормализация значения строки при проверке устаревшей карточки, тесты конфликта по дате и двух соединений PostgreSQL, CSV-хелпер тестов без потери переводов строк. Новых тестов 6 (+3 параметра существующего), 4 мутации убиты; статус `review`.
- 2026-10-15 — третий прогон ревью Codex на `46125f94`: по решению Alex R42.5-12…14 оставлены открытыми задачами без исправления кода; три повтора отложенного долга, шесть исходных замечаний отклонено. Целевой Docker-прогон: 103 passed. Статус `in-progress`, sprint-status синхронизирован.
- 2026-10-15 — Addressed code review findings — 3 items resolved (R42.5-12…14): 404 вместо 500 при удалении заказа между чтениями, гарантированное завершение потоков конкурентного теста, страж отсутствия `save()` и бонуса при неизменённой карточке. Новых тестов 2, переписан 1; полный прогон 4289 passed, 76 skipped, 17 failed (CRLF `scripts/deploy`, с LF 20 passed); статус `review`.
- 2026-10-15 — четвёртый прогон ревью Codex на `141aff23`: по решению Alex R42.5-15…18 оставлены открытыми задачами без исправления кода; три повтора отложенного долга, восемь исходных замечаний отклонено. Целевой Docker-прогон с двумя временными воспроизведениями: 107 passed; две временные мутации выжили (3 passed). Статус `in-progress`, sprint-status синхронизирован.
- 2026-10-15 — Addressed code review findings — 4 items resolved (R42.5-15…18). Блокирующее чтение карточки теперь ограничено `scope_orders`: заказ, выведенный из выборки до блокировки, отвечает 404. Тест поиска сверяет точные множества результатов. Работник другого соединения вынесен в фикстуру с `statement_timeout` и гарантированным `join`. Статус и сумма субзаказов проверяются в строках инлайна. Новый тест — 1 (3 параметра), переписаны 3. Полный прогон: 4292 passed, 76 skipped, 17 failed (CRLF `scripts/deploy`, с LF 20 passed). Статус `review`.
- 2026-10-15 — пятый прогон ревью Codex на `4b6e898`: по решению Alex R42.5-19…22 оставлены открытыми задачами без исправления кода; три повтора отложенного долга, девять исходных замечаний отклонено. Новые тестовые прогоны и мутации не запускались из-за уже работающего контейнера с общей тестовой БД. Статус `in-progress`, sprint-status синхронизирован.
