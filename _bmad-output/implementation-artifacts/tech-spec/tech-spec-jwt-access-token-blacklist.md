---
title: 'JWT Access Token Blacklist (Redis)'
slug: 'jwt-access-token-blacklist'
created: '2026-01-18'
status: 'done'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Django 5.2.7
  - Django REST Framework 3.14
  - SimpleJWT (rest_framework_simplejwt)
  - Redis 7.0 (django_redis)
  - pytest 7.4.3 + pytest-django 4.7.0
files_to_modify:
  - backend/apps/users/authentication.py (NEW)
  - backend/apps/users/views/authentication.py (lines 517-609)
  - backend/freesport/settings/base.py (lines 152-160)
  - backend/tests/integration/test_auth_logout_api.py (lines 596-624)
code_patterns:
  - Redis cache via django_redis (CACHES in base.py)
  - SimpleJWT token_blacklist for refresh tokens (token.blacklist())
  - JWTAuthentication from rest_framework_simplejwt.authentication
  - Audit logging pattern with [AUDIT] prefix
test_patterns:
  - pytest-django integration tests
  - APIClient fixtures
  - @pytest.mark.integration marker
  - create_test_user factory fixture
---

# Tech-Spec: JWT Access Token Blacklist (Redis)

**Created:** 2026-01-18

## Overview

### Problem Statement

При logout пользователя в системе FREESPORT инвалидируется только **refresh-токен** через механизм `simplejwt.token_blacklist` (база данных). **Access-токен** остаётся валидным до истечения TTL (60 минут).

Это создаёт окно уязвимости:

- Украденный access-токен может использоваться до 60 минут после logout
- При смене пароля старые access-токены продолжают работать
- Нет возможности немедленно "выбросить" пользователя из системы

**Текущее поведение задокументировано в тесте:**
`test_logout_does_not_affect_access_token_immediately` (строка 596-624 в `test_auth_logout_api.py`)

### Solution

Реализовать **Redis-based blacklist для access-токенов** с:

1. **Кастомный `JWTAuthentication`** — проверяет JTI токена в Redis blacklist
2. **Обновлённый `LogoutView`** — добавляет access token JTI в Redis при logout
3. **Минимальный TTL в Redis** = TTL access-токена (60 мин) — автоочистка

### Scope

**In Scope:**

- Redis blacklist для access-токенов при logout
- Кастомный JWTAuthentication класс
- Обновление LogoutView для blacklist access token
- Интеграционные тесты

**Out of Scope:**

- Отзыв токенов при смене пароля (отдельный tech-spec)
- Endpoint "Выйти со всех устройств" (пункт 5 в tech-debt.md)
- Уменьшение TTL access-токена (рассмотреть позже)
- Frontend изменения (не требуются)

## Context for Development

### Codebase Patterns

1. **Redis Cache** уже настроен в `base.py`:

   ```python
   CACHES = {
       "default": {
           "BACKEND": "django_redis.cache.RedisCache",
           "LOCATION": config("REDIS_URL", default="redis://:redis123@redis:6379/0"),
       }
   }
   ```

2. **SimpleJWT Blacklist** для refresh-токенов:
   - Использует DB таблицы `token_blacklist_outstandingtoken`, `token_blacklist_blacklistedtoken`
   - Настроен `BLACKLIST_AFTER_ROTATION: True`

3. **LogoutView** (`authentication.py:506-609`):
   - Уже вызывает `token.blacklist()` для refresh-токена
   - Логирует через audit trail

4. **JWTAuthentication** — стандартный из `rest_framework_simplejwt`

### Files to Reference

| File                                                | Purpose                           |
| --------------------------------------------------- | --------------------------------- |
| `backend/freesport/settings/base.py`                | SIMPLE_JWT config, CACHES (Redis) |
| `backend/apps/users/views/authentication.py`        | LogoutView (строки 506-609)       |
| `backend/tests/integration/test_auth_logout_api.py` | Существующие тесты logout         |
| `backend/tests/integration/test_token_blacklist.py` | Тесты DB blacklist механизма      |

### Technical Decisions

1. **Redis vs DB для access blacklist:**
   - ✅ Redis: O(1) lookup, auto-expiry, не нагружает DB
   - ❌ DB: Нужна периодическая очистка, медленнее

2. **Ключ в Redis:**
   - Формат: `access_blacklist:{jti}`
   - TTL = ACCESS_TOKEN_LIFETIME (60 мин)

