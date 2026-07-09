---
title: 'Привязка существующего 1С-клиента к регистрации на портале'
type: 'feature'
created: '2026-07-09'
status: 'done'
context: []
baseline_commit: '6beb607c5ee5f0866da9df51ac95d7c4d66c31ea'
review_loop_iteration: 2
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Клиент, уже выгруженный из 1С (`created_in_1c=True`, пароль не задан), при регистрации на сайте с тем же email/ИНН получает жёсткий отказ без пути восстановления доступа. Первая версия решения (мгновенная привязка пароля при матче) оказалась уязвима к захвату аккаунта — ИНН юрлиц часто публичен, а подтверждения владения не требовалось.

**Approach:** Матч по ИНН для B2B (есть tax_id) → если email формы совпадает с email в 1С, аккаунт сразу уходит в `pending` и на ручное одобрение администратору (как обычная B2B-заявка); если email отличается — сперва ссылка-подтверждение на НОВЫЙ email, и только после клика (с заменой email и новым паролем) — `pending` + уведомление админам. Матч с уже занятым/верифицированным аккаунтом — 400, без дубля. **Retail временно вне скоупа** — доступ к порталу через привязку 1С-записи предоставляется только B2B; матч по email для retail-клиента из 1С не даёт доступа (решение человека 2026-07-09, раунд 3: временно доступ только для B2B).

## Boundaries & Constraints

**Always:** ссылка подтверждения для B2B с несовпадающим email уходит на НОВЫЙ email из формы (доказывает лишь его живость), никогда на старый email из 1С; пароль и переход в `pending` выполняются одним атомарным шагом (нет окна "пароль уже есть, но verification_status ещё не блокирует вход" — `UserLoginView` блокирует вход только по `verification_status == "pending"`, `is_active` не проверяется); "1C wins" — ФИО/роль/компания форма не переопределяет никогда; email — единственное исключение, обновляется только после явного подтверждения владения новым адресом; финальную верификацию (`verified`/`is_verified`) делает только человек-администратор через существующий `approve_b2b_users`, не код; матч в `validate()` допускается только для `verification_status == 'unverified'` — запись, уже переведённая в `pending` этой же фичей, повторно не матчится (иначе второй заявитель может перезаписать пароль до одобрения администратором первой заявки).

**Ask First:** нет открытых решений — дизайн подтверждён человеком 2026-07-09 (четыре раунда уточнений).

