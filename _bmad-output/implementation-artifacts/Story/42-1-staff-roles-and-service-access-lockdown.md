---
baseline_commit: c8907d17
---

# Story 42.1: Роли сотрудников и закрытие служебного доступа

Status: in-progress
Baseline Revision: c8907d17

## Story

As a владелец сайта,
I want выдавать сотрудникам учётные записи с ролями «Менеджер», «Маркетинг» и «Руководитель»,
so that сотрудник не получил вместе с ними доступ к обмену с 1С, запуску импорта, основной админке и способ сделать себя суперпользователем.

**Закрывает:** FR-42-01, FR-42-02, FR-42-03, FR-42-04. **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.1), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-1).

Это жёсткое предусловие всего эпика: пока `is_staff` открывает обмен 1С и `/admin/`, учётные записи сотрудникам выдавать нельзя. Разделов `/manager/`, `/marketing/` в этой стори **нет** — они появятся в 42.4–42.7.

## Утверждённые решения (не пересматривать)

1. **Основная `/admin/` — только суперпользователю.** Сотрудник с `is_staff=True` без `is_superuser` получает отказ на любой странице `/admin/…`, включая `/admin/monitoring/` и `/admin/integrations/import_1c/`. Отказ — штатное поведение `AdminSite.admin_view`: 302 на `/admin/login/?next=…`.
2. **Обмен 1С — только по праву `integrations.can_exchange_1c`** (суперпользователь проходит автоматически: `has_perm` у активного суперпользователя всегда `True`). Ветка `is_staff` из `Is1CExchangeUser` удаляется **без подготовки**: на проде обмен ходит под `1c_exchange_robot@freesport.ru` (id 17) — `is_staff=false`, `can_exchange_1c` выдано напрямую (проверено 08.10.2026, action_item эпика 42 закрыт).
3. **Страница запуска импорта, API метрик синхронизации, `include_inactive` — только суперпользователю.** Отдельного права для них не вводится.
4. **Группа «Менеджер» (id 1 на проде) переиспользуется:** миграция переименовывает её в «Менеджеры» и **заменяет** её права набором роли, участников сохраняет. Второй группы с похожим именем не появляется.
5. **Повторный прогон миграции идемпотентен:** не создаёт дублей и не отнимает права, выданные целевой группе вручную (для уже существующей «Менеджеры»/«Маркетинг»/«Руководители» недостающие права роли **добавляются**, лишние не удаляются). «Замена» прав — только при переименовании старой группы «Менеджер».
6. **Прямые права сотрудников (`user_permissions`) миграция не трогает.** `managermsk3@freesportopt.ru` (id 15, `is_staff=true`, `role=admin`, прямые права) после стори теряет `/admin/`; по решению 8 он руководитель.
7. **`alexmw2006@yandex.ru` — суперпользователь** (решение Alex 08.10.2026). Это делается ручным шагом на проде **до** выката 42.1 (см. «Выкат», шаг 2), а не миграцией: data-миграция не выдаёт `is_superuser` по email. На этом же шаге запись выводится из группы «Менеджер»: суперпользователю членство в группе прав не добавляет, а в 42.2+ состав «Менеджеры» означает «менеджер по продажам» (списки выбора ответственного и правил регионов). **Выполнено 08.10.2026.**
8. **`managermsk3@freesportopt.ru` (id 15, Виктор Чернов) — руководитель** (решение Alex 08.10.2026). Ручной шаг **после** выката 42.1 (группа «Руководители» появляется только с миграцией `0023`): добавить в «Руководители» и снять прямые права — все 10 входят в набор роли, а доступ сотрудника должен определяться только группой. Миграция по email ничего не назначает. Между выкатами 42.1 и 42.7 своего раздела у него нет: `/admin/` закрыта, последний вход — 2026-04-13, так что потеря доступа на этот период приемлема.

## Acceptance Criteria

### AC1 — группы трёх ролей создаются миграцией

**Given** база без групп ролей
**When** выполняется прямая функция data-миграции `0023_staff_role_groups`
**Then** существуют ровно по одной группе «Менеджеры», «Маркетинг», «Руководители», и набор прав каждой совпадает с константой миграции (таблица «Наборы прав» ниже)
**And** повторный вызов функции не создаёт дублей и не теряет право, добавленное группе вручную между вызовами

### AC2 — `/admin/` только суперпользователю

**Given** сотрудник любой из трёх ролей (`is_staff=True`, член группы роли, не суперпользователь)
**When** он открывает `/admin/`, `/admin/users/user/`, `/admin/users/user/<id>/change/`, `/admin/users/user/<id>/verify/`, `/admin/users/user/<id>/password/`, `/admin/monitoring/` или `/admin/integrations/import_1c/`
**Then** каждая отвечает 302 на `/admin/login/`, а не содержимым
**And** суперпользователь открывает те же страницы с кодом 200, как раньше
**And** анонимный запрос к `/admin/monitoring/` отвечает 302 на вход (сегодня дашборд отдаётся без проверки — см. Dev Notes, «Найденная дыра»)

### AC3 — служебный доступ не по `is_staff`

**Given** сотрудник любой из трёх ролей
**When** он обращается к API обмена 1С (`/api/integration/1c/exchange/?mode=checkauth`), к странице запуска импорта `/api/integration/import_1c/`, к четырём API метрик синхронизации (`/api/v1/monitoring/metrics/{operations,business,realtime}/`, `/api/v1/monitoring/health/`) или к фильтрам каталога `/api/v1/catalog/filters/?include_inactive=true` (`AttributeFilterViewSet`, `products/views.py:515`)
**Then** обмен отвечает 403, страница импорта — 302 на `/admin/login/`, метрики — 403, а фильтры каталога не содержат неактивных атрибутов
**And** учётная запись с правом `integrations.can_exchange_1c` и `is_staff=False` проходит `checkauth` обмена как прежде (NFR-42-05)
**And** суперпользователь по-прежнему получает метрики (200) и неактивные атрибуты

### AC4 — нет пути эскалации через форму пользователя

