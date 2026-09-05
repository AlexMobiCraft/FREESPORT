---
baseline_commit: 8c8f69c5
---

# Story 41.2: Фиксация согласия при привязке к записи 1С

Status: ready-for-dev

> 🟢 **Blast radius LOW** (GitNexus CLI, `--repo C:\Users\1\DEV\FREESPORT`, индекс `up-to-date` на `8c8f69c`, 2026-09-05). `UserRegistrationView` — 0 upstream-потребителей, 0 затронутых процессов. `UserRegistrationSerializer._link_matched_1c_customer` — 0 upstream-потребителей (вызовов нет вообще). HIGH/CRITICAL нет.
> 🔴 **Главное, что нужно знать до первой строки кода: ветка, которую чинит эта стори, сегодня недостижима.** Guard `if not pending_1c_link:` (`authentication.py:139`) на `8c8f69c5` **никогда не срабатывает**: флаги `_pending_admin_review` / `_pending_link_confirmation` выставляет только `UserRegistrationSerializer._link_matched_1c_customer`, а он не вызывается ни из одного места (`create()` перестал его вызывать в коммите `ffee94d5` от 2026-07-26, «отключить автопривязку регистрации к записи 1С по ИНН»). Маршрут `PortalLinkConfirmView` тоже снят (`urls.py:55-65`, закомментирован). Значит **прямо сейчас согласие пишется при любой регистрации**, и наблюдаемого бага нет.
> 🔴 **Из этого следует главное требование к тестам:** обычный HTTP-тест регистрации в эту ветку **не попадёт** и проверит пустоту. Воспроизводить ветку нужно патчем `UserRegistrationSerializer.create` — точный рецепт в Dev Notes → «Как вообще протестировать мёртвую ветку».
> ⚠️ **Стори не закрывает «4606 записей 1С без согласия».** Контекст эпика упоминает их рядом с FR-41-03, но это разные вещи: записи 1С созданы импортом, их субъекты никакой формы не заполняли, и никакой код регистрации согласия за них не создаст. Правовое основание для них — иное (данные получены от контрагента по договору), и вопрос находится вне объёма эпика. Не пытаться закрыть его здесь.
> ⚠️ **В ветке привязки нового пользователя НЕ создаётся.** `create()` возвращал бы `_link_matched_1c_customer(matched_customer, …)` — то есть **найденную запись 1С**, на которую заявитель ставит пароль. Формулировка AC эпика «привязанная к созданному пользователю» неточна; согласие крепится к тому объекту `User`, который вернул `serializer.save()`. Разбор — в Dev Notes → «К кому крепится согласие».
> ⚠️ **Находка сверх текста эпика:** в ветке привязки терялся бы и `_marketing_consent` — `create()` выходил через `return` **до** строки 273, где флаг выставляется. Без правки отмеченное согласие на рассылку молча пропадало бы. Учтено в AC3.
> 🚫 **Стори не удаляет мёртвый код.** `_link_matched_1c_customer` и `PortalLinkConfirmView` оставлены в кодовой базе осознанно (решение 2026-07-26: «привязку могут вернуть, но только с настоящим доказательством права на компанию»). Удаление вынесено в `deferred-work.md` и в объём этой стори не входит.
> 🚫 **Стори не трогает фронтенд, модель, миграции и API-контракт.** `UserConsent` не меняется (это стори 41.9), `openapi.yaml` и типы фронта не регенерируются — ответ эндпоинта остаётся байт в байт прежним.

## Story

As a **оператор персональных данных**,
I want **чтобы согласие, поставленное пользователем при регистрации, попадало в журнал и тогда, когда регистрация уходит на привязку к записи 1С**,
so that **по каждому человеку, чью форму мы приняли и чьи ПДн обрабатываем, было доказательство полученного согласия**.

**Закрывает:** FR-41-03. **Соблюдает:** NFR-41-01, NFR-41-03.

**Фактическая ценность (сказать прямо):** латентный дефект. Ветка привязки отключена, поэтому сегодня журнал полон. Стори гарантирует, что при возврате привязки — а решение 2026-07-26 его прямо допускает — согласие не начнёт теряться молча. Цена ошибки высока и асимметрична: пропущенная запись обнаруживается только при проверке регулятором, восстановить её задним числом нельзя.

