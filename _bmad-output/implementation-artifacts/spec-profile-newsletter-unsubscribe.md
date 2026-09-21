---
title: 'Отписка от рассылки в личном кабинете и подписка при регистрации'
type: 'feature'
created: '2026-09-21'
status: 'done'
baseline_commit: 'b9590d7a79bfd27b68bd200d89e0d955178e2d58'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-marketing-consent-page-link.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** П. 7 «Согласия на получение рекламы» (`/marketing-consent`) обещает отзыв согласия снятием отметки в личном кабинете, а такой функции нет. Кроме того, регистрация с галочкой рассылки пишет только `UserConsent(marketing_email)`, но не создаёт запись `Newsletter`. Рассылка уходит только активным `Newsletter`, так что зарегистрированный с согласием человек писем не получит, а кабинет показал бы ему «не подписан».

**Approach:**
- Upsert подписки выносится из `SubscribeSerializer.create` в сервис. Его зовут подписка и регистрация с согласием.
- Два эндпоинта для авторизованного пользователя: статус и отписка. Подписка ищется по email пользователя.
- В кабинете `/profile` — блок «Рассылка» со статусом и кнопкой «Отписаться». Повторно подписаться можно только через форму на главной.

## Boundaries & Constraints

**Always:**
- Сервис `activate_newsletter_subscription(email, ip_address, user_agent, user=None)` повторяет текущее поведение `SubscribeSerializer.create`, включая `select_for_update`, savepoint на гонку `IntegrityError`, `rotate_unsubscribe_token()` и реактивацию. Дополнительно он проставляет `user`, если тот передан, а у записи он пуст. Поведение `/subscribe/` не меняется.
- Регистрация зовёт сервис в той же транзакции, что и запись `UserConsent(marketing_email)`, и только при `_marketing_consent`, в обеих ветках источника (`registration`, `1c_link`). Email — `user.email.lower().strip()`.
- `GET /api/v1/newsletter/me/` → `200 {"subscribed": bool}`. `POST /api/v1/newsletter/me/unsubscribe/` → `200 {"subscribed": false}`, идемпотентно: у записи вызывается `Newsletter.unsubscribe()`, при отсутствии записи тоже 200. Оба эндпоинта `IsAuthenticated`, аноним получает 401. `DatabaseError` → 503 `unsubscribe_processing_failed`, как у существующей отписки.
- Отписка в кабинете не пишет и не удаляет `UserConsent`. Факт отзыва фиксирует `Newsletter.unsubscribed_at`, как и у отписки по ссылке.
- Тексты блока:
  - подписан — «Вы подписаны на информационные и рекламные рассылки OPTISPORT по электронной почте.» и кнопка «Отписаться»;
  - не подписан — «Вы не подписаны на рассылку.»;
  - ошибка — toast «Не удалось отписаться. Попробуйте позже.».
- Схема: `openapi.yaml` перегенерируется через `spectacular --validate`, типы фронта — через `npm run generate:types`.
- Перед правкой символа — `npx gitnexus impact`. Pytest — последовательно.

**Ask First:** новый источник `UserConsent`; изменение модели `Newsletter` или миграции; подписка из кабинета; диалог подтверждения отписки.

**Never:** удалять запись `Newsletter`; искать подписку по email из тела запроса; менять ответы `/subscribe/` и отписки по токену.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Регистрация с галочкой, email новый | `marketing_consent: true` | `Newsletter(email, user=user, is_active=True)` + `UserConsent` | Ошибка БД откатывает регистрацию целиком (как сейчас) |
| Регистрация с галочкой, email ранее отписан | неактивный `Newsletter` | Реактивирован, новый токен, `user` проставлен | — |
| Регистрация без галочки | `marketing_consent: false` | `Newsletter` не создаётся и не меняется | — |
| Статус | подписка активна / неактивна / нет | `subscribed: true` / `false` / `false` | — |
| Отписка | активная подписка | `is_active=False`, `unsubscribed_at` задан | — |
| Повторная отписка | уже неактивна или записи нет | 200, `unsubscribed_at` не меняется | — |
| Аноним | без токена | 401 | — |

</frozen-after-approval>

## Code Map