**Given** пользователь с правом `users.change_user`, не суперпользователь
**When** для него строятся форма и fieldsets `UserAdmin` (через `get_fieldsets`/`get_form`), в том числе с подделанными данными `is_superuser=on`, `is_staff=on`, `groups=[…]`, `user_permissions=[…]`
**Then** этих полей в форме нет, а сохранённый объект их значений не меняет
**And** такой пользователь не может изменить, удалить или сменить пароль суперпользователю (`has_change_permission`/`has_delete_permission` → `False` для цели-суперпользователя)
**And** через `/admin/` тот же подделанный POST отвечает 302 на вход, данные не меняются
**And** суперпользователь по-прежнему видит и правит `is_staff`, `is_superuser`, `groups`, `user_permissions`

### AC5 — переиспользование группы «Менеджер»

**Given** в базе есть группа «Менеджер» с произвольным набором прав и участником
**When** выполняется функция миграции
**Then** группа (тот же `pk`) переименована в «Менеджеры», её права равны набору роли, участник сохранён
**And** группы «Менеджер» больше нет, второй группы с похожим именем не появилось
**And** если одновременно существуют «Менеджер» и «Менеджеры», участники «Менеджер» перенесены в «Менеджеры», а «Менеджер» удалена

### AC6 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `flake8`, `black --check`, `mypy` и `check_openapi_sync`
**Then** всё зелёное; изменены только ожидания тестов, прямо перечисленные в Task 7

## Наборы прав (константа миграции)

Права — модельный «грубый» слой. Поля и строки скрывают урезанные представления стори 42.4–42.7. Если последующей стори понадобится другое право — она добавляет **свою** миграцию; править `0023` после выката нельзя.

| Группа | Права (`app_label.codename`) |
|---|---|
| **Менеджеры** | `users.view_user`, `users.change_user`, `users.view_company`, `users.change_company`, `users.view_address`, `users.add_address`, `users.change_address`, `users.delete_address`, `orders.view_order`, `orders.change_order`, `orders.view_orderitem` |
| **Маркетинг** | `banners.view_banner`, `banners.add_banner`, `banners.change_banner`, `banners.delete_banner`; `common.{view,add,change,delete}_news`, `common.{view,add,change,delete}_blogpost`, `common.{view,add,change,delete}_category`; `products.view_product`, `products.change_product`, `products.view_brand`, `products.change_brand`, `products.view_homepagecategory`, `products.change_homepagecategory` |
| **Руководители** | всё из «Менеджеры» и «Маркетинг», плюс `users.add_user`; `common.{view,add,change,delete}_notificationrecipient`, `common.{view,add,change,delete}_managerroutingrule`, `common.view_auditlog`; `bonuses.view_bonusprogramsettings`, `bonuses.change_bonusprogramsettings`, `bonuses.view_bonustransaction` |

Не выдаётся никому из трёх групп (`section-contents.md`, «Ни одной из ролей»): `auth.*` (группы и права), `integrations.*` (в т. ч. `can_exchange_1c`), `common.newsletter`, `common.synclog`, `common.customersynclog`, `common.syncconflict`, `common.userconsent`, `pages.*`, `delivery.*`, `cart.*`, `users.favorite`, `users.delete_user`, `products.{productvariant,productimage,attribute,attributevalue,brand1cmapping,attribute1cmapping,attributevalue1cmapping,onecexcludeditem,pricetype,colormapping,importsession,category}`, `orders.delete_order`.

`products.HomepageCategory` — proxy-модель `products.Category` (`products/models.py:252`): права proxy создаются на content type самого proxy (`products.change_homepagecategory`), права `products.change_category` маркетингу **не** даются.

## Tasks / Subtasks

- [ ] **Task 0 — GitNexus pre-flight** (обязательно, AGENTS.md)
  - [ ] `npx gitnexus status`; при `stale` попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md` (на `c8907d17` индекс отставал только на docs-коммиты).
  - [ ] `impact --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по: `Is1CExchangeUser`, `UserAdmin`, `import_from_1c_view`, `monitoring_dashboard_view`, `operation_metrics`, `business_metrics`, `system_health`, `realtime_metrics`, `AttributeFilterViewSet` (`products/views.py:481`). На `c8907d17`: `Is1CExchangeUser` — LOW (1 файл, `onec_exchange/views.py:197`), `UserAdmin` — LOW (0 вызывающих). HIGH/CRITICAL — сообщить Alex до правок.

- [ ] **Task 1 — константы ролей** (AC1, AC5)
  - [ ] Новый модуль `backend/apps/users/staff_roles.py`: `MANAGERS_GROUP = "Менеджеры"`, `MARKETING_GROUP = "Маркетинг"`, `SUPERVISORS_GROUP = "Руководители"`, `STAFF_ROLE_GROUPS = (MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP)`. Docstring — на русском, что это имена групп ролей эпика 42 и что наборы прав зафиксированы в миграции `0023`. Модуль понадобится 42.2+ (исключение сотрудников из автоназначения), поэтому имена — здесь, а не только в миграции.
  - [ ] **Наборы прав в модуль не выносить:** миграция хранит свою замороженную копию (миграции не импортируют изменяемый код приложения). Имена групп в миграции тоже литералами.

- [ ] **Task 2 — data-миграция `apps/users/migrations/0023_staff_role_groups.py`** (AC1, AC5)
  - [ ] `dependencies`: `("users", "0022_alter_user_country")`, `("auth", "0012_alter_user_first_name_max_length")`, `("contenttypes", "0002_remove_content_type_name")`, `("orders", "0016_customercodesequence")`, `("banners", "0007_banner_ad_disclosure")`, `("common", "0021_newsletter_unsubscribe_token")`, `("products", "0056_onec_deleted_and_excluded_items")`, `("bonuses", "0003_bonus_journal_survives_deletion")`. Проверить актуальность последних миграций этих приложений на момент работы (`ls apps/<app>/migrations`).
  - [ ] Константа `ROLE_PERMISSIONS: dict[str, tuple[str, ...]]` — ровно таблица «Наборы прав» (строки `"app_label.codename"`); набор «Руководители» собрать как объединение двух других плюс свои — без копипасты.
  - [ ] `LEGACY_NAMES = {"Менеджеры": ("Менеджер",)}`.
  - [ ] **Права в чистой БД ещё не существуют** во время миграций: `post_migrate` (`create_permissions`) срабатывает после всех миграций. Перед поиском прав вызвать для каждого затронутого приложения
    ```python
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for label in ("users", "orders", "banners", "common", "products", "bonuses"):
        create_permissions(global_apps.get_app_config(label), verbosity=0, apps=apps, using=alias)
    ```
    (передаётся **глобальный** `app_config` — у него заполнен `models_module`, иначе функция молча выходит; `apps=apps` — историческое состояние). `create_permissions` сам создаёт недостающие content types.
  - [ ] Поиск права: `Permission.objects.get(content_type__app_label=…, codename=…)`. Ненайденное право — **исключение**, не тихий пропуск: опечатка в наборе должна ронять миграцию и тест.
  - [ ] Алгоритм по каждой роли:
    1. `target = Group.objects.filter(name=role).first()`, `legacy = Group.objects.filter(name__in=LEGACY_NAMES.get(role, ())).first()`.
    2. Нет `target`, есть `legacy` → `legacy.name = role; save()`; `legacy.permissions.set(perms)` (замена — решение 4).
    3. Есть и `target`, и `legacy` → `target.user_set.add(*legacy.user_set.all())`; `legacy.delete()`; `target.permissions.add(*perms)`.
    4. Нет ни того ни другого → `Group.objects.create(name=role)`; `permissions.set(perms)`.
    5. Есть только `target` → `target.permissions.add(*perms)` (ручные права не трогаем — решение 5).
  - [ ] `alias = schema_editor.connection.alias`; все запросы через `.using(alias)` не обязательны (одна БД), но `create_permissions(using=alias)` — да.
  - [ ] Обратная миграция — `migrations.RunPython.noop`: откат не удаляет группы и членство (оно могло быть выдано вручную).
  - [ ] Функцию вперёд назвать `create_staff_role_groups(apps, schema_editor)` — тест вызывает её напрямую.

