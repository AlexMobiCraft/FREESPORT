# Logout Feature Implementation - Epic 30 & Epic 31

## Overview

Реализация полноценной функциональности выхода из системы (logout) для платформы FREESPORT. Функциональность разделена на два последовательных эпика:

- **Epic 30:** Backend logout endpoint с инвалидацией refresh токенов
- **Epic 31:** Frontend UI интеграция с кнопкой "Выйти"

---

## Epic Sequence

### 📋 Epic 30: Backend Logout Endpoint Implementation

**Цель:** Реализовать серверный endpoint для инвалидации refresh токенов.

**Статус:** Active (Pending Implementation)

**Документация:** [docs/epics/epic-30/epic-30-backend-logout.md](epic-30/epic-30-backend-logout.md)

**Stories:**

1. ✅ **Story 30.1:** Настройка JWT Token Blacklist
2. ✅ **Story 30.2:** Реализация Logout View и Serializer
3. ✅ **Story 30.3:** Регистрация маршрута и обновление API документации
4. ✅ **Story 30.4:** Тесты для Logout функциональности

**Key Deliverables:**

- Backend endpoint `POST /auth/logout/`
- JWT blacklist механизм (djangorestframework-simplejwt)
- Database migrations для blacklist таблиц
- API документация в OpenAPI спецификации
- Comprehensive tests (coverage >= 90%)

**Tech Stack:**

- Django 4.2 LTS + DRF 3.14+
- djangorestframework-simplejwt 5.3.1
- PostgreSQL 15+
- pytest + Factory Boy

---

### 🎨 Epic 31: Frontend Logout UI Integration

**Цель:** Добавить UI кнопку "Выйти" и интегрировать с backend endpoint.

**Статус:** Active (Depends on Epic 30)

**Документация:** [docs/epics/epic-31/epic-31-frontend-logout.md](epic-31/epic-31-frontend-logout.md)

**Stories:**

1. ✅ **Story 31.1:** Добавление кнопки "Выйти" в Header компонент
2. ✅ **Story 31.2:** Интеграция authService с backend logout endpoint
3. ✅ **Story 31.3:** Обработчик logout с редиректом
4. ✅ **Story 31.4:** Тесты для logout функциональности

**Key Deliverables:**

- Кнопка "Выйти" в Header (desktop + mobile)
- `authService.logout()` метод для API вызова
- Обновленный `authStore.logout()` с backend интеграцией
- Редирект на главную страницу после logout
- Comprehensive tests (coverage >= 90%)

**Tech Stack:**

- Next.js 15.4.6 + React 19.1.0
- Zustand 4.5.7 + Axios 1.11.0
- Vitest + RTL + MSW
- TypeScript 5.0+

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Epic 31)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Header Component                                           │
│  ┌──────────────┐                                          │
│  │ Кнопка       │  onClick                                 │
│  │ "Выйти"      │ ────────► handleLogout()                │
│  └──────────────┘                                          │
│                              │                              │
│                              ▼                              │
│                    authStore.logout()                       │
│                              │                              │
│                              ▼                              │
│                    authService.logout(refreshToken)         │
│                              │                              │
│                              │ POST /auth/logout/           │
│                              ▼                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               │ HTTP Request
                               │ { "refresh": "token" }
                               │
┌──────────────────────────────┼──────────────────────────────┐
│                     Backend (Epic 30)                       │
├──────────────────────────────┼──────────────────────────────┤
│                              ▼                              │
│                        LogoutView                           │
│                              │                              │
│                              ▼                              │
│                    LogoutSerializer                         │
│                    (validate refresh token)                 │
│                              │                              │
│                              ▼                              │
│                RefreshToken(token).blacklist()              │
│                              │                              │
│                              ▼                              │
│              ┌───────────────────────────┐                  │
│              │  PostgreSQL Blacklist DB  │                  │
│              │  - OutstandingToken       │                  │
│              │  - BlacklistedToken       │                  │
│              └───────────────────────────┘                  │
│                              │                              │
│                              ▼                              │
│                      204 No Content                         │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               │ HTTP Response
                               │
┌──────────────────────────────┼──────────────────────────────┐
│                     Frontend (Epic 31)                      │
├──────────────────────────────┼──────────────────────────────┤
│                              ▼                              │
│                    Cleanup State                            │
│                    - localStorage.removeItem('refreshToken')│
│                    - deleteCookie('refreshToken')           │
│                    - authStore.set({ isAuthenticated: false})│
│                              │                              │
│                              ▼                              │
│                    router.push('/')                         │
│                    (Redirect to Home)                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Backend (Epic 30)