## Acceptance Criteria

### AC1 (FR-41-03) — согласие фиксируется и в ветке привязки

**Given** регистрация прошла валидацию и `serializer.save()` вернул объект `User`
**When** этот объект помечен `_pending_admin_review` или `_pending_link_confirmation`
**Then** создаётся запись `UserConsent` с `consent_type="pdp_contract"`, привязанная к **тому самому** объекту `User`, который вернул `serializer.save()`
**And** заполнены `ip_address` (через `get_consent_ip_address(request)`) и `user_agent` (через `sanitize_consent_user_agent(...)`) — теми же helper'ами, что и в обычной ветке
**And** `policy_version` остаётся значением по умолчанию `"1.0"` — поле в этой стори **не** заполняется осмысленно (это объём стори 41.9)
**And** запись создаётся внутри того же `transaction.atomic()`, что и `serializer.save()`

### AC2 (FR-41-03) — выдача токенов и PII не изменилась

**Given** та же регистрация в ветке привязки
**When** создана запись согласия
**Then** ответ по-прежнему `201 Created` с телом ровно `{"message": "Если данные совпадают с записью в 1С, дальнейшие инструкции отправлены на указанный email."}`
**And** в ответе **нет** ключей `refresh`, `access` и **нет** объекта `user` — персональные данные найденной записи 1С не раскрываются
**And** ветка ответа `if pending_1c_link:` (`authentication.py:158-167`) остаётся на месте и не сливается с обычной

### AC3 (FR-41-03) — рассылка следует отметке пользователя

**Given** регистрация уходит на привязку
**When** пользователь **не** отмечал согласие на рассылку
**Then** запись `marketing_email` **не** создаётся — у `User` ровно одна запись `UserConsent`

**Given** та же ветка привязки
**When** пользователь **отметил** согласие на рассылку (`marketing_consent: true`)
**Then** создаётся и `pdp_contract`, и `marketing_email` — так же, как в обычной регистрации
**And** для этого `_marketing_consent` выставляется на возвращаемом объекте и в ветке привязки тоже (сейчас `create()` вышел бы через `return` до строки 273 и флаг потерялся бы)

### AC4 (регрессия) — обычная регистрация не изменилась

**Given** регистрация без совпадения с записью 1С — то есть **любая** регистрация на текущем коде
**When** она завершается
**Then** поведение прежнее: одна запись `pdp_contract` (+ `marketing_email` при отметке), тот же ответ, те же три письма в очереди
**And** все существующие тесты `backend/tests/integration/test_auth_registration_consent.py` (24 тест-функции, часть параметризована) и `backend/tests/integration/test_portal_registration_1c_link.py` зелёные **без правок**
**And** правка `create()` из Task 3 не задевает `backend/tests/unit/test_serializers/test_user_serializers.py` (unit-покрытие `UserRegistrationSerializer`) и `backend/tests/regression/test_epic_28_intact.py` — оба набора прогоняются отдельно и обязаны остаться зелёными

### AC5 (FR-41-03) — сбой записи согласия откатывает регистрацию целиком

**Given** ветка привязки
**When** создание `UserConsent` падает с `DatabaseError`
**Then** транзакция откатывается целиком — объект `User` не остаётся в изменённом состоянии, частичной записи нет
**And** тест **не** проверяет отсутствие постановки писем в очередь: `send_admin_verification_email.delay` вызывается внутри `create()` и при откате уже поставлен — это известное свойство кода, а не дефект этой стори

### AC6 (NFR-41-01) — тесты

**Given** изменения бэкенда
**When** прогоняется набор
**Then** добавлены integration-тесты, покрывающие AC1, AC2, AC3 (оба случая) и AC5
**And** ветка привязки в тестах воспроизводится патчем `UserRegistrationSerializer.create` (рецепт в Dev Notes), а **не** правкой продового кода ради тестируемости
**And** тесты лежат в `backend/tests/integration/test_auth_registration_consent.py` рядом с существующими — новый файл не заводится
**And** прогон выполняется через Docker (`docker-compose.test.yml`), локальный SQLite не используется

### AC7 (границы) — что стори НЕ делает

