# Epic 30: Backend Logout Endpoint Implementation

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-12-13 | 1.0 | Initial Epic Draft for Backend Logout | John (PM) |

---

## Goals

- Реализовать серверный endpoint `/auth/logout/` для инвалидации refresh токенов
- Обеспечить безопасный выход пользователей через blacklist механизм
- Предотвратить использование blacklisted токенов для получения новых access токенов
- Обновить API документацию с новым endpoint

## Background Context

Epic 28 реализовал JWT аутентификацию, но не включал функциональность logout на backend. При выходе на frontend токены удаляются локально, но остаются валидными на сервере до истечения срока действия (30 дней для refresh token). Это создает потенциальный security gap.

### Documents & Artifacts

- **Previous Epic:** `docs/epics/epic-28/epic-28-authentication.md` (Epic 28)
- **API Spec:** `docs/api-spec.yaml` (требует обновления)
- **JWT Library Docs:** https://django-rest-framework-simplejwt.readthedocs.io/
- **Testing Standards:** `docs/architecture/10-testing-strategy.md`

### Tech Stack

- **Backend:** Django 4.2 LTS + Django REST Framework 3.14+
- **JWT:** djangorestframework-simplejwt 5.3.1
- **Database:** PostgreSQL 15+
- **Testing:** pytest 7.4.3 + pytest-django 4.7.0 + Factory Boy 3.3.0

---

## Requirements

### Functional Requirements

- **FR1:** Backend endpoint `POST /auth/logout/` принимает refresh token и инвалидирует его
- **FR2:** Blacklisted refresh токен не может использоваться для получения нового access токена
- **FR3:** Endpoint требует аутентификации (только авторизованные пользователи могут logout)
- **FR4:** Обработка edge cases: invalid token, expired token, already blacklisted token

### Non-Functional Requirements

- **NFR1:** Blacklist таблицы должны иметь индексы для производительности
- **NFR2:** Механизм автоматической очистки expired tokens из blacklist
- **NFR3:** API документация обновлена с примерами запросов/ответов
- **NFR4:** Coverage тестами >= 90%

---

## Epic 30: Backend Logout Scope

### Story 30.1: Настройка JWT Token Blacklist

**As a** backend developer,
**I want** to configure JWT token blacklist mechanism,
**so that** refresh tokens can be invalidated server-side.

**Scope:**

- Добавить `'rest_framework_simplejwt.token_blacklist'` в `INSTALLED_APPS`
- Создать миграции для таблиц blacklist
- Обновить JWT настройки для включения blacklist
- Проверить работу blacklist в Django shell

**Acceptance Criteria:**

1. Приложение `token_blacklist` добавлено в settings
2. Миграции созданы и применены
3. Таблицы blacklist существуют в БД
4. JWT настройки включают `ROTATE_REFRESH_TOKENS` и `BLACKLIST_AFTER_ROTATION`
5. Blacklist работает корректно (проверено в shell)

---

### Story 30.2: Реализация Logout View и Serializer

**As a** backend developer,
**I want** to create logout API view,
**so that** frontend can invalidate refresh tokens.

**Scope:**

- Создать `LogoutSerializer` для валидации refresh token
- Создать `LogoutView(GenericAPIView)` с `IsAuthenticated` permission
- Реализовать логику blacklisting через `RefreshToken.blacklist()`
- Обработать ошибки (invalid token, expired, already blacklisted)
- Возвращать `204 No Content` при успехе

**Acceptance Criteria:**

1. `LogoutSerializer` валидирует поле `refresh`
2. `LogoutView` требует аутентификации
3. При валидном токене вызывается `.blacklist()`
4. Возвращается `204` при успехе, `400` при ошибке
5. Код соответствует стандартам (Black, Flake8, mypy)

---

### Story 30.3: Регистрация маршрута и обновление API документации

**As a** backend developer,
**I want** to register logout endpoint and update API documentation,
**so that** frontend developers can integrate logout functionality.

**Scope:**

- Добавить маршрут в `apps/users/urls.py`
- Обновить `docs/api-spec.yaml` с новым endpoint
- Добавить примеры запросов/ответов в OpenAPI
- Добавить drf-spectacular декораторы

**Acceptance Criteria:**

1. Маршрут `/auth/logout/` доступен
2. OpenAPI спецификация содержит endpoint описание
3. Swagger UI отображает endpoint корректно
4. drf-spectacular генерирует документацию
5. Endpoint доступен по адресу `/api/v1/auth/logout/`

---

### Story 30.4: Тесты для Logout функциональности

**As a** backend developer,
**I want** to write comprehensive tests for logout,
**so that** functionality is reliable and bug-free.

**Scope:**

- Unit-тесты для `LogoutSerializer`
- Integration-тесты для `LogoutView`:
  - Успешный logout
  - Ошибка без аутентификации (401)
  - Ошибка с невалидным токеном (400)
  - Ошибка с blacklisted токеном (400)
  - Проверка что blacklisted токен не работает для refresh
- Factory Boy для тестовых данных
- Pytest fixtures для setup/teardown

**Acceptance Criteria:**

