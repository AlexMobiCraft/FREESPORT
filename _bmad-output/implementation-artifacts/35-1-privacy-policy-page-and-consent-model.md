# Story 35.1: Страница «Политика обработки персональных данных» и модель UserConsent

**Epic:** 35 — Соответствие 152-ФЗ о персональных данных  
**Story ID:** 35.1  
**Status:** in-progress (15 review patches как action items)  
**Priority:** High (блокирует истории 35.2, 35.3)

---

## User Story

Как пользователь сайта,
я хочу видеть страницу «Политика обработки персональных данных»,
доступную по прямой ссылке,
чтобы ознакомиться с правилами обработки моих данных (требование 152-ФЗ).

Как администратор,
я хочу управлять текстом «Политики ПДн» через Django Admin,
чтобы обновлять документ без привлечения разработчиков.

---

## Acceptance Criteria

### AC-1: Backend — Страница политики в Admin

**Given** Django Admin с зарегистрированной моделью `Page` (уже готово — `backend/apps/pages/admin.py`),  
**When** администратор создаёт страницу с `slug="privacy-policy"` и `is_published=True`,  
**Then** страница доступна через API: `GET /api/pages/privacy-policy/`.

**Note:** Модель `Page` и `PageAdmin` уже реализованы. Код admin **не изменять**.

---

### AC-2: Backend — Модель UserConsent

**Given** пользователь выражает согласие на обработку ПДн,  
**When** форма регистрации / подписки отправляется,  
**Then** согласие записывается в модель `UserConsent` со следующими полями:

| Поле | Тип | Описание |
|------|-----|----------|
| `user` | FK → User (nullable) | Привязка к авторизованному пользователю |
| `session_key` | CharField(40, blank) | Для анонимных пользователей |
| `consent_type` | CharField(30) | `"pdp_contract"` или `"marketing_email"` |
| `given_at` | DateTimeField(auto_now_add) | Момент согласия |
| `ip_address` | GenericIPAddressField(null) | IP пользователя |
| `user_agent` | TextField(blank) | User-Agent строки |
| `policy_version` | CharField(20, default="1.0") | Версия политики на момент согласия |

**Choices для consent_type:**
```python
CONSENT_TYPE_CHOICES = [
    ("pdp_contract", "Согласие на обработку ПДн для исполнения договора"),
    ("marketing_email", "Согласие на получение рекламных рассылок"),
]
```

**Meta:** `verbose_name = "Согласие пользователя"`, `ordering = ["-given_at"]`

**Расположение:** `backend/apps/common/models.py` (в конце файла, после `Newsletter`).

**Миграция:** создать через `makemigrations common`.

---

### AC-3: Backend — Admin для UserConsent

**Given** модель `UserConsent` в `backend/apps/common/admin.py`,  
**When** администратор открывает раздел «Согласия пользователей»,  
**Then** доступен список с колонками: `user`, `consent_type`, `given_at`, `ip_address`, `policy_version`.  
**And** фильтрация по `consent_type` и `given_at`.  
**And** поиск по `user__email`, `ip_address`.  
**And** все записи **только для чтения** (нельзя редактировать/добавлять через admin).

---

### AC-4: Frontend — Страница `/privacy-policy`

**Given** страница создана в Admin (AC-1),  
**When** пользователь переходит на `/privacy-policy`,  
**Then** рендерится Server Component, который:
- Делает `GET /api/pages/privacy-policy/` (server-side, без кэша браузера)
- Отображает `title` как `<h1>`
- Отображает `content` через `dangerouslySetInnerHTML` (контент уже sanitized на backend через bleach)
- SEO: использует `metadata` из `seo_title` и `seo_description`

**If** страница не найдена (404 от API) **or** `is_published=False`,  
**Then** Next.js `notFound()` → стандартная 404-страница.

**Маршрут:** `frontend/src/app/(blue)/privacy-policy/page.tsx`

