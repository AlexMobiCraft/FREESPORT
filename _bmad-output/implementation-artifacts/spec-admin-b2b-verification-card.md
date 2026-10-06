---
title: 'Карточка подтверждения B2B-заявки с данными 1С'
type: 'feature'
created: '2026-10-06'
status: 'done'
baseline_commit: 'eda4f9089e2bcedfffb3c19ebeb68991209fd851'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Чтобы подтвердить B2B-заявку, менеджер работает с полной карточкой пользователя (≈30 полей) и вручную ставит флаги. Привязка к 1С — отдельное действие в списке. 05.10.2026 на проде три заявки «верифицировали» галочками: привязку к 1С пропустили, AuditLog не записан, у одной заявки вручную взведён `created_in_1c`.

**Approach:** Отдельная страница «Подтверждение заявки». На ней только данные заявки и рядом — контрагенты 1С с тем же ИНН. Менеджер отмечает «Подтвердить». Одной транзакцией аккаунт связывается с контрагентом 1С (сервис `link_1c_customer`), получает роль, верифицируется и активируется, а в AuditLog пишется запись.

**Решения (Alex, 2026-10-06):**
1. Отдельная страница `/admin/users/user/<id>/verify/`. Ссылки на неё: `admin_url` в письмах о новой заявке (админу и региональному менеджеру), кнопка в полной карточке, колонка «Подтвердить» в списке. Полная карточка не меняется.
2. Нет кандидата в 1С → для подтверждения нужна вторая явная галочка «Подтвердить без привязки к 1С». Рядом предупреждение: контрагент будет создан в 1С при первом заказе.
3. На странице есть и «Отклонить». Поведение как у `reject_b2b_users`: `is_verified=False`, `verification_status="unverified"`, AuditLog `reject_b2b`. Роль и привязка не меняются.
4. Роль следует FR-40-12 (1С — источник истины). Если вид цен выбранного кандидата разрешился в B2B-роль, применяется она, а на странице показывается только для чтения: «из соглашения 1С: <вид цен>». Менеджер выбирает роль из `User.B2B_ROLES` только когда вид цен не разрешился или привязки нет; по умолчанию — текущая роль заявки.

## Boundaries & Constraints

**Always:**
- Связывание только через `link_1c_customer` (его проверки под блокировкой, перенос реквизитов, AuditLog привязки), без копии логики.
- Всё подтверждение — одна транзакция. Флаги верификации сохраняются последней записью: AuditLog `verify_b2b` пишется до них. Сигнал `check_verification_status_change` зовёт `.delay` без `on_commit`, поэтому при любом откате письмо пользователю не должно уйти в очередь.
- Условие «заявка ждёт решения» — `verification_status != "verified"`; `is_verified` в условии не участвует (на проде флаги расходятся).
- Страница доступна при праве `users.change_user` (явный `has_change_permission(request, obj)` на GET и POST) аккаунту с ролью из `B2B_ROLES`, не суперпользователю, если выполнено одно из двух:
  - (а) заявка ждёт решения;
  - (б) аккаунт верифицирован, но не связан (`link_target_q`), и у него есть кандидаты (`find_link_candidates`).
  
  В случае (б) «Подтвердить» только связывает и применяет роль: `is_active` и флаги верификации не трогаются (заблокированный клиент не разблокируется), «Отклонить» не показывается.
- Кандидаты показываются только при `link_target_q(target)`. У уже связанной заявки их нет, и подтверждение идёт без привязки и без второй галочки.
- Сервис повторяет проверки под `select_for_update` цели. Отказ, если:
  - условие доступа больше не выполняется (двойная отправка формы);
  - при `source_id=None` у цели, проходящей `link_target_q`, появились кандидаты (страница устарела).
- Данные из 1С экранируются.
- На странице и в колонке списка нет запросов на кандидата или строку. Виды цен читаются одним запросом (`load_price_type_role_map()` и наименования `PriceType` по набору GUID). Колонка списка строится только по полям строки и аннотации `_has_1c_candidate`.

**Never:**
- Не менять модели, миграции, `link_1c_customer`, `signals.py` и импорт 1С.
- Не удалять полную карточку и действия списка.
- Не выбирать контрагента 1С автоматически, если кандидатов больше одного.
- Не трогать `created_in_1c`, `sync_status`, `is_staff`, `is_superuser`, группы и права.

## I/O & Edge-Case Matrix