1. Unit-тесты покрывают все методы serializer
2. Integration-тесты покрывают все сценарии
3. Тесты изолированы (нет побочных эффектов)
4. Coverage >= 90%
5. Все тесты проходят в Docker Compose
6. Следование pytest conventions

---

## Compatibility Requirements

- [x] Существующие auth endpoints не изменяются
- [x] Database schema изменения backward compatible
- [x] Existing JWT login/refresh flow не затрагивается
- [x] Performance impact минимален
- [x] Frontend может продолжать работать без вызова logout

---

## Risk Mitigation

**Primary Risk:** Blacklist таблицы могут расти неограниченно.

**Mitigation:**
1. Django management command для очистки expired tokens
2. Celery periodic task для автоматической очистки
3. Индексы на blacklist таблицы
4. Документация процесса очистки

**Rollback Plan:**
1. Удалить маршрут из urls.py
2. Удалить LogoutView и LogoutSerializer
3. Убрать token_blacklist из INSTALLED_APPS
4. Откатить миграции БД
5. Удалить endpoint из API документации

---

## Definition of Done

- [x] Все 4 stories завершены
- [x] Blacklist механизм настроен
- [x] Endpoint `/auth/logout/` работает
- [x] Blacklisted токены не работают для refresh
- [x] API документация обновлена
- [x] Тесты написаны и проходят (>= 90%)
- [x] Нет регрессий
- [x] Code review пройден
- [x] Миграции применены
- [x] QA завершено

---

## Technical Implementation Details

### JWT Blacklist Configuration

```python
# backend/freesport/settings/base.py
INSTALLED_APPS = [
    # ...
    'rest_framework_simplejwt.token_blacklist',
]

SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}
```

### LogoutView Implementation

```python
# apps/users/views.py
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

class LogoutView(GenericAPIView):
    """Logout пользователя через blacklisting refresh токена"""
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TokenError:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
```

### LogoutSerializer Implementation

```python
# apps/users/serializers.py
from rest_framework import serializers

class LogoutSerializer(serializers.Serializer):
    """Serializer для logout endpoint"""
    refresh = serializers.CharField(
        required=True,
        help_text="Refresh token для инвалидации"
    )
```

### API Endpoint Specification

```yaml
# docs/api-spec.yaml
/auth/logout/:
  post:
    tags: [Authentication]
    summary: Logout пользователя
    description: |
      Инвалидация refresh токена через blacklist механизм.
      После logout токен не может использоваться для получения новых access tokens.
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [refresh]
            properties:
              refresh:
                type: string
                description: Refresh token для инвалидации
                example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
    responses:
      '204':
        description: Токен успешно инвалидирован
      '400':
        description: Невалидный или уже инвалидированный токен
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Invalid or expired token"
      '401':
        description: Пользователь не аутентифицирован
        content:
          application/json:
            schema:
              type: object
              properties:
                detail:
                  type: string
                  example: "Authentication credentials were not provided."
```

### URL Configuration

```python
# apps/users/urls.py
urlpatterns = [
    # ... существующие маршруты
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
```

---

## Next Steps

### Dependencies

- **Blocking:** Epic 28 должен быть завершен (JWT аутентификация работает)
- **Related:** Epic 31 будет использовать этот endpoint для frontend logout UI

### Future Enhancements

1. **Blacklist Management:**
   - Django admin интерфейс для просмотра blacklisted токенов
   - Dashboard для мониторинга размера blacklist таблиц
   - Автоматические алерты при превышении лимитов

2. **Security Improvements:**
   - Rate limiting для logout endpoint
   - Logging всех logout операций для audit trail
   - IP-based tracking для подозрительной активности

3. **Performance Optimization:**
   - Партиционирование blacklist таблиц по дате
   - Кэширование blacklist checks в Redis
   - Batch cleanup операции для производительности

---

## Story Manager Handoff

**Используйте этот Epic для создания детальных User Stories.**

**Ключевые соображения:**

- Это enhancement существующей JWT аутентификации (Epic 28) на **Django 4.2 + DRF 3.14+ + simplejwt 5.3.1**
- **Integration points:**
  - `apps/users/views.py` - добавление `LogoutView`
  - `apps/users/serializers.py` - добавление `LogoutSerializer`
  - `apps/users/urls.py` - регистрация маршрута
  - `backend/freesport/settings/base.py` - JWT конфигурация
  - `docs/api-spec.yaml` - API документация
- **Существующие паттерны:**
  - GenericAPIView для API views
  - IsAuthenticated permission для защищенных endpoints
  - Serializers для валидации request data
  - Factory Boy для тестовых данных
  - pytest для тестирования
- **Критические compatibility requirements:**
  - Миграции должны быть backward compatible
  - Существующая JWT аутентификация не должна сломаться
  - Blacklist cleanup должен быть документирован
- **Каждая story должна включать:**
  - Полное покрытие тестами (>= 90%)
  - Проверку отсутствия регрессий
  - Type hints для всех методов (mypy compliance)
  - Документацию в коде (docstrings)

Epic должен обеспечить **безопасный серверный logout с инвалидацией refresh токенов через blacklist механизм**.
