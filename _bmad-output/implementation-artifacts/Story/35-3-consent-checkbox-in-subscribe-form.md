# Story 35.3: Чек-бокс согласия с ПДн в форме подписки на рассылку

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных
**Story ID:** 35.3
**Status:** ready-for-dev
**Priority:** High (часть compliance-пакета 152-ФЗ; сейчас email подписчика принимается без явного согласия — нарушение)

---

## User Story

Как анонимный пользователь сайта,
я хочу при подписке на email-рассылку явно выразить согласие на обработку персональных данных,
чтобы FREESPORT мог хранить мой email и отправлять рекламные письма согласно 152-ФЗ.

Как комплаенс-офицер,
я хочу, чтобы каждое согласие на подписку фиксировалось в `UserConsent` (`pdp_contract` + `marketing_email`) с IP / User-Agent / версией политики,
чтобы при проверке Роскомнадзора предоставить полный аудиторский след даже для анонимных подписчиков.

---

## Контекст и решения

- Story 35.1 (`done`) реализовала модель `UserConsent` (`backend/apps/common/models.py:587-653`) с `CheckConstraint` `userconsent_user_or_session_required` (требует `user` ИЛИ `session_key`).
- Story 35.2 (`done`) реализовала аудит-helpers в `backend/apps/users/views/authentication.py:553-639` (`get_consent_ip_address`, `sanitize_consent_user_agent`, `normalize_consent_ip`, `sanitize_log_value` + константы `MAX_CONSENT_USER_AGENT_LENGTH`, `MAX_LOG_VALUE_LENGTH`, `IPV4_*`, `UNSAFE_LOG_CHAR_ESCAPES`). Эта story переносит их в `backend/apps/common/utils/consent_audit.py` (см. AC-7) — этого требует deferred-item «Pass 2 → 35.3 refactor».
- Endpoint подписки: `POST /api/v1/subscribe` (`backend/apps/common/urls.py:19` → `backend/apps/common/views.py:343-382` + `SubscribeSerializer` в `backend/apps/common/serializers.py:15-86`). Сейчас принимает только `{"email"}` — без согласия.
- Frontend имеет ДВА компонента подписки, бьющих в один endpoint:
  - `frontend/src/components/home/SubscribeForm.tsx` (Blue theme, продакшен) — `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` уже существует.
  - `frontend/src/components/home/ElectricSubscribeForm.tsx` (Electric theme, страница `/electric` — comparison demo). Тестов нет.
- 35.4 (cookie-баннер) — отдельная история, не трогать.

### Решения по UX и compliance

1. **Один обязательный чекбокс PDN** (а не два, как в формах регистрации). Подписка на newsletter ПО СУТИ является маркетинговым согласием, отдельный «marketing» чекбокс был бы избыточным и сбивающим (юзер подписывается ради рассылки).
2. **На бэкенде создаются ДВЕ записи `UserConsent`** для одного запроса подписки — `pdp_contract` (юридический base) **и** `marketing_email` (специфичный для рекламной рассылки) — обе с одинаковыми `ip/user_agent/given_at/policy_version`. Это даёт чистый аудиторский след под 152-ФЗ: явный pdp_contract + специфичное marketing_email согласие.
3. **Анонимные подписчики**: используем `request.session.session_key` (форсируем создание сессии через `request.session.save()` если ключа нет) — `UserConsent.session_key` удовлетворяет `CheckConstraint`. Если пользователь авторизован — заполняем `user` FK (и тогда `session_key=""`).
4. **Реактивация подписки**: при повторной подписке email-а, который ранее `unsubscribe`-нулся, **всегда** создаём новые записи `UserConsent` (audit log — append-only, никогда не апдейтим существующие).

---

## Acceptance Criteria

### AC-1: Frontend — обязательный чек-бокс PDN в `SubscribeForm` (Blue)

**Given** компонент `frontend/src/components/home/SubscribeForm.tsx`,
**When** форма отрендерена,
**Then** ПЕРЕД кнопкой «Подписаться» добавлен чек-бокс с текстом
> «Я даю согласие на [обработку моих персональных данных](`/privacy-policy`) в соответствии с Политикой».

Ссылка `/privacy-policy` открывается в новой вкладке (`target="_blank" rel="noopener noreferrer"`). Использовать паттерн вынесенной ссылки + `aria-labelledby` из 35.2 (см. `RegisterForm.tsx:284-336`) — НЕ ставить `<Link>` внутрь `<label>`.

**Given** чек-бокс не отмечен,
**When** пользователь нажимает «Подписаться»,
**Then** показывается ошибка `«Необходимо согласие на обработку персональных данных»` под чек-боксом, submit блокируется (RHF validation).

**Given** чек-бокс отмечен,
**When** подписка успешна,
**Then** в payload `POST /subscribe` отправляется `pdp_consent: true`. Форма ресетит email **и** чек-бокс через `reset()`.

**A11y:** PDN checkbox получает `aria-invalid={!!errors.pdp_consent}`, `aria-describedby="subscribe-pdp-consent-error"` при ошибке, danger-border (как в 35.2 RegisterForm).

---

### AC-2: Frontend — обязательный чек-бокс PDN в `ElectricSubscribeForm`

**Given** компонент `frontend/src/components/home/ElectricSubscribeForm.tsx`,
**When** форма отрендерена,
**Then** добавлен такой же PDN-чекбокс с теми же правилами валидации, текстом и ссылкой, как в AC-1, но стилизован в духе Electric Orange (uppercase, skew-x-12, `var(--color-primary)` border). Ссылка `<Link href="/privacy-policy">` оранжевая (`text-[var(--color-primary)]`), та же логика `target="_blank"`/`rel`/`aria-labelledby`.

**Без отметки** — submit блокируется тем же сообщением.

---

### AC-3: Frontend — расширение `SubscribeRequest` и сервис

**Given** `frontend/src/types/api.ts:209-211` (interface `SubscribeRequest` УЖЕ существует с одним полем `email`),
**When** интерфейс расширяется,
**Then** в этот же файл (`api.ts`, **не** `api.generated.ts`) добавляется обязательное поле:

```ts
// frontend/src/types/api.ts:209-211 — расширить существующий interface
export interface SubscribeRequest {
  email: string;
  pdp_consent: boolean;   // NEW — обязательное
}
```

**Не создавать** новый interface с тем же именем — это даст TS ошибку `Duplicate identifier 'SubscribeRequest'`.

**Given** `frontend/src/services/subscribeService.ts:13-32` (метод `subscribe(email: string)`),
**When** обновлена сигнатура,
**Then** метод принимает `(payload: SubscribeRequest)` (а не `email: string`) и POST-ит весь payload без изменения семантики ошибок (409 → `already_subscribed`, 400 → `validation_error`, иначе → `network_error`).

**Migration в callers:** обновить вызовы в `SubscribeForm.tsx` и `ElectricSubscribeForm.tsx`:

```ts
await subscribeService.subscribe({ email: data.email, pdp_consent: data.pdp_consent });
```

**`api.generated.ts` (codegen из OpenAPI):** проект использует `npm run generate:types` (`package.json:22` → `openapi-typescript ../docs/api-spec.yaml -o ./src/types/api.generated.ts`). После backend-изменений (AC-4) и `python manage.py spectacular ...` нужно прогнать regenerate. Generated-файл создаст свой набор типов из схемы DRF (например, `SubscribeRequestSchema` или `paths['/subscribe/']['post']['requestBody']`). Проверить, что **не возникает** конфликта имён с ручным `SubscribeRequest` из `api.ts` — если конфликт появится, переименовать ручной (например, в `SubscribeRequestPayload`) и обновить импорты в сервисе/формах. Если в `api.generated.ts` ничего с таким именем не появилось — оставить как есть.

---

### AC-4: Backend — `SubscribeSerializer` принимает `pdp_consent`

**Given** `backend/apps/common/serializers.py:15-86` (`SubscribeSerializer`),
**When** добавлено write-only поле и validate,
**Then** сериализатор расширен:

```python
pdp_consent = serializers.BooleanField(
    write_only=True,
    required=True,
    error_messages={
        "required": "Необходимо согласие на обработку персональных данных.",
        "invalid": "Необходимо согласие на обработку персональных данных.",
        "null": "Необходимо согласие на обработку персональных данных.",
    },
)
```

В `validate()` добавляется проверка (после существующего `validate_email`):

```python
def validate(self, attrs):
    if not attrs.get("pdp_consent"):
        raise serializers.ValidationError(
            {"pdp_consent": "Необходимо согласие на обработку персональных данных."}
        )
    return attrs
```

`pdp_consent` НЕ должен попасть в `Newsletter.objects.create(...)` — `pop` из `validated_data` в `create()` ДО передачи остальных полей в модель.

**Не нарушать** существующее поведение: 409 для duplicate (`Этот email уже подписан...`), 400 для invalid email, lowercase-нормализация — всё остаётся.

---

### AC-5: Backend — view `subscribe()` создаёт записи `UserConsent` в одной транзакции

**Given** `backend/apps/common/views.py:343-382` (`subscribe`),
**When** подписка валидна,
**Then** в одном `transaction.atomic()`:

1. Создаётся / реактивируется `Newsletter` (как сейчас — через `serializer.save()`).
2. Гарантируется `session_key` для анонимного запроса:

```python
if not request.user.is_authenticated and not request.session.session_key:
    request.session.save()  # форсируем создание session_key
```

3. Создаются ДВЕ записи `UserConsent` с одним и тем же `ip/user_agent/given_at` (timestamp у обеих практически совпадёт — auto_now_add):

```python
consent_kwargs = {
    "user": request.user if request.user.is_authenticated else None,
    "session_key": "" if request.user.is_authenticated else (request.session.session_key or ""),
    "ip_address": get_consent_ip_address(request),
    "user_agent": sanitize_consent_user_agent(request.META.get("HTTP_USER_AGENT")),
}
UserConsent.objects.create(consent_type="pdp_contract", **consent_kwargs)
UserConsent.objects.create(consent_type="marketing_email", **consent_kwargs)
```

`policy_version` берётся из default модели (`"1.0"`).

**Атомарность:** если падает `UserConsent.create` — откатывается и `Newsletter` (защита от orphan-подписки без согласия). При duplicate-conflict (409) транзакция вообще не доходит до этой ветки — `UserConsent` записи **не** создаются (consent уже был дан при первой подписке, повторное создание было бы шумом в audit log).

**Реактивация уже существующего unsubscribed email** (`SubscribeSerializer.create()` `try/except Newsletter.DoesNotExist`): записи `UserConsent` всё равно создаются заново (audit log — append-only).

**Throttling — обязательная проверка:**
- В `production.py:112` зарегистрирован `apps.common.throttling.ProxyAwareAnonRateThrottle` в `DEFAULT_THROTTLE_CLASSES` — он применяется ко всем views, у которых нет явного `@throttle_classes([])` override.
- `subscribe()` НЕ имеет `@throttle_classes([])` (в отличие от `health_check` на line 52) — значит default-throttle работает.
- **Перед merge:** написать smoke-тест (или ручной curl x100) для подтверждения, что `/api/v1/subscribe/` действительно троттлится в production-настройках. Если по какой-то причине нет — добавить явный `@throttle_classes([ProxyAwareAnonRateThrottle])` к view.
- **Risk:** `request.session.save()` создаёт row в `django_session` для каждой успешной подписки анонимного пользователя. Без throttling это DOS-vector (заполнение таблицы). С `ProxyAwareAnonRateThrottle` — bounded. Cleanup orphan-сессий — Django `clearsessions` management command (рекомендуется добавить в Celery Beat расписание; вне scope 35.3, в Dev Notes).

---

### AC-6: Backend — рефактор audit-helpers в `apps/common/utils/consent_audit.py`

**Given** хелперы из 35.2 живут в `backend/apps/users/views/authentication.py:524-639` (`get_client_ip` + 4 consent-helpers + константы lines 28-53),
**When** они используются ДВУМЯ местами (auth + subscribe),
**Then** перенести в новый модуль `backend/apps/common/utils/consent_audit.py`:

**Содержимое нового модуля** (skeleton — функции переносятся **строка-в-строку** из исходника, без изменений поведения):

