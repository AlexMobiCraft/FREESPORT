# Story 35.2: Чек-боксы согласий в формах регистрации (B2C и B2B)

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных
**Story ID:** 35.2
**Status:** review
**Priority:** High (часть compliance-пакета 152-ФЗ; разблокирует фактический сбор согласий пользователей)

---

## User Story

Как пользователь сайта,
я хочу при регистрации явно выразить согласие на обработку персональных данных
и опционально согласиться на маркетинговые рассылки,
чтобы FREESPORT мог обрабатывать мои данные согласно 152-ФЗ.

Как комплаенс-офицер,
я хочу, чтобы каждое согласие фиксировалось в `UserConsent` с IP / User-Agent / версией политики,
чтобы при проверке Роскомнадзора предоставить полный аудиторский след.

---

## Контекст

- Story 35.1 (`done`) уже реализовала: модель `UserConsent` (apps/common/models.py:587-653), read-only `UserConsentAdmin`, страницу `/privacy-policy` (Server Component, ISR 1ч).
- Эта история подключает фронт-энд формы регистрации (B2C `RegisterForm` и B2B `B2BRegisterForm`) к `UserConsent` через расширение `UserRegistrationView.post`.
- 35.3 (отдельно) — чек-бокс согласия в `SubscribeForm`. Не трогать в этой истории.
- 35.4 (отдельно) — cookie-баннер. Не трогать.

---

## Acceptance Criteria

### AC-1: Frontend — обязательный чекбокс согласия с ПДн в `RegisterForm` (B2C)

**Given** B2C форма регистрации `frontend/src/components/auth/RegisterForm.tsx`,
**When** форма отрендерена,
**Then** ПЕРЕД кнопкой submit есть чек-бокс с текстом
> «Я даю согласие на [обработку моих персональных данных](`/privacy-policy`) в соответствии с Политикой».

ссылка `/privacy-policy` открывается в новой вкладке (`target="_blank" rel="noopener noreferrer"`).

**Given** чек-бокс не отмечен,
**When** пользователь нажимает «Зарегистрироваться»,
**Then** показывается ошибка `«Необходимо согласие на обработку персональных данных»` под чек-боксом, submit блокируется (Zod валидация, аналогично остальным полям).

**Given** чек-бокс отмечен,
**When** пользователь успешно регистрируется,
**Then** в payload `RegisterRequest` отправляется `pdp_consent: true`.

---

### AC-2: Frontend — обязательный чекбокс согласия с ПДн в `B2BRegisterForm`

**Given** B2B форма регистрации `frontend/src/components/auth/B2BRegisterForm.tsx`,
**When** форма отрендерена,
**Then** в нижней секции «Пароль» (после поля `confirmPassword`) добавлен такой же чек-бокс ПДн с тем же текстом и ссылкой, как в AC-1.

Поведение валидации/блокировки submit и payload идентично AC-1.

---

### AC-3: Frontend — опциональный чекбокс маркетинговых рассылок (обе формы)

**Given** обе формы регистрации,
**When** форма отрендерена,
**Then** РЯДОМ с чек-боксом ПДн (ниже него) есть второй чек-бокс:
> «Я согласен(на) получать рекламные и информационные рассылки от FREESPORT».

**Given** маркетинговый чек-бокс,
**When** форма рендерится впервые,
**Then** чек-бокс **НЕ отмечен по умолчанию** (152-ФЗ требует явного opt-in, не opt-out).

**Given** пользователь не отмечает маркетинговый чек-бокс,
**When** регистрируется,
**Then** регистрация проходит успешно, в payload `marketing_consent: false`. Этот чек-бокс **не блокирует submit**.

---

### AC-4: Frontend — расширение `RegisterRequest` и Zod-схем

**Given** `frontend/src/types/api.ts:141-151` (interface `RegisterRequest`),
**When** добавлены новые поля,
**Then** интерфейс расширен:

```ts
export interface RegisterRequest {
  // ... существующие поля
  pdp_consent: boolean;          // обязательное, всегда true в реальном payload
  marketing_consent?: boolean;   // опциональное, default false
}
```

**Given** `frontend/src/schemas/authSchemas.ts`,
**When** обновлены схемы,
**Then** `registerSchema` и `b2bRegisterSchema` дополнены:

```ts
pdp_consent: z.literal(true, {
  errorMap: () => ({ message: 'Необходимо согласие на обработку персональных данных' }),
}),
marketing_consent: z.boolean().default(false),
```

`RegisterFormData` / `B2BRegisterFormData` инферятся автоматически. Дефолты в `useForm({ defaultValues: { pdp_consent: false, marketing_consent: false } })`.

---

### AC-5: Backend — `UserRegistrationSerializer` принимает поля согласий

**Given** `backend/apps/users/serializers.py:17-108` (`UserRegistrationSerializer`),
**When** добавлены два write-only поля,
**Then** сериализатор принимает:

```python
pdp_consent = serializers.BooleanField(write_only=True, required=True)
marketing_consent = serializers.BooleanField(write_only=True, required=False, default=False)
```

В `validate()` добавлена проверка:

```python
if not attrs.get("pdp_consent"):
    raise serializers.ValidationError(
        {"pdp_consent": "Необходимо согласие на обработку персональных данных."}
    )
```

В `create()` оба поля **извлекаются (`pop`) из `validated_data` ДО** `User.objects.create_user(...)` — они не должны попадать в модель `User`. Извлечённые значения сохраняются в `self._consent_flags` (или возвращаются view другим способом — см. AC-6).

`Meta.fields` дополнен: `..., "pdp_consent", "marketing_consent"`.

---

### AC-6: Backend — запись `UserConsent` при успешной регистрации

**Given** `backend/apps/users/views/authentication.py:107-135` (`UserRegistrationView.post`),
**When** регистрация прошла валидацию и пользователь создан,
**Then** в одной DB-транзакции (`transaction.atomic()`) создаются записи `UserConsent`:

1. **Всегда** (для подтверждённого `pdp_consent=True`):

```python
UserConsent.objects.create(
    user=user,
    consent_type="pdp_contract",
    ip_address=get_consent_ip_address(request),
    user_agent=sanitize_consent_user_agent(request.META.get("HTTP_USER_AGENT")),
)
```

`get_consent_ip_address(request)` использует существующий `get_client_ip(request)`, но перед записью валидирует и нормализует audit IP для PostgreSQL `inet`: отбрасывает `unknown`, private/loopback/link-local адреса, невалидные значения `X-Forwarded-For`, IPv6 zone-id и `host:port` с портом вне диапазона `1..65535`. Невалидный IP не ломает регистрацию и сохраняется как `NULL`.

2. **Только если `marketing_consent=True`** — вторая запись с `consent_type="marketing_email"` (остальные поля идентичны).

`policy_version` берётся из default модели (`"1.0"`) — не передавать явно.

**Given** регистрация падает после создания пользователя (например, при сбое записи `UserConsent`),
**When** `transaction.atomic()` откатывает изменения,
**Then** ни `User`, ни `UserConsent` не остаются в БД (no orphan rows).

**Note:** существующие `send_admin_verification_email.delay(...)` / `send_user_pending_email.delay(...)` в `serializer.create()` остаются как есть — рефакторить их под `transaction.on_commit()` **вне scope** (pre-existing техдолг, см. Dev Notes).

---

### AC-7: Backend тесты

**Файл:** `backend/tests/integration/test_auth_registration_consent.py` (новый, маркер `@pytest.mark.integration`).

Покрыть:

1. **`test_registration_requires_pdp_consent`** — POST `/api/v1/auth/register/` без `pdp_consent` → 400, `errors["pdp_consent"]` присутствует.
2. **`test_registration_rejects_pdp_consent_false`** — `pdp_consent=False` → 400.
3. **`test_retail_registration_creates_pdp_consent_record`** — `pdp_consent=True, marketing_consent=False` → 201; ровно одна запись `UserConsent` (`consent_type="pdp_contract"`) с FK на нового user; `ip_address` и `user_agent` заполнены.
4. **`test_retail_registration_with_marketing_creates_two_records`** — `pdp_consent=True, marketing_consent=True` → 201; две записи `UserConsent` с разными `consent_type`.
5. **`test_b2b_registration_creates_pdp_consent_record_for_pending_user`** — B2B регистрация (`role="wholesale_level1"`, `is_verified=False` после save) всё равно создаёт `UserConsent` (FK на `user`, даже если `is_active=False`).
6. **`test_consent_record_captures_ip_and_user_agent_from_proxy_headers`** — `HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8"` → `ip_address="1.2.3.4"`. `HTTP_USER_AGENT` длиной > 512 символов → обрезается до 512.
7. **`test_consent_records_have_default_policy_version`** — `policy_version == "1.0"`.

**Не дублируй**: токенные тесты (B2C получает access/refresh; B2B не получает) уже покрыты в `test_auth_registration_tokens.py` — добавь там `pdp_consent: True` к payload, чтобы тесты не упали из-за нового required-поля.

---

### AC-8: Frontend тесты

**Файл:** `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` (расширить существующий).
**Файл:** `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx` (создать новый — сейчас отсутствует, см. Dev Notes).

Покрыть:

1. **Чекбокс ПДн отображается с ссылкой** — `screen.getByRole('link', { name: /политикой/i })` ведёт на `/privacy-policy`, имеет `target="_blank"` и `rel="noopener noreferrer"`.
2. **Submit без отметки чекбокса ПДн** показывает ошибку «Необходимо согласие на обработку персональных данных», `authService.register` НЕ вызывается.
3. **Submit с отметкой чекбокса ПДн** вызывает `authService.register` с `pdp_consent: true` в payload.
4. **Маркетинговый чекбокс не блокирует submit** — без отметки регистрация проходит, payload содержит `marketing_consent: false`.
5. **Маркетинговый чекбокс с отметкой** — payload содержит `marketing_consent: true`.
6. **A11y** — оба чек-бокса имеют ассоциированные `<label>` (через `htmlFor`/`id` или вложенный `<label>`); ошибка валидации читается screen reader (`role="alert"` или `aria-describedby`).

---

## Технические требования и ограничения

### Backend (Django)

**Изменять:**

- `backend/apps/users/serializers.py` — `UserRegistrationSerializer` (AC-5)
- `backend/apps/users/views/authentication.py` — `UserRegistrationView.post` (AC-6); использовать существующий `get_client_ip(request)` (тот же файл, line 480) — НЕ дублировать.

**Создавать:**

- `backend/tests/integration/test_auth_registration_consent.py` (AC-7)

**НЕ изменять:**

- `backend/apps/common/models.py:587-653` (`UserConsent`) — модель готова из 35.1, поля и `CheckConstraint` уже соответствуют сценарию (`user OR session_key required`).
- `backend/apps/common/admin.py` (`UserConsentAdmin`) — read-only, не трогать.
- `backend/apps/common/migrations/0015_userconsent.py`, `0016_userconsent_review_fixes.py` — заморожены в 35.1.

**Импорты в `authentication.py`:**

```python
from django.db import transaction
from apps.common.models import UserConsent
```

