---
baseline_commit: d53f42a6
---

# Story 42.5: Раздел менеджера — заказы и главная страница

Status: ready-for-dev
Baseline Revision: d53f42a6 (`develop` = `353e33a7` + коммит nginx-фикса в ветке `fix/nginx-prod-stale-bind-mount`; код приложения на обоих одинаковый)

## Story

As a менеджер,
I want видеть заказы своих клиентов, вести трек-номер и комментарий, а на главной — сколько заявок и заказов ждут меня,
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
4. **Карточка — белый список полей** (как решение 5 стори 42.4). Правятся только `tracking_number`, `delivery_date`, `notes`. Всё остальное, что показано, — только чтение. `payment_id`, `parent_order`, `vat_group`, `status_1c`, `sent_to_1c_at`, а также служебные `export_skipped`, `customer_code_snapshot`, `order_year`, `customer_year_sequence`, `suborder_sequence`, `is_master` в форме отсутствуют.
5. **Сохранение — только правимые поля через `save(update_fields=…)`.** `save_model` пишет в БД пересечение `form.changed_data` с тремя правимыми полями плюс `updated_at`. Пустое пересечение — `save()` не вызывается вовсе: ни `post_save`, ни записи журнала. Так:
   - подделанный POST не может изменить другие колонки, даже если белый список формы когда-нибудь расширят по ошибке;
   - правка менеджера не затирает статус, оплату и флаги 1С, которые импорт статусов пишет параллельно (`order_status_import.py:785`, `:914` — тоже `update_fields` под `select_for_update`);
   - `post_save` бонусов (`bonuses/signals.py:18`) срабатывает только при реальной правке и видит статус, прочитанный в этом запросе. Начисление идемпотентно (`accrual.py`, проверка по `order_number_snapshot`), а статус в форме не меняется, поэтому лишнего начисления нет.
6. **Блокировок строк в карточке заказа нет — это осознанно, а не пропуск.** В 42.4 блокировка строки клиента понадобилась потому, что полное `save()` устаревшего объекта возвращало прежнего ответственного (R42.4-1, R42.4-5). Здесь `save()` пишет только три поля, которых не трогает ни импорт статусов, ни передача клиента, ни пересчёт ответственных. Передача клиента другому менеджеру меняет строку `users`, а не `orders`: правка, попавшая в миллисекундное окно передачи, записывает трек-номер под автором-менеджером A, и это видно в журнале. Вред — нулевой, а блокировка `users` из карточки заказа добавила бы порядок блокировок `users → orders` против `orders → bonuses` импорта. Ревьюеру: это не повтор R42.4-1.
7. **Журнал правки заказа — одна запись `AuditLog` на сохранение:** `action="update_order"`, `resource_type="Order"`, `resource_id=<pk мастер-заказа>`, `changes={"order_number": <канонический>, "fields": {<поле>: {"old": …, "new": …}}}`. В `fields` — только реально изменённые поля из трёх. Даты — строкой ISO, пустые — `None`. Старое значение — из `form.initial`. Django `LogEntry` пишется штатно, отдельно; это не дубль: 42.9 строит ленту по `AuditLog`.
8. **Экспорт CSV — существующее действие `OrderAdmin.export_to_csv`**, без новой логики выгрузки. Выборка уже ограничена: `response_action` берёт строки из `ChangeList.get_queryset`, то есть из `get_queryset` раздела, и при `_selected_action`, и при `select_across=1`. В разделе действие называется по-русски «Выгрузить выбранные заказы в CSV»: обёртка с собственным `@admin.action(description=…)` зовёт тело `OrderAdmin.export_to_csv`. Колонки и формат файла не меняются (см. вопросы в конце).
9. **«Новые заказы» — мастер-заказы своих клиентов в статусе `pending`** («Ожидает обработки»). Ссылка — `/manager/orders/order/?status__exact=pending`. Статус `pending` у заказа с сайта до решения в 1С, и в него же 1С переводит «Не согласован» и «На согласовании» (`orders/constants.py`, `STATUS_MAPPING`), то есть это заказы, которые ещё ждут обработки.
10. **«Заявки на верификацию» — клиенты из `scope_clients` со статусом `verification_status="pending"` без записей `unregistered`** — ровно то, что покажет список клиентов по ссылке `/manager/users/user/?verification_status__exact=pending`: фильтр «Учётная запись на портале» по умолчанию скрывает `unregistered` (42.4, `PortalAccountFilter`). «Старейшая» считается по `created_at`: заявка подаётся при регистрации (`users/serializers.py:381`). Исключение — устаревший путь привязки по ссылке (`views/authentication.py:675`), где `created_at` — дата импорта записи 1С; путь отключён с 26.07.2026, точность для него не нужна.
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
**And** поиск по номеру заказа клиента B (в каноническом формате и в формате UI), его email, трек-номеру и названию компании ничего не находит, а свой заказ по тем же полям находится

