---
title: 'Смена роли клиента в разделе менеджера и маркетинговые метки товара'
type: 'feature'
created: '2026-10-30'
status: 'done'
baseline_commit: a59aaaaeb6fc2f4ad99c95a8575fc579f0e8473f
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В карточке клиента `/manager/` роль только для чтения (FR-42-13), поэтому менеджер и руководитель не могут сменить уровень цен клиента: её меняют только 1С, подтверждение заявки и владелец в `/admin/`.

**Approach:** Поле «Роль» становится правимым в карточке `/manager/` у верифицированного B2B-клиента, из списка без служебных ролей. Смена пишется в журнал действий.

Решения владельца (2026-10-30):
- **Флаги товара не меняются.** «Хит», «Новинка», «Распродажа», «Премиум» уже правят «Маркетинг» и «Руководители» в `/marketing/`. «Акция» (`is_promo`) остаётся за импортом 1С.
- **Розница → B2B запрещена.** Розничный клиент получает B2B-роль только через заявку.
- **1С главнее.** Импорт вправе вернуть роль по виду цен соглашения; у клиента, связанного с 1С, карточка об этом предупреждает.

## Boundaries & Constraints

**Always:**
- Роль правят группы «Менеджеры» (только свои клиенты, `scope_clients`) и «Руководители» (все клиенты).
- Выбор ролей: `User.ROLE_CHOICES` без `admin` и `unregistered`. Проверка на сервере, подделанный POST с этими ролями отклоняется.
- Роль правима, только если `obj.role` в `User.B2B_ROLES` и `activation_locked(obj)` ложно. Розница, запись 1С без аккаунта и незавершённая заявка остаются только для чтения.
- Подсказка у поля про возврат роли обменом с 1С — только если у клиента есть `onec_id` или `onec_guid`.
- Смена роли — запись `AuditLog` с кодом `change_user_role` (`old`, `new`, `email`, `source: card`) и подписью в ленте `/supervisor/journal/`.
- Сохранение идёт под уже существующей блокировкой строки `change_view`.

**Never:**
- Не показывать поле роли в `/supervisor/` (там сотрудники) и не менять `SupervisorStaffAdmin`.
- Не менять импорт 1С, страницу подтверждения заявки и `marketing_admin.py`, не добавлять миграции.
- Не делать роль массовым действием.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Смена уровня | Верифицированный оптовик 1 → оптовик 3 | Роль сохранена, запись в журнале, цены клиента новые | N/A |
| Понижение | Верифицированный оптовик → розница | Роль сохранена, запись в журнале | N/A |
| Розничный клиент | `retail` | Роль только для чтения, POST поле игнорирует | N/A |
| Заявка ждёт решения | B2B, `pending` | Роль только для чтения, POST поле игнорирует | N/A |
| Запись 1С | `unregistered` | Роль только для чтения | N/A |
| Подделка | POST `role=admin` или `unregistered` | Роль не меняется | Ошибка поля формы |
| Чужой клиент | POST менеджера на клиента другого менеджера | 404 | Как сейчас |
| Без изменений | Сохранение карточки с той же ролью | Записи в журнале нет | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/users/manager_admin.py` -- `ManagerClientAdmin`: `readonly_fields`, `get_readonly_fields`, `get_form`, `save_model`.
- `backend/apps/users/admin.py:203` -- `activation_locked` переиспользовать. `UserAdmin` не менять: `/admin/` у владельца.
- `backend/apps/users/models.py:159` -- `ROLE_CHOICES`, `B2B_ROLES`.
- `backend/apps/users/services/processor.py:475` -- `_resolve_role_change`: импорт 1С перезаписывает роль.
- `backend/apps/products/pricing_policy.py:124` -- B2B-цены только при `is_verified`.
- `backend/apps/common/staff_actions.py`, `staff_journal.py:341` -- код действия и подробности в ленте.
- `backend/tests/integration/test_manager_clients_section.py:593` -- подделка POST на `pending`-клиенте остаётся верной.
- `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md:71` -- FR-42-13 устарел.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/manager_admin.py` -- снять `role` из `readonly_fields`, вернуть для всех, кроме верифицированных B2B, ограничить выбор и добавить подсказку 1С в `get_form`, журналировать в `save_model` -- основная правка.
- [x] `backend/apps/common/staff_actions.py`, `backend/apps/common/staff_journal.py` -- код `change_user_role` и «было → стало» подписями ролей -- иначе запись не попадёт в ленту.
- [x] `backend/tests/integration/test_manager_clients_section.py` -- случаи матрицы, журнал -- покрытие.
- [x] `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` -- обновить FR-42-13 -- решение владельца.

**Acceptance Criteria:**
- Given менеджер открыл карточку своего верифицированного клиента, when он меняет роль, then каталог показывает клиенту цены новой роли.
- Given руководитель сменил роль, when он открывает `/supervisor/journal/`, then видит запись «было → стало» с автором.

## Implementation Notes

