---
title: 'Этапы заказа из 1С: таблица 1:1 в форме БУС, лог [BUS ORDERS], уточнения runbook'
type: 'bugfix'
created: '2026-11-23'
status: 'done'
baseline_commit: 'c521878847a2d8bd2b4351a10555fc5f38043741'
route: 'dispatch'
review_loop_iteration: 0
context: ['{project-root}/.windsurf/rules/gitnexus.md', '{project-root}/_bmad-output/implementation-artifacts/spec-1c-order-statuses-import.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Находки (1)–(3) сквозной проверки 23.11.2026 из спеки `spec-1c-order-statuses-import.md` (Implementation Notes):
- таблицу «много состояний → один Ид» в форме БУС не собрать;
- строки `[BUS ORDERS]` нет в логах;
- в runbook'е не хватает ограничений УТ и БУС.

**Approach:** Каждому состоянию УТ — свой одноимённый Ид в `STATUS_MAPPING`. Логгер `apps.integrations` перевести на INFO. Дописать runbook.

## Boundaries & Constraints

**Decisions (владелец, 23.11.2026):** у каждого состояния УТ свой Ид статуса. Always исходной спеки приводится к таблице 1:1, запись — в её Spec Change Log.

**Always:**
- Новые ключи: «Ожидается согласование» → `pending`; «Ожидается оплата до обеспечения», «Готов к обеспечению», «Ожидается оплата до отгрузки», «Ожидается обеспечение» → `processing`; «Готов к отгрузке», «В процессе отгрузки» → `at_warehouse`; «Ожидается оплата», «Готов к закрытию» → `shipped`. «Закрыт» → `delivered` уже есть.
- Порядок ключей обязателен: сначала 10 состояний УТ по жизненному циклу, потом старые ключи. Выгрузка БУС берёт первую строку таблицы с нужным состоянием (`БУС_ВыгрузкаСервер:8179`, `Найти` без колонки), строки идут в порядке `mode=info`.
- Старые ключи остаются: на них держатся настроенные базы и реальный файл `orders_1_89b0ff0d-….xml`.
- Правило отмены и запрет финального статуса при ложной отмене не меняются.
- INFO-строки `apps.integrations` выводятся один раз (без дубля через root), со временем и уровнем — и в backend, и в Celery.
- Старый путь `filename=orders.xml`: ответы не меняются; новые названия там тоже распознаются, потому что маппинг общий.

**Never:** не трогать `.env*`, 1С на проде, `OrderExportService`. Синтетический XML вместо реальной выгрузки не делать. Таблицу узла «Загрузка заказов локально» через COM не править: её пересоберёт владелец через форму. Never исходной спеки в силе.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Handling |
|---|---|---|---|
| Новый Ид | `processing`, «В процессе отгрузки» | `at_warehouse` | — |
| Старый Ид | «Передан на склад» | как раньше | — |
| Отмена на новом Ид | `Отменен`=true, строк нет, «Готов к закрытию» | `cancelled` | — |
| Ложная отмена на новом Ид | `Отменен`=true, строки есть, «Готов к закрытию» | `shipped` | warning |
| Старый путь | `bus_format=False`, «Готов к отгрузке» | `at_warehouse` | — |

</frozen-after-approval>

## Code Map

- `backend/apps/orders/constants.py:30` `STATUS_MAPPING` — `handle_info` (`views.py:423`) отдаёт `keys()` по порядку. Читает маппинг `_process_order_update` (`order_status_import.py:847–853`), код метода не меняется. GitNexus: risk HIGH.
- Логи: свой `LOGGING` в `development.py:89`, `staging.py:70`, `production.py:76`, каждый целиком заменяет `base.py:633`. Docker выбирает модуль через `DJANGO_SETTINGS_MODULE`. Правка `base.py` ни на что не влияет — она для единообразия, по заданию. В dev и staging у `console` нет форматтера, поэтому нужен отдельный хендлер с временем, уровнем и именем логгера. В prod у `console` уже есть `verbose`. Celery запущен с `-l info` и сам перехватывает root: `propagate=False` убирает дубль. Тесты идут на `test.py`, где `LOGGING={}`, — caplog не страдает.
- Тест настроек — `ast`, как в `tests/unit/test_security_settings.py`: `production.py` без `DB_NAME` не импортируется. `literal_eval` применять к узлу `loggers["apps.integrations"]`, потому что `LOGGING` в `base.py` не литерал.
- Форма БУС: таблица `СоответствияССостояниямиЗаказа` (`Form.xml:270–281`). Add, Copy, Delete и перестановка строк исключены. После «Загрузить с сайта» — по строке на Ид, состояние переносится из прежней строки с тем же Ид, взятой первой (`Form/Module.bsl:232–245`). Пустые строки форма сохраняет (`:106–116`), выгрузке они не мешают.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/constants.py` — 9 ключей и порядок. Переписать комментарии `:20–29`, `:34–35`, `:44–45`: они описывают «блоки» и «один Ид на несколько состояний». Новый комментарий объясняет, почему порядок важен.
- [x] `backend/freesport/settings/{base,development,staging,production}.py` — логгер `apps.integrations`: INFO, `propagate False`, хендлер, у форматтера которого в формате есть `asctime` и `levelname`.
- [x] `backend/tests/unit/test_order_status_import.py` — 10 состояний УТ, старые ключи, первые 10 ключей по порядку, строки матрицы.
- [x] `backend/tests/integration/test_onec_exchange_info_mode.py` — первые 10 `<Ид>` — состояния УТ по порядку, дублей нет.
- [x] `backend/tests/unit/test_logging_settings.py` — в 4 модулях проверить: INFO; `propagate False`; хендлер логгера объявлен; формат его форматтера содержит `asctime` и `levelname`. Для `base.py` хендлеры читать из присваивания `_base_handlers` (`:599`).
- [x] `docs/integrations/1c/order-statuses-from-1c-setup.md`:
  - шаг 2 — таблица 1:1, признак релиза — Ид «В процессе отгрузки». Очистить состояние у строк со старыми Ид: ОжидаетОбработки, Подтвержден, Отгружен, Доставлен, Отменен, Возвращен, Не согласован, На согласовании, К выполнению, Передан на склад. «Закрыт» не трогать: это и старый, и новый Ид;
  - ограничения: заказ с сайта до правки в 1С не выгружается (`ЗагрузкаСБУС`, `БУС_РегистрацияИзмененийВызовСервера:108`), сайт показывает «Новый»; «Закрыт» — только при полной оплате или отменённых строках; резерв — только со складом в строках; ордерный склад сразу даёт «В процессе отгрузки»; при отмене всех строк УТ даёт «Готов к закрытию», сайт ставит «Отменён» по `Отменен`;
  - «Проверка», шаг 2: `[BUS ORDERS]` есть начиная с этого релиза;
  - инструкция владельцу по форме на `test_base`.
- [x] `_bmad-output/implementation-artifacts/spec-1c-order-statuses-import.md` — Always 1:1, Spec Change Log, итог в Implementation Notes.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` — две записи:
  - логгер `apps.orders.services.order_status_import` не настроен, на проде WARNING идёт через `lastResort` без времени;
  - `sessid` обмена — это ключ Django-сессии (`views.py:205–211`). Он целиком уходит в query 1С и в access-лог nginx, а с INFO — ещё и в лог backend (`views.py:330, 486, 499`, `import_orchestrator.py:112, 463, 515`). Маскировать в backend бесполезно, нужен отдельный `sessid`.

**Acceptance Criteria:**
- Given обновлённый сайт, when GET `type=sale&mode=info`, then первые 10 `<Ид>` — состояния УТ по порядку, дублей нет.
- Given локальный dev-стек, when пришёл один `mode=info`, then `docker logs --since 1m freesport-backend | grep -c "\[INFO MODE\]"` = 1, и строка со временем и уровнем.
- Given реальный файл со старыми Ид, when идёт импорт, then `test_bus_orders_real_export` зелёный и не скипается.

## Implementation Notes

- 23.11.2026, dev: `STATUS_MAPPING` — 10 состояний УТ первыми, затем прежние ключи («Закрыт» — один раз, среди первых десяти); логгер `apps.integrations` — INFO, `propagate=False`; в `development.py`/`staging.py` добавлены форматтер `timestamped` и хендлер `integrations_console`, в `base.py`/`production.py` — существующий `console` (форматтеры `simple`/`verbose`). Runbook, исходная спека и `deferred-work.md` обновлены.
- Проверка: команда Verification — 372 passed, пропусков нет (`test_bus_orders_real_export` прошёл на реальном файле); black/isort/flake8/mypy по изменённым файлам чисто. Живой dev-стек после `restart backend celery`: `mode=info` отдаёт 20 Ид, первые 10 — состояния УТ по порядку; `[INFO MODE]` в логе backend — 1 строка `[2026-11-24 00:21:38] INFO apps.integrations.onec_exchange.views …`; пустой `run_selective_import_task` — 2 строки `[Task` со временем и уровнем в логе Celery. `detect-changes` — только `STATUS_MAPPING`, `LOGGING` и тесты (прочие переменные в списке — сдвиг строк), процессов 0; `check --cycles` — два цикла базовой линии.
- Не сделано (ручные проверки владельца): «Загрузить с сайта» на `test_base`, пересборка таблицы узла «Загрузка заказов локально» в форме и контрольный заказ.

## Spec Change Log

## Review Triage Log

| # | Находка (слой) | Вердикт | Маршрут и обоснование |
|---|---|---|---|
| 1 | `test_logging_settings.py` читает настройки через AST: не видит `level` хендлера (WARNING на `console` молча глушит INFO) и не проверяет, что конфиг грузится в `dictConfig` (verification-gap; blind-hunter) | medium | patch — у хендлеров уровня в dev/staging/prod нет, в `base` `INFO`; регресс уровня или опечатка в `class` пройдут зелёными. Тест через `dictConfig` на извлечённых узлах. Часть «дочерние логгеры переопределяют уровень» — false: дочерних логгеров `apps.integrations.*` в `LOGGING` нет. |
| 2 | Запись про `sessid` в `deferred-work.md` неполна: пропущены `views.py:481–484`, `import_orchestrator.py:417`, `file_service.py:293, 299`; хелпер — `_get_exchange_identity`, и он предпочитает `sessid` из query (edge-case-hunter; blind-hunter) | low | patch — сверено по коду; исправление прямое, в тексте записи. |
| 3 | Runbook, шаг 2: после «Загрузить с сайта» на старой таблице каждый прежний Ид держит только первое состояние; «Применить» до заполнения 10 строк оставит 5 состояний без строки → `no_status` (edge-case-hunter) | medium | patch — `Form/Module.bsl:232–245` переносит состояние из первой строки с тем же Ид; предупреждение в шаг 2. |
| 4 | Раздел «Откат» не учитывает таблицу 1:1: откат сайта ниже релиза делает новые Ид неизвестными → `no_status`, этапы замирают (blind-hunter) | medium | patch — пункт в «Откат»: перед откатом сайта вернуть в форме прежние Ид. Уточнено при правке: прежний сайт даёт не `no_status`, а `skipped_unknown_status` (`order_status_import.py:858`); исход тот же — этапы замирают. |
| 5 | Структура runbook: «Ограничения» разорвали шаги 2 и 3, абзац «Статусы двигаются только вперёд» оторван от шага 2, ссылка «пункты 3–4 шага 2» неоднозначна; «этот релиз» без привязки (blind-hunter) | low | patch — перенести абзац в шаг 2, «Ограничения» — после «Отмена заказа», уточнить ссылку, «этот релиз» привязать к признаку релиза. Инструкция по `test_base` остаётся в runbook — её требует задача спеки. |
| 6 | Полный ключ сессии теперь пишется в лог backend (blind-hunter) | low | reject — INFO для `apps.integrations` задан самим Intent; тот же ключ на том же хосте уже в access-логе nginx, новой аудитории нет; корень отложен записью №2 этой спеки. |
| 7 | Логгер `apps.orders` не настроен, WARNING ложной отмены идёт через `lastResort` (blind-hunter) | medium | defer — дефект существовал до изменения; уже записан задачей этой спеки в `deferred-work.md`, дубль не добавлен. |
| 8 | INFO на весь пакет `apps.integrations` даёт построчный шум (чанки, файлы) (blind-hunter) | low | reject — уровень пакета задан Intent; строки по ~150 Б, на цикл обмена — десятки, ротация 30 МБ не под угрозой. |
| 9 | В `base.py` форматтер `simple` без даты (blind-hunter) | low | reject — `LOGGING` из `base.py` ни один запускаемый модуль не использует (Code Map). |
| 10 | Время в логах без часового пояса (blind-hunter) | false | Django при загрузке настроек ставит `os.environ["TZ"] = TIME_ZONE` (`Europe/Moscow`) и `tzset()`; backend и Celery пишут московское время — как у админа 1С. |
| 11 | Прод-форматтер `verbose` без имени логгера (blind-hunter) | low | reject — теги `[INFO MODE]`, `[BUS ORDERS]`, `[Task` уникальны, grep их находит; Always требует только время и уровень. |
| 12 | Новые Ид не проверены на реальной выгрузке (blind-hunter) | low | reject — покрыто ручной проверкой владельца (Manual checks: «Статуса заказа ИД» равен новому Ид в копии файла). |
| 13 | Тест `mode=info` не проверяет прежние Ид и регистронезависимые дубли; `import re` внутри метода (blind-hunter) | low | reject — прежние ключи проверяет `test_legacy_key_is_preserved`, `handle_info` отдаёт `STATUS_MAPPING.keys()`; регистровых дублей в ключах нет; импорт — косметика. |
| 14 | Индекс GitNexus `stale`, слой graph-impact не выполнен (graph-impact) | false | `Current commit` = `Indexed commit` = `c521878`; `stale` из-за незакоммиченного diff под ревью. Функций в diff нет; `impact` читателей `STATUS_MAPPING` выполнен при реализации (`_process_order_update` HIGH, `handle_info` LOW; код не меняется, поиск — `.get`), `check --cycles` — базовая линия. |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:sugar tests/unit/test_order_status_import.py tests/unit/test_logging_settings.py tests/integration/test_orders_bus_import.py tests/integration/test_orders_xml_mode_file.py tests/integration/test_onec_exchange_info_mode.py tests/integration/test_order_status_import_db.py apps/orders apps/bonuses` — зелёные, `test_bus_orders_real_export` не скипается.
- `mode=info` по живому HTTP:
  - пароль пользователя обмена не нужен: в `freesport-backend` через `manage.py shell` сделать `Client().force_login(<пользователь с правом обмена 1С>)` и взять cookie `sessionid`;
  - `curl -b "sessionid=…" "http://localhost:8001/api/integration/1c/exchange/?type=sale&mode=info"` → 10 названий первыми;
  - `docker logs --since 1m freesport-backend | grep -c "\[INFO MODE\]"` = 1.
- Celery:
  - `docker exec freesport-celery-worker celery -A freesport call apps.integrations.tasks.run_selective_import_task --args='[[]]'` — пустой импорт пишет две строки `[Task` (`tasks.py:49, 94`);
  - `docker logs --since 1m freesport-celery-worker | grep -c "\[Task"` = 2, строки со временем.
- Схема API и фронтенд не меняются. `npx gitnexus detect-changes --scope all`, `check --cycles` → циклы как в базовой линии.

**Manual checks (владелец):**
- на `test_base` нажать «Загрузить с сайта» — 10 состояний первыми;
- пересобрать таблицу и изменить один заказ;
- в копии файла (`EXCHANGE_LOG_DIR`) «Статуса заказа ИД» равен новому Ид, в логе есть `[BUS ORDERS] … updated=1`.