### AC3 — 404 на чужой заказ и на субзаказ

**Given** менеджер A
**When** он открывает по прямому URL карточку (`/manager/orders/order/<id>/change/`, GET и POST) или историю (`…/history/`) заказа клиента B, а также карточку субзаказа своего клиента
**Then** каждая отвечает 404, данные заказа B не меняются, записи `AuditLog` не создаются
**And** `/manager/orders/order/add/` и `…/<id>/delete/` своего заказа отвечают 403

### AC4 — состав карточки

**Given** менеджер открывает свой мастер-заказ
**When** страница отрисована
**Then** в форме правятся только `tracking_number`, `delivery_date`, `notes`
**And** только для чтения: номер (UI и канонический), клиент (ссылка на `/manager/users/user/<id>/change/`), статус, контакты из заказа (`customer_name`, `customer_email`, `customer_phone`), состав (позиции всех субзаказов: субзаказ, товар, артикул, количество, цена, сумма), суммы (`total_amount`, `discount_amount`, `delivery_cost`), адрес и способ доставки, способ и статус оплаты, даты оплаты и отгрузки, «Передан в 1С: да/нет», даты создания и обновления
**And** субзаказы показаны блоком только для чтения: номер, статус, сумма; без ссылок на их карточки, без добавления и удаления
**And** в HTML нет ни поля (`name="…"`), ни подписи из списка «Не показывать»: `payment_id` («ID платежа (ЮKassa)»), `parent_order` («Мастер-заказ»), `vat_group` («Группа НДС (%)»), `status_1c` («Статус из 1С»), `sent_to_1c_at` («Дата и время отправки в 1С»), `export_skipped` («Пропущен при экспорте») — в том числе в блоке субзаказов
**And** кнопок «Добавить» и «Удалить» нет

### AC5 — подделанный POST заказа

**Given** клиент-тренер (`role="trainer"`, верифицирован), активная бонусная программа с `accrual_status="delivered"` и без отсечки по дате, его мастер-заказ в статусе `processing`
**When** менеджер отправляет карточку с новым трек-номером и подделанными `status=delivered`, `payment_status=paid`, `sent_to_1c`, `total_amount`, `payment_id`, `user`, `parent_order`, `vat_group`, `status_1c`
**Then** сохранён только трек-номер, остальные поля прежние
**And** `BonusTransaction` по заказу не создана
**And** `Order.save` вызван с `update_fields`, состоящим только из изменённых правимых полей и `updated_at` (решение 5)

### AC6 — экспорт CSV только своих заказов

**Given** менеджер A, его заказы и заказ клиента B
**When** A применяет «Выгрузить выбранные заказы в CSV» со списком `_selected_action`, где подделан id заказа B, и отдельно с `select_across=1` без выбора
**Then** в обоих файлах только заказы клиентов A, номера заказа B нет
**And** в выпадающем списке действий раздела нет «Удалить выбранные» и нет английских подписей

### AC7 — журнал правки заказа

**Given** менеджер меняет трек-номер, дату доставки или комментарий своего заказа
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