```python
# backend/apps/common/utils/consent_audit.py
"""Audit-helpers для записи UserConsent (152-ФЗ).

Используется UserRegistrationView (35.2) и subscribe view (35.3).
"""
import logging
import re
from ipaddress import ip_address as parse_ip_address
from typing import Any, cast

from rest_framework.request import Request

logger = logging.getLogger("apps.common.consent_audit")

MAX_CONSENT_USER_AGENT_LENGTH = 512
MAX_LOG_VALUE_LENGTH = 128

IPV4_OCTET_RE = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_PORT_RE = r"(?:6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3})"
IPV4_WITH_PORT_RE = re.compile(rf"^(?P<ip>{IPV4_OCTET_RE}(?:\.{IPV4_OCTET_RE}){{3}}):(?P<port>{IPV4_PORT_RE})$")

UNSAFE_LOG_CHAR_ESCAPES = {
    "\x00": "\\x00", "\r": "\\r", "\n": "\\n", "\x1b": "\\x1b",
    "​": "\\u200b", "‌": "\\u200c", "‍": "\\u200d",
    "": "\\u2028", "": "\\u2029",
    "‪": "\\u202a", "‫": "\\u202b", "‬": "\\u202c",
    "‭": "\\u202d", "‮": "\\u202e",
    "⁦": "\\u2066", "⁧": "\\u2067", "⁨": "\\u2068", "⁩": "\\u2069",
    "﻿": "\\ufeff",
}


def get_client_ip(request: Request) -> str:
    """Извлечь IP клиента (X-Forwarded-For first hop или REMOTE_ADDR)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
        if ip:
            return cast(str, ip)
    return cast(str, request.META.get("REMOTE_ADDR", "unknown"))


def normalize_consent_ip(raw_ip: str) -> str | None:
    """Нормализовать IP из audit-заголовка перед записью в PostgreSQL inet."""
    # IMPLEMENTATION: скопировать тело функции normalize_consent_ip
    # из backend/apps/users/views/authentication.py lines 553-593


def sanitize_log_value(value: str) -> str:
    """Сжать и экранировать внешнее значение перед записью в structured log."""
    # IMPLEMENTATION: скопировать тело функции sanitize_log_value
    # из backend/apps/users/views/authentication.py lines 596-610


def sanitize_consent_user_agent(user_agent: Any) -> str:
    """Удалить невалидные UTF-8 surrogate-символы и ограничить длину User-Agent."""
    # IMPLEMENTATION: скопировать тело функции sanitize_consent_user_agent
    # из backend/apps/users/views/authentication.py lines 613-616


def get_consent_ip_address(request: Request) -> str | None:
    """Получить валидный IP для audit-записи согласия."""
    # IMPLEMENTATION: скопировать тело функции get_consent_ip_address
    # из backend/apps/users/views/authentication.py lines 619-639
```

**КРИТИЧНО про копирование:**
- Все 5 функций (`get_client_ip` + 4 выше) переносятся **строка-в-строку** из `authentication.py`. Никакой логики менять нельзя — это инвариант (тесты 35.2 покрывают поведение и должны остаться зелёными после рефактора).
- Stub-комментарии `# IMPLEMENTATION: ...` — placeholder. Dev должен заменить их на реальное тело функции из указанных строк исходника.
- `UNSAFE_LOG_CHAR_ESCAPES` обязательно использовать `\uXXXX` escape-форму для ключей словаря (как в исходнике `authentication.py:33-53`). Если копировать через clipboard из Markdown — invisible chars (zero-width spaces, BiDi marks) могут потеряться при mojibake. Безопаснее открыть `authentication.py` напрямую и скопировать оттуда.

**Изменения в `backend/apps/users/views/authentication.py`:**

- Удалить блоки `MAX_CONSENT_USER_AGENT_LENGTH..UNSAFE_LOG_CHAR_ESCAPES` (lines 28-53).
- Удалить функцию `get_client_ip(request)` (lines 524-550) — переносится в новый модуль.
  - **Не путать** с `_get_client_ip` (с подчёркиванием) в `apps/users/admin.py:466` — это **другой** private метод admin-классов, его НЕ трогаем.
  - Подтверждено грепом: `get_client_ip` (без подчёркивания) используется только внутри `authentication.py` (passwords reset, login, registration view) — все эти call-site после рефактора будут импортировать из `apps.common.utils.consent_audit`.
- Удалить функции `normalize_consent_ip`, `sanitize_log_value`, `sanitize_consent_user_agent`, `get_consent_ip_address` (lines 553-639).
- Удалить неиспользуемые импорты: `import re`, `from ipaddress import ip_address as parse_ip_address` (проверить грепом по файлу — после удаления функций они станут dead).
- Заменить импорты в начале файла на:

```python
from apps.common.utils.consent_audit import (
    get_client_ip,
    get_consent_ip_address,
    sanitize_consent_user_agent,
)
```

(Если в `LoginView` / `PasswordResetView` / других местах файла используются ещё какие-то из 5 helpers — добавить их в этот же импорт.)

**`backend/apps/common/utils/__init__.py`** — создать **пустым файлом** (без re-exports). Импорты в модулях-потребителях делать через полный путь:

```python
from apps.common.utils.consent_audit import (
    get_consent_ip_address,
    sanitize_consent_user_agent,
)
```

Это снижает риск ambiguous-импортов, если в будущем в `apps/common/utils/` появятся другие модули с пересекающимися именами.

**Все существующие тесты 35.2** (`backend/tests/integration/test_auth_registration_consent.py` + `test_auth_registration_tokens.py`) должны остаться зелёными — поведение helpers не меняется, только location. Если в тестах есть прямой импорт `from apps.users.views.authentication import normalize_consent_ip` (или другой helper) — переписать на `from apps.common.utils.consent_audit import normalize_consent_ip`. Если тесты вызывают функции только через HTTP (черный ящик через `client.post(...)`) — не трогать.

**Order of operations** (безопасный рефактор без красного CI):