- [ ] **Task 3 — `/admin/` только суперпользователю** (AC2)
  - [ ] Новый модуль `backend/freesport/admin_site.py`: `class SuperuserAdminSite(admin.AdminSite)` с `has_permission(self, request) -> bool: return request.user.is_active and request.user.is_superuser`. Docstring: почему (эпик 42, `is_staff` теперь означает «сотрудник», а не «администратор»).
  - [ ] Новый модуль `backend/freesport/apps.py`: `class FreesportAdminConfig(AdminConfig): default_site = "freesport.admin_site.SuperuserAdminSite"`. В `freesport/settings/base.py` в `DJANGO_APPS` заменить `"django.contrib.admin"` на `"freesport.apps.FreesportAdminConfig"` (рецепт из документации Django «Overriding the default admin site»). **Не класть `AdminConfig`-подкласс в `apps/common/apps.py`:** при двух подклассах `AppConfig` в модуле Django перестанет автоматически выбирать `CommonConfig` для `"apps.common"`.
  - [ ] Проверить, что всё продолжает регистрироваться: `admin.site` — `DefaultAdminSite` (lazy), он возьмёт новый класс; `@admin.register(...)`, заголовки в `integrations/admin.py:9-11` и monkey-patch `get_urls` в `integrations/admin_urls.py` работают с экземпляром любого подкласса.
  - [ ] **Монки-патч `admin.site.has_permission` не использовать** — только подкласс сайта.
  - [ ] `backend/freesport/urls.py:41-45`: обернуть дашборд — `admin.site.admin_view(monitoring_dashboard_view)`. Это закрывает и анонимный доступ (AC2, «Найденная дыра»).

- [ ] **Task 4 — обмен, импорт, метрики, `include_inactive`** (AC3)
  - [ ] `integrations/onec_exchange/permissions.py`: `return request.user.is_authenticated and request.user.has_perm("integrations.can_exchange_1c")`. Docstring класса — на русском: доступ по праву, суперпользователь проходит через `has_perm`, `is_staff` доступа не даёт (эпик 42).
  - [ ] `integrations/views.py:16,29`: заменить `@staff_member_required` на проверку суперпользователя с тем же поведением отказа (редирект на `admin:login` с `next`):
    ```python
    from django.contrib.auth.decorators import user_passes_test
    superuser_required = user_passes_test(lambda u: u.is_active and u.is_superuser, login_url="admin:login")
    ```
    Вью доступна по двум адресам: `/admin/integrations/import_1c/` (через `admin.site.admin_view` в `admin_urls.py` — уже станет superuser-only после Task 3) и `/api/integration/import_1c/` (`integrations/urls.py:12` — защищена **только** декоратором). Декоратор обязателен именно для второго адреса.
  - [ ] `common/views.py:22,146,218,277,310`: `IsAdminUser` → новый класс `IsSuperUser` (DRF `BasePermission`: `bool(request.user and request.user.is_authenticated and request.user.is_superuser)`). Положить в новый `apps/common/permissions.py` (модуля ещё нет). Импорт `IsAdminUser` убрать, если больше не используется.
  - [ ] `products/views.py:515`: `self.request.user.is_staff` → `self.request.user.is_superuser`; комментарий `# Staff users…` и docstring (`:503-507`) — «суперпользователь». Описание параметра в `extend_schema` (`products/views.py:~532`): «Включить неактивные атрибуты (только для суперпользователя). Для остальных пользователей параметр игнорируется.»
  - [ ] Синхронизировать `docs/api/openapi.yaml:1632` и `:1677` с новым описанием (NFR-42-06) и прогнать `check_openapi_sync` (рецепт — Dev Notes). Пути `/monitoring/*` в контракте есть (`openapi.yaml:22-77`), но смена класса прав схему не меняет — проверить это тем же `check_openapi_sync`.

- [ ] **Task 5 — закрыть эскалацию в `UserAdmin`** (AC4)
  - [ ] Константа класса `PRIVILEGE_FIELDS = ("is_staff", "is_superuser", "groups", "user_permissions")`.
  - [ ] `get_fieldsets` (`users/admin.py:~388`): для `not request.user.is_superuser` вычищать `PRIVILEGE_FIELDS` из всех fieldsets и выбрасывать опустевшие fieldsets («Права доступа» исчезает целиком; в «Роль и статус» остаются `role`, `is_active`). Сохранить существующую логику скрытия `onec_link_candidates`. Поскольку `ModelAdmin.get_form` берёт поля из `get_fieldsets`, поля пропадут и из формы — подделанный POST их не тронет (m2m `groups`/`user_permissions` вне формы `save_m2m` не трогает).
  - [ ] `list_filter` (`"is_staff"`) не трогать — это не форма.
  - [ ] `has_change_permission(request, obj=None)` и `has_delete_permission(request, obj=None)`: если `obj is not None and obj.is_superuser and not request.user.is_superuser` → `False`, иначе `super()`. Это закрывает смену пароля суперпользователю (`BaseUserAdmin.user_change_password` проверяет `has_change_permission`), страницу подтверждения B2B и правку карточки.
  - [ ] Ничего больше в `UserAdmin` не менять: действия, `verify_b2b_view`, `user_change_password` с `AuditLog`, инлайны остаются как есть (их урезанные версии — 42.4).