### AC9 — права внутри раздела

**Given** член «Менеджеры», у группы которого в тесте оставлено только `orders.view_order` (и `users.view_user` — для входа на главную)
**When** он открывает свой заказ, отправляет POST карточки и экспорт
**Then** карточка открывается только для чтения (в форме нет полей ввода `tracking_number`, `delivery_date`, `notes`)
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

- [ ] **Task 0 — GitNexus pre-flight** (AGENTS.md)
  - [ ] `npx gitnexus status`. При `stale` — `git diff --stat <indexed> HEAD -- backend/apps backend/freesport`: пусто — переиндексация не нужна (на `d53f42a6` индекс на `7b169a1`, разница только в CI, deploy-скриптах, nginx и тестах скриптов). Иначе попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`.
  - [ ] `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по `OrderAdmin`, `export_to_csv`, `items_count`, `ManagerAdminSite`. При подготовке стори: `OrderAdmin` — LOW, 0 вызывающих; `ManagerAdminSite` — LOW, 2 прямых импорта (`freesport/urls.py`, `apps/users/manager_admin.py`). `scope_clients` — HIGH, но стори его не меняет. Сообщить Alex blast radius до правок.

- [ ] **Task 1 — `ManagerOrderAdmin`** (AC1–AC7, AC9–AC11; решения 1–8, 12, 13)
  - [ ] Новый модуль `backend/apps/orders/manager_admin.py`, регистрация в нём же: `manager_site.register(Order, ManagerOrderAdmin)`. Импорт в `OrdersConfig.ready()` (`apps/orders/apps.py`) рядом с `import apps.orders.signals`: `import apps.orders.manager_admin  # noqa: F401 — регистрация на сайте /manager/`. Порядок безопасен по той же причине, что в 42.4: `FreesportAdminConfig` в `DJANGO_APPS` раньше `apps.users` и `apps.orders`, `admin.autodiscover()` уже загрузил оба `admin.py`. Если `OrdersConfig.ready()` выполнится раньше `UsersConfig.ready()` (порядок `LOCAL_APPS`: `apps.users` раньше `apps.orders`, так что нет), импорт `apps.users.manager_admin` всё равно корректен — модуль просто загрузится раньше.
  - [ ] Функция видимости (решение 2), docstring о 42.7:
    ```python
    def scope_orders(request: HttpRequest, queryset: QuerySet[Order]) -> QuerySet[Order]:
        return queryset.filter(is_master=True, user__in=scope_clients(request, User.objects.all()))
    ```
    `user__in` с подзапросом отсекает и `user IS NULL`. Проверить в тесте AC11, что на строку лишнего запроса нет.
  - [ ] `class ManagerOrderAdmin(OrderAdmin)`:
    - `get_queryset`: `scope_orders(request, super().get_queryset(request))` — `select_related("user")` и `prefetch_related("items", "sub_orders__items")` родителя сохраняются;
    - `_get_obj_does_not_exist_redirect(self, request, opts, object_id)` → `raise Http404("Заказ не найден")` (решение 3), с комментарием, как в `ManagerClientAdmin`;
    - `has_add_permission` → `False`, `has_delete_permission` → `False`;
    - `list_display = ["order_number_ui", "customer", "status", "payment_status_ru", "total_amount", "positions", "created_at"]`, `list_display_links = ["order_number_ui"]` — обёртки с русскими подписями (решение 13): `order_number_ui` («Номер», `ordering="order_number"`) → `obj.order_number_display`; `customer` («Клиент», `ordering="user__email"`) → `self.customer_display(obj)`; `payment_status_ru` («Оплата») → `self.payment_status_display(obj)`; `positions` («Позиций») → `self.items_count(obj)`;
    - `list_filter = ["status", "payment_status", "delivery_method"]`, `date_hierarchy = "created_at"` (как у родителя);
    - `search_fields = ["order_number", "user__email", "customer_email", "tracking_number", "user__company_name"]`. `get_search_results` родителя (нормализация UI-номера) наследуется: `base_queryset` в нём — уже выборка раздела, поэтому объединение `queryset | normalized_queryset` чужого не добавляет. Тест AC2 это закрепляет;
    - `actions = ["export_orders_csv"]` и метод `@admin.action(description="Выгрузить выбранные заказы в CSV") def export_orders_csv(self, request, queryset): return self.export_to_csv(request, queryset)` (решение 8). `export_to_csv` родителя декорирован `@admin.action` — это обычный метод, вызывать его напрямую можно;
    - `inlines = [SubOrderInline]`;
    - `fieldsets` — белый список (решение 4):
      ```python
      fieldsets = (
          ("Заказ", {"fields": ("order_number_ui", "order_number", "client_link", "status", "created_at", "updated_at")}),
          ("Контакты из заказа", {"fields": ("customer_name", "customer_email", "customer_phone")}),
          ("Состав и суммы", {"fields": ("items_table", "total_amount", "discount_amount", "delivery_cost")}),
          ("Доставка", {"fields": ("delivery_method", "delivery_address", "delivery_date", "tracking_number")}),
          ("Оплата", {"fields": ("payment_method", "payment_status", "paid_at", "shipped_at", "sent_to_1c_ru")}),
          ("Комментарий", {"fields": ("notes",)}),
      )
      ```
    - `readonly_fields` — всё из fieldsets, кроме `delivery_date`, `tracking_number`, `notes`. `get_readonly_fields` возвращает список целиком, без логики родителя (у родителя он статичен — проверить, что `OrderAdmin` его не переопределяет);
    - `get_fieldsets` → `self.fieldsets` как есть;
    - display-методы: `client_link` («Клиент», решение 12) — `format_html('<a href="{}">{}</a>', reverse(f"{self.admin_site.name}:users_user_change", args=[obj.user_id]), …)`, подпись — email и компания; `items_table` («Состав») — таблица `format_html_join` по позициям: у мастера с субзаказами — позиции всех субзаказов с номером субзаказа, у мастера без субзаказов (legacy) — его собственные. Брать из `obj.sub_orders.all()` и `sub.items.all()` / `obj.items.all()`: `get_object` идёт через `get_queryset`, prefetch родителя уже загрузил их. `_get_order_display_items` (`orders/tasks.py:22`) не использовать: он строит новый запрос с `select_related`, а нужного там нет; `sent_to_1c_ru` («Передан в 1С», `boolean=True`) → `obj.sent_to_1c`;
    - `changelist_view`: `extra_context["title"] = "Заказы"`.
  - [ ] `save_model` (решения 5 и 7):
    ```python
    EDITABLE_FIELDS = ("tracking_number", "delivery_date", "notes")

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
  - [ ] `SubOrderInline(admin.TabularInline)`: `model = Order`, `fk_name = "parent_order"`, `fields = readonly_fields = ("sub_number", "status", "total_amount")`, `sub_number` («Субзаказ») → `obj.order_number_display`; `can_delete = False`, `show_change_link = False`, `extra = 0`; `has_add_permission`, `has_change_permission`, `has_delete_permission` → `False`. `verbose_name = "Субзаказ"`, `verbose_name_plural = "Субзаказы"`. Без `vat_group` (решение 4). Убедиться, что view-only инлайн не ломает POST карточки: форма инлайна без изменяемых полей, `has_changed()` ложно — Django ничего не пишет.

- [ ] **Task 2 — главная со счётчиками** (AC8, AC10, AC11; решения 9–11)
  - [ ] В `apps/orders/manager_admin.py` — `manager_queue(request, site_name) -> list[dict]`:
    - заявки: `scope_clients(request, User.objects.all()).exclude(role=User.ROLE_UNREGISTERED).filter(verification_status="pending").aggregate(count=Count("pk"), oldest=Min("created_at"))` — один запрос;
    - новые заказы: `scope_orders(request, Order.objects.all()).filter(status="pending").count()` — один запрос;
    - ссылки через `reverse(f"{site_name}:users_user_changelist")` и `reverse(f"{site_name}:orders_order_changelist")` с `?verification_status__exact=pending` и `?status__exact=pending`;
    - текст: «Заявки на верификацию: N, старейшая — X <дней>» (при N = 0 — «Заявки на верификацию: 0»), «Новые заказы: N». Дни — `(timezone.now() - oldest).days`, склонение — модульная функция `days_ru(n)` (1 день, 2–4 дня, 5–20 дней, 11–14 дней, 21 день, 111 дней). Готовой в проекте нет.
  - [ ] `ManagerAdminSite.index` (`freesport/admin_site.py`): `from apps.orders.manager_admin import manager_queue` внутри метода (решение 11), `extra_context = {**(extra_context or {}), "manager_queue": manager_queue(request, self.name)}`, затем `super().index(request, extra_context)`. `index` оборачивается `admin_view` в `get_urls` через `self.index`, поэтому проверка доступа идёт до подсчёта.
  - [ ] Шаблон `backend/templates/admin/manager/index.html`: сохранить `{% block sidebar %}{% endblock %}` (решение 13 стори 42.4) и добавить `{% block content %}` — блок очереди (`<div class="module" id="manager-queue">`, таблица со ссылками из `manager_queue`) и затем `{{ block.super }}` (список моделей из проектного `templates/admin/index.html`). Обновить комментарий шаблона: счётчики — 42.5.
  - [ ] Подпись блока «Заказы» на главной не трогать: `verbose_name` приложения и модели уже «Заказы». `ManagerAdminSite.get_app_list` не менять.

- [ ] **Task 3 — тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [ ] `backend/tests/integration/test_manager_orders_section.py` (integration). Хелперы и autouse-фикстуры — явным импортом из `tests.integration.test_manager_clients_section`: `role_groups`, `no_routing_rules`, `verified_email_task`, `make_staff_member`, `make_client`, `form_payload`, `message_texts`, `PASSWORD`, `get_unique_suffix`. **Не `import *`**: тестовые классы модуля собрались бы второй раз. Нового общего модуля хелперов не заводить (правило 42.4). Свои хелперы:
    - `make_master(client, *, status="pending", subs=2, **overrides)` — мастер `Order.objects.create(user=client, is_master=True, …)` с явным каноническим `order_number` (10 цифр: `customer_code` клиента или 5 случайных цифр + `"26"` + 3 цифры; без явного номера `Order.save` ставит UUID, и поиск по UI-номеру не проверить), субзаказы `is_master=False, parent_order=master, user=client, suborder_sequence=i, vat_group=…` и по позиции `OrderItem` в каждом (`ProductFactory` из `tests.factories`, как в `tests/unit/test_orders_admin.py:180`);
    - URL-хелперы `order_change_url`, `order_history_url`, `ORDERS_URL = "/manager/orders/order/"`;
    - `post_order_action(client, action, *orders, **extra)` по образцу `post_action`.
  - [ ] Сценарии:
    - AC1 — матрица входа по `/manager/orders/order/` (как `TestEntry` 42.4) и блок «Заказы» в `response.context["app_list"]` главной.
    - AC2 — параметризация группами «Менеджеры» и «Руководители» (фикстура `section_member` из 42.4 — импортировать или повторить). Набор id в `response.context["cl"].result_list` = мастер-заказы своих клиентов. Заказы сотрудников с `responsible_manager=A` — через `User.objects.filter(pk=…).update(responsible_manager=A)`, по одной записи на каждое условие `staff_accounts_q()`. Заказ `user=None`. Поиск по шести значениям заказа B — пусто, по своим — находится. Заголовки колонок — русские (`label_for_field` или HTML `<th>`).
    - AC3 — GET/POST карточки и `history` заказа B → 404, карточка своего субзаказа → 404; `add` и `delete` своего → 403; после POST заказ B без изменений, `AuditLog` пуст.
    - AC4 — `response.context["adminform"].form.fields` = ровно `{tracking_number, delivery_date, notes}`; readonly-поля по fieldsets; для каждого скрытого поля нет `name="<поле>"` и подписи `verbose_name` в HTML; ссылка клиента `href="/manager/users/user/<id>/change/"`; в «Составе» есть артикулы позиций обоих субзаказов; блок субзаказов без `href` на `/manager/orders/order/<sub_id>/`; нет `addlink`/`deletelink`.
    - AC5 — `BonusProgramSettings.load()` с `is_active=True`, `accrual_status="delivered"`, `program_start_at=None`; клиент `role="trainer"`, `is_verified=True`; POST с подделками. Проверка `update_fields` — `patch.object(Order, "save", autospec=True, side_effect=Order.save)` и разбор `call_args.kwargs["update_fields"]`.
    - AC6 — разобрать CSV (`csv.reader(response.content.decode().splitlines())`): номера только своих заказов; `select_across=1` с пустым `_selected_action` — Django требует непустой `_selected_action` в POST даже при `select_across`, передать любой свой id. В контексте списка `response.context["action_form"].fields["action"].choices` — только наше действие с русской подписью.
    - AC7 — правка одного поля, трёх полей, без изменений (`updated_at` прежний, записей нет). Значения `old`/`new`, дата строкой ISO.
    - AC8 — заявки через `make_client(A, verification_status="pending", is_verified=False, is_active=False, role="wholesale_level1")`, `created_at` — `User.objects.filter(pk=…).update(created_at=timezone.now() - timedelta(days=5, hours=1))`. Текст счётчиков в HTML; переход по каждой ссылке, `cl.result_count` = значение счётчика, id — только записи A. Отдельно — `days_ru` параметризованно (unit) и «0» без «старейшая».
    - AC9 — `group.permissions.set([view_order, view_user])`: в форме нет полей ввода, POST → 403, экспорт работает.
    - AC10 — `'href="/admin/' not in html` для главной (после POST заказа — есть `LogEntry`), списка, карточки, истории; `response.url` после `_save` и `_continue`.
    - AC11 — `CaptureQueriesContext` / `django_assert_num_queries`: 5 мастер-заказов → baseline, ещё 45 → тот же счёт (образец — `TestChangelistQueryCount` 42.4). Главная — 3 и 30 заявок/заказов.
  - [ ] `backend/tests/unit/test_manager_orders_admin.py` (unit, `RequestFactory`): `scope_orders` (свой мастер, свой субзаказ, чужой, без клиента, заказ сотрудника); `days_ru`; `manager_queue` на пустых данных (0 и без «старейшая»); `ManagerOrderAdmin.get_readonly_fields`/`get_fieldsets` не содержат скрытых полей (страж белого списка); регистрация: `manager_site._registry[Order]` — экземпляр `ManagerOrderAdmin`, а `admin.site._registry[Order]` — по-прежнему `OrderAdmin`.
  - [ ] **Тесты транзакционные** (как в 42.4): autouse `clear_db_before_test(transactional_db)` в `tests/conftest.py`, после теста `flush`; правки прав группы внутри теста не откатываются, их стирает `flush`, а `role_groups` следующего теста создаёт группы заново. `ATOMIC_REQUESTS=True` только в тестовых настройках.
  - [ ] **Проверка мутациями** — по каждой защите временно убрать её, убедиться, что падает названный тест, вернуть. Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | `is_master=True` в `scope_orders` | AC2 (субзаказы в списке), AC3 (карточка субзаказа) |
    | `user__in=scope_clients(...)` → `user__responsible_manager=request.user` | AC2, записи сотрудников |
    | `_get_obj_does_not_exist_redirect` → `Http404` | AC3 |
    | `update_fields` в `save_model` → `super().save_model(...)` | AC5, проверка `update_fields` |
    | `"status"` добавлен в правимые поля (из `readonly_fields` убран) и в `EDITABLE_FIELDS` | AC5, статус и бонус |
    | ранний `return` при пустом `changed` | AC7, сохранение без изменений |
    | `exclude(role=ROLE_UNREGISTERED)` в счётчике заявок | AC8, равенство счётчика и списка (добавить в данные `unregistered` с `pending`) |
    | `index_template`/`block sidebar` в шаблоне | AC10, главная после правки |

- [ ] **Task 4 — существующие тесты: без правок**
  - [ ] Прогнать и убедиться, что зелёные без изменений: `tests/unit/test_orders_admin.py` (`/admin/` не тронут), `tests/integration/test_manager_clients_section.py` (главная теперь с блоком очереди: `TestLinksStayInSection`, `test_index_names_block_clients`), `tests/unit/test_manager_admin_site.py`, `apps/bonuses/tests/test_admin.py`, тесты импорта статусов (`tests/integration/test_order_status_import_db.py`).
  - [ ] Если `test_manager_admin_site.py` проверяет число запросов главной или её контекст — счётчики добавят ровно два запроса; правка ожиданий — только с записью в Completion Notes как отклонение.

- [ ] **Task 5 — проверки и закрытие**
  - [ ] Полный backend-прогон в Docker, один compose-проект: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` (~16 мин, ориентир после 42.4 — 4201 passed, 76 skipped). Запускать в фоне.
  - [ ] Линтеры строго после зачётного pytest, в том же `-p freesport-test` (проект `freesport-lint` не поднимается при живом `freesport-test`): `black --check .`, `isort --check-only .`, `flake8`, `mypy`. Любая ошибка — новая.
  - [ ] `makemigrations --check --dry-run` — миграций нет. `check_openapi_sync` не нужен: API не меняется.
  - [ ] Nginx не меняется (`/manager/` проксируется с 42.4). Smoke `scripts/deploy/check-manager-*.sh` не меняются.
  - [ ] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [ ] Completion Notes: отклонения от стори с причиной, ответы Alex на вопросы ниже (если получены до разработки).

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