1. Создать `apps/common/utils/__init__.py` (пустой) и `apps/common/utils/consent_audit.py` с **полными** копиями всех 5 функций + констант.
2. В `authentication.py` ДОБАВИТЬ импорт из нового модуля (не удаляя локальные определения). Локальные shadowing-имена временно сосуществуют с импортами — Python не падает (импорт первый, потом локальные перезаписывают). Главное: убедиться, что `serializers.py` или другие места НЕ импортируют локальные имена из `authentication.py` напрямую.
3. Прогнать `make test-integration` + `make test-unit` через Docker — оба должны быть зелёные.
4. ТОЛЬКО ПОСЛЕ зелёного шага 3 — удалить локальные определения констант/функций в `authentication.py` + неиспользуемые импорты.
5. Прогнать тесты ещё раз — всё ещё зелёные.
6. Тогда же добавить использование helpers в `apps/common/views.py::subscribe()` (AC-5/AC-7) — это новая call-site.

---

### AC-7: Backend — обновление `SubscribeSerializer.create()` и `subscribe` view

**Given** AC-4 расширил serializer полем `pdp_consent`,
**When** реализуется AC-5,
**Then**:

1. `SubscribeSerializer.create()` (`backend/apps/common/serializers.py:41-86`): извлечь `pdp_consent` через `validated_data.pop("pdp_consent", False)` ДО Newsletter операций (он не должен попасть в `Newsletter.objects.create`).
2. `subscribe()` view (`backend/apps/common/views.py:343-382`): обернуть в `transaction.atomic()`, после `subscription = serializer.save()` создать обе `UserConsent` записи (см. AC-5).
3. Импорты в `views.py`:

```python
from django.db import transaction
from apps.common.models import UserConsent
from apps.common.utils.consent_audit import (
    get_consent_ip_address,
    sanitize_consent_user_agent,
)
```

4. `extend_schema(request=SubscribeSerializer, ...)` (`backend/apps/common/views.py:295-340`) — текущий `extend_schema` имеет examples только для responses (success/validation_error/already_subscribed). Нужно:

   **(а)** добавить request example в request-параметр (если используется `request=SubscribeSerializer` без явных examples — добавить через `examples=[...]` в `extend_schema(request=...)`):

   ```python
   examples=[
       OpenApiExample(
           name="successful_subscription_request",
           value={"email": "user@example.com", "pdp_consent": True},
           request_only=True,
       ),
   ],
   ```

   Альтернатива (если drf-spectacular в проекте не поддерживает `examples` на request top-level) — добавить пример как response_only под status 201, с пометкой в `name="request_payload_shape"`.

   **(б)** добавить response-кейс 400 для `pdp_consent`:

   ```python
   OpenApiExample(
       name="pdp_consent_required",
       value={"pdp_consent": ["Необходимо согласие на обработку персональных данных."]},
       response_only=True,
   ),
   ```

5. После всех изменений запустить `python manage.py spectacular --file docs/api-spec.yaml` через Docker — проверить дельту в git diff (должна включать оба изменения).

---

### AC-8: Backend тесты

**Расширить:** `backend/tests/integration/test_common_subscribe_api.py` (существующий).

Добавить кейсы:

1. **`test_subscribe_requires_pdp_consent`** — POST `/api/v1/subscribe/` без `pdp_consent` → 400, `errors["pdp_consent"]` точное контрактное сообщение `«Необходимо согласие на обработку персональных данных.»`.
2. **`test_subscribe_rejects_pdp_consent_false`** — `pdp_consent=False` → 400, контрактное сообщение.
3. **`test_subscribe_creates_two_consent_records_for_anonymous`** — анонимный POST с `email + pdp_consent=True` → 201; ровно две записи `UserConsent` с `user=None`, `session_key != ""`, `consent_type ∈ {pdp_contract, marketing_email}`, одинаковым `ip_address`, `user_agent`, `policy_version="1.0"`.
4. **`test_subscribe_creates_two_consent_records_for_authenticated`** — POST с залогиненным user → 201; обе `UserConsent` имеют `user=<user>`, `session_key=""`.
5. **`test_subscribe_consent_records_capture_ip_and_user_agent`** — `HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1"` → `ip_address="203.0.113.5"` (или `None` для invalid IP — параметризация с private/loopback/zone-id/невалидным IP).
6. **`test_subscribe_user_agent_truncated_to_512`** — UA длиной 1000 → `len(consent.user_agent) <= 512`; surrogate chars очищаются.
7. **`test_subscribe_reactivation_creates_new_consent_records`** — email с `is_active=False` подписывается заново → 201; `Newsletter` реактивирован (как раньше) **и** созданы 2 НОВЫХ записи `UserConsent` (старые, если были, не трогаются).
8. **`test_subscribe_atomic_rollback_on_consent_failure`** — мок `UserConsent.objects.create` бросает `IntegrityError` → 500/Exception; `Newsletter` НЕ создан (rollback). Использовать `monkeypatch` или `mock.patch`.
9. **`test_subscribe_anonymous_creates_session_key`** — анонимный POST → 201; обе `UserConsent` записи имеют `session_key != ""` (assert просто на non-empty, без assertion на «reuse» между запросами — DRF `APIClient` не гарантирует cookie-persistence между call-ами, и тестировать reuse нужно либо через ручную работу с `Client` cookies, либо через unit-тест на view-функцию напрямую — **out of scope**).

**Обновить существующие 5 кейсов** в `test_common_subscribe_api.py:13-77` — добавить `"pdp_consent": True` к каждому `data = {...}`. Иначе они упадут с 400 после AC-4. Это обязательно в этой story (red CI блокирует merge).

**Маркеры:**
- В файле уже есть `pytestmark = pytest.mark.django_db` (line 10).
- Маркер `integration` зарегистрирован в `backend/pytest.ini:7` (`integration: integration tests`) — можно безопасно расширить до `pytestmark = [pytest.mark.django_db, pytest.mark.integration]`. Это включит файл в `make test-integration` и исключит из `make test-unit`.

**Для AC-8 кейса №4** (authenticated user) использовать `api_client.force_authenticate(user=user)` (стандартный DRF паттерн). Создание test-user через `User.objects.create_user(...)` с уникальным email через `get_unique_suffix()` или `Sequence`-фикстуру (см. existing factories в `backend/apps/users/tests/`).

**Дополнительно** — найти грепом любые другие тесты, которые делают POST `/subscribe/` или вызывают `SubscribeSerializer`:

```bash
grep -rn "subscribe/\|SubscribeSerializer" backend/tests/ backend/apps/
```

И добавить `pdp_consent: True` там же.

---

### AC-9: Frontend тесты

**Расширить:** `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` (существующий, 7 кейсов сейчас).

Добавить кейсы:

1. **PDN checkbox рендерится с ссылкой на `/privacy-policy`** — `screen.getByRole('link', { name: /политикой/i })` (или альтернативно по имени `/обработку моих персональных данных/i`):
   - `expect(link).toHaveAttribute('href', '/privacy-policy');`
   - `expect(link).toHaveAttribute('target', '_blank');`
   - `expect(link).toHaveAttribute('rel', 'noopener noreferrer');`
2. **Submit без отметки PDN** показывает ошибку «Необходимо согласие на обработку персональных данных»; `subscribeService.subscribe` НЕ вызывается (`expect(subscribeService.subscribe).not.toHaveBeenCalled();`).
3. **Submit с отметкой PDN** вызывает `subscribeService.subscribe` с **точным** payload `{ email: 'test@example.com', pdp_consent: true }` — assertion через `expect(subscribeService.subscribe).toHaveBeenCalledWith({ email: 'test@example.com', pdp_consent: true });`.
4. **Reset формы после успешной подписки** очищает email **и** PDN-чек-бокс (после `reset()` чекбокс снова `unchecked`).
5. **A11y:** PDN-чекбокс получает `aria-invalid="true"` при ошибке; ошибка читается через `role="alert"`; `aria-describedby` указывает на id error-элемента.

**Обновить существующие** кейсы 5–7 (success/already_subscribed/network_error/disabled-button) — теперь они **должны** отмечать PDN-чекбокс перед submit, иначе валидация заблокирует:

```ts
const pdpCheckbox = screen.getByRole('checkbox', { name: /согласие на обработку/i });
await user.click(pdpCheckbox);
```

**Создать:** `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx` (новый, минимальный набор):

1. PDN-чекбокс рендерится с ссылкой `/privacy-policy` (assertions на `href`/`target`/`rel` как в SubscribeForm кейс №1).
2. Submit без PDN → ошибка, `subscribeService.subscribe` НЕ вызван.
3. Submit с PDN → `subscribeService.subscribe` вызван с точным payload `{ email, pdp_consent: true }`.

(Electric-тестов нет в проекте, новый файл; не покрывать UX edge cases — это comparison demo.)

---

## Технические требования и ограничения

### Backend (Django)

**Изменять:**

- `backend/apps/common/serializers.py` — `SubscribeSerializer` (AC-4)
- `backend/apps/common/views.py` — `subscribe()` (AC-5, AC-7)
- `backend/apps/users/views/authentication.py` — удалить блоки helpers/констант (AC-6)
- `backend/tests/integration/test_common_subscribe_api.py` — расширить (AC-8) + обновить существующие 5 кейсов
- `backend/tests/integration/test_auth_registration_consent.py` — если импортирует helpers напрямую (AC-6 примечание)

**Создавать:**

- `backend/apps/common/utils/__init__.py` (AC-6)
- `backend/apps/common/utils/consent_audit.py` (AC-6)

**НЕ изменять:**

- `backend/apps/common/models.py:587-653` (`UserConsent`) — модель готова из 35.1.
- `backend/apps/common/models.py:516-584` (`Newsletter`) — модель готова, миграции не нужны.
- `backend/apps/common/admin.py` (`UserConsentAdmin`, `NewsletterAdmin`) — read-only / не трогать.
- `backend/apps/common/urls.py` — endpoint `subscribe/` остаётся.
- `backend/apps/common/serializers.py:96-130` (`UnsubscribeSerializer`) — отписка остаётся БЕЗ pdp_consent (отписка — действие против собственных данных, не требует нового согласия).
- `backend/apps/users/serializers.py` — registration логика 35.2 не меняется.

### Frontend (Next.js 15 / React 19)

**Изменять:**

- `frontend/src/components/home/SubscribeForm.tsx` (AC-1, AC-3 caller)
- `frontend/src/components/home/ElectricSubscribeForm.tsx` (AC-2, AC-3 caller)
- `frontend/src/services/subscribeService.ts` (AC-3)
- `frontend/src/types/api.ts` (AC-3)
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx` (AC-9)

**Создавать:**

- `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx` (AC-9)

**НЕ изменять:**

- `frontend/src/components/ui/Checkbox/Checkbox.tsx` — компонент уже есть, использовать как есть (см. 35.2 Dev Notes — `label` проп НЕ передавать, использовать внешний `<label htmlFor>` с inline `<Link>`).
- `frontend/src/components/home/SubscribeNewsSection.tsx` — wrapper layout, не трогать.
- `frontend/src/components/auth/RegisterForm.tsx`, `B2BRegisterForm.tsx` — это 35.2 scope; читать только как reference-паттерн.
- `frontend/src/services/api-client.ts` — axios instance, не трогать.

### API контракт (изменение)

```
POST /api/v1/subscribe/
Request body:
{
  "email": "user@example.com",
  "pdp_consent": true       // NEW — required, MUST be true
}

Errors:
- 400 {"pdp_consent": ["Необходимо согласие на обработку персональных данных."]}
- 400 {"email": ["Введите корректный email адрес."]}     (existing)
- 409 {"email": ["Этот email уже подписан на рассылку"]} (existing)
```

**`docs/api-spec.yaml` обновлять руками НЕ требуется** — `drf-spectacular` сгенерирует дельту автоматически. После изменений выполнить (так же, как в 35.2):

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py spectacular --file docs/api-spec.yaml
```

Если на фронте есть generated types — `npm run generate:types` (см. project-context §4).

---

## Структура файлов (изменения)

