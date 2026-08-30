---
title: 'Маршрутизация email о регистрации B2B-клиента на регионального менеджера'
type: 'feature'
created: '2026-07-21'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'f7c267f8'
context:
  - '{project-root}/backend/apps/users/serializers.py'
  - '{project-root}/backend/apps/users/tasks.py'
  - '{project-root}/backend/apps/common/models.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** При регистрации нового B2B-клиента письмо уходит только общим админам (`NotificationRecipient` с `notify_user_verification`). Региональные менеджеры не получают заявку своего региона и не могут вовремя её обработать.

**Approach:** По стране (выбирается в форме) и первым 2 цифрам ИНН (= код субъекта РФ) определять ответственного менеджера и **дополнительно** к текущему письму админам ставить в очередь письмо этому менеджеру. Сопоставление «код региона / страна → менеджер» и резервные адреса хранятся в редактируемой через Django Admin БД-модели.

## Boundaries & Constraints

**Always:**
- Маршрутизация срабатывает только для B2B (`role != "retail"`) заявок. Для `country == "Россия"` менеджер определяется по `tax_id[:2]`; для `country in ("Беларусь","Казахстан")` — по стране (→ Лопатина), ИНН не требуется.
- Письмо менеджеру **дополняет**, а не заменяет существующее `send_admin_verification_email`. Существующий поток админ-уведомлений не трогать.
- Если менеджер не определён (нет активного правила для кода/страны, ИНН пустой/короче 2 цифр, `country=="Россия"` но код неизвестен) → письмо уходит на резервные адреса (Чернов + admin).
- УФО → Лопатина (`d.lopatina@freesportopt.ru`). ЮФО делится по регионам: Лопатина = Волгоградская(34), Астраханская(30), Калмыкия(08), Ростовская(61); Исакова = Краснодарский(23), Крым(91); неперечисленные ЮФО (Адыгея 01, Севастополь 92) → Исакова.
- Отправка асинхронная (Celery `shared_task` с retry, как соседние таски в `tasks.py`). Сбой письма менеджеру не должен ломать регистрацию.
- Один код региона → ровно один менеджер; резерв → несколько адресов. Resolver возвращает список email.

**Ask First:**
- Точные коды новых территорий (ДНР/ЛНР/Запорожская) и любые коды регионов, в которых не уверены при сидинге — подтвердить у пользователя перед фиксацией значений в data-миграции.

