# Story 35.2: Чек-боксы согласий в формах регистрации (B2C и B2B)

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных
**Story ID:** 35.2
**Status:** ready-for-dev
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
    ip_address=get_client_ip(request) if get_client_ip(request) != "unknown" else None,
    user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
)
```

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

- [ ] AC-1..AC-8 реализованы.
- [ ] `make test-unit` и `make test-integration` зелёные локально (через Docker).
- [ ] Новые тесты `test_auth_registration_consent.py` зелёные (7 кейсов).
- [ ] Существующий `test_auth_registration_tokens.py` обновлён и зелёный.
- [ ] `npm run test -- src/components/auth/__tests__/RegisterForm.test.tsx` зелёный.
- [ ] `npm run test -- src/components/auth/__tests__/B2BRegisterForm.test.tsx` зелёный (новый файл).
- [ ] `npm run build` (frontend) без ошибок TypeScript.
- [ ] OpenAPI спецификация регенерирована (`python manage.py spectacular --file docs/api-spec.yaml`), если используется generated types на фронте — `npm run generate:types` прогнан.
- [ ] `gitnexus_detect_changes()` подтверждает: затронуты только символы из списка UPDATE/CREATE.
- [ ] Покрытие `apps/users/views/authentication.py::UserRegistrationView.post` ≥ 90% (критический модуль).
- [ ] Manual QA через UI (Docker dev): регистрация B2C без чекбокса → ошибка; с чекбоксом → 201 + JWT; в Django Admin раздел «Согласия пользователей» появилась запись с корректным IP / User-Agent / `consent_type=pdp_contract`. То же для B2B (но без auto-login: pending status).

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

_Заполнит dev-agent при реализации._

### Implementation Plan

_Заполнит dev-agent перед началом._

### Debug Log References

### Completion Notes List

### File List

_Заполнить по факту реализации (минимум 8 файлов: 4 backend + 4 frontend, см. Структура файлов выше)._