**Then** не удаляется мёртвый код `_link_matched_1c_customer` и `PortalLinkConfirmView`, не восстанавливается маршрут `auth/portal-link/confirm/`
**And** не включается обратно автопривязка регистрации к записи 1С по ИНН
**And** не меняются модель `UserConsent`, `CONSENT_TYPE_CHOICES`, миграции — поля источника и версии текста согласия добавляет стори 41.9
**And** не пишется согласие в `PortalLinkConfirmView`: галочка ставится один раз, на форме регистрации, и фиксируется там же — дубль на шаге подтверждения был бы второй записью об одном согласии
**And** не трогается фронтенд (`RegisterForm.tsx`, `B2BRegisterForm.tsx`), `docs/api/openapi.yaml`, `frontend/src/types/api.ts` — контракт эндпоинта не меняется
**And** не создаются согласия задним числом для 4606 импортированных записей 1С

## Tasks / Subtasks

- [ ] **Task 1 — Зафиксировать точку отсчёта** (AC: 4)
  - [ ] Ветка `feature/story-41-2-consent-on-1c-link` от `develop`
  - [ ] Прогнать до правок: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest tests/integration/test_auth_registration_consent.py tests/integration/test_portal_registration_1c_link.py tests/unit/test_serializers/test_user_serializers.py` — записать число passed в Debug Log
- [ ] **Task 2 — Снять guard с записи согласия** (AC: 1, 2)
  - [ ] `backend/apps/users/views/authentication.py:129-156`: вынести создание `UserConsent` из-под `if not pending_1c_link:` — согласие пишется всегда, когда `serializer.save()` отработал
  - [ ] Переменную `pending_1c_link` **сохранить**: она по-прежнему управляет формой ответа (строка 158)
  - [ ] Переписать комментарий на строках 132-134: нынешний текст утверждает «не создаём consent-запись … это не новая регистрация, а привязка» — это и есть исправляемая ошибка. Новый комментарий (на русском, NFR-41-03) должен объяснять: форму заполнил человек, галочку он поставил, ПДн уже обрабатываются — согласие фиксируется независимо от того, чем регистрация закончилась; `pending_1c_link` влияет только на ответ
  - [ ] Убедиться, что запись осталась **внутри** `with transaction.atomic()` (AC5)
- [ ] **Task 3 — Не терять отметку рассылки в ветке привязки** (AC: 3)
  - [ ] `backend/apps/users/serializers.py:239-274`: выставить `_marketing_consent` на возвращаемом объекте и на пути `_link_matched_1c_customer`, а не только на новом `user` (строка 273)
  - [ ] **Способ выбирает дев.** Требование одно и оно проверяемое: флаг должен пережить возврат мёртвой ветки **без дополнительных действий со стороны того, кто её вернёт**. Сегодня в `create()` ровно одна точка выхода (строка 274), и присваивание на строке 273 её покрывает — то есть правка «на месте» ничего не гарантирует на будущее: вернувший привязку добавит второй `return` и снова потеряет флаг
  - [ ] Приёмка этого требования — тест `_historic_link_create` из Task 4: он подменяет `create()` историческим вариантом и проходит по пути `_link_matched_1c_customer`. Зелёный тест означает, что флаг живёт **на пути привязки**, а не только в текущем теле `create()`. Где именно его поставить, чтобы тест прошёл, — решение дева
  - [ ] Комментарием (на русском) зафиксировать: флаг читается во view (`authentication.py:150`) и без него отмеченное согласие на рассылку теряется молча
- [ ] **Task 4 — Тесты ветки привязки** (AC: 1, 2, 3, 5, 6)
  - [ ] В `backend/tests/integration/test_auth_registration_consent.py` добавить helper, воспроизводящий ветку патчем `UserRegistrationSerializer.create` (рецепт — Dev Notes)
  - [ ] Тест AC1+AC2: `_pending_admin_review` → одна запись `pdp_contract` у вернувшегося `User`, `ip_address`/`user_agent` заполнены, ответ = ровно `{"message": ...}` без `access`/`refresh`/`user`
  - [ ] Тест того же для `_pending_link_confirmation` (вторая ветка флага)
  - [ ] Тест AC3 негативный: без `marketing_consent` — ровно одна запись
  - [ ] Тест AC3 позитивный: с `marketing_consent: true` — две записи, оба типа. **Обязательно через `_historic_link_create`**, а не через `_pending_create`: только он проходит по пути `_link_matched_1c_customer` и различает реализации Task 3
  - [ ] Тест AC5: патч `UserConsent.objects.create` на `DatabaseError` → проверить откат (объект `User` не сохранён / состояние не изменено); **не** проверять отсутствие `.delay`
- [ ] **Task 5 — Регрессия и качество** (AC: 4, 6)
  - [ ] Прогнать целиком: `make test-integration`, затем `make test-unit`; сверить с числами Task 1
  - [ ] Отдельно убедиться в зелёности `tests/unit/test_serializers/test_user_serializers.py` и `tests/regression/test_epic_28_intact.py` — Task 3 правит `create()`, который они покрывают
  - [ ] `black` + `flake8` через навык `backend-lint` (или Docker) — CI гоняет их с нулевым допуском
  - [ ] Убедиться, что `docs/api/openapi.yaml` и `frontend/src/types/api.ts` **не** изменились (`git status`)
- [ ] **Task 6 — Сдача** (AC: 7)
  - [ ] `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — убедиться, что затронуты только `UserRegistrationView.post`, `UserRegistrationSerializer.create` и тестовый файл
  - [ ] `File List` собрать по `git diff --name-only develop...HEAD`, **не** по памяти (трижды был неполон в 41.0, 41.3, 41.5)
  - [ ] Записать в Completion Notes, что дефект был латентным и как именно тесты достают ветку
  - [ ] Коммит и push — **только** по явной просьбе владельца