**Паттерн реализации** — аналогично другим страницам проекта, но с данными из API:
```
frontend/src/app/(blue)/delivery/page.tsx  ← образец структуры (статическая)
frontend/src/app/(blue)/blog/[slug]/page.tsx  ← образец с fetch данных из API
```

---

### AC-5: Frontend — Страница оформлена в стиле Blue Theme

**Given** страница `/privacy-policy`,  
**When** она рендерится,  
**Then**:
- Breadcrumb: `Главная → Политика обработки персональных данных`
- Hero section с `<h1>`
- Контент завёрнут в `<Card>` с `prose`-классами для читаемости текста
- Responsive (mobile-first)
- Компоненты: `Breadcrumb`, `Card` из `@/components/ui`

---

## Технические требования и ограничения

### Backend (Django)

**Не изменять:**
- `backend/apps/pages/models.py` — `Page` уже готова
- `backend/apps/pages/admin.py` — `PageAdmin` уже готова
- `backend/apps/pages/views.py` — `PageViewSet` уже готова (ReadOnlyModelViewSet, кэш 24ч)

**Изменять:**
- `backend/apps/common/models.py` — добавить `UserConsent` в конец файла
- `backend/apps/common/admin.py` — зарегистрировать `UserConsentAdmin`
- `backend/apps/common/migrations/` — новая миграция

**Важно:** Миграция должна следовать после последней существующей миграции `common`. Не добавляй зависимости на миграции из других app кроме `users` (для FK).

### Frontend (Next.js)

**Создать:**
- `frontend/src/app/(blue)/privacy-policy/page.tsx` — Server Component

**Не изменять в этой истории:**
- `RegisterForm.tsx`, `B2BRegisterForm.tsx` — чек-боксы в Story 35.2
- `SubscribeForm.tsx` — чек-бокс в Story 35.3

**API fetch pattern** — используй `fetch` с `{ next: { revalidate: 3600 } }` (ISR, 1 час):
```typescript
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pages/privacy-policy/`, {
  next: { revalidate: 3600 },
});
if (!res.ok) notFound();
const page = await res.json();
```

**Переменная окружения:** `NEXT_PUBLIC_API_URL` уже есть в проекте (используется в других page.tsx).

### API контракт (уже существующий)

```
GET /api/pages/{slug}/
Response 200:
{
  "id": 1,
  "title": "Политика обработки персональных данных",
  "slug": "privacy-policy",
  "content": "<p>HTML-текст политики...</p>",
  "seo_title": "Политика ПДн | FREESPORT",
  "seo_description": "...",
  "is_published": true,
  "created_at": "2026-05-09T...",
  "updated_at": "2026-05-09T..."
}

Response 404: {"detail": "Not found."}
```

---

## Структура файлов (изменения)

```
backend/
  apps/
    common/
      models.py          [MODIFY] — добавить класс UserConsent
      admin.py           [MODIFY] — добавить UserConsentAdmin
      migrations/
        00XX_add_user_consent.py  [CREATE]

frontend/
  src/
    app/
      (blue)/
        privacy-policy/
          page.tsx       [CREATE] — Server Component
```

---

## Реализация UserConsent (полный код)

Добавить в `backend/apps/common/models.py` после класса `Newsletter`:

```python
class UserConsent(models.Model):
    """Фиксация согласий пользователей (152-ФЗ)"""

    CONSENT_TYPE_CHOICES = [
        ("pdp_contract", "Согласие на обработку ПДн для исполнения договора"),
        ("marketing_email", "Согласие на получение рекламных рассылок"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consents",
        verbose_name="Пользователь",
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="Ключ сессии",
        help_text="Для анонимных пользователей",
    )
    consent_type = models.CharField(
        max_length=30,
        choices=CONSENT_TYPE_CHOICES,
        verbose_name="Тип согласия",
    )
    given_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата согласия")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="IP адрес"
    )
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    policy_version = models.CharField(
        max_length=20, default="1.0", verbose_name="Версия политики"
    )

    class Meta:
        verbose_name = "Согласие пользователя"
        verbose_name_plural = "Согласия пользователей"
        ordering = ["-given_at"]

    def __str__(self) -> str:
        who = self.user.email if self.user else f"аноним ({self.session_key[:8]})"
        return f"{who} — {self.get_consent_type_display()} — {self.given_at:%d.%m.%Y}"