**Never:** не переписывать `CustomerIdentityResolver`/`CustomerConflictResolver` целиком (используются как есть); не хранить пароль из формы регистрации, если завершение отложено до клика — он запрашивается заново на confirm-шаге; не строить отдельный validate-token эндпоинт, confirm сразу проверяет и применяет; не трогать `UserLoginView`; не давать retail-матчу по email из 1С никакого доступа/письма — временно вне скоупа, отклонять так же, как обычный дубликат; не переписывать `docs/.../18-*.md` целиком — только один раздел; concurrency-hardening (`select_for_update`, `MultipleObjectsReturned`, рассинхрон password-reset, `.strip()` в email) — вне скоупа, в `deferred-work.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| B2B-матч по ИНН, email формы совпадает с 1С | Регистрация: tax_id совпадает с User(created_in_1c=True, verification_status=='unverified'), email формы == customer.email | Пароль + `verification_status='pending'` атомарно; письмо `notify_user_verification`-получателям; новый User не создаётся; JWT не выдаются | N/A |
| B2B-матч по ИНН, email формы ОТЛИЧАЕТСЯ от 1С | То же, но email формы != customer.email | Пароль пока не сохраняется; письмо-ссылка на НОВЫЙ email формы | N/A |
| Переход по ссылке (B2B, email менялся) | POST confirm с валидным token + новым паролем | `customer.email` заменён на подтверждённый, пароль установлен, `verification_status='pending'`, письмо админам; JWT не выдаются | N/A |
| Просроченный/неверный/повторный токен | POST confirm с невалидным token или уже `verified`/`pending` записью | 404/410, ничего не меняется | ValidationError |
| Retail-матч по email (1С-клиент, role='retail') | email формы совпадает с User(created_in_1c=True, role='retail', verification_status=='unverified') | Временно вне скоупа: 400 под `email` (тот же текст, что и для дубликата), без привязки, без письма, дубль не создаётся | ValidationError |
| Дубликат (портальный аккаунт, уже верифицированная 1С-запись, или 1С-запись уже в pending через эту фичу) | email/tax_id совпадает с User(created_in_1c=False ИЛИ verification_status != 'unverified') | 400 под полем, без привязки/дубля | ValidationError |
| Сброс пароля непривязанного 1С-клиента | POST password-reset, created_in_1c=True, verification_status=='unverified' | 200 как для несуществующего email | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/users/serializers.py:62-140` -- `validate()` — identify_customer + guard `role != 'retail'` на матч; `create()` ветвится на 2 исхода (B2B-совпадение / B2B-нужен confirm); новый `PortalLinkConfirmSerializer(token, new_password)`
- `backend/apps/users/views/authentication.py` -- `UserRegistrationView.post` — ответ без JWT/PII для matched-случаев; новый `PortalLinkConfirmView` (единственный путь: подтвердить новый email → `pending` + `send_admin_verification_email`)
- `backend/apps/users/tasks.py` -- новая Celery-таска `send_portal_link_confirmation_email` (по образцу `send_password_reset_email`)
- `backend/templates/emails/portal_link_confirmation.{html,txt}` -- новые шаблоны
- `backend/apps/users/urls.py`, `views/__init__.py` -- маршрут `auth/portal-link/confirm/`
- `docs/architecture/18-b2b-verification-workflow.md` -- переписать "Этап 2.5"

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/users/serializers.py` -- `validate()`: `CustomerIdentityResolver().identify_customer({"email":..., "tax_id":...})`; матч с `created_in_1c=True and verification_status == 'unverified' and customer.role != 'retail'` → сохранить в `self._matched_1c_customer`; любой другой матч (включая retail-матч и уже-`pending`-запись через эту же фичу — временно вне скоупа) → `ValidationError` под `email`/`tax_id`, тем же текстом, что и раньше -- идентификация + временное исключение retail + защита от повторного матча pending-записи (round 4)
- [x] `backend/apps/users/serializers.py` -- `create()`: если матч есть и email формы (normalized) == `customer.email` (normalized) → `customer.set_password(password); customer.verification_status = 'pending'; customer.save(update_fields=[...])` одним вызовом, затем `send_admin_verification_email.delay(customer.id)`; выставить `self._pending_admin_review = True` -- B2B-same-email путь, пароль и pending — одной атомарной операцией
- [x] `backend/apps/users/serializers.py` -- `create()`: иначе (email формы отличается) → НЕ сохранять пароль; через `django.core.signing.dumps` собрать токен `{"user_id": customer.id, "new_email": <email формы>}`; поставить `send_portal_link_confirmation_email.delay(customer.id, new_email, confirm_url)` на НОВЫЙ email формы; выставить `self._pending_link_confirmation = True` -- откладывает пароль/email до клика
- [x] `backend/apps/users/serializers.py` -- добавить `PortalLinkConfirmSerializer(token, new_password[validate_password], new_password_confirm)` -- вход для confirm-эндпоинта
- [x] `backend/apps/users/views/authentication.py` -- `UserRegistrationView.post`: если `_pending_admin_review` или `_pending_link_confirmation` установлен на пользователе — не создавать `UserConsent`, не выдавать JWT, вернуть нейтральный ответ (без ФИО/роли найденной записи) -- закрывает утечку PII/токенов из находки ревью
- [x] `backend/apps/users/views/authentication.py` -- новый `PortalLinkConfirmView.post`: `django.core.signing.loads(token, salt=..., max_age=...)` → `{user_id, new_email}`; `user = User.objects.get(pk=user_id, created_in_1c=True)`; если `user.verification_status != "unverified"` → 410 (уже применено или неприменимо); иначе `user.email = new_email; user.set_password(new_password); user.verification_status = "pending"; user.save(...)`, `send_admin_verification_email.delay(user.id)`, ответ без JWT -- единственная точка финализации confirm-ветки
- [x] `backend/apps/users/tasks.py` -- `send_portal_link_confirmation_email(self, user_id, new_email, confirm_url)` по образцу `send_password_reset_email` -- письмо на явно переданный `new_email` (ещё не сохранён в `user.email`)
- [x] `backend/templates/emails/portal_link_confirmation.html` и `.txt` -- новые шаблоны по образцу `password_reset.*`
- [x] `backend/apps/users/urls.py`, `backend/apps/users/views/__init__.py` -- зарегистрировать `PortalLinkConfirmView` на `auth/portal-link/confirm/`
- [x] `backend/tests/integration/test_portal_registration_1c_link.py` (new) -- покрыть всю I/O-матрицу: B2B-match-same-email, B2B-mismatch+confirm, retail-матч → 400, invalid/replay token, duplicate, password-reset
- [x] `docs/architecture/18-b2b-verification-workflow.md` -- переписать "Этап 2.5" под новый flow

**Acceptance Criteria:**
- Given B2B 1С-клиент с tax_id=Y, unverified, email формы совпадает с 1С, when регистрируется, then пароль и `pending` выставлены сразу одной операцией, письмо ушло получателям с `notify_user_verification=True`, новый User не создан, JWT не выданы
- Given тот же клиент, but email формы отличается, when регистрируется, then пароль НЕ сохранён, письмо-ссылка ушла на НОВЫЙ email; when клиент переходит по ссылке и вводит пароль, then `email` заменён, пароль установлен, `pending` выставлен, письмо админам ушло, JWT не выданы
- Given retail 1С-клиент, unverified, email формы совпадает, when регистрируется, then 400 под `email`, ничего не меняется (тот же результат, что и до фичи — временное ограничение)
- Given непривязанный 1С-клиент запрашивает сброс пароля, then ответ идентичен случаю "email не найден" (200, без утечки)
- Given два портальных аккаунта пытаются использовать один ИНН (без гонки, последовательно), then второй получает 400 под `tax_id`, дубль не создаётся

## Spec Change Log

- 2026-07-09: Реализация выявила, что DRF `ModelSerializer` автоматически навешивает field-level `UniqueValidator` на `email` (модель `unique=True`), который сработал бы раньше `validate()` и блокировал сценарий привязки. Добавлено `"email": {"required": True, "validators": []}` в `Meta.extra_kwargs`. *(код впоследствии откачен вместе со всей реализацией — см. запись ниже; вывод про `UniqueValidator` остаётся верным для повторной реализации.)*

- 2026-07-09 (loopback, review_loop_iteration → 1): Adversarial-ревью нашло **intent_gap**: одобренный дизайн "матч по email/ИНН → сразу ставим пароль и верифицируем" не требовал подтверждения владения аккаунтом. Код полностью откачен. **Решение человека (раунд 1):** email-подтверждение перед привязкой вместо мгновенной привязки.

- 2026-07-09 (token budget split): пере-собранная спека (~1605 слов) превышала 900–1600 токенов. Человек выбрал `[S] Split`; 4 hardening-находки (гонки состояний, `MultipleObjectsReturned`, рассинхрон password-reset, `.strip()` в email) вынесены в `deferred-work.md`.

- 2026-07-09 (renegotiation раунд 2, до реализации): человек уточнил дизайн подробнее — B2B (есть ИНН) при совпадающем email не нуждается в клике по ссылке вообще: сразу `pending` + ручное одобрение администратором (переиспользуя существующий `NotificationRecipient.notify_user_verification` + `send_admin_verification_email`, тот же путь, что и для обычных B2B-заявок, включая финальное одобрение через уже существующий `approve_b2b_users`). При несовпадающем email — сначала подтверждение НОВОГО email по ссылке (новый email после подтверждения заменяет старый — единственное согласованное исключение из "1C wins"), затем тот же `pending`-путь. Retail сохраняет исходную (первого раунда) схему "клик по ссылке → мгновенная активация", т.к. в админке нет действия для ручного одобрения retail и совпадение email там гарантировано уже на этапе матчинга.

  **Важное техническое ограничение, обнаруженное при проверке кода** (не от человека, а из чтения `UserLoginView`): вход блокируется только условием `verification_status == "pending"`, `is_active` не проверяется вообще. Поэтому пароль нельзя сохранять раньше, чем `verification_status` встанет в `pending`/`verified` в той же операции — иначе возникает окно, в которое рабочий пароль уже есть, а блокировки входа ещё нет. Отсюда: B2B-same-email путь делает это одним вызовом сразу при регистрации; во всех остальных случаях (B2B-mismatch, retail) пароль не сохраняется до подтверждающего клика.

  **KEEP:** `CustomerIdentityResolver` используется как есть, без переписывания.

- 2026-07-09 (renegotiation раунд 3, до реализации): человек решил временно ограничить доступ через привязку 1С-записи только B2B — retail-ветка (матч по email, клик по ссылке, мгновенная активация через `CustomerConflictResolver`) убрана из скоупа целиком. Retail-матч теперь просто попадает в существующую ветку "любой другой матч → 400", как и было до этой фичи. Это отменяет всё, что раньше планировалось для retail: `PortalLinkConfirmView` больше не ветвится на два исхода (остался только B2B-confirm), `CustomerConflictResolver`/`_handle_portal_registration` в этой спеке больше не используются и не меняются, JWT нигде в этом flow не выдаются. Спека заметно сократилась.

- 2026-07-09 (реализация): Все Execution-задачи выполнены. `PasswordResetRequestView` не потребовал изменений — ответ (200, generic detail) уже идентичен для найденного и ненайденного email независимо от совпадения; тест `TestPasswordResetForUnlinked1CCustomer` фиксирует это как регресс-гвард, а не новую логику. Confirm-токен переиспользует `settings.PASSWORD_RESET_TIMEOUT` (default 259200s) как `max_age` вместо отдельной настройки. Новый тестовый файл (10 тестов) + регресс: `test_auth_registration_tokens.py`, `test_auth_registration_consent.py`, `test_auth_api.py`, `test_auth_logout_api.py`, `test_conflict_resolution_scenarios.py`, `test_customer_identity_resolver.py` — все зелёные (Black/Flake8 чисто). GitNexus MCP-инструменты были недоступны в сессии реализации (сервер не подключился даже после рестарта) — impact-анализ символов выполнен вручную через Read/Grep по Code Map спеки.

- 2026-07-09 (loopback, review_loop_iteration → 2; renegotiation раунд 4, adversarial-ревью после первой реализации): Blind Hunter нашёл **intent_gap** внутри frozen I/O-матрицы: guard `verification_status != 'verified'` матчил 1С-запись, уже переведённую в `pending` этой же фичей (первая заявка ждёт одобрения администратора) — второй заявитель, знающий тот же ИНН и тот же email, мог перезаписать пароль pending-записи до одобрения (итоговый пароль после `approve_b2b_users` принадлежал бы второму заявителю). **Решение человека (раунд 4):** ужесточить guard до `verification_status == 'unverified'` — строго один матч на запись, всё остальное (включая уже-`pending` через эту же фичу) уходит в обычную ветку "дубликат → 400". I/O-матрица и Boundaries обновлены; `validate()` в `serializers.py` и тест `test_pending_1c_customer_cannot_be_rematched` (в `test_portal_registration_1c_link.py`) приведены в соответствие.

  Отдельно, **patch** (root cause вне frozen, тривиально фиксируется без изменения дизайна): отсутствовала валидация занятости НОВОГО email формы в mismatch-ветке при регистрации — коллизия обнаруживалась только на confirm-клике как необработанный `IntegrityError` (500). Добавлена явная проверка в `validate()` (до отправки confirm-ссылки) + defensive `try/except IntegrityError` (409) в `PortalLinkConfirmView` как fallback на гонку между регистрацией и кликом.

  **KEEP:** остальной дизайн (email-подтверждение перед привязкой, атомарность пароль+pending, "1C wins", retail временно вне скоупа) подтверждён ревью без замечаний и не менялся.

## Design Notes

При регистрации доступны только tax_id/email; матч теперь возможен только для B2B (есть tax_id) — у retail нет tax_id, а без него `identify_customer` матчит только по точному совпадению email, что при отключённой retail-ветке всегда попадает в error-branch.

Токен confirm-ссылки — `django.core.signing.dumps({"user_id": ..., "new_email": ...}, salt="portal-link-confirm")` с `max_age` при `loads`. Подписанный токен сам несёт нужные данные — отдельный `key_salt`-генератор или таблица токенов не нужны.

Флоу не вызывает `CustomerConflictResolver` — его задача "поставить в очередь на верификацию", а не "верифицировать сразу". Аудит — там, где он уже есть по умолчанию для pending B2B (видимость через `verification_status` в Django Admin + email `notify_user_verification`), без `SyncConflict`/`CustomerSyncLog`.

## Verification

**Commands:**
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/integration/test_portal_registration_1c_link.py -v` -- expected: все сценарии зелёные
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/unit/test_conflict_resolution.py backend/tests/unit/test_customer_identity_resolver.py -v` -- expected: регресс не сломан

**Manual checks (if no CLI):**
- В Django Admin найти тестовый B2B-1С-импорт без пароля, зарегистрироваться с его ИНН и другим email — убедиться, что письмо ушло на новый email, а после клика запись видна в списке pending-верификации и одобряется через `approve_b2b_users`

## Suggested Review Order

**Идентификация и защита от повторного матча**

- Точка входа: матч по ИНН/email через `CustomerIdentityResolver`, guard строго на `unverified` (round 4 fix против повторного матча pending-записи).
  [`serializers.py:75`](../../backend/apps/users/serializers.py#L75)

- Проверка занятости нового email в mismatch-ветке до отправки confirm-ссылки (round 4 patch — раньше падало на confirm-клике).
  [`serializers.py:117`](../../backend/apps/users/serializers.py#L117)

**Ветвление create(): same-email vs mismatch**

- `create()` делегирует найденной 1С-записи вместо создания нового User.
  [`serializers.py:135`](../../backend/apps/users/serializers.py#L135)

- `_link_matched_1c_customer`: атомарно пароль+pending при совпадении email, иначе — подписанный токен на новый email формы.
  [`serializers.py:174`](../../backend/apps/users/serializers.py#L174)

- `PortalLinkConfirmSerializer` — вход для confirm-эндпоинта (token + новый пароль).
  [`serializers.py:208`](../../backend/apps/users/serializers.py#L208)

**Ответ регистрации: без JWT/PII/consent для matched-путей**

- `UserRegistrationView.post` — ветка `pending_1c_link` пропускает создание `UserConsent` и не выдаёт JWT.
  [`authentication.py:119`](../../backend/apps/users/views/authentication.py#L119)

**Confirm-эндпоинт**

- `PortalLinkConfirmView.post` — единственная точка финализации mismatch-ветки: декодирует токен, применяет email+пароль+pending.
  [`authentication.py:572`](../../backend/apps/users/views/authentication.py#L572)

- Defensive `except IntegrityError` — fallback на гонку между регистрацией и confirm-кликом (round 4 patch).
  [`authentication.py:599`](../../backend/apps/users/views/authentication.py#L599)

**Инфраструктура**

- Новая Celery-таска на образе `send_password_reset_email`.
  [`tasks.py:328`](../../backend/apps/users/tasks.py#L328)

- Маршрут `auth/portal-link/confirm/`.
  [`urls.py:56`](../../backend/apps/users/urls.py#L56)

- Раздел "Этап 2.5" — новый flow в архитектурной документации.
  [`18-b2b-verification-workflow.md:173`](../../docs/architecture/18-b2b-verification-workflow.md#L173)

**Тесты**

- Regression-guard: повторный матч уже-pending записи не проходит и не перезаписывает пароль.
  [`test_portal_registration_1c_link.py:129`](../../backend/tests/integration/test_portal_registration_1c_link.py#L129)

- "1C wins": ФИО/роль/компания формы не переопределяют найденную запись.
  [`test_portal_registration_1c_link.py:103`](../../backend/tests/integration/test_portal_registration_1c_link.py#L103)

- Полная I/O-матрица спеки (13 тестов): same-email, mismatch+confirm, invalid/replay token, retail out-of-scope, дубликаты, password-reset.
  [`test_portal_registration_1c_link.py:1`](../../backend/tests/integration/test_portal_registration_1c_link.py#L1)