## Dev Notes

### Что есть сейчас (проверено чтением файлов на `8c8f69c5`)

`backend/apps/users/views/authentication.py:124-156`:

```python
def post(self, request, *args, **kwargs):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        with transaction.atomic():
            user = serializer.save()
            # Привязка к существующей 1С-записи (см. serializers._link_matched_1c_customer):
            # не создаём consent-запись и не выдаём JWT/PII найденной записи —
            # это не новая регистрация, а привязка ожидающая подтверждения/ручного одобрения.
            pending_1c_link = getattr(user, "_pending_admin_review", False) or getattr(
                user, "_pending_link_confirmation", False
            )
            if not pending_1c_link:            # <- строка 139, guard
                ip_address = get_consent_ip_address(request)
                user_agent = sanitize_consent_user_agent(request.META.get("HTTP_USER_AGENT"))
                UserConsent.objects.create(user=user, consent_type="pdp_contract", ...)
                if getattr(user, "_marketing_consent", False):
                    UserConsent.objects.create(user=user, consent_type="marketing_email", ...)
        if pending_1c_link:                     # <- строка 158, форма ответа
            return Response({"message": "Если данные совпадают ..."}, status=201)
        ...
```

Правка минимальна: снять один уровень отступа и переписать комментарий. Всё остальное в файле остаётся.

### Почему ветка мертва — и почему это не повод закрыть стори как неактуальную

Цепочка проверена по коду и по истории:

1. `_pending_admin_review` / `_pending_link_confirmation` выставляются **только** в `serializers.py:303` и `:313`, внутри `_link_matched_1c_customer`.
2. `_link_matched_1c_customer` не вызывается ниоткуда — `grep` по `backend/` даёт одно определение и ноль вызовов; GitNexus `impact --direction upstream` → `impactedCount: 0`.
3. Вызов убран коммитом `ffee94d5` (2026-07-26): из `create()` вырезаны три строки `matched_customer = getattr(self, "_matched_1c_customer", None) / if ... / return self._link_matched_1c_customer(...)`.
4. `PortalLinkConfirmView` живёт в коде, но маршрут закомментирован (`urls.py:55-65`) — эндпоинт был `AllowAny` и по подписанному токену менял email и пароль записи 1С.

Причина отключения (из тела `ffee94d5`): ИНН публичен, а email заполнен лишь у 149 из 4606 записей 1С — знание одного ИНН позволяло занять контрагента чужой компании. Код оставлен намеренно: «привязку могут вернуть, но только с настоящим доказательством права на компанию».

Именно поэтому guard чинится, а не удаляется: если привязку вернут, дефект станет боевым в тот же день, а забытая запись согласия — это ровно тот класс дефекта, который не находится тестами и всплывает при проверке.