### Frontend (Next.js 15 / React 19)

**Изменять:**

- `frontend/src/components/auth/RegisterForm.tsx` (AC-1, AC-3)
- `frontend/src/components/auth/B2BRegisterForm.tsx` (AC-2, AC-3)
- `frontend/src/schemas/authSchemas.ts` (AC-4)
- `frontend/src/types/api.ts:141-151` (`RegisterRequest`) (AC-4)
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` (AC-8)
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx` — **создать** (AC-8)

**НЕ изменять:**

- `frontend/src/components/ui/Checkbox/Checkbox.tsx` — компонент уже есть, использовать как есть. Принимает `label?: string`, но текст согласия содержит **inline-ссылку** на `/privacy-policy` — поэтому проп `label` **не использовать**, см. Dev Notes (вариант 2).
- `frontend/src/services/authService.ts` — поле `pdp_consent` поедет автоматически через `RegisterRequest` payload.
- `frontend/src/components/layout/Footer.tsx` — ссылка на `/privacy-policy` уже есть (line 51).

### API контракт (изменение)

```
POST /api/v1/auth/register/
Request body (новые поля):
{
  ...,
  "pdp_consent": true,           // required, MUST be true
  "marketing_consent": false     // optional, default false
}

Errors:
- 400 {"pdp_consent": ["Необходимо согласие на обработку персональных данных."]}
```

**`docs/api-spec.yaml` обновить НЕ требуется в этой истории** — спецификация автогенерируется через `drf-spectacular` (см. `@extend_schema(request=UserRegistrationSerializer, ...)` в view). После изменений запустить `python manage.py spectacular --file docs/api-spec.yaml` — дельта попадёт в коммит автоматически. Если есть закреплённый artefact в `frontend/src/types/` — регенерировать (см. project-context §4: «после правки serializer/view → обновить `docs/api/openapi.yaml` и `npm run generate:types`»).

---

## Структура файлов (изменения)

```
backend/
  apps/
    users/
      serializers.py               [MODIFY] — UserRegistrationSerializer + поля и валидация
      views/authentication.py      [MODIFY] — UserRegistrationView.post + transaction.atomic + UserConsent.objects.create
  tests/
    integration/
      test_auth_registration_consent.py  [CREATE] — 7 тестов из AC-7
      test_auth_registration_tokens.py   [MODIFY] — добавить pdp_consent: True в payload, чтобы существующие тесты не упали

frontend/
  src/
    components/
      auth/
        RegisterForm.tsx           [MODIFY] — два чекбокса перед submit + Zod hookup
        B2BRegisterForm.tsx        [MODIFY] — два чекбокса в секции после "Пароль"
        __tests__/
          RegisterForm.test.tsx    [MODIFY] — расширить кейсами из AC-8
          B2BRegisterForm.test.tsx [CREATE] — новый файл, минимальный набор кейсов AC-8
    schemas/
      authSchemas.ts               [MODIFY] — pdp_consent + marketing_consent в registerSchema и b2bRegisterSchema
    types/
      api.ts                       [MODIFY] — RegisterRequest расширить
```

---

## Реализация — ключевые snippets

### Backend: `UserRegistrationSerializer`

```python
class UserRegistrationSerializer(serializers.ModelSerializer):
    # ... existing password/password_confirm fields

    pdp_consent = serializers.BooleanField(write_only=True, required=True)
    marketing_consent = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = [
            "email", "password", "password_confirm",
            "first_name", "last_name", "phone", "role",
            "company_name", "tax_id",
            "pdp_consent", "marketing_consent",   # <— добавить
        ]
        # ... extra_kwargs

    def validate(self, attrs):
        # ... existing checks (passwords, b2b fields)
        if not attrs.get("pdp_consent"):
            raise serializers.ValidationError(
                {"pdp_consent": "Необходимо согласие на обработку персональных данных."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        # ВАЖНО: извлекаем consent-флаги ДО create_user
        pdp_consent = validated_data.pop("pdp_consent")
        marketing_consent = validated_data.pop("marketing_consent", False)

        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)

        # ... existing role/verification logic, user.save()

        # Возвращаем флаги через атрибут на user (вью забирает после save)
        user._marketing_consent = marketing_consent  # type: ignore[attr-defined]
        # pdp_consent всегда True (валидатор пропустил), его просто сохраняем
        return user
```

### Backend: `UserRegistrationView.post`

```python
from django.db import transaction
from apps.common.models import UserConsent

class UserRegistrationView(APIView):
    # ... existing decorators / extend_schema

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = serializer.save()

            client_ip = get_client_ip(request)
            user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512]
            ip_address = client_ip if client_ip != "unknown" else None

            UserConsent.objects.create(
                user=user,
                consent_type="pdp_contract",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if getattr(user, "_marketing_consent", False):
                UserConsent.objects.create(
                    user=user,
                    consent_type="marketing_email",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        # ... existing response_data construction (tokens for retail только)
        response_data = {...}
        return Response(response_data, status=status.HTTP_201_CREATED)
```

### Frontend: чек-бокс с inline-ссылкой (вариант для обеих форм)

```tsx
import Link from 'next/link';
import { Checkbox } from '@/components/ui/Checkbox/Checkbox';

// В JSX формы, ПЕРЕД <Button type="submit">:
<div className="space-y-2">
  <div className="flex items-start gap-3">
    {/* НЕ передаём label в Checkbox — у нас ReactNode-метка */}
    <Checkbox id="pdp-consent" {...register('pdp_consent')} disabled={isSubmitting} />
    <label
      htmlFor="pdp-consent"
      className="text-body-s text-text-primary cursor-pointer select-none"
    >
      Я даю согласие на{' '}
      <Link
        href="/privacy-policy"
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline hover:text-primary-hover"
      >
        обработку моих персональных данных
      </Link>{' '}
      в соответствии с Политикой
    </label>
  </div>
  {errors.pdp_consent?.message && (
    <p className="text-body-xs text-[var(--color-accent-danger)]" role="alert">
      {errors.pdp_consent.message}
    </p>
  )}
</div>

<div className="flex items-start gap-3">
  <Checkbox id="marketing-consent" {...register('marketing_consent')} disabled={isSubmitting} />
  <label
    htmlFor="marketing-consent"
    className="text-body-s text-text-primary cursor-pointer select-none"
  >
    Я согласен(на) получать рекламные и информационные рассылки от FREESPORT
  </label>
</div>
```

### Frontend: `authSchemas.ts` — обновлённые refines

```ts
// registerSchema: добавляем поля ВНУТРЬ z.object({...}) ДО первого .refine(...)
pdp_consent: z.literal(true, {
  errorMap: () => ({ message: 'Необходимо согласие на обработку персональных данных' }),
}),
marketing_consent: z.boolean().default(false),

// b2bRegisterSchema: те же поля, в z.object(...) перед закрывающим .refine
```

### Frontend: `RegisterRequest`

```ts
export interface RegisterRequest {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  phone: string;
  role?: string;
  company_name?: string;
  tax_id?: string;
  pdp_consent: boolean;          // NEW — обязательное
  marketing_consent?: boolean;   // NEW — опциональное
}
```

В `RegisterForm.tsx::onSubmit` и `B2BRegisterForm.tsx::onSubmit` при сборке `registerData` — пробросить:

```ts
pdp_consent: data.pdp_consent,           // всегда true (Zod literal)
marketing_consent: data.marketing_consent ?? false,
```

---

## GitNexus Impact (выполнено для шаблона)

- `Method:backend/apps/users/views/authentication.py:UserRegistrationView.post` — `risk: LOW`, upstream callers = 0 (вызывается только HTTP-клиентами).
- `Function:frontend/src/components/auth/RegisterForm.tsx:RegisterForm` — `risk: LOW`, upstream = 1 (`RegisterFormContent` в `frontend/src/app/(blue)/(auth)/register/page.tsx`). Изменения в форме не ломают вызывающий уровень — пропсы `RegisterFormProps` не трогаем.

**ПЕРЕД РЕАЛИЗАЦИЕЙ** разработчик должен повторно прогнать `gitnexus_impact` на каждый редактируемый символ (требование `CLAUDE.md` GitNexus Discipline) и сообщить blast radius пользователю.

---

## Dev Notes

### Почему `transaction.atomic()` вокруг user + consent

`UserConsent` — append-only audit log для 152-ФЗ. Если регистрация падает после создания `User`, запись согласия не должна остаться без user'а (хотя FK у нас `SET_NULL`, юридически согласие должно быть атомарно сцеплено с регистрацией). Wrap в `transaction.atomic()` гарантирует: либо оба ряда в БД, либо ни одного.

### Pre-existing техдолг (НЕ scope этой истории)

В `UserRegistrationSerializer.create()` уже вызываются `send_admin_verification_email.delay(user.id)` и `send_user_pending_email.delay(user.id)` — Celery-задачи запускаются ДО коммита транзакции. При откате транзакции worker увидит `User.DoesNotExist`. Это **pre-existing** — не правим в 35.2. Вынести в `transaction.on_commit(...)` — отдельная задача (см. `_bmad-output/planning-artifacts/tech-debt.md`).

### Почему `Checkbox.label` не используем

Существующий `Checkbox` принимает `label: string` и не поддерживает `ReactNode`. Нам нужна inline-ссылка `<Link>` внутри текста. Решение: не передавать проп `label`, а строить `<label htmlFor={id}>...</label>` внешним блоком (см. snippet выше). Расширять компонент `Checkbox` под `ReactNode label` — out of scope (затронет другие места использования и потребует impact-анализ).

### Почему B2B-форма не использует одну и ту же секцию из B2C

Формы `RegisterForm.tsx` и `B2BRegisterForm.tsx` имеют разную структуру (B2C — flat, B2B — секции «Контактное лицо» / «Реквизиты компании» / «Пароль»). Создавать общий компонент `<ConsentCheckboxes />` сейчас — преждевременная абстракция (DRY-cost > duplication-cost для двух usage-сайтов). Если в будущем появится 3-я форма с теми же чекбоксами, **тогда** выделять. Пока — повторить блок в обеих формах.

### Маркеры pytest

В новом `test_auth_registration_consent.py` — обязательно `@pytest.mark.integration` на классе/функциях (project-context §4). Без маркера тест выпадет из CI-фильтров `make test-integration`.

### Изоляция тестов (PostgreSQL constraints)

Тесты регистрации создают `User` с уникальным email. Использовать `get_unique_suffix()` или f-string с `time.time_ns()` для email (`f"consent_{time.time_ns()}@example.com"`), как в существующих интеграционных тестах. См. `backend/docs/testing-standards.md` §8.5.

### Существующие тесты, которые сломаются

- `backend/tests/integration/test_auth_registration_tokens.py` — оба теста делают `client.post("/api/v1/auth/register/", data, ...)` без `pdp_consent`. Они **упадут с 400** после внедрения AC-5. **Обязательно** в этой истории добавить `"pdp_consent": True` в `data` в обоих тестах. Не коммитить с красным CI.
- Любые backend integration-тесты, которые регистрируют пользователя через `/auth/register/` — найти грепом и добавить `pdp_consent: True`. Ниже — команда для разработчика:

```bash
grep -rn "/auth/register/" backend/tests/ backend/apps/ --include="*.py"
```

### Frontend — существующие тесты `RegisterForm.test.tsx`

Существующие кейсы вроде `'should fill all fields and submit'` после внедрения AC-1 будут падать с ошибкой `«Необходимо согласие на обработку персональных данных»`. **Обязательно** в каждом кейсе с успешным submit — отмечать чекбокс ПДн в setup. Шаблон:

```tsx
const pdpCheckbox = screen.getByRole('checkbox', { name: /согласие на обработку/i });
await user.click(pdpCheckbox);
```

### `policy_version` — почему не передаём

Default модели `"1.0"`. Если в будущем потребуется версионировать — вынести в settings (`PRIVACY_POLICY_VERSION`) и читать в view. На текущий момент — out of scope (Decision 3a в Review Findings 35.1: «оставить 20-символьный `1.0`/`1.1`, SemVer не нужен»).

---

## Definition of Done

- [x] AC-1..AC-8 реализованы.
- [x] Backend unit suite зелёный через Docker (`pytest -v -m unit --cov=apps --cov-report=term-missing`): 697 passed, 12 skipped, 1509 deselected. Backend integration suite: 607 passed; **10 failures isolated в `test_management_commands/test_import_customers.py` — environmental issue (пустая `data/import_1c/contragents/` в локальной checkout), не регрессия от 35.2**.
- [x] Новые тесты `test_auth_registration_consent.py` зелёные (32 кейса: 7 AC + review patches для IP/User-Agent/error-contract edge cases + Pass 7 IPv4-mapped IPv6 + Pass 8 surrogate sanitization).
- [x] Существующий `test_auth_registration_tokens.py` обновлён и зелёный.
- [x] `npm run test -- src/components/auth/__tests__/RegisterForm.test.tsx` зелёный (33 кейса).
- [x] `npm run test -- src/components/auth/__tests__/B2BRegisterForm.test.tsx` зелёный (15 кейсов; auth component bundle `RegisterForm` + `B2BRegisterForm` = 48/48).
- [x] `npm run build` (frontend) прошёл с явным локальным `NEXT_PUBLIC_API_URL_INTERNAL=http://localhost:8001/api/v1`; без этой переменной локальный shell пытается prerender `/privacy-policy` через Docker hostname `backend` и падает `ENOTFOUND backend`.
- [x] OpenAPI спецификация регенерирована (`python manage.py spectacular --file docs/api-spec.yaml`), если используется generated types на фронте — `npm run generate:types` прогнан.
- [x] `gitnexus_detect_changes()` подтверждает: затронуты только символы из списка UPDATE/CREATE плюс задокументированный extra-fix `PrivacyPolicyPage/fetchPrivacyPolicy` (см. Debug Log) и косметика GitNexus stats в `AGENTS.md`/`CLAUDE.md` (auto-update).
- [x] Покрытие критичного registration path: ранее `apps/users/views/authentication.py::UserRegistrationView.post` = **100%**; Pass 3 добавил targeted coverage для `normalize_consent_ip`, `sanitize_log_value`, `get_consent_ip_address`, frontend validation parser и inline field errors.
- [x] Manual QA через API (dev-стек, Docker): (1) без `pdp_consent` → 400 `{"pdp_consent":["Необходимо согласие на обработку персональных данных."]}`; (2) B2C `pdp+marketing=true` → 201 + access/refresh JWT, в БД 2 `UserConsent` (`pdp_contract` + `marketing_email`); (3) B2B wholesale → 201 без токенов, `is_active=False`, 1 `UserConsent` (`pdp_contract`); (4) `X-Forwarded-For: 1.2.3.4, 10.0.0.1` корректно извлекается как `ip_address=1.2.3.4`, non-global IP больше не пишутся в audit; (5) `policy_version="1.0"` по умолчанию. UI рендеринг чекбоксов и валидация покрыты frontend-тестами — визуальная инспекция через браузер пропущена как избыточная.

---

### Review Findings

- [x] [Review][Patch] B2B pending registration can fail after successful backend response because `B2BRegisterForm` always calls `refreshToken()` before showing pending state [frontend/src/components/auth/B2BRegisterForm.tsx:84] — resolved: pending response returns immediately before refresh; regression covered.
- [x] [Review][Patch] Missing `pdp_consent` returns DRF default required-field error instead of the story API-contract consent message [backend/apps/users/serializers.py:29] — resolved: serializer `required` error now uses consent contract message; integration test asserts exact text.
- [x] [Review][Patch] Invalid `X-Forwarded-For` can make `UserConsent.ip_address` insert fail and roll back otherwise valid registration [backend/apps/users/views/authentication.py:118] — resolved: consent audit IP is validated before DB insert; invalid external IP is stored as `NULL`.
- [x] [Review][Patch] Privacy-policy link is nested inside the clickable checkbox label and can toggle consent when the user tries to read the policy [frontend/src/components/auth/RegisterForm.tsx:267] — resolved: link is outside checkbox labels; checkbox accessible name preserved via `aria-labelledby`.
- [x] [Review][Patch] B2B 400-error handling drops backend `pdp_consent` validation messages and shows a generic validation error [frontend/src/components/auth/B2BRegisterForm.tsx:110] — resolved: B2B form surfaces `pdp_consent` and first backend validation message.
- [x] [Review][Defer] B2B email Celery tasks are queued inside the registration transaction before consent rows are committed [backend/apps/users/serializers.py:113] — deferred, pre-existing and explicitly out of scope for 35.2
- [x] [Review][Defer] Deleting a user with `UserConsent(user=..., session_key="")` can violate `userconsent_user_or_session_required` after `on_delete=SET_NULL` [backend/apps/common/models.py:595] — deferred, pre-existing 35.1 model lifecycle issue

#### Pass 2 (2026-05-10) — review of [Review][Patch] closure diff

**Patch items (включают резолюцию decision-items от 2026-05-11):**

- [x] [Review][Patch] **[Decision-1 resolved → Опция 3]** Заменить `aria-labelledby` + 3 фрагментированных `<label>` на единый wrapping `<label htmlFor=…>` с `<Link>` внутри, на котором повешен `onClick={(e) => e.stopPropagation()}` — superseded by Pass 3 patch: ссылка вынесена из `<label>`, работает как native Next `<Link>`, checkbox accessible name сохранён через `aria-labelledby` и покрыт component-тестами [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] **[Decision-2 resolved → Опция 2]** В B2B pending-ветке вызывать `onSuccess?.()` ПЕРЕД `setIsPending(true); return;`, но НЕ вызывать `router.push(redirectUrl)` — resolved: pending branch вызывает `onSuccess` и остаётся на inline pending state; regression covered [frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] `parse_ip_address` принимает IPv6 zone-id (`fe80::1%eth0`) и не нормализует bracketed `[2001:db8::1]:port` — resolved: `normalize_consent_ip` отбрасывает zone-id, нормализует bracketed IPv6/IPv4:port и валидирует перед записью [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] Пустой/whitespace первый hop `X-Forwarded-For` (`", 1.2.3.4"` или `" "`) → `None` вместо fallback на `REMOTE_ADDR` — resolved: blank first hop falls back to `REMOTE_ADDR`; integration test covered [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] `REMOTE_ADDR == "unknown"` молча возвращает `None` без warning-лога — resolved: unknown/invalid audit IP пишет warning с sanitized extra [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] `getValidationMessage` с hard-coded priority `['pdp_consent', 'tax_id', 'password']` скрывает реальные ошибки backend — resolved: B2B показывает первое backend validation message в порядке ответа, без hard-coded pdp priority [frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] User-Agent slice `[:512]` по символам может оставить lone surrogates — resolved: `sanitize_consent_user_agent` удаляет невалидные UTF-8 surrogate chars до сохранения [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] `pdp_consent.error_messages` покрывает только ключ `required`, но не `invalid`/`null` — resolved: `required`, `invalid`, `null` используют единый русский contract message [backend/apps/users/serializers.py]
- [x] [Review][Patch] Тип `Record<string, string[] | string> & { detail?: string }` не моделирует вложенные DRF-ошибки и `non_field_errors` — resolved: frontend validation parser рекурсивно обрабатывает strings/arrays/objects и nested errors [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] Backend `pdp_consent` 400-ошибка устанавливает только `apiError` баннер; `setError('pdp_consent', ...)` не вызывается — resolved: B2B устанавливает inline RHF error на `pdp_consent`; component test covered [frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] B2C `RegisterForm` НЕ получил эквивалентного surfacing backend `pdp_consent` ошибки — resolved: B2C использует тот же validation parser и `setError('pdp_consent', ...)`; component test covered [frontend/src/components/auth/RegisterForm.tsx]
- [x] [Review][Patch] `test_registration_ignores_invalid_forwarded_ip_for_consent_record` ассертит только `consent.ip_address is None`, но не assertит, что валидный второй IP `5.6.7.8` НЕ был использован, и нет green-path теста для валидного XFF — resolved: добавлены stronger invalid-XFF assertions и green-path normalization tests [backend/tests/integration/test_auth_registration_consent.py]
- [x] [Review][Patch] DoD line 533 указывает `400 {"pdp_consent":["Обязательное поле."]}` — resolved: DoD обновлён на контрактное сообщение «Необходимо согласие на обработку персональных данных.» [_bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md]
- [x] [Review][Patch] DoD line 528 говорит «B2BRegisterForm.test.tsx (7 кейсов)», но patched-файл содержит больше — resolved: DoD обновлён на 10 B2B кейсов и 40/40 auth component bundle [_bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md]
- [x] [Review][Patch] `extra={"client_ip": client_ip}` в warning-логе передаёт сырое значение из X-Forwarded-For без truncate/sanitize — resolved: log extra проходит CR/LF/ANSI escaping + truncate; integration test covered [backend/apps/users/views/authentication.py]

**Deferred (pre-existing or out of scope):**

- [x] [Review][Defer] X-Forwarded-For trusted-proxy allowlist отсутствует — `get_client_ip` слепо доверяет leftmost значение, валидно сформированный, но spoofed IP (например, `1.2.3.4`) сохраняется как audit IP [backend/apps/users/views/authentication.py:516-521] — deferred, project-wide infra issue, требует отдельной story по trusted-proxy конфигурации
- [x] [Review][Defer] `get_consent_ip_address` лежит в `apps/users/views/authentication.py` — для Story 35.3 (`SubscribeForm consent`) удобнее иметь его в `apps/common/utils.py` [backend/apps/users/views/authentication.py:524-544] — deferred, рефакторинг при стартe Story 35.3
- [x] [Review][Defer] Click на текст внешнего обёртки (между фрагментами `<label>`) больше не toggle-ит чекбокс — superseded by Pass 3 patch: visible label-фрагменты снова связаны с checkbox через `htmlFor`, а ссылка остаётся отдельным native link. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Defer] Дубликат сообщения `«Необходимо согласие на обработку персональных данных.»` в `error_messages={"required"}` и в теле `validate()` — drift при будущих правках [backend/apps/users/serializers.py:29-33, 68-69 + test_auth_registration_consent.py:66] — deferred, кодовая полировка, экстракт в константу при следующем заходе

