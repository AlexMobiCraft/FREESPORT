---
title: 'Бонусная программа для тренеров + маппинг статусов УТ 11'
type: 'feature'
created: '2026-07-25'
status: 'done'
baseline_commit: '310dbf1fe5c75a125af7094d7e2ff693e5d7e3bd'
review_loop_iteration: 1
context:
  - '{project-root}/project-context.md'
  - '{project-root}/docs/guides/bonus-program-trainers.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Тренеры закупают товар для учеников и команд, но система никак их не поощряет — нет ни начисления вознаграждения, ни учёта выплат, ни истории для тренера. Дополнительно: импорт статусов из 1С нерабочий — `STATUS_MAPPING` ждёт значения, которых в УТ 11 не существует («Отгружен», «Доставлен»), поэтому реальный статус «Закрыт» отбрасывается как unknown ещё до записи в БД.

**Approach:** Расширить `STATUS_MAPPING` реальными статусами УТ 11 и добавить приложение `apps/bonuses` с журналом операций (ledger): автоначисление процента от суммы товаров при закрытии мастер-заказа, ручные выплаты и списания в админке, раздел «Бонусы» в личном кабинете тренера.

## Boundaries & Constraints

**Always:**
- Баланс — всегда `SUM(amount)` по журналу. Денормализованного поля баланса не существует.
- `amount` хранится со знаком: `accrual` > 0, `payout` и `writeoff` < 0 (CheckConstraint). Менеджер вводит положительное число — знак проставляет модель.
- Начисление идемпотентно: `UniqueConstraint(order, transaction_type='accrual')`. Импорт из 1С ретраится — двойного начисления быть не должно.
- Начисление только по `is_master=True`. База = сумма `OrderItem.total_price` по **субзаказам** мастера (у мастера своих позиций нет), fallback на собственные позиции, если `sub_orders` пуст.
- Субзаказы в статусах `cancelled` и `refunded` в базу **не входят**: мастер со смешанными статусами агрегируется в `delivered`, и без фильтра бонус считался бы за неотгруженный товар.
- Начисление только по заказам, созданным не раньше `program_start_at` (дата запуска программы в настройках). Пустое значение отключает отсечку. Без неё первый же импорт после деплоя начислил бы бонусы за все ранее закрытые заказы по сегодняшнему проценту.
- `percent_applied` и `base_amount` — снимки на момент начисления. Изменение % в админке не пересчитывает прошлое.
- Начисление выполняется синхронно в транзакции импорта — откат импорта откатывает бонус.
- Существующие ключи `STATUS_MAPPING` сохраняются (обратная совместимость).
- Комментарии и docstrings — на русском.

**Ask First:**
- Изменение семантики `STATUS_PRIORITY` или логики агрегации мастер-статуса (`_aggregate_master_status`).
- Любое изменение расчёта базы (вычитание `discount_amount`, включение `delivery_cost`).
- Backfill начислений по ранее закрытым заказам.