### К кому крепится согласие

В ветке привязки **нового пользователя не создаётся**. До `ffee94d5` `create()` выглядел так:

```python
matched_customer = getattr(self, "_matched_1c_customer", None)
if matched_customer is not None:
    return self._link_matched_1c_customer(matched_customer, validated_data["email"], password)
```

То есть `serializer.save()` возвращал **найденную запись 1С** (`created_in_1c=True`), на которую заявитель ставит пароль, а не свежесозданного `User`. Формулировка AC эпика «привязанная к созданному пользователю» — неточность источника.

Правильное поведение, и оно же реализуется тривиально: крепить согласие к тому объекту, который вернул `serializer.save()` (переменная `user`). Это единственная связь, которая есть, и семантически она верна — этот аккаунт становится аккаунтом заявителя.

**Тонкость, которую надо понимать, но не решать в этой стори:** в подветке `_pending_link_confirmation` (email формы отличался от email в 1С) привязка ещё не подтверждена, и теоретически согласие ляжет на запись, которую заявитель так и не займёт. Это не делает запись ложной: она фиксирует факт, что конкретный человек с конкретного IP отправил форму с отметкой согласия. Различать такие записи в журнале будет поле источника из стори 41.9 — здесь этот вопрос закрывать нечем и не нужно.

### Как вообще протестировать мёртвую ветку

Через HTTP ветка недостижима: `validate()` больше не ищет `_matched_1c_customer`, поэтому никакой payload флаги не выставит. Не пытаться «подобрать данные» — это потерянный день.

Рабочий приём — обернуть настоящий `create`, чтобы он выставил флаг на реально созданном пользователе. Транзакция, ответ и helper'ы IP/UA при этом исполняются боевые:

```python
from unittest.mock import patch
from apps.users.serializers import UserRegistrationSerializer

def _pending_create(flag_name):
    """Обёртка над настоящим create(): помечает результат флагом привязки к 1С."""
    original_create = UserRegistrationSerializer.create

    def create_with_pending(self, validated_data):
        user = original_create(self, validated_data)
        setattr(user, flag_name, True)
        return user

    return patch.object(UserRegistrationSerializer, "create", create_with_pending)


def test_pending_admin_review_registration_creates_pdp_consent():
    client = APIClient()
    with _pending_create("_pending_admin_review"):
        response = post_register(client, trainer_payload(), REMOTE_ADDR="1.2.3.4",
                                 HTTP_USER_AGENT="ConsentTestAgent/1.0")

    assert response.status_code == status.HTTP_201_CREATED
    assert set(response.data) == {"message"}          # AC2: ни access, ни refresh, ни user
    user = User.objects.get(email=...)                 # email берётся из payload, не из ответа
    consent = UserConsent.objects.get(user=user)
    assert consent.consent_type == "pdp_contract"
    assert consent.ip_address == "1.2.3.4"
```

**Этой обёртки достаточно для AC1, AC2, AC5 и негативного AC3 — но не для позитивного AC3.** Она вызывает настоящий `create()`, а тот выставляет `_marketing_consent` на строке 273 **до** возврата. Такой тест пройдёт зелёным независимо от того, сделана правка Task 3 или нет, и устойчивость не докажет.

Для позитивного AC3 нужна вторая обёртка, воспроизводящая **исторический** путь — возврат через `_link_matched_1c_customer`, каким `create()` был до `ffee94d5`:

```python
def _historic_link_create(customer):
    """Эмулирует create() до ffee94d5: возврат найденной записи 1С вместо нового User."""
    def create_via_link(self, validated_data):
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")
        return self._link_matched_1c_customer(customer, validated_data["email"], password)

    return patch.object(UserRegistrationSerializer, "create", create_via_link)
```

`customer` — запись 1С из фикстуры (`created_in_1c=True`, `verification_status="unverified"`, `role=User.ROLE_UNREGISTERED`).

Обёртка подменяет `create()` целиком, поэтому присваивание, оставленное только в текущем теле `create()`, она обойдёт — и тест упадёт. Это не придирка теста, а ровно то свойство, которое требуется: сегодняшняя строка 273 исчезнет вместе с телом `create()`, когда привязку будут возвращать. Зелёный тест означает, что флаг живёт на пути привязки и переживёт такой возврат. Существующее присваивание на строке 273 при этом **остаётся** — обычная регистрация продолжает работать через него.

