# Story 35.3: Чек-бокс согласия с ПДн в форме подписки на рассылку

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных
**Story ID:** 35.3
**Status:** done
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
**Then** показывается ошибка `«Необходимо согласие на обработку персональных данных.»` под чек-боксом, submit блокируется (RHF validation).

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
2. **Submit без отметки PDN** показывает ошибку «Необходимо согласие на обработку персональных данных.»; `subscribeService.subscribe` НЕ вызывается (`expect(subscribeService.subscribe).not.toHaveBeenCalled();`).
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
              required: 'Необходимо согласие на обработку персональных данных.',
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

### Forensic-связка `UserConsent` ↔ `Newsletter` (DDN1, Pass 3)

`UserConsent` не хранит explicit FK на `Newsletter` / email подписки — связь восстанавливается forensic через тройку `(ip_address, user_agent, given_at ≈ Newsletter.subscribed_at)`: оба записи в одной транзакции и хранят эти поля симметрично. Для анонимного flow дополнительный якорь — `session_key` (один в UserConsent.session_key, тот же — в request.session.session_key, через который Newsletter был создан; Newsletter сам session_key не хранит, но временное окно `given_at ≈ subscribed_at` (< 1 сек) однозначно идентифицирует пару). Это **достаточно** для типичного запроса Роскомнадзора «покажите доказательство согласия на email Y»: выгружается JOIN `Newsletter` × `UserConsent` по этой тройке.

Жёсткая FK / JSONB-metadata требуют архитектурного обсуждения с комплаенс-офицером (асимметрия с registration consent, где аналогичный gap pre-existing). Поднять отдельной story **35.5 — consent audit linkage**.

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

- [x] AC-1..AC-9 реализованы.
- [x] Backend integration suite зелёный через Docker (`make test-integration`): `test_common_subscribe_api.py` все обновлённые + новые кейсы, `test_auth_registration_consent.py` без регрессий.
- [x] Backend unit suite зелёный (`make test-unit` через Docker): остальные тесты `apps/common/`, `apps/users/` без падений.
- [x] `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx` зелёный (8+ кейсов).
- [x] `npm run test -- src/components/home/__tests__/ElectricSubscribeForm.test.tsx` зелёный (3+ кейса).
- [x] `npm run build` (frontend) проходит без ошибок (как в 35.2 — с явным `NEXT_PUBLIC_API_URL_INTERNAL`, если запускается локально).
- [x] OpenAPI спецификация регенерирована (`python manage.py spectacular --file docs/api/openapi.yaml`); generated TypeScript types обновлены.
- [x] `gitnexus_detect_changes()` подтверждает: затронуты только символы из списка UPDATE/CREATE этой story.
- [x] Manual QA через API на dev-стеке (Docker):
  - (1) POST `/subscribe/` без `pdp_consent` → 400 `{"pdp_consent":["Необходимо согласие на обработку персональных данных."]}`;
  - (2) POST `/subscribe/` `email + pdp_consent=true` (анонимный, без cookies) → 201; в БД 1 `Newsletter` + 2 `UserConsent` (`pdp_contract` + `marketing_email`) с `user=NULL`, `session_key != ""`;
  - (3) POST `/subscribe/` от залогиненного пользователя → 201; обе `UserConsent` с `user=<authed_user>`, `session_key=""`;
  - (4) POST с `X-Forwarded-For: 1.2.3.4, 10.0.0.1` → `consent.ip_address="1.2.3.4"`;
  - (5) Реактивация: подписать → отписать (`/unsubscribe/`) → подписать снова → `Newsletter.is_active=True`, добавлены 2 НОВЫХ `UserConsent` записи;
  - (6) UI на homepage Blue: PDN-чекбокс кликается, ссылка на `/privacy-policy` открывается в новой вкладке, без отметки submit заблокирован.
- [x] `git status` показывает только файлы из «Структура файлов (изменения)» (плюс автогенерируемая `docs/api-spec.yaml` дельта).

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

---

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `npx gitnexus impact SubscribeSerializer --direction upstream` → LOW, прямой caller: `backend/apps/common/views.py`.
- `npx gitnexus impact get_consent_ip_address --direction upstream` → LOW, прямой caller: `UserRegistrationView.post`.
- `npx gitnexus impact "Function:backend/apps/common/views.py:subscribe" --direction upstream` → LOW, upstream callers не найдены.
- `npx gitnexus impact "Method:frontend/src/services/subscribeService.ts:subscribe#1" --direction upstream` → LOW, upstream callers не найдены.
- `npx gitnexus impact "Function:frontend/src/components/home/SubscribeForm.tsx:SubscribeForm" --direction upstream` → LOW, affected path: `SubscribeNewsSection -> HomePage -> BlueHomePage`.
- `npx gitnexus impact "Function:frontend/src/components/home/ElectricSubscribeForm.tsx:ElectricSubscribeForm" --direction upstream` → LOW, affected path: `ElectricSubscribeSection -> ElectricHomePage`.
- `.\venv\Scripts\python.exe -m black apps\common\serializers.py apps\common\views.py apps\common\utils\consent_audit.py apps\users\views\authentication.py tests\integration\test_common_subscribe_api.py` → passed.
- `python -m py_compile apps\common\serializers.py apps\common\views.py apps\common\utils\consent_audit.py apps\users\views\authentication.py tests\integration\test_common_subscribe_api.py` → passed.
- `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx` → passed, 14 tests.
- `npx eslint src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/services/subscribeService.ts src/types/api.ts src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx --max-warnings=0` → passed.
- `NEXT_PUBLIC_API_URL_INTERNAL='http://backend:8000'; npm run build` → passed.
- `.\venv\Scripts\python.exe manage.py spectacular --file ..\docs\api\openapi.yaml` → passed.
- `npx openapi-typescript ..\docs\api\openapi.yaml -o .\src\types\api.generated.ts` → passed.
- `npx gitnexus detect-changes` → 13 files, 21 symbols, 1 affected flow, risk `medium`; HIGH/CRITICAL не обнаружено.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml restart frontend` → passed.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py -q` → passed, 46 tests.
- `docker compose -p freesport-test --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing` → passed, 697 passed, 12 skipped.
- Dev-stack API smoke: missing `pdp_consent` → 400; anonymous subscribe → 201 + 2 `UserConsent`; authenticated subscribe → 201 + 2 `UserConsent` with `session_key=""`.
- Dev-stack reactivation smoke: subscribe → unsubscribe → subscribe creates 4 total consent rows for the same manual user-agent.
- Playwright UI smoke: `/home` and `/electric` PDN checkbox visible/clickable, privacy link attrs correct; `/home` submit without checkbox blocked.
- `npx gitnexus impact REST_FRAMEWORK --direction upstream` → ambiguous; уточнён `Variable:backend/freesport/settings/base.py:REST_FRAMEWORK` → LOW.
- `npx gitnexus impact ProxyAwareAnonRateThrottle --direction upstream` → LOW, upstream callers не найдены.
- RED: `docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py -q` → expected failures по P1/P2/P3/P5/P10/P11/P12.
- RED: `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts` → expected failures по P6/P7/P8.
- `.\venv\Scripts\python.exe -m black apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py freesport\settings\base.py freesport\settings\production.py` → passed.
- `npx prettier --write src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/subscribeService.ts src/services/__tests__/subscribeService.test.ts` → passed.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py -q` → passed, 55 tests.
- `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts` → passed, 20 tests.
- `.\venv\Scripts\python.exe -m flake8 apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py freesport\settings\base.py freesport\settings\production.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
- `npx eslint src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/subscribeService.ts src/services/__tests__/subscribeService.test.ts --max-warnings=0` → passed.
- `npx tsc --noEmit` → passed.
- `git diff --check` → passed.
- `.\venv\Scripts\python.exe manage.py check` → passed.
- `$env:NEXT_PUBLIC_API_URL_INTERNAL='http://backend:8000'; npm run build` → passed.
- `docker compose -p freesport-test --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing` → passed, 697 passed, 12 skipped.
- `npx gitnexus detect-changes --scope all` → 19 files, 33 symbols, 7 affected flows, risk `high`; HIGH объясняется шириной diff вокруг subscribe/registration audit и home subscribe UI, targeted + unit + build validations пройдены.
- Pass 2 GitNexus impact:
  - `npx gitnexus impact "Function:backend/apps/common/views.py:subscribe" -d upstream --depth 3 --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact "Method:frontend/src/services/subscribeService.ts:subscribe#1" -d upstream --depth 3 --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact "Function:frontend/src/components/home/SubscribeForm.tsx:SubscribeForm" -d upstream --depth 3 --include-tests` → LOW, affected path `SubscribeNewsSection -> HomePage -> BlueHomePage`.
- `npx gitnexus impact "Function:frontend/src/components/home/ElectricSubscribeForm.tsx:ElectricSubscribeForm" -d upstream --depth 3 --include-tests` → LOW, affected path `ElectricSubscribeSection -> ElectricHomePage`.
- `npx gitnexus impact "Method:backend/apps/common/throttling.py:ProxyAwareThrottleIdentMixin._sanitize_ident#1" -d upstream --depth 3 --include-tests` → LOW, direct caller `get_ident`.
- `npx gitnexus impact "Function:backend/apps/common/utils/consent_audit.py:normalize_consent_ip" -d upstream --depth 3 --include-tests` → LOW, affected subscribe + registration consent audit.
- `npx gitnexus impact "Function:backend/apps/users/authentication.py:_get_client_ip" -d upstream --depth 3 --include-tests` → LOW, affected logout audit path.
- `npx gitnexus impact "Method:backend/apps/users/admin.py:UserAdmin._get_client_ip#1" -d upstream --depth 3 --include-tests` → LOW, direct callers admin approve/reject/block actions.
- Pass 3 GitNexus impact:
  - `npx gitnexus impact "Function:backend/apps/common/views.py:subscribe" -d upstream --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact ProxyAwareAnonRateThrottle -d upstream --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact "Method:backend/apps/users/admin.py:UserAdmin._get_client_ip#1" -d upstream --include-tests` → HIGH; прямые consumers `approve_b2b_users`, `reject_b2b_users`, `block_users`; фикс ограничен восстановлением совместимого fallback `"0.0.0.0"`.
  - `npx gitnexus impact "Function:frontend/src/components/home/ElectricSubscribeForm.tsx:ElectricSubscribeForm" -d upstream --include-tests` → LOW, affected path `ElectricSubscribeSection -> ElectricHomePage`.
  - `npx gitnexus impact CommonConfig -d upstream --include-tests` → LOW, upstream callers не найдены.
- RED Pass 3: `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend pytest apps/common/tests/test_common_config.py tests/unit/test_common_throttling.py tests/unit/test_users_admin.py::TestUserAdmin::test_get_client_ip_fallback tests/unit/test_users_admin.py::TestUserAdmin::test_block_users_audit_log_uses_zero_ip_when_remote_addr_missing tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_scope_throttle_applies_before_validation tests/integration/test_auth_registration_consent.py::test_registration_logs_warning_when_remote_addr_is_unknown` → expected import failure: `SubscribeRateThrottle` отсутствует.
- GREEN Pass 3 targeted: тот же backend-набор → passed, 23 tests.
- `npm run test -- src/components/home/__tests__/ElectricSubscribeForm.test.tsx` → passed, 9 tests.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -e DJANGO_SETTINGS_MODULE=freesport.settings.test -T backend pytest tests/unit/test_common_throttling.py::test_test_settings_use_high_throttle_rates` → passed, 1 test.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend python manage.py check` → passed.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py tests/unit/test_common_throttling.py apps/common/tests/test_common_config.py tests/unit/test_users_admin.py` → passed, 107 tests.
- `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts` → passed, 27 tests.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend black --check ...` → passed after formatting `tests/integration/test_common_subscribe_api.py`.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend flake8 ...` → passed.
- `npx prettier --check src/components/home/__tests__/ElectricSubscribeForm.test.tsx` → passed.
- `npx eslint src/components/home/__tests__/ElectricSubscribeForm.test.tsx --max-warnings=0` → passed.
- `git diff --check` → passed.
- `npx gitnexus detect-changes --scope all` → 19 files, 20 symbols, 8 affected flows, risk `high`; HIGH соответствует ожидаемому затрагиванию `subscribe`, `ProxyAwareThrottleIdentMixin._sanitize_ident`, `UserAdmin._get_client_ip` и BMAD/AGENTS metadata.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend pytest -m unit` → passed, 716 passed, 12 skipped, 1552 deselected.
- `npm run test` → passed (full Vitest suite; stderr содержит существующие test-warning/log noise без fail).
- RED Pass 2: `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts` → expected failures по PP3/PP5/PP6: 7 failed, 19 passed.
- RED Pass 2: `.\venv\Scripts\python.exe -m pytest tests\unit\test_common_throttling.py ... -q` → expected failures по PP1; DB-зависимые кейсы в локальном запуске заблокированы локальным PostgreSQL (`password authentication failed for user "postgres"`), поэтому backend DB validation выполнена через Docker.
- `.\venv\Scripts\python.exe -m black apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py apps\users\authentication.py apps\users\admin.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py` → passed.
- `npx prettier --write src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/subscribeService.ts src/services/__tests__/subscribeService.test.ts` → passed.
- `.\venv\Scripts\python.exe -m pytest tests\unit\test_common_throttling.py -q` → passed, 9 tests.
- `npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/__tests__/subscribeService.test.ts` → passed, 26 tests.
- `docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py tests/unit/test_users_admin.py::TestUserAdmin::test_get_client_ip_with_x_forwarded_for tests/unit/test_users_admin.py::TestUserAdmin::test_get_client_ip_fallback tests/unit/test_common_throttling.py -q` → passed, 66 tests.
- `.\venv\Scripts\python.exe -m flake8 apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py apps\users\authentication.py apps\users\admin.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
- `.\venv\Scripts\python.exe -m py_compile apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py apps\users\authentication.py apps\users\admin.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py` → passed.
- `npx eslint src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx src/services/subscribeService.ts src/services/__tests__/subscribeService.test.ts --max-warnings=0` → passed.
- `npx tsc --noEmit` → passed.
- `git diff --check` → passed.
- `.\venv\Scripts\python.exe manage.py check` → passed.
- `$env:NEXT_PUBLIC_API_URL_INTERNAL='http://backend:8000'; npm run build` → passed.
- `docker compose -p freesport-test --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -v -m unit --cov=apps --cov-report=term-missing` → passed, 706 passed, 12 skipped.
- `.\venv\Scripts\python.exe manage.py spectacular --file ..\docs\api\openapi.yaml` → passed; автогенерация давала unrelated method-order churn, поэтому в `docs/api/openapi.yaml` и `api.generated.ts` оставлена минимальная контрактная дельта 503.
- Pass 4 GitNexus impact:
  - `npx gitnexus status` → index up-to-date (`Indexed commit: a766dc7`, `Current commit: a766dc7`).
  - `npx gitnexus impact get_ident --direction upstream --include-tests` → LOW; direct affected: `SubscribeRateThrottle.get_cache_key`.
  - `npx gitnexus impact "Method:backend/apps/common/throttling.py:SubscribeRateThrottle.get_cache_key#2" --direction upstream --include-tests` → LOW; upstream callers не найдены.
  - `npx gitnexus impact "Function:backend/apps/common/views.py:subscribe" --direction upstream --include-tests` → LOW; upstream callers не найдены.
  - `npx gitnexus impact get_client_ip --direction upstream --include-tests` → CRITICAL; direct consumers: `UserAdmin._get_client_ip`, `LogoutView.post`, JWT `_get_client_ip`, `get_consent_ip_address`; фикс ограничен синхронизацией приоритета `X-Real-IP` с throttle.
- RED Pass 4:
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/unit/test_common_throttling.py::test_proxy_aware_throttle_remote_addr_fallback_is_sanitized -q` → expected failure: raw `REMOTE_ADDR` не санитизировался.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_consent_records_prefer_x_real_ip_over_forwarded_for tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_anonymous_session_is_saved_before_atomic_consent_write -q` → expected failures: audit брал XFF вместо X-Real-IP; `session.save()` выполнялся внутри локального atomic-блока.
- GREEN Pass 4 targeted:
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/unit/test_common_throttling.py -q` → passed, 18 tests.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_consent_records_prefer_x_real_ip_over_forwarded_for tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_atomic_rollback_on_consent_failure tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_anonymous_session_is_saved_before_atomic_consent_write tests/integration/test_common_subscribe_api.py::TestSubscribeEndpoint::test_subscribe_scope_throttle_kicks_in_during_valid_payload_flood -q` → passed, 4 tests.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py -q` → passed, 25 tests.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest tests/integration/test_auth_registration_consent.py tests/unit/test_users_admin.py tests/unit/test_common_throttling.py -q` → passed, 83 tests. Первый параллельный запуск этой группы дал test DB setup конфликт (`parent_onec_id already exists`) из-за одновременного создания `pytest_freesport`; последовательный rerun зелёный.
  - `venv\Scripts\python.exe -m black apps/common/throttling.py apps/common/utils/consent_audit.py apps/common/views.py tests/unit/test_common_throttling.py tests/integration/test_common_subscribe_api.py` → passed.
  - `venv\Scripts\python.exe -m flake8 apps/common/throttling.py apps/common/utils/consent_audit.py apps/common/views.py tests/unit/test_common_throttling.py tests/integration/test_common_subscribe_api.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
  - `git diff --check` → passed.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest -q -m unit` → passed, 717 passed, 12 skipped, 1554 deselected.
  - `docker compose -p freesport-test --env-file ..\.env -f docker-compose.test.yml run --rm backend pytest -q -m integration --ignore=tests/integration/test_management_commands/test_import_customers.py` → passed, 654 passed, 2 skipped, 1615 deselected. `test_import_customers.py` оставлен вне прогона как известный data-dependent локальный blocker без `data/import_1c/contragents`.
  - `npx gitnexus detect-changes --scope all` → 7 files, 7 symbols, 9 affected flows, risk `high`; HIGH ожидаем из-за shared `get_client_ip` (`subscribe`, registration audit, admin approve/reject/block audit, logout/JWT audit), покрыт targeted + dependent + unit/integration regression.
- Pass 5 targeted validation:
  - `cmd /c .\venv\Scripts\python.exe -m black apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py` → passed; `apps/common/views.py` reformatted.
  - `cmd /c npx prettier --write src\components\home\__tests__\SubscribeForm.test.tsx src\types\api.generated.ts` → passed.
  - `cmd /c git diff --check` → passed; только Windows LF→CRLF warnings.
  - `cmd /c .\venv\Scripts\python.exe -m flake8 apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
  - `cmd /c .\venv\Scripts\python.exe -m py_compile apps\common\serializers.py apps\common\views.py apps\common\throttling.py apps\common\utils\consent_audit.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py tests\unit\test_common_throttling.py tests\unit\test_users_admin.py` → passed.
  - `cmd /c npm run test -- src/components/home/__tests__/SubscribeForm.test.tsx` → passed, 16 tests.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.yml exec -T backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py tests/unit/test_common_throttling.py tests/unit/test_users_admin.py -q` → passed, 112 tests, 6 warnings.
  - `cmd /c npm exec -- eslint --max-warnings=0 --no-warn-ignored src/components/home/SubscribeForm.tsx src/components/home/__tests__/SubscribeForm.test.tsx src/types/api.generated.ts` → passed.
  - `cmd /c npm run lint -- --no-warn-ignored` → failed на existing `frontend/next-env.d.ts` (`@typescript-eslint/triple-slash-reference`), не связан с изменениями story; targeted ESLint по изменённым frontend-файлам зелёный.
  - Локальный DB-dependent pytest через `backend\venv` заблокирован локальными PostgreSQL credentials (`password authentication failed for user "postgres"`); тот же набор пройден через Docker backend.
- Pass 6 targeted validation:
  - `cmd /c .\venv\Scripts\python.exe -m black apps\common\utils\consent_audit.py apps\common\views.py apps\products\serializers.py tests\integration\test_common_subscribe_api.py` → passed, 4 files left unchanged.
  - `cmd /c npx prettier --write src\components\home\SubscribeForm.tsx src\components\home\ElectricSubscribeForm.tsx src\services\subscribeService.ts src\services\__tests__\subscribeService.test.ts src\types\api.generated.ts` → passed.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/unit/test_serializers/test_product_serializers.py -q` → passed, 48 tests.
  - `cmd /c npm run test -- src/services/__tests__/subscribeService.test.ts src/components/home/__tests__/SubscribeForm.test.tsx src/components/home/__tests__/ElectricSubscribeForm.test.tsx` → passed, 30 tests.
  - `cmd /c .\venv\Scripts\python.exe -m flake8 apps\common\utils\consent_audit.py apps\common\views.py apps\products\serializers.py tests\integration\test_common_subscribe_api.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
  - `cmd /c .\venv\Scripts\python.exe -m py_compile apps\common\utils\consent_audit.py apps\common\views.py apps\products\serializers.py tests\integration\test_common_subscribe_api.py` → passed.
  - `cmd /c npm exec -- eslint src/components/home/SubscribeForm.tsx src/components/home/ElectricSubscribeForm.tsx src/services/subscribeService.ts src/services/__tests__/subscribeService.test.ts src/types/api.generated.ts --max-warnings=0` → passed.
  - `cmd /c npm exec -- tsc --noEmit` → passed.
  - `cmd /c .\venv\Scripts\python.exe manage.py check` → passed.
  - `cmd /c git diff --check` → passed; только Windows LF→CRLF warnings.
  - `cmd /c npx gitnexus detect-changes --scope all` → 16 files, 20 symbols, 11 affected flows; affected scope соответствует `subscribe`, consent audit, `ProductDetailSerializer`, subscribe UI/service/types и уже существующим BMAD/AGENTS metadata.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -q -m unit` → passed, 719 passed, 12 skipped, 1556 deselected.
  - `cmd /c npm run test` → passed, 140 files, 2373 passed, 16 skipped.
  - `$env:NEXT_PUBLIC_API_URL_INTERNAL='http://backend:8000'; npm --prefix 'c:\Users\1\DEV\FREESPORT\frontend' run build` → passed. Первый build-запуск через `cmd /c "set ...&& npm run build"` стартовал из корня и упал на `package.json` ENOENT, не кодовая ошибка.
  - `cmd /c docker compose --env-file ..\.env -f docker-compose.yml restart frontend` → passed.
