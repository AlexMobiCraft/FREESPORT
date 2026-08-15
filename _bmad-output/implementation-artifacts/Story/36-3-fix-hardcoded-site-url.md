# Story 36.3: Устранение захардкоженного SITE_URL в письме сброса пароля

**Epic:** 36 — Critical Security & Export Fixes (Week 1)
**Story ID:** 36.3
**Status:** review
**Priority:** 🔴 CRITICAL
**Source:** tech-debt.md #7

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## User Story

Как Developer,
я хочу, чтобы в письме сброса пароля адрес сайта брался из `settings.SITE_URL`, а не был захардкожен,
чтобы ссылка восстановления пароля была корректной в production, а не указывала на `localhost:3000`.

---

## Контекст и суть дефекта (tech-debt #7)

В `PasswordResetRequestView.post` ссылка восстановления пароля собирается с захардкоженным доменом:

```python
# backend/apps/users/views/authentication.py:334
reset_url = f"http://localhost:3000/password-reset/confirm/{uid}/{token}/"
```

В production пользователь получает письмо со ссылкой на `localhost:3000` — **сброс пароля на проде фактически неработоспособен**.

### Анализ кодовой базы

- `SITE_URL` уже определён в настройках: `base.py:568` — `SITE_URL = config("SITE_URL", default="http://localhost:3000")`. Значение прокидывается в контейнеры через env (`docker-compose*.yml`, переменная `SITE_URL`).
- Захардкоженный адрес сайта в backend остался **только в одном месте** — `authentication.py:334`. Остальные места уже корректны:
  - `apps/users/tasks.py:75,344` — используют `settings.SITE_URL`.
  - `apps/orders/tasks.py:203,305` — используют `getattr(settings, "SITE_URL", ...)`.
- `settings` **не импортирован** в `authentication.py` — импорт нужно добавить (`from django.conf import settings`).
- `reset_url` собирается во view и передаётся в Celery-задачу `send_password_reset_email.delay(user.id, reset_url)` (строка 337) — правка локальна, задачу и шаблон письма менять не нужно.

---

## Acceptance Criteria

### AC-1: Базовый адрес из settings.SITE_URL

**Given** код Password Reset в `apps/users/views/authentication.py`,
**When** формируется ссылка восстановления пароля,
**Then** базовый адрес берётся из `settings.SITE_URL`; захардкоженный `http://localhost:3000` удалён.

### AC-2: Корректная ссылка в production

**Given** окружение production (`SITE_URL` указывает на production-домен),
**When** пользователь запрашивает сброс пароля,
**Then** письмо содержит ссылку на production-домен, путь `/password-reset/confirm/{uid}/{token}/` сохранён.

### AC-3: Отсутствие двойного слэша

**Given** значение `SITE_URL` с завершающим слэшем или без него,
**When** формируется `reset_url`,
**Then** в URL нет `//` между доменом и путём (склейка устойчива к trailing slash).

### AC-4: Прочие места проверены

**Given** backend-код,
**When** выполняется проверка хардкода адреса сайта,
**Then** подтверждено: `authentication.py:334` — единственное такое место; остальные уже используют `settings.SITE_URL` (фиксируется в Dev Agent Record).

---

## Рекомендуемое решение

`backend/apps/users/views/authentication.py`:

1. Добавить импорт: `from django.conf import settings` (в блок импортов Django, строки 8-12).
2. Заменить строку 334:

```python
reset_url = f"{settings.SITE_URL.rstrip('/')}/password-reset/confirm/{uid}/{token}/"
```

`rstrip('/')` закрывает AC-3 — устойчивость к завершающему слэшу в `SITE_URL`.

> Фронтенд-маршрут подтверждён: путь `/password-reset/confirm/...` остаётся прежним, меняется только базовый адрес.

---

## Структура файлов (изменения)

```
backend/
  apps/users/views/authentication.py        [MODIFY] — импорт settings + reset_url из SITE_URL
  apps/users/tests/ (или tests/unit|integration) [MODIFY/CREATE] — тест формирования reset_url
```

---

## Тесты

**Файл:** существующий тест-набор Password Reset (см. `tests/unit/test_email_tasks.py` — там уже мокается `settings.SITE_URL`; найти/дополнить тесты `PasswordResetRequestView`).