Две ловушки этих тестов:

- **Email из ответа взять нельзя** — в ветке привязки ответ содержит только `message`. Сохраняй payload в переменную и ищи пользователя по нему.
- **`autouse`-фикстура `_mute_b2b_notification_tasks`** (строки 35-46 файла) уже глушит три письма; отдельные `@patch` для них не нужны.

Для AC5 патчить `apps.users.views.authentication.UserConsent.objects.create` на `side_effect=DatabaseError` и проверять откат. Помнить: `serializer.save()` внутри уже вызвал `.delay` трёх писем — Celery вне транзакции, и это не регрессия данной стори.

### Ловушки, на которых легко потерять день

- **`get_client_ip` vs `get_consent_ip_address`.** Оба импортированы в `authentication.py:26-30`. В `UserConsent` пишется только `get_consent_ip_address` — он нормализует значение под PostgreSQL `inet` и возвращает `None` на мусоре. `get_client_ip` используется в этом файле для логов (строки 733, 746) и в consent-запись **не** годится: невалидный `X-Forwarded-For` уронит вставку.
- **`user_agent` обязателен через `sanitize_consent_user_agent`** — поле `CharField(max_length=512)`, сырой заголовок длиннее 512 символов или с surrogate-байтами валит вставку. Существующий тест `test_consent_record_captures_ip_and_user_agent_from_proxy_headers` это проверяет.
- **Не «оптимизировать» два `objects.create` в `bulk_create`.** Существующие тесты сверяют `count()` и набор типов; выигрыша нет, риск есть.
- **Не менять `policy_version`.** Соблазн проставить осмысленное значение здесь велик и прямо запрещён AC7: поле переопределяет стори 41.9, и разъехавшиеся значения из двух стори придётся мигрировать.
- **`pending_1c_link` вычисляется внутри `with`, читается снаружи** (строка 158). Python это позволяет, но при рефакторинге легко случайно занести `return` внутрь блока и получить коммит транзакции на выходе из `return` — оставить структуру как есть.
- **`flake8` с нулевым допуском.** Если Task 3 сделан «единой точкой выхода», проверить, что не осталось недостижимого кода и неиспользуемых имён.

### Связь со стори 41.9

41.9 добавит в `UserConsent` поля источника (`newsletter` / `registration` / `1c_link`) и версии текста согласия. Эта стори создаёт **третью** точку записи, и в перечислении источников 41.9 значение для привязки к 1С обязано появиться. Специально ничего готовить не нужно — достаточно, чтобы код записи остался в одном месте (`UserRegistrationView.post`), а не расползся по сериализатору: тогда 41.9 правит одну точку.

### Уроки предыдущих стори эпика 41

- **41.3:** настоящий дефект оказался не там, где его видел эпик. Здесь — тот же случай: эпик описывает FR-41-03 как живой баг, фактически он латентный. Если по ходу работы выяснится, что AC неверен, — править AC отдельной строкой Change Log, а не «по факту реализации».
- **41.0, 41.3, 41.5:** `File List` трижды был неполон — собирать по `git diff --name-only`.
- **41.5:** «done по прод-замеру, а не по мержу». К этой стори не применимо: наблюдаемого поведения на проде она не меняет, приёмка — по тестам.
- **41.1:** guard-подобные «оптимизации», сделанные из лучших побуждений, дают неверное поведение в редкой ветке. Комментарий в коде, объясняющий *почему*, здесь важнее самой правки.

### Project Structure Notes