- [ ] **Task 6 — новые тесты** (AC1–AC5, NFR-42-02 — у каждой проверки доступа негативный тест)
  - [ ] `backend/tests/unit/test_staff_role_groups_migration.py` (unit, `django_db`): модуль миграции грузить через `importlib.import_module("apps.users.migrations.0023_staff_role_groups")`, вызывать `create_staff_role_groups(django.apps.apps, SimpleNamespace(connection=connection))`. Autouse-фикстура удаляет группы `STAFF_ROLE_GROUPS` и «Менеджер» перед тестом (данные data-миграции в тестовой БД могут быть, а могут быть стёрты `flush` транзакционных тестов — тест не должен зависеть ни от того, ни от другого). Сценарии:
    - чистая база → три группы, `set(codenames) == ROLE_PERMISSIONS[...]` для каждой;
    - повторный вызов → по одной группе каждого имени; право, добавленное вручную между вызовами, на месте;
    - «Менеджер» c чужим правом (например `pages.change_page`) и участником → тот же `pk`, имя «Менеджеры», права ровно набор роли, участник в группе, «Менеджер» нет;
    - «Менеджер» и «Менеджеры» одновременно → участник перенесён, «Менеджер» удалена;
    - ни одна группа не содержит `integrations.can_exchange_1c` и права `auth.*`.
  - [ ] `backend/tests/integration/test_staff_access_lockdown.py` (integration): фикстура `staff_member(group_name)` — `is_staff=True`, член группы роли (группы создавать через функцию миграции или `Group.objects.get_or_create` + функцию — по тому же правилу независимости от состояния БД). Параметризация по трём ролям:
    - AC2: все URL из AC2 → 302, `"/admin/login/" in response.url`; суперпользователь → 200 (для `/verify/` и `/password/` — целевой B2B-пользователь с ожидающей заявкой, как в `test_admin_verify_b2b_application.py`, либо проверить «не 302 на вход»); аноним `/admin/monitoring/` → 302.
    - AC3: `checkauth` обмена с Basic-авторизацией сотрудника → 403; `/api/integration/import_1c/` → 302 на `/admin/login/`; четыре метрики → 403, суперпользователь → 200 (у `health` при нездоровой системе возможен 503 — мокать `CustomerSyncMonitor` или проверять `!= 403`); `include_inactive=true` от сотрудника — неактивного атрибута нет, от суперпользователя — есть.
  - [ ] `backend/tests/unit/test_users_admin.py` (дописать) — AC4: `RequestFactory` + `UserAdmin(User, admin.site)`; запросчик — `is_staff=True` с правами `view_user`, `change_user`, не суперпользователь:
    - `flatten_fieldsets(get_fieldsets(request, obj))` не содержит ни одного из `PRIVILEGE_FIELDS`; у суперпользователя — содержит все четыре;
    - `get_form(request, obj)` с подделанными данными (`is_superuser="on"`, `is_staff="on"`, `groups=[group.pk]`, `user_permissions=[perm.pk]`) → после `form.save(); form.save_m2m()` у цели флаги и m2m не изменились (данные формы собрать из `model_to_dict`/initial, чтобы форма была валидной);
    - `has_change_permission`/`has_delete_permission` для цели-суперпользователя → `False`, для обычного клиента → `True`; у запросчика-суперпользователя → `True`.
  - [ ] `Is1CExchangeUser` — юнит-тест класса (в `tests/unit/`): аноним → `False`; `is_staff=True` без права → `False`; право без `is_staff` → `True`; суперпользователь → `True`.

- [ ] **Task 7 — починить существующие тесты, завязанные на `is_staff`** (AC6)
  Источник списка — `grep -rln "is_staff=True\|is_staff = True" backend/tests backend/apps` на `c8907d17`. Менять **только** перечисленное:
  - [ ] **Фикстуры «технического пользователя 1С» с `is_staff=True` без права** — выдать `integrations.can_exchange_1c` (как на проде; `is_staff=True` убрать — ровно так выглядит робот обмена): `tests/integration/test_onec_exchange_api.py` (фикстуры `:38`, `:132`, `:300`), `test_1c_file_routing.py:47`, `test_1c_file_upload.py`, `test_onec_exchange_info_mode.py`, `test_onec_export.py`, `test_onec_export_e2e.py`, `test_onec_import.py:99`, `test_orders_xml_mode_file.py`, `test_order_exchange_import_e2e.py`, `apps/integrations/tests/test_handle_init_cleanup_race.py`, `apps/integrations/tests/test_import_orchestration_view.py:20` (комментарий «Required for Is1CExchangeUser permission» исправить), `apps/products/tests/integration/test_import_orchestration.py`. Если в файле несколько фикстур — общий хелпер в пределах файла, не новый глобальный модуль. Добавить в `test_onec_exchange_api.py` негатив: `is_staff=True` без права → 403.
  - [ ] `apps/products/tests/test_api_attributes.py:37` — фикстура `staff_user` для позитива `include_inactive` → суперпользователь; сам `is_staff`-пользователь становится негативным случаем (неактивных нет).
  - [ ] `tests/integration/test_admin_user_password.py:215` `test_password_form_requires_change_permission` — ожидание `403` → `302` на `/admin/login/` (сотрудник отсекается сайтом раньше проверки права); проверка «пароль не изменился» остаётся.
  - [ ] `tests/integration/test_admin_link_1c_customer.py:226` `test_action_requires_change_user_permission` — негативная часть: данные не изменились, `AuditLog` нет (статус после `follow=True` — страница входа). **Позитивный контроль** (`:260-276`, тот же сотрудник с `change_user`) больше невозможен в `/admin/`: заменить на тот же payload от суперпользователя (`manager_client`), сохранив смысл «действие рабочее, а не опечатка в `actions`».
  - [ ] `tests/integration/test_admin_verify_b2b_application.py` `make_staff` (`:131`) и тесты `:442-455`, `:479-485`: `view_user`-сотрудник → 302 на вход (было 403/200); `view_user+change_user`-сотрудник → 302 на вход (было 200). Логика «страница подтверждения требует `change_user`» вернётся тестами раздела менеджера в 42.4 — оставить у теста комментарий со ссылкой на 42.4.
  - [ ] Тесты, где пользователь уже `create_superuser`/`is_superuser=True` (`test_import_page_integration.py`, `test_integrations_views.py`, `test_admin/test_products_admin.py`, `tests/conftest.py:561`, `test_monitoring_api.py`), трогать не нужно — прогнать и убедиться.
  - [ ] После правок: `grep -rn "is_staff=True" backend/tests backend/apps` — каждое оставшееся вхождение либо суперпользователь, либо осознанный негативный случай.

