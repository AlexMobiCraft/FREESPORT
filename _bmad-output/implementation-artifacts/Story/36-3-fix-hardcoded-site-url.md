# Story 36.3: Устранение захардкоженного SITE_URL в письме сброса пароля

**Epic:** 36 — Critical Security & Export Fixes (Week 1)
**Story ID:** 36.3
**Status:** ready-for-dev
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

- [ ] `from django.conf import settings` добавлен в `authentication.py`
- [ ] `reset_url` формируется из `settings.SITE_URL`, хардкод `localhost:3000` удалён
- [ ] Склейка устойчива к завершающему слэшу в `SITE_URL` (AC-3)
- [ ] Тест: `reset_url` использует production-домен при заданном `SITE_URL`
- [ ] Тест: нет двойного слэша при `SITE_URL` с trailing slash
- [ ] Регресс: запрос для несуществующего email возвращает 200 без письма
- [ ] AC-4 зафиксирован в Dev Agent Record (других хардкодов нет)
- [ ] `make test-unit` проходит
- [ ] Black / Flake8 / isort / mypy без ошибок

---

## Dev Agent Record

### Agent Model Used

_(заполняется dev-агентом)_

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-05-18: Создана Story 36.3 (bmad-create-story). Status: ready-for-dev.
