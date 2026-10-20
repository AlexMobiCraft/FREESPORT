---
title: 'Отклонение B2B-заявки удаляет заявителя и отправляет ему письмо'
type: 'bugfix'
created: '2026-10-20'
status: 'done'
baseline_commit: 'c33b90044bb86cfafb0e235e7629add3b6c18ef2'
review_loop_iteration: 0
context:
  - '{project-root}/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Кнопка «Отклонить» на странице `/verify/` лишь ставит `unverified` и ведёт в полную карточку. Заявитель остаётся в БД, письма об отказе нет. Сигнал письма срабатывает только на переход в `verified`.

**Approach:** Отклонение новой заявки удаляет заявителя в одной транзакции с записью в AuditLog. После коммита на email заявителя уходит письмо: заявка отклонена, причину уточняйте по контактам на сайте. Менеджера возвращает в список клиентов. Массовое действие `reject_b2b_users` ведёт себя так же.

## Boundaries & Constraints

**Always:**
- Удалять можно только заявку, ждущую решения (`verification_mode == MODE_DECISION`), без заказов и без привязки к 1С (`onec_id`/`onec_guid`).
- AuditLog `reject_b2b` пишется до удаления и сохраняет `email` (требование владельца), роль и признак `deleted: true`.
- Письмо ставится в очередь через `transaction.on_commit`; данные для него (email, имя, роль) берутся до удаления и передаются в задачу значениями, а не `user_id`.
- Тот же email и ИНН могут зарегистрироваться заново.

**Ask First:** удаление любой записи вне перечисленных условий.

**Never:**
- Не удалять верифицированных, связанных с 1С, с заказами, `is_staff`, суперпользователей.
- Не менять `approve_b2b_users`, `block_users`, подтверждение заявки.
- Не трогать `Newsletter` и `UserConsent`: у них `user` с `SET_NULL`, это отдельные согласия.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Отказ на странице | новая заявка, заказов и 1С нет | пользователь удалён, AuditLog с email, письмо после коммита, редирект на список клиентов | N/A |
| Есть заказ или привязка 1С | заявка с заказом либо `onec_id` | ничего не удалено, письма нет | `VerificationError` → сообщение менеджеру |
| Верифицированный / `LINK_ONLY` | `verification_status=verified` | отказ, данные не тронуты | сообщение «Отклонить можно только заявку, ждущую решения» |
| Массовое действие | выборка из подходящих и неподходящих | подходящие удалены, неподходящие пропущены с сообщением | сводка «отклонено N, пропущено M» |
| Устаревшая вкладка | заявку уже удалили | 404 вместо 500 | `VerificationError` |
| Сбой отправки | SMTP недоступен | пользователь уже удалён, задача повторяется (`autoretry`) | лог ошибки |

</frozen-after-approval>

## Code Map