- [ ] **Task 8 — проверки и закрытие**
  - [ ] Полный backend-прогон в Docker (один compose-проект, без параллельных прогонов): `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest`.
  - [ ] Линтеры — навык `backend-lint` или в `freesport-lint` (не параллельно с зачётным pytest).
  - [ ] `check_openapi_sync` (рецепт — Dev Notes).
  - [ ] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [ ] В Completion Notes — список учётных записей, которые потеряют `/admin/` на проде (SQL в «Выкат»), чтобы Alex решил их судьбу до выката.

### Замечания ревью — 09.10.2026

Диапазон: `c8907d17..2620716`, режим `full`. Независимые проверки: слепое ревью (BH), граничные случаи (ECH), пробелы в проверках (VG), аудит приёмки (AA). Все четыре завершены. После проверки: 0 решений владельца, 1 исправление, 3 отложенных пункта, 23 отклонённых замечания. Обхода служебного доступа в текущих маршрутах не подтверждено.

- [ ] [Review][Patch] **AA4, low — изменённая фраза ADR написана на английском.** `docs/decisions/ADR-009-csrf-exemption-1c-protocol.md:26`: описание нового правила `can_exchange_1c` нарушает требование вести документацию на русском. Перевести изменённый пункт без изменения смысла и без переписывания остального ADR.
- [x] [Review][Defer] **BH9 + AA1, medium — общий Black/mypy не проходят, буквальный AC6 не закрыт.** Проверено в Docker: `black --check .` требует форматирования `backend/tests/unit/test_pytest_marker_autotagging.py`; `mypy --config-file=mypy.ini .` выдаёт 16 ошибок в `apps/products/tests/unit/test_variant_import_admission.py` и `test_variant_import_error_paths.py`. Все три файла не изменены относительно baseline. Отложено как ранее существовавший долг, не регрессия 42.1; не считать эти проверки зелёными.
- [x] [Review][Defer] **VG1, medium — проверки `change_user` внутри UserAdmin потеряли достижимые HTTP-тесты.** Отказы B2B-подтверждения, действия привязки, смены пароля и видимость кнопки теперь скрыты за отказом сайта. Уже учтено в `deferred-work.md:901-903` и Task 7: вернуть тесты в 42.4 до переиспользования UserAdmin в разделе менеджера. Защита суперпользователя-цели при прямом вызове методов покрыта unit-тестом.
- [x] [Review][Defer] **BH10, low — инвариант служебного доступа не записан в контексте агента.** Уже учтено в `deferred-work.md:904-906`: закрепить в AGENTS.md, что `is_staff` означает сотрудника, а служебный доступ проверяется по `is_superuser` или конкретному праву. Изменение контекста агента отложено; текущей открытой служебной вью не обнаружено.

**Повторная проверка:** целевые четыре файла pytest — 91 passed; Flake8 — код 0; `check_openapi_sync` — контракт синхронен; общий Black и mypy — код 1 по ранее существовавшим проблемам выше. Полный backend-набор в этом ревью повторно не запускался; 3838 passed в Dev Agent Record — результат реализации, не нового ревью. Точечный GitNexus impact по девяти символам Task 0 — LOW; анализ диапазона — 36 символов, 14 потоков, совокупный риск high.

**Решение владельца 09.10.2026:** вариант 2 — оставить единственное исправление AA4 задачей, не применять перевод ADR в этом запуске. Замечание остаётся открытым. Статус story и sprint tracking: `in-progress`.

#### Отклонённые замечания

- BH1 — false: неактивный суперпользователь не проходит используемые JWT/session-классы аутентификации; отсутствие `is_active` в IsSuperUser не даёт описанного HTTP-доступа.
- BH2 — false: Basic1CAuthentication наследует стандартную DRF BasicAuthentication, отвергающую неактивного пользователя; session-аутентификация также его отвергает.
- BH3 — false: AC4 не требует отдельного подделанного POST каждой роли; отказ сайта одинаков для всех трёх, что проверено параметризованным тестом AC2.
- BH4 — false: требуемые отказы IsSuperUser проверены интеграционно на всех четырёх API; отдельный unit-файл сам по себе не закрывает обнаруженную дыру, которой здесь нет.
- BH5 — false: локальная фикстура manager в `test_admin_link_1c_customer.py:72-78` действительно создаёт суперпользователя, позитивный контроль достижим.
- BH6 — false: Permission остаётся используемым, в том числе при выдаче view_user в `test_admin_link_1c_customer.py:238`; повторный Flake8 завершается успешно.
- BH7 — false: все семь URL AC2 покрыты; дополнительные password_change/changelist-действия защищены тем же admin_view. Действие привязки дополнительно проверяется изменённым тестом Task 7.
- BH8 — false: baseline story, baseline реализации и коммит последнего изменения кода относятся к разным этапам; выбранный диапазон однозначно задан frontmatter story, потери кода из ревью нет.
- BH11 — false: has_view_permission и массовые операции сотрудников недостижимы на текущем /admin/; просмотр суперпользователя не запрещён AC4, новые разделы вне этой стори.
- BH12 — false: четыре набора метрик вычислялись и до изменения; доступ теперь ограничен суперпользователем, увеличения доступной анониму нагрузки нет.
- BH13 — false: описание monitoring не обещает доступ сотрудникам; AC требует сохранения синхронности схемы, повторный check_openapi_sync проходит. Отсутствие нового описания 403 не подтверждает регрессию контракта.
- BH14 — false: длина строки соответствует лимиту 120, повторный Flake8 проходит; Black изменённый UserAdmin не отклоняет.
- BH15 — false: Is1CExchangeUser проверяет право независимо от staff; отсутствие отдельного сочетания staff+право в тестах не подтверждает ошибочного отказа.
- ECH1 — false: /admin/ не допускает не-суперпользователя, группы ролей не получают delete_user, block_users уже пропускает суперпользователей. Предполагаемый новый AdminSite не существует в 42.1.
- ECH2 — false: role намеренно оставлена по Task 5; сотрудник не достигает формы через /admin/, а readonly-поля будущего раздела входят в 42.4.
- ECH3 — false: запрет просмотра суперпользователя не входит в AC4, текущий сайт всё равно не пропускает сотрудника.
- ECH4 — false: коллизия app_label/codename в текущих данных не показана; Django модельные права используют имя модели, а неизвестное или неоднозначное право должно прерывать миграцию.
- ECH5 — false: перенос только участников legacy и сохранение ручных прав target — утверждённый алгоритм Task 2; сохранение прав старой «Менеджер» противоречило бы замене её полномочий.
- ECH6 — false: в действующем urls дашборд обёрнут admin.site.admin_view; другого незащищённого подключения не обнаружено.
- ECH7 — false: заявленный запрет изменения/удаления суперпользователя соблюдается текущим сайтом и пообъектными методами; массовые действия на гипотетическом будущем сайте не опровергают текущую реализацию.
- VG2 — false: название старой фикстуры manager не меняет создаваемого суперпользователя; неверного позитивного контроля нет, названный вред относится лишь к возможному будущему копированию.
- AA2 — false: each_context возвращает штатную шапку и инструменты админки, не меняет защиту доступа или метрики; нарушение поведения либо критерия приёмки не показано.
- AA3 — false: изменены только два описания в сгенерированном файле типов, обязательная регенерация после OpenAPI поддерживает проектный инвариант; поведение фронтенда не изменено. Переписывание ограничения спеки не является исправлением кода.