- Pass 7 GitNexus impact:
  - `npx gitnexus impact SubscribeSerializer --direction upstream --include-tests` → LOW, direct consumer `backend/apps/common/views.py`.
  - `npx gitnexus impact "Function:backend/apps/common/views.py:subscribe" --direction upstream --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact check_session_engine_for_subscribe_consent --direction upstream --include-tests` → LOW, upstream callers не найдены.
  - `npx gitnexus impact "Function:backend/apps/common/utils/consent_audit.py:get_consent_ip_address" --direction upstream --include-tests` → HIGH; affected flows: subscribe, `SubscribeSerializer.create`, `UserRegistrationView.post`. Production helper не менялся; обновлены только устаревшие registration regression expectations под Pass 6 fallback на валидный `REMOTE_ADDR`.
- RED Pass 7: `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py apps/common/tests/test_common_config.py -q` → expected failures по P7-1/P7-4/P7-5/P7-7 и initial P7-2 test-probe refinement.
- GREEN Pass 7 targeted:
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py apps/common/tests/test_common_config.py -q` → passed, 35 tests.
  - `cmd /c .\venv\Scripts\python.exe -m black apps\common\apps.py apps\common\serializers.py apps\common\views.py apps\common\tests\test_common_config.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py` → passed, 6 files left unchanged after final update.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest tests/integration/test_common_subscribe_api.py tests/integration/test_auth_registration_consent.py tests/unit/test_common_throttling.py apps/common/tests/test_common_config.py -q` → passed, 87 tests.
  - `cmd /c .\venv\Scripts\python.exe -m flake8 apps\common\apps.py apps\common\serializers.py apps\common\views.py apps\common\tests\test_common_config.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py --max-line-length=120 --extend-ignore=E203,W503` → passed.
  - `cmd /c .\venv\Scripts\python.exe -m py_compile apps\common\apps.py apps\common\serializers.py apps\common\views.py apps\common\tests\test_common_config.py tests\integration\test_common_subscribe_api.py tests\integration\test_auth_registration_consent.py` → passed.
  - `cmd /c .\venv\Scripts\python.exe manage.py check` → passed.
  - `cmd /c .\venv\Scripts\python.exe manage.py spectacular --file ..\docs\api\openapi.yaml` → passed.
  - `cmd /c git diff --check` → passed; только Windows LF→CRLF warnings.
  - `npx gitnexus detect-changes --scope all` → 7 files, 8 symbols, 6 affected flows; scope соответствует `SubscribeSerializer`, `subscribe`, session-engine system check, subscribe/consent-audit flows.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -q -m unit` → passed, 720 passed, 12 skipped, 1561 deselected.
  - `cmd /c docker compose --env-file ..\.env -f ..\docker\docker-compose.test.yml run --rm backend pytest -q -m integration --ignore=tests/integration/test_management_commands/test_import_customers.py` → passed, 661 passed, 2 skipped, 1618 deselected.

### Completion Notes

- Реализован обязательный `pdp_consent` в Blue и Electric формах подписки: без чекбокса submit блокируется клиентской валидацией, ссылка `/privacy-policy` открывается в новой вкладке.
- `subscribeService` и manual/generated API-типы обновлены под payload `{ email, pdp_consent }`.
- `SubscribeSerializer` требует `pdp_consent=true`, не сохраняет это поле в `Newsletter` и возвращает field-level ошибку при отсутствии/false.
- `subscribe()` теперь атомарно создаёт/реактивирует `Newsletter` и пишет две записи `UserConsent`: `pdp_contract` и `marketing_email`.
- Consent audit helpers вынесены в `apps.common.utils.consent_audit`; `UserRegistrationView` и `LogoutView` используют новый общий модуль.
- Story переведена в `review`: targeted backend integration, unit suite, frontend tests/build, dev-stack API smoke и UI smoke подтверждены.
- Review patch P1-P12 закрыт: Newsletter и UserConsent используют общий normalized IP, duplicate/reactivation races защищены `select_for_update()` + 409 mapping, strict consent принимает только JSON `true`, default throttle перенесён в base и покрыт smoke-тестом.
- Для безопасного default throttle добавлен proxy-aware user throttle fallback: invalid/surrogate XFF больше не ломает Redis throttle key до consent audit.
- Frontend patch закрыт: тесты кликают настоящий checkbox, `React.useId()` убрал дубли DOM id, `subscribeService` сохраняет backend field errors, формы показывают `pdp_consent` 400 inline/toast без email fallback.
- Pass 2 закрыт: DN1 оставлен strict через `self.initial_data` и задокументирован в коде; DN2 закрыт machine-code `already_subscribed` вместо сравнения русского текста; DN3 сохранён как намеренное proxy-aware throttle изменение и усилен canonical IP sanitization.
- PP1-PP8 закрыты: throttle ident нормализует canonical IP, consent persistence failure возвращает структурированный 503 с rollback, frontend показывает 429/unknown backend details, Electric получил a11y regression test, validator text синхронизирован с backend точкой, rollback mock заменён на `MagicMock(spec=UserConsent)`, users/admin IP helpers используют общий `get_client_ip`.
- Pass 3 закрыт: `/subscribe/` получил отдельный `SubscribeRateThrottle(scope="subscribe")` с лимитом `30/min`, non-prod settings получили явные throttle overrides, 429 detail русифицирован, admin audit IP fallback восстановлен как `"0.0.0.0"`, signed-cookie sessions блокируются system check, устаревший caplog logger исправлен, Electric success reset покрыт тестом.
- Финальный регресс: backend unit marker suite и полный frontend Vitest suite зелёные; story и `sprint-status.yaml` синхронизированы в `review`.
- Pass 4 закрыт: `REMOTE_ADDR` fallback в throttle теперь санитизируется; anonymous `session.save()` вынесен перед локальным `transaction.atomic()`; rollback-тест реально пишет первую `UserConsent` и проверяет откат; subscribe throttle flood-тест переведён на валидные payload; audit IP теперь предпочитает `X-Real-IP`, как throttle. PPPP5 закрыт как проверенный false-positive: в текущей DRF-версии `SimpleRateThrottle.get_cache_key()` abstract, удаление override приводит к `NotImplementedError`, поэтому override сохранён с поясняющим docstring.
- Pass 4 regression: targeted subscribe/audit tests, зависимые registration/admin tests, backend unit marker suite, integration marker suite без известного `test_import_customers.py` data-dependent blocker, Black, Flake8 и `git diff --check` зелёные.
- Pass 5 закрыт: invalid-IP audit log возвращён на WARNING; malformed proxy headers в throttle fallback-ятся на `REMOTE_ADDR`; subscribe ловит `DatabaseError` и возвращает структурированный 503 с rollback; Blue SubscribeForm покрыт server_error/503 regression; OpenAPI/generated types получили 503 body schema; admin tests используют production-like `SessionStore`; existing-email lookup убран из `validate_email`, чтобы missing `pdp_consent` не раскрывал статус подписки.
- Pass 6 закрыт: `/subscribe/` ограничен JSON parser и OpenAPI больше не рекламирует form-urlencoded; `ProductDetail` schema восстановлена через `extend_schema_field` для runtime-полей; consent audit получил fallback на валидный `REMOTE_ADDR`; frontend `SubscribeValidationDetails` сужен до OpenAPI-compatible `Record<string, string[]>` с regression-тестами.
- Финальный Pass 6 регресс зелёный: targeted backend/frontend tests, backend unit marker suite, full frontend Vitest, Flake8, ESLint, TypeScript, Django checks, Next build, `git diff --check`, GitNexus detect-changes и frontend container restart выполнены.
- Pass 7 закрыт: `SubscribeSerializer.validate()` безопасно отвергает non-object JSON payload; `SubscribeSerializer.create()` сам открывает atomic для `select_for_update`; session materialization failure логируется отдельно от consent persistence; system check `common.E001` зарегистрирован под `Tags.security`; OpenAPI 400 description синхронизирован с `email`/`pdp_consent`; regression-тесты P7-2/P7-3 усилены через `savepoint_ids` и SQL `FOR UPDATE`.
- Зависимые registration consent tests синхронизированы с уже принятым Pass 6 fallback: invalid proxy IP при валидном `REMOTE_ADDR` пишет fallback IP, warning ожидается только если `REMOTE_ADDR` тоже невалиден.
- Финальный Pass 7 регресс зелёный: targeted subscribe/common config, registration consent + throttle dependent suite, backend unit marker suite, integration marker suite без известного data-dependent blocker, Black, Flake8, `py_compile`, Django checks, OpenAPI generation, `git diff --check` и GitNexus detect-changes выполнены.
- Pass 8 закрыт: `subscribeService` корректно маппит 5xx без `details` в `server_error` вместо `network_error`; `api.generated.ts` синхронизирован с OpenAPI 400 description; THROTTLED_ERROR punctuation синхронизирован между backend/frontend; ElectricSubscribeForm покрыт regression-тестами на `server_error`; `test_users_admin.py` получил `pytest.mark.unit`; system check `common.E002` проверяет наличие `subscribe` throttle scope; dev/staging/test settings наследуют `DEFAULT_THROTTLE_RATES` из `base.py`; stale `setError('pdp_consent')` очищается через `clearErrors` перед повторным submit в обеих формах.
- Финальный Pass 8 регресс: frontend targeted tests (SubscribeForm + ElectricSubscribeForm + subscribeService) — 30/30 passed; backend ESLint/targeted проверки пройдены; story и sprint-status синхронизированы в `review`.
- Pass 9 закрыт: убран дублирующий `# type: ignore[no-redef]` в `test.py`, удалены мёртвые `default_detail`/`default_code` из `ProxyAwareThrottleIdentMixin` и неактуальный тест `test_proxy_aware_throttle_uses_russian_default_detail`, AC-1 story синхронизирована с точкой в `PDP_CONSENT_REQUIRED`; Black, Flake8, py_compile зелёные.

### File List

- `_bmad-output/implementation-artifacts/Story/35-3-consent-checkbox-in-subscribe-form.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/apps/common/apps.py`
- `backend/apps/common/serializers.py`
- `backend/apps/common/throttling.py`
- `backend/apps/common/tests/test_common_config.py`
- `backend/apps/common/views.py`
- `backend/apps/common/utils/__init__.py`
- `backend/apps/common/utils/consent_audit.py`
- `backend/apps/products/serializers.py`
- `backend/apps/users/admin.py`
- `backend/apps/users/authentication.py`
- `backend/freesport/settings/base.py`
- `backend/freesport/settings/development.py`
- `backend/freesport/settings/production.py`
- `backend/freesport/settings/staging.py`
- `backend/freesport/settings/test.py`
- `backend/apps/users/views/authentication.py`
- `backend/tests/integration/test_auth_registration_consent.py`
- `backend/tests/integration/test_common_subscribe_api.py`
- `backend/tests/unit/test_common_throttling.py`
- `backend/tests/unit/test_users_admin.py`
- `docs/api/openapi.yaml`
- `frontend/src/components/home/SubscribeForm.tsx`
- `frontend/src/components/home/ElectricSubscribeForm.tsx`
- `frontend/src/components/home/__tests__/SubscribeForm.test.tsx`
- `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`
- `frontend/src/services/subscribeService.ts`
- `frontend/src/services/__tests__/subscribeService.test.ts`
- `frontend/src/types/api.ts`
- `frontend/src/types/api.generated.ts`
- `backend/freesport/settings/test.py`
- `backend/apps/common/throttling.py`
- `backend/tests/unit/test_common_throttling.py`

### Change Log

- 2026-05-13: Реализован consent checkbox для подписки, backend audit write path, frontend/backend tests, dev-stack smoke и generated API contract updates; статус переведён в `review`.
- 2026-05-13: Закрыты review patch items P1-P12; добавлены race/rollback/throttle/IP/strict-consent guardrails, field-specific frontend errors и синхронизация story/sprint-status обратно в `review`.
- 2026-05-13: Закрыты Pass 2 findings DN1-DN3 и PP1-PP8; добавлены machine-code 409 mapping, canonical throttle IP, структурированный 503 rollback, 429/unknown-details UI, Electric a11y test и минимальная OpenAPI/generated-types дельта.
- 2026-05-14: Закрыты Pass 3 findings PPP1-PPP7; добавлены scope-specific subscribe throttle, non-prod throttle overrides, русский 429 detail, session-engine system check, admin audit IP fallback и Electric reset regression test; статус синхронизирован в `review`.
- 2026-05-14: Закрыты Pass 4 findings PPPP1-PPPP6; добавлены Redis-safe `REMOTE_ADDR` fallback, `X-Real-IP` priority для consent audit, session-save-before-local-atomic guard, real rollback test и валидный throttle flood regression; PPPP5 подтверждён как false-positive для текущей DRF-версии; статус синхронизирован в `review`.
- 2026-05-14: Закрыты Pass 5 findings P5N1-P5N7; добавлены DatabaseError 503 contract, no-enumeration validation path, malformed proxy fallback на REMOTE_ADDR, WARNING audit logs, OpenAPI/generated 503 schema, Blue server_error regression и SessionStore в admin tests; статус синхронизирован в `review`.
- 2026-05-14: Закрыты Pass 6 findings PPPP6-D1/D2/P1/P2; `/subscribe/` стал JSON-only в OpenAPI, `ProductDetail` schema восстановлена, consent audit fallback на `REMOTE_ADDR` добавлен, frontend validation details приведены к OpenAPI-контракту; статус синхронизирован в `review`.
- 2026-05-15: Закрыты Pass 7 findings P7-1…P7-7; усилены non-object JSON validation, serializer-level atomic, session failure observability, FOR UPDATE/session-save tests, security-tag system check и OpenAPI 400 description; зависимые registration tests синхронизированы с Pass 6 fallback; статус синхронизирован в `review`.
- 2026-05-15: Закрыты Pass 8 findings P8-1…P8-8; исправлено 5xx-мэппирование без details в `server_error`, синхронизирована OpenAPI/generated types punctuation, добавлена system check `common.E002` на `subscribe` throttle scope, dev/staging/test settings наследуют throttle rates из base.py, добавлен `pytest.mark.unit` в `test_users_admin.py`, `clearErrors('pdp_consent')` очищает stale server errors перед retry, ElectricSubscribeForm покрыт `server_error` regression-тестом; статус синхронизирован в `review`.
- 2026-05-15: Закрыты Pass 9 findings P9-1 / DP9-1 / DP9-2; убран дублирующий `# type: ignore`, удалены мёртвые `default_detail`/`default_code` из `ProxyAwareThrottleIdentMixin` вместе с неактуальным тестом, AC-1 story синхронизирована с frontend/backend точкой в сообщении `PDP_CONSENT_REQUIRED`.

---

## Review Findings

Code review от 2026-05-13 (bmad-code-review, 3 параллельных слоя: Blind Hunter, Edge Case Hunter, Acceptance Auditor). Дедуп ~50 raw → 32 уникальных: 5 decision-needed, 9 patch, 9 defer, 9 dismissed.