**Never:**
- Email-уведомления о начислении/выплате.
- Выгрузка бонусов и выплат в 1С.
- Автосписание бонусов как скидки при оформлении заказа.
- Индивидуальный % на тренера (только глобальный).
- Автоматическое сторно при отмене заказа (только ручное списание менеджером).
- Редактирование или удаление начислений в админке — исправления только через `writeoff`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Начисление | Верифицированный тренер, мастер-заказ переходит в `accrual_status`, товаров на 80 000 ₽, доставка 1 500 ₽, % = 5 | `accrual` +4 000 ₽, `base_amount`=80000, `percent_applied`=5 | N/A |
| Импорт «Закрыт» | Субзаказ получает `СтатусЗаказа` = «Закрыт» | `status` → `delivered`, `status_1c` = «Закрыт» сохранён | N/A |
| Частичное закрытие | Закрыт 1 субзаказ из 3 | Мастер остаётся не-`delivered`, начисления нет | N/A |
| Полное закрытие | Закрыты все субзаказы | Агрегация → мастер `delivered` → одно начисление | N/A |
| Повторный импорт | Заказ уже имеет `accrual` | Новых транзакций нет, баланс не меняется | `IntegrityError` подавляется, логируется debug |
| Неверифицированный тренер | `is_verified=False`, заказ закрыт | Начисления нет | N/A |
| Не тренер | `role='retail'`, заказ закрыт | Начисления нет | N/A |
| Программа выключена | `is_active=False`, заказ закрыт | Начисления нет | N/A |
| Выплата в пределах баланса | Баланс 6 500 ₽, выплата 5 000 ₽ | `payout` −5 000 ₽, баланс 1 500 ₽ | N/A |
| Выплата сверх баланса | Баланс 1 500 ₽, выплата 5 000 ₽ | Сохранение отклонено | `ValidationError` с текущим балансом в тексте |
| Списание в минус | Баланс 0 ₽, списание 4 000 ₽ | `writeoff` −4 000 ₽, баланс −4 000 ₽ (разрешено) | N/A |
| Ручная операция без комментария | `comment=''` | Сохранение отклонено | `ValidationError` на поле `comment` |
| ЛК не-тренера | `role='retail'`, `GET /users/bonuses/` | `403` | Пункт меню «Бонусы» не отображается |
| Неизвестный статус 1С | `СтатусЗаказа` = «Отменен клиентом» | Заказ пропущен, `skipped_unknown_status` +1 | warning в лог (существующее поведение) |
| Смешанный мастер | Субзаказы 100 000 ₽ `delivered` и 100 000 ₽ `cancelled`, % = 5 | База 100 000 ₽, `accrual` +5 000 ₽ (не 10 000 ₽) | N/A |
| Заказ до запуска программы | Мастер создан раньше `program_start_at`, импорт трогает `payment_status` | Начисления нет | N/A |
| Отсечка не задана | `program_start_at` пуст, заказ закрыт | Начисление проходит (отсечка отключена) | N/A |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/constants.py:22` -- `STATUS_MAPPING`; `STATUS_MAPPING_LOWER` (:32) выводится автоматически — трогать не нужно. `ORDER_STATUSES` (:35) — источник choices для `accrual_status`
- `backend/apps/orders/services/order_status_import.py` -- :693-701 отбрасывает unknown-статус; `_apply_master_aggregation` (:849) вызывает `master.save(update_fields=[...])` (:884) → post_save. Вызывается внутри `transaction.atomic()` (:195 → :256)
- `backend/apps/orders/models.py` -- `Order.is_master` (:240), `parent_order`/`related_name='sub_orders'` (:228), `OrderItem.total_price` (:469)
- `backend/apps/orders/signals.py` -- существующий `post_save` на `Order` работает только при `created=True` — конфликта нет; образец стиля receiver
- `backend/apps/users/models.py` -- `User.role` (:84, choices :69), `User.is_verified` (:141)
- `backend/freesport/settings/base.py:63` -- `LOCAL_APPS`; DRF: `PageNumberPagination`, `PAGE_SIZE=20`, `page_size` query-param (:167), `DjangoFilterBackend` (:163)
- `backend/freesport/urls.py:30-38` -- подключение `api/v1/`-маршрутов приложений
- `backend/apps/users/views/personal_cabinet.py` -- образец APIView ЛК с `permission_classes=[IsAuthenticated]` и `@extend_schema`; `CompanyView._check_b2b_access` — образец role-guard, возвращающего 403
- `backend/apps/users/urls.py` -- образец `app_name` + router; сюда же по смыслу ложатся `users/bonuses/`
- `backend/apps/banners/apps.py` -- образец `AppConfig.ready()` с импортом сигналов
- `backend/apps/orders/admin.py:32`, `backend/apps/integrations/admin.py:79` -- образцы `has_add_permission`-запретов
- `backend/tests/unit/test_order_status_import.py` -- существующие тесты маппинга статусов
- `frontend/src/components/layout/ProfileLayout.tsx:35` -- `navigationItems`, флаг `b2bOnly` (:40) и фильтрация (:122) — образец для `trainerOnly`
- `frontend/src/stores/authStore.ts:143` -- `authSelectors`, `useIsB2BUser` (:155); поля `user.role`, `user.is_verified` (snake_case)
- `frontend/src/app/(blue)/profile/orders/page.tsx` -- образец страницы ЛК: `'use client'`, `Suspense`, фильтр и пагинация через `useSearchParams`
- `frontend/src/services/ordersService.ts` -- образец сервиса поверх `api-client` + `PaginatedResponse` из `@/types/api`
- `docs/guides/bonus-program-trainers.md` -- бизнес-описание и терминология UI

## Tasks & Acceptance

**Execution:**

- [x] `backend/apps/orders/constants.py` -- добавить в `STATUS_MAPPING`: «Не согласован»→`pending`, «На согласовании»→`pending`, «К выполнению»→`processing`, «Закрыт»→`delivered`; существующие ключи не трогать -- без этого «Закрыт» отбрасывается и бонусы не начисляются никогда
- [x] `backend/apps/bonuses/` -- создать приложение (`__init__.py`, `apps.py` с `BonusesConfig.ready()` → импорт сигналов) -- изолированный домен, минимум связанности с `orders`
- [x] `backend/apps/bonuses/models.py` -- `BonusProgramSettings` (singleton pk=1: `is_active`, `percent`, `accrual_status` с choices из `ORDER_STATUSES`, default `delivered`) и `BonusTransaction` (поля из Design Notes, CheckConstraint на знак `amount`, условный `UniqueConstraint` на `order` при `transaction_type='accrual'`, `clean()` — обязательный комментарий для ручных операций и лимит выплаты) -- ledger как единственный источник истины
- [x] `backend/apps/bonuses/services/accrual.py` -- `calculate_base(order)`, `get_balance(user)`, `accrue_for_order(order)` со всеми проверками и подавлением `IntegrityError` во вложенном savepoint -- бизнес-логика вне сигналов и админки
- [x] `backend/apps/bonuses/signals.py` -- `post_save` на `Order` → `accrue_for_order` при `is_master=True` и `status == accrual_status` -- ловит и импорт из 1С, и ручную смену статуса в админке
- [x] `backend/apps/bonuses/admin.py` -- singleton-админка настроек (`has_add_permission=False` при существующей записи, `has_delete_permission=False`); `BonusTransactionAdmin`: `accrual` только на чтение, ручные операции с вводом положительной суммы, фильтры по типу и тренеру, колонка баланса -- защита истории от правок
- [x] `backend/apps/bonuses/serializers.py`, `views.py`, `urls.py` -- `GET /api/v1/users/bonuses/` (баланс, начислено, выплачено, действующий %) и `GET /api/v1/users/bonuses/transactions/` (`PageNumberPagination`, фильтр `type`); `permission_classes=[IsAuthenticated]` + guard роли `trainer` → 403, выдача только своих данных -- `DEFAULT_PERMISSION_CLASSES=AllowAny`, полагаться на default нельзя
- [x] `backend/freesport/settings/base.py`, `backend/freesport/urls.py` -- добавить `apps.bonuses` в `LOCAL_APPS` и `path("api/v1/", include("apps.bonuses.urls"))`
- [x] `backend/apps/bonuses/migrations/0001_initial.py` -- миграция моделей
- [x] `backend/apps/bonuses/tests/` -- unit-тесты (`@pytest.mark.unit`) на все строки I/O-матрицы: начисление, идемпотентность, частичное/полное закрытие субзаказов, роль и верификация, выключенная программа, лимит выплаты, минус при списании, обязательный комментарий, права API
- [x] `backend/tests/unit/test_order_status_import.py` -- тесты маппинга статусов УТ 11: сохранение `status_1c='Закрыт'`, переход субзаказа в `delivered`, агрегация мастера после закрытия всех субзаказов
- [x] `docs/api/openapi.yaml` -- описать оба endpoint, затем `npm run generate:types` -- рассинхрон ломает сборку фронта
- [x] `frontend/src/types/bonus.ts`, `frontend/src/services/bonusService.ts` -- типы и сервис поверх `api-client` (`PaginatedResponse` из `@/types/api`) -- голый `fetch`/`axios` запрещён
- [x] `frontend/src/app/(blue)/profile/bonuses/page.tsx` -- страница «Бонусы»: `'use client'`, сводка сверху, история с пагинацией и фильтром по типу через `useSearchParams` внутри `Suspense`, номер заказа ссылкой на `/profile/orders/[id]` -- терминология из `docs/guides/bonus-program-trainers.md`
- [x] `frontend/src/components/layout/ProfileLayout.tsx` -- пункт «Бонусы» с флагом `trainerOnly` по образцу `b2bOnly`; условие — `user.role === 'trainer' && user.is_verified` -- другим ролям раздел не виден

**Acceptance Criteria:**

- Given мастер-заказ верифицированного тренера с закрытыми субзаказами, when импорт из 1С агрегирует статус мастера в `accrual_status`, then создаётся ровно одна транзакция `accrual`, и повторный прогон того же XML не меняет баланс и не прерывает импорт остальных заказов.
- Given тренер с историей операций, when он открывает `/profile/bonuses`, then видит баланс, равный сумме всех операций, и полный список с суммами, датами, номерами заказов и комментариями менеджера.
- Given администратор изменил `percent` в админке, when создаётся новое начисление, then оно считается по новому проценту, а ранее созданные транзакции сохраняют прежние `percent_applied` и `base_amount`.
- Given покрытие тестами, when выполняется `make test-unit`, then все тесты проходят, а модуль `apps/bonuses` покрыт ≥ 90 % (критический модуль — деньги).

## Spec Change Log

- **Итерация 1 (2026-07-25), adversarial + edge-case ревью.**
  - **Находка 1:** `calculate_base` суммировал позиции всех субзаказов без фильтра по статусу, а `_aggregate_master_status` переводит мастер со смешанными статусами (`cancelled` + `delivered`) в `delivered` — бонус начислялся за отменённый товар (двойная переплата на примере 2×100 000 ₽).
  - **Находка 2:** отсутствовала отсечка по дате: сигнал висит на `post_save` любого мастера, а `_apply_master_aggregation` сохраняет мастера при изменении `payment_status`/`sent_to_1c_at`. Первый импорт после деплоя начислил бы бонусы за все ранее закрытые заказы по сегодняшнему проценту — прямое нарушение §9 `docs/guides/bonus-program-trainers.md`.
  - **Пересогласовано с человеком:** база исключает `cancelled`/`refunded` субзаказы; в настройки добавлено `program_start_at` (пустое значение = отсечка отключена).
  - **Известное плохое состояние, которого избегаем:** переплата тренеру по смешанным заказам и массовое начисление задним числом при первом же импорте.
  - **KEEP (должно пережить перегенерацию):** нормализация знака `amount` в `clean()`, а не в `save()` — `full_clean()` проверяет `CheckConstraint` до сохранения, иначе ручные операции с положительной суммой отклоняются; savepoint вокруг всех обращений к БД в `accrue_for_order` — сигнал работает внутри `transaction.atomic()` импорта; собственный класс пагинации, поскольку глобальный `PAGE_SIZE_QUERY_PARAM` в DRF неактивен.

- **Итерация 2 (2026-07-25), закрытие отложенных находок ревью.**
  - **Долговечность журнала:** `BonusTransaction.user` переведён с `CASCADE` на `SET_NULL` (`null=True`, `blank=False`), добавлены снимки `user_email_snapshot`, `user_name_snapshot`, `order_number_snapshot`. `CASCADE` стирал исполненные выплаты вместе с учётной записью, нарушая гарантию «история не удаляется»; `PROTECT` конфликтовал бы с удалением по запросу ПДн. **Решение человека (Alex, 2026-07-25):** вариант «SET_NULL + снимки».
  - **Ключ идемпотентности** перенесён с FK `order` на `order_number_snapshot`: в PostgreSQL NULL-ы различны, поэтому после удаления заказа `UniqueConstraint(order)` перестал бы защищать от повторного начисления.
  - **Лимит выплаты** проверяется под `SELECT ... FOR UPDATE` по строке тренера (`lock_trainer_account`); добавлен сервис `create_manual_transaction`, а `save()` принудительно валидирует новые ручные операции — прямой `objects.create()` больше не обходит ни лимит, ни требование комментария.
  - **`accrual_status`** сужен до нетерминальных статусов (`ACCRUAL_STATUS_CHOICES` + `CheckConstraint`). **Осознанное отклонение от буквы спеки** «choices из `ORDER_STATUSES`»: полный список позволял настроить начисление за отменённые заказы, что прямо противоречит разделу Boundaries.
  - **Доступ к API** выровнен с начислением и пунктом меню: `IsTrainer` требует `is_verified`, неподтверждённый тренер получает 403 вместо 200 с нулями.
  - **Обратный переход статуса УТ 11:** семантика `STATUS_PRIORITY` не изменена (граница «Ask First» соблюдена), но фактический `status_1c` фиксируется при заблокированном переходе. **Решение человека (Alex, 2026-07-25):** вариант «сохранять `status_1c`».
  - **KEEP (должно пережить перегенерацию):** снимки заполняются один раз при создании и никогда не переписываются — журнал обязан хранить состояние на момент операции; `lock_trainer_account` молча пропускает блокировку вне транзакции, поскольку `full_clean()` вызывают и из кода без транзакции; блокировка в админке работает только потому, что POST `ModelAdmin.changeform_view` идёт внутри `transaction.atomic()`.

## Design Notes

**`BonusTransaction`:** `user` (FK, `related_name='bonus_transactions'`), `transaction_type` (`accrual`/`payout`/`writeoff`), `amount` (Decimal 10,2, со знаком), `order` (FK `orders.Order`, null), `percent_applied` (Decimal 5,2, null), `base_amount` (Decimal 10,2, null), `comment` (Text), `created_by` (FK User, null, `on_delete=SET_NULL`), `created_at`. Индекс по `(user, created_at)`.

**База начисления** — позиции живут в субзаказах, у мастера их нет (проверено на проде: мастер id=39 → 0 позиций, три субзаказа → 2560 ₽):

```python
sub_ids = list(order.sub_orders.values_list("id", flat=True))
target_ids = sub_ids or [order.id]
base = OrderItem.objects.filter(order_id__in=target_ids).aggregate(
    total=Sum("total_price")
)["total"] or Decimal("0")
amount = (base * percent / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

**Savepoint при подавлении `IntegrityError` — критично.** Сигнал срабатывает внутри `transaction.atomic()` импорта (`order_status_import.py:195`). Голый `try/except IntegrityError` пометит всю транзакцию как broken и уронит весь батч. Создание обязано идти во вложенном atomic:

```python
try:
    with transaction.atomic():  # savepoint
        BonusTransaction.objects.create(...)
except IntegrityError:
    logger.debug("Бонус по заказу %s уже начислен", order.pk)
```

**Асимметрия лимитов:** `payout` ограничен балансом (защита от опечатки), `writeoff` — нет. Если бонус уже выплачен, а заказ потом отменён, отрицательный баланс корректно отражает долг тренера и закроется будущими начислениями.

**Известный риск:** в УТ 11 «Закрыт» ставится и на выполненный, и на закрытый с отменой заказ — различить автоматически нельзя. Ошибочные начисления снимает менеджер через `writeoff`. Поэтому `accrual_status` вынесен в админку — переключается без деплоя.

## Verification

**Commands:**
- `make test-unit` -- expected: все тесты проходят, новые тесты `apps/bonuses` и маппинга статусов зелёные
- `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run` -- expected: нет несозданных миграций
- `cd frontend && npm run test` -- expected: тесты проходят
- `cd frontend && npm run build` -- expected: сборка без ошибок TypeScript (проверяет синхронность `api.generated.ts`)

**Manual checks:**
- Админка `/admin/`: настройки программы редактируются, вторую запись создать нельзя; начисление открывается только на чтение; выплата сверх баланса отклоняется с сообщением; списание в минус проходит.
- ЛК под тренером: пункт «Бонусы» виден, баланс совпадает с суммой операций; под ролью `retail` пункт отсутствует, прямой переход на `/profile/bonuses` данных не отдаёт.

## Suggested Review Order

**Триггер начисления и деньги**

- Точка входа: единственное место, где создаётся денежная операция; savepoint охватывает все обращения к БД
  [`accrual.py:98`](../../backend/apps/bonuses/services/accrual.py#L98)

- База начисления: отменённые субзаказы исключены, иначе смешанный мастер оплачивался бы дважды
  [`accrual.py:35`](../../backend/apps/bonuses/services/accrual.py#L35)

- Условия начисления, включая отсечку по дате запуска программы
  [`accrual.py:76`](../../backend/apps/bonuses/services/accrual.py#L76)

- Сигнал на `post_save` ловит и импорт 1С, и ручную смену статуса; фикстуры отсечены
  [`signals.py:28`](../../backend/apps/bonuses/signals.py#L28)

**Инварианты журнала**

- Знак нормализуется в `clean()`, а не в `save()`: `full_clean()` проверяет CheckConstraint раньше сохранения
  [`models.py:256`](../../backend/apps/bonuses/models.py#L256)

- Отсечка `program_start_at`; пустое значение осознанно отключает её
  [`models.py:75`](../../backend/apps/bonuses/models.py#L75)

**Причина, по которой бонусы вообще не начислялись**

- Реальные статусы УТ 11: без «Закрыт» заказ никогда не доходил до `delivered`
  [`constants.py:42`](../../backend/apps/orders/constants.py#L42)

**Доступ и API**

- Роль проверяется permission-классом, а не внутри `get()` — иначе новый метод остался бы без защиты
  [`views.py:37`](../../backend/apps/bonuses/views.py#L37)

- Валидация `?type=`: опечатка даёт 400, а не пустую историю, похожую на пропажу бонусов
  [`views.py:95`](../../backend/apps/bonuses/views.py#L95)

- Свой класс пагинации: глобальный `PAGE_SIZE_QUERY_PARAM` в DRF неактивен
  [`views.py:26`](../../backend/apps/bonuses/views.py#L26)

**Админка**

- Сумма показывается по модулю при правке, иначе запись отклоняет собственный знак
  [`admin.py:96`](../../backend/apps/bonuses/admin.py#L96)

- Баланс считается подзапросом: кэш на `ModelAdmin` протекал бы между запросами
  [`admin.py:131`](../../backend/apps/bonuses/admin.py#L131)

**Фронтенд**

- 403 отдаёт понятный экран вместо сетевой ошибки; гонка ответов отсекается номером запроса
  [`page.tsx:134`](../../frontend/src/app/(blue)/profile/bonuses/page.tsx#L134)

- Пункт меню виден только подтверждённым тренерам
  [`ProfileLayout.tsx:128`](../../frontend/src/components/layout/ProfileLayout.tsx#L128)

**Тесты и контракт**

- Продакшен-путь целиком: `process()` → агрегация → сигнал → начисление
  [`test_import_integration.py:47`](../../backend/apps/bonuses/tests/test_import_integration.py#L47)

- Savepoint проверяется настоящим дублирующим INSERT внутри внешней транзакции
  [`test_accrual.py:236`](../../backend/apps/bonuses/tests/test_accrual.py#L236)

- Контракт двух endpoint'ов, синхронизирован с `api.generated.ts`
  [`openapi.yaml:675`](../../docs/api/openapi.yaml#L675)
