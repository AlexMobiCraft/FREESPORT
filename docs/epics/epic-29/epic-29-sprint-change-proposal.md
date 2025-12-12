# Sprint Change Proposal: Epic 29 Enhancement

**Дата:** 2025-12-12  
**Epic:** 29 - Role-Based Registration & User Verification  
**Автор:** Sarah (Product Owner)  
**Статус:** Готов к ревью

---

## 1. Executive Summary

Данный Sprint Change Proposal документирует применённые изменения к Epic 29 на основе результатов PO Master Checklist валидации и Risk Analysis.

**Результат:** Epic 29 синхронизирован с `epic-29-risk-analysis.md`, все Should-Do items интегрированы в соответствующие истории.

---

## 2. Identified Issue Summary

Валидация Epic 29 через PO Master Checklist выявила пробелы в детализации:

| Категория | Проблема | Severity |
|-----------|----------|----------|
| Story 29.2 | Отсутствует API Spec update requirement | MEDIUM |
| Story 29.3 | Не документированы SMTP rate limits | MEDIUM |
| Story 29.4 | Monitoring section без примеров реализации | MEDIUM |

Все 5 критических рисков из `epic-29-risk-analysis.md` уже были RESOLVED ранее:
- ✅ RISK-001: Database Schema Conflict
- ✅ RISK-002: Story Dependency Order  
- ✅ RISK-003: SMTP Account Creation
- ✅ RISK-004: Regression Testing
- ✅ RISK-005: Monitoring

---

## 3. Epic Impact Summary

**Текущее состояние Epic 29:**
- 4 истории сохранены без изменения scope
- Последовательность историй корректна: 29.1 → 29.2 → 29.3 → 29.4
- Blocking dependency 29.3 → 29.4 явно обозначена
- Estimated duration: 9 дней (включая regression testing)

**Изменения в структуре эпика:** НЕТ (только детализация существующих историй)

---

## 4. Applied Changes

### Story 29.2: Backend Verification Logic

**Добавлено: API Spec Update Requirement**

```yaml
# POST /api/auth/register/
requestBody:
  properties:
    role:
      type: string
      enum: [retail, trainer, wholesale_level1, federation_rep]
      default: retail
```

### Story 29.3: Email Server Configuration

**Добавлено: SMTP Rate Limits Table**

| Provider | Лимит | Рекомендация |
|----------|-------|--------------|
| Gmail | 500 emails/день | Только для development |
| Yandex Mail | 100-500/день | Уточнить с провайдером |
| SendGrid Free | 100/день | Альтернатива для production |
| SendGrid Paid | 40,000+/месяц | Рекомендуется для scale |

**Добавлено: Rate Limiting Example**

```python
@shared_task(rate_limit='10/m')  # max 10 emails/minute
def send_verification_email(user_id):
    ...
```

### Story 29.4: Email Notification System

**Добавлено: Monitoring Implementation Examples**

- Celery task с proper logging (success/failure)
- Celery Beat scheduled task для pending queue monitoring
- Alert при > 10 pending verifications за 24ч

---

## 5. Artifact Adjustment Summary

| Артефакт | Изменение | Статус |
|----------|-----------|--------|
| `epic-29-role-registration.md` | Синхронизация с risk-analysis | ✅ Выполнено |
| `docs/api-spec.yaml` | Добавить `role` parameter | ⏳ Developer task |
| `tests/regression/test_epic_28_intact.py` | Создать regression suite | ⏳ Developer task |

---

## 6. Recommended Path Forward

**Выбранный путь:** Direct Adjustment / Integration

**Обоснование:**
- Изменения носят характер детализации, не меняют scope
- Все критические риски уже resolved
- Epic готов к разработке после применения изменений

**Действия:**
1. ✅ Обновить `epic-29-role-registration.md` (выполнено)
2. ⏳ Разработчик Story 29.2: обновить `docs/api-spec.yaml`
3. ⏳ Разработчик Story 29.2: создать `tests/regression/test_epic_28_intact.py`
4. ⏳ Разработчик Story 29.4: реализовать monitoring по примерам

---

## 7. PRD MVP Impact

**Влияние на MVP:** ОТСУТСТВУЕТ

- Scope эпика не изменён
- Timeline: +0 дней (улучшения компенсируются ясностью)
- Buffer: +1 день для regression testing (уже учтён)

---

## 8. Next Steps

| # | Действие | Ответственный | Статус |
|---|----------|---------------|--------|
| 1 | Ревью Sprint Change Proposal | User | ⏳ Ожидание |
| 2 | Начать Story 29.1 и 29.3 параллельно | Developer | 🔜 После approval |
| 3 | Создать regression test suite | Developer (29.2) | 🔜 После 29.1/29.3 |
| 4 | Реализовать monitoring | Developer (29.4) | 🔜 Последняя история |

---

## 9. Validation Criteria

**Успех Sprint Change применения:**

- [x] Epic 29 синхронизирован с risk-analysis findings
- [x] Should-Do items интегрированы в stories
- [x] Change Log обновлён (v1.1)
- [ ] User approval получен

---

**Document Version:** 1.0  
**Created:** 2025-12-12  
**Status:** Pending User Approval