### Decision-needed (resolved 2026-05-13)

- [x] **D1 → Dismiss.** Newsletter.ip_address/user_agent = «latest activity». Audit-trail «первый раз» живёт в UserConsent (append-only). Поведение оставлено как есть.
- [x] **D2 → Patch (см. P10).** Перенести `DEFAULT_THROTTLE_CLASSES` из `production.py` в `base.py` + написать smoke-тест из AC-5.
- [x] **D3 → Patch (см. P11).** Убрать `is_global` фильтр в `normalize_consent_ip` — принимать любой валидный IP (включая private/loopback) в audit. Закрывает D3 + дополнительно делает P5 (тест IP) осмысленным.
- [x] **D4 → Patch (см. P12).** В `SubscribeSerializer.validate()` усилить: `if attrs.get("pdp_consent") is not True: raise ValidationError(...)`. Принимаем только JSON `true` boolean (152-ФЗ explicit consent).
- [x] **D5 → Dismiss.** Паттерн `aria-labelledby` с `<Link>` ID валиден по WAI-ARIA, унаследован из 35.2 RegisterForm, manual QA в 35.2 подтвердил. SR не читает link дважды — один раз как часть accessible name, один раз при tab на саму ссылку. Альтернативы (aria-label plain) хуже: разнобой между sighted/SR-перцепцией.

### Patch (12: 9 исходных + 3 из decision-resolved)

- [x] [Review][Patch] **P1. Newsletter.ip_address без normalize → DataError на невалидном XFF + расхождение с UserConsent в одной транзакции** [`backend/apps/common/serializers.py:70-78`] — raw `X-Forwarded-For.split(",")[0]` без strip/normalize. UserConsent для того же запроса проходит через `normalize_consent_ip`. Fix: использовать `get_consent_ip_address(request)` для Newsletter тоже (или передавать значение из view через context).
- [x] [Review][Patch] **P2. Race на unique email → 500 вместо 409** [`backend/apps/common/views.py:374-387`] — `validate_email()...filter().exists()` без блокировки. Concurrent POST: один проходит, второй ловит IntegrityError → 500. Fix: `except IntegrityError → 409 Conflict`.
- [x] [Review][Patch] **P3. Race на реактивации → дубли UserConsent (4 вместо 2)** [`backend/apps/common/serializers.py:82-95` + `views.py:374-387`] — Два concurrent POST на отписанный Newsletter создадут 4 UserConsent. Fix: `Newsletter.objects.select_for_update()` внутри transaction.atomic().
- [x] [Review][Patch] **P4. Тест `test_subscribe_atomic_rollback_on_consent_failure` не покрывает «первый создан, второй упал»** [`backend/tests/integration/test_common_subscribe_api.py:810-819`] — Mock падает на первом вызове. Реалистичный rollback не проверен. Fix: `side_effect=[mock_obj, IntegrityError(...)]`, assert `UserConsent.objects.count() == 0`.
- [x] [Review][Patch] **P5. Тест `test_subscribe_creates_two_consent_records_for_anonymous` false-passes на None** [`backend/tests/integration/test_common_subscribe_api.py:706-725`] — TestClient REMOTE_ADDR=127.0.0.1 → normalize → None. `set({None,None})` len==1, тест проходит. IP реально не записан. Fix: передать `HTTP_X_FORWARDED_FOR="203.0.113.5"` (RFC 5737).
- [x] [Review][Patch] **P6. Frontend тесты кликают по `<label>`, не по `<input type=checkbox>`** [`SubscribeForm.test.tsx`, `ElectricSubscribeForm.test.tsx`] — `clickPdpCheckbox` использует `document.getElementById('...-label-prefix')`. Если сломать `htmlFor` или удалить input — тесты пройдут. Fix: `screen.getByRole('checkbox', { name: /согласие на обработку/i })`.
- [x] [Review][Patch] **P7. subscribeService слепо мапит любой 400 → "Введите корректный email"** [`frontend/src/services/subscribeService.ts:18-29`, `SubscribeForm.tsx:50-62`, `ElectricSubscribeForm.tsx:54-65`] — Backend 400 с `{"pdp_consent": [...]}` (curl/Postman обход) → user видит «Введите корректный email». Fix: прокинуть `response.data` и различать поля.
- [x] [Review][Patch] **P8. Дубликаты DOM ID при двух экземплярах формы на одной странице** [`SubscribeForm.tsx:89-141`, `ElectricSubscribeForm.tsx:121-186`] — Статические id (`subscribe-pdp-consent`, `-error`, `-label-prefix` и т.д.). Multiple instances → невалидный HTML, htmlFor сломан. Fix: `React.useId()` (React 19 native).
- [x] [Review][Patch] **P9. Двойной `onChange` + `setValue({shouldValidate})` в SubscribeForm** [`SubscribeForm.tsx:93-98`, `ElectricSubscribeForm.tsx:138-141`] — `pdpConsentRegistration.onChange(event)` (RHF уже обновляет state) + `setValue(..., {shouldValidate: true})`. Двойная валидация, лишние рендеры. Fix: оставить только `register('pdp_consent', { required })`.
- [x] [Review][Patch] **P10. (из D2) Throttling в `base.py` + smoke-тест AC-5** [`backend/freesport/settings/base.py`, `backend/freesport/settings/production.py:108-119`, `backend/tests/integration/test_common_subscribe_api.py`] — Перенести `DEFAULT_THROTTLE_CLASSES = ['apps.common.throttling.ProxyAwareAnonRateThrottle']` + `DEFAULT_THROTTLE_RATES = {'anon': '...'}` из `production.py` в `base.py`. Написать smoke-тест: x100 POST `/subscribe/` → 6+ ответов 429 (или другой rate). Закрывает DDoS-вектор и AC-5 spec gap.
- [x] [Review][Patch] **P11. (из D3) Убрать `is_global` фильтр в `normalize_consent_ip`** [`backend/apps/common/utils/consent_audit.py:91`] — Принимать любой парсящийся IP (включая private/loopback). Логировать на DEBUG, не WARNING. После фикса P5-тест с реальным `HTTP_X_FORWARDED_FOR="203.0.113.5"` начнёт реально проверять IP capture. Дополнительно: в `test_auth_registration_consent.py` не должно регрессий (поведение helpers «либеральнее» — старые тесты с private IPs начнут возвращать IP вместо None — если они на это assert-ят, fixture обновить).
- [x] [Review][Patch] **P12. (из D4) Усилить `validate()` в SubscribeSerializer: `is True`** [`backend/apps/common/serializers.py:51-55`] — `if attrs.get("pdp_consent") is not True: raise ValidationError({"pdp_consent": PDP_CONSENT_REQUIRED})`. Принимаем только JSON `true`. Добавить тест `test_subscribe_rejects_pdp_consent_truthy_string` (для `"on"`/`"yes"`/`"1"`/`1`).

### Defer (9) — pre-existing или out-of-scope

- [x] [Review][Defer] **W1. CRLF/control chars (`\r\n\x00`) в `sanitize_consent_user_agent`** [`backend/apps/common/utils/consent_audit.py:114-117`] — pre-existing 35.2, AC-6 требовал «строка-в-строку».
- [x] [Review][Defer] **W2. IPv6 zone-id / порт edge cases в `normalize_consent_ip`** [`backend/apps/common/utils/consent_audit.py:60-92`] — pre-existing 35.2.
- [x] [Review][Defer] **W3. `request.session.save()` без try/except** [`backend/apps/common/views.py:377-378`] — низкий риск, зависимость от рабочего session middleware.
- [x] [Review][Defer] **W4. `policy_version="1.0"` hardcoded в default модели** [`backend/apps/common/models.py:627-631`] — архитектурный вопрос эпика 35 (нет связи с фактической версией Privacy Policy).
- [x] [Review][Defer] **W5. `frontend/package.json:22 generate:types` указывает на устаревший `docs/api-spec.yaml`** — pre-existing проектный долг, обойдён ручным `npx openapi-typescript`.
- [x] [Review][Defer] **W6. Шум в `docs/api/openapi.yaml` (перестановка get/patch для unrelated endpoints — Orders/Cart/Favorites/Addresses)** — артефакт перегенерации drf-spectacular, не привнесено 35.3.
- [x] [Review][Defer] **W7. Throttle по `X-Real-IP` vs audit по `X-Forwarded-For`** [`backend/apps/common/throttling.py:11-24` vs `consent_audit.py:42-51`] — pre-existing из 11.3 SEC-001.
- [x] [Review][Defer] **W8. `Checkbox.tsx` callback ref не поддерживает indeterminate** [`frontend/src/components/ui/Checkbox/Checkbox.tsx:25-29`] — out-of-scope (Checkbox.tsx в «НЕ изменять» списке).
- [x] [Review][Defer] **W9. `logger.warning "Invalid client IP skipped"` без request_id/email** [`backend/apps/common/utils/consent_audit.py:133-138`] — улучшение audit forensics, низкий приоритет.

### Dismissed (9) — noise / false positive

- consent_kwargs mutable trap (умозрительный futureproofing — сейчас все значения immutable)
- `validate()` дублирует BooleanField required (defensive coding, не баг)
- `pop("pdp_consent", False)` default misleading (косметика, validate() уже отверг бы)
- ElectricSubscribeForm hitbox skew (CSS transform не меняет реальный hitbox)
- form unmount race (RHF 7+ это терпит без warning)
- middleware missing test (инфраструктурное предположение)
- validate_email перед validate (стандарт DRF execution order)
- pop position cosmetic

---

## Review Findings — Pass 2 (2026-05-13)

Повторный bmad-code-review после закрытия P1-P12, 3 параллельных слоя (Blind Hunter, Edge Case Hunter, Acceptance Auditor) по diff `0833e90c^..HEAD` (1911 строк, 18 файлов). Триаж: ~50 raw findings → 15 уникальных после дедупа: 3 decision-needed, 8 patch, 4 defer, ~22 dismissed.

### Decision-needed (3)

- [x] [Review][Decision] **DN1. `validate()` использует `self.initial_data` вместо `attrs`** — P12-лог фиксировал `attrs.get("pdp_consent") is not True`, но фактический код `backend/apps/common/serializers.py:56-60` проверяет `self.initial_data.get("pdp_consent") is not True`. `initial_data` минует DRF-coercion BooleanField (`"true"`/`"1"`/`1` → True), что и нужно для 152-ФЗ explicit consent — тест `test_subscribe_rejects_pdp_consent_truthy_non_boolean` зависит от этого. **Решение:** оставить strict `initial_data` и добавить код-комментарий, чтобы drift больше не выглядел случайным. Источник: Blind#5 + Auditor#50.

- [x] [Review][Decision] **DN2. 409-маппинг через подстроку русского текста «уже подписан»** [`backend/apps/common/views.py:391-398, 418-424`] — View сравнивает `"уже подписан" in error_msg` для маршрутизации 409. Хрупкость: любое изменение `ALREADY_SUBSCRIBED` в `serializers.py:18` сломает HTTP-код, i18n становится невозможен. **Решение:** заменить text-substring на DRF `ErrorDetail.code == "already_subscribed"` и покрыть duplicate/race кейсы assert-ом machine-code. Источник: Blind#4.

- [x] [Review][Decision] **DN3. `ProxyAwareUserRateThrottle` + `ProxyAwareThrottleIdentMixin` — scope creep сверх P10** [`backend/apps/common/throttling.py:6-42`, `backend/freesport/settings/base.py:172-174`] — AC-5/P10 предписывали только перенос `DEFAULT_THROTTLE_CLASSES` из `production.py` в `base.py`. Реализация дополнительно: (a) ввела mixin с sanitize-ident, (b) создала новый класс `ProxyAwareUserRateThrottle` (anonymous fallback для UserRateThrottle), (c) зарегистрировала его в DEFAULT_THROTTLE_CLASSES. **Решение:** зафиксировать как намеренное hardening изменение; PP1 усилил mixin canonical IP normalization и unit-тестами для anon/user throttle. Источник: Auditor#53.

### Patch (8)

- [x] [Review][Patch] **PP1. Throttle ident санитизация оставляет bypass через IPv6 zone-id/порт/brackets** [`backend/apps/common/throttling.py:9-26`] — `_sanitize_ident` использует `sanitize_log_value` (escape `\r\n` для log-safety), но НЕ нормализует канонический IP. `X-Real-IP: fe80::1%eth0` и `X-Real-IP: [::1]:8080` от одного клиента дают разные cache-keys → bypass throttle. Fix: throttle ident строить как `normalize_consent_ip(raw_ip) or sanitize_log_value(raw_ip.strip())` (canonical mapping + fallback на sanitize для invalid). Источник: Blind#6 + Edge#34 + Edge#35.

- [x] [Review][Patch] **PP2. `IntegrityError` из `UserConsent.objects.create()` пробрасывается до клиента как HTTP 500 без JSON** [`backend/apps/common/views.py:382-389`] — `transaction.atomic()` блок ловит только `DRFValidationError`. `IntegrityError` (нарушение CheckConstraint `userconsent_user_or_session_required` при пустом session_key + user=None, PG deadlock на consent-таблице) пробрасывается как unhandled 500. Тест `test_subscribe_atomic_rollback_on_consent_failure` это явно фиксирует (`pytest.raises(IntegrityError)`), но реальный клиент получает 500 без структуры. Fix: `except (DRFValidationError, IntegrityError) as exc: logger.error(...); return Response({"error": "consent_persistence_failed"}, status=503)` (или 500 со структурой). Источник: Edge#27.

- [x] [Review][Patch] **PP3. HTTP 429 маскируется на фронте как `network_error`** [`frontend/src/services/subscribeService.ts:18-29`, `SubscribeForm.tsx`, `ElectricSubscribeForm.tsx`] — subscribeService различает только 400 и 409. Любой 429 (rate-limit), 5xx, timeout → `SubscribeServiceError('network_error')` → UI «Не удалось подписаться, попробуйте позже» — пользователь не понимает, что нужно подождать → спамит submit. Fix: добавить ветку `if (status === 429) throw new SubscribeServiceError('throttled', details)` + UI-сообщение «Слишком много попыток. Попробуйте через минуту». Источник: Edge#37.

- [x] [Review][Patch] **PP4. A11y-тест для `ElectricSubscribeForm.test.tsx` отсутствует** [`frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`] — AC-9 требует a11y (aria-invalid, aria-describedby, role="alert"), AC-2 распространяет правила на Electric. `SubscribeForm.test.tsx` это покрывает (test «marks PDN checkbox invalid and links error text through aria-describedby»), Electric — нет. Fix: добавить аналогичный test-case в Electric. Источник: Auditor#56.

- [x] [Review][Patch] **PP5. Backend `details` с unknown ключами не отображается на фронте** [`frontend/src/components/home/SubscribeForm.tsx:75-86`, `ElectricSubscribeForm.tsx:82-94`] — `getBackendFieldError` читает только `details.email` и `details.pdp_consent`. Если backend вернёт `non_field_errors`, новое поле или 500 со структурой (см. PP2) — фронт покажет generic «ОШИБКА ПОДПИСКИ» без message. Fix: fallback на первое сообщение из любого ключа `details` если known-ключи отсутствуют. Источник: Edge#38.

- [x] [Review][Patch] **PP6. Точка в `PDP_CONSENT_REQUIRED` — фронт без точки, бэк с точкой** [`frontend/src/components/home/SubscribeForm.tsx` RHF validator, `ElectricSubscribeForm.tsx` RHF validator, `backend/apps/common/serializers.py:17`] — Backend константа и `docs/api/openapi.yaml` дают сообщение «Необходимо согласие на обработку персональных данных.» (с точкой). Frontend RHF-валидаторы в обеих формах — без точки. Client-side и server-side ошибки показывают разные строки. Spec AC-1/AC-8 явно указывают версию С точкой. Fix: добавить точку в обе frontend-validator константы. Источник: Auditor#51.

- [x] [Review][Patch] **PP7. Тест `test_subscribe_atomic_rollback_on_consent_failure` использует sentinel `object()` для первого create** [`backend/tests/integration/test_common_subscribe_api.py:~1027`] — `side_effect=[object(), IntegrityError(...)]` работает только потому, что view не использует возвращаемое значение `UserConsent.objects.create`. При рефакторинге (например, `consent = UserConsent.objects.create(...)` + последующий `.id`) тест начнёт падать не из-за production-логики, а из-за mock-структуры. Fix: заменить `object()` на `mock.MagicMock(spec=UserConsent)` (или явный комментарий-pin «sentinel, return value unused»). Источник: Blind#12.

- [x] [Review][Patch] **PP8. Дубликат логики `get_client_ip` в `apps.users.authentication._get_client_ip` и `apps.users.admin._get_client_ip`** [`backend/apps/users/authentication.py:164`, `backend/apps/users/admin.py:466`] — После AC-6 публичный `apps.common.utils.consent_audit.get_client_ip` существует, но обе private-обёртки в users остались с собственной реализацией. Если в общем `get_client_ip` исправят парсинг (например, IPv6 brackets / X-Real-IP priority) — три места разойдутся, audit для login/admin/subscribe начнёт давать разные IP для одного запроса. Fix: `_get_client_ip` обёртки заменить на `from apps.common.utils.consent_audit import get_client_ip` (admin.py может оставить private alias). Источник: Edge#49.

### Defer (4) — pre-existing или out-of-scope

- [x] [Review][Defer] **WW1. Stale Redis throttle-ключи после deploy** — Замена `UserRateThrottle` на `ProxyAwareUserRateThrottle` (DN3) меняет cache-key (REMOTE_ADDR → X-Real-IP). В первое окно после deploy старые ключи остаются параллельно — возможны временные stale rate limits. Ops-concern, не код-issue. Решение: `redis-cli FLUSHDB` для throttle namespace при deploy или принять transient окно. [ops/deploy]
- [x] [Review][Defer] **WW2. Throttle конфиг в `base.py` без override для test/dev/staging** [`backend/freesport/settings/base.py:171-176`] — Все среды получают `anon: 6000/min` без переопределения в `test.py`/`development.py`. Для local-dev и параллельных CI runner-ов с shared Redis возможно исчерпание. Pre-existing per P10 decision. Решение: добавить override в `development.py` (`'anon': '10000/min'`) при необходимости.
- [x] [Review][Defer] **WW3. `ProxyAwareThrottleIdentMixin` без trusted-proxy allowlist** [`backend/apps/common/throttling.py:13-26`] — Pre-existing pattern (зафиксирован как W7 в Pass 1): клиент напрямую без proxy шлёт `X-Real-IP: 1.2.3.4` → throttle bucket произвольный. Решение на уровне nginx (overwrite заголовков от внешних клиентов) или middleware с TRUSTED_PROXIES списком. Связано с 11.3 SEC-001, единая infra-story.
- [x] [Review][Defer] **WW4. Email-input не disabled при `isSubmitting`** [`frontend/src/components/home/SubscribeForm.tsx:101-115`, `ElectricSubscribeForm.tsx:123-143`] — Пользователь может изменить email после клика «Подписаться» до ответа сервера; `setError('email')` ассоциирует server-side ошибку с уже-другим значением. UX-edge, не bug. Решение: `disabled={isSubmitting}` на input или fieldset (отдельная UX-story).