```
backend/
  apps/
    common/
      serializers.py                                   [MODIFY] — SubscribeSerializer + pdp_consent
      views.py                                         [MODIFY] — subscribe + transaction.atomic + UserConsent.create x2
      utils/                                           [CREATE]
        __init__.py                                    [CREATE] — публичные ре-экспорты
        consent_audit.py                               [CREATE] — перенос helpers из authentication.py
    users/
      views/
        authentication.py                              [MODIFY] — удалить helpers/константы, импорт из common.utils.consent_audit
  tests/
    integration/
      test_common_subscribe_api.py                     [MODIFY] — добавить кейсы AC-8, обновить 5 существующих с pdp_consent
      test_auth_registration_consent.py                [MODIFY?] — только если импортирует normalize_consent_ip напрямую

frontend/
  src/
    components/
      home/
        SubscribeForm.tsx                              [MODIFY] — PDN-чекбокс перед submit + Zod/RHF hookup
        ElectricSubscribeForm.tsx                      [MODIFY] — PDN-чекбокс в Electric стиле
        __tests__/
          SubscribeForm.test.tsx                       [MODIFY] — 5 новых кейсов AC-9 + обновить 4 существующих
          ElectricSubscribeForm.test.tsx               [CREATE] — 3 базовых кейса AC-9
    services/
      subscribeService.ts                              [MODIFY] — subscribe(payload: SubscribeRequest)
    types/
      api.ts                                           [MODIFY] — добавить interface SubscribeRequest
```

---

## GitNexus Impact (preliminary)

Запущено через `npx gitnexus context/impact`:

- `Function:backend/apps/common/views.py:subscribe` — `incoming: {}, outgoing: {}` (только HTTP-вход через urlpatterns; **risk: LOW**, прямых call-site нет в кодовой базе).
- `Function:frontend/src/components/home/SubscribeForm.tsx:SubscribeForm` — upstream = 1 (`SubscribeNewsSection`); сигнатура props не меняется → **risk: LOW**.
- `Function:backend/apps/common/serializers.py:SubscribeSerializer` (косвенно) — изменение Meta/полей backwards-incompatible для клиентов, не передающих `pdp_consent` (требуемое поведение AC-1..AC-4).
- Для `apps.users.views.authentication.normalize_consent_ip / sanitize_consent_user_agent / sanitize_log_value / get_consent_ip_address` — после AC-6 будут перенесены, **обязательно** перед удалением прогнать `npx gitnexus impact <symbol> --direction upstream` и убедиться, что нет внешних импортов кроме `UserRegistrationView` и тестов.

**ПЕРЕД РЕАЛИЗАЦИЕЙ** разработчик должен повторно прогнать `gitnexus_impact` на каждый редактируемый символ (требование `CLAUDE.md` GitNexus Discipline) и сообщить blast radius пользователю.

---

## Реализация — ключевые snippets

### Backend: `SubscribeSerializer` (фрагмент)

```python
class SubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True, max_length=255,
        help_text="Email адрес для подписки",
    )
    pdp_consent = serializers.BooleanField(
        write_only=True,
        required=True,
        error_messages={
            "required": "Необходимо согласие на обработку персональных данных.",
            "invalid": "Необходимо согласие на обработку персональных данных.",
            "null": "Необходимо согласие на обработку персональных данных.",
        },
    )

    def validate_email(self, value: str) -> str:
        # ... existing
        ...

    def validate(self, attrs):
        if not attrs.get("pdp_consent"):
            raise serializers.ValidationError(
                {"pdp_consent": "Необходимо согласие на обработку персональных данных."}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Newsletter:
        validated_data.pop("pdp_consent", False)  # ВАЖНО: убираем перед Newsletter.create
        # ... rest existing logic
```

### Backend: `subscribe()` view (фрагмент)

```python
from django.db import transaction
from apps.common.models import UserConsent
from apps.common.utils.consent_audit import (
    get_consent_ip_address,
    sanitize_consent_user_agent,
)

@api_view(["POST"])
@permission_classes([AllowAny])
def subscribe(request: Request) -> Response:
    serializer = SubscribeSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        if "email" in serializer.errors:
            error_msg = str(serializer.errors["email"][0])
            if "уже подписан" in error_msg:
                return Response(serializer.errors, status=status.HTTP_409_CONFLICT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        subscription = serializer.save()

        if not request.user.is_authenticated and not request.session.session_key:
            request.session.save()  # форсируем session_key для CheckConstraint

        consent_kwargs = {
            "user": request.user if request.user.is_authenticated else None,
            "session_key": (
                "" if request.user.is_authenticated
                else (request.session.session_key or "")
            ),
            "ip_address": get_consent_ip_address(request),
            "user_agent": sanitize_consent_user_agent(request.META.get("HTTP_USER_AGENT")),
        }
        UserConsent.objects.create(consent_type="pdp_contract", **consent_kwargs)
        UserConsent.objects.create(consent_type="marketing_email", **consent_kwargs)

    response_serializer = SubscribeResponseSerializer(
        {"message": "Вы успешно подписались на рассылку", "email": subscription.email}
    )
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)
```

### Frontend: `SubscribeForm.tsx` (фрагмент с PDN чекбоксом)