Кейсы:
- `POST` на запрос сброса пароля с `override_settings(SITE_URL="https://freesport.ru")` → `reset_url`, переданный в `send_password_reset_email.delay`, начинается с `https://freesport.ru/password-reset/confirm/`. Мок задачи (`mock.patch` на `send_password_reset_email.delay`) — проверить аргумент.
- `SITE_URL` с завершающим слэшем (`"https://freesport.ru/"`) → в `reset_url` нет `//` перед `password-reset` (AC-3).
- Запрос для несуществующего email по-прежнему возвращает 200 без отправки письма (регресс — security-инвариант не нарушен).

### Запуск

```bash
make test-unit
docker compose --env-file .env -f docker/docker-compose.test.yml exec backend \
  pytest -xvs apps/users/tests/
```

**Покрытие:** `users` — критический модуль; изменённая ветка ≥ 90%.

---

## Связанные истории

- **Эпик 36** — security/bugfix-спринт. С 36.1 и 36.2 общих файлов нет — независимая story, самая малая по объёму в эпике.

---

## Примечания для разработчика

1. `settings` в `authentication.py` **не импортирован** — не забудь добавить импорт, иначе `NameError` в рантайме.
2. Правка строго локальна: Celery-задача `send_password_reset_email` и шаблон письма не меняются — они уже получают готовый `reset_url`.
3. AC-4 — это не правка кода, а проверка: пройди по результатам `grep` (раздел «Анализ»), подтверди в Dev Agent Record, что других хардкодов адреса сайта нет.
4. `getattr(settings, "SITE_URL", ...)` в `orders/tasks.py` — оставить как есть, это не хардкод, а defensive-fallback; в скоуп story не входит.

---

## Definition of Done

- [x] `from django.conf import settings` добавлен в `authentication.py` — **уже был импортирован** (строка 8), правка не потребовалась
- [x] `reset_url` формируется из `settings.SITE_URL`, хардкод `localhost:3000` удалён
- [x] Склейка устойчива к завершающему слэшу в `SITE_URL` (AC-3)
- [x] Тест: `reset_url` использует production-домен при заданном `SITE_URL`
- [x] Тест: нет двойного слэша при `SITE_URL` с trailing slash
- [x] Регресс: запрос для несуществующего email возвращает 200 без письма
- [x] AC-4 зафиксирован в Dev Agent Record (других хардкодов нет)
- [x] Тесты проходят (прогон через `docker-compose.test.yml`, см. Dev Agent Record)
- [x] Black / Flake8 / mypy без ошибок; **isort — предсуществующее расхождение**, см. Dev Agent Record

---

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (Devin CLI), 2026-08-15. Ветка `fix/password-reset-site-url`, baseline `ba52e28b` (= `origin/develop`), PR #92.

### Debug Log References

- `npx gitnexus impact PasswordResetRequestView --direction upstream` → `risk: LOW`, `impactedCount: 0`, затронутых процессов нет. Правка локальна, как и предполагала стори.
- `npx gitnexus detect-changes` **применить не удалось**: индекс привязан к основному клону (`C:\Users\1\DEV\FREESPORT`), а работа шла в отдельном worktree, поэтому команда показала символы чужой ветки, а не диф стори. Объём подтверждён `git diff` — 4 файла, из них продакшен-код один.

### Completion Notes List