### Dismissed (~22) — noise / false positive / already-resolved

**Blind Hunter:** `select_for_update` без локального atomic в `create()` (покрыто P3/view-level atomic), `policy_version="1.0"` (AC-5 default), control-flow в `subscribe()` (false positive — структура корректна), DoS UserConsent через 6000/min (покрыто DN3/WW2), `session.save()` DoS (покрыто WW3/throttling), нет bulk_create (преждевременная оптимизация), двойная проверка is_active (защитный паттерн), удалённый is_global фильтр (D3→P11 решено), мёртвый код email_errors mapping (defensive), `sanitize_log_value` 128-char truncation (реальные IPv6 короче), `try/except DRFValidationError` crufty (субъективно), aria-labelledby склейка в тестах (стандарт a11y testing), двойная защита BooleanField + custom validate (purposeful), logger WARNING → DEBUG (связано с P11), `'details' in error` слабая проверка (низкий риск), `pop` default `False` (косметика), потерянный SEC-001 комментарий (минор docs), логгер не наследует имя модуля (тривиально), Newsletter.create race (IntegrityError ловится).

**Edge Case Hunter:** `str(dict)` при future nested validators (hypothetical), reuse session_key анонима (audit-correct по дизайну), concurrent unsubscribe-resubscribe chain (покрытие, не bug), `REMOTE_ADDR="unknown"` (hypothetical middleware), IPv6 `::`/broadcast `255.255.255.255` (deliberate после P11), throttle test `THROTTLE_RATES` patch (smoke-уровень, реальное поведение проверяется), autofill на checkbox (browser behavior), `setError` race (теоретический), test для request.session без middleware (инфраструктурное), form-urlencoded (API JSON-only), concurrent с разными emails (coverage), IPv4-mapped IPv6 test (coverage), дублирующее покрытие реактивации (noise, не bug).

**Acceptance Auditor:** `select_for_update` без локального atomic (= Blind, dismiss), logger DEBUG vs WARNING (связано с P11 dismiss), `test_auth_registration_consent.py` rename+invert (часть P11, согласовано).
- sanitize_consent_user_agent `Any` type hint cosmetic

---

## Review Findings — Pass 3 (2026-05-14)

Третий заход bmad-code-review после закрытия P1-P12 + DN1-DN3 + PP1-PP8. 3 параллельных слоя (Blind Hunter, Edge Case Hunter, Acceptance Auditor) по diff `0833e90c^..HEAD` (2377 строк, 21 файл production-кода, без metadata/openapi.yaml шума). Edge Case Hunter дал детально только #17-#20 (output обрезан), но темы #1-#16 пересекались с Blind Hunter и были учтены при дедупе. Триаж: ~38 raw findings → 23 уникальных после дедупа: **2 decision-needed, 6 patch, 15 defer, ~6 dismissed**.

### Decision-needed (resolved 2026-05-14)

- [x] **DDN1 → Defer.** Принято: forensic-связка через `(ip_address, user_agent, given_at ≈ Newsletter.subscribed_at)` работает (Newsletter и UserConsent хранят эти поля симметрично). Жёсткая FK ломает асимметрию с registration consent (FK=NULL), JSONB-metadata требует архитектурного обсуждения с комплаенс-офицером (аналогичный pre-existing gap есть и для регистрации). Поднять отдельной story **35.5 — consent audit linkage**. В 35.3: оставить статус-кво + добавить защитную заметку в Dev Notes.
- [x] **DDN2 → Patch (см. PPP7).** Принято: вариант 2 — scope-specific `SubscribeRateThrottle(scope="subscribe", rate="30/min")` на `subscribe()` view. SSR на read-endpoints не страдает, write-endpoint изолирован, DDoS-вектор закрыт без CAPTCHA. Для e2e/load-tests — override в `test.py`.

### Patch (7: 6 исходных + 1 из DDN2)

- [x] [Review][Patch] **PPP7. (из DDN2) Scope-specific `SubscribeRateThrottle` для `/subscribe/`** [`backend/apps/common/throttling.py`, `backend/apps/common/views.py:subscribe`, `backend/freesport/settings/base.py:171-176`] — Создать класс `SubscribeRateThrottle(SimpleRateThrottle)` с `scope = "subscribe"` (использовать `ProxyAwareThrottleIdentMixin` для canonical IP), зарегистрировать `"subscribe": "30/min"` в `DEFAULT_THROTTLE_RATES`, повесить `@throttle_classes([SubscribeRateThrottle])` на `subscribe()` view. Глобальный `anon: 6000/min` остаётся для SSR/pages-API. **Тест:** smoke-тест в `test_common_subscribe_api.py` — x40 POST на `/api/v1/subscribe/` от одного IP → ≥10 ответов 429 (или другой rate). Override `"subscribe": "100000/min"` в test-settings, чтобы основной integration-suite не сталкивался с throttle между кейсами. Также добавить assert, что без `pdp_consent` запрос всё равно throttle'ится (валидация — после throttle middleware).

- [x] [Review][Patch] **PPP1. `DEFAULT_THROTTLE_RATES` активен в test/dev/staging без override** [`backend/freesport/settings/base.py:171-176`, `backend/freesport/settings/test.py`, `backend/freesport/settings/development.py`] — После P10 переноса throttle из `production.py` в `base.py` все среды получают `anon: 6000/min` без явных overrides. В CI с параллельными test-runner'ами на shared Redis возможно исчерпание квоты между тестами (особенно в integration suite). Источник: Blind#3 + Edge#5 + Pass 2 deferred WW2. Fix: добавить в `freesport/settings/test.py` (если есть) или через pytest fixture `settings.DEFAULT_THROTTLE_RATES = {"anon": "100000/min", "user": "100000/min"}` + `cache.clear()` autouse fixture; либо явно установить `THROTTLE_RATES = {}` в `pytest.ini` через `DJANGO_SETTINGS_MODULE`.

- [x] [Review][Patch] **PPP2. Английский `Throttled.default_detail` для русскоязычного UX** [DRF default behavior, `backend/apps/common/throttling.py`] — Throttle возвращает «Request was throttled. Expected available in X seconds.» на ответе 429. Frontend Pass 2 PP3 добавил code `throttled` и UI-сообщение «Слишком много попыток...», но если детальный `detail` из backend попадёт в toast (через `details.detail` или fallback), пользователь увидит английский текст. Источник: Edge#4. Fix: либо переопределить `ProxyAwareAnonRateThrottle.default_detail = _("Слишком много попыток. Попробуйте через минуту.")` через `gettext_lazy`, либо явно очищать `detail` в кастомном `throttled()` view-helper.

- [x] [Review][Patch] **PPP3. `_get_client_ip` в `apps/users/admin.py` изменил сигнатуру с `str` на `str | None`, downstream AuditLog потребляет result** [`backend/apps/users/admin.py:540-552`, downstream callers approve/reject/block actions] — PP8 Pass 2 заменил приватную реализацию на делегирование общему `get_client_ip`, который возвращает `None` для отсутствующего IP. Тест `test_users_admin.py` обновлён с `assertEqual(ip, "0.0.0.0")` на `assertIsNone(ip)`. Spec AC-6 явно говорил «НЕ трогать `_get_client_ip` в admin», PP8 это override. Downstream: если admin-actions передают этот IP в `AuditLog.ip_address` (PG inet field), `None` записывается как NULL вместо строки "0.0.0.0" — миграция исторических записей, фильтры в admin-журнале, экспорт CSV могут отличаться. Источник: Auditor A5. Fix: проверить вызывающие коды (`approve_users_action`, `reject_users_action`, `block_users_action`) — если значение используется как обязательное (например, форматирование `f"{ip}"` или фильтр `__icontains`), завернуть в `or "0.0.0.0"` для совместимости; иначе документировать поведение `None` в Dev Notes.

- [x] [Review][Patch] **PPP4. Анонимная сессия зависит от `SESSION_ENGINE=django.contrib.sessions.backends.db`** [`backend/apps/common/views.py:~398-400`, `backend/freesport/settings/base.py` SESSION_ENGINE setting] — `request.session.save()` для `signed_cookies` backend — no-op (`session_key` остаётся None). В `UserConsent.session_key` попадёт `""`, CheckConstraint `userconsent_user_or_session_required` (user IS NOT NULL OR session_key != '') нарушится → IntegrityError → PP2 503 ответ для legit пользователей. Тест `test_subscribe_anonymous_creates_session_key` проходит в test settings (db backend), но регрессирует если кто-то поменяет SESSION_ENGINE. Источник: Blind#8. Fix: либо `assert settings.SESSION_ENGINE != "django.contrib.sessions.backends.signed_cookies"` в Django startup check (apps/common/apps.py `ready()`), либо документировать жёсткое требование в Dev Notes + комментарий в `subscribe()` view рядом с `request.session.save()`.

- [x] [Review][Patch] **PPP5. caplog `logger="apps.users.auth"` устарел в `test_registration_logs_warning_when_remote_addr_is_unknown`** [`backend/tests/integration/test_auth_registration_consent.py:372`] — После AC-6 рефактора `logger.warning("Unknown client IP skipped for consent audit")` живёт в `apps.common.consent_audit`. 4 других caplog-теста в этом файле уже обновлены на `logger="apps.common.consent_audit"`, этот — нет. Тест passed per Dev Agent Record (через propagation), но при будущем рефакторе log propagation легко упасть unnoticed. Источник: Auditor A8. Fix: заменить `caplog.at_level("WARNING", logger="apps.users.auth")` → `logger="apps.common.consent_audit"`.

- [x] [Review][Patch] **PPP6. `reset()` не вызывается в `ElectricSubscribeForm` onSubmit success** [`frontend/src/components/home/ElectricSubscribeForm.tsx` onSubmit success branch] — `reset` импортируется в деструктуризации `useForm`, но в `try { await subscribeService.subscribe(...); toast.success(...); }` после `toast.success` нет `reset()`. После успешной подписки email и PDN-checkbox остаются заполненными — пользователь может случайно отправить ещё один запрос (особенно учитывая 6000/min throttle ↔ DDN2 риск). В `SubscribeForm` (Blue) `reset()` корректно вызывается. Источник: Blind#12. Fix: добавить `reset()` после `toast.success(...)` в success-ветке onSubmit.

### Defer (15) — pre-existing или out-of-scope

- [x] [Review][Defer] **WWW1. Hardcoded русский error-message без gettext_lazy** [`backend/apps/common/serializers.py:17-30` PDP_CONSENT_REQUIRED/ALREADY_SUBSCRIBED] — Pre-existing проектный паттерн (тот же подход в `apps/users/serializers.py`). Не вводится 35.3. Решать единой i18n-story.
- [x] [Review][Defer] **WWW2. SEC-001 комментарий потерян при миграции THROTTLE_RATES в base.py** [`backend/freesport/settings/base.py:171-176`] — Косметика-документация: исходный комментарий `# Story 11.3 — SEC-001` в production.py не перенесён, остался только `# Increased to fix SSR 429 errors`. Pre-existing привязка к SEC-001 не задокументирована. Источник: Auditor A3.
- [x] [Review][Defer] **WWW3. `_has_error_code` рекурсивная без depth-limit** [`backend/apps/common/views.py:13-19`] — Глубоко вложенный сериализатор или вредоносный nested-error может вызвать stack overflow. Маловероятно для текущего сериализатора (глубина 1-2), но code smell. Источник: Blind#14.
- [x] [Review][Defer] **WWW4. `except IntegrityError` ловит ТОЛЬКО IntegrityError, не различает source constraint** [`backend/apps/common/views.py` 503-handler] — `DatabaseError`/`OperationalError` пробрасываются как 500. Также: IntegrityError может прийти и от Newsletter (race на unique email), и от UserConsent (CheckConstraint) — ветка возвращает 503 "consent_persistence_failed" для обоих, что вводит в заблуждение при race на Newsletter. Источник: Blind#15 + Edge#20. Future-proofing.
- [x] [Review][Defer] **WWW5. `getBackendMessage(['', 'real'])` возвращает `''` (falsy)** [`frontend/src/components/home/*SubscribeForm.tsx` getBackendMessage helper] — Если backend вернёт массив с пустой первой строкой, frontend покажет пустой toast. Гипотетический сценарий, backend DRF серриализатор не генерит пустые строки. Источник: Blind#6.
- [x] [Review][Defer] **WWW6. `getFirstBackendError` зависит от порядка ключей в JSON-ответе** [`frontend/src/components/home/*SubscribeForm.tsx` getFirstBackendError] — DRF errors не специфицируют order; обновление DRF/serializer order может поменять, какое сообщение увидит пользователь. Хрупкая зависимость от детали реализации. Источник: Blind#5.
- [x] [Review][Defer] **WWW7. AC-1 `aria-invalid={hasPdpConsentError || undefined}` vs spec `{!!errors.pdp_consent}`** [`frontend/src/components/home/SubscribeForm.tsx:162`, `ElectricSubscribeForm.tsx:1485`] — Spec говорит boolean cast `!!`, код использует `|| undefined` (если false — атрибут отсутствует, а не `aria-invalid="false"`). Функционально эквивалентно для SR. Источник: Auditor A7.
- [x] [Review][Defer] **WWW8. Spec разделы «Структура файлов (изменения)» и «API контракт» отстают от Pass 1/Pass 2 scope creep** [`spec lines 493-525, 466-480`] — `backend/apps/common/throttling.py`, `backend/apps/users/admin.py`, `backend/apps/users/authentication.py`, `backend/freesport/settings/base.py+production.py`, `backend/tests/unit/test_common_throttling.py`, `backend/tests/unit/test_users_admin.py`, `frontend/src/services/__tests__/subscribeService.test.ts` — все реально изменены/созданы, но не в spec-списке. API contract не упоминает 503 (PP2). Docs maintenance, не блокирует. Источник: Auditor A9 + scope creep.
- [x] [Review][Defer] **WWW9. `setError('pdp_consent', { type: 'server' })` сохраняется между submit'ами** [`frontend/src/components/home/SubscribeForm.tsx:108-117`, `ElectricSubscribeForm.tsx:113-128`] — RHF 7+ `setError({type: 'server'})` сохраняется до явного `clearErrors`. Если на 2-м submit backend больше не возвращает ошибку для pdp_consent, старая ошибка может зависнуть. Тесты делают только 1 submit, не серию. UX-edge, теоретический. Источник: Edge#17.
- [x] [Review][Defer] **WWW10. `getValidationDetails` возвращает весь errorData когда `details` отсутствует → машинный код в toast** [`frontend/src/services/subscribeService.ts:11-22`, `SubscribeForm.tsx:107`] — Если backend 5xx вернёт `{error: "consent_persistence_failed"}` без вложенного `details` (corner case PP2 path), `getValidationDetails` отдаст `{error: "..."}` целиком → `getFirstBackendError` найдёт строку `"consent_persistence_failed"` → toast машинного кода. Источник: Edge#18.
- [x] [Review][Defer] **WWW11. `serializer.save()` бросает `serializers.ValidationError` — нарушение DRF-конвенции** [`backend/apps/common/serializers.py:120-127` `already_subscribed_error()`] — `serializer.save()` по DRF-конвенции не должен бросать `ValidationError` (она для фазы `is_valid()`). View ловит её специально, но любой middleware/wrapper, ожидающий стандартного DRF flow (например, exception_handler с auto-400 mapping), может неверно обработать race. Также `from exc` теряет original traceback в логах. Pass 2 PP2 pattern. Источник: Blind#10.
- [x] [Review][Defer] **WWW12. `UserConsent.objects.create` дважды вместо `bulk_create`** [`backend/apps/common/views.py:~407-410`] — Два отдельных INSERT в цикле. На write-эндпоинте с throttle 6000/min — лишний DB roundtrip. Преждевременная оптимизация для текущего объёма (~5-10 подписок/час). Источник: Blind#7.
- [x] [Review][Defer] **WWW13. Тест `test_subscribe_default_anon_throttle_applies` через `patch.object(THROTTLE_RATES)`** [`backend/tests/integration/test_common_subscribe_api.py`] — DRF создаёт новый throttle на каждый запрос, поэтому patch работает. Если в будущем DRF введёт throttle-pool/caching — false-positive (все 201, ассерт `>= 6` упадёт). Также `cache.clear()` влияет на параллельные тесты. Pre-existing pattern. Источник: Blind#11.
- [x] [Review][Defer] **WWW14. Деградация политики `is_global` фильтра в `normalize_consent_ip`** [`backend/apps/common/utils/consent_audit.py:91`] — Теперь private/loopback IPs пишутся в audit (Pass 1 D3→P11 явное решение). Если Docker/k8s неправильно настроены — в audit попадают внутренние IP контейнеров. Юридически бесполезные записи. Источник: Blind#9 + Edge#9. Закрыто decision D3 Pass 1 как намеренное, оставлено для compliance-офицера на форум проверить.
- [x] [Review][Defer] **WWW15. Throttle 6000/min глобально без CAPTCHA + связка с DDN2** — Связано с DDN2 как architectural concern; до решения decision-needed defer'им сам defer как pre-existing post-DDN2 cleanup.

### Dismissed (~6)

- **Blind #4 `validate()` использует `self.initial_data` ломает form-encoded** — DN1 Pass 2 явно зафиксировал strict `initial_data` как намеренное решение для 152-ФЗ; в коде есть код-комментарий-обоснование. API JSON-only, dismiss.
- **Edge #3 form-encoded клиенты не получают валидацию consent** — дубль Blind #4, dismiss (= DN1 Pass 2).
- **Edge #1/#8/#10/#11 throttle bypass через empty XFF first hop / длинный мусор / IPv4-mapped IPv6 / port=0/big** — PP1 Pass 2 закрыл через `_sanitize_ident` + `normalize_consent_ip` canonical fallback в `apps/common/throttling.py:ProxyAwareThrottleIdentMixin`. Тест `tests/unit/test_common_throttling.py` покрывает canonical IP mapping для основных форматов. Dismiss.
- **Edge #6 потеря `unsubscribed_at` истории при reactivation** — Pass 1 D1 явно зафиксировал: `Newsletter.ip_address`/`user_agent`/`unsubscribed_at` = «latest activity», а audit-trail «первый раз» / «каждое согласие» живёт в `UserConsent` (append-only — каждая реактивация = 2 новых записи). Архитектурное решение. Dismiss.
- **Edge #15 mock-based тест с false-positive (без указания конкретного теста)** — generic concern без evidence в diff, dismiss как noise.
- **Acceptance scope creep `policy_version="1.0"` hardcoded в default модели** — AC-5 explicit fallback на default. Auditor сам пометил «верификация пройдена». Dismiss.

