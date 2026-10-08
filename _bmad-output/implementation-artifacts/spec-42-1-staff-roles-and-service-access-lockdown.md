---
title: 'Story 42.1 — роли сотрудников и закрытие служебного доступа'
type: 'feature'
created: '2026-10-08'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
story_key: '42-1-staff-roles-and-service-access-lockdown'
baseline_commit: 'cef1318e29cdf6f49d600c47413ee82d95141766'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/Story/42-1-staff-roles-and-service-access-lockdown.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-42-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `is_staff` сегодня открывает основную `/admin/`, обмен 1С, запуск импорта, API метрик и неактивные атрибуты каталога, а право `users.change_user` позволяет поставить себе `is_superuser`. Пока это так, сотрудникам (эпик 42) нельзя выдавать учётные записи. Кроме того, `/admin/monitoring/` отдаётся вообще без проверки — даже анониму.

**Approach:** Data-миграция `users/0023_staff_role_groups` создаёт группы «Менеджеры», «Маркетинг», «Руководители» с замороженными наборами прав (переиспользует «Менеджер»). Весь служебный доступ переводится с `is_staff` на `is_superuser` или конкретное право, а из `UserAdmin` убирается путь эскалации. Утверждённые решения 1–8 и таблица «Наборы прав» из файла стори (`context[0]`) — обязательная часть этого intent.

## Boundaries & Constraints

**Always:**
- `/admin/` — только активному суперпользователю, через подкласс `AdminSite` (`SuperuserAdminSite`) + `AdminConfig.default_site`; отказ — штатный 302 на `/admin/login/?next=…`.
- Обмен 1С — только `has_perm("integrations.can_exchange_1c")`; импорт, метрики, `include_inactive` — только суперпользователь.
- Миграция: права ищутся строго (ненайденное — исключение), перед поиском `create_permissions` для 6 приложений; повтор идемпотентен и не снимает вручную добавленные права; «замена» прав — только при переименовании «Менеджер»; обратная — `noop`; наборы прав и имена групп в миграции — литералы.
- У каждой проверки доступа — негативный тест; тесты миграции не зависят от того, есть ли группы в тестовой БД.
- Русский язык в docstrings/комментариях; `docs/api/openapi.yaml` синхронен (`check_openapi_sync`).

**Never:**
- Не monkey-patch `admin.site.has_permission`; не класть `AdminConfig`-подкласс в `apps/common/apps.py`.
- Не трогать `user_permissions` сотрудников, не назначать роли/суперпользователя по email в миграции.
- Не создавать разделы `/manager/`, `/marketing/` (42.4+), не урезать действия/инлайны `UserAdmin`, не менять `list_filter`, `AdminAuthenticationForm`, фронтенд.
- Не править тесты сверх перечня Task 7 стори.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Сотрудник в `/admin/…` | `is_staff`, член группы роли, не su; 7 URL из AC2 стори | 302 на `/admin/login/` | — |
| Аноним на дашборде | GET `/admin/monitoring/` | 302 на вход (сейчас 200 — утечка) | — |
| Робот обмена | `can_exchange_1c`, `is_staff=False`, `checkauth` | 200 `success` | — |
| Сотрудник на обмене | `is_staff=True` без права | 403 | — |
| Сотрудник: импорт / метрики | `/api/integration/import_1c/` / 4 метрики | 302 на `admin:login` / 403 | su: 200 (health может 503) |
| `include_inactive=true` | сотрудник / su | без неактивных / с неактивными | — |
| Подделанный POST в `UserAdmin` | не-su с `change_user`, `is_superuser=on`, `groups`, `user_permissions` | полей нет в форме, значения не меняются | — |
| Цель — суперпользователь | не-su с `change_user` | `has_change/delete_permission` → False | — |
| Миграция: «Менеджер» + «Менеджеры» | обе группы | участники перенесены, «Менеджер» удалена | — |

</frozen-after-approval>

## Code Map