**Never:**
- Не добавлять сторонние сервисы геолокации/справочники ФНС по сети — сопоставление статично, из БД.
- Не менять роль/ветку `retail` (мгновенный доступ) и логику верификации.
- Не расширять список стран сверх России/Беларуси/Казахстана.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| РФ, регион с менеджером | role=wholesale_level1, country=Россия, tax_id="7701234567" | Письмо на менеджера ЦФО (Гусев) + текущее письмо админам | N/A |
| РФ, ЮФО split | country=Россия, tax_id="2312345678" (код 23) | Письмо Исаковой | N/A |
| РФ, УФО | country=Россия, tax_id="6612345678" (код 66) | Письмо Лопатиной | N/A |
| Зарубеж | country=Беларусь | Письмо Лопатиной (по стране), ИНН игнорируется | N/A |
| Неизвестный код | country=Россия, tax_id="0012345678" | Письмо на резерв (Чернов+admin) | Логируется предупреждение |
| Пустой/короткий ИНН | country=Россия, tax_id="" или "7" | Письмо на резерв | Логируется предупреждение |
| retail | role=retail | Маршрутизация не запускается | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/common/models.py` — добавить модель `ManagerRoutingRule` (правила: тип совпадения + значение → менеджер) рядом с `NotificationRecipient`.
- `backend/apps/common/admin.py` — зарегистрировать `ManagerRoutingRuleAdmin` (list_display/filter по типу, активности, округу).
- `backend/apps/common/migrations/` — schema-миграция модели + data-миграция сидинга правил из Excel-таблицы.
- `backend/apps/users/models.py` — добавить `User.country` (choices Россия/Беларусь/Казахстан, default "Россия").
- `backend/apps/users/migrations/` — миграция поля `country`.
- `backend/apps/users/services/region_routing.py` — **новый** сервис `resolve_manager_recipients(country, tax_id) -> list[str]` (страна → ИНН-код → резерв).
- `backend/apps/users/tasks.py` — новый таск `send_manager_region_email(user_id)` (рендер шаблона, `send_mail`, retry как соседи).
- `backend/apps/users/serializers.py` — `country` в `Meta.fields`; валидация обязательности для B2B; постановка `send_manager_region_email.delay(...)` в `create()` и в `_link_matched_1c_customer()` (обе B2B-ветки, где уже вызывается `send_admin_verification_email`).
- `backend/templates/emails/manager_region_notification.{html,txt}` — **новые** шаблоны (клиент, компания, ИНН, роль, регион/страна, ссылка в админку).
- `frontend/src/components/auth/B2BRegisterForm.tsx` + `schemas/authSchemas.ts` + `types/api.ts` + `services/authService.ts` — селект «Страна» (Россия/Беларусь/Казахстан, обязателен), проброс в payload.
- `backend/apps/users/tests/`, `backend/apps/common/tests/`, `frontend/.../__tests__/` — тесты resolver, таска, сериализатора, формы.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/common/models.py` -- добавить `ManagerRoutingRule(match_type[inn_region|country|fallback], match_value, manager_name, manager_email, federal_district, is_active)` с индексом по `(match_type, match_value, is_active)` -- гибкое БД-хранилище маршрутов.
- [x] `backend/apps/common/migrations/xxxx_manager_routing_rule.py` -- schema + data-миграция: засеять все коды субъектов РФ по округам (СКФО→Милованов; СЗФО/УФО→Лопатина; ЦФО/ПФО→Гусев; СибФО/ДФО→Исакова; ЮФО split), country-правила Беларусь/Казахстан→Лопатина, fallback→Чернов+admin. Коды новых территорий — по подтверждению (Ask First).
- [x] `backend/apps/common/admin.py` -- `@admin.register(ManagerRoutingRule)` с list_display, list_filter, search -- редактирование без деплоя.
- [x] `backend/apps/users/models.py` + миграция -- поле `User.country` (choices, default "Россия").
- [x] `backend/apps/users/services/region_routing.py` -- `resolve_manager_recipients(country, tax_id)`: 1) country≠Россия → country-правило; 2) иначе `tax_id[:2]` (только 2 цифры) → inn_region-правило; 3) пусто → fallback-правила. Возвращает список активных email (без дублей). Логирует, когда сработал fallback.
- [x] `backend/apps/users/tasks.py` -- `send_manager_region_email(user_id)`: собрать получателей через resolver, отрендерить `manager_region_notification.{html,txt}`, `send_mail(fail_silently=False)`, `@shared_task` с retry по `SMTPException/ConnectionError`. Пустой список получателей → лог + return False.
- [x] `backend/templates/emails/manager_region_notification.html|txt` -- шаблон письма менеджеру.
- [x] `backend/apps/users/serializers.py` -- `country` в `fields`; в `validate()` требовать `country` для `role != "retail"`; после `send_admin_verification_email.delay(...)` (в `create()` и `_link_matched_1c_customer()` для B2B) добавить `send_manager_region_email.delay(user.id)`.
- [x] `frontend/src/schemas/authSchemas.ts`, `types/api.ts`, `services/authService.ts`, `components/auth/B2BRegisterForm.tsx` -- поле-селект «Страна» (обязательное для B2B, default Россия) + проброс в `RegisterRequest`.
- [x] Тесты -- resolver (все строки I/O-матрицы), таск (получатели/пустой список), сериализатор/интеграция (delay вызывается для B2B, не для retail), форма (рендер и submit со «Страна»).

**Acceptance Criteria:**
- Given активные правила маршрутизации в БД, when B2B-клиент из РФ регистрируется с ИНН региона X, then `send_manager_region_email` ставится в очередь и письмо уходит менеджеру региона X **в дополнение** к письму админам.
- Given B2B-клиент выбрал страну Беларусь или Казахстан, when он регистрируется, then письмо уходит Лопатиной независимо от значения ИНН.
- Given ИНН не даёт известного кода региона (или country=Россия и код не засеян), when B2B-клиент регистрируется, then письмо уходит на резервные адреса (Чернов + admin) и факт fallback логируется.
- Given `role == "retail"`, when пользователь регистрируется, then маршрутизация менеджеру не запускается и поведение не меняется.
- Given B2B-заявка привязывается к существующей 1С-записи (email совпал), when создаётся заявка, then письмо менеджеру ставится в очередь так же, как для новой B2B-регистрации.
- Given B2B-регистрация без переданного `country`, when создаётся пользователь, then `country` принимает значение по умолчанию «Россия» и маршрутизация идёт по ИНН (жёсткой ошибки нет).

## Spec Change Log

- **2026-07-21 (impl):** Строгая серверная валидация `country` для B2B заменена на default «Россия» без ошибки (решение пользователя). Причина: строгое требование ломало регистрацию B2B в ~6 файлах существующих тестов, а требование звучало как «Россия по умолчанию» (дефолт всегда есть). Avoids: массовую правку несвязанных тестов и расхождение с формулировкой пользователя. KEEP: `country` остаётся в форме и API, фронтенд-селектор с default «Россия».
- **2026-07-21 (impl):** Коды новых территорий подтверждены пользователем: ДНР=93, ЛНР=94, Запорожская=90 → Лопатина.
- **2026-07-21 (tests):** Прогон в Docker выявил, что тестовая среда выполняет миграции (включая data-сид), поэтому unit-тесты resolver получили autouse-фикстуру очистки `ManagerRoutingRule`, а сравнения нескольких fallback-получателей переведены на множества (порядок задаётся Meta.ordering по email). Также имя индекса зафиксировано явно в модели (`common_mrr_type_val_act_idx`), чтобы `makemigrations --check` проходил.
- **2026-07-21 (review/patch):** Добавлен вызов `send_manager_region_email.delay` в `PortalLinkConfirmView` (`apps/users/views/authentication.py`) — путь подтверждения привязки к 1С (email отличался) тоже переводит заявку в pending и слал письмо только админам. Теперь менеджер уведомляется во всех B2B-путях входа в pending.