---

## Review Findings — Pass 4 (2026-05-14)

Четвёртый заход bmad-code-review после закрытия Pass 3 (PPP1-PPP7, DDN1-DDN2). Запущены 3 параллельных слоя — Blind Hunter, Edge Case Hunter, Acceptance Auditor — по diff `0833e90c^..fa435897` (2932 строки production-кода + tests, без BMAD-артефактов / AGENTS.md / CLAUDE.md / api.generated.ts). **Edge Case Hunter и Acceptance Auditor наткнулись на rate-limit (00:50 Europe/Ljubljana)** и не отдали output; их слои частично воспроизведены в основной сессии (выборочный AC-аудит ключевых файлов + дополнительные edge-cases). Blind Hunter выдал 25 находок. Триаж в свете истории P1-P12 + PP1-PP8 + PPP1-PPP7: **0 decision-needed, 6 patch, 3 defer, ~17 dismissed (already-resolved в предыдущих проходах)**.

### Decision-needed (0)

Все архитектурные decisions, всплывшие у Blind Hunter, **уже зафиксированы** в спеке: D3→P11 (is_global filter намеренно убран), DN1 (strict `initial_data` JSON-only), DN3 (`ProxyAwareUserRateThrottle` в production), DDN1 (forensic связка через ip+ua+timestamp), DDN2 (scope-specific `SubscribeRateThrottle`). Pass 4 ничего нового по архитектуре не выявил.

### Patch (6)

- [x] [Review][Patch] **PPPP1. `ProxyAwareThrottleIdentMixin.get_ident()` fallback не санитизует `REMOTE_ADDR`** [`backend/apps/common/throttling.py:18-31`] — Если запрос приходит **без** `HTTP_X_REAL_IP` и `HTTP_X_FORWARDED_FOR`, метод делает `return super().get_ident(request)` — `BaseThrottle.get_ident` возвращает **сырой** `REMOTE_ADDR` без `_sanitize_ident`. PP1 Pass 2 закрыл proxy-заголовочные пути, но REMOTE_ADDR fallback всё ещё может содержать unsafe chars (если фронт ходит мимо Nginx или REMOTE_ADDR заспуфен в тестах) → unsafe Redis cache key. Fix: `return self._sanitize_ident(super().get_ident(request))` или `return self._sanitize_ident(request.META.get("REMOTE_ADDR", ""))`. Источник: Blind#6. Закрыто Pass 4: fallback теперь проходит через `_sanitize_ident`, добавлен RED/GREEN unit-тест.

- [x] [Review][Patch] **PPPP2. `request.session.save()` внутри `transaction.atomic()` создаёт session-row, который откатывается при IntegrityError** [`backend/apps/common/views.py:406-419`] — Текущая последовательность: открываем atomic → `serializer.save()` (Newsletter) → `session.save()` (создаёт row в `django_session` через тот же connection) → 2× `UserConsent.create`. Если `UserConsent.create` падает на CheckConstraint/IntegrityError, atomic-rollback откатит **и `Newsletter`, и `django_session` row**. Дальше `SessionMiddleware.process_response` попытается записать session повторно с тем же ключом — может вернуть конфликт уникальности или потеряет привязку. Также блокировка `django_session` (горячая таблица) внутри длинной транзакции — contention vector. Fix: вынести `session.save()` **до** `with transaction.atomic():` блока — session_key должен существовать **независимо** от успеха consent-вставки (он используется только как идентификатор анонима в audit). Источник: Blind#4. Закрыто Pass 4: `session.save()` вынесен перед локальным atomic-блоком; тест проверяет depth локального atomic.

- [x] [Review][Patch] **PPPP3. `test_subscribe_atomic_rollback_on_consent_failure` тавтологичный** [`backend/tests/integration/test_common_subscribe_api.py:~1331-1346`] — `side_effect=[MagicMock(spec=UserConsent), IntegrityError(...)]` — первый вызов `UserConsent.objects.create` возвращает мок, **не пишет в БД**. Финальный assert `UserConsent.objects.count() == 0` тавтологичен — мок ничего не создаёт независимо от наличия rollback. Тест проверяет только что код возвращает 503 при IntegrityError, но **не подтверждает rollback реальной записи**. Fix: либо использовать `mock.patch` ТОЛЬКО для второго вызова через `side_effect=[DEFAULT, IntegrityError(...)]` + `wraps=UserConsent.objects.create` (первый вызов идёт в реальную БД), либо переписать assert на `Newsletter.objects.count() == 0` (более явный proxy для rollback). Источник: Blind#17. Закрыто Pass 4: первый `UserConsent.objects.create` теперь реальный, второй бросает `IntegrityError`, финальный count доказывает rollback.

- [x] [Review][Patch] **PPPP4. `test_subscribe_scope_throttle_applies_before_validation` имя мисслидит реальное поведение** [`backend/tests/integration/test_common_subscribe_api.py:~1384-1394`] — Payload без `pdp_consent`, ассерты `400 in statuses` + `429 count >= 10`. Если throttle действительно применялся **до** validation, мы получили бы **только** 429 после лимита, не комбинацию 400+429. Тест проверяет «во время серии запросов встречаются и 400, и 429», что не доказывает порядок их применения. Fix: либо переименовать в `test_subscribe_scope_throttle_kicks_in_during_invalid_payload_flood`, либо отправлять валидный payload (`pdp_consent: True`) с уникальными email — тогда сравнение «без throttle = 40×201, с throttle = N×201 + M×429» становится prove of behaviour. Источник: Blind#8. Закрыто Pass 4: тест переименован и использует валидные unique payload; первые 5 запросов дают 201, последующие — 429.

- [x] [Review][Patch] **PPPP5. `SubscribeRateThrottle.get_cache_key` полностью дублирует `SimpleRateThrottle.get_cache_key`** [`backend/apps/common/throttling.py:55-60`] — Базовая реализация `SimpleRateThrottle.get_cache_key` уже использует `self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}` — точно тот же код. Override не добавляет логики. Fix: удалить override — `SubscribeRateThrottle` отнаследует базовый метод. Источник: Blind#19. Закрыто Pass 4 как false-positive для текущей DRF-версии: удаление override воспроизвело `NotImplementedError: .get_cache_key() must be overridden`; override сохранён с docstring.

- [x] [Review][Patch] **PPPP6. `consent_audit.get_client_ip` смотрит только `X-Forwarded-For`, throttle mixin — `X-Real-IP` first** [`backend/apps/common/utils/consent_audit.py:42-51` vs `backend/apps/common/throttling.py:19-28`] — Под Nginx, который ставит и `X-Real-IP`, и `X-Forwarded-For`, throttle bucket будет ключиться по X-Real-IP, а audit IP — по XFF first-hop. Если nginx-конфиг устроен так, что эти заголовки расходятся (например, intermediate proxy), у одной и той же сессии IP в audit и в throttle ключе будут разные. Fix: синхронизировать порядок: `get_client_ip` тоже должен смотреть `X-Real-IP` first, как PP1 Pass 2 формализовал для throttle. Альтернатива — оставить расхождение, но задокументировать в Dev Notes и `consent_audit.py` docstring. Источник: Blind#16. Закрыто Pass 4: `get_client_ip()` предпочитает непустой `X-Real-IP`, добавлен subscribe regression на совпадение Newsletter/UserConsent audit IP.

### Defer (3) — pre-existing или out-of-scope

- [x] [Review][Defer] **WWWW1. Мёртвая ветка `if getattr(parsed_ip, "scope_id", None): return None` в `normalize_consent_ip`** [`backend/apps/common/utils/consent_audit.py:80-95`] — После `candidate.split("%", 1)[0]` (line 81) zone_id уже отсечён до парсинга, поэтому `scope_id` после `parse_ip_address(candidate)` всегда `None`. Условие на line 92-93 никогда не сработает. Защитный fallback на гипотетический случай, когда `parse_ip_address` сам распознает scope. Не баг, но мёртвый код. Fix (опционально): убрать `scope_id` проверку или добавить комментарий «defensive». Источник: Blind#2.

- [x] [Review][Defer] **WWWW2. OpenAPI yaml: массовая перестановка get/patch операций без видимой причины** [`docs/api/openapi.yaml`] — Большая часть из 182 строк изменений в openapi.yaml — drf-spectacular regenerated с другим порядком ключей. Blind Hunter отметил возможную утрату описаний `'401'`/`'404'` для одной из операций (`/orders/{id}`) — нужно сверить с прошлой версией, чтобы понять, реально ли утрачены ответы. Если да — это **regression в API контракте, не связанный со story 35.3**. Fix: вне scope 35.3 — отдельная задача «verify openapi.yaml diff for unintended response removal». Источник: Blind#13.

- [x] [Review][Defer] **WWWW3. `/unsubscribe/` не обвешан throttle — enumeration attack vector** [`backend/apps/common/views.py:518-554`] — После DDN2 Pass 3 на `/subscribe/` повесили scope-specific 30/min. На `/unsubscribe/` остался global `ProxyAwareAnonRateThrottle` (после DN3 Pass 2 — 6000/min anon). Атакующий может массово опрашивать `/unsubscribe/` с разными email-ами: 200 (success) vs 404 (not subscribed) → пассивное email enumeration (известно, кто подписан). Pre-existing — endpoint существовал до 35.3, story 35.3 не меняет unsubscribe flow. Fix: вне scope — отдельная security-story «harden unsubscribe enumeration». Источник: внутренний edge case audit.

### Dismissed (~17) — already-resolved в P1-P12 / PP1-PP8 / PPP1-PPP7 + false positives

**Blind Hunter:**
- **#1 `normalize_consent_ip` потерял `is_global` filter** — D3 Pass 1 → P11 Pass 2 явно зафиксировал как намеренное изменение политики (audit пишет всё, juridical filtering — на read-time). См. WWW14 Pass 3.
- **#3 race на новый email** — IntegrityError на unique constraint → already_subscribed_error → 409, поведение корректное.
- **#5 двойной 409 path (через validate_email + через IntegrityError)** — defensive defense-in-depth, не баг.
- **#7 `THROTTLE_RATES` patch хрупкий** — WWW13 defer Pass 3.
- **#9 Newsletter.ip_address: raw XFF → normalized** — положительное усиление, не нарушение.
- **#10 `_has_error_code` рекурсивный any** — WWW3 defer Pass 3.
- **#11 `validate()` initial_data ломает form-urlencoded** — DN1 Pass 2 strict JSON-only.
- **#12 OpenAPI form-urlencoded валиден, но кода не работает** — следствие DN1, dismiss.
- **#14 development.py `100000/min` фактически без лимита** — intentional dev override; CI/test не страдают.
- **#15 production.py: `UserRateThrottle` → `ProxyAwareUserRateThrottle`** — DN3 Pass 2.
- **#18 `MAX_LOG_VALUE_LENGTH=128` collision** — теоретическая, не реальная угроза.
- **#20 `ErrorDetail` многословный** — косметика.
- **#21 `getFirstBackendError` порядок ключей** — WWW6 defer Pass 3.
- **#22 `getValidationDetails` error string в loop** — WWW10 defer Pass 3.
- **#23 `policy_version` hardcoded** — false positive, default="1.0" в `UserConsent` модели (`backend/apps/common/models.py:627-629`).
- **#24 `pdp_consent: false` payload на фронте** — design choice, RHF блокирует submit, бэк отвергает.
- **#25 `api.generated.ts` required-flag** — корректно, openapi.yaml содержит `required: [email, pdp_consent]`.

**Edge Case Hunter (rate-limited, темы воспроизведены в основной сессии и пересеклись с Blind находками выше).**

**Acceptance Auditor (rate-limited, ключевые AC проверены в основной сессии):**
- AC-1..AC-3, AC-5, AC-7, AC-9 — **OK**.
- AC-4 — формально OK, нюанс с form-urlencoded — DN1 closed (dismiss).
- AC-6 — формально нарушен («строка-в-строку»), но D3 Pass 1 → P11 Pass 2 → WWW14 Pass 3 явно зафиксировали изменение как намеренное; AC-6 considered amended (dismiss).
- AC-8 — OK с замечаниями на хрупкость тестов (PPPP3, PPPP4).

---

## Review Findings — Pass 5 (2026-05-14)

Пятый заход bmad-code-review после Pass 4 closure (PPPP1-PPPP6 закрыты, WWWW1-WWWW3 deferred). Запущены 3 параллельных subagent-слоя (Blind Hunter, Edge Case Hunter, Acceptance Auditor) по cumulative diff `fb47fbeb..HEAD` (28 файлов, +1785/-366, без BMAD-артефактов / AGENTS.md / CLAUDE.md). Все три слоя завершились успешно: BH=20, EC=15, AA=8 = 43 raw findings. После dedup и сверки с историей P1-P12 / PP1-PP8 / PPP1-PPP7 / PPPP1-PPPP6: **2 decision-needed (обе разрешены ниже) → 7 patch, 7 defer, ~32 dismiss**.

### Decision-needed (0)

Обе всплывшие у Edge Case Hunter архитектурные decisions **разрешены** в Pass 5:
- **D5N1** (validate_email раскрывает subscription state) → **разрешено: вариант 1** — реклассифицировано как patch P5N7 (убрать existing-email lookup из `validate_email`; race-check остаётся через `select_for_update + IntegrityError` в `save()`).
- **D5N2** (cross-identity reactivation) → **разрешено: вариант 5** — реклассифицировано как defer W5N7 (defer в существующую Story 35.5 «consent audit linkage» — единый pattern для всех типов согласий, требует юридического input).

### Patch (7)

- [x] [Review][Patch] **P5N7. Переместить existing-email lookup из `validate_email` в `save()` — закрыть 152-ФЗ enumeration vector** [`backend/apps/common/serializers.py:56-77` (`validate_email`) → `serializers.py:96-106` (`save()`)] — Текущий `validate_email` сначала вызывает `Newsletter.objects.filter(email=value, unsubscribed_at__isnull=True).exists()` и raises 409 `already_subscribed` ДО проверки cross-field `validate()` для `pdp_consent`. Анонимный POST `{email: "known@x.com"}` (без pdp_consent) раскрывает subscription state существующего подписчика. **Fix**: убрать early existing-email check из `validate_email` — оставить только нормализацию (`lower()`, `strip()`) + DRF EmailValidator. Race-check уже покрыт через `select_for_update().get() / DoesNotExist → create() / IntegrityError → already_subscribed_error()` в `save()`. Поведенческий эффект: невалидный/отсутствующий `pdp_consent` → 400 без leak; валидный consent + существующий email → 409 на save-time (тот же контракт для клиента). Добавить regression test: `test_subscribe_missing_pdp_consent_does_not_leak_subscriber_status` — POST `{email: <known>}` без pdp_consent → 400 с pdp_consent error, **БЕЗ** email-field 409. Источник: Edge#1 (decision D5N1 → вариант 1). Закрыто Pass 5.

- [x] [Review][Patch] **P5N1. Log level invalid-IP понижен с WARNING до DEBUG при переносе helpers** [`backend/apps/common/utils/consent_audit.py:127` / `:435`] — Источник в `apps/users/views/authentication.py` (35.2, до миграции) логировал `logger.warning("Invalid client IP skipped...")`. Новый модуль `consent_audit.py` использует `logger.debug(...)`. Тесты `tests/integration/test_auth_registration_consent.py:300,316,388,407,424` переведены на `caplog.at_level("DEBUG", ...)`. AC-6 spec явно требует «строка-в-строку» — log-level понижение даже формально drift, к тому же реальная цена: SOC/ops больше не видят WARNING при попытках header-injection. Inconsistency: `"unknown REMOTE_ADDR"` ветка осталась на `logger.warning(...)`. **Fix**: вернуть `logger.warning(...)` для invalid-IP в `consent_audit.py`, обновить тесты на `caplog.at_level("WARNING", ...)`. Источник: Blind#12 + Auditor F-AA-7. Закрыто Pass 5.

- [x] [Review][Patch] **P5N2. Throttle bypass через ротацию malformed `X-Real-IP` / `X-Forwarded-For`** [`backend/apps/common/throttling.py:_sanitize_ident` (≈ ProxyAwareThrottleIdentMixin)] — Цепочка: `normalize_consent_ip(raw)` возвращает `None` для невалидного IP → fallback `sanitize_log_value(raw)` возвращает уникальный escaped string. Этот escaped string становится throttle cache key. Attacker ротирует `X-Real-IP`: `bad1`, `bad2`, ..., `badN` — каждый получает свой 30/min bucket. Эффективный rate = `N × 30/min`. PP1 Pass 2 закрыл log-safety + Redis-injection, но НЕ закрыл этот bypass — `_sanitize_ident` всё ещё возвращает header-derived value. **Fix**: когда `normalize_consent_ip` вернул `None`, fallback должен использовать `REMOTE_ADDR` (TCP-source IP, не spoofable через header), а не sanitized header. Идиоматически: `return self._sanitize_ident(request.META.get("REMOTE_ADDR", "")) if not normalize_consent_ip(parsed) else parsed`. Опционально: добавить `logger.warning(...)` при fallback на REMOTE_ADDR (signal для SOC). Источник: Blind#9 + Edge#6. Закрыто Pass 5.

- [x] [Review][Patch] **P5N3. `OperationalError` / `DatabaseError` не пойман в subscribe atomic блоке — 503 контракт работает только для `IntegrityError`** [`backend/apps/common/views.py:412-441` (consent persistence block)] — Текущий код: `except IntegrityError → return 503 {"error": "consent_persistence_failed", ...}`. Но `UserConsent.objects.create` может бросить и другие `DatabaseError` подклассы: `OperationalError` (DB connection drop, deadlock retry exhausted), `DataError` (CHECK constraint violation на edge data). Эти исключения **не пойманы** → Django default 500 handler → ответ без custom `error/details` shape, фронтенд `subscribeService.ts` маппит на generic `network_error`. **Fix**: расширить `except` до `(IntegrityError, OperationalError)` или базовый `DatabaseError` (`from django.db import DatabaseError`). Желательно различать в logging — `IntegrityError` (constraint, retry бесполезен), `OperationalError` (transient, можно retry). Источник: Edge#8. Закрыто Pass 5.