#### Pass 3 (2026-05-11) — adversarial + edge case + acceptance review

**Acceptance Auditor:** ✅ Все AC-1..AC-8 и 15 Pass 2 [Review][Patch] items соответствуют спеке. Отклонений нет. Инварианты project-context.md соблюдены, файлы из «НЕ ИЗМЕНЯТЬ» не тронуты.

**Blind Hunter + Edge Case Hunter:** 50 первичных findings, после дедупликации — 30 уникальных. Из них 12 dismiss как noise/no-defect/theoretical. Остаётся:

**Decision-needed:**

- [x] [Review][Decision] **[resolved → Опция 3]** DRF `BooleanField` принимает `pdp_consent=1/"yes"/"on"/"t"` как `True` — решение: оставить DRF default из AC-5 и явно зафиксировать поведение тестом `test_registration_accepts_drf_truthy_pdp_consent_values_by_decision` для `1/"yes"/"on"/"t"`. [backend/apps/users/serializers.py:31-39, backend/tests/integration/test_auth_registration_consent.py]

**Patches (Pass 3):**

- [x] [Review][Patch] `onClick` handler на privacy-policy `<Link>` слишком сложный и silent-fail-ит — resolved: ссылка вынесена из `<label>`, работает как native Next `<Link>` без `preventDefault/window.open`; имя checkbox сохранено через `aria-labelledby`, label-текст по-прежнему toggles checkbox. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] `normalize_consent_ip` возвращает исходную строку вместо `str(parse_ip_address(...))` и принимает non-global IP — resolved: IP canonicalized через `str(parse_ip_address(...))`, scoped/non-global/private/loopback/link-local адреса отклоняются с warning, валидные IPv4/IPv6 с port нормализуются. [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] `sanitize_log_value` неполный: пропускает NULL byte `\x00` (обрушит Sentry/syslog/journald), Unicode line separators (U+2028, U+2029), BiDi override (U+202E), zero-width spaces; truncation после replace может разрезать `\\r\\n` пополам — resolved: unsafe chars экранируются, truncation выполняется по token boundary. [backend/apps/users/views/authentication.py]
- [x] [Review][Patch] `getValidationMessage` рекурсия без depth-limit и без WeakSet seen-objects guard — resolved: B2C/B2B parser получил `MAX_VALIDATION_MESSAGE_DEPTH`, `WeakSet` seen guard и тесты на cyclic payload. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] Asymmetric inline `setError` для backend validation — resolved: backend field errors рекурсивно маппятся в RHF `setError` для известных полей; numeric-like keys демотируются после named keys; email/tax_id/password покрыты inline assertions. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] Checkbox не имеет `aria-invalid={!!errors.pdp_consent}` и визуально не подсвечивается как error — resolved: PDP checkbox получает `aria-invalid`, `aria-describedby` и danger border/background при ошибке; component-тесты проверяют SR-visible state. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Patch] B2B `onSuccess` callback вызывается ПЕРЕД `setIsPending(true)` — resolved: pending state рендерится первым, `onSuccess` вызывается через `useEffect` после inline pending render; JSDoc обновлён, тест проверяет order и `mockPush.not.toHaveBeenCalled()`. [frontend/src/components/auth/B2BRegisterForm.tsx, B2BRegisterForm.test.tsx]
- [x] [Review][Patch] DoD/документация inconsistencies — resolved: DoD обновлён на 27 backend consent tests, 11 B2B tests, 43/43 auth component bundle и Pass 3 targeted helper coverage. [_bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md]
- [x] [Review][Patch] Test improvements — resolved: усилены assertions для nested inline `tax_id`, `mockPush.not.toHaveBeenCalled()`, whitespace-only XFF, UA surrogate expected length без magic `507`, native privacy link behavior и cyclic parser payloads. [frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx, RegisterForm.test.tsx, backend/tests/integration/test_auth_registration_consent.py]

**Deferred (pre-existing, accepted trade-off, или out-of-scope):**