3. **Fallback при недоступности Redis (Circuit Breaker):**
   - При Redis failure: логировать warning
   - **Ограничение:** bypass разрешён max **2 минуты** (усилено после Red Team анализа)
   - После 2 мин недоступности: reject все токены или require re-auth
   - Rate limiting при failure: снизить RPS на protected endpoints
   - Метрика: `access_blacklist_redis_unavailable` gauge
   - Алерт: CRITICAL при `redis_unavailable > 30s`

### Risk Analysis (Pre-mortem)

| #      | Риск                                            | Митигация                                                        | Статус        |
| ------ | ----------------------------------------------- | ---------------------------------------------------------------- | ------------- |
| **R1** | Redis failure → bypass blacklist                | Circuit breaker (max **2 мин** fallback)                         | ✅ В scope    |
| **R2** | Password reset не инвалидирует токены           | Отдельный tech-spec                                              | ⏳ Roadmap    |
| **R3** | Race condition при concurrent logout            | Добавить concurrency тест                                        | ✅ В scope    |
| **R4** | Нет мониторинга failed blacklist checks         | Метрики + alerting                                               | ✅ В scope    |
| **R5** | Redis memory pressure при peak load             | Мониторинг Redis memory                                          | ⏳ Ops task   |
| **R6** | Token Replay (украденный токен работает до TTL) | ⚠️ Limitation stateless JWT. Mitigation: сократить TTL           | 📝 Documented |
| **R7** | Redis restart → blacklist потерян (FMA F3.2)    | ⚠️ **Accepted risk**. Window: max 60 мин. Ops: Redis persistence | 📝 Documented |

## Implementation Plan

### Task Checklist

- [ ] **Task 1:** Создать `backend/apps/users/authentication.py` с `BlacklistCheckJWTAuthentication`
- [ ] **Task 2:** Обновить `LogoutView.post()` для blacklist access token в Redis
- [ ] **Task 3:** Заменить `JWTAuthentication` на кастомный в `base.py`
- [ ] **Task 4:** Обновить тест `test_logout_does_not_affect_access_token_immediately` → `test_access_token_rejected_after_logout`
- [ ] **Task 5:** Добавить новые тесты (concurrency, Redis failure, metrics)

### Tasks

#### Task 1: Создать кастомный JWTAuthentication

**Файл:** `backend/apps/users/authentication.py` (NEW)

```python
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
import logging

logger = logging.getLogger(__name__)

ACCESS_BLACKLIST_PREFIX = "access_blacklist:"

class BlacklistCheckJWTAuthentication(JWTAuthentication):
    """
    JWTAuthentication с проверкой Redis blacklist для access-токенов.
    """

    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)

        jti = validated_token.get("jti")
        if jti and self._is_token_blacklisted(jti):
            # Security: Generic message to prevent information leakage
            raise InvalidToken("Token is invalid")

        return validated_token

    def _is_token_blacklisted(self, jti: str) -> bool:
        """Проверить, находится ли токен в blacklist.

        Note: We store JSON metadata in Redis for forensics,
        but only check existence here (not parsing JSON).
        This keeps the hot path simple and fast.
        """
        try:
            # Existence check only - JSON metadata is for forensics, not validation
            return cache.get(f"{ACCESS_BLACKLIST_PREFIX}{jti}") is not None
        except Exception as e:
            # Redis недоступен — пропускаем проверку (graceful degradation)
            logger.warning(f"Redis blacklist check failed: {e}")
            return False
```

#### Task 2: Обновить LogoutView

**Файл:** `backend/apps/users/views/authentication.py`

Добавить импорт и blacklist access-токена:

```python
# Новый импорт
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import json

ACCESS_BLACKLIST_PREFIX = "access_blacklist:"

# В методе post() после token.blacklist():
def post(self, request, *args, **kwargs):
    # ... существующий код ...

    # После token.blacklist():

    # Blacklist access token в Redis с metadata для forensics
    access_token = request.auth  # Текущий access token из заголовка
    if access_token:
        jti = access_token.get("jti")
        if jti:
            ttl = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME").total_seconds()
            # Security Audit: Store metadata for forensics
            blacklist_data = {
                "blacklisted": True,
                "ip": get_client_ip(request),
                "timestamp": timezone.now().isoformat(),
                "user_id": request.user.id,
            }
            try:
                cache.set(
                    f"{ACCESS_BLACKLIST_PREFIX}{jti}",
                    json.dumps(blacklist_data),
                    timeout=int(ttl)
                )
            except Exception as e:
                logger.warning(f"Failed to blacklist access token: {e}")
    else:
        # FMA F1.3: Edge case - session auth instead of JWT
        logger.warning(
            f"[AUDIT] Logout without access token | "
            f"user_id={request.user.id} | "
            f"auth_type=session | "
            f"ip={get_client_ip(request)}"
        )
```

