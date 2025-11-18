# Технический долг FREESPORT

Этот документ отслеживает технический долг проекта, включая известные проблемы, рекомендации по улучшению и задачи на будущее.

---

## Активный технический долг

### SEC-001: Rate Limiting для Newsletter Subscribe Endpoint

**Статус:** ✅ RESOLVED (2025-11-18)
**Приоритет:** MEDIUM
**Story:** 11.3 - Backend API Design
**Файлы:**
- `backend/freesport/settings/production.py:118-129`
- `backend/apps/common/views.py:306-393`

**Описание:**
Endpoint `/api/v1/subscribe` требует rate limiting для защиты от SPAM атак в production.

**Риски:**
- Автоматизированные подписки (bots)
- SPAM атаки на базу данных
- Перегрузка сервера

**Решение (реализовано):**
```python
# backend/freesport/settings/production.py
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # Наследуем настройки из base.py
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/hour",  # SPAM protection для /subscribe endpoint
        "user": "100/hour",  # Для авторизованных пользователей
    },
}
```

**QA Review:** docs/qa/gates/11.3-backend-api-design.yml

---

## Запланированные улучшения

### FUTURE-001: Token-based Unsubscribe (Story 11.4)

**Статус:** Запланировано
**Приоритет:** LOW
**Story:** 11.4 (будущая)

**Описание:**
Текущая реализация unsubscribe использует email в body. Для улучшения UX и соответствия индустриальным стандартам рекомендуется реализовать token-based unsubscribe.

**Преимущества:**
- One-click unsubscribe (RFC 8058 compliance)
- Защита от злоупотреблений (никто не может отписать чужой email)
- Улучшенная email deliverability
- Соответствие GDPR

**Рекомендуемая реализация:**

1. **Backend:**
   ```python
   # Добавить поле в Newsletter model
   unsubscribe_token = models.UUIDField(
       default=uuid.uuid4,
       unique=True,
       db_index=True,
   )

   # Новый endpoint
   # GET /api/v1/unsubscribe/{token}/
   ```

2. **Email Templates:**
   - Включить ссылку отписки в footer: `https://freesport.com/unsubscribe?token={token}`
   - Поддержка List-Unsubscribe header

3. **Frontend:**
   - Страница отписки с обработкой токена из URL
   - Автоматическая отписка при переходе по ссылке

**Референс:** docs/stories/epic-11/11.3-backend-api-design.md:1844-1873

---

## История решенных проблем

### DEP-001: Django 6.0 CheckConstraint Deprecation Warning

**Статус:** ✅ RESOLVED (2025-11-18)
**Приоритет:** LOW
**Story:** 11.3
**Файл:** `backend/apps/common/models.py:528`

**Описание:**
CheckConstraint использовал deprecated параметр `check` вместо `condition`.

**Решение:**
```python
# ❌ Before (deprecated):
models.CheckConstraint(
    check=models.Q(...),
    name="newsletter_active_consistency",
)

# ✅ After (Django 6.0 compatible):
models.CheckConstraint(
    condition=models.Q(...),
    name="newsletter_active_consistency",
)
```

**Resolved by:** Quinn (QA Agent)

---

## Метрики технического долга

| Категория | Активных | Решенных | Запланировано |
|-----------|----------|----------|---------------|
| Security  | 0        | 1        | 0             |
| Performance | 0      | 0        | 0             |
| Deprecation | 0      | 1        | 0             |
| Feature Enhancement | 0 | 0     | 1             |

**Последнее обновление:** 2025-11-18
