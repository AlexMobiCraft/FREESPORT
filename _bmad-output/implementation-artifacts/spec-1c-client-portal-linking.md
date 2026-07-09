---
title: 'Привязка существующего 1С-клиента к регистрации на портале'
type: 'feature'
created: '2026-07-09'
status: 'in-progress'
context: []
baseline_commit: 'e63b07c609f6bb2ba30a0bc54c1f40b07a746582'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Клиент, уже выгруженный из 1С (`created_in_1c=True`, пароль не задан), при регистрации на сайте с тем же email/ИНН получает жёсткий отказ "email уже существует" без пути восстановления доступа. Готовые сервисы `CustomerIdentityResolver`/`CustomerConflictResolver._handle_portal_registration` для этого написаны, но нигде не вызываются — только в тестах; проверки дубля по ИНН нет; сброс пароля пускает непривязанного 1С-клиента в обход верификации.

**Approach:** Подключить эти сервисы в `UserRegistrationSerializer.validate()/create()`: матч с непривязанной 1С-записью → привязать пароль и верифицировать вместо создания дубля; матч с занятым email/ИНН → понятная ошибка вместо создания дубля. Закрыть обход через сброс пароля для непривязанных 1С-профилей. Актуализировать `docs/architecture/18-b2b-verification-workflow.md`.

## Boundaries & Constraints

**Always:** данные существующей 1С-записи, кроме пароля/verification_status/is_verified, не менять ("1C wins"); роль из формы регистрации при привязке игнорируется — берётся роль из 1С; `PasswordResetRequestView` не должен раскрывать существование аккаунта (тот же 200 всегда); изменения — внутри `transaction.atomic()` (уже есть в `resolve_conflict`).

**Ask First:** нет открытых решений — дизайн однозначен благодаря принципу "1C wins".

**Never:** не переписывать `CustomerIdentityResolver`/`CustomerConflictResolver` целиком; не трогать frontend (400-ошибки уже рендерятся из любого поля); не трогать `UserLoginView`/pending-проверку (Epic 29.2); не переписывать `docs/.../18-*.md` целиком — только два раздела.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Привязка 1С-клиента (email или ИНН) | Регистрация email/tax_id совпадает с User(created_in_1c=True, verification_status='unverified') | Пароль ставится на найденной записи, verification_status='verified', is_verified=True, новый User не создаётся; SyncConflict+CustomerSyncLog+письмо админу | N/A |
| Дубликат (портальный аккаунт или уже привязанный 1С) | Регистрация email/tax_id совпадает с User(created_in_1c=False ИЛИ verification_status='verified') | 400 под соответствующим полем, ссылка на вход/восстановление пароля, дубль не создаётся | ValidationError |
| Сброс пароля непривязанного 1С-клиента | POST password-reset, email → User(created_in_1c=True, verification_status='unverified') | 200 как обычно, письмо не отправляется (форсирует регистрацию) | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/users/serializers.py:62-113` -- `UserRegistrationSerializer` — заменить безусловный блок по email на ветвление через identity resolver
- `backend/apps/users/services/identity_resolution.py` -- `CustomerIdentityResolver.identify_customer()` — использовать как есть
- `backend/apps/users/services/conflict_resolution.py:116-138` -- `_handle_portal_registration` — добавить `is_verified=True`
- `backend/apps/users/views/authentication.py:290-352` -- `PasswordResetRequestView.post` — добавить проверку unlinked-1С
- `docs/architecture/18-b2b-verification-workflow.md` -- обновить 2 устаревших раздела

## Tasks & Acceptance

**Execution:**
- [ ] `backend/apps/users/services/conflict_resolution.py` -- в `_handle_portal_registration` добавить `existing_customer.is_verified = True` рядом с `verification_status = "verified"` -- закрывает разрыв между двумя флагами, B2B-цены доступны сразу
- [ ] `backend/apps/users/serializers.py` -- в `validate()` вызвать `CustomerIdentityResolver().identify_customer({"email": attrs.get("email"), "tax_id": attrs.get("tax_id")})`; матч с `created_in_1c=True and verification_status != 'verified'` → сохранить в `self._matched_1c_customer`, не поднимать ошибку; любой другой матч → ValidationError с текстом про вход/восстановление; убрать безусловный `exists()` из `validate_email` -- основной сценарий привязки + устранение дублей по email/ИНН
- [ ] `backend/apps/users/serializers.py` -- в `create()`: если `self._matched_1c_customer` установлен, вызвать `CustomerConflictResolver().resolve_conflict(self._matched_1c_customer, {**validated_data, "password": password}, "portal_registration")` и вернуть найденного пользователя вместо `create_user()`; сохранить логику `_marketing_consent` -- подключает готовый сервис
- [ ] `backend/apps/users/views/authentication.py` -- в `PasswordResetRequestView.post`, после `User.objects.get(...)`, если `user.created_in_1c and user.verification_status == "unverified"` — пропустить отправку письма, как при `DoesNotExist` -- закрывает обход верификации
- [ ] `backend/tests/integration/test_portal_registration_1c_link.py` (new) -- покрыть 3 сценария I/O-матрицы -- фиксирует контракт
- [ ] `docs/architecture/18-b2b-verification-workflow.md` -- обновить раздел "Django Admin Interface" (уже реализован) и добавить описание сценария привязки -- убирает расхождение с кодом

**Acceptance Criteria:**
- Given 1С-клиент с tax_id=Y и unverified-статусом, when регистрируется с другим email и тем же tax_id, then получает пароль на существующей записи, роль остаётся из 1С, новый User не создаётся
- Given привязка произошла, then созданы `SyncConflict(conflict_type='portal_registration_blocked')` и `CustomerSyncLog`, письмо на `CONFLICT_NOTIFICATION_EMAIL` поставлено в очередь
- Given непривязанный 1С-клиент запрашивает сброс пароля, then ответ идентичен случаю "email не найден" (200, без утечки)
- Given два портальных аккаунта пытаются использовать один ИНН, then второй получает 400 под `tax_id`, дубль не создаётся

## Spec Change Log

## Design Notes

Приоритет резолвера (onec_id → onec_guid → tax_id → email) не меняется; при регистрации доступны только tax_id/email, поэтому B2B-форма матчится по ИНН, retail — по email.

## Verification

**Commands:**
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/integration/test_portal_registration_1c_link.py -v` -- expected: все сценарии зелёные
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec -T backend pytest backend/tests/unit/test_conflict_resolution.py backend/tests/unit/test_customer_identity_resolver.py -v` -- expected: регресс не сломан

**Manual checks (if no CLI):**
- В Django Admin найти тестовый 1С-импорт, привязать через `/api/v1/auth/register/`, убедиться что `is_verified`/`verification_status` обновились и запись в `SyncConflict` появилась
</content>