#### Task 3: Подключить кастомный Authentication

**Файл:** `backend/freesport/settings/base.py`

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.BlacklistCheckJWTAuthentication",  # Заменить
        "rest_framework.authentication.SessionAuthentication",
    ],
    # ...
}
```

#### Task 4: Обновить тесты

**Файл:** `backend/tests/integration/test_auth_logout_api.py`

Изменить тест `test_logout_does_not_affect_access_token_immediately`:

```python
def test_access_token_rejected_after_logout(
    self,
    logout_api_client,
    authenticated_user_with_tokens,
    get_logout_url,
):
    """Access токен отклоняется после logout.

    После logout access токен добавляется в Redis blacklist
    и не может использоваться для авторизации.
    """
    # Arrange
    tokens = authenticated_user_with_tokens
    logout_api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    # Act - logout
    response = logout_api_client.post(
        get_logout_url,
        data={"refresh": tokens["refresh"]},
        format="json",
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Assert - access токен больше не работает
    profile_response = logout_api_client.get(reverse("users:profile"))
    assert profile_response.status_code == status.HTTP_401_UNAUTHORIZED
```

### Acceptance Criteria

**AC1:** При logout access-токен добавляется в Redis blacklist

```gherkin
Given пользователь залогинен с access и refresh токенами
When пользователь делает POST /api/v1/auth/logout/ с валидным refresh
Then access token JTI записывается в Redis с ключом "access_blacklist:{jti}"
And TTL записи = ACCESS_TOKEN_LIFETIME (60 минут)
```

**AC2:** Blacklisted access-токен отклоняется

```gherkin
Given access-токен был добавлен в Redis blacklist
When запрос с этим токеном поступает на защищённый endpoint
Then возвращается 401 Unauthorized
And в ответе "Token is blacklisted"
```

**AC3:** Graceful degradation при недоступности Redis

```gherkin
Given Redis недоступен
When запрос с access-токеном поступает на защищённый endpoint
Then авторизация проходит по стандартной логике JWT
And в логах warning о недоступности Redis blacklist
```

## Additional Context

### Dependencies

- `django-redis` — уже установлен и настроен
- `rest_framework_simplejwt` — уже используется
- Redis — уже работает в Docker Compose

### Testing Strategy

**Существующие тесты (обновить):**

- `test_auth_logout_api.py::test_logout_does_not_affect_access_token_immediately` → переименовать и изменить ожидание

**Новые тесты:**

```
# Core functionality
test_access_token_rejected_after_logout
test_access_token_blacklist_expires_after_ttl

# Graceful degradation (Pre-mortem R1)
test_blacklist_check_graceful_degradation_on_redis_error

# Concurrency (Pre-mortem R3)
test_concurrent_logout_same_user_no_race_condition

# Metrics (Pre-mortem R4)
test_blacklist_failure_logged_with_warning
```

**Команда запуска:**

```bash
docker compose exec backend pytest tests/integration/test_auth_logout_api.py -v
```

### Notes

> [!IMPORTANT]
> Существующий тест `test_logout_does_not_affect_access_token_immediately` документирует **текущее поведение** как "expected". После реализации этот тест должен быть **изменён** — access токен ДОЛЖЕН отклоняться после logout.

> [!TIP]
> Рассмотреть уменьшение ACCESS_TOKEN_LIFETIME до 15-30 мин как дополнительную меру безопасности (отдельный task).

> [!WARNING]
> **Password Reset:** Текущий scope НЕ включает инвалидацию токенов при смене пароля. Это отдельный tech-spec (см. Risk R2).

> [!NOTE]
> **Security Audit Recommendations (Roadmap):**
>
> - **IR Plan:** Документировать процедуру реагирования на массовый компромат токенов
> - **Logout-All:** Endpoint `/auth/logout-all/` для инвалидации всех токенов пользователя (см. tech-debt.md #5)

> [!CAUTION]
> **Production Check (Rubber Duck G3):**
> Убедиться, что Redis в production использует **синхронные writes** (не async). При async acknowledgment возможен race condition: logout возвращает 204, но blacklist ещё не записан. `django_redis` по умолчанию синхронный, но проверить конфиг!