- Backend-тесты — **только** через Docker с PostgreSQL. Конкретный файл: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs tests/integration/test_auth_registration_consent.py`. `--env-file` тестовому compose **не** передаётся.
- Не запускать два прогона pytest в одном compose-проекте параллельно — deadlock на `TRUNCATE` даёт лавину ложных падений.
- Маркеры проставляются автоматически по каталогу: файл в `tests/integration/` получает `integration`. Руками маркер не ставить.
- Покрытие считает `main.yml` (порог 73), быстрый гейт `backend-ci.yml` покрытие не меряет и `integration` не гоняет. Новые тесты в PR-гейт **не** попадут — это нормально, их прогонит `main.yml`.
- Комментарии и docstrings нового кода — на русском (NFR-41-03).
- Ветка `feature/*` от `develop`; прямые коммиты в `develop` запрещены.
- Новых зависимостей, миграций и правок API-контракта стори не вводит — `requirements.txt`, `openapi.yaml`, `npm run generate:types` не трогаются.

### Latest tech information

Веб-исследование не требуется и не проводилось: стори не добавляет и не обновляет ни одной библиотеки. Задействованы только уже установленные Django ORM (`transaction.atomic`), DRF (`APIView`) и `unittest.mock.patch` из стандартной библиотеки; версии зафиксированы в `backend/requirements.txt` и меняться не должны. Правовая рамка — ФЗ-152 ст. 9 (согласие фиксируется с датой и подтверждением факта) — покрыта существующими полями модели.

### Git intelligence

- `8c8f69c5` (HEAD, `develop`) — merge PR #127, стори 41.1. Последние пять коммитов — только документация и закрытие 41.1; конфликтов с этой стори нет.
- `ffee94d5` (2026-07-26) — коммит, сделавший ветку привязки мёртвой; читать его тело обязательно, там причина, по которой автопривязку нельзя возвращать «заодно».
- `95b75399` (2026-07-09) — коммит, добавивший guard `pending_1c_link`. Тогда ветка была живой, и guard имел смысл в части JWT/PII; ошибочной была только часть про consent.

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Functional Requirements] — FR-41-03 и примечание о снятом требовании чекбокса в checkout
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.2] — user story и AC-скелет
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#NonFunctional Requirements] — NFR-41-01, NFR-41-03, NFR-41-04 (последнее — объём 41.9)
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.9] — поля источника и версии текста согласия, третья точка записи
- [Source: backend/apps/users/views/authentication.py:124-167] — `UserRegistrationView.post`, guard и форма ответа
- [Source: backend/apps/users/views/authentication.py:26-30,733,746] — импорт helper'ов, отличие `get_client_ip` от `get_consent_ip_address`
- [Source: backend/apps/users/serializers.py:239-274] — `create()`, выставление `_marketing_consent` на строке 273
- [Source: backend/apps/users/serializers.py:276-316] — `_link_matched_1c_customer`, флаги на строках 303 и 313, docstring «НЕ ИСПОЛЬЗУЕТСЯ»
- [Source: backend/apps/users/urls.py:55-65] — снятый маршрут `auth/portal-link/confirm/`
- [Source: backend/apps/common/models.py:586-664] — модель `UserConsent`, `CONSENT_TYPE_CHOICES`, `policy_version` с default `1.0`
- [Source: backend/apps/common/utils/consent_audit.py:121-153] — `sanitize_consent_user_agent`, `get_consent_ip_address`
- [Source: backend/apps/common/views.py:417-428] — вторая точка записи согласия (подписка), образец двойной записи в одной транзакции
- [Source: backend/tests/integration/test_auth_registration_consent.py:35-46,130-160] — `autouse`-фикстура глушения писем и существующие тесты записи согласия
- [Source: backend/tests/integration/test_portal_registration_1c_link.py:1-17] — регрессионный набор по отключённой автопривязке
- [Source: backend/tests/unit/test_serializers/test_user_serializers.py] — unit-покрытие `UserRegistrationSerializer.create`, задевается правкой Task 3
- [Source: git ffee94d5] — отключение автопривязки, причина и решение сохранить код
- [Source: git 95b75399] — введение guard `pending_1c_link`
- [Source: project-context.md] — Docker-only тесты, PostgreSQL, русские комментарии, GitNexus-дисциплина
- [Source: backend/docs/testing-standards.md] — автоматические маркеры, что гоняет `backend-ci.yml` и `main.yml`

## Change Log

| Дата | Версия | Изменение | Автор |
|---|---|---|---|
| 2026-09-05 | 1.0 | Стори создана. Ключевое отличие от текста эпика: дефект признан латентным — ветка привязки недостижима с `ffee94d5` (2026-07-26). Добавлены AC3 (потеря `_marketing_consent`) и AC6 (рецепт тестирования мёртвой ветки) сверх скелета эпика. | Alex / create-story |

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