## Design Notes

`ManagerRoutingRule` — плоская модель вместо двух связанных: `match_type ∈ {inn_region, country, fallback}`, `match_value` = 2-значный код («23»), название страны («Беларусь») или «default» для fallback. Уникальности на `(match_type, match_value)` нет — несколько строк с одинаковым ключом дают нескольких получателей (нужно для fallback = Чернов + admin). Пример resolver:

```python
def resolve_manager_recipients(country, tax_id):
    rules = ManagerRoutingRule.objects.filter(is_active=True)
    if country and country != "Россия":
        emails = rules.filter(match_type="country", match_value=country)
    else:
        code = (tax_id or "")[:2]
        emails = rules.filter(match_type="inn_region", match_value=code) if len(code) == 2 else rules.none()
    result = list(emails.values_list("manager_email", flat=True))
    if not result:
        logger.warning("Region routing fallback", extra={"country": country, "tax_id_prefix": (tax_id or "")[:2]})
        result = list(rules.filter(match_type="fallback").values_list("manager_email", flat=True))
    return list(dict.fromkeys(result))
```

Коды субъектов РФ по округам для сидинга — стандартная таблица «первые 2 цифры ИНН». Коды присоединённых территорий (ДНР/ЛНР/Запорожская) уточнить перед сидингом (Ask First); они входят в зону Лопатиной по файлу.

## Verification

**Commands:**
- `docker compose --env-file .env -f docker/docker-compose.test.yml exec backend pytest -xvs apps/users/tests/ apps/common/tests/ -k "routing or region or country"` -- expected: все новые тесты зелёные.
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run` -- expected: нет незакоммиченных изменений схемы.
- `cd frontend && npm run test -- src/components/auth/__tests__/B2BRegisterForm.test.tsx` -- expected: тесты формы (в т.ч. «Страна») зелёные.

**Manual checks:**
- В Django Admin открыть `ManagerRoutingRule`: правила видны, редактируются; деактивация правила исключает менеджера из рассылки.

## Suggested Review Order

**Ядро маршрутизации**

- Алгоритм: страна → код субъекта РФ (ИНН[:2]) → резерв, дедуп получателей
  [`region_routing.py:17`](../../backend/apps/users/services/region_routing.py#L17)

**Модель данных и сидинг (редактируется в админке)**

- Плоская модель правил: match_type + match_value → менеджер (несколько строк = несколько получателей)
  [`models.py:945`](../../backend/apps/common/models.py#L945)

- Начальный сид: коды субъектов по округам, ЮФО split, страны, резерв
  [`0018_seed_manager_routing_rules.py:43`](../../backend/apps/common/migrations/0018_seed_manager_routing_rules.py#L43)

- Админ-интерфейс правил
  [`admin.py:609`](../../backend/apps/common/admin.py#L609)

**Постановка письма в очередь (все B2B-пути → pending)**

- Новая B2B-регистрация и привязка к 1С (email совпал)
  [`serializers.py:173`](../../backend/apps/users/serializers.py#L173)

- Подтверждение привязки к 1С (email отличался) — добавлено в ревью
  [`authentication.py:611`](../../backend/apps/users/views/authentication.py#L611)

- Celery-таск: получатели → рендер шаблона → send_mail (retry)
  [`tasks.py:401`](../../backend/apps/users/tasks.py#L401)

**Поле «Страна» (default «Россия»)**

- Модель User
  [`models.py:132`](../../backend/apps/users/models.py#L132)

- API-поле сериализатора
  [`serializers.py:64`](../../backend/apps/users/serializers.py#L64)

- Селект в B2B-форме
  [`B2BRegisterForm.tsx:410`](../../frontend/src/components/auth/B2BRegisterForm.tsx#L410)

- Zod-схема и тип запроса
  [`authSchemas.ts:144`](../../frontend/src/schemas/authSchemas.ts#L144)

**Тесты**

- Resolver: все ветки I/O-матрицы + дедуп + неактивные правила
  [`test_region_routing.py:42`](../../backend/tests/unit/test_region_routing.py#L42)

- Интеграция: B2B ставит письмо менеджеру, retail — нет
  [`test_registration_emails.py:122`](../../backend/tests/integration/test_registration_emails.py#L122)