## Dev Notes

### Текущее состояние кода (сверено на `c8907d17`, код = `20ca0c31`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/settings/base.py:42` | `"django.contrib.admin"` | → `"freesport.apps.FreesportAdminConfig"` |
| `backend/freesport/urls.py:41-45` | `path("admin/monitoring/", monitoring_dashboard_view)` — **без обёртки**; `path("admin/", admin.site.urls)` | обернуть дашборд в `admin.site.admin_view` |
| `backend/apps/common/admin.py:245` `monitoring_dashboard_view` | функция без декораторов | не меняется (защита в urls) |
| `backend/apps/integrations/onec_exchange/permissions.py:11` | `is_staff or has_perm("integrations.can_exchange_1c")` | только `has_perm` |
| `backend/apps/integrations/onec_exchange/views.py:196-197` | `authentication_classes = [Basic1CAuthentication, CsrfExemptSessionAuthentication]`, `permission_classes = [Is1CExchangeUser]` | не меняется |
| `backend/apps/integrations/models.py:21` | право `can_exchange_1c` у `integrations.Session` | не меняется |
| `backend/apps/integrations/views.py:16,29` | `@staff_member_required` на `import_from_1c_view` | superuser-декоратор |
| `backend/apps/integrations/urls.py:12` | `/api/integration/import_1c/` → та же вью, без `admin_view` | не меняется (защита декоратором) |
| `backend/apps/integrations/admin_urls.py:27` | `/admin/integrations/import_1c/` через `admin.site.admin_view` (monkey-patch `get_urls`, подключается в `integrations/apps.py:16`) | не меняется |
| `backend/apps/common/views.py:146,218,277,310` | `@permission_classes([IsAuthenticated, IsAdminUser])` | `IsSuperUser` |
| `backend/apps/products/views.py:497-519` | `include_inactive` для `is_staff` — **это фильтры каталога (атрибуты), а не товары**: эпик пишет «неактивные товары», по коду это неактивные `Attribute` | `is_superuser` |
| `backend/apps/users/admin.py:235-560` `UserAdmin` | `fieldsets` с `is_staff`, `is_superuser` («Роль и статус») и `groups`, `user_permissions` («Права доступа»); `filter_horizontal`; `get_fieldsets` прячет `onec_link_candidates`; `verify_b2b_view` проверяет `has_change_permission` (`:533`, комментарий «admin_view проверяет только is_staff» станет неточным — поправить на «только доступ к сайту») | см. Task 5 |
| `backend/apps/users/models.py:116-127` `create_superuser` | ставит `is_staff`, `is_superuser`, `role="admin"` | не меняется |

Других проверок `is_staff`/`IsAdminUser`/`staff_member_required` в нетестовом коде `backend/apps` и `backend/freesport` нет (grep на `c8907d17`); в шаблонах и во `frontend/src` `is_staff` не встречается. `role == "admin"` даёт только видимость оптовых цен (`products/pricing_policy.py:80`) — вне скоупа.

### Найденная дыра: `/admin/monitoring/` без проверки доступа

`freesport/urls.py:41-44` подключает `monitoring_dashboard_view` напрямую, без `admin.site.admin_view`, а у функции нет декораторов. Значит сегодня дашборд мониторинга синхронизации (здоровье компонентов, метрики операций, бизнес-метрики) отдаётся **любому, включая анонима**. Тест AC2 на анонима сначала написать и увидеть красным (подтвердить дыру), потом чинить. В Completion Notes указать, что это была реальная утечка на проде.

### Поведение отказа `AdminSite`

- `admin_view` при `has_permission() == False` делает `redirect_to_login(next, reverse("admin:login"))` → 302. Для аутентифицированного сотрудника страница входа покажет «Вы вошли как …, но не имеете доступа к этой странице» — это нормально.
- `AdminAuthenticationForm.confirm_login_allowed` по-прежнему пускает в форму входа любого `is_staff` — менять не нужно: после входа `has_permission` его всё равно не пропустит. Свои страницы входа разделов появятся в 42.4+.
- `/admin/password_change/` тоже станет superuser-only — у сотрудников нет пути сменить свой пароль через `/admin/`, это ожидаемо до появления разделов.

### Почему тест миграции вызывает функцию, а не проверяет БД

Тестовая БД строится **с миграциями** (флагов `--nomigrations` нет — `backend/AGENTS.md`), но транзакционные тесты (`clear_db_before_test` в `backend/tests/conftest.py:672` зависит от `transactional_db`) после себя делают `flush`, который стирает и `auth_group`. Права после `flush` восстанавливает `post_migrate`, группы — нет. Поэтому «группы есть после миграций» проверяется прямым вызовом `create_staff_role_groups` с глобальным реестром приложений, а не чтением состояния БД.