- `backend/freesport/settings/base.py:42` -- `"django.contrib.admin"` → `"freesport.apps.FreesportAdminConfig"`.
- `backend/freesport/urls.py:41-45` -- дашборд без обёртки → `admin.site.admin_view(monitoring_dashboard_view)`.
- `backend/apps/integrations/admin.py:9-11`, `admin_urls.py` -- заголовки и monkey-patch `get_urls` на lazy `admin.site`; работают с подклассом, не менять.
- `backend/apps/integrations/onec_exchange/permissions.py` -- `Is1CExchangeUser`: убрать ветку `is_staff`, docstring перевести.
- `backend/apps/integrations/views.py:16,29` -- `@staff_member_required` → `user_passes_test(su, login_url="admin:login")`; вью также на `/api/integration/import_1c/` (`integrations/urls.py:12`) без `admin_view`.
- `backend/apps/common/views.py:22,146,218,277,310` -- `IsAdminUser` → `IsSuperUser` из нового `apps/common/permissions.py`; `IsAuthenticated` оставить.
- `backend/apps/products/views.py:481-545` -- `AttributeFilterViewSet`: `is_staff` → `is_superuser`, docstrings и `extend_schema`; `docs/api/openapi.yaml:~1632,~1677` — то же описание.
- `backend/apps/users/admin.py:236-560` -- `UserAdmin`: `get_fieldsets` (`:435`, сохранить скрытие `onec_link_candidates`), добавить `PRIVILEGE_FIELDS`, `has_change/delete_permission`; комментарий `:532` поправить.
- Последние миграции (сверено): users `0022_alter_user_country`, orders `0016_customercodesequence`, banners `0007_banner_ad_disclosure`, common `0021_newsletter_unsubscribe_token`, products `0056_onec_deleted_and_excluded_items`, bonuses `0003_bonus_journal_survives_deletion`. `default_permissions` нигде не переопределён; `products.HomepageCategory` — proxy.
- Тесты: перечень Task 7 стори совпадает с `grep is_staff=True` на baseline; `tests/integration/test_monitoring_api.py` уже на `create_superuser`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/staff_roles.py` -- имена групп + `STAFF_ROLE_GROUPS` -- нужны 42.2+.
- [x] `backend/apps/users/migrations/0023_staff_role_groups.py` -- `ROLE_PERMISSIONS`, `LEGACY_NAMES`, `create_staff_role_groups` по алгоритму Task 2 стори -- AC1, AC5.
- [x] `backend/freesport/admin_site.py`, `backend/freesport/apps.py`, `settings/base.py`, `urls.py` -- superuser-only сайт и обёртка дашборда -- AC2.
- [x] `onec_exchange/permissions.py`, `integrations/views.py`, `common/permissions.py`, `common/views.py`, `products/views.py`, `docs/api/openapi.yaml` -- AC3.
- [x] `backend/apps/users/admin.py` -- Task 5 стори -- AC4.
- [x] Новые тесты (Task 6 стори): `tests/unit/test_staff_role_groups_migration.py`, `tests/integration/test_staff_access_lockdown.py`, дописать `tests/unit/test_users_admin.py`, юнит-тест `Is1CExchangeUser` в `tests/unit/`. Тест анонима на дашборде сначала увидеть красным.
- [x] Существующие тесты — ровно перечень Task 7 стори.

**Acceptance Criteria:** AC1–AC6 файла стори (`context[0]`) — без изменений.

## Implementation Notes

- **Дашборд мониторинга был сломан целиком.** Шаблон `apps/common/templates/admin/monitoring_dashboard.html:264` вызывал `{% url 'admin:monitoring_dashboard' %}`, а маршрут называется `admin_monitoring_dashboard` и лежит вне пространства `admin`. Страница падала с `NoReverseMatch` у всех. AC2 требует от суперпользователя 200, поэтому ссылка в шаблоне исправлена на `admin_monitoring_dashboard`. Других правок шаблона нет.
- **Утечка на проде — 500, а не 200.** Анонимный `GET https://optisport.ru/admin/monitoring/` 08.10.2026 вернул 500. Метрики аноним не получал: страница падала на той же ссылке, но перед этим успевала посчитать все четыре набора метрик по БД. Красный тест (аноним → 302) после правки шаблона и до обёртки в `admin_view` падал на `200 == 302`, так что дыра в коде была настоящей.
- `superuser_required` в `integrations/views.py` вызывает именованную типизированную функцию `_is_active_superuser`, а не лямбду: на лямбду mypy выдаёт `attr-defined` и `return-value`.
- `UserAdmin.has_change_permission` принимает `apps.users.models.User`, поэтому `# type: ignore[arg-type]` в `change_view` и `verify_b2b_view` стали лишними (`warn_unused_ignores`). Их пришлось снять, после чего black склеил условие `show_verify_b2b_button` в одну строку.
- Тесты Task 7, у которых изменился смысл, переименованы: `test_staff_without_change_permission_gets_403` → `test_staff_is_redirected_to_login`, `test_change_form_button_hidden_without_change_permission` → `test_change_form_closed_for_staff`, `test_catalog_filters_include_inactive_for_staff` → `..._for_superuser`. Кроме того, добавлен `test_catalog_filters_include_inactive_ignored_for_staff`.
- **mypy:** базис не нулевой. 16 ошибок в двух нетронутых файлах `apps/products/tests/unit/test_variant_import_{admission,error_paths}.py` были и до стори, в файлах стори ошибок 0.
- isort в CI не запускается. Прогон isort по изменённым файлам переставил чужие импорты, эти правки откатаны.