`notes` — **комментарий клиента при оформлении** (`OrderCreateSerializer.Meta.fields`, `orders/serializers.py:183`). Клиент видит его в личном кабинете в карточке «Примечания» (`frontend/src/components/business/OrderDetail/OrderDetail.tsx:249`), туда же уходит `tracking_number` (`:201`). Субзаказы получают копию `notes` и `delivery_date` при создании (`order_create.py:128-130`) и после правки мастера не обновляются — в 1С `notes` и трек-номер не выгружаются (`order_export.py` их не читает). Значит, правка менеджера в `notes` **заменяет текст клиента и видна клиенту**; исходный текст остаётся в `AuditLog` (`old`) и в субзаказах. Стори делает ровно то, что задано спецификацией; вопрос Alex — в конце.

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

- **42.7** снимает фильтр для руководителя: меняет `scope_clients` и `scope_orders` (заказы без клиента — только руководителю, FR-42-24). Счётчики главной у руководителя тогда покажут весь отдел — это ожидаемо.
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

## Вопросы к Alex (не блокируют разработку)

1. **«Новые заказы» = статус `pending`** (решение 9). Альтернатива — «созданы за последние N дней». Если заказы подолгу висят в «Не согласован», счётчик будет копиться. Оставить `pending`?
2. **Комментарий заказа — текст клиента** (раздел «Чей это комментарий»). Менеджер, правя его, заменяет то, что написал клиент, и клиент это видит. Так и задумано, или менеджеру нужно отдельное внутреннее поле (новая колонка и миграция, отдельная стори)?
3. **CSV — английские заголовки и UTF-8 без BOM**, как в `/admin/`. Excel на Windows откроет кириллицу кракозябрами. Перевести заголовки и добавить BOM для раздела менеджера (небольшая правка в этой стори) или оставить как есть?

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

### Change Log

- 2026-10-15 — стори создана (`bmad-create-story`), статус `ready-for-dev`.