### Наследие прод-данных

- Группа «Менеджер» (id 1, 68 прав, включая `add/change/delete_user`, `change/delete_page`, `delete_order`, `change/delete_deliverymethod`, `change/delete_newsletter`), единственный участник — `alexmw2006@yandex.ru`. По решению 7 до выката эта запись становится суперпользователем и выходит из группы, поэтому на проде миграция переименует **пустую** группу: «Менеджеры», 11 прав из таблицы. Сценарий «участник сохраняется» (AC5) от этого не меняется — он проверяется тестом на синтетических данных.
- Учётные записи с доступом в служебную часть на проде (снято 08.10.2026, критерий: `is_staff`, `is_superuser`, `role=admin`, членство в группе или прямые права):

  | id | email | кто | staff / su | прямые права | после 42.1 |
  |---|---|---|---|---|---|
  | 1 | `admin@freesport.ru` | служебный суперпользователь | t / t | — | `/admin/` как прежде |
  | 11 | `alexmw2006@yandex.ru` | Alex | t / t | — | `/admin/` как прежде (решение 7) |
  | 15 | `managermsk3@freesportopt.ru` | Виктор Чернов, руководитель | t / f | `users.{view,change}_user`, `users.{view,change}_company`, `users.{view,change}_address`, `banners.{view,add,change,delete}_banner` | без `/admin/`; в «Руководители» после выката (решение 8) |
  | 17 | `1c_exchange_robot@freesport.ru` | робот обмена 1С | f / f | `integrations.can_exchange_1c`, `integrations.{view,add,change,delete}_session` | обмен как прежде (по праву) |

  Других сотрудников нет. У всех четырёх `role=admin`.

### Выкат (для Completion Notes и Alex)

1. Гейт обмена 1С **закрыт** (action_item done 08.10.2026): робот обмена ходит по `can_exchange_1c`, `is_staff=false`.
2. **Выполнено 08.10.2026:** `alexmw2006@yandex.ru` (id 11) — суперпользователь, из группы «Менеджер» выведен; группа «Менеджер» (id 1) на проде теперь пустая. Использованный SQL (таблицы — `users`, `users_groups`):
   ```sql
   BEGIN;
   UPDATE users SET is_staff = true, is_superuser = true WHERE email = 'alexmw2006@yandex.ru';
   DELETE FROM users_groups
    WHERE user_id = (SELECT id FROM users WHERE email = 'alexmw2006@yandex.ru')
      AND group_id = (SELECT id FROM auth_group WHERE name = 'Менеджер');
   COMMIT;
   ```
   Проверка: `SELECT is_staff, is_superuser, is_active FROM users WHERE email = 'alexmw2006@yandex.ru';` → `t, t, t`; вход в `/admin/` под этой записью работает.
3. Перед выкатом сверить, что состав не изменился (снято 08.10.2026: единственный — id 15):
   ```sql
   SELECT id, email, role, is_active FROM users WHERE is_staff AND NOT is_superuser ORDER BY id;
   ```
   Новая запись в списке — вопрос Alex до выката. **Сверено 09.10.2026:** состав не изменился, единственная запись — id 15 (`managermsk3@freesportopt.ru`, `role=admin`, `is_active=t`).
4. **После выката** (решение 8) — `managermsk3@freesportopt.ru` в «Руководители», прямые права снять, одной транзакцией:
   ```sql
   BEGIN;
   INSERT INTO users_groups (user_id, group_id)
   SELECT 15, id FROM auth_group WHERE name = 'Руководители'
   ON CONFLICT DO NOTHING;
   DELETE FROM users_user_permissions WHERE user_id = 15;
   COMMIT;
   ```
   Проверка: у id 15 одна группа «Руководители», `users_user_permissions` пуст. Если `INSERT` вставил 0 строк — миграция `0023` не применилась, остановиться.
5. После выката: `checkauth` обмена 1С из журнала nginx/backend проходит (следующий плановый обмен — достаточно), `/admin/` у суперпользователя открывается.
6. После рестарта backend на проде — `docker compose restart nginx` (memory: nginx держит старый IP upstream).

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, drf-spectacular 0.28.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет.
- Замена сайта по умолчанию — штатный механизм Django: подкласс `AdminConfig` с `default_site` в `INSTALLED_APPS` (docs: «Overriding the default admin site»). `admin.site` при этом остаётся тем же объектом для всех `@admin.register`.
- `create_permissions(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs)` в Django 5.2 выходит молча, если у `app_config.models_module` пусто, — поэтому передаётся глобальный конфиг, а `apps=` — историческое состояние.
- DRF `DEFAULT_PERMISSION_CLASSES = AllowAny` — у защищённых вью классы прав указываются явно (`project-context.md` §3); `IsAuthenticated` в декораторах метрик оставить, `IsSuperUser` добавить вместо `IsAdminUser`.
- Язык: интерфейс, комментарии, docstrings — русский (NFR-42-03). Существующий английский docstring `Is1CExchangeUser` перевести, раз класс правится.

### Тестирование