1. **Импорт `settings` уже был на месте.** Раздел «Примечания для разработчика» п. 1 и анализ (строка 38) утверждают, что `settings` в `authentication.py` не импортирован и `NameError` неизбежен без правки. Фактически `from django.conf import settings` стоит на строке 8 и используется ниже в `PortalLinkConfirmView` (`PASSWORD_RESET_TIMEOUT`). Правка импортов не потребовалась.
2. **Координаты в стори сдвинулись.** Стори указывает `authentication.py:334` (и `:337` для `delay`) на момент 2026-05-18. Фактически на `ba52e28b` это строки 377 и 380 — файл вырос за счёт `PasswordResetRequestView`-гарда для записей 1С и `PortalLinkConfirmView`. Дефект тот же, номера другие.
3. **AC-3 сначала был реализован неверно и исправлен по тексту стори.** В первой итерации `rstrip('/')` был сознательно опущен «ради консистентности» с `serializers.py:276`, где та же склейка идёт без него. Это прямое нарушение AC-3, обнаруженное при сверке со story-файлом; исправлено, тест на завершающий слэш добавлен. Вывод на будущее: story-файл читать до правки, а не после.
4. **AC-4 подтверждён замером.** `grep -nE "[\"']https?://(localhost|127\.0\.0\.1)" backend/apps/**/*.py` даёт три совпадения: `authentication.py:377` (исправлено) и `orders/tasks.py:203,305` — последние используют `getattr(settings, "SITE_URL", ...)`, то есть defensive-fallback, а не хардкод, и в скоуп не входят (п. 4 примечаний). На этот fallback опираются тесты `tests/integration/test_onec_export.py:767-815` (проверяют отсутствие падения при удалённом `SITE_URL`) — трогать их нельзя. В `backend/templates/emails/` абсолютных адресов нет вовсе.
5. **Тесты положены в `tests/integration/`, а не в `apps/users/tests/`.** Стори допускала оба варианта. Проверка идёт через HTTP (`APIClient` + реальный URL-роутинг), поэтому по правилу авторазметки каталога это `integration`. Дополнять `tests/unit/test_email_tasks.py` (предложение стори) неуместно: там тестируется Celery-задача, которая `reset_url` получает готовым и не собирает.
6. **Прогоны.** `tests/integration/test_password_reset_link.py` + `test_portal_registration_1c_link.py` + `tests/unit/test_email_tasks.py` → `40 passed`. Расширенный контур (`apps/users`, auth-интеграции, `tests/regression/test_epic_28_intact.py`, `tests/unit/test_email_tasks.py`) на первой итерации → `58 passed, 2 skipped` (оба skip преднастроены в `test_auth_api.py`). До правки новые тесты падали дословно на дефекте: `http://localhost:3000/password-reset/confirm/MQ/...`.
7. **Линтеры.** `black --check` и `flake8` (`--max-line-length=120`) чисты. `mypy` даёт 8 ошибок, все в чужих файлах (`settings/staging.py`, `settings/development.py`, `orders/services/order_numbering.py`, `orders/tasks.py`, `common/utils/consent_audit.py`) — предсуществующие, в `authentication.py` ни одной; в CI шаг стоит `continue-on-error: true`. **`isort --check-only` падает на `authentication.py`**, требуя схлопнуть многострочные импорты `apps.common.utils.consent_audit` и `..tasks` — блоки, которых диф не касается: расхождение предсуществующее (конфликт настроек isort с `line-length` black). В CI isort не запускается ни в одном workflow, поэтому приведение импортов не делалось — иначе в PR попал бы несвязанный шум. Кандидат в отдельную задачу «согласовать isort с black».
8. **Не проверено и требует человека:** значение `SITE_URL` в `.env.prod`. Дефолт в `base.py:577` — тот же `http://localhost:3000`, поэтому при незаданной переменной правка ничего не чинит. `docker/docker-compose.prod.yml:72` подставляет `${SITE_URL}` без дефолта, `docs/deploy/domain-migration-optisport.md:221` называет `SITE_URL=https://optisport.ru` — косвенно указывает, что переменная задана, но подтверждения на сервере нет.
9. **Смежное наблюдение (в скоуп не входит):** `apps/users/serializers.py:276` собирает `confirm_url` для portal-link тем же способом и без `rstrip('/')`, то есть остаётся уязвимым к завершающему слэшу. Код относится к отключённой автопривязке (мёртвый слой, см. `deferred-work.md`, запись от 2026-07-26), поэтому правка отложена, а не сделана заодно.

### File List

| Файл | Тип | Что сделано |
|---|---|---|
| `backend/apps/users/views/authentication.py` | MODIFY | `reset_url` собирается из `settings.SITE_URL.rstrip('/')`; хардкод удалён (AC-1, AC-3) |
| `backend/tests/integration/test_password_reset_link.py` | CREATE | 4 теста: хост из `SITE_URL` (параметризован по завершающему слэшу), совпадение пути с маршрутом фронта, регресс на неизвестный email |
| `_bmad-output/planning-artifacts/tech-debt.md` | MODIFY | Пункт #7 отмечен закрытым |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | MODIFY | `36-3-fix-hardcoded-site-url`: ready-for-dev → review; запись в журнал |

## Change Log

- 2026-05-18: Создана Story 36.3 (bmad-create-story). Status: ready-for-dev.
- 2026-08-15: Реализована. Status: ready-for-dev → review, PR #92. AC-1..AC-4 закрыты. Правка продакшен-кода — одна строка; импорт `settings` оказался уже на месте, координаты строк в тексте стори устарели (334 → 377). AC-3 в первой итерации был опущен и исправлен по тексту стори. `isort` оставлен в предсуществующем расхождении осознанно (в CI не запускается).