- `role_is_editable` запоминает решение на объекте при первом вызове. `form.is_valid()` пишет выбранную роль в тот же `obj`, а Django при ошибке в другом поле зовёт `get_readonly_fields` повторно: выбор «Розница» убрал бы поле из перерисованной формы, и следующий POST упал бы на обязательном поле. Закреплено тестом `test_validation_error_keeps_role_input`, мутация проверена.
- Вне списка задач, но неизбежно: литералы кодов действий в `tests/unit/test_staff_journal.py` и `tests/integration/test_staff_journal.py` (`ALL_CODES`) — иначе сторожа падают на новом коде.
- По ревью: поле роли несёт `show_hidden_initial`, а `save_model` возвращает роль из строки, если сотрудник её не менял, — устаревшая карточка не откатывает импорт. Пустое и отсутствующее значение означает текущую роль (`required=False`, `empty_value`, `bound_data` для перерисовки). Журнал пишется только при реальной смене. Условие правимости дополнено `is_verified`.
- По ревью приведены к FR-42-13: эпик 42 (FR-42-14, ограничения, стори 42.4), `spec-staff-admin-sections/SPEC.md`, `section-contents.md`.

## Spec Change Log

## Review Triage Log

Слои: Blind Hunter, Edge Case Hunter, Verification Gap, graph-impact. Ни один не пропущен: graph-impact на первом запуске остановился на устаревшем индексе и повторён после переиндексации.

- medium, patch — устаревшая карточка откатывает роль (Edge Case, Verification Gap): `form.initial` читается из свежей строки, POST несёт старую роль, поэтому правка телефона затирает роль импорта, а журнал приписывает откат менеджеру. Трассировка `save_model` подтвердила.
- medium, patch — POST без поля роли (Edge Case): заявку подтвердили при открытой read-only карточке, поле стало обязательным, браузер покажет первую опцию «Розница», повторное сохранение понизит клиента.
- medium, patch — расхождение признаков (Blind Hunter, Edge Case): правимость смотрит `verification_status`, цены — `is_verified`, а `verify_b2b_application.py:73` подтверждает расхождение на проде. У такого клиента смена роли не меняет цены.
- medium, patch — документы противоречат FR-42-13 (Blind Hunter): `epic-42:73,143,379,399`, `SPEC.md:101`, `section-contents.md:15`.
- medium, patch — нет теста «импорт возвращает роль пониженному клиенту» (Verification Gap, предварительно проверено): все `_linked_account` стартуют с оптовой роли.
- low, patch — формулировка «Обратно в B2B — только через заявку» в тесте и FR-42-13 (Blind Hunter, Edge Case): заявки для существующего retail нет, `verification_mode` вернёт `None`. Сам эффект владельцу назван на checkpoint и принят.
- medium, defer — снимок цены в корзине не следует за ролью (все слои): `order_create.py:138`. Так же работают смена роли импортом и решение 2026-10-26 «снимки цен в корзине не пересчитываются»; правка сюда не относится.
- medium, defer — бонус тренера считается по текущей роли (Blind Hunter): `accrual.py:158`. Так же действует смена роли импортом, выбор «Тренер» на странице подтверждения был у менеджера и раньше.
- low, отклонено — откат 1С не виден в ленте: `role_from_1c` исключён из ленты намеренно (`staff_actions.py:5`).
- low, отклонено — подсказка «может вернуть» расплывчата: формулировка верна, точный прогноз требует новой логики.
- low, отклонено — подсказки нет у read-only поля: менеджер видит её в момент понижения, вывод для read-only усложнил бы карточку.
- low, отклонено — роль без заполненных цен: тот же список на странице подтверждения, правка усложнила бы выбор.
- low, отклонено — инструкция менеджера не описывает поле: поле видно в карточке, в запросе инструкции нет.
- low, отклонено — клиент не получает письмо: в запросе этого нет, новая поверхность.
- low, отклонено — гонка импорта с сохранением карточки (`processor.py:624`): окно мало, следующий обмен всё равно ставит роль 1С.
- false — нет проверки, что роли нет в `/supervisor/`: её держит `test_staff_card_whitelist_has_no_privileges`.
- false — команда Verification не запускает тесты журнала: правка спеки, а не кода; тесты журнала прогоняются отдельно.
- low, patch — FR-42-13 обещал возврат обменом с 1С любому клиенту (graph-impact): несвязанному клиенту обмен не поможет, а привязка принимает только B2B (`users/admin.py:1123`). Формулировка уточнена.
- low, отклонено — вид цен заказа зависит от роли, у `vip` и `special_price` нет маппинга (graph-impact): экспорт намеренно не менялся в спеке ролей VIP, БУС `ВидЦены` строки заказа не читает.
- low, отклонено — ограничение способов оплаты зависит от текущей роли (graph-impact): правило корректно для новой роли, остаток связан с отложенным снимком цены.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/integration/test_manager_clients_section.py tests/integration/test_supervisor_section.py` -- expected: все зелёные
