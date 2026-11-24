---
title: 'Этапы заказа из 1С (БУС) на сайт: «Передан на склад», «Отправлен», «Доставлен», отмена'
type: 'feature'
created: '2026-11-23'
status: 'done'
route: 'dispatch'
baseline_commit: '6ab2928ce1865830cb266813892a98043ea5e344'
review_loop_iteration: 0
context: ['{project-root}/.windsurf/rules/gitnexus.md', '{project-root}/_bmad-output/implementation-artifacts/research-1c-order-statuses.md', '{project-root}/backend/docs/testing-standards.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 1С не отдаёт сайту этапы заказа. Если включить выгрузку заказов в БУС, сайт её не примет: формат, имя файла и маршрут не совпадают (research, раздел 4).

**Approach:** Принимать выгрузку заказов БУС в существующий `OrderStatusImportService`. Добавить статус «Передан на склад» (`at_warehouse`). Написать runbook настройки БУС.

## Boundaries & Constraints

**Decisions (владелец, 23.11.2026):** источник этапа в БУС — «Состояния заказа». «На складе» — новый статус сайта. Оплату из 1С не принимать. Реальную выгрузку снимает агент через COM с `test_base` (менять `test_base` разрешено): проводит 3–4 заказа с сайта до «Готов к отгрузке» и «Закрыт», один отменяет, создаёт настройку «Обмен локальный» (выгрузка заказов в папку, источник «Состояния заказа», соответствия из Always) и выгружает `orders_*.xml`. Если COM не справится, файл снимает владелец по черновику runbook'а.

**Always:**
- Соответствия runbook'а — таблица 1:1, Ид статуса = название состояния (Состояние → статус сайта; изменено 23.11.2026, см. Spec Change Log):
  - «Ожидается согласование» → `pending`;
  - «Ожидается оплата до обеспечения», «Готов к обеспечению», «Ожидается оплата до отгрузки», «Ожидается обеспечение» → `processing`;
  - «Готов к отгрузке», «В процессе отгрузки» → `at_warehouse`;
  - «Ожидается оплата», «Готов к закрытию» → `shipped`;
  - «Закрыт» → `delivered`.
  - Прежние Ид («На согласовании», «К выполнению», «Передан на склад», «Отгружен», «Закрыт» и исторические) остаются в `STATUS_MAPPING`.
- В БУС поля «Когда оплачен / отгружен / оплачен и отгружен» пустые. Галка «Выгружать отменённые товары» выключена.
- Отмена применяется, только если `Отменен`=`true` и в документе либо нет строк `<Товар>`, кроме `Ид`=`ORDER_DELIVERY`, либо `<ПометкаУдаления>`=`true`. Тогда сайт ставит `cancelled` и пишет `status_1c`=«Отменен». `Отменен`=`true` при живых строках означает, что галка включена: отмену игнорировать, писать warning, статус брать как обычно, но **в финальный статус не переводить**. Если по соответствию выходит `delivered`, писать `status_1c`, а `status` не менять: в УТ «Закрыт» ставится и на отменённый заказ, и `delivered` начислил бы бонус за отмену.
- Логику регрессий (`STATUS_PRIORITY`) и агрегацию мастера не менять; числа приоритетов сдвигаются: `at_warehouse`=4, `shipped`=5, `delivered`=6.
- На маршруте БУС ответ `failure` — только когда нет XML, XML битый или устаревший, а также при внутреннем сбое (БД недоступна после повторов, неожиданное исключение; решение владельца 23.11.2026). Всё остальное — `success`: на `failure` БУС оставляет пакет в `БУС_ПакетыВыгрузки` и пересылает его при каждом запуске.

**Never:** не принимать оплаты, `paid_at` и документы оплат и отгрузок. Не запускать импорт каталога для `orders*`. Не делать синтетический XML БУС. Не менять ответы старого пути `filename=orders.xml` и `OrderExportService`. Не трогать `.env*` и 1С на проде.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Handling |
|---|---|---|---|
| Этап | субзаказ `processing`, «Передан на склад» | `at_warehouse`, мастер пересчитан | — |
| Отмена | `Отменен`=true, строк нет | `cancelled` | — |
| Ложная отмена | `Отменен`=true, строки есть, пометки нет | статус по «Статуса заказа ИД»; если он финальный — `status` без изменений, `status_1c` записан | warning |
| Нет соответствия | реквизита статуса нет | без изменений | счётчик пропусков, `success` |
| Не заказ | `ХозОперация` ≠ «Заказ товара» | пропуск | — |
| Чужой заказ | `Номер`/`Ид` не найдены | `not_found` | `success` |
| Несколько XML | в temp-каталоге сессии несколько `orders*.xml` (в zip или открыто) | обработаны все | — |
| Идёт импорт каталога | каталожная `ImportSession` IN_PROGRESS | заказы обработаны | — |
| Нет XML или битый | — | без изменений | `failure` + лог |

</frozen-after-approval>

## Code Map

- `backend/apps/integrations/onec_exchange/views.py`:
  - `handle_import` — до `ImportOrchestratorService`: `type=sale` и имя `orders*.xml` (без учёта регистра), кроме ровно `orders.xml` → новый `_handle_bus_orders_import(sessid)`. `orders.xml` идёт как раньше (старый путь не трогаем).
  - `_handle_orders_xml` — вынести цикл повторов `service.process` (`ORDERS_IMPORT_MAX_RETRIES`) в общий хелпер; ответы и лимиты старого пути (5 МБ, 1000 документов) не менять. На маршруте БУС эти лимиты не действуют: размер уже ограничен `FILE_LIMIT_BYTES` при `mode=file`.
  - Переиспользовать `_reencode_xml_if_needed`, `_validate_xml_timestamp` (устаревший → `failure`), `_save_exchange_log` (копия каждого файла до разбора).
- Источники `orders*.xml` сессии: `FileStreamService(sessid).session_dir` — открытые файлы и члены `*.zip` (читать `ZipFile.read` по имени, без `extractall`); плюс `session_import_dir(sessid) / "orders"` — туда их раскладывает `ImportOrchestratorService._route_unpacked_files`, если раньше в той же сессии прошёл `mode=import` другого файла. Удалять: прочитанные `orders*.xml`; архив — только если все его члены `orders*.xml`. Остальное не трогать.
- `backend/apps/orders/services/order_status_import.py`:
  - конструктор `OrderStatusImportService(bus_format: bool = False)`; БУС-маршрут передаёт `True`, старый путь — без изменений;
  - в обоих режимах: снятие namespace с тегов после `ET.fromstring` (как `users/services/parser.py::_strip_namespace`); документ с `<ХозОперация>` ≠ «Заказ товара» → новый счётчик `skipped_non_order`, не ошибка; статус из «Статуса заказа ИД», иначе из «СтатусЗаказа»;
  - только `bus_format`: нет статуса → счётчик `skipped_no_status` без записи в `errors`; `ДатаОплаты`/`ДатаОтгрузки` не читать; правило отмены — `status_1c`=«Отменен» и обычный путь через `STATUS_MAPPING`; ложная отмена с финальным результатом → `_record_blocked_status_1c` + `SKIPPED_STATUS_REGRESSION`;
  - новые счётчики — в `ImportResult.skipped`.
- `backend/apps/orders/constants.py` — `STATUS_MAPPING` + «Передан на склад»; `ORDER_STATUSES` + `("at_warehouse", "Передан на склад")` между `processing` и `shipped`; `_ACTIVE_STATUS_CODES`, `STATUS_PRIORITY`; `ALLOWED_REQUISITES` + «Статуса заказа ИД», «Отменен». `handle_info` берёт ключи `STATUS_MAPPING` сам.
- `orders/models.py:150` (`ORDER_STATUSES`), `bonuses/models.py:32` (`ACCRUAL_STATUS_CHOICES`) — `AlterField`-миграции `orders/0019`, `bonuses/0004`.
- `bonuses/services/accrual.py:145` — начисление при точном совпадении статуса; не менять, сказать в runbook (заказ может перескочить `shipped`).
- Frontend: `types/order.ts`, `OrderStatusBadge.tsx` (+ тест), `OrdersList.tsx` (вкладка «На складе»), `app/(blue)/profile/orders/page.tsx:28`, `checkout/OrderSuccessView.tsx:34`, `utils/orderPdfExport.ts:56` (последние два — `Record<string,string>`, `tsc` не поймает). `docs/api/openapi.yaml` → `npm run generate:types` (рецепт `check_openapi_sync` — память `reference_backend_checks_in_container`).
- Тестовые данные: `backend/data/import_1c/orders/` (bind в тестовый контейнер). Пуш в приватный `FREESPORT-1c-test-data` — по команде владельца.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/orders/constants.py` — статус, ключ, приоритеты, реквизиты.
- [x] `backend/apps/orders/services/order_status_import.py` — режим `bus_format`, namespace, `ХозОперация`, источник статуса, отмена, счётчики. Тест `tests/unit/test_order_status_import.py:1357` остаётся как есть (старый режим).
- [x] `backend/apps/integrations/onec_exchange/views.py` — маршрут БУС и общий хелпер повторов.
- [x] `backend/apps/orders/migrations/0019_*`, `backend/apps/bonuses/migrations/0004_*` — choices.
- [x] Frontend — 6 файлов из Code Map, перегенерация `openapi.yaml` и `api.generated.ts`.
- [x] 1С `test_base` через COM (память `reference_1c_com_query`) — заказы, настройка «Обмен локальный», выгрузка; файл в `backend/data/import_1c/orders/`.
- [x] `docs/integrations/1c/order-statuses-from-1c-setup.md` — runbook: выгрузка заказов «только изменения» в настройке «По расписанию» из `orders-pull-schedule-setup.md`; источник статусов, «Загрузить с сайта», таблица соответствий; поля «Когда …» пустые, галка отменённых товаров выключена; `<Номер>` из «Номер с сайта»; проверка по nginx `type=sale&mode=import&filename=orders`; бонусы.
- [x] Тесты: `tests/unit/test_order_status_import.py` — матрица I/O в режиме `bus_format`; `tests/integration/test_orders_bus_import.py` — HTTP-цепочка `checkauth → init → file → import` (zip и открытый XML, смешанный архив, файл в `orders/` каталога импорта, время заморожено, нет каталожной `ImportSession`); `test_onec_exchange_info_mode.py` — новый статус; тест на реальном файле с `data_dependent`.

**Acceptance Criteria:**
- Given реальная выгрузка БУС, when 1С проходит `checkauth → init → file → import`, then статусы субзаказов и мастеров обновлены, а новой каталожной `ImportSession` нет.
- Given `mode=info`, when 1С нажимает «Загрузить с сайта», then в списке есть «Передан на склад».
- Given заказ `at_warehouse`, when клиент открывает кабинет, success-страницу или PDF, then везде видна подпись «Передан на склад».
- Given старый клиент шлёт `mode=file&filename=orders.xml`, when импорт проходит, then ответы прежние (`test_orders_xml_mode_file.py` зелёный без правок).

## Implementation Notes

- 23.11.2026, dev: код, миграции `orders/0019_at_warehouse_status`, `bonuses/0004_at_warehouse_status`, фронтенд, `openapi.yaml`/`api.generated.ts`, runbook и тесты готовы. Тест `apps/bonuses/tests/test_journal_integrity.py::test_active_statuses_remain_available` обновлён: `at_warehouse` закономерно попал в `ACCRUAL_STATUS_CHOICES`.
- **Не сделано: выгрузка с `test_base`.** COM-соединение отвечает «Сеанс работы завершен администратором» и на `127.0.0.1`, и на имени хоста; блокировки сеансов нет (`rac infobase info`: `sessions-deny: off`), журнал регистрации с 18.11 пуст. По Boundaries файл снимает владелец по разделу «Тестовые данные» runbook'а и кладёт в `backend/data/import_1c/orders/`. До этого `test_bus_orders_real_export` скипается, а маршрут проверен на XML, собранном в тесте по раскладке `СформироватьЗаказ`.
- В выгрузке БУС `<Номер>` = `НомерПоДаннымКлиента` без вариантов настройки (`Module.bsl:6927`); заполняет его при загрузке строка «Номер по данным клиента» → «Номер с сайта» (`БУС_НастройкиОбмена.ManagerModule.bsl:217`) — так и записано в runbook.

- 23.11.2026, сквозная проверка на `test_base` ↔ локальный сайт (живой обмен узла «Загрузка заказов локально», «По расписанию», 300 с). В узле включена выгрузка заказов «только изменения», источник «Состояния заказов», таблица соответствий runbook'а записана через COM. Заказы сайта: А 213/214, Б 215/216, В 217/218, Г 219/220.
  - А: «К выполнению» (состояние «Ожидается обеспечение») → `processing`; резерв «Отгрузить» на «1 СДВ склад» (состояние «В процессе отгрузки») → `at_warehouse`; реализация (оформил владелец в UI) → «Ожидается оплата» → `shipped`; ПКО + статус «Закрыт» → `delivered`. Мастер шёл вместе с субзаказом.
  - Б: все строки отменены, УТ даёт «Готов к закрытию» → «Отгружен», в XML `Отменен`=true и 0 строк → `cancelled`. В: пометка удаления, статуса нет → `cancelled`.
  - Сводный пакет (А, Б, В, Г) — `backend/data/import_1c/orders/orders_1_89b0ff0d-b9e7-4cfe-93bf-10ab3cbef25c.xml`; `test_orders_bus_import.py` — 16 passed, `test_bus_orders_real_export` больше не скипается. В приватный репозиторий не пушился.
  - Находки: (1) форма «Сопоставление статусов» даёт одну строку на Ид сайта, «Добавить»/«Копировать» отключены (`Form.xml`) — таблица «многие состояния → один Ид» из runbook'а через UI не собирается; (2) итог `[BUS ORDERS] …` пишется INFO, а логгер `apps.integrations` не настроен (root WARNING) — строки нет ни локально, ни на проде; (3) заказ, загруженный с сайта, БУС к выгрузке не регистрирует (`ЗагрузкаСБУС`, `БУС_РегистрацияИзмененийВызовСервера:108`) — первый этап уходит на сайт только после правки заказа в 1С.
- 23.11.2026, итог находок (1)–(3) — `spec-1c-order-statuses-followup.md`: в `STATUS_MAPPING` первыми идут 10 состояний УТ одноимёнными Ид по жизненному циклу, прежние ключи сохранены (реальный файл `orders_1_89b0ff0d-….xml` разбирается как раньше); логгер `apps.integrations` — INFO, `propagate=False`, хендлер со временем и уровнем во всех модулях настроек; runbook — таблица 1:1, очистка строк с прежними Ид, ограничения УТ и БУС, порядок перенастройки формы на `test_base`.

## Spec Change Log

- 23.11.2026 (владелец, `spec-1c-order-statuses-followup.md`): Always «Соответствия runbook'а» переведено с таблицы «много состояний → один Ид» на таблицу 1:1 (Ид статуса = название состояния УТ). Причина — находка (1) сквозной проверки: форма БУС «Сопоставление статусов» даёт одну строку на Ид и не позволяет добавить вторую. Статусы сайта для каждого состояния не изменились; прежние Ид остаются в `STATUS_MAPPING`.

## Review Triage Log

| # | Находка ревью 23.11.2026 | Вердикт | Что сделано |
|---|---|---|---|
| 1 | XML БУС с namespace — парсер не видит `Документ` | high, подтверждено (`contragents_*.xml`: `xmlns="urn:1C.ru:commerceml_3"`) | снятие namespace в задаче |
| 2 | При включённой галке «Выгружать отменённые товары» `Отменен`=true у всех | high, подтверждено (`Module.bsl:6854`, `:8672`) | правило отмены по строкам и пометке, плюс runbook |
| 3 | `data/import_1c` не в git, данные в `FREESPORT-1c-test-data` | high, подтверждено (`main.yml:101`, `testing-standards.md`) | `data_dependent`, файл — в приватный репозиторий |
| 4 | Агент не может снять выгрузку | high | Open Question → решение владельца |
| 5 | `_validate_xml_timestamp` роняет старый файл | medium | время в тестах заморожено |
| 6 | «Success всегда» против общего кода и тестов | medium | ответ задан только для маршрута БУС, тест `:1357` назван |
| 7 | Неверное обоснование success | medium | заменено на пересылку пакета |
| 8 | Пропущены `OrderSuccessView`, `orderPdfExport` | medium | добавлены |
| 9 | В архиве может быть несколько XML | medium | «все `orders*.xml` сессии» |
| 10 | Лишние ключи `STATUS_MAPPING`, нет `status_1c` при отмене | low | исправлено |
| 11 | В Verification не те тесты | low | исправлено |
| 12 | Источник `<Номер>` настраивается | low | добавлено в runbook |
| 13 | Размер | low | спека сокращена |
| 14 | Always «`STATUS_PRIORITY` не менять» противоречил Code Map «приоритеты сдвигаются» | medium | владелец 23.11: «логику регрессий не менять, числа сдвигаются» |
| 15 | Галка «Выгружать отменённые товары» + состояние «Закрыт» → `delivered` → бонус за отменённый заказ | high | владелец 23.11: при `Отменен`=true и живых строках финальный статус не ставится |
| 16 | «Очистить temp» сносит `contragents_*.xml` того же обмена | medium | удаляются только обработанные `orders*` |
| 17 | Устаревший пакет пересылается вечно | снято | БУС формирует пакет заново, `ДатаФормирования` = `ТекущаяДатаСеанса()` (`БУС_ВыгрузкаСервер`, `Module.bsl:10050`) |

**Ревью кода, итерация 0 (23.11.2026).** Слои: blind, edge-case, verification-gap; graph-impact не выполнен — индекс GitNexus `stale` из-за незакоммиченного дерева. Маршрут БУС сверен с исходником: каждый пакет — отдельные `checkauth` → `init` (`БУС_ОбменССайтомВызовСервера`, `Module.bsl:930–970`), один файл `orders_<пакет>_<uuid>.xml` (`БУС_ВыгрузкаСервер`, `:2584`), один `mode=import` на исходный XML (`:1098`).

| # | Находка | Вердикт | Маршрут / что сделано |
|---|---|---|---|
| 18 | Сбой БД: `process()` глотает `OperationalError` пакета в `result.errors`, маршрут БУС отвечает `success`, пакет теряется (edge, gap 1, blind) | high — `order_status_import.py:313` | patch: `failure` при «Database error…», тест через `_bulk_fetch_orders` |
| 19 | Второй `mode=import` той же сессии получает «not found» (blind, edge, gap 3) | false | один `orders_*` и один `mode=import` на сессию БУС |
| 20 | Уборка задачи каталога сносит `IMPORT_DIR/<sessid>/orders/`; тест кладёт файл руками (edge, gap 2) | low | недостижимо: в сессии БУС нет других файлов; отклонено |
| 21 | Устаревший пакет → вечный `failure` (blind, edge) | false | см. #17, решение владельца в Always |
| 22 | Нет лимита документов и суммарного размера (blind, edge) | low | файлы «только изменения» малы, член ограничен `FILE_LIMIT_BYTES`; отклонено |
| 23 | Архив с `RuntimeError`/`zlib.error` → `Internal error` (edge) | false | итог тот же `failure`, что и для битого XML по спеке |
| 24 | CRC-ошибка позднего члена — полархива обработано (edge) | low | маловероятно, фикс — новая ветка; отклонено |
| 25 | При `failure` файлы не удаляются, повторная загрузка в тот же sessid допишет их (edge) | false | БУС пересылает пакет в новой сессии |
| 26 | `ПометкаУдаления`=true без `Отменен` не отменяет заказ (blind, edge) | false | правило отмены задано в Always |
| 27 | Ложная отмена без статуса теряет warning (edge) | false | `logger.warning` вызывается до `DocumentSkipped` |
| 28 | Старый путь теперь пропускает не-заказы и снимает namespace; ответ на файл из одних не-заказов сменился (edge) | low | так задано Code Map «в обоих режимах»; `test_orders_xml_mode_file.py` зелёный; отклонено |
| 29 | Докстринг класса: «старый путь не меняется» — неверно (blind) | low | patch: докстринг |
| 30 | `not_found` пишется в `errors` и `consecutive_errors` (blind) | low | шум лога, на ответ не влияет; отклонено |
| 31 | Ложная отмена не видна отдельным счётчиком, две записи в `errors` (blind) | low | warning в логе есть; отклонено |
| 32 | Тест на реальной выгрузке всегда скипается (blind, gap 4) | medium | открытая задача спеки: файл снимает владелец |
| 33 | Синтетический XML против `AGENTS.md` / Never (blind, gap) | false | Never относится к подмене реальной выгрузки; задачи спеки требуют собранных zip и смешанного архива, реальный файл — отдельный `data_dependent`-тест |
| 34 | Runbook ссылается на несуществующий `scripts/prep-1c-test-data.sh` (blind) | low | patch: ссылка убрана |
| 35 | Фильтр `?status=at_warehouse` без теста (gap 5) | low | тест страницы с моками — не прямая правка; отклонено |
| 36 | Тесты: импорт хелперов из unit-модуля, дубль `_strip`, оракул повторяет правила (blind) | low | вреда кроме стиля не названо; отклонено |
| 37 | Тавтологичный assert в `test_info_contains_at_warehouse_stage` (blind) | low | patch: удалён |
| 38 | Смешанный архив оставит `orders_*` в `orders/` на повторный разбор (blind) | false | смешанных архивов у БУС нет, повтор идемпотентен |
| 39 | Комментарий «исторические ключи» над «Отгружен» устарел (blind) | low | patch: комментарий |
| 40 | `BUS_ORDERS_SUBDIR` дублирует карту маршрутизации (blind) | low | отклонено |
| 41 | Вкладка «На складе» ≠ «Передан на склад» (blind) | false | подпись задана Code Map |
| 42 | `OperationalError` при `save()` одного заказа ловит `except Exception` → «Error processing order…», пакет, вероятно, откатывается (`mark_for_rollback_on_error`), маршрут отвечает `success` (graph-impact, после переиндексации; остальные категории слоя — без находок, циклы — базовая линия) | maybe-false | defer (medium, не проверено): нужен тест с `OperationalError` из `Order.save`; фикс — в `process()`, задевает и старый путь |

Патчи #18, #29, #34, #37, #39 внесены; полная проверка Verification: 342 passed, 1 skipped (`test_bus_orders_real_export`, нет файла).

## Design Notes

- **Почему режим `bus_format`, а не общий парсер.** «Нет статуса — не ошибка» и игнор дат оплаты, включённые для всех, поменяли бы ответ старого пути: сейчас файл из одних документов без статуса даёт `failure` (ADR-003). Флаг держит старый путь байт в байт.
- **Почему ещё и каталог `orders/` импорта.** Если в той же сессии `mode=import` другого файла (например, `contragents_*.xml`) пришёл раньше, оркестратор уже перенёс и распаковал архив, и `orders_*.xml` лежит там. Без этого источника маршрут ответил бы «нет XML», и БУС пересылал бы пакет вечно.
- Элементы БУС сверены по `БУС_ВыгрузкаСервер.СформироватьЗаказ` (`Module.bsl:7981`): `<ПометкаУдаления>`, `<ХозОперация>Заказ товара`, `<Номер>` = номер на сайте, `<Товары><Товар><Ид>`, реквизиты «Отменен» (`:8139`) и «Статуса заказа ИД» (`:8197`).

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -p no:sugar tests/unit/test_order_status_import.py tests/integration/test_orders_bus_import.py tests/integration/test_orders_xml_mode_file.py tests/integration/test_onec_exchange_info_mode.py tests/integration/test_order_status_import_db.py tests/integration/test_1c_file_routing.py tests/integration/test_order_exchange_import_e2e.py apps/orders apps/bonuses` — зелёные.
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run` — чисто.
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` и `npx gitnexus check --cycles -r "C:\Users\1\DEV\FREESPORT"` — только ожидаемые символы, новых циклов нет.