```tsx
'use client';

import React from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import { subscribeService } from '@/services/subscribeService';
import { Input } from '@/components/ui/Input/Input';
import { Button } from '@/components/ui/Button/Button';
import { Checkbox } from '@/components/ui/Checkbox/Checkbox';

interface SubscribeFormData {
  email: string;
  pdp_consent: boolean;
}

export const SubscribeForm: React.FC = () => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<SubscribeFormData>({
    defaultValues: { email: '', pdp_consent: false },
  });

  const hasPdpConsentError = !!errors.pdp_consent;

  const onSubmit = async (data: SubscribeFormData) => {
    try {
      await subscribeService.subscribe({
        email: data.email,
        pdp_consent: data.pdp_consent,
      });
      toast.success('Вы успешно подписались на рассылку');
      reset();
    } catch (error: unknown) {
      // ... existing error mapping
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* ... title, subtitle, Input email — без изменений */}

      <div className="space-y-2">
        <div className="flex items-start gap-3">
          <Checkbox
            id="subscribe-pdp-consent"
            {...register('pdp_consent', {
              required: 'Необходимо согласие на обработку персональных данных',
            })}
            disabled={isSubmitting}
            aria-invalid={hasPdpConsentError || undefined}
            aria-labelledby="subscribe-pdp-consent-label-prefix subscribe-pdp-consent-policy-link subscribe-pdp-consent-label-suffix"
            aria-describedby={hasPdpConsentError ? 'subscribe-pdp-consent-error' : undefined}
            className={
              hasPdpConsentError
                ? 'border-[var(--color-accent-danger)] bg-[var(--color-accent-danger)]/8 peer-focus:ring-[var(--color-accent-danger)]'
                : undefined
            }
          />
          <span className="text-body-s text-text-primary select-none">
            <label
              id="subscribe-pdp-consent-label-prefix"
              htmlFor="subscribe-pdp-consent"
              className="cursor-pointer"
            >
              Я даю согласие на
            </label>{' '}
            <Link
              id="subscribe-pdp-consent-policy-link"
              href="/privacy-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline hover:text-primary-hover"
            >
              обработку моих персональных данных
            </Link>{' '}
            <label
              id="subscribe-pdp-consent-label-suffix"
              htmlFor="subscribe-pdp-consent"
              className="cursor-pointer"
            >
              в соответствии с Политикой
            </label>
          </span>
        </div>
        {errors.pdp_consent?.message && (
          <p
            id="subscribe-pdp-consent-error"
            className="text-body-xs text-[var(--color-accent-danger)]"
            role="alert"
          >
            {errors.pdp_consent.message}
          </p>
        )}
      </div>

      <Button type="submit" variant="primary" disabled={isSubmitting} loading={isSubmitting} className="w-full">
        {isSubmitting ? 'Отправка...' : 'Подписаться'}
      </Button>
    </form>
  );
};
```

### Frontend: `subscribeService.ts` (полная замена сигнатуры)

```ts
import apiClient from './api-client';
import type { SubscribeRequest, SubscribeResponse } from '@/types/api';

export const subscribeService = {
  async subscribe(payload: SubscribeRequest): Promise<SubscribeResponse> {
    try {
      const { data } = await apiClient.post<SubscribeResponse>('/subscribe', payload);
      return data;
    } catch (error: unknown) {
      // ... existing error mapping (без изменений)
    }
  },
};
```

---

## Dev Notes

### Почему ДВЕ записи `UserConsent` за один POST

Подписка на newsletter — это и есть marketing-канал. Создание ОБЕИХ записей (`pdp_contract` для юридического базиса + `marketing_email` для конкретной цели обработки) делает аудиторский след максимально явным: при проверке Роскомнадзор видит и согласие на обработку ПДн, и явное согласие на маркетинговый канал — без двусмысленности «pdp_contract есть, а marketing_email нет → можно ли вообще слать письма?».

### Почему нет отдельного `marketing_consent` чекбокса

В формах регистрации (35.2) marketing был ОПЦИОНАЛЬНЫМ — пользователь регистрируется ради аккаунта, а не ради писем. В SubscribeForm — наоборот: пользователь специально подписывается на рассылку, отдельный «согласен ли я получать рекламу» чекбокс был бы дублирующим и сбивающим с толку (при `marketing=false` подписка теряет смысл). Solution: единый PDN-чекбокс в UI, две записи в БД.

### Почему `request.session.save()` для анонимного пользователя

`UserConsent.CheckConstraint` требует `user IS NOT NULL OR session_key != ''`. У анонимного API-клиента (стейтлес fetch без cookies) `request.session.session_key` = `None` до первого `save()`. Без `save()` мы получим `IntegrityError` на INSERT в `UserConsent`. `request.session.save()` создаёт пустую запись в `django_session`, выдаёт key — этого достаточно для constraint. Cookie `sessionid` улетит в response set-cookie, что норм для дальнейших запросов того же клиента. Если переживаем за лишние session-rows — Django `clearsessions` команда чистит истёкшие.

### Почему рефактор helpers в `apps.common.utils.consent_audit` обязателен

Pass 2 35.2 (line 572) явно зафиксировал: «`get_consent_ip_address` для Story 35.3 удобнее иметь в `apps/common/utils.py` — deferred, рефакторинг при старте Story 35.3». Без рефактора у нас два пути:
- (A) дублировать код в `common/views.py` — нарушение DRY и риск drift при будущих fixes (например, новый surrogate char в `UNSAFE_LOG_CHAR_ESCAPES`).
- (B) импортировать `from apps.users.views.authentication import ...` — общий слой через app-views — антипаттерн (`common` зависит от `users.views` — циклическая зависимость и нарушение слоистости).

Делаем правильно — переносим helpers + констант в общий util-модуль. Это локализованный refactor (~80 строк перенести), `git mv`-эквивалент через копирование + удаление + импорт правок.

### Атомарность

`with transaction.atomic():` оборачивает `Newsletter.create + 2 UserConsent.create`. Если `UserConsent.create` упадёт (например, redis-DB рассинхрон или сбой constraint) — `Newsletter` тоже не сохранится. Это правильное поведение для compliance: запись подписки без согласия = orphan-нарушение.

**Note про реактивацию:** при реактивации (`Newsletter.is_active = True` → save через `update_fields`) UPDATE в `Newsletter` тоже находится внутри транзакции — `UserConsent.create` failure откатит и UPDATE. Это корректно (хотя «откат» возвращает `is_active=False`, но это лучше, чем reactivation без аудита).

### Изоляция тестов

Существующие 5 кейсов в `test_common_subscribe_api.py` используют **статические** email-ы (`newuser@example.com`, `existing@example.com` etc.) — это работает, потому что `pytest.mark.django_db` + проектная фикстура `autouse` `TRUNCATE CASCADE` (см. `backend/docs/testing-standards.md` §8.5). НЕ ломаем этот паттерн — продолжаем использовать статические email-ы в новых кейсах. Для AC-3 (`test_subscribe_creates_two_consent_records_for_authenticated`) — `User`-фикстура должна использовать `get_unique_suffix()` или `Sequence` (см. existing factories).

### Маркеры pytest

Тест-файл `test_common_subscribe_api.py` — это **integration** тест (HTTP via APIClient + DB). Должен попадать под `make test-integration`. Текущий файл имеет только `pytestmark = pytest.mark.django_db` — этого недостаточно для CI-фильтра. **Добавить** в новый код:

```python
pytestmark = [pytest.mark.django_db, pytest.mark.integration]
```

(Сделать это аккуратно — чтобы не сломать существующий `make test-unit`, который **должен** этот файл пропускать.)