## Spec Change Log

## Review Triage Log

Проход 1 (blind-hunter BH, edge-case-hunter ECH, verification-gap VG):

| # | Находка | Вердикт | Доказательство / маршрут |
|---|---|---|---|
| BH1, ECH1, ECH2 | не-su с `change_user` может менять другого сотрудника (руководителя): пароль, email → захват | false | `SuperuserAdminSite.has_permission` не пускает в `UserAdmin` ни одного не-su, путь недостижим. **Учесть в 42.4/42.7**: защита цели-сотрудника при переиспользовании `UserAdmin` |
| BH2 | `role` (значение `admin` открывает оптовые цены) не в `PRIVILEGE_FIELDS` | false | Тот же довод: не-su до формы не доходит. Роль в разделе менеджера — read-only по эпику (42.4) |
| BH3 | HTTP-тест AC4 проверяет только отказ сайта, unit обходит `change_view` | false | AC4 стори требует ровно это: 302 через `/admin/` + `get_form`/`save_m2m`; `save_model` привилегий не трогает |
| BH4 | `IsSuperUser` не проверяет `is_active`; лишний `IsAuthenticated` | false | Неактивного пользователя не аутентифицируют ни JWT (`User is inactive`), ни сессия (`ModelBackend.get_user`), ни Basic; `IsAuthenticated` оставлен по спеке |
| BH5 | миграция теряет прежние права «Менеджер», откат релиза их не вернёт | low → reject | Замена прав — утверждённое решение 4; на проде группа пустая, старый код имён групп не читает |
| BH6, VG-gap, ECH3 | проверки `change_user` в `UserAdmin` (verify, действие связывания, пароль, кнопка) больше не закреплены тестами | medium → defer | VG pre-verified; возврат тестов в 42.4 зафиксирован стори (Task 7) |
| BH7 | имя `test_action_requires_change_user_permission` не соответствует проверке | low → patch | Прямое переименование |
| BH8 | дашборд мониторинга рендерится без `each_context` (дефолтный заголовок, нет выхода) | low → patch | `common/admin.py:245` — `render` без контекста админки; страница впервые рабочая после правки шаблона |
| BH9 | ADR-009:26 — «and is staff/admin by default» | low → patch | Строка подтверждена grep |
| BH10 | нет страховки от возврата `IsAdminUser`/`is_staff` в служебных местах | medium → defer | Фикс — правило в `AGENTS.md` («Неочевидное в коде»): агент-контекст |
| BH11 | сотрудник логинится в `/admin/login/` и уходит в редирект | false | Решено стори: `AdminAuthenticationForm` не трогать (frozen «Never») |
| BH12 | два фильтра fieldsets устроены по-разному; `list_filter is_staff` | low → reject | Без названного вреда; `list_filter` — «не трогать» по стори |
| BH13 | дубли тестов; импорт `Permission` внутри фикстуры | low → reject | Косметика, вреда нет |
| VG-other | `frontend/src/types/api.generated.ts` не перегенерирован — упадёт required-чек `api-contract.yml` | high → patch | Строки 911, 4619 со старым текстом; шаг «Сверка сгенерированных типов» сравнивает файл |

## Design Notes

Почему функция миграции тестируется прямым вызовом, поведение отказа `AdminSite`, наследие прод-данных и шаги выката — Dev Notes стори; в Completion Notes перенести: список учётных записей, теряющих `/admin/` (id 15), факт утечки `/admin/monitoring/` на проде, шаги выката 3–6.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest` -- expected: всё зелёное (один прогон, без параллельных).
- Линтеры (`flake8`, `black --check`, `mypy`) в compose-проекте `freesport-lint`, не параллельно pytest -- expected: 0 ошибок.
- `check_openapi_sync` по рецепту Dev Notes стори -- expected: синхронно.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` -- expected: только символы стори.