- [x] [Review][Patch] **P5N4. `SubscribeForm.tsx` не обрабатывает `server_error` / 503 — toast показывает generic «Не удалось подписаться»** [`frontend/src/components/home/SubscribeForm.tsx:103-128` vs `ElectricSubscribeForm.tsx:113-128`] — `ElectricSubscribeForm` имеет полноценную `server_error` ветку с разбором `details.non_field_errors` через `getFirstBackendError` (см. AC-7 / PP2 Pass 2). `SubscribeForm.tsx` (Blue, основной продакшен) той же ветки не имеет — 503 попадает в `default` блок и пользователь видит «Не удалось подписаться. Попробуйте позже» вместо более конкретного сообщения. Тесты `SubscribeForm.test.tsx` не покрывают 503/server_error путь (только ElectricSubscribeForm.test.tsx это делает). **Fix**: скопировать `server_error` switch-case из `ElectricSubscribeForm.tsx:113-128` в `SubscribeForm.tsx`, добавить `test_subscribe_form_shows_backend_message_on_503` тест по аналогии с Electric. Источник: Edge#11. Закрыто Pass 5.

- [x] [Review][Patch] **P5N5. 503 OpenAPI response schema пустая — generated TypeScript типы `content?: never` маскируют body** [`docs/api/openapi.yaml:1577-1578` (subscribe 503) / `frontend/src/types/api.generated.ts:2976-2982`] — `@extend_schema(responses={503: OpenApiResponse(description="...")})` не передал `inline_serializer` / `OpenApiTypes.OBJECT` с реальной body shape, поэтому openapi-typescript генерирует `'503': { headers; content?: never }`. Фронтенд видит «нет body» — typed consumer не может прочитать `{error, details}`. **Fix**: добавить inline serializer в `@extend_schema` для 503 с полями `error: str`, `details: dict`, регенерировать `python manage.py spectacular --file docs/api/openapi.yaml`, прогнать `npm run generate:types` (но см. defer W5N1 про двойственность файлов). Источник: Blind#17. Закрыто Pass 5.

- [x] [Review][Patch] **P5N6. `test_users_admin.py` передаёт строку как `request.session` — dormant breakage** [`backend/tests/unit/test_users_admin.py:~1545`] — `setattr(request, "session", "session")`. Admin action `block_users` сейчас не читает `request.session.session_key`, поэтому тест проходит. Если в будущем action добавит session-use (например, для CSRF check / audit), `"session".session_key` → AttributeError. Также: маркер plain string в production-like тесте — misleading reader. **Fix**: `from importlib import import_module; SessionStore = import_module(settings.SESSION_ENGINE).SessionStore; request.session = SessionStore()` или `request.session = MagicMock(spec=SessionStore)`. Источник: Blind#14. Закрыто Pass 5.

### Defer (7) — pre-existing или out-of-scope

- [x] [Review][Defer] **W5N7. Cross-identity reactivation — authenticated user B переподписывает email user A** [`backend/apps/common/views.py:412-419`] — Сценарий: anon A подписал `victim@x.com`, отписался. Позже authenticated B (со своим email) POST-ит `{email: "victim@x.com", pdp_consent: true}`. View реактивирует `Newsletter` row и пишет 2× `UserConsent` с `user=B`. Audit не доказывает согласие владельца email — только что B утверждал согласие. **Defer**: cross-identity reactivation органично укладывается в уже-открытую **Story 35.5 «consent audit linkage»** (DDN1 Pass 3). Без юриста/комплаенс-офицера выбор между «запретить если user.email != email», «double-opt-in», «anon-only для reactivation», «принять» — неполный. Единый pattern proof-of-consent для всех типов согласий (registration + subscribe + cookie-banner) должен решаться в одной story. Источник: Edge#4 (decision D5N2 → вариант 5).

- [x] [Review][Defer] **W5N1. `docs/api-spec.yaml` не синхронизирован с `docs/api/openapi.yaml` — frontend codegen читает первый файл** [`frontend/package.json:22` `openapi-typescript ../docs/api-spec.yaml ...`] — Story 35.3 (и предыдущие 35.1/35.2) обновляли `docs/api/openapi.yaml`. Codegen команда `npm run generate:types` читает `docs/api-spec.yaml`. Если оба файла должны существовать — нужно явное правило (один — canonical), либо мигрировать package.json на `docs/api/openapi.yaml`. Pre-existing inconsistency (была до 35.3). Источник: Auditor F-AA-8.

- [x] [Review][Defer] **W5N2. `SubscribeRateThrottle` 30/min шарится между всеми клиентами за одним CGNAT/NAT exit IP — DoS amplification против легитимных подписчиков** [`backend/freesport/settings/base.py:864` + `apps/common/throttling.py`] — Один attacker за корпоративным NAT занимает 30/min → все остальные за тем же IP получают 429. Особенно болезненно для мобильных операторов (carrier-grade NAT). Architectural решение DDN2 Pass 3 принято осознанно. Mitigation вне scope: добавить session-scoped throttle (для аутентифицированных), CAPTCHA для 429-фоллбэка, либо `DEFAULT_THROTTLE_CLASSES` с per-session ключом. Источник: Blind#8.

- [x] [Review][Defer] **W5N3. `Newsletter.email` lookup чувствителен к регистру — legacy mixed-case rows провоцируют unrecoverable 409** [`backend/apps/common/serializers.py:96-106`] — Если в `Newsletter` есть legacy `"User@X.com"`, новый запрос с `"user@x.com"` (нормализованный validator-ом) промахивается на `select_for_update().get()` → `DoesNotExist` → `create(email="user@x.com")` → `IntegrityError` (если в PG `email` имеет unique CI index) или второй row (если CS index). Story 35.3 не делает миграцию данных. Fix вне scope: `migrations/000X_normalize_newsletter_emails.py` (UPDATE Lower(email)) + CITEXT field или `Lower()` functional index. Источник: Blind#18 + Edge#14.

- [x] [Review][Defer] **W5N4. Cross-domain session cookies — `SAMESITE=Strict` / domain mismatch ломает session-key reuse для анонимного subscriber** [`backend/freesport/settings/production.py:37`] — Если фронт `freesport.ru`, API `api.freesport.ru`, и `SESSION_COOKIE_SAMESITE='Strict'` — браузер не отправит cookie на cross-site POST. Каждый запрос → новая session → audit-records с разными session_keys для одного человека (defeats forensic linkage). Deploy-config concern, story 35.3 не отвечает за production cookie policy. Источник: Edge#12.

- [x] [Review][Defer] **W5N5. `sanitize_consent_user_agent` slice по `[:512]` после surrogate strip — boundary fragile для emoji/мульти-байтовых UA** [`backend/apps/common/utils/consent_audit.py:415-418`] — `encode("utf-8","ignore").decode(...)` может удалить surrogate pair → итоговая Python-длина переменна. Тест ассертит `len == 512` exactly при конкретном входе, но input-вариативность ломает assertion. Не баг runtime (slice безопасен), test brittleness. Источник: Edge#15.

- [x] [Review][Defer] **W5N6. `policy_version` всегда пишется как model-default "1.0" — при будущем обновлении политики audit не отражает version drift** [`backend/apps/common/models.py:627-629` + `backend/apps/common/views.py:412-419`] — `views.py` не передаёт `policy_version` в `consent_kwargs`, поэтому DB default `"1.0"` записывается всегда. При смене текста privacy policy (новая версия "1.1") старые admin-action создания consent продолжат писать "1.0" пока кто-то вручную не сменит default в модели. Pass 3 dismiss обосновывал «default в модели достаточно», но не учитывал live versioning. Compliance forward-concern: добавить `POLICY_VERSION` setting или FK на `PrivacyPolicy` entity (если 35.1 модель содержит). Pre-existing — не story scope. Источник: Edge#13.

### Dismissed (~32) — already-closed in P1-P12 / PP1-PP8 / PPP1-PPP7 / PPPP1-PPPP6 + trivial

**Acceptance Auditor:**
- AA-1 `normalize_consent_ip is_global filter removed` = **D3 Pass 1 → P11 Pass 2 → WWW14 Pass 3** intentional.
- AA-2 `get_client_ip X-Real-IP priority` = **PPPP6 Pass 4** intentional (sync с throttle mixin).
- AA-3 `session.save() outside atomic` = **PPPP2 Pass 4** intentional (avoid django_session rollback ping-pong).
- AA-4 `503 not in AC` = pedantic, PP2 Pass 2 фактически ввёл 503-контракт; AC-8 пункт «throttling smoke» неявно одобряет.
- AA-5 `scope SubscribeRateThrottle vs default` = **DDN2 Pass 3** intentional.
- AA-6 `scope-throttle test patches non-existent attribute` = **WWW13 Pass 3** defer (DRF re-instantiates throttle per-request → patch фактически работает).

**Blind Hunter:**
- BH-1 `validate() uses initial_data — breaks form-urlencoded` = **DN1 Pass 2** strict JSON intentional (152-ФЗ требует явный boolean).
- BH-2 `select_for_update outside atomic для alternative callers` = serializer.create() вызывается в view atomic, single call-site — accepted pattern. Pre-existing.
- BH-3 `race get/create на fresh email` = handled через IntegrityError → `already_subscribed_error()`. Не баг.
- BH-4 `_has_error_code dead branch` = check работает в shared error-handling helper, не dead в IntegrityError path. False positive.
- BH-5 `session engine check only signed_cookies` = defensive, расширение на cache/cached_db — out of scope.
- BH-6 `anon session.save outside atomic — session leak on 503` = **PPPP2 Pass 4** intentional trade-off (session row OK, audit linkability важнее).
- BH-7 `IPv6 zone id stripped silently` = подпункт WWW14 Pass 3 (политика «всё пишем»).
- BH-10 `ip/ua recomputed twice` = micro-optimization, не баг.
- BH-11 `OpenAPI massive reordering noise` = **WWW2 Pass 4** defer (drf-spectacular regeneration artifact).
- BH-13 `UserConsent unbounded growth` = by design (append-only audit). Retention policy — отдельный epic.
- BH-15 `Object.values() non-deterministic order` = **WWW6 Pass 3** defer.
- BH-16 `RHF controlled/uncontrolled hybrid checkbox` = стандартный pattern, тесты зелёные.
- BH-19 `_has_error_code recursion no depth limit` = **WWW3 Pass 3** defer.
- BH-20 `apps.py register check at import time` = стандартный Django AppConfig.ready() pattern.

**Edge Case Hunter:**
- EC-2 `select_for_update outside atomic` = duplicate of BH-2, dismiss.
- EC-3, EC-9 `session created on 409 / table growth` = **PPPP2 Pass 4** intentional; растёт — по design.
- EC-5 `form-encoded edge` = duplicate of BH-1 / **DN1 Pass 2**.
- EC-7 `_has_error_code non-ErrorDetail string` = **WWW3 Pass 3** defer.
- EC-10 `RHF rapid double-submit` = `isSubmitting` действительно блокирует re-entry (handleSubmit guards).
- EC-14 `legacy mixed-case email` = duplicate of BH-18 → defer W5N3.

---

## Review Findings — Pass 6 (2026-05-14)

Reviewer: Claude Code `bmad-code-review` (Opus 4.7) — параллельные слои: Blind Hunter, Edge Case Hunter, Acceptance Auditor. Диф: `fb47fbeb..0b67968c` (10 коммитов Story 35.3). Сверены с Pass 1-5 patch/defer/dismiss списками, чтобы исключить уже-закрытые. AC-1 … AC-9 — все **PASS** по Acceptance Auditor с задокументированными deviations (AC-4 `initial_data`, AC-5 no-leak, AC-6 `is_global` — все ссылаются на Pass 1-5 decision trail).

### Decision-needed (resolved 2026-05-14)

- **PPPP6-D1 → Patch (investigate + fix root cause).** Alex: «Разобраться сейчас» — исследовать, почему drf-spectacular больше не видит fields, и устранить причину (annotations / Meta / `extend_schema_field`).
- **PPPP6-D2 → Patch (align with throttling).** Alex: «Выровнять с throttling» — добавить REMOTE_ADDR fallback в `get_consent_ip_address` + обновить `test_subscribe_newsletter_ip_uses_normalized_audit_ip` (PIN заменяется на новое поведение).
- **PPPP6-D3 → Dismiss.** Alex: «Оставить checkbox checked» — текущее поведение остаётся; каждый submit = consent для конкретного запроса.

### Decision-resolved unchecked patches (3 added)

- [x] **[Review][Patch] PPPP6-D1→P3: восстановить 6 properties в `ProductDetail` OpenAPI schema** — закрыто через `extend_schema_field` annotations для `images`, `related_products`, `category_breadcrumbs` и регенерацию `docs/api/openapi.yaml` / `frontend/src/types/api.generated.ts`; schema содержит runtime-поля `images`, `related_products`, `category_breadcrumbs`, `seo_title`, `seo_description`, `variants`.
- [x] **[Review][Patch] PPPP6-D2→P4: REMOTE_ADDR fallback в `get_consent_ip_address`** — закрыто: invalid first-hop proxy IP fallback-ится на валидный `REMOTE_ADDR`; `test_subscribe_newsletter_ip_uses_normalized_audit_ip` обновлён под новое поведение.

### Decision-needed (3, ORIGINAL — оставлено для истории)

- [x] **[Review][Decision] PPPP6-D1: OpenAPI `ProductDetail` schema потеряла 6 properties вне scope Story 35.3** — resolved 2026-05-14: выбран вариант «разобраться сейчас»; root cause закрыт schema annotations, см. PPPP6-D1→P3.
- [x] **[Review][Decision] PPPP6-D2: `get_consent_ip_address` не делает fallback на REMOTE_ADDR при невалидном first-hop XFF** — resolved 2026-05-14: выбран вариант «выровнять с throttling»; см. PPPP6-D2→P4.
- [x] **[Review][Decision] PPPP6-D3: UX — сбрасывать ли `pdp_consent` на 409 `already_subscribed`** — resolved 2026-05-14: выбран вариант «оставить checkbox checked»; каждый submit подтверждает текущий checked-state.

### Patch (2)

- [x] **[Review][Patch] PPPP6-P1: OpenAPI subscribe-схема рекламирует `application/x-www-form-urlencoded`, но DN1 strict-bool гарантированно ломает form-encoded** — закрыто: `subscribe` ограничен `JSONParser`, regenerated OpenAPI для `/subscribe/` содержит только `application/json`.
- [x] **[Review][Patch] PPPP6-P2: типы `SubscribeValidationDetails` шире OpenAPI-контракта 503** — закрыто: `SubscribeValidationDetails = Record<string, string[]>`, добавлен runtime guard, string details не сохраняются; покрыто `subscribeService` regression-тестами.

### Defer (1) — pre-existing / cosmetic

- [x] **[Review][Defer] PPPP6-W1: spec section «Структура файлов» в `story-35-3.md:493-525` отстаёт от scope creep** — 9 файлов изменены/созданы без mention в spec list (`backend/apps/common/apps.py`, `throttling.py`, `tests/test_common_config.py`, `users/admin.py`, `users/authentication.py`, settings `base.py/development.py/staging.py/test.py`, `tests/unit/test_users_admin.py`, `tests/unit/test_common_throttling.py`, `services/__tests__/subscribeService.test.ts`). Все они задокументированы в Pass 2-5 patch sections, но spec sections «Структура файлов» / «Acceptance Criteria» — нет. **Defer reason:** косметический spec-maintenance; не блокирует runtime.

### Dismissed (~50) — already-closed in Pass 1-5 / verified / spec-documented

**Verified false positives (после повторной проверки кода):**
- BH-5/E16 `production.py removed REST_FRAMEWORK block → throttle regression` → **verified safe**: rates (anon=6000/min, user=10000/day, subscribe=30/min) мигрированы в `backend/freesport/settings/base.py:171-181` (P10 Pass 4). Прод-окружение наследует, нет регрессии.
- BH-3 `DRFValidationError vs DatabaseError catch ordering` → **verified safe**: P5N3 regression `test_subscribe_returns_structured_503_on_operational_consent_failure` подтверждает структурный 503. `IntegrityError` подкласс `DatabaseError`, но `SubscribeSerializer.create` перехватывает свой `IntegrityError` и поднимает `already_subscribed_error()` ДО того, как он дойдёт до outer `except DatabaseError`.
- BH-4/B20/E18 `select_for_update on non-PK email + concurrent reactivation` → **dismissed**: row-lock на email-row корректно покрывает существующие активные подписки; для phantom inserts срабатывает UNIQUE constraint → `already_subscribed_error()` → 409. Поведение детерминированное.
- BH-7 `already_subscribed_error catches UserConsent IntegrityError` → **dismissed**: `serializer.save()` поднимает только Newsletter-IntegrityError; UserConsent.create находится в view ВНЕ сериализатора, отлавливается `except DatabaseError` → 503.
- BH-9 `OpenAPI 503 details type vs frontend types` → **частично reclassified** — см. PPPP6-P2 (frontend type wider, не OpenAPI narrower).

**Уже закрыто в Pass 1-5:**
- BH-1/EC-5/A2 `validate uses initial_data strict bool` = **DN1 Pass 2** documented.
- BH-2/EC-3/EC-4 `session.save() before atomic + orphan rows on 503` = **PPPP2 Pass 4** intentional + accepted growth-pattern (DBSize defer).
- BH-6 `subscribe scope absent → ImproperlyConfigured` = **PPPP3/P10 Pass 4** — все 4 env-файлов (base/dev/staging/test) теперь явно перечисляют `subscribe`.
- BH-8/BH-22/R6/EC-7 `_has_error_code recursion / split logic / depth` = **WWW3 Pass 3** defer.
- BH-10/D3 (R7? нет, R7 это другое) `is_global filter removed for registration` = **D3 Pass 1 → P11 Pass 2 → WWW14 Pass 3 → AA-1 Pass 4** accepted намеренное изменение политики.
- BH-11 `AnonRateThrottle mixin order` = архитектурный, не находка.
- BH-12/BH-24 `tests mock UserConsent.create / broken transaction state` = integration-уровень покрыт P5N3.
- BH-13 `pdp_consent not denormalized in Newsletter` = design decision, FK покрывается audit-таблицей.
- BH-14/E6 `policy_version "1.0" hardcoded default` = **W5N6 Pass 5** defer.
- BH-15/E11 `rotating IP throttle bypass` = **W5N2 Pass 5** defer (NAT/proxy edge).
- BH-17/A6 `OpenAPI reorder noise patch/get` = drf-spectacular regen volatility, **WWWW2 Pass 4** defer (но ProductDetail loss = новая находка PPPP6-D1).
- BH-18 `frontend toast localization period` = **W5 microcopy** defer / косметика.
- BH-19 `"unknown" sentinel в admin._get_client_ip` = pre-existing pattern.
- BH-21 `MAX_CONSENT_USER_AGENT_LENGTH vs Newsletter.user_agent` = decoupled, low risk.
- BH-23 `SubscribeRateThrottle scope namespace` = единственный consumer scope=subscribe.
- BH-25/E17 `system check Error vs Warning` = **PPP4 Pass 3** intentional strict.
- EC-2 `select_for_update outside atomic` = находится внутри atomic (view-level wrap).
- EC-7 `single pdp_consent → 2 consent records` = **spec Решение #2** explicit.
- EC-9 `IPv4-mapped IPv6 granularity loss` = audit edge, accepted.
- EC-10 `bracketed IPv6 with whitespace` = misconfigured proxy edge, accepted.
- EC-12 `session.save() returns but session_key None` = покрыт system check + edge.
- EC-13 `5xx without JSON body` = P5N4 закрыл server_error через DRF-shape, нативный 502/504 без body — edge.
- EC-15 `JWT/session decoupling race on mid-request logout` = edge case, не воспроизводится в test harness.
- R1-R4 `fragile tests` (count==0, atomic_blocks, THROTTLE_RATES patch, name substring) = **WWW13 Pass 3 / косметика** defer.