### Frontend — почему две формы (Blue + Electric)

`ElectricSubscribeForm` используется только на демо-странице `/electric` (design comparison). Если бы мы НЕ обновили его, ВСЕ подписки через demo страницу падали бы 400 (`pdp_consent required`) после AC-4. Чтобы не оставлять «битого» демо, обновляем обе формы.

### Существующие тесты, которые сломаются

- **Backend:** `test_common_subscribe_api.py` (все 5 кейсов) — упадут с 400 после AC-4. Обязательно обновить (см. AC-8).
- **Backend:** `test_auth_registration_consent.py` — если в нём есть `from apps.users.views.authentication import normalize_consent_ip` или другие helpers — переписать импорт. Если используются только через `UserRegistrationView.post` (черный ящик через HTTP) — не трогать.
- **Frontend:** `SubscribeForm.test.tsx` — кейсы `success`, `already_subscribed`, `network_error`, `disabled-button` будут падать с ошибкой «Необходимо согласие...» — обязательно отметить PDN-чекбокс в setup.
- **Команда грепа для разработчика:**

```bash
# Backend
grep -rn "subscribe/\|SubscribeSerializer\|normalize_consent_ip\|sanitize_consent_user_agent\|sanitize_log_value\|get_consent_ip_address\|MAX_CONSENT_USER_AGENT_LENGTH\|UNSAFE_LOG_CHAR_ESCAPES\|IPV4_WITH_PORT_RE" backend/

# Frontend
grep -rn "subscribeService\|/subscribe" frontend/src/
```

### `policy_version` — почему не передаём

Default модели `UserConsent` = `"1.0"`. Та же логика, что в 35.2 (Decision 3a Pass 1): SemVer не нужен, версионирование через миграцию + `default="1.1"` при будущей правке политики. Для 35.3 — оставляем default.

---

## Definition of Done

- [ ] AC-1..AC-9 реализованы.
- [ ] Backend integration suite зелёный через Docker (`make test-integration`): `test_common_subscribe_api.py` все обновлённые + новые кейсы, `test_auth_registration_consent.py` без регрессий.
- [ ] Backend unit suite зелёный (`make test-unit` через Docker): остальные тесты `apps/common/`, `apps/users/` без падений.
- [ ] `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx` зелёный (8+ кейсов).
- [ ] `npm run test -- src/components/home/__tests__/ElectricSubscribeForm.test.tsx` зелёный (3+ кейса).
- [ ] `npm run build` (frontend) проходит без ошибок (как в 35.2 — с явным `NEXT_PUBLIC_API_URL_INTERNAL`, если запускается локально).
- [ ] OpenAPI спецификация регенерирована (`python manage.py spectacular --file docs/api-spec.yaml`); если используется `npm run generate:types` — прогнан.
- [ ] `gitnexus_detect_changes()` подтверждает: затронуты только символы из списка UPDATE/CREATE этой story.
- [ ] Manual QA через API на dev-стеке (Docker):
  - (1) POST `/subscribe/` без `pdp_consent` → 400 `{"pdp_consent":["Необходимо согласие на обработку персональных данных."]}`;
  - (2) POST `/subscribe/` `email + pdp_consent=true` (анонимный, без cookies) → 201; в БД 1 `Newsletter` + 2 `UserConsent` (`pdp_contract` + `marketing_email`) с `user=NULL`, `session_key != ""`;
  - (3) POST `/subscribe/` от залогиненного пользователя → 201; обе `UserConsent` с `user=<authed_user>`, `session_key=""`;
  - (4) POST с `X-Forwarded-For: 203.0.113.5, 10.0.0.1` → `consent.ip_address="203.0.113.5"`;
  - (5) Реактивация: подписать → отписать (`/unsubscribe/`) → подписать снова → `Newsletter.is_active=True`, добавлены 2 НОВЫХ `UserConsent` записи;
  - (6) UI на homepage Blue: PDN-чекбокс кликается, ссылка на `/privacy-policy` открывается в новой вкладке, без отметки submit заблокирован.
- [ ] `git status` показывает только файлы из «Структура файлов (изменения)» (плюс автогенерируемая `docs/api-spec.yaml` дельта).

---

## Связанные истории

- **Зависит от:** 35.1 (`done`) — модель `UserConsent`, страница `/privacy-policy`. 35.2 (`done`) — паттерн PDN-чекбокса, audit-helpers (которые рефакторятся в этой story).
- **Параллельно:** 35.4 (cookie-баннер) — может разрабатываться независимо.
- **Не блокирует:** ничего за пределами эпика 35.

---

## Примечания для разработчика

1. **Перед написанием кода** — прогони `npx gitnexus impact <symbol>` для каждого символа из «Структура файлов (изменения)» и сообщи blast radius (требование `CLAUDE.md` GitNexus Discipline).
2. **Order of operations** для безопасного рефактора AC-6:
   - (a) создать `apps/common/utils/consent_audit.py` с дублирующим кодом;
   - (b) обновить импорты в `authentication.py` на новый путь;
   - (c) запустить `make test-integration` — `test_auth_registration_consent.py` должен остаться зелёным;
   - (d) ТОЛЬКО ПОСЛЕ (c) удалить старые определения в `authentication.py`;
   - (e) повторно прогнать `make test-integration`.
3. **`apps/common/utils/__init__.py` vs `apps/common/utils.py`** — выбираем package (директория с `__init__.py`), а не файл, потому что в будущем сюда могут добавляться другие util-модули (логирование, валидация). Single-file `utils.py` антипаттерн для расширяемости.
4. **Не рефакторить** `Checkbox` компонент под `ReactNode label` — это решение задокументировано в 35.2 Dev Notes (out-of-scope, требует отдельный impact-анализ).
5. **Важно:** `request.session.save()` в `subscribe()` — единственный осознанный side-effect. Если в будущем появится требование «не создавать session для анонимных подписок» — потребуется отдельная стратегия (например, дать `UserConsent.session_key` свой default-генератор UUID), но это переоптимизация для текущего objem.
6. **Электрический фронт** (`/electric`) — тестируем минимально (3 кейса AC-9), потому что это comparison demo, не продакшен.