- `backend/apps/common/serializers.py:245` -- `SubscribeSerializer.create`: upsert, переносится в сервис
- `backend/apps/common/services/` -- `newsletter_unsubscribe.py` рядом; новый `newsletter_subscription.py`
- `backend/apps/users/views/authentication.py:182` -- запись `marketing_email` при регистрации
- `backend/apps/common/views.py`, `backend/apps/common/urls.py` -- эндпоинты newsletter
- `frontend/src/services/unsubscribeService.ts` -- образец сервиса
- `frontend/src/app/(blue)/profile/page.tsx`, `profile/profile/page.tsx` -- страница профиля (два дубля, обе рендерят `ProfileForm`)

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/common/services/newsletter_subscription.py` -- сервис upsert; `SubscribeSerializer.create` переводится на него
- [x] `backend/apps/users/views/authentication.py` -- вызов сервиса рядом с `UserConsent(marketing_email)`
- [x] `backend/apps/common/views.py` + `urls.py` -- `newsletter_me`, `newsletter_me_unsubscribe` с `extend_schema`
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- перегенерировать
- [x] `frontend/src/services/newsletterSettingsService.ts` -- `getStatus()`, `unsubscribe()`
- [x] `frontend/src/components/business/NewsletterSettings/` -- блок + тесты (загрузка, оба статуса, отписка, ошибка)
- [x] обе страницы профиля -- рендер блока под `ProfileForm`
- [x] backend-тесты -- сервис (новый/реактивация/гонка), регистрация с галочкой и без, эндпоинты по матрице

**Acceptance Criteria:**
- Given авторизованный подписанный пользователь, when он нажимает «Отписаться» в `/profile`, then блок показывает «Вы не подписаны на рассылку.», а `MarketingDeliveryService` возвращает `suppressed` для его подписки.
- Given существующие тесты `/subscribe/`, when они запускаются после рефакторинга, then проходят без изменений.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/common apps/users tests/integration` -- expected: зелёный
- `check_openapi_sync` (рецепт из памяти, `--schema-file /contract/api/openapi.yaml`) -- expected: синхронен
- `cd frontend && npx vitest run && npx tsc --noEmit && npx eslint src` -- expected: зелёный

## Spec Change Log

- Ревью, 2026-09-21. Подписка в кабинете ищется не только по email учётной записи, но и по привязке `Newsletter.user` (`email__iexact`). Это закрывает случай, когда email учётной записи сменили в админке: без поиска по привязке отозвать согласие из кабинета было нельзя. Добавлены 503 для чтения статуса и троттлинг отписки. KEEP: email из тела запроса не принимается.
- Ветка `_pending_link_confirmation` не создаёт подписку: email записи 1С отличается от адреса формы. Ветка — мёртвый код (автопривязка отключена 2026-07-26).

## Suggested Review Order

**Подписка при регистрации**

- Общий upsert подписки: форма и регистрация, токен ротируется всегда
  [`newsletter_subscription.py:20`](../../backend/apps/common/services/newsletter_subscription.py#L20)

- Регистрация с галочкой создаёт `Newsletter` в той же транзакции
  [`authentication.py:198`](../../backend/apps/users/views/authentication.py#L198)

- Форма подписки переведена на сервис без изменения поведения
  [`serializers.py:271`](../../backend/apps/common/serializers.py#L271)

**Отписка из кабинета**

- Поиск подписок пользователя: email без учёта регистра или привязка
  [`newsletter_unsubscribe.py:39`](../../backend/apps/common/services/newsletter_unsubscribe.py#L39)

- Эндпоинты статуса и отписки, 503 на ошибку БД
  [`views.py:800`](../../backend/apps/common/views.py#L800)

- Блок «Рассылка»: строгий разбор ответа, aria-live
  [`NewsletterSettings.tsx:22`](../../frontend/src/components/business/NewsletterSettings/NewsletterSettings.tsx#L22)

**Тесты**

- Регистрация и сервис
  [`test_newsletter_profile.py:102`](../../backend/tests/integration/test_newsletter_profile.py#L102)

- Кабинет: поиск по привязке после смены email
  [`test_newsletter_profile.py:220`](../../backend/tests/integration/test_newsletter_profile.py#L220)