- Только Docker + PostgreSQL. Конкретный тест: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`. `--env-file` тестовому compose не передаётся. Параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры проставляются по каталогу автоматически (`backend/conftest.py`): `tests/unit/` → `unit`, `tests/integration/` → `integration`. Новый каталог под `tests/` не заводить (оборвёт сбор `UsageError`).
- Модуль доступа — критический (NFR-42-01, ≥ 90 %); у каждой проверки доступа — негативный тест (NFR-42-02). Позитивных тестов недостаточно.
- Уникальные email — через `get_unique_suffix()`/`unique_suffix()` проекта; фабрики — `LazyFunction`.
- 1С-обмен в тестах — Basic-авторизация (`"Basic " + base64(email:password)`), как в `test_onec_exchange_api.py:108`.
- `check_openapi_sync` (тестовый контейнер монтирует только `backend/`):
  ```bash
  cd docker
  MSYS_NO_PATHCONV=1 docker compose -p freesport-lint -f docker-compose.test.yml run --rm --no-deps -T \
    -v "C:/Users/1/DEV/FREESPORT/docs:/contract:ro" backend \
    python manage.py check_openapi_sync --schema-file /contract/api/openapi.yaml
  ```
- Базис mypy — 0 ошибок: любая ошибка новая.

### Связь с последующими стори

- 42.2 использует `staff_roles.STAFF_ROLE_GROUPS`, чтобы не назначать ответственного сотрудникам.
- 42.4–42.7 создают отдельные `AdminSite` (`/manager/`, `/marketing/`) со своим `has_permission` по группам; `SuperuserAdminSite` остаётся сайтом `/admin/`. Урезанные `ModelAdmin` для разделов наследуют защиту Task 5 или повторяют её — `PRIVILEGE_FIELDS` держать атрибутом класса, чтобы его можно было переиспользовать.
- Тесты «страница подтверждения требует `change_user`» вернутся в 42.4 на сайте менеджера.

### Project Structure Notes

- Новые файлы: `backend/freesport/admin_site.py`, `backend/freesport/apps.py`, `backend/apps/common/permissions.py`, `backend/apps/users/staff_roles.py`, `backend/apps/users/migrations/0023_staff_role_groups.py`, `backend/tests/unit/test_staff_role_groups_migration.py`, `backend/tests/integration/test_staff_access_lockdown.py` (+ юнит-тест `Is1CExchangeUser` в `backend/tests/unit/`).
- Изменяемые: `freesport/settings/base.py`, `freesport/urls.py`, `apps/integrations/onec_exchange/permissions.py`, `apps/integrations/views.py`, `apps/common/views.py`, `apps/products/views.py`, `apps/users/admin.py`, `docs/api/openapi.yaml`, тесты из Task 7.
- Фронтенд не затрагивается.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.1, FR-42-01…04, NFR-42-01/02/05/06, «Additional Requirements».
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-1, Constraints), `affected-code.md` («Права и эскалация»), `section-contents.md` («Ни одной из ролей»), `.memlog.md`.
- Статус прод-проверки: `sprint-status.yaml`, action_items эпика 42 (гейт 42.1 — done).
- Стандарты: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), 08.10.2026.

### Debug Log References

- GitNexus pre-flight: `impact --direction upstream` по всем девяти символам Task 0 — LOW (индекс на `20ca0c3`, после него только docs-коммиты).
- Красный тест анонима: после правки ссылки в шаблоне и до обёртки дашборда в `admin_view` — `assert 200 == 302`.
- Полный прогон в Docker (`freesport-test`, без параллельных): 3838 passed, 76 skipped, 0 failed.
- flake8 по `backend/` — 0; `black --check` по изменённым файлам — чисто (во всём `backend/` black хочет переформатировать только чужой `tests/unit/test_pytest_marker_autotagging.py`); mypy — 16 ошибок, все в нетронутых `apps/products/tests/unit/test_variant_import_{admission,error_paths}.py` (были до стори); `check_openapi_sync` — «Контракт синхронен с кодом».

### Completion Notes List

- **Кто теряет `/admin/` на проде:** по снимку 08.10.2026 — только `managermsk3@freesportopt.ru` (id 15, `is_staff=t`, `is_superuser=f`). Перед выкатом сверить запросом из шага 3.
- **`/admin/monitoring/` был открыт без проверки и на проде.** Анонимный `GET https://optisport.ru/admin/monitoring/` 08.10.2026 вернул **500**: шаблон вызывал несуществующий `{% url 'admin:monitoring_dashboard' %}`. Страница падала у всех, в том числе у суперпользователя, но перед этим считала по БД все четыре набора метрик — и для анонима тоже. Метрики аноним не получал, однако любой мог бесплатно нагружать базу. Ссылка исправлена на `admin_monitoring_dashboard`, дашборд обёрнут в `admin.site.admin_view`. Теперь аноним и сотрудник получают 302 на вход, суперпользователь — 200.
- **Шаги выката** (подробно — Dev Notes, «Выкат»):
  3. До выката: `SELECT id, email, role, is_active FROM users WHERE is_staff AND NOT is_superuser ORDER BY id;` — ожидается только id 15, новая запись — вопрос Alex.
  4. После выката: id 15 добавить в «Руководители» и снять прямые права одной транзакцией. Если `INSERT` вставил 0 строк, значит `0023` не применилась — остановиться.
  5. После выката: `checkauth` обмена 1С проходит (хватит следующего планового обмена), `/admin/` у суперпользователя открывается, `/admin/monitoring/` у суперпользователя отдаёт 200.
  6. После рестарта backend — `docker compose restart nginx`.
- Отклонения от стори описаны в разделе «Implementation Notes» спеки `spec-42-1-staff-roles-and-service-access-lockdown.md`: правка шаблона дашборда, снятые `type: ignore`, переименованные тесты Task 7, ненулевой базис mypy.

### File List

Новые:
- `backend/freesport/admin_site.py`
- `backend/freesport/apps.py`
- `backend/apps/common/permissions.py`
- `backend/apps/users/staff_roles.py`
- `backend/apps/users/migrations/0023_staff_role_groups.py`
- `backend/tests/unit/test_staff_role_groups_migration.py`
- `backend/tests/unit/test_onec_exchange_permissions.py`
- `backend/tests/integration/test_staff_access_lockdown.py`

Изменённые:
- `backend/freesport/settings/base.py`
- `backend/freesport/urls.py`
- `backend/apps/common/templates/admin/monitoring_dashboard.html`
- `backend/apps/common/admin.py` (контекст сайта админки в дашборде)
- `docs/decisions/ADR-009-csrf-exemption-1c-protocol.md`
- `frontend/src/types/api.generated.ts` (перегенерирован `npm run generate:types`)
- `backend/apps/common/views.py`
- `backend/apps/integrations/onec_exchange/permissions.py`
- `backend/apps/integrations/views.py`
- `backend/apps/products/views.py`
- `backend/apps/users/admin.py`
- `docs/api/openapi.yaml`
- `backend/tests/unit/test_users_admin.py`
- Task 7: `backend/tests/integration/{test_onec_exchange_api,test_1c_file_routing,test_1c_file_upload,test_onec_exchange_info_mode,test_onec_export,test_onec_export_e2e,test_onec_import,test_orders_xml_mode_file,test_order_exchange_import_e2e,test_admin_user_password,test_admin_link_1c_customer,test_admin_verify_b2b_application}.py`, `backend/apps/integrations/tests/{test_handle_init_cleanup_race,test_import_orchestration_view}.py`, `backend/apps/products/tests/integration/test_import_orchestration.py`, `backend/apps/products/tests/test_api_attributes.py`