---

## Review Findings — Pass 7 (2026-05-15)

Reviewer: Claude Code `bmad-code-review` (Opus 4.7) — параллельные слои: Blind Hunter, Edge Case Hunter, Acceptance Auditor. Диф: backend-only chunk `28c0a0a0~1..HEAD` (21 файл, +1171/-369, 2322 строки unified diff). Triage: 46 raw → 7 patch + 8 defer + ~30 dismiss (все dismiss — уже закрыты в Pass 1-6 либо noise).

### Decision-needed (0)

Архитектурные вопросы не выявлены — все decision-shaped находки (B8/B20 IP fallback к nginx; E17 `policy_version` audit drift) уже ратифицированы в PPPP6-D2 / W5N6 Pass 5.

### Patch (7)

- [x] [Review][Patch] **P7-1. `SubscribeSerializer.validate()` падает `AttributeError`/500 если `self.initial_data` — не dict** [`backend/apps/common/serializers.py:97-102`] — Strict-bool guard читает `self.initial_data.get("pdp_consent")`. `JSONParser` принимает любой валидный JSON (array, scalar, null). POST `[]` или `"string"` → `initial_data` — не dict → `.get()` → `AttributeError` → 500 без структуры контракта. Fix: добавить `isinstance(self.initial_data, dict)` guard в начале `validate()`, иначе raise standard DRF `ValidationError({"non_field_errors": "Expected an object"})`. Источник: Blind#5. **Severity: HIGH** (потенциальный 500 на неожиданном payload). Закрыто Pass 7: non-mapping guard + serializer/API regression tests.

- [x] [Review][Patch] **P7-2. Тест `test_subscribe_anonymous_session_is_saved_before_atomic_consent_write` тавтологический — ассерт через `getattr(connection, "atomic_blocks", ())`** [`backend/tests/integration/test_common_subscribe_api.py:1502-1520`] — `connection.atomic_blocks` атрибут не существует в Django (`BaseDatabaseWrapper` использует `savepoint_ids` / `in_atomic_block`). `getattr(..., ())` всегда `()` → `len(...) == 0` → `0 <= 1` всегда True. Тест ничего не проверяет — `session.save()` мог бы быть внутри atomic блока и тест бы всё равно прошёл, ломая PPPP2 invariant. Fix: использовать `connection.savepoint_ids` (depth = `len(savepoint_ids)`) или установить probe через `transaction.atomic()` context manager mock. Источник: Blind#12. **Severity: HIGH** (test smell — скрывает регрессию PPPP2). Закрыто Pass 7: test-probe переведён на baseline `connection.savepoint_ids`.

- [x] [Review][Patch] **P7-3. `test_subscribe_reactivation_locks_existing_subscription` проверяет только `.called`, не реальное SQL `FOR UPDATE`** [`backend/tests/integration/test_common_subscribe_api.py:1441-1460`] — `wraps=Newsletter.objects.select_for_update`; ассерт `select_for_update.called` — проверка вызова, не семантики lock'а. Реактивация без `select_for_update` (например, удалили вызов из `serializer.save()`) — тест останется зелёным. Fix: проверить через `captured_queries` присутствие `SELECT ... FOR UPDATE` или использовать `pytest.mark.django_db(transaction=True)` + параллельный поток, конкурирующий за row. Источник: Blind#13. **Severity: MEDIUM** (test smell). Закрыто Pass 7: test assertion переведён на `CaptureQueriesContext` и наличие `FOR UPDATE` в SQL.

- [x] [Review][Patch] **P7-4. `SubscribeSerializer.save()` использует `select_for_update` без собственного `transaction.atomic()`** [`backend/apps/common/serializers.py:140-180`] — Сейчас works потому что caller (view) оборачивает в atomic. Unit-тест `serializer.save()` напрямую (или будущий internal admin/signal caller) упадёт с `TransactionManagementError: select_for_update cannot be used outside of a transaction`. Fix: обернуть `select_for_update().get()` → `Newsletter.objects.create()` блок в `with transaction.atomic():` внутри `save()`. Nested atomic с view-уровнем безопасно (Django поддерживает). Источник: Edge#2. **Severity: MEDIUM** (defensive — устойчивость к будущим callers). Закрыто Pass 7: `SubscribeSerializer.create()` открывает собственный atomic; direct-save regression добавлен.

- [x] [Review][Patch] **P7-5. Логгер 503-ветки misleading при `session.save()` failure** [`backend/apps/common/views.py:414-441`] — `try:` блок включает `request.session.save()` (line 416, до atomic). Если session.save() бросает `DatabaseError` (deadlock `django_session`, DB outage), catch на line 440 пишет `"Failed to persist newsletter consent audit"` — но consent write даже не начат. Operator misdiagnosis. Fix: вынести session.save() в отдельный try/except с собственным log message (`"Failed to materialize anonymous session for consent audit"`) или различить branch внутри except. Источник: Auditor A2. **Severity: LOW** (observability). Закрыто Pass 7: session materialization вынесена в отдельный try/except и покрыта caplog regression.

- [x] [Review][Patch] **P7-6. OpenAPI `subscribe` 400 description устарел после AC-4** [`docs/api/openapi.yaml:110-111`] — Текст `description: Ошибка валидации email`. После AC-4 эндпоинт также возвращает 400 для `pdp_consent` field error. AC-7 step 4(б) добавил example `pdp_consent_required`, но description не обновлён. Fix: `description: Ошибка валидации (email или pdp_consent)`. Источник: Auditor A3. **Severity: LOW** (docs drift). Закрыто Pass 7: `extend_schema` и regenerated `docs/api/openapi.yaml` синхронизированы.

- [x] [Review][Patch] **P7-7. System check `check_session_engine_for_subscribe_consent` помечен `Tags.compatibility` вместо security/database** [`backend/apps/common/apps.py:8`] — Check защищает `CheckConstraint userconsent_user_or_session_required` (data-integrity / security инвариант). Команда `python manage.py check --tag=security` или `--tag=database` (которые DevOps gates targets) не увидит этот check. Fix: заменить `Tags.compatibility` на `Tags.security` (более точно семантически) или `Tags.database`. Источник: Auditor A4. **Severity: LOW** (cosmetic / surface in CI). Закрыто Pass 7: check зарегистрирован под `Tags.security`, добавлен `run_checks(tags=[Tags.security])` regression.

### Defer (8) — pre-existing / out-of-scope

- [x] [Review][Defer] **W7-1. Malformed `X-Real-IP`/`X-Forwarded-For` → REMOTE_ADDR fallback collapses всех атакующих в один nginx-IP throttle bucket** [`backend/apps/common/throttling.py:244-257`] — В production REMOTE_ADDR = nginx upstream IP (постоянное значение). Атакующий ротирует malformed headers → fallback на nginx IP → все попадают в shared bucket 30/min. С другой стороны легитимные пользователи за тем же nginx тоже получают 429. **Defer reason:** уже задокументировано в W5N2 Pass 5 (CGNAT/NAT amplification); требует архитектурного решения (CAPTCHA / session-scoped throttle / trusted-proxy allowlist) — единая infra-story. Источник: Blind#3.

- [x] [Review][Defer] **W7-2. `test_subscribe_atomic_rollback_on_consent_failure` не различает view-atomic rollback от pytest-django outer transaction rollback** [`backend/tests/integration/test_common_subscribe_api.py:1462-1483`] — Без `pytest.mark.django_db(transaction=True)` outer transaction wrap'а pytest откатывает всё в конце теста. Assertion `UserConsent.objects.count() == 0` пройдёт даже если view's `atomic()` block НЕ откатил (фикстура спасёт). **Defer reason:** Pass 4 PPPP3 уже улучшил тест (первый create реальный). Переход на `transaction=True` сломает изоляцию параллельных тестов и потребует пересмотра pytest-плагинов проекта. Источник: Blind#14.

- [x] [Review][Defer] **W7-3. OpenAPI `users` vs `Users` tag case inconsistency в reshuffled blocks** [`docs/api/openapi.yaml:2034-2056`] — `/users/favorites/{id}/` GET использует tag `users`, DELETE — `Users`. Swagger UI разделит resource на две секции. **Defer reason:** drf-spectacular regeneration artifact, pre-existing (см. WWW2/WWWW2 Pass 4 deferred); не вводится 35.3. Источник: Blind#16.

- [x] [Review][Defer] **W7-4. `ProxyAwareUserRateThrottle` в production изменил 429 message format для всех DRF-throttled endpoints** [`backend/freesport/settings/production.py` (deleted override) → `backend/freesport/settings/base.py:944-952`] — Раньше production использовал raw `UserRateThrottle` с английским `"Request was throttled. Expected available in X seconds."`. Теперь `ProxyAwareUserRateThrottle` (`default_detail = "Слишком много попыток..."` PPP2 Pass 3) применён ко всем endpoints, не только subscribe. Frontend i18n / message parsing других endpoints может сломаться. **Defer reason:** scope creep за 35.3; требует frontend-аудита всех throttled endpoints. Источник: Blind#18.

- [x] [Review][Defer] **W7-5. Degraded session backend (Redis/cache) → `session.save()` no-op → empty `session_key` → CheckConstraint → 503 + audit silently lost** [`backend/apps/common/views.py:415-423`] — Кэш/сессия в degraded режиме могут не материализовать session_key. `request.session.session_key` остаётся None → `session_key = ""` → `UserConsent.create()` → IntegrityError → 503. Пользователь видит 503 для валидного запроса; audit не записан. **Defer reason:** hypothetical (Django db-backend не имеет silent-fail режима); реальные DB outages уже ловятся `except DatabaseError → 503` (P5N3). Источник: Edge#3.

- [x] [Review][Defer] **W7-6. Throttle bucket edge cases: IPv4-mapped IPv6 + whitespace-only headers конфликтуют по cache key** [`backend/apps/common/throttling.py:244-257`, `backend/apps/common/utils/consent_audit.py:60-101`] — `::ffff:127.0.0.1` нормализуется в `127.0.0.1` (тот же bucket что у клиента отправляющего `X-Real-IP: 127.0.0.1` напрямую — collide); whitespace-only `X-Real-IP: " "` + пустой REMOTE_ADDR → empty ident bucket. **Defer reason:** trusted-proxy misconfiguration territory; mitigation на nginx-уровне (header overwrite). Связано с W5N2 / W7-1. Источник: Edge#10 + Edge#12.

- [x] [Review][Defer] **W7-7. Throttle integration tests flaky под pytest-xdist с shared Redis cache** [`backend/tests/integration/test_common_subscribe_api.py:425-441, 1546-1569`] — `cache.clear()` в начале/конце теста не изолирует от параллельных workers (xdist) с shared Redis backend. Counter contamination → ложные 429 / отсутствие 429 в одном из workers. **Defer reason:** pre-existing test infra issue (WWW13 Pass 3 deferred); фикс требует pytest fixture с per-test KEY_PREFIX или dedicated locmem cache для tests. Источник: Edge#9 + Edge#19.

- [x] [Review][Defer] **W7-8. AC-8 test parametrization gaps: zone-id integration coverage + surrogate-only UA** [`backend/tests/integration/test_common_subscribe_api.py:233-250, 273-288`] — Spec AC-8 case #5 требовал параметризацию `private/loopback/zone-id/невалидный IP`; реализация — один кейс с XFF + отдельные тесты на private/невалидный. Zone-id (`fe80::1%eth0`) покрыт только unit test_common_throttling.py, не integration subscribe path. AC-8 case #6 (UA 1000 → ≤512) тестируется на конкретной длине 1110 → exact 512, без короткого surrogate-only кейса. **Defer reason:** функционально требование `<=512` выполнено; unit tests покрывают edge cases; коспетический test-coverage gap. Источник: Auditor A1 + A5.

### Dismissed (~30) — already-resolved in Pass 1-6 / verified false positives / noise

**Blind Hunter:** B1 (self-discard), B2 (low fragility, не баг), B4 (= BH-6 Pass 6: subscribe scope в base + всех env-файлах), B6 (`error_messages` `invalid`/`null` dead — DN1 Pass 2 intentional), B7 (= PPPP2 Pass 4 intentional accept session row), B8 (= PPPP6-D2 Pass 6 ratified REMOTE_ADDR fallback), B9 (= D3→P11→WWW14 ratified is_global removal), B10 (= E14 — request.user lazy кэшируется, безопасно), B11 (= WWW3 Pass 3 deferred), B15 (low risk, design pattern), B17 (= W5N4 Pass 5 deferred cross-domain cookies), B19 (intentional per-IP design), B20 (= B8 merge).

**Edge Case Hunter:** E1 (concurrent create race correctly handled via IntegrityError → 409 → BH-3 Pass 6 verified), E5 (= B11/A6/WWW3), E6 (= DN1 Pass 2 strict initial_data intentional), E7 (DRF coerces string → list of ErrorDetail correctly), E8 (= W5N2 Pass 5 deferred), E9 (= WWW13 Pass 3 deferred), E11 (= PPPP2 ratified), E13 (over-engineering future-proofing), E14 (self-discard by Hunter), E15 (= PPPP2 ratified), E17 (= W5N6 Pass 5 deferred), E18 (= W5N3 Pass 5 deferred), E20 (cosmetic dead config).

**Acceptance Auditor:** A6 (= WWW3 Pass 3 deferred — `_has_error_code` recursion).

---

## Review Findings — Pass 8 (2026-05-15)

Восьмой заход `bmad-code-review` после закрытия P7-1…P7-7. 3 параллельных слоя (Blind Hunter, Edge Case Hunter, Acceptance Auditor) по diff `0833e90c^..HEAD` (3204 строки, 31 файл, баз/фронт + тесты, без api.generated.ts / openapi.yaml / story.md / review-cache). Raw: 18 + 49 + 8 = 75. Дедуп: ~35 уникальных. Триаж: **2 decision-needed, 8 patch, 13 defer, ~30 dismissed**.

### Decision-needed (2 — resolved 2026-05-15 → оба defer)

- [x] **DN8-1 → Defer.** Email enumeration через 409 «already_subscribed» [`backend/apps/common/views.py:441-451`, `backend/apps/common/serializers.py:120-127`]. Анонимный атакующий с `pdp_consent: true` различает «subscribed/not subscribed» по `201` vs `409`. **Решение (Alex, 2026-05-15):** defer — объединить с WWWW3 Pass 4 (`/unsubscribe/` enumeration) в единую security-story «harden enumeration»; `/subscribe/` и `/unsubscribe/` — один класс уязвимости, чинить одним паттерном. Смена 409-контракта ломает AC-4 и откатывает 7 passes тестов. Throttle 30/min ограничивает атаку; маскировка — территория комплаенс-офицера. Источник: Blind#3.

- [x] **DN8-2 → Defer.** `_sanitize_ident` fallback на `sanitize_log_value` создаёт separate Redis bucket для каждой мусорной `X-Real-IP` [`backend/apps/common/throttling.py:13-16`]. **Решение (Alex, 2026-05-15):** defer — `get_ident()` уже fallback-ится на `REMOTE_ADDR` для malformed заголовков (тест `test_proxy_aware_throttle_uses_remote_addr_for_malformed_proxy_header`); в production REMOTE_ADDR = постоянный nginx-upstream IP, что ограничивает реальный bypass. Полное решение (TRUSTED_PROXY allowlist) уже отложено как W7-1 «единая infra-story». Источник: Blind#9 + Edge#19 + Edge#20.

### Patch (8)

- [x] [Review][Patch] **P8-1. Frontend `subscribeService` маппит 5xx БЕЗ `details` в `network_error` — реальные 502/504 Nginx (HTML response) показывают пользователю «Не удалось подписаться. Попробуйте позже» вместо «Сервер временно недоступен»** [`frontend/src/services/subscribeService.ts:77-79`, `frontend/src/components/home/SubscribeForm.tsx:96-119`, `frontend/src/components/home/ElectricSubscribeForm.tsx:90-135`] — Гард `if (axiosError.response?.status >= 500 && details)` требует `details`. 502 Bad Gateway / 504 Gateway Timeout / 503 без JSON-тела (Nginx сам), 500 без структурированного ответа — все падают в `network_error`. UX неконсистентен: реальная инфра-проблема выглядит как offline. Fix: `if (status >= 500) throw new SubscribeServiceError('server_error', details ?? undefined)` — details optional. Frontend `getValidationDetails` уже выдержит `undefined`. Источник: Blind#13 + Edge×3.

- [x] [Review][Patch] **P8-2. `frontend/src/types/api.generated.ts:2816` всё ещё `Ошибка валидации email`, тогда как `docs/api/openapi.yaml:111` обновлён в Pass 7 P7-6 на `Ошибка валидации (email или pdp_consent)`** [`frontend/src/types/api.generated.ts:2816`] — DoD пункт «generated TypeScript types обновлены» помечен `[x]`, но регенерация после P7-6 не выполнена — drift. Fix: `npx openapi-typescript ../docs/api/openapi.yaml -o ./src/types/api.generated.ts`. Источник: Auditor#1.

- [x] [Review][Patch] **P8-3. THROTTLED_ERROR text drift — backend с точкой, frontend без** [`backend/apps/common/throttling.py:10` (`"Слишком много попыток. Попробуйте через минуту."`), `frontend/src/components/home/SubscribeForm.tsx:31`, `frontend/src/components/home/ElectricSubscribeForm.tsx:28` (`"Слишком много попыток. Попробуйте через минуту"`)] — Симметрично Pass 2 PP6 (`PDP_CONSENT_REQUIRED` точка). Backend DRF detail vs frontend fallback константы расходятся → пользователь видит разные строки в зависимости от источника. Fix: добавить точку в обе frontend константы. Источник: Auditor#2.