| Сценарий | Состояние | Результат | Ошибки |
|---|---|---|---|
| Один кандидат | pending, 1 запись 1С | Кандидат предвыбран; «Подтвердить» → связан, роль по решению 4, verified, `is_active=True` | — |
| Несколько кандидатов | 2+ записей 1С | Радиокнопки без предвыбора, у каждой строки — вид цен и роль по нему; выбор обязателен | Без выбора → ошибка формы |
| Нет кандидатов | ИНН в 1С не найден, не связан | Предупреждение + галочка «без привязки к 1С»; роль — выбор менеджера | Без галочки → ошибка формы |
| Связан, не верифицирован | onec_id есть, pending | Блок 1С показывает текущую привязку; «Подтвердить» → verified без второй галочки | — |
| Верифицирован, не связан, есть кандидаты | verified, кандидаты есть | Только привязка и роль; `is_active` не трогается; «Отклонить» скрыта | — |
| Нет оснований | verified и (связан или без кандидатов); не B2B; суперпользователь | Редирект на полную карточку с сообщением | — |
| Повтор / устаревшая вкладка | условие доступа уже не выполняется, кандидат занят или появился | Сообщение об ошибке, изменений нет | откат транзакции |
| Не отмечено «Подтвердить» | POST без `confirm` | Ошибка формы, ничего не меняется | — |
| Отклонение | кнопка «Отклонить» | Решение 3 | — |
| Нет права | staff без `change_user` | 403 | — |

</frozen-after-approval>

## Code Map

- `backend/apps/users/admin.py` -- `UserAdmin`. Добавить: свой URL в `get_urls()` (**перед** `super().get_urls()`, иначе `<path:object_id>/` перехватит путь); view; колонку списка; `change_view` с `extra_context` (флаг для кнопки). Переиспользовать `find_link_candidates`, `link_target_q`, аннотацию `_has_1c_candidate` (стр. 336), `_get_client_ip`, предупреждение о расхождении `customer_code` (стр. 708–718).
- `backend/apps/users/services/link_1c_customer.py` -- не менять. Сам ставит роль из вида цен (FR-40-11) и бросает `LinkCandidateError` / `TargetAlreadyLinkedError`.
- `backend/apps/users/services/price_type_role.py` -- `resolve_role_from_price_types(ids, role_map=...)`, `load_price_type_role_map()`.
- `backend/apps/users/services/processor.py:499-527` -- импорт пересчитывает роль связанных аккаунтов (FR-40-12). Основание решения 4.
- `backend/apps/users/signals.py:44` -- `.delay` без `on_commit`. Не менять.
- `backend/apps/users/tasks.py:75,441` -- `admin_url` писем. Тесты этот URL не проверяют.
- `backend/templates/admin/users/link_1c_customer.html` -- образец шаблона.
- `backend/tests/unit/test_users_admin.py:77-89` -- `test_list_display_fields` сравнивает точный список, обновить.
- `backend/tests/integration/test_admin_link_1c_customer.py` -- фикстуры (`manager` = суперпользователь, для проверки прав нужен staff без прав); тест `test_query_count_does_not_grow_with_rows` (стр. 313) должен остаться зелёным.