1. **JWT Blacklist Mechanism:**
   - Использование встроенного `rest_framework_simplejwt.token_blacklist`
   - Blacklisted токены сохраняются в PostgreSQL
   - Автоматическая проверка blacklist при refresh операциях

2. **Authentication Required:**
   - Endpoint `/auth/logout/` требует аутентификации (`IsAuthenticated` permission)
   - Защита от abuse и spam logout requests

3. **Token Validation:**
   - Валидация формата и signature refresh токена
   - Проверка expiration time
   - Обработка уже blacklisted токенов

4. **Database Security:**
   - Индексы на blacklist таблицы для производительности
   - Периодическая очистка expired tokens (Celery task)

### Frontend (Epic 31)

1. **Fail-Safe Approach:**
   - Локальная очистка происходит ВСЕГДА, даже при ошибке API
   - Пользователь не может "застрять" в авторизованном состоянии

2. **Token Management:**
   - Refresh token берется из localStorage перед очисткой
   - Полная очистка: localStorage + cookies + Zustand state
   - Синхронизация между вкладками через storage events (опционально)

3. **Error Handling:**
   - Graceful degradation при network errors
   - Logging ошибок для monitoring
   - User-friendly error messages (опционально)

4. **XSS Protection:**
   - Access token ТОЛЬКО в memory (Zustand store)
   - Refresh token в localStorage + non-HttpOnly cookie (для middleware)
   - Все токены очищаются при logout

---

## Testing Strategy

### Backend Tests (Epic 30)

**Unit Tests:**

- `LogoutSerializer` валидация
- Token blacklisting logic
- Error handling (invalid token, expired, already blacklisted)

**Integration Tests:**

- Успешный logout с валидным refresh токеном
- Ошибка 401 без аутентификации
- Ошибка 400 с невалидным токеном
- Blacklisted токен не работает для refresh
- Database transactions и rollback

**Coverage Target:** >= 90%

### Frontend Tests (Epic 31)

**Unit Tests:**

- Header компонент с/без авторизации
- Кнопка "Выйти" отображается корректно
- `handleLogout` вызывает правильные методы

**Integration Tests:**

- `authStore.logout()` вызывает backend API (MSW mock)
- Успешная очистка state + localStorage + cookies
- Fail-safe: очистка при ошибке API
- Редирект на главную страницу

**E2E Tests (опционально):**

- Full logout flow: клик → API → очистка → редирект
- Проверка что logout работает на всех вкладках

**Coverage Target:** >= 90%

---

## Dependencies

### Epic 30 Dependencies

**Blocking:**

- ✅ Epic 28 завершен (JWT аутентификация работает)
- ✅ PostgreSQL 15+ настроен
- ✅ djangorestframework-simplejwt установлен

**Required:**

- Django 4.2 LTS
- DRF 3.14+
- pytest + pytest-django

### Epic 31 Dependencies

**Blocking:**

- ⏳ Epic 30 завершен (backend `/auth/logout/` endpoint доступен)
- ✅ Epic 28 завершен (authStore существует)
- ✅ Header компонент реализован

**Required:**

- Next.js 15.4.6
- React 19.1.0
- Zustand 4.5.7
- Axios 1.11.0
- Vitest + RTL + MSW

---

## Implementation Timeline

### Phase 1: Backend Implementation (Epic 30)

**Estimated Duration:** 3-5 дней

**Story Sequence:**

1. Day 1: Story 30.1 - Setup JWT blacklist
2. Day 2: Story 30.2 - Implement LogoutView
3. Day 3: Story 30.3 - Register endpoint + API docs
4. Day 4-5: Story 30.4 - Tests + QA

### Phase 2: Frontend Implementation (Epic 31)

**Estimated Duration:** 3-4 дня

**Story Sequence:**

1. Day 1: Story 31.1 - Add logout button UI
2. Day 2: Story 31.2 - Integrate authService
3. Day 3: Story 31.3 - Implement logout handler
4. Day 4: Story 31.4 - Tests + QA

**Total Estimated Duration:** 6-9 дней

---

## Risk Assessment

### High Risk Items

1. **Blacklist Table Growth:**
   - **Risk:** Blacklist таблицы растут неограниченно
   - **Mitigation:** Celery task для периодической очистки expired tokens
   - **Impact:** High (performance degradation)