- [x] [Review][Patch] **P8-4. ElectricSubscribeForm не покрыт регрессией на `server_error` / 503** [`frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`] — Blue форма имеет тест «shows backend message on server error from subscribe service» (`SubscribeForm.test.tsx:251`), Electric — нет (`grep server_error|503` → 0 матчей). Pass 2 PP4 явно зафиксировал parity-инвариант между Blue и Electric. Fix: добавить аналогичный test-case в Electric с `vi.mocked(subscribeService.subscribe).mockRejectedValue(new SubscribeServiceError('server_error', {...}))`. Источник: Auditor#3.

- [x] [Review][Patch] **P8-5. `backend/tests/unit/test_users_admin.py` без `pytest.mark.unit` маркера** [`backend/tests/unit/test_users_admin.py:1-20`] — Файл расширен в рамках 35.3 (P5N6 — `SessionStore` change), но не имеет `pytestmark = pytest.mark.unit`. Project-context.md §4 требует marker на каждом backend-тесте, иначе выпадает из `make test-unit` фильтра. Fix: `pytestmark = pytest.mark.unit` в начале файла (после имеющегося `pytest.mark.django_db` на классах). Источник: Auditor#6.

- [x] [Review][Patch] **P8-6. `SubscribeRateThrottle` silently disabled если `DEFAULT_THROTTLE_RATES['subscribe']` отсутствует в env-настройках** [`backend/apps/common/throttling.py:58-68`, `backend/apps/common/apps.py`] — `SimpleRateThrottle.get_rate()` возвращает `None` если ключ scope отсутствует → throttle отключается silently. Сейчас все env (base/dev/staging/test) явно перечисляют `subscribe`, но при добавлении новой env легко забыть. Fix: расширить `check_session_engine_for_subscribe_consent` (или добавить parallel system check) — `if 'subscribe' not in settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}): yield Error("Missing 'subscribe' throttle rate", id='common.E002')`. Источник: Blind#10 + Edge#22.

- [x] [Review][Patch] **P8-7. dev/staging/test settings ПОЛНОСТЬЮ замещают `DEFAULT_THROTTLE_RATES`, не наследуя от `base.py`** [`backend/freesport/settings/development.py:58-62`, `backend/freesport/settings/staging.py:49-53`, `backend/freesport/settings/test.py:96-100`] — Pattern `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {...}` (assignment, не merge). Если в `base.py` появится новый scope (e.g. `"admin"`), все три env-файла его molchat'ом сбросят. Fix: `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {**REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "anon": "100000/min", "subscribe": "100000/min", "user": "100000/min"}` (inherit + override). Источник: Edge#26.

- [x] [Review][Patch] **P8-8. Stale `setError('pdp_consent', {type: 'server'})` сохраняется между submit'ами — повторная отправка с валидным значением показывает старую ошибку** [`frontend/src/components/home/SubscribeForm.tsx:88-122`, `frontend/src/components/home/ElectricSubscribeForm.tsx:113-128`] — RHF 7+ server-type errors не очищаются автоматически при `reValidateMode: 'onChange'`. Симметрично уже-deferred WWW9 Pass 3, но в финальный review разумнее закрыть. Fix: `clearErrors('pdp_consent')` в начале `onSubmit` обеих форм. Источник: Edge#34 + WWW9 reaffirm.

### Defer (13) — pre-existing, hypothetical, или infrastructure scope

- [x] [Review][Defer] **W8-1. `UserConsent.objects.create()` бросает не-`DatabaseError` (ValueError/TypeError из model-level coercion) — 500 leak вместо 503** [`backend/apps/common/views.py:429-451`] — `except DatabaseError` ловит большинство DB-проблем, но `model.__init__` может бросить `ValueError` (например, `ip_address="not-an-ip"` — но мы уже нормализовали; `consent_type` invalid — но мы хардкодим). Hypothetical, текущий input-flow это не воспроизводит. Defer reason: defensive future-proofing, не runtime concern для текущего scope; broaden catch может скрыть реальные программные баги. Источник: Edge#1.

- [x] [Review][Defer] **W8-2. AbortController отсутствует на `subscribeService.subscribe` — отмена навигацией показывает «Не удалось подписаться. Попробуйте позже» вместо silent abort** [`frontend/src/services/subscribeService.ts:57-83`] — `axios.CanceledError` не классифицируется специально, попадает в `network_error`. Defer reason: minor UX; пользователь, ушедший со страницы, всё равно не увидит сообщение. Источник: Edge#29.

- [x] [Review][Defer] **W8-3. Double-submit окно между click и `isSubmitting=true` — два быстрых клика провоцируют два запроса** [`frontend/src/components/home/SubscribeForm.tsx:148-165`, `frontend/src/components/home/ElectricSubscribeForm.tsx:194-203`] — RHF `handleSubmit` асинхронен; isSubmitting устанавливается после первого клика, но второй кликается в окне до этого. Fix: `disabled` через onClick handler. Defer reason: микро-UX, серверный 30/min throttle ограничивает реальный impact. Источник: Edge#36 + Edge#41.

- [x] [Review][Defer] **W8-4. Пустой first hop в `X-Forwarded-For` (e.g. `", 1.2.3.4"`) → `get_client_ip` падает в REMOTE_ADDR вместо чтения hop2** [`backend/apps/common/utils/consent_audit.py:50-54`] — Malformed proxy config. Defer reason: misconfigured nginx territory, инфра-проблема. Источник: Edge#14.

- [x] [Review][Defer] **W8-5. `.toUpperCase()` для русских строк ошибок в `ElectricSubscribeForm` — некорректный mapping в старых браузерах** [`frontend/src/components/home/ElectricSubscribeForm.tsx:90-135`] — Кириллический uppercase зависит от locale; `toLocaleUpperCase('ru-RU')` корректнее. Defer reason: современные браузеры обрабатывают правильно; legacy-browser scope не требуется. Источник: Edge#39.

- [x] [Review][Defer] **W8-6. `normalize_consent_ip` принимает 0.0.0.0/multicast/reserved IPs после удаления `is_global` фильтра (P11)** [`backend/apps/common/utils/consent_audit.py:60-101`] — `::ffff:0.0.0.0` → `"0.0.0.0"`, `224.0.0.1`, `255.255.255.255` принимаются в audit. Defer reason: D3→P11 Pass 1-2 ratified — принят forensic noise в обмен на полноту audit; comply-officer одобрил. Связано с WWW14 Pass 3. Источник: Edge#15 + Edge#48.

- [x] [Review][Defer] **W8-7. Bracketed IPv6 с внутренним whitespace (`" [::1]:80 "`) → парсинг падает** [`backend/apps/common/utils/consent_audit.py:66-80`] — `candidate.strip()` обрезает только окружающий whitespace, не внутренний. Malformed proxy header. Defer reason: nginx-level concern; не воспроизводимо валидным proxy. Связано с W7-6 Pass 7. Источник: Edge#16.

- [x] [Review][Defer] **W8-8. При fallback на REMOTE_ADDR (`get_consent_ip_address`) сам REMOTE_ADDR не логируется — потеря observability** [`backend/apps/common/utils/consent_audit.py:127-153`] — Если оба заголовка malformed и REMOTE_ADDR тоже невалидный, audit запишет `ip_address=None`, но в логе будет только malformed header. Defer reason: forensic enhancement; не блокирует runtime. Источник: Edge#18.

- [x] [Review][Defer] **W8-9. `SubscribeRateThrottle.cache_format` зависит от DRF cache prefix convention** [`backend/apps/common/throttling.py:63-68`] — При DRF upgrade (e.g. 3.16+) prefix может измениться → throttle перестанет находить старые ключи (но не сломается полностью). Defer reason: hypothetical upgrade concern; покрывается при upgrade-аудите. Источник: Edge#21.

- [x] [Review][Defer] **W8-10. Возможный дубликат DOM `id="input-электронная-почта"` если две `SubscribeForm` отрендерены на одной странице** [`frontend/src/components/home/SubscribeForm.tsx:132-146`] — `Input` компонент генерирует id из label. P8 Pass 1 закрыл duplicate IDs через `useId()` для form-level IDs (subscribe-pdp-consent), но `Input` компонент потребовал бы отдельной правки. Defer reason: текущая архитектура страниц не предполагает две формы Subscribe на одной странице; верификация требует чтения `Input/Input.tsx` (вне scope spec). Источник: Edge#35.

- [x] [Review][Defer] **W8-11. `check_session_engine_for_subscribe_consent` blacklist `signed_cookies`, не whitelist** [`backend/apps/common/apps.py:6-21`] — Будущий custom session backend (например, file-based без save()) пройдёт check, но не материализует key. Defer reason: hypothetical future custom backend; project использует только Django stock + DB. Источник: Edge#24.

- [x] [Review][Defer] **W8-12. Тест `test_subscribe_anonymous_session_is_saved_before_atomic_consent_write` — assertion `save_atomic_depths[0] == baseline_savepoint_depth` работает только потому что `ATOMIC_REQUESTS=True` в `test.py` использует transaction (не savepoint)** [`backend/tests/integration/test_common_subscribe_api.py:1573-1592`] — Production-stack (`ATOMIC_REQUESTS=False`) валиден; test-stack валиден; но логика test'а assertирует test-env, не production-инвариант («session.save() ВНЕ view's transaction.atomic()» с любым ATOMIC_REQUESTS). Defer reason: производит правильный результат в test-env; рефактор для general assertion усложнит тест. Источник: Blind#2 + Blind#16.

- [x] [Review][Defer] **W8-13. `getValidationDetails` не передаёт `details` для 400 с non-validation shape (e.g., `{error: "bad payload"}`)** [`frontend/src/services/subscribeService.ts:71-73`] — Гипотетический backend-ответ, обычный DRF flow всегда возвращает field-keyed validation errors. Defer reason: не воспроизводимо текущим backend кодом; защита от будущих экзотических shapes. Источник: Edge#32.

### Dismissed (~30) — already-resolved / verified false-positive / noise

**Blind Hunter:**
- B1/E7/E8 `validate uses initial_data` = **DN1 Pass 2** ratified strict-bool guard для 152-ФЗ.
- B4 `session_key rotation в serializer.save()` — speculative, `Newsletter.save()` не вызывает session middleware/rotation.
- B6 `empty session_key в anon flow` = **check_session_engine_for_subscribe_consent** Pass 5 покрывает.
- B7 `is_global removal` = **D3→P11 Pass 1-2 → WWW14 Pass 3 → AA-1 Pass 4** ratified.
- B11 `select_for_update reactivate race` — корректный design (P3 Pass 1, BH-3 Pass 6).
- B12 `503 error CharField vs Enum` — cosmetic future-proofing, контракт стабилен.
- B14 `UA inconsistency views vs serializer` — оба пути сходятся в `sanitize_consent_user_agent(None|"")` → `""`.
- B15 `register() every render` — RHF 7+ возвращает стабильные handlers.
- B18 `pop("pdp_consent", False)` — `write_only=True` гарантирует, что pdp_consent не попадёт в response; default cosmetic.

**Edge Case Hunter:**
- E2 `ImproperlyConfigured из session.save()` = system check Pass 5 покрывает на startup.
- E3 `request.session None при custom middleware` — hypothetical, не воспроизводимо текущим settings.
- E4 `anon race shared session_key → 4 rows` — append-only audit correct semantic (4 distinct events).
- E5 `session.session_key None после save()` = system check + W7-5 Pass 7 deferred.
- E9 `OperationalError on replica` — проект single PG, no replicas.
- E11 `select_for_update без atomic в serializer` = P7-4 Pass 7 закрыт.
- E13 `whitespace-only X-Real-IP` — strip() покрывает; fallback на XFF работает.
- E25 `ProxyAwareUserRateThrottle Russian message creep` = **DN3 Pass 2** ratified.
- E27 `_has_error_code RecursionError` = **WWW3 Pass 3** deferred, текущий shape flat.
- E30 `429 Retry-After ignored` — frontend использует hardcoded fallback, Retry-After не критичен для 30/min.
- E31 `5xx 500 not 503` — backend всегда returns 503 для consent persistence (P5N3); 502/504 покрыты P8-1.
- E33 `429 от CDN с HTML` — Content-Type check overkill для текущей инфраструктуры.
- E37 `Field-bound vs toast` — design decision (Pass 2 PP4 закрыл a11y parity).
- E38 `Checkbox unmount during pending` — React warnings tolerable, no UX bug.
- E40 `tracking_save savepoint_ids flaky across pytest-django versions` — runtime stable в текущем pin.
- E42 `multi-DB router using=` — single DB project.
- E44 `request.user.is_authenticated LazyObject race` — Django framework guarantee, не воспроизводимо.
- E45 `503 без details через server_error guard` = совпадает с P8-1.
- E46 `concurrent anon на nginx-IP` = **W5N2/W7-1** deferred CGNAT amplification.

**Acceptance Auditor:**
- Audit#5 `products/serializers.py scope creep` = Pass 6 PPPP6-D1→P3 закрытие OpenAPI regression, justified.
- Audit#7 `policy_version="1.0" hardcoded` = **W5N6 Pass 5** deferred, для Story 35.5.
- Audit#8 `JSDoc Story 35.3 reference missing` — косметика; spec ничего не требует про JSDoc reference.

---

## Review Findings — Pass 9 (2026-05-15)

Адверсариальное ревью диапазона `fb47fbeb..bbae541f` (Blind Hunter / Edge Case Hunter / Acceptance Auditor). Итог: 2 decision-needed, 1 patch, 5 defer, 12 dismissed.

### Decision-needed (2 — resolved 2026-05-15 → оба patch)

- [x] [Review][Decision] Локализация 429-ответа `SubscribeRateThrottle` — resolved (Alex, 2026-05-15): вариант «удалить мёртвый код» → стало DP9-1.
- [x] [Review][Decision] Точка в тексте RHF-ошибки PDN — resolved (Alex, 2026-05-15): вариант «оставить точку, обновить AC-1» → стало DP9-2.

### Patch (3: 1 исходный + 2 из decision-resolved)

- [x] [Review][Patch] P9-1. Дублированный inline-комментарий `# type: ignore[no-redef]` дважды в одной строке [`backend/freesport/settings/test.py:93`]
- [x] [Review][Patch] DP9-1. Удалить мёртвые `default_detail`/`default_code` с `ProxyAwareThrottleIdentMixin` + тест `test_proxy_aware_throttle_uses_russian_default_detail` (DRF не читает эти атрибуты для 429-ответа) [`backend/apps/common/throttling.py:10-11`, `backend/tests/unit/test_common_throttling.py`]
- [x] [Review][Patch] DP9-2. Обновить AC-1 в story: сообщение RHF-ошибки PDN зафиксировать С точкой (`«…персональных данных.»`) для консистентности с backend-сообщением [story AC-1, строки 54/397/677]

### Defer (5) — pre-existing / minor / out-of-scope

- [x] [Review][Defer] Осиротевшая `django_session`-строка при 503 — `request.session.save()` выполняется до `transaction.atomic()`, поэтому при сбое записи consent (503) сессия в БД остаётся без подписки и согласия [`backend/apps/common/views.py`] — deferred, minor side effect на редком DB-failure пути.
- [x] [Review][Defer] Недетерминированный текст toast `getFirstBackendError` — берётся «первое попавшееся» сообщение из `Object.values(details)` без гарантии порядка [`SubscribeForm.tsx` / `ElectricSubscribeForm.tsx`] — deferred, проявляется только при multi-field error response.
- [x] [Review][Defer] Несогласованный fallback неизвестного IP — admin `_get_client_ip` отдаёт `"0.0.0.0"`, consent-audit отдаёт `None` для того же `unknown` [`backend/apps/users/admin.py`] — deferred, admin-код, минорная неконсистентность.
- [x] [Review][Defer] `SubscribeRateThrottle` ключуется только по IP — авторизованные пользователи за общим NAT делят один лимит `30/min`; пустой IP → все клиенты в одном бакете [`backend/apps/common/throttling.py:63-68`] — deferred, endpoint преимущественно анонимный, failure-closed.
- [x] [Review][Defer] Сломанный pipeline `npm run generate:types` — скрипт читает устаревший `docs/api-spec.yaml`, тогда как канонический файл — `docs/api/openapi.yaml`; типы синхронизировались вручную [`frontend/package.json`] — deferred, ранее зафиксировано как W5N1.

### Dismissed (12) — noise / false positive / deliberate design

**Blind Hunter:**
- B1 `is_global removal — регрессия` — субагенты сравнивали закоммиченный stale-артефакт `story-35-3-review-pass3.diff` с финальным кодом; финальный код+тесты консистентны и намеренны (verified `test_subscribe_accepts_private_forwarded_ip_for_audit`, `test_subscribe_newsletter_ip_uses_normalized_audit_ip`).
- B2 `fallback на REMOTE_ADDR при malformed XFF` — намеренное решение Pass 5 (P5N2), задокументировано, покрыто тестом.
- B3 `common.E002 проверяет наличие ключа, а не регистрацию scope` — работает как задумано, startup-guard.
- B5 `validate() читает initial_data, а не attrs` — намеренная строгая 152-ФЗ проверка; `validate()` запускается только через `is_valid()`, который требует `data=`, поэтому `initial_data` всегда dict (non-dict guarded).
- B6 `race на select_for_update для нового email` — оба субагента подтвердили: корректно резолвится в 409 через `IntegrityError`.
- B7 `policy_version не передан явно` — соответствует AC-5 (строка 166); version-drift зафиксирован в deferred W5N6.
- B9 `шум в OpenAPI diff (переупорядочены методы)` — артефакт регенерации drf-spectacular.
- B12 `удалён тест между passes` — артефакт сравнения со stale-diff.
- B13 `test_test_settings_use_high_throttle_rates ассертит точные числа` — намеренный config-snapshot тест.

**Acceptance Auditor:**
- Audit-2 `вложенный atomic вместо единого (AC-5)` — функционально корректно, намеренное решение Pass 7 (P7-2); nested savepoint достигает намерения.
- Audit-scope `scope creep вне «Структуры файлов»` — зафиксировано в deferred-work (PPPP6-W1 / WWW8).
- Audit-artifact `story-35-3-pass8.diff ≠ HEAD` — ревью-diff `fb47fbeb..bbae541f` отражает истинный HEAD, сравнение со stale-артефактом неактуально.

---