```

**Импорт:** убедись, что `from django.conf import settings` уже есть в `common/models.py` (проверь перед добавлением).

---

## Реализация UserConsentAdmin

Добавить в `backend/apps/common/admin.py`:

```python
@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ["user", "consent_type", "given_at", "ip_address", "policy_version"]
    list_filter = ["consent_type", "given_at"]
    search_fields = ["user__email", "ip_address"]
    readonly_fields = [
        "user", "session_key", "consent_type", "given_at",
        "ip_address", "user_agent", "policy_version",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
```

**Импорт в admin.py:** добавь `UserConsent` в импорт из `models`.

---

## Реализация Frontend страницы

`frontend/src/app/(blue)/privacy-policy/page.tsx`:

```typescript
import React from 'react';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { Breadcrumb, Card } from '@/components/ui';

interface PageData {
  title: string;
  slug: string;
  content: string;
  seo_title: string;
  seo_description: string;
  is_published: boolean;
}

async function fetchPrivacyPolicy(): Promise<PageData | null> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/pages/privacy-policy/`,
    { next: { revalidate: 3600 } }
  );
  if (!res.ok) return null;
  return res.json();
}

export async function generateMetadata(): Promise<Metadata> {
  const page = await fetchPrivacyPolicy();
  return {
    title: page?.seo_title || 'Политика обработки персональных данных | FREESPORT',
    description: page?.seo_description || '',
  };
}

const breadcrumbItems = [
  { label: 'Главная', href: '/' },
  { label: 'Политика обработки персональных данных' },
];

export default async function PrivacyPolicyPage() {
  const page = await fetchPrivacyPolicy();
  if (!page || !page.is_published) notFound();

  return (
    <div className="min-h-screen bg-neutral-100">
      <div className="container mx-auto px-4 py-4">
        <Breadcrumb items={breadcrumbItems} />
      </div>

      <section className="bg-white py-8 sm:py-12">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-headline-l sm:text-headline-xl font-bold text-text-primary">
            {page.title}
          </h1>
        </div>
      </section>

      <section className="container mx-auto px-4 py-8 sm:py-12">
        <Card className="p-6 sm:p-10">
          <div
            className="prose prose-neutral max-w-none text-text-primary"
            dangerouslySetInnerHTML={{ __html: page.content }}
          />
        </Card>
      </section>
    </div>
  );
}
```

**Безопасность `dangerouslySetInnerHTML`:** допустимо, так как контент прошёл `bleach.clean()` на backend (только теги p, h1-h6, ul, ol, li, a, strong, em, br — XSS невозможен).

---

## Тесты

### Backend

**Файл:** `backend/apps/common/tests/test_user_consent.py`

```python
# Тесты для модели UserConsent
# 1. Создание записи согласия (pdp_contract)
# 2. Создание записи согласия (marketing_email)
# 3. Анонимное согласие через session_key
# 4. __str__ возвращает корректный текст
# 5. Нельзя создать согласие без consent_type (IntegrityError / ValidationError)
```

**Файл:** `backend/apps/pages/tests/test_page_api.py` — проверить что GET /api/pages/privacy-policy/ возвращает 404 до публикации и 200 после.

### Frontend

**Файл:** `frontend/src/app/(blue)/privacy-policy/__tests__/page.test.tsx`

```typescript
// 1. Рендерит страницу с заголовком из API
// 2. Рендерит контент из API
// 3. При 404 от API вызывает notFound()
// 4. При is_published=false вызывает notFound()
// Мок: MSW handler для GET /api/pages/privacy-policy/
```

**Покрытие:** модель `UserConsent` ≥ 90%, страница `/privacy-policy` ≥ 80%.

---

## Связанные истории

- **Блокирует:** 35.2 (чек-боксы регистрации), 35.3 (чек-бокс подписки) — ссылки на `/privacy-policy` появятся в этих формах
- **Использует:** существующую модель `Page` (pages app), `PageAdmin`, `PageViewSet`
- **Параллельно:** может разрабатываться одновременно с 35.4 (cookie-баннер)

---

## Примечания для разработчика

1. **Не создавай фикстуры** для Политики ПДн — содержимое добавляется вручную через Django Admin продакшен-сервера.
2. **Проверь** в `common/models.py`, что импорт `settings` уже есть (используется в `Newsletter`). Если нет — добавь `from django.conf import settings`.
3. **Slug** страницы должен быть точно `privacy-policy` (проверяется хардкодом во фронтенде).
4. **ISR revalidate: 3600** — не ставь `cache: 'no-store'`, иначе каждый запрос ударит по backend.
5. Страница `/delivery` — статическая (без API), `/privacy-policy` — динамическая через API. Не путай паттерны.
6. **`prose` классы** — Tailwind Typography (`@tailwindcss/typography`). Проверь, что плагин подключён в `tailwind.config.ts`. Если нет — используй ручные стили вместо `prose`.

---

## Definition of Done

- [x] Модель `UserConsent` добавлена в `common/models.py`
- [x] Миграция создана и применена
- [x] `UserConsentAdmin` зарегистрирован, записи только для чтения
- [x] `GET /api/pages/privacy-policy/` возвращает 200 для опубликованной страницы
- [x] Страница `/privacy-policy` рендерится корректно (SSR)
- [x] При отсутствии страницы в базе — 404
- [x] Breadcrumb корректный
- [x] Тесты backend проходят
- [x] Тесты frontend проходят
- [x] TypeScript: `npm run build` без ошибок

---

## Dev Agent Record

### Implementation Plan

- Добавить `UserConsent` в `apps.common` как append-only модель согласий с nullable `user`, `session_key`, типом согласия, IP/User-Agent и версией политики.
- Зарегистрировать `UserConsentAdmin` как read-only интерфейс: просмотр списка/фильтры/поиск без add/change/delete.
- Не менять `Page`, `PageAdmin`, `PageViewSet`, `PageSerializer`: существующий backend уже отдаёт только опубликованные страницы, а текущий serializer намеренно не раскрывает `is_published`.
- Добавить `/privacy-policy` как Server Component blue theme с ISR `revalidate: 3600`, breadcrumb, hero и HTML-контентом в `Card`.

### Debug Log

- RED backend: `pytest apps/common/tests/test_user_consent.py tests/integration/test_pages_api.py -q` падал на `ImportError: cannot import name 'UserConsent'`.
- RED frontend: `npm run test -- "src/app/(blue)/privacy-policy/__tests__/page.test.tsx"` падал на отсутствии `../page`.
- RED admin read-only: `pytest apps/common/tests/test_user_consent.py -q` падал, потому что Django Admin по умолчанию разрешал delete.
- Обнаружено расхождение story с текущим API: `PageSerializer` не отдаёт `is_published`, и существующий тест `test_api_response_structure` проверяет отсутствие этого поля. Frontend реализован совместимо: 404 от backend является основным сигналом неопубликованной/отсутствующей страницы, `is_published === false` дополнительно обрабатывается, если поле появится.

### Completion Notes

- Реализованы модель `UserConsent`, read-only admin, миграция `0015_userconsent`, API-тест публикации `privacy-policy` и frontend-страница `/privacy-policy`.
- Миграция применена в Docker backend: `python manage.py migrate common`.
- Полный backend `pytest -q` дважды не уложился в лимиты 10 и 20 минут. После разделения suite: `pytest -m unit -q --reuse-db` прошёл, `pytest -m integration -q --reuse-db` выявил 10 pre-existing/data-dependent падений в `test_import_customers.py` из-за отсутствия `/app/data/import_1c/contragents`, а `pytest -m integration -q --reuse-db --ignore=tests/integration/test_management_commands/test_import_customers.py` прошёл.

## File List

- `_bmad-output/implementation-artifacts/35-1-privacy-policy-page-and-consent-model.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/apps/common/models.py`
- `backend/apps/common/admin.py`
- `backend/apps/common/migrations/0015_userconsent.py`
- `backend/apps/common/tests/test_user_consent.py`
- `backend/tests/integration/test_pages_api.py`
- `frontend/src/app/(blue)/privacy-policy/page.tsx`
- `frontend/src/app/(blue)/privacy-policy/__tests__/page.test.tsx`

## Review Findings

_Code review run: 2026-05-09 (3 параллельных слоя: Blind Hunter / Edge Case Hunter / Acceptance Auditor; ~70 raw findings → 4 decision-needed / 12 patch / 13 defer / 20+ dismiss)._

### Decision Needed (resolved 2026-05-09)

- [x] [Review][Decision→Patch 1a] **`is_published` в PageSerializer** — РЕШЕНИЕ: удалить мёртвый guard на фронте (`page.is_published === false` всегда `undefined === false = false` потому что бекенд не отдаёт поле). См. patch ниже.
- [x] [Review][Decision→Dismiss 2a] **Unique constraint на `(user, consent_type, policy_version)`** — РЕШЕНИЕ: НЕ добавлять. Каждый клик «Согласен» = отдельное audit-событие (требование 152-ФЗ). Дубликаты допустимы, проверка «дал ли пользователь согласие?» через `.exists()`.
- [x] [Review][Decision→Dismiss 3a] **`policy_version max_length=20`** — РЕШЕНИЕ: оставить 20. Используется простой формат `1.0`/`1.1`, SemVer-with-metadata не нужен.
- [x] [Review][Decision→Patch 4a] **Тест на отсутствие `delete_selected` в admin actions** — РЕШЕНИЕ: добавить тест (см. patch ниже). Двойную защиту через `get_actions` override НЕ добавляем — Django default достаточно, тест фиксирует инвариант.

### Patch (story-scope, fixable)

- [ ] [Review][Patch] **Создать `backend/apps/common/tests/__init__.py`** [backend/apps/common/tests/__init__.py] — Все остальные `apps/*/tests/` имеют `__init__.py` (banners, delivery, integrations, products). Отсутствие может вызвать конфликты импорта между `apps.common.tests` и `apps.common` namespace-пакетом при pytest-discovery.
- [ ] [Review][Patch] **`UserConsent.__str__`: обработать пустой `session_key` для полностью анонимного случая** [backend/apps/common/models.py:629-630] — Если `user is None` и `session_key=""`, выводится `"аноним () — ..."` с пустыми скобками. Заменить на условную ветку: `who = "аноним"` без скобок при пустом ключе.
- [ ] [Review][Patch] **`UserConsent.__str__`: использовать `timezone.localtime`** [backend/apps/common/models.py:630] — `f"{self.given_at:%d.%m.%Y}"` берёт naive UTC при `USE_TZ=True`, отдаёт неправильный день для вечерних MSK-согласий. Использовать `timezone.localtime(self.given_at).strftime("%d.%m.%Y")`.
- [ ] [Review][Patch] **`UserConsent`: CheckConstraint `user OR session_key`** [backend/apps/common/models.py + новая миграция] — Сейчас можно создать запись с `user=NULL, session_key=""` — orphan-row без субъекта. Добавить `Meta.constraints = [CheckConstraint(check=Q(user__isnull=False) | ~Q(session_key=""), name="userconsent_user_or_session_required")]`. Связан с тестом ниже.
- [ ] [Review][Patch] **`UserConsent`: `db_index` на горячих полях** [backend/apps/common/models.py + миграция] — Compliance-запросы фильтруют по `consent_type`, `given_at`, `session_key`. FK `user` индексирован автоматически. Добавить `db_index=True` на `consent_type`, `given_at`, `session_key`, либо `Meta.indexes = [Index(fields=["consent_type", "-given_at"])]`.
- [ ] [Review][Patch] **`user_agent`: ограничить длину** [backend/apps/common/models.py:613 + миграция] — `TextField(blank=True)` без верхней границы — DoS / storage bloat при больших UA-строках. Заменить на `CharField(max_length=512)` с обрезкой при сохранении.
- [ ] [Review][Patch] **Frontend: try/catch вокруг `fetch` и обработка 5xx ≠ 404** [frontend/src/app/(blue)/privacy-policy/page.tsx:26-36] — Сейчас `!res.ok` для всего возвращает `null` → `notFound()`. Сетевая ошибка/таймаут/5xx превращаются в 404 для SEO. Обернуть в try/catch (network errors), 4xx → `null`, 5xx → пробросить (Next.js error boundary).
- [ ] [Review][Patch] **Frontend: guard для malformed JSON и `content`/`title` = null** [page.tsx:31-35] — `res.json()` бросает на не-JSON ответе, ломает SSR. `dangerouslySetInnerHTML={{ __html: undefined }}` рендерит сломанный HTML. Обернуть `await res.json()` в try/catch; добавить `if (!page.title || !page.content) notFound()`.
- [ ] [Review][Patch] **Frontend: дедуплицировать `fetchPrivacyPolicy` через React `cache()`** [page.tsx:26-45] — `generateMetadata` и `PrivacyPolicyPage` оба вызывают `fetchPrivacyPolicy()` → две запроса к backend на каждый запрос. `import { cache } from 'react'; const fetchPrivacyPolicy = cache(async () => {...})`.
- [ ] [Review][Patch] **`UserConsentAdmin.search_fields`: убрать `ip_address`** [backend/apps/common/admin.py:307] — `GenericIPAddressField` + `icontains` поиск даёт неинтуитивное поведение и медленные запросы. Оставить только `user__email`. Поиск по IP делать через явный фильтр.
- [ ] [Review][Patch] **Frontend tests: добавить кейсы для malformed JSON, null content, отсутствующего title** [frontend/src/app/(blue)/privacy-policy/__tests__/page.test.tsx] — Сейчас покрыты только success / 404 / `is_published=false`. После Patch выше (`page.tsx`) покрыть: 500 от API, не-JSON body, `content=null`, `title=undefined`.
- [ ] [Review][Patch] **Backend tests: anonymous-only инварианты** [backend/apps/common/tests/test_user_consent.py] — Добавить: (1) `__str__` для `session_key` короче 8 символов (slice не падает, но надо зафиксировать формат); (2) после Patch CheckConstraint — тест что `UserConsent.objects.create(user=None, session_key="")` поднимает `IntegrityError`.
- [ ] [Review][Patch 1a] **Удалить мёртвый guard `is_published === false`** [frontend/src/app/(blue)/privacy-policy/page.tsx:55] — Заменить `if (!page || page.is_published === false) notFound();` на `if (!page) notFound();`. Также удалить из `PageData` interface optional поле `is_published?: boolean` (теперь не используется).
- [ ] [Review][Patch 1a] **Удалить тест мёртвого guard** [frontend/src/app/(blue)/privacy-policy/__tests__/page.test.tsx:97-102] — Удалить тест `it('вызывает notFound при is_published=false', ...)` целиком (тест проходит только из-за фейкового мока, в реальности кейс невозможен).
- [ ] [Review][Patch 4a] **Добавить тест что `delete_selected` отсутствует в admin actions** [backend/apps/common/tests/test_user_consent.py] — Создать тест `test_user_consent_admin_excludes_delete_selected_action`: создать `UserConsentAdmin(UserConsent, admin.site)`, вызвать `model_admin.get_actions(request)`, проверить `assert "delete_selected" not in actions`. Защищает от регрессии если кто-то ошибочно поднимет `has_delete_permission`.

### Deferred (не блокирует merge, в `_bmad-output/implementation-artifacts/deferred-work.md`)

- [x] [Review][Defer] **`cache_page` в `pages/views.py:49` invalidation broken** [backend/apps/pages/views.py:49] — pre-existing
- [x] [Review][Defer] **`policy_version` не связан с фактической версией контента Page** [backend/apps/common/models.py:617-621] — pre-existing
- [x] [Review][Defer] **Russian-only labels (no `gettext_lazy`)** [backend/apps/common/models.py + admin.py] — pre-existing
- [x] [Review][Defer] **Admin UX: нет `date_hierarchy`/`list_per_page`/`ordering`** [backend/apps/common/admin.py:301-325] — polish
- [x] [Review][Defer] **Нет data migration для backfill согласий легаси-пользователей** — out of scope
- [x] [Review][Defer] **`NEXT_PUBLIC_API_URL` fallback на localhost в проде** [page.tsx:22-24] — project-wide pattern
- [x] [Review][Defer] **`revalidate: 3600` = до 1ч stale legal text** [page.tsx:28] — спека мандатирует, нужна координация с backend
- [x] [Review][Defer] **Card/Breadcrumb prop validation, accessibility** [page.tsx] — компонентный уровень
- [x] [Review][Defer] **`on_delete=SET_NULL` теряет атрибуцию аудита после удаления юзера** [backend/apps/common/models.py:594-602] — спека мандатирует SET_NULL, денормализация email — отдельная compliance-story
- [x] [Review][Defer] **Vitest test brittle (нет проверок method/headers/body)** — test polish
- [x] [Review][Defer] **`has_view_permission` не переопределён — любой staff видит ПДн** [backend/apps/common/admin.py] — project-wide admin convention
- [x] [Review][Defer] **`ip_address` nullable** [backend/apps/common/models.py:611] — спека мандатирует `null=True, blank=True`
- [x] [Review][Defer] **`__str__` format не запинен в тесте** [backend/apps/common/tests/test_user_consent.py:80-83] — test polish

### Dismissed (false positives / handled elsewhere) — 20+ items

- XSS via `dangerouslySetInnerHTML` — `apps/pages/models.py:56,77` запускает `bleach.clean(tags=[], strip=True)` на save (verified)
- `HttpRequest` import — verified в `admin.py:12`
- Bulk delete bypass — Django убирает `delete_selected` action когда `has_delete_permission(request)` возвращает False
- `__str__` при `user.email=None` — User model требует unique non-null email
- `__str__` при `given_at=None` — `auto_now_add=True` всегда выставляет
- `NEXT_PUBLIC_API_URL` trailing slash — project convention without trailing slash
- `Response.json` static — Node 18+ guaranteed (Next.js 15)
- Page slug collision в integration test — Django TestCase rolls back per test
- `cache_page` flakiness — тест явно вызывает `cache.clear()` перед каждым запросом
- Spec wording IntegrityError vs ValidationError — спека OR
- Spec URL `${API_URL}/api/pages/...` vs реальный `/pages/...` — реализация корректна (project convention NEXT_PUBLIC_API_URL уже содержит `/api/v1`), нужно поправить spec literal а не код
- robots metadata — default index/follow OK
- module-scope `breadcrumbItems` — premature i18n abstraction
- AC-3 broader interpretation (delete_permission=False) — auditor подтвердил, что соответствует «только для чтения»
- lucide-react не замокан — happy-dom рендерит SVG корректно
- `clear_db_before_test` для User — тесты используют уникальные email
- `create_superuser` extra fields — verifiable при запуске тестов; пока не блокер
- Test name `test_privacy_policy_page_is_available_only_after_publication` слегка неточен — но проверяет 404 до публикации и 200 после, корректно по сути
- Тест создаёт superuser избыточно — style nit
- `__str__` em-dash format — стилистика, не функциональный риск

## Change Log

- 2026-05-09: Реализована Story 35.1: модель и admin согласий пользователей, миграция, страница политики ПДн, backend/frontend тесты и BMAD статус `review`.
- 2026-05-09: Code review run — 4 decision-needed / 12 patch / 13 defer / 20+ dismiss. Раздел `Review Findings` добавлен.