**Показываемые данные.** Заявка: email, ФИО, телефон, компания, ИНН, страна, дата регистрации, роль, статус. Кандидат 1С: наименование, ИНН, КПП, юр. адрес, вид цен и роль по нему, ID в 1С, код клиента.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/services/verify_b2b_application.py` -- две функции, обе пишут AuditLog и годятся для admin и shell:
  - `verify_b2b_application(*, target_id, source_id|None, expected_onec_id, role, confirm_without_1c, actor, ip_address, user_agent)`: проверки из Always под блокировкой; «роль до» фиксируется до `link_1c_customer`; затем роль (решение 4), AuditLog `verify_b2b` (роль до/после и её источник, onec_id или «без привязки»), флаги последними;
  - `reject_b2b_application(...)`.
- [x] `backend/apps/users/admin.py` -- URL, view, форма, колонка «Подтвердить» (ссылка только у подходящих строк), `change_view` с флагом для кнопки.
- [x] `backend/templates/admin/users/verify_b2b_application.html` -- страница.
- [x] `backend/templates/admin/users/user/change_form.html` -- кнопка в `object-tools` по флагу из `extra_context`.
- [x] `backend/apps/users/tasks.py` -- `admin_url` → `/verify/`.
- [x] `backend/tests/unit/test_users_admin.py` -- обновить `test_list_display_fields`.
- [x] `backend/tests/unit/test_services/test_verify_b2b_application.py` -- сервис: каждая ветка, откаты, роль вне `B2B_ROLES`, при откате нет вызова `send_user_verified_email.delay`.
- [x] `backend/tests/integration/test_admin_verify_b2b_application.py` -- строки матрицы через HTTP, права, экранирование, число запросов страницы и списка не растёт с числом кандидатов и строк.

**Acceptance Criteria:**
- Given pending-заявка, when менеджер открывает страницу, then видит только перечисленные выше поля, без групп, прав, пароля и полей синхронизации.
- Given подтверждение с привязкой, when смотрим AuditLog, then есть `link_1c_customer` и `verify_b2b` с актором-менеджером, а в `verify_b2b` записана роль до привязки.
- Given ошибка на любом шаге, when транзакция откатилась, then флаги, роль и привязка не изменены, письмо о верификации не поставлено в очередь.

## Implementation Notes

## Spec Change Log

## Review Triage Log

| # | Находка ревью спеки | Вердикт | Решение |
|---|---|---|---|
| 1 | FR-40-12 перетирает роль менеджера | high | Решение 4 (Alex) |
| 2 | Связанная pending-заявка застревает | high | Строка матрицы, кандидаты только при `link_target_q` |
| 3 | Verified без кандидатов — пустая страница | medium | Условие доступа (б) |
| 4 | Повтор/устаревшая вкладка в ветке без привязки | medium | Проверки под блокировкой |
| 5 | `.delay` внутри транзакции | medium | Флаги последними + тест |
| 6 | Предвыбор роли при 2+ и N+1 | medium | Роль по кандидату в строке, один запрос |
| 7 | `test_list_display_fields` | medium | Задача в Tasks |
| 8 | Порядок URL | low | Code Map |
| 9 | `admin_view` проверяет только staff | low | Явный `has_change_permission` |
| 10 | Кнопка карточки, блокировка, предикат, created_in_1c | low | `extra_context`; (б) не трогает `is_active`; предикат по `verification_status`; экспорт заказа смотрит только `onec_id` (`order_export.py:251`) — предупреждение верно |

**Ревью кода (итерация 0)**

| # | Находка ревью кода | Вердикт | Решение |
|---|---|---|---|
| C1 | `admin_url` писем на `/verify/` не проверен тестами (VG, BH) | low | patch: проверки в `test_email_tasks.py` и `test_region_routing.py`. Сборка пути строкой — прежний приём |
| C2 | Кнопка карточки в режиме (б) и без `change_user` не проверена (VG) | medium | patch: тест |
| C3 | Предупреждение о расхождении `customer_code` и тексты успеха не проверены (VG, BH) | medium | patch: интеграционный тест |
| C4 | Регистронезависимое имя вида цен не проверено (VG) | low | patch: GET-тест с GUID в верхнем регистре |
| C5 | Отклонённая (`unverified`) заявка остаётся «ждущей решения» (BH, ECH) | false | Предикат задан в замороженном Always: `verification_status != "verified"` |
| C6 | Повторное отклонение пишет второй `reject_b2b` (ECH) | low | rejected: редкий случай, фикс — новая ветка-guard |
| C7 | Карточка и `approve_b2b_users` по-прежнему верифицируют мимо страницы (BH) | false | Намерение: «Полная карточка не меняется», «Не удалять … действия списка» |
| C8 | Документация `docs/architecture/18-b2b-verification-workflow.md` не обновлена (BH) | low | rejected: документацию задача не заказывала |
| C9 | Подтверждение в режиме решения ставит `is_active=True` заблокированному (BH) | false | Строка матрицы «Один кандидат»: `is_active=True` |
| C10 | Отклонение без галочки и причины (BH) | false | Решение 3: как `reject_b2b_users` |
| C11 | `verify_b2b` пишется и в режиме (б), лог «подтверждена» (BH) | low | rejected: поле `mode`/`verified` в записи различает режимы; текст лога косметика |
| C12 | `"без привязки"` в поле `onec_id` AuditLog (BH) | false | Спека: «onec_id или «без привязки»» |
| C13 | Тесты числа запросов зависят от прогрева (BH) | false | Оба теста прогнаны по отдельности — зелёные |
| C14 | `test_double_submit_is_rejected` принимает две ошибки (BH) | low | patch: сузить до `VerificationError` |
| C15 | Расхождение «Верифицирован» в списке и ссылки «Подтвердить» (BH) | low | rejected: отображение `is_verified` прежнее, предикат задан намерением |
| C16 | Лишний `get_object` и поиск кандидатов в `change_view` (BH) | low | rejected: пара запросов на открытие карточки, фикс — перестройка view |
| C17 | Ветки view: `_reject` в режиме (б) без теста (BH) | low | patch: интеграционный тест |
| C18 | Цель, связанная только по `onec_guid`: AuditLog «без привязки», сообщение «без привязки», блок 1С с «—» (ECH) | low | patch: fallback на `onec_guid` в трёх местах |
| C19 | `.delay` в сигнале до commit (ECH, 2 находки) | medium (unverified) | defer: сигнал менять запрещено (Never), поведение прежнее |
| C20 | ИНН из пробелов: ссылка в списке есть, страница редиректит (ECH) | low | defer: дефект аннотации `has_1c_candidate_expression` существовал до задачи |
| C21 | Ошибки кроме `VerificationError`/`LinkCandidateError` → 500 (ECH) | maybe-false | rejected: сценарий не показан, если правда — low |
| C22 | Маппинг видов цен изменился между GET и POST (ECH) | low | rejected: маловероятно, фикс — новое скрытое поле |
| C23 | Staff с `view_user` получает 403 по ссылке из письма (ECH) | false | Матрица: «Нет права → 403» |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/unit/test_services/test_verify_b2b_application.py tests/integration/test_admin_verify_b2b_application.py tests/integration/test_admin_link_1c_customer.py tests/unit/test_users_admin.py` -- expected: всё зелёное
- навык `backend-lint` -- expected: black/flake8 чисто