2. **Backend Endpoint Unavailable:**
   - **Risk:** Frontend logout не может инвалидировать токен на сервере
   - **Mitigation:** Fail-safe подход с локальной очисткой
   - **Impact:** Medium (security gap до expiration)

### Medium Risk Items

3. **Migration Issues:**
   - **Risk:** Blacklist миграции могут конфликтовать с production data
   - **Mitigation:** Тестирование на staging перед production
   - **Impact:** Medium (downtime)

4. **Token Rotation Conflicts:**
   - **Risk:** Refresh token rotation может конфликтовать с blacklist
   - **Mitigation:** Корректная настройка `BLACKLIST_AFTER_ROTATION`
   - **Impact:** Low (user inconvenience)

### Low Risk Items

5. **UI/UX Issues:**
   - **Risk:** Кнопка "Выйти" может быть незаметна
   - **Mitigation:** UX review и user testing
   - **Impact:** Low (user confusion)

---

## Success Metrics

### Backend Metrics (Epic 30)

- ✅ Endpoint `/auth/logout/` доступен и работает
- ✅ Blacklisted токены не могут использоваться для refresh
- ✅ API response time < 100ms для logout операций
- ✅ Test coverage >= 90%
- ✅ Zero downtime deployment

### Frontend Metrics (Epic 31)

- ✅ Кнопка "Выйти" видна всем авторизованным пользователям
- ✅ Logout успешно работает в 99%+ случаев (с/без backend)
- ✅ Редирект происходит < 1 секунды после клика
- ✅ Test coverage >= 90%
- ✅ Zero regressions в Epic 28 функциональности

### Business Metrics

- 📈 User satisfaction с logout функциональностью
- 📊 Frequency of logout operations (analytics)
- 🔒 Security incidents related to token invalidation
- ⚡ Average logout time (UX metric)

---

## Future Enhancements

### Phase 3: Advanced Logout Features (Future Epic)

1. **Multi-Device Logout:**
   - Logout из всех устройств одновременно
   - Управление активными сессиями в профиле
   - Показывать список устройств и timestamps

2. **Auto-Logout:**
   - Автоматический logout при истечении refresh token
   - Предупреждение за N минут до auto-logout
   - "Remember me" функциональность с extended tokens

3. **Enhanced UX:**
   - Confirmation dialog перед logout
   - "Are you sure?" для предотвращения случайного logout
   - Toast notifications при logout
   - Loading states во время API вызова

4. **Analytics & Monitoring:**
   - Track logout events в analytics (Google Analytics, Amplitude)
   - Monitoring частоты logout для UX insights
   - A/B testing различных logout flows
   - Dashboard для admin: logout statistics

5. **Security Enhancements:**
   - Forced logout для suspended users
   - IP-based anomaly detection
   - Logout при смене пароля
   - Session timeout settings per user role

---

## Documentation Updates

### Required Documentation Changes

**Epic 30:**

- ✅ `docs/api-spec.yaml` - добавить `/auth/logout/` endpoint
- ✅ `docs/epics/epic-30/epic-30-backend-logout.md` - epic documentation
- 📝 `backend/apps/users/README.md` - обновить с logout endpoint
- 📝 `docs/architecture/authentication.md` - добавить blacklist механизм

**Epic 31:**

- ✅ `docs/epics/epic-31/epic-31-frontend-logout.md` - epic documentation
- 📝 `frontend/README.md` - обновить с logout функциональностью
- 📝 `docs/architecture/frontend-architecture.md` - authStore.logout() flow

**General:**

- 📝 `docs/user-guide/authentication.md` - user-facing logout documentation
- 📝 `CHANGELOG.md` - версионирование и release notes

---

## Conclusion

Epic 30 и Epic 31 вместе обеспечивают полноценную и безопасную функциональность logout для платформы FREESPORT. Реализация следует best practices:

- ✅ **Security-First:** Серверная инвалидация токенов через blacklist
- ✅ **User-Friendly:** Простая и интуитивная UI кнопка "Выйти"
- ✅ **Fail-Safe:** Локальная очистка работает даже при ошибках
- ✅ **Well-Tested:** Comprehensive test coverage (>= 90%)
- ✅ **Well-Documented:** Полная документация для developers и users

**Готовность к реализации:**

- Epic 30 готов к разработке ✅
- Epic 31 зависит от завершения Epic 30 ⏳

**Следующий шаг:** Передать Epic 30 в Backend команду для реализации.