- `backend/apps/users/services/verify_b2b_application.py` -- `reject_b2b_application` (стр. 279): сейчас ставит `unverified`; сюда добавляются проверки и удаление.
- `backend/apps/users/admin.py` -- `_apply_reject_b2b` (стр. 830, редирект на карточку), `reject_b2b_users` (стр. 1205, цикл с `save`), `verify_b2b_view`.
- `backend/apps/users/manager_admin.py` -- `ManagerClientAdmin` оборачивает вью и действие в `atomic` с блокировкой строки.
- `backend/apps/users/tasks.py` -- рядом с `send_user_verified_email` (стр. 499) добавляется задача письма.
- `backend/templates/emails/account_verified.{html,txt}` -- образец шаблонов; контакты сайта в `frontend/src/components/layout/Footer.tsx:77` (`+7 968 273-21-68`, `info@optisport.ru`).
- `backend/templates/admin/users/verify_b2b_application.html` -- подпись у кнопки «Отклонить».
- `backend/apps/common/staff_journal.py:452` -- журнал руководителя уже подписывает удалённого клиента email из `changes`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/tasks.py` -- задача `send_b2b_rejection_email(email, first_name, role_display)` с теми же `autoretry`, что у соседних -- пользователя уже нет в БД.
- [x] `backend/templates/emails/b2b_application_rejected.html`, `.txt` -- текст: заявка отклонена, причину уточняйте по контактам, указанным на сайте; телефон и email из подвала, ссылка на `site_url`.
- [x] `backend/apps/users/services/verify_b2b_application.py` -- проверки заказов, 1С, `is_staff`; AuditLog; `delete()` с обработкой `ProtectedError`; `on_commit` с задачей; вернуть email -- один путь для страницы и массового действия.
- [x] `backend/apps/users/admin.py` -- `_apply_reject_b2b`: сообщение и редирект на `…_users_user_changelist`; `reject_b2b_users`: вызов сервиса на каждого, сводка «отклонено/пропущено».
- [x] `backend/templates/admin/users/verify_b2b_application.html` -- пояснение «данные заявителя будут удалены, ему уйдёт письмо».
- [x] Тесты: `tests/integration/test_admin_verify_b2b_application.py` (`test_reject`), `test_manager_clients_section.py` (стр. ~500, 870, 1081, 1537; блокировка строки теперь не через `save`), `test_staff_journal.py` (`do_reject_*`), `tests/unit/test_users_admin.py` (стр. 318, 430) -- переписать под удаление; добавить случаи из матрицы и тест письма через `django_capture_on_commit_callbacks`.

**Acceptance Criteria:**
- Given новая заявка без заказов и 1С, when менеджер нажимает «Отклонить», then пользователя нет в БД, есть AuditLog `reject_b2b` с его email, письмо поставлено в очередь на его адрес.
- Given заявка с заказом или привязкой к 1С, when менеджер отклоняет, then пользователь и данные целы, письма нет.
- Given клиент `verified`, when запускается `reject_b2b_users`, then он пропущен и остаётся верифицированным.
- Given менеджер вне раздела клиента, when он отклоняет чужую заявку, then 404 и ничего не удалено.

## Design Notes

Журнал и так переживает удаление: `UserConsent.user`, `Newsletter.user`, `SyncLog.customer` и `AuditLog.user` имеют `SET_NULL`, `Cart`/`Company`/`Address` удаляются каскадом. `Order.user` каскадный, поэтому проверка заказов обязательна до `delete()`.

## Verification

**Commands:**
- `docker compose -p freesport-test -f docker/docker-compose.test.yml run --rm -T backend pytest -q tests/integration/test_admin_verify_b2b_application.py tests/integration/test_manager_clients_section.py tests/integration/test_staff_journal.py tests/unit/test_users_admin.py` -- expected: все тесты зелёные
- `black --check` и `flake8` по затронутым файлам (навык `backend-lint`) -- expected: чисто

## Suggested Review Order

**Удаление заявки и письмо**

- Точка входа: проверки, запись в журнал, `delete()` и письмо после коммита.
  [`verify_b2b_application.py:305`](../../backend/apps/users/services/verify_b2b_application.py#L305)

- Что считается «живым» аккаунтом: сотрудник, привязка к 1С, заказы.
  [`verify_b2b_application.py:289`](../../backend/apps/users/services/verify_b2b_application.py#L289)

- Письмо ставится через `on_commit(robust=True)`: сбой брокера не роняет запрос.
  [`verify_b2b_application.py:369`](../../backend/apps/users/services/verify_b2b_application.py#L369)

- Задача принимает значения, а не `user_id`: заявителя к этому моменту уже нет.
  [`tasks.py:568`](../../backend/apps/users/tasks.py#L568)

**Страница и массовое действие**

- Отказ на странице: редирект в список клиентов и честное сообщение о письме.
  [`admin.py:830`](../../backend/apps/users/admin.py#L830)

- Массовое действие идёт через тот же сервис и пропускает неподходящих.
  [`admin.py:1216`](../../backend/apps/users/admin.py#L1216)

- Пояснение менеджеру: отказ безвозвратно удаляет заявителя.
  [`verify_b2b_application.html:144`](../../backend/templates/admin/users/verify_b2b_application.html#L144)

**Тесты**

- Страница: удаление, письмо, откат, сбой брокера, заказы, 1С, сотрудник.
  [`test_admin_verify_b2b_application.py:405`](../../backend/tests/integration/test_admin_verify_b2b_application.py#L405)

- Сервис: журнал с email, каскад связанных данных, отказы.
  [`test_verify_b2b_application.py:448`](../../backend/tests/unit/test_services/test_verify_b2b_application.py#L448)

- Текст письма, пустое имя, отсутствие HTML-экранирования, ретрай.
  [`test_b2b_rejection_email.py:1`](../../backend/tests/unit/test_b2b_rejection_email.py#L1)
