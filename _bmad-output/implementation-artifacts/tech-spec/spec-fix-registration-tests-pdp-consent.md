---
title: 'Исправление тестовых регистраций с обязательным pdp_consent'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
route: 'one-shot'
context: []
---

# Исправление тестовых регистраций с обязательным pdp_consent

## Intent

**Problem:** После введения обязательного согласия на обработку персональных данных старые тестовые payload'ы регистрации падали на `pdp_consent` раньше целевых проверок пароля, B2B-полей и catalog API.

**Approach:** Обновить только тестовые данные регистрации, добавив явное `pdp_consent: True` в сценарии, где согласие не является предметом проверки.

## Suggested Review Order

**Тестовые payload'ы регистрации**

- Unit-тесты снова проверяют свои целевые ошибки, а не отсутствие согласия.
  [`test_user_serializers.py:37`](../../backend/tests/unit/test_serializers/test_user_serializers.py#L37)

- Integration helper принимает актуальный контракт `/auth/register/` для catalog API.
  [`test_catalog_api.py:129`](../../backend/tests/integration/test_catalog_api.py#L129)