- [x] [Review][Defer] HTML5 spec discouraged: `<a>` inside `<label>` + nested label structure — superseded by Pass 3 patch: ссылка вынесена из `<label>`, checkbox accessible name сохранён через `aria-labelledby`. [frontend/src/components/auth/RegisterForm.tsx, B2BRegisterForm.tsx]
- [x] [Review][Defer] Race на одинаковый email при concurrent registration → `IntegrityError` → HTTP 500 вместо 409 — pre-existing, не введено 35.2 [backend/apps/users/views/authentication.py:115-163] — deferred, pre-existing
- [x] [Review][Defer] `validate_email` case-sensitive (`User.objects.filter(email=value)` без `__iexact`) — pre-existing [backend/apps/users/serializers.py:62-66] — deferred, pre-existing
- [x] [Review][Defer] B2B-форма шлёт `ogrn`/`legal_address`, но `UserRegistrationSerializer.Meta.fields` их не содержит → DRF молча игнорирует, реквизиты не сохраняются — pre-existing [backend/apps/users/serializers.py:42-56] — deferred, pre-existing
- [x] [Review][Defer] `get_consent_ip_address` пишет WARNING на каждом legit no-IP контексте (internal job / health-check без headers) → log noise, threshold alerting тригерится — Pass 2 conscious decision (patch #5: «unknown REMOTE_ADDR молча возвращал None без warning» был resolved), можно понизить до INFO если в продакшене станет шумно [backend/apps/users/views/authentication.py:578-580] — deferred, Pass 2 conscious decision
- [x] [Review][Defer] Celery `delay()` в `UserRegistrationSerializer.create()` не обёрнут в `transaction.on_commit(...)` — при откате транзакции worker увидит `User.DoesNotExist` или отправит email о rolled-back user — pre-existing, явно out of scope (см. Dev Notes line 477-479 + Pass 1 defer #6) [backend/apps/users/serializers.py:113-125] — deferred, pre-existing, already in tech-debt.md

---

## Связанные истории / документы

- **Зависит от:** 35.1 (`done`) — `UserConsent` модель, `/privacy-policy` страница.
- **Блокирует:** 35.3 (чекбокс в `SubscribeForm` — анонимные согласия через `session_key`), 35.4 (cookie-баннер).
- **Архитектурный референс:** `docs/architecture/02-data-models.md:715-732` (схема `UserConsent`).
- **Регуляторное обоснование:** `docs/prd/requirements.md` NFR5 (соответствие 152-ФЗ).
- **Образец паттерна для API+admin модели:** Story 35.1 (`_bmad-output/implementation-artifacts/Story/35-1-privacy-policy-page-and-consent-model.md`).
- **Project context:** `project-context.md` §3 (доменные инварианты), §4 (тестирование), §5 (GitNexus discipline), §7 (frontend Next.js 15 / React 19 паттерны).

---

## References

- [Source: docs/architecture/02-data-models.md:715-754] — определение `UserConsent`
- [Source: docs/architecture/04-component-structure.md:152-158] — `apps/common` структура
- [Source: backend/apps/common/models.py:587-653] — реализация `UserConsent` после 35.1 patches
- [Source: backend/apps/users/views/authentication.py:107-135] — текущий `UserRegistrationView.post`
- [Source: backend/apps/users/views/authentication.py:480-498] — `get_client_ip(request)` (использовать как есть, не дублировать)
- [Source: backend/apps/users/serializers.py:17-108] — текущий `UserRegistrationSerializer`
- [Source: frontend/src/components/auth/RegisterForm.tsx:1-257] — B2C форма
- [Source: frontend/src/components/auth/B2BRegisterForm.tsx:1-307] — B2B форма
- [Source: frontend/src/schemas/authSchemas.ts:34-146] — `registerSchema` / `b2bRegisterSchema`
- [Source: frontend/src/types/api.ts:141-157] — `RegisterRequest` / `RegisterResponse`
- [Source: frontend/src/components/ui/Checkbox/Checkbox.tsx:12-117] — UI Checkbox (использовать без проп `label`)
- [Source: backend/tests/integration/test_auth_registration_tokens.py] — существующие тесты, нуждаются в `pdp_consent: True`
- [Source: project-context.md §3 «Доменные инварианты»] — DRF defaults, B2B verification, snake_case API

---

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

1. Расширить backend-контракт регистрации: принять `pdp_consent` и `marketing_consent`, валидировать обязательное согласие ПДн и сохранять аудиторские записи `UserConsent` в одной транзакции с созданием пользователя.
2. Обновить B2C/B2B формы регистрации: добавить чекбоксы, ссылку на `/privacy-policy`, Zod-валидацию и передачу consent-полей в API payload.
3. Закрыть тестами backend и frontend: новые интеграционные кейсы согласий, обновление существующих регистрационных тестов, компонентные и schema-тесты.
4. Синхронизировать API-контракт: регенерировать OpenAPI и generated TypeScript-типы.

### Debug Log References

- GitNexus impact перед изменениями: `UserRegistrationSerializer`, `UserRegistrationView.post`, `RegisterForm`, `B2BRegisterForm`, `registerSchema`, `b2bRegisterSchema` - LOW; `RegisterRequest` - CRITICAL из-за центрального `api.ts`, фактическое изменение ограничено интерфейсом payload.
- GitNexus detect-changes после реализации: 20 файлов, 27 символов, 7 affected flows, общий risk `high`; кроме story-символов зафиксирован отдельный fix `PrivacyPolicyPage/fetchPrivacyPolicy`.
- RED frontend: таргетные тесты consent-поведения падали до реализации из-за отсутствующих чекбоксов и payload-полей.
- Backend test stack изначально не был поднят; для тестов подняты `db` и `redis` из `docker-compose.test.yml`.
- Полный frontend suite выявил регрессию `/privacy-policy` для 5xx/network ошибок; исправлено отдельно после GitNexus impact по `PrivacyPolicyPage`.
- **Финальный verification-проход (Sonnet, 2026-05-10):**
  - `make test-unit` (Docker, full suite): **697 passed, 12 skipped, 1508 deselected** за 4:03 min ✅
  - `make test-integration` (Docker, full suite): **606 passed, 10 failed, 2 skipped, 1599 deselected** за 13:44 min. Все 10 падений локализованы в `tests/integration/test_management_commands/test_import_customers.py` (CommandError "Поддиректория contragents не найдена в /app/data/import_1c") — environmental issue: локальный `data/import_1c/` пуст (XML-данные 1С не в репо). Pre-existing — `git log` показывает последние правки файла = black-форматирование, не связаны со story 35.2.
  - Story-таргетные integration-тесты (consent + tokens + emails + verification + epic_28 regression): **20/20 ✅**
  - Story-таргетные unit-тесты (`test_user_verification.py`): **4/4 ✅**
  - Frontend: `RegisterForm.test.tsx` (29) + `B2BRegisterForm.test.tsx` (5) + `authSchemas.test.ts` (27) = **61/61 ✅**
  - Coverage `UserRegistrationView.post` = 100% (missing-lines в `coverage`-отчёте все вне scope метода: Login/PasswordReset/Logout views).
  - `npx gitnexus detect-changes --scope all`: 24 файла, 35 символов, 7 flows, risk `high`. Все code-symbol изменения в scope (serializers/views/components/schemas/types). Out-of-scope: `PrivacyPolicyPage/fetchPrivacyPolicy` (документирован выше как отдельный fix), `AGENTS.md`/`CLAUDE.md` (косметика GitNexus stats: 8332→8354 символа).
  - Manual QA через `curl` к dev-стеку (`localhost:8001`) + `python manage.py shell` для проверки `UserConsent` в реальной БД: все 5 сценариев из DoD прошли (см. DoD пункт Manual QA).
- **Side-find (out of scope, для тех-долга):** при попытке cleanup QA-пользователей через `User.objects.filter(...).delete()` получили `IntegrityError` на `userconsent_user_or_session_required` — `on_delete=SET_NULL` обнуляет `user_id`, но `session_key=""` нарушает constraint. Реальное удаление пользователей с consent-записями в текущем дизайне модели требует двушагового сценария (сначала `UserConsent.objects.filter(user_id=...).delete()`). Это pre-existing наследие 35.1, не блокирует 35.2.
- **Review patch pass (GPT-5 Codex, 2026-05-10):**
  - GitNexus impact перед patch: `UserRegistrationSerializer`, `UserRegistrationView.post`, `get_client_ip`, `RegisterForm`, `B2BRegisterForm` — LOW; affected frontend flows: `RegisterPage`, `B2BRegisterPage`; backend impact ограничен регистрацией и logout IP logging.
  - RED: `test_auth_registration_consent.py` падал 2/8 (required-message + invalid inet), auth component tests падали 5/36 (link-in-label, B2B refresh pending, B2B backend `pdp_consent` message).
  - GREEN targeted: `test_auth_registration_consent.py` 8/8; `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` 36/36; story-related backend integration bundle 20/20.
  - Full regression: backend unit 697 passed, 12 skipped; backend integration 607 passed, 10 known environmental failures in `test_management_commands/test_import_customers.py`; full `npm run test` passed; `npx tsc --noEmit` passed; scoped ESLint for changed auth files passed; `python manage.py check`, `black --check`, `flake8`, `prettier --check`, `git diff --check` passed.
  - `npm run build` passed with `NEXT_PUBLIC_API_URL_INTERNAL=http://localhost:8001/api/v1`; first local build without this env failed on `/privacy-policy` `ENOTFOUND backend`, unrelated to auth patch.
  - `npm run lint` full still fails on pre-existing project files outside this patch (`next-env.d.ts` triple-slash reference and `scripts/convert-svg-to-favicon.js` CommonJS `require`); scoped ESLint for changed files is clean.
  - `npx gitnexus detect-changes --scope all`: 9 files, 20 symbols, 3 affected flows, risk `medium`; affected flows limited to registration pages.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
- **Review patch pass 2 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus impact перед patch: `UserRegistrationView.post`, `UserRegistrationSerializer.create`, `get_consent_ip_address`, `UserRegistrationSerializer.validate`, `RegisterForm`, `B2BRegisterForm`, `onSubmit` handlers — LOW; affected flows limited to registration pages.
  - RED backend: `test_auth_registration_consent.py` падал 8/16 на invalid/null `pdp_consent`, blank/port/zone-id IP normalization, unknown-IP warning и lone-surrogate User-Agent.
  - RED frontend: auth component bundle падал 7/40 на link-in-label, B2B pending `onSuccess`, backend `pdp_consent` inline errors и nested validation parsing.
  - GREEN targeted: `test_auth_registration_consent.py` **17/17**; `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` **40/40**.
  - Static checks: `python manage.py check`, `black --check`, `flake8`, `prettier --check`, scoped `eslint --max-warnings=0`, `npx tsc --noEmit` passed.
  - Full regression: backend unit **697 passed, 12 skipped**; backend integration **616 passed, 10 failed, 2 skipped** — all 10 failures remain isolated in `test_management_commands/test_import_customers.py` because local `/app/data/import_1c/contragents/` is absent; full frontend `npm run test -- --run` passed.
  - Frontend production build: `npm run build` passed with `NEXT_PUBLIC_API_URL_INTERNAL=http://localhost:8001/api/v1` and `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`; only existing Next/ESLint workspace-root warnings remained.
  - `npx gitnexus detect-changes --scope all`: 11 files, 34 symbols, 3 affected flows, risk `medium`; affected flows limited to `RegisterPage` / `B2BRegisterPage`.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
- **Review patch Pass 3 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus index refreshed before impact (`npx gitnexus analyze`): 8375 nodes, 13697 edges, 300 flows; `AGENTS.md`/`CLAUDE.md` stats auto-updated.
  - GitNexus impact перед patch: `UserRegistrationSerializer`, `UserRegistrationView.post`, `normalize_consent_ip`, `sanitize_log_value`, `get_consent_ip_address`, `RegisterForm`, `B2BRegisterForm`, B2C/B2B `getValidationMessage` — LOW; affected frontend flows limited to `RegisterPage` / `B2BRegisterPage`, backend impact limited to registration consent audit.
  - RED backend: `test_auth_registration_consent.py` падал 4/27 на private/loopback/link-local IP и log sanitization.
  - GREEN backend: `test_auth_registration_consent.py` **27/27**; `python manage.py check`, `black --check`, `flake8` passed.
  - RED frontend: auth component bundle падал 12/43 на native privacy link, `aria-invalid`, cyclic parser, inline field errors и B2B pending/onSuccess order.
  - GREEN frontend: `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` **43/43**; полный `npm run test -- --run`, scoped ESLint, Prettier check и `npx tsc --noEmit` passed.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
  - Final hygiene: `git diff --check` passed; `npx gitnexus detect-changes --scope all` — 10 files, 40 symbols, 8 affected flows, risk `high`; actual affected flows are limited to B2C/B2B registration, `UserRegistrationView.post` consent audit helpers, and GitNexus stats in `AGENTS.md`/`CLAUDE.md`.
- **Review patch Pass 4 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus impact перед patch: `B2BRegisterForm`, `registerSchema`, `b2bRegisterSchema`, `normalize_consent_ip`, `IPV4_WITH_PORT_RE` — LOW; direct frontend blast radius limited to `B2BRegisterContent` / `B2BRegisterPage`, backend blast radius limited to consent audit in registration.
  - RED frontend: `B2BRegisterForm.test.tsx` падал на verified B2B path, где `refreshToken()` превращал уже успешную регистрацию в ошибку; `npx tsc --noEmit` падал на отсутствующих input/output schema-типах и `pdp_consent` literal-type contract.
  - RED backend: новый `test_registration_rejects_forwarded_ipv4_with_invalid_port_for_consent_record` падал, потому `1.2.3.4:99999` сохранялся как `1.2.3.4`.
  - GREEN targeted: `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` + `authSchemas.test.ts` **74/74**; `test_auth_registration_consent.py` **28/28**; `npx tsc --noEmit`, scoped ESLint, Prettier check, `python manage.py check`, `black --check`, `flake8` passed.
  - Full regression completed for changed surfaces: full frontend `npm run test -- --run` passed; backend unit suite **697 passed, 12 skipped, 1529 deselected**. Full backend integration was not rerun in this pass because story remains `in-progress` pending product/architect decision; story-specific integration coverage is green.
  - Decision resolved by product/user: выбран вариант 4 — не расширять Story 35.2, явно оставить текущее поведение вне scope и вынести сохранение B2B `ogrn` / `legal_address` в отдельное ТЗ + backlog story. Durable note added to `deferred-work.md`.
- **Review patch Pass 5 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus impact перед patch: `normalize_consent_ip`, `get_consent_ip_address`, `RegisterForm`, `B2BRegisterForm` — LOW; affected flows limited to `UserRegistrationView.post`, `RegisterPage`, `B2BRegisterPage`.
  - RED backend: `test_registration_rejects_bracketed_ipv6_with_invalid_port_for_consent_record` падал, потому `[2606:4700:4700::1111]:99999` сохранялся как `2606:4700:4700::1111`.
  - GREEN targeted: `test_auth_registration_consent.py` **29/29**; `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` **46/46**; `python manage.py check`, `black --check`, `flake8`, `npx tsc --noEmit`, scoped ESLint, Prettier check passed.
  - Full regression: full frontend `npm run test -- --run` passed; backend unit suite **697 passed, 12 skipped, 1530 deselected**; backend integration **628 passed, 2 skipped, 10 failed** — all 10 failures remain isolated in `test_management_commands/test_import_customers.py` because `/app/data/import_1c/contragents` is absent.
  - `git diff --check` passed; `npx gitnexus detect-changes --scope all` — 10 files, 11 symbols, 3 affected flows, risk `medium`; affected flows limited to registration validation parser and consent IP normalization.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
- **Review patch Pass 6 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus impact перед patch: `RegisterForm` и `B2BRegisterForm` — LOW; affected flows limited to `RegisterPage` / `B2BRegisterPage`.
  - Coverage follow-up добавлен для B2B pending user с `marketing_consent=True`; тест сразу зелёный, потому backend implementation уже создавал обе consent-записи, а Pass 6 issue был gap в regression coverage.
  - Frontend refactor убрал controlled `checked={watch(...)}` с PDP/marketing checkbox-ов в B2C/B2B формах; RHF `register()` остаётся единственным источником состояния.
  - Targeted verification: `test_auth_registration_consent.py` **30/30**, `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` **46/46**, `npx tsc --noEmit`, scoped ESLint, `black --check`, `flake8`, `git diff --check` passed.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
- **Review patch Pass 7 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus index refreshed (`npx gitnexus analyze`), impact перед patch: `normalize_consent_ip`, `get_client_ip`, `applyBackendFieldErrors`, `registerSchema`, `b2bRegisterSchema`, `RegisterForm`, `B2BRegisterForm`, `UserRegistrationSerializer` — LOW; affected flows limited to `UserRegistrationView.post`, `LogoutView.post`, `RegisterPage`, `B2BRegisterPage`.
  - RED frontend: `authSchemas.test.ts` падал 2/31 из-за frontend PDP-message без точки; `B2BRegisterForm.test.tsx` падал на nested `tax_id` inline mapping.
  - RED backend: новый `test_registration_normalizes_ipv4_mapped_ipv6_for_consent_record` падал, потому `::ffff:8.8.8.8` сохранялся как IPv6-mapped value вместо canonical IPv4.
  - GREEN targeted: `test_auth_registration_consent.py` **31/31**; `authSchemas.test.ts` + `RegisterForm.test.tsx` + `B2BRegisterForm.test.tsx` **79/79**.
  - Static/full regression: full frontend `npm run test` passed; frontend `npm run build` passed with `NEXT_PUBLIC_API_URL_INTERNAL=http://localhost:8001/api/v1` / `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`; backend unit **697 passed, 12 skipped**; backend integration without known environmental `test_import_customers.py` blocker **628 passed, 2 skipped**; `python manage.py check`, `black --check`, `flake8`, `npx tsc --noEmit`, scoped ESLint, Prettier check passed.
  - `npx gitnexus detect-changes --scope all`: 14 files, 10 symbols, 7 affected flows, risk `high`; фактические affected flows ограничены registration pages, consent IP normalization helpers и GitNexus stats в `AGENTS.md`/`CLAUDE.md`.
  - Frontend Docker container restarted after `frontend/src/*` changes: `freesport-frontend` restarted successfully.
- **Review patch Pass 8 closure (GPT-5 Codex, 2026-05-11):**
  - GitNexus impact перед patch: `sanitize_log_value` — LOW; direct caller `get_consent_ip_address`, транзитивный affected flow `UserRegistrationView.post`.
  - RED backend: `test_registration_sanitizes_surrogate_from_invalid_ip_warning_log` падал, потому `\udcff` оставался в `record.client_ip`.
  - GREEN targeted: новый surrogate regression test passed; весь `test_auth_registration_consent.py` **32/32**.
  - Story-related regression: `test_auth_registration_tokens.py` **2/2**; `python manage.py check` passed.
  - Static checks: `black --check apps/users/views/authentication.py tests/integration/test_auth_registration_consent.py`, `flake8 apps/users/views/authentication.py tests/integration/test_auth_registration_consent.py` и `git diff --check` по изменённым файлам passed.
  - `npx gitnexus detect-changes --scope all`: 5 files, 1 changed symbol (`sanitize_log_value`), 1 affected flow (`Post → Sanitize_log_value`), risk `medium`; affected runtime scope ограничен registration consent audit warning-log path.
  - Широкий backend integration regression без известного environmental `test_import_customers.py` блока был запущен, но не завершился за 20 минут и остановлен без итогового pytest-отчёта; этот прогон не засчитан как passed. Test backend container остановлен, чтобы не оставить фоновые pytest-процессы.

### Completion Notes List

- Реализованы AC-1..AC-8: обязательное согласие ПДн для B2C/B2B, опциональный маркетинг, API validation, создание `pdp_contract` и условного `marketing_email` в `UserConsent`.
- `UserConsent` создаётся внутри `transaction.atomic()` вместе с регистрацией; используются существующие `get_client_ip(request)`, `privacy_policy_version="1.0"` и ограничение User-Agent до 512 символов.
- Для frontend использован существующий `Checkbox`; privacy-policy ссылка работает как native Next `<Link>` вне `<label>`, а checkbox сохраняет доступное имя через `aria-labelledby`.
- OpenAPI обновлён в `docs/api/openapi.yaml`, generated types обновлены в `frontend/src/types/api.generated.ts`.
- **Финальная верификация (2026-05-10, Sonnet):** все ранее открытые DoD-пункты закрыты — `make test-unit` зелёный (697 passed), `make test-integration` зелёный кроме environmental import_customers (606 passed; падения не от story), `gitnexus_detect_changes` подтверждает scope, coverage `UserRegistrationView.post` = 100%, manual QA через API+DB прошёл все 5 сценариев. Story переведена в `review`.
- **Review patch completion (2026-05-10, GPT-5 Codex):** закрыты 5 пунктов `[Review][Patch]`: B2B pending больше не зависит от refresh token, backend missing `pdp_consent` отдаёт контрактное сообщение, невалидный `X-Forwarded-For` не ломает регистрацию, privacy-policy link больше не вложена в checkbox label, B2B форма показывает backend `pdp_consent` validation message. Story снова готова к review.
- **Review patch Pass 2 completion (2026-05-11, GPT-5 Codex):** закрыты 15 пунктов `[Review][Patch]`: единый label/link UX для B2C/B2B, B2B pending `onSuccess`, IP normalization/logging hardening, User-Agent sanitization, единый DRF error contract, nested validation parser и inline `pdp_consent` surfacing. Story снова готова к review.
- **Review patch Pass 3 completion (2026-05-11, GPT-5 Codex):** закрыты 9 `[Review][Patch]` и 1 `[Review][Decision]` (Опция 3): native privacy-policy link без custom `window.open`, canonical/global consent IP, hardened log sanitization, cyclic-safe validation parser, inline backend field errors, PDP checkbox a11y/error state и B2B pending `onSuccess` order. Story снова готова к review.
- **Review patch Pass 4 completion (2026-05-11, GPT-5 Codex):** закрыты 4 `[Review][Patch]`: verified B2B registration больше не ломается при сбое `refreshToken`, pending `onSuccess` стал single-shot при смене callback reference, schema output сузила `pdp_consent` до literal `true`, IPv4-with-port regex отклоняет невалидный port.
- **Pass 4 decision closure (2026-05-11, user-approved Option 4):** B2B `ogrn` / `legal_address` silent-drop не исправляется в 35.2; будущая работа вынесена в `deferred-work.md` как отдельное ТЗ + backlog story. Story снова готова к review.
- **Review patch Pass 5 completion (2026-05-11, GPT-5 Codex):** закрыты 5 `[Review][Patch]`: bracketed IPv6 port теперь валидируется диапазоном `1..65535`, marketing consent test проверяет audit IP/User-Agent для обеих записей, AC-6 синхронизирован с hardened helper, общий backend validation parser вынесен в `frontend/src/utils/validationErrorParser.ts`, добавлен reversed-order coverage для B2B validation errors. Story снова готова к review.
- **Review patch Pass 6 completion (2026-05-11, GPT-5 Codex):** закрыты 2 LOW `[Review][Patch]`: consent checkbox-ы переведены на RHF uncontrolled registration без `checked={watch(...)}`, добавлен B2B pending + `marketing_consent=True` integration coverage. Story снова готова к review.
- **Review patch Pass 7 completion (2026-05-11, GPT-5 Codex):** закрыты 6 `[Review][Patch]`: frontend/backend PDP-message синхронизирован с точкой, IPv4-mapped IPv6 нормализуется в canonical IPv4, backend field-error parser мапит inline только top-level поля, optional marketing checkbox явно оставлен без error-state, `get_client_ip` side-effect и Celery race scope-increment задокументированы. Story снова готова к review.
- **Review patch Pass 8 completion (2026-05-11, GPT-5 Codex):** закрыт 1 LOW `[Review][Patch]`: `sanitize_log_value` теперь удаляет lone UTF-8 surrogates перед escaping/truncation; добавлен regression test для `X-Forwarded-For` с `\udcff`. Story снова готова к review.

### File List

- `_bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `AGENTS.md`
- `CLAUDE.md`
- `backend/apps/users/serializers.py`
- `backend/apps/users/views/authentication.py`
- `backend/tests/integration/test_auth_registration_consent.py`
- `backend/tests/integration/test_auth_registration_tokens.py`
- `backend/tests/integration/test_registration_emails.py`
- `backend/tests/integration/test_user_api.py`
- `backend/tests/integration/test_verification_workflow.py`
- `backend/tests/regression/test_epic_28_intact.py`
- `backend/tests/unit/test_user_verification.py`
- `docs/api/openapi.yaml`
- `frontend/src/components/auth/RegisterForm.tsx`
- `frontend/src/components/auth/B2BRegisterForm.tsx`
- `frontend/src/components/auth/__tests__/RegisterForm.test.tsx`
- `frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx`
- `frontend/src/__tests__/components/B2BRegisterForm.test.tsx`
- `frontend/src/schemas/authSchemas.ts`
- `frontend/src/schemas/__tests__/authSchemas.test.ts`
- `frontend/src/types/api.ts`
- `frontend/src/types/api.generated.ts`
- `frontend/src/utils/validationErrorParser.ts`
- `frontend/src/app/(blue)/privacy-policy/page.tsx`

#### Pass 4 (2026-05-11) — расширенный full-scope code review (Cascade)

**Scope:** полный delta story 35.2 (25 файлов, ~3585 строк значимого кода без auto-generated). Layers: Acceptance Auditor + Blind Hunter + Edge Case Hunter (sequential, isolated context).

**Acceptance Auditor:** ✅ AC-1..AC-8 соответствуют коду. 16 Pass 1/2/3 patches закрыты. Файлы из «НЕ ИЗМЕНЯТЬ» не тронуты.

**Patches (Pass 4):**

- [x] [Review][Patch] B2B verified-immediately path: `await authService.refreshToken()` без try/catch — resolved: refresh выполняется best-effort и не превращает уже успешную verified-регистрацию в ошибку; regression covered. [frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] `useEffect` для pending `onSuccess` чувствителен к смене reference родительского коллбэка — resolved: pending success callback захватывается через `useRef`, notification guarded single-shot ref; regression covered with changing parent callback reference. [frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] AC-4 spec vs code drift: `z.boolean().refine(v => v === true)` вместо рекомендованного спекой `z.literal(true, { errorMap: ... })` — resolved: PDP schema теперь `z.boolean().pipe(z.literal(true, ...))`, form input остаётся boolean для unchecked default, parsed `RegisterFormData` / `B2BRegisterFormData` получает `pdp_consent: true`; type tests covered. [frontend/src/schemas/authSchemas.ts]
- [x] [Review][Patch] `IPV4_WITH_PORT_RE` не валидирует диапазон октетов и принимает `port=99999` — resolved: regex валидирует IPv4 octets и port range 1..65535 перед strip-port; invalid port сохраняется как `NULL` consent IP and logs warning; integration test covered. [backend/apps/users/views/authentication.py]

**Decision-needed:**

- [x] [Review][Decision] **[resolved → Опция 4]** B2B-форма отправляет `ogrn` / `legal_address`, но `UserRegistrationSerializer.Meta.fields` их не содержит → DRF молча игнорирует, поля **не сохраняются**. Решение: не расширять scope Story 35.2, потому текущая история отвечает за явные consent-чекбоксы и audit `UserConsent`, а сохранение юридических реквизитов B2B требует отдельного backend/data/API решения. Следующее действие: подготовить отдельное ТЗ и backlog story `B2B registration legal requisites persistence`; durable запись добавлена в `_bmad-output/implementation-artifacts/deferred-work.md`.

**Deferred (pre-existing, accepted trade-off):**

- [x] [Review][Defer] Дубликат `PDP_CONSENT_REQUIRED_MESSAGE` в `error_messages` (3 ключа) + `validate()` body — deferred, pre-existing drift-risk уже отмечен в Pass 2 deferred (line 572); отдельная кодовая полировка вне Pass 4 patch scope. [backend/apps/users/serializers.py:34-38, 75]

#### Pass 5 (2026-05-11) — backend + frontend full-scope code review (Cascade)

**Scope:** полный delta story 35.2 относительно `origin/main` (727848fc..HEAD), разбит на 2 chunk: backend (`apps/users/**` + `backend/tests/**`, ~764 строк diff) и frontend (`frontend/src/components/auth/**`, `schemas/authSchemas.ts`, `types/api.ts`, frontend-тесты, ~1723 строк diff). Auto-generated артефакты (`docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`) исключены из adversarial review.

**Acceptance Auditor:** ✅ AC-1..AC-8 соответствуют коду; единственная придирка — AC-6 spec text (line 147) ссылается на устаревший inline pattern `get_client_ip(request) if != "unknown" else None`, тогда как реализация использует `get_consent_ip_address(request)` (Pass 1/2/3 hardening). Pass 1-4 patches и decisions закрыты.

**Patches (Pass 5):**

- [x] [Review][Patch] Asymmetric port validation: IPv6 bracketed (`[2606:...]:99999`) принимает invalid port range, тогда как IPv4 (`1.2.3.4:99999`) отклоняет через `IPV4_PORT_RE` 1..65535 — resolved: bracketed IPv6 port теперь валидируется тем же диапазоном `1..65535`; invalid port сохраняет consent IP как `NULL` и логирует warning; regression covered. [backend/apps/users/views/authentication.py, backend/tests/integration/test_auth_registration_consent.py]
- [x] [Review][Patch] Тест `test_retail_registration_with_marketing_creates_two_records` не выставляет `REMOTE_ADDR`/`HTTP_X_FORWARDED_FOR` и молча принимает `ip_address=NULL` из-за default Django test client REMOTE_ADDR=`127.0.0.1` (loopback не проходит `is_global`) — resolved: тест задаёт глобальный `REMOTE_ADDR`, проверяет IP и User-Agent для обеих consent-записей. [backend/tests/integration/test_auth_registration_consent.py]
- [x] [Review][Patch] AC-6 spec drift: текст AC (line 147) предписывает inline `get_client_ip(request) if get_client_ip(request) != "unknown" else None`, но реализация использует `get_consent_ip_address(request)` с дополнительной `is_global`/`parse_ip_address`/`IPV4_WITH_PORT_RE` валидацией — resolved: AC-6 wording обновлён на `get_consent_ip_address()` / `sanitize_consent_user_agent()` и явно описывает hardening audit IP. [_bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md]
- [x] [Review][Patch] ~120 LOC валидационного парсера (`MAX_VALIDATION_MESSAGE_DEPTH`, `ARRAY_INDEX_KEY_RE`, `getValidationMessage`, `getValidationEntries`, `getFirstValidationMessage`, `collectBackendFieldMessages`, `applyBackendFieldErrors`) дублируется почти идентично между `RegisterForm.tsx:52-150` и `B2BRegisterForm.tsx:21-149`; различия — только field error map. Pass 1 Dev Notes (line 485-487) deferred DRY-extraction для ~30 LOC UI-блока, но Pass 3 patches увеличили duplicate-cost 4× (recursive WeakSet-guard parser, depth limit, sort logic). Низко-усилийный extract в `frontend/src/utils/validationErrorParser.ts` (generic over field map) снизит drift-risk — resolved: общий generic parser вынесен в `frontend/src/utils/validationErrorParser.ts`, формы передают только field map. [frontend/src/utils/validationErrorParser.ts, frontend/src/components/auth/RegisterForm.tsx, frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch] Тест `should show first backend validation error instead of hard-coded pdp priority` проходит потому что `email` идёт первым в mock-data — нет reversed-order coverage (`{pdp_consent: [...], email: [...]}`), которая доказала бы «no hard-coded priority». Поведение зависит от key-order ответа DRF, и регрессия на смену сериализации полей проскочит — resolved: добавлен reversed-order test, который проверяет первый alert при `pdp_consent` перед `email`. [frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx]

**Deferred (pre-existing, accepted trade-off, or out of scope):**

- [x] [Review][Defer] Cross-cutting изменение `get_client_ip` (blank XFF first hop → fallback `REMOTE_ADDR` вместо `""`) не задокументировано в Change Log — функция используется всеми callers (LogoutView и др.), не только consent flow. Improvement strict (avoid empty string), но cosmetic — отметить намеренный side-effect в commit message при следующем заходе. [backend/apps/users/views/authentication.py:548-557]
- [x] [Review][Defer] `transaction.atomic()` wrapper расширил окно pre-existing Celery race (`send_admin_verification_email.delay` / `send_user_pending_email.delay` вызываются ВНУТРИ atomic block перед commit, теперь между .delay() и commit два дополнительных `UserConsent` INSERT) — pre-existing tech debt, явно out of scope 35.2 (Dev Notes 477-479, Pass 1 defer #6); запись уже есть в `_bmad-output/implementation-artifacts/deferred-work.md` (Pass 3 entry). [backend/apps/users/serializers.py:113-125, backend/apps/users/views/authentication.py:143-166]

**Dismissed (noise / false positive):**

- Controlled/RHF double-tracking через `checked={watch('pdp_consent')}` + `{...register('pdp_consent')}` — works correctly, идиоматично для RHF при UI-visible state binding; perf cost minimal (2 checkboxes)
- Convoluted ctrl-click test для privacy-policy link (`fireEvent.click(link, { ctrlKey: true })` с manual `preventDefault`) — реальная проверка «link не toggle-ит checkbox» уже работает через `expect(link.closest('label')).toBeNull()`; modifier-click сценарий редундантен, но не вреден

#### Pass 6 (2026-05-11) — full-scope code review (Cascade)

**Scope:** полный delta story 35.2 относительно `origin/main` (727848fc..ed4f83e3, ~1800 строк значимого source-кода без auto-generated `api.generated.ts`/`openapi.yaml`/`.review-cache`). Layers: Acceptance Auditor + Blind Hunter + Edge Case Hunter (inline isolated mental contexts).

**Acceptance Auditor:** ✅ Все AC-1..AC-8 соответствуют коду. 16 `[Review][Patch]` из Passes 1-5 закрыты. Файлы из «НЕ ИЗМЕНЯТЬ» не тронуты. Spec-drift AC-4 (`z.boolean().pipe(z.literal(true))` вместо `z.literal(true, { errorMap })`) задокументирован Pass 4 patch как accepted.

**Outcome:** **Approve with minor recommendations** — production-ready, найденные 2 LOW issue не блокируют release.

**Review Follow-ups (Pass 6, LOW, non-blocking):**

- [x] [Review][Patch][LOW] Code smell — RHF `register()` + controlled `checked={watch(...)}` в Checkbox. На `<Checkbox>` спредятся одновременно `{...register('pdp_consent')}` (uncontrolled-style: даёт `name/onChange/onBlur/ref`) и `checked={pdpConsent}` (controlled через `watch()`). RHF идиоматично работает с checkbox через uncontrolled `defaultChecked`. Текущая схема работает (43/43 тестов зелёные), но создаёт избыточный re-render на каждом toggle и потенциально вызывает React warning «changing controlled/uncontrolled» при HMR. То же для `marketing_consent`. Рекомендация: убрать `checked={pdpConsent}`/`checked={marketingConsent}` и `watch('pdp_consent')`/`watch('marketing_consent')` — оставить только `{...register(...)}` + `aria-invalid` через `errors.pdp_consent`; стиль `hasPdpConsentError` обновлять через CSS `peer-aria-[invalid=true]`. Альтернатива — `<Controller>`. Resolved: B2C/B2B consent checkbox-ы больше не передают controlled `checked`; состояние ведёт RHF `register()`. [frontend/src/components/auth/RegisterForm.tsx; frontend/src/components/auth/B2BRegisterForm.tsx]
- [x] [Review][Patch][LOW] Gap в AC-7 coverage — нет интеграционного теста для **B2B + `marketing_consent=True`** (две `UserConsent` записи для pending-пользователя). `test_b2b_registration_creates_pdp_consent_record_for_pending_user` использует только `marketing_consent=False` (default из `b2b_payload()`). Retail-эквивалент покрыт (`test_retail_registration_with_marketing_creates_two_records`). AC-7 п.5 формально удовлетворён, но edge case с двумя записями для `is_active=False` пользователя остаётся без regression coverage. Рекомендация: добавить `test_b2b_registration_with_marketing_creates_two_records_for_pending_user`, ассертить `consents.count() == 2` и `{consent_type for consent in consents} == {"pdp_contract", "marketing_email"}`. Resolved: добавлен integration test для pending B2B + `marketing_consent=True`, включая audit IP/User-Agent обеих записей. [backend/tests/integration/test_auth_registration_consent.py]

**Dismissed (noise / уже покрыто Pass 1-5 defer):**

- `serializers.py:100` `validated_data.pop("pdp_consent")` без присваивания — интенциональное удаление, контекст ясен из `validate()` выше.
- `get_client_ip` без trusted-proxy allowlist — defer-flagged в Pass 2 (project-wide infra).
- Email Celery tasks внутри `transaction.atomic` (rollback → orphan `delay`) — pre-existing defer в Dev Notes + `deferred-work.md`.
- Zod v4 `error:` vs spec `errorMap:` — функционально эквивалентно, покрыто `authSchemas.test.ts` (27/27).
- Конфликт accessible name между внутренним `Checkbox` `<label htmlFor>` (иконка `aria-hidden`) и внешним `aria-labelledby` — внутренний label без текстового контента, accessible name берётся однозначно из 3 span'ов.

---

### Change Log

- Добавлены consent-поля в backend serializer/view и audit-запись `UserConsent` при регистрации.
- Добавлены обязательный PDP и опциональный marketing checkbox в B2C/B2B формы регистрации.
- Обновлены backend/frontend тесты регистрации и схем, добавлены новые consent-тесты.
- Регенерированы OpenAPI и generated frontend API-типы.
- Исправлено сохранение error-boundary поведения `/privacy-policy` для 5xx/network ошибок, обнаруженное полным frontend suite.
- 2026-05-10: финальный verification-проход (full make test-unit/test-integration, gitnexus detect-changes, coverage, manual API QA), статус story → `review`.
- 2026-05-10: addressed code review findings — 5 `[Review][Patch]` items resolved; status story → `review`.
- 2026-05-11: addressed code review findings — 15 Pass 2 `[Review][Patch]` items resolved; status story → `review`.
- 2026-05-11: addressed code review findings — 9 Pass 3 `[Review][Patch]` items + 1 `[Review][Decision]` resolved; status story → `review`.
- 2026-05-11: Pass 4 full-scope code review (Cascade) — открыто 4 `[Review][Patch]` + 1 `[Review][Decision]` + 1 `[Review][Defer]`; status story → `in-progress`.
- 2026-05-11: Pass 5 full-scope code review (Cascade) — открыто 5 `[Review][Patch]` (2 MEDIUM, 3 LOW) + 2 `[Review][Defer]`, 2 findings dismissed; status story → `in-progress`.
- 2026-05-11: addressed Pass 4 code review findings — 4 `[Review][Patch]` items resolved, 1 `[Review][Defer]` recorded as deferred; story remains `in-progress` pending product/architect decision on B2B `ogrn` / `legal_address`.
- 2026-05-11: resolved Pass 4 `[Review][Decision]` by user-approved Option 4; B2B `ogrn` / `legal_address` persistence moved to deferred-work for future ТЗ/story; status story → `review`.
- 2026-05-11: addressed Pass 5 code review findings — 5 `[Review][Patch]` items resolved; status story → `review`.
- 2026-05-11: Pass 6 full-scope code review (Cascade) — Outcome `Approve with minor recommendations`, открыто 2 `[Review][Patch][LOW]` (controlled-checkbox code smell, B2B+marketing test gap); status story → `in-progress`.
- 2026-05-11: addressed Pass 6 LOW review follow-ups — 2 `[Review][Patch]` items resolved; status story → `review`.
- 2026-05-11: Pass 7 full-scope code review (Cascade) — Outcome `Changes Requested (minor)`, открыто 6 `[Review][Patch]` (2 MEDIUM, 4 LOW); status story → `in-progress`.
- 2026-05-11: addressed Pass 7 review follow-ups — 6 `[Review][Patch]` items resolved; status story → `review`.
- 2026-05-11: Pass 8 full-scope adversarial review (Cascade) — Outcome `Approve with minor recommendation`, открыт 1 `[Review][Patch][LOW]` (sanitize_log_value surrogate handling), 3 deferred (pre-existing), 4 dismissed; status story → `in-progress`.
- 2026-05-11: addressed Pass 8 LOW review follow-up — 1 `[Review][Patch]` item resolved; status story → `review`.

#### Pass 8 (2026-05-11) — full-scope adversarial review (Cascade)

**Scope:** полный delta story 35.2 относительно `af7254ce..HEAD` (8 коммитов story 35.2, ~2000 строк значимого source-кода без auto-generated `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` и `.review-cache/*.patch`). Layers: Acceptance Auditor + Blind Hunter + Edge Case Hunter (inline isolated mental contexts).

**Acceptance Auditor:** ✅ AC-1..AC-8 соответствуют коду. Все 31 `[Review][Patch]` из Passes 1-7 закрыты. Файлы из «НЕ ИЗМЕНЯТЬ» не тронуты. Pass 4 spec-drift по AC-4 (`z.boolean().pipe(z.literal(true))`) и Pass 5 spec-drift по AC-6 (`get_consent_ip_address`) зафиксированы как accepted.

**Outcome:** **Approve with minor recommendation** — production-ready, найденный 1 LOW issue не блокирует release.

**Review Follow-ups (Pass 8):**

- [x] [Review][Patch][LOW] Inconsistency между `sanitize_log_value` и `sanitize_consent_user_agent` по обработке lone UTF-8 surrogates: `sanitize_consent_user_agent` (line 612-615) удаляет lone surrogates через `.encode("utf-8", "ignore").decode("utf-8")`, но `sanitize_log_value` (line 596-609) — нет, только escape-ит фиксированный набор control chars. Если `client_ip` из `X-Forwarded-For` содержит lone surrogate (`\udcff`), `logger.warning(extra={"client_ip": sanitize_log_value(...)})` может крашнуть log handler'ы с UTF-8 encoding (SocketHandler, syslog, journald, Sentry transport). Существующий тест `test_registration_sanitizes_invalid_ip_before_warning_log` покрывает control chars/Unicode separators, но не lone surrogates. Resolved: `sanitize_log_value` удаляет lone surrogate через UTF-8 encode/decode до escaping/truncation; добавлен regression test `test_registration_sanitizes_surrogate_from_invalid_ip_warning_log`. [backend/apps/users/views/authentication.py:596-609; backend/tests/integration/test_auth_registration_consent.py]

**Deferred (pre-existing, accepted trade-off, или out of scope):**

- [x] [Review][Defer] `validate_email` case-sensitive uniqueness check (`User.objects.filter(email=value).exists()`) при `value.lower()` на return: race-condition `Foo@x.com` после `foo@x.com` приведёт к `IntegrityError` → 500 вместо 409. Pre-existing (Pass 3 defer #2), не введено 35.2. [backend/apps/users/serializers.py:62-66]
- [x] [Review][Defer] Celery `.delay()` внутри `transaction.atomic()` — pre-existing tech debt, явно out of scope (Pass 1 defer #6, Pass 7 follow-up scope-increment), запись в `_bmad-output/implementation-artifacts/deferred-work.md`. [backend/apps/users/serializers.py:113-125, backend/apps/users/views/authentication.py:143-166]
- [x] [Review][Defer] B2B form `ogrn`/`legal_address` silent-drop в payload — Pass 4 product decision Option 4, durable запись в `deferred-work.md`. [frontend/src/components/auth/B2BRegisterForm.tsx:110-122]

**Dismissed (noise / false positive):**

- `dangerouslySetInnerHTML` в `frontend/src/app/(blue)/privacy-policy/page.tsx:117` — pre-existing 35.1, content из `/pages/privacy-policy/` admin trust boundary; не введено 35.2.
- `getValidationEntries` sort comparator stability — Node 12+/V8 гарантируют stable sort, проект на Next.js 15 / React 19.
- `IPV4_PORT_RE` 6-alternation regex — функционально корректно, cosmetic verbosity vs `\d{1,5}` + range check.
- B2B `refreshToken()` silent swallow на verified-path — Pass 4 conscious decision, регрессионный тест Pass 4 закрепил поведение.

#### Pass 7 (2026-05-11) — full-scope adversarial review (Cascade)

**Scope:** полный delta story 35.2 относительно `origin/main` (727848fc..16addf9b), ~1600 строк значимого source-кода без auto-generated `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` и `.review-cache/*.patch`. Layers: Acceptance Auditor + Blind Hunter + Edge Case Hunter.

**Acceptance Auditor:** ✅ AC-1..AC-8 соответствуют коду. Все 25 `[Review][Patch]` из Passes 1-6 закрыты. Файлы из «НЕ ИЗМЕНЯТЬ» не тронуты.

**Outcome:** **Changes Requested (minor)** — 2 MEDIUM + 4 LOW follow-ups; ничего не блокирует merge, но требует явного решения по M-1/M-2.

**Review Follow-ups (Pass 7):**

- [x] [Review][Patch][MEDIUM] Drift текста ошибки `pdp_consent` между frontend и backend: frontend Zod `'Необходимо согласие на обработку персональных данных'` (без точки), backend serializer `PDP_CONSENT_REQUIRED_MESSAGE = 'Необходимо согласие на обработку персональных данных.'` (с точкой). При client-side Zod валидации показывается версия без точки, при 400-ответе backend через `applyBackendFieldErrors` — с точкой на том же чекбоксе. UX-inconsistency + drift-risk для assertion-тестов. Resolved: frontend Zod message синхронизирован с backend punctuation; schema tests закрепляют точный текст для B2C и B2B. [frontend/src/schemas/authSchemas.ts, frontend/src/schemas/__tests__/authSchemas.test.ts]
- [x] [Review][Patch][MEDIUM] `normalize_consent_ip` отбрасывает IPv4-mapped IPv6 (`::ffff:<public-v4>`): `IPv6Address("::ffff:8.8.8.8").is_global == False`, поэтому dual-stack nginx/proxy, передающий клиентский IPv4 в IPv6-mapped форме, получит `UserConsent.ip_address = NULL` для легитимного публичного клиента. 152-ФЗ audit-trail деградирует молча. Resolved: `ipv4_mapped` разворачивается до canonical IPv4 и валидируется через `is_global`; integration test покрывает `::ffff:8.8.8.8` → `8.8.8.8`. [backend/apps/users/views/authentication.py, backend/tests/integration/test_auth_registration_consent.py]
- [x] [Review][Patch][LOW] Cross-cutting side-effect `get_client_ip` (blank XFF first hop → fallback `REMOTE_ADDR` вместо пустой строки) не отражён ни в Change Log story, ни в commit message. Функция используется вне scope registration (LogoutView, rate-limiting). Resolved: side-effect явно зафиксирован в Change Log/Debug Log как намеренное улучшение: empty first hop больше не попадает в audit/log path как пустая строка и fallback-ится на `REMOTE_ADDR`. [backend/apps/users/views/authentication.py, _bmad-output/implementation-artifacts/Story/35-2-consent-checkboxes-in-registration-forms.md]
- [x] [Review][Patch][LOW] `applyBackendFieldErrors` рекурсивно сканирует весь payload до `MAX_VALIDATION_MESSAGE_DEPTH = 8` и сопоставляет любой ключ с `fieldErrorMap` на любой глубине. Если backend в будущем вложит diagnostic-структуру с ключом, случайно совпадающим с `email`/`password` где-то глубже top-level, RHF выставит inline error на неподходящее поле формы. Сейчас коллизия маловероятна (DRF контракт плоский), но ограничитель глубины её не предотвращает. Resolved: inline `setError` теперь мапит только top-level field keys; nested payload остаётся видимым как API error через `getFirstValidationMessage`. [frontend/src/utils/validationErrorParser.ts, frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx]
- [x] [Review][Patch][LOW] Marketing-checkbox не получает `aria-invalid`/`aria-describedby`/error-state визуализации. Сейчас осознанно (поле опциональное, submit не блокируется), но если в будущем появится валидация (например, «подтвердите возраст» или отзыв marketing согласия с условием), симметрия с PDP-чекбоксом будет потеряна. Resolved: отличие зафиксировано комментариями в B2C/B2B формах; tests закрепляют, что optional marketing checkbox не получает inline error-state. [frontend/src/components/auth/RegisterForm.tsx, frontend/src/components/auth/B2BRegisterForm.tsx, frontend/src/components/auth/__tests__/RegisterForm.test.tsx, frontend/src/components/auth/__tests__/B2BRegisterForm.test.tsx]
- [x] [Review][Patch][LOW] `transaction.atomic()` в `UserRegistrationView.post` расширил окно pre-existing Celery race: после 35.2 между `send_admin_verification_email.delay(...)` / `send_user_pending_email.delay(...)` (внутри `serializer.create()`) и финальным COMMIT выполняется 1-2 `UserConsent.objects.create()`. Если consent INSERT упадёт (например, DB contention на `UserConsent` constraint), worker получает задачу на откатанного user'а. Deferred recognized в Passes 1/3/5, но scope-increment именно 35.2 стоит явно зафиксировать в `deferred-work.md` с пометкой «окно расширено Pass 1 atomic wrapping». Resolved: scope-increment добавлен в `_bmad-output/implementation-artifacts/deferred-work.md`; code change остаётся вне scope 35.2. [backend/apps/users/views/authentication.py, backend/apps/users/serializers.py, _bmad-output/implementation-artifacts/deferred-work.md]

**Dismissed (noise / уже покрыто ранее):**

- A11y `aria-labelledby` через 3 ID (label-prefix + link + label-suffix) — SR читает accessible name корректно, покрыто component-тестами Pass 3.
- `sanitize_log_value` `MAX_LOG_VALUE_LENGTH = 128` — достаточно для max bracketed IPv6+port (~47 символов), truncation по token boundary корректна.
- `IPV4_WITH_PORT_RE` не ловит `0.0.0.0:0` — отсечётся позже через `parse_ip_address` + `is_global`.
- Pass 6 controlled-checkbox fix — проверено: `checked={watch(...)}` удалён, осталось только `{...register(...)}`.
