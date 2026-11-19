---
title: 'Статистика показов и кликов баннеров для отчётности в ОРД'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_commit: '738b1f99cf6496c875cce2a1ad9b15ca1b04f753'
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Сайт размещает рекламные баннеры с ERID и как рекламораспространитель обязан ежемесячно передавать в ОРД число показов по каждому креативу (ФЗ «О рекламе», ст. 18.1). Показы и клики баннеров сейчас нигде не учитываются; Метрика не годится как источник — она работает только после согласия на cookie, режется блокировщиками и не попадает в админку.

**Approach:** Собственный обезличенный счётчик: frontend шлёт события «показ»/«клик» пачками на backend, backend копит дневные суммы по баннеру и ERID; маркетинг видит цифры в админке и выгружает месячный CSV для ОРД.

**Decisions (владелец, 19.11.2026):** цель — отчётность в ОРД по рекламе с ERID; источник истины — свой счётчик; Яндекс Метрика в эту задачу не входит (цель `banner_click` перенесена в задачу «Цели Яндекс Метрики»); показ = баннер виден ≥ 50 % площади не меньше 1 с; удаление баннера статистику не уничтожает — строка хранит снимок названия, ERID, рекламодателя и ИНН, ссылка на баннер становится `NULL` (`SET_NULL`), удалять баннер можно; выгрузка для ОРД — универсальный CSV (ERID, рекламодатель, ИНН, баннер, начало и конец периода, показы, клики) для ручного переноса в кабинет ОРД; спецификация не делится, несмотря на объём.

## Boundaries & Constraints

**Always:**
- Показ: ≥ 50 % площади баннера во вьюпорте непрерывно ≥ 1 с при видимой вкладке; один раз на баннер за монтирование секции (возврат на главную — новый показ). Для карусели — каждый слайд отдельно.
- Учитываются все баннеры из API (hero и marketing, темы blue и electric); статические fallback-баннеры без `id` — нет.
- ERID и реквизиты рекламодателя берутся на сервере из баннера в момент события, клиенту не доверяем.
- Сутки — по `Europe/Moscow` (`timezone.localdate()`).
- Приращение счётчиков атомарно (`INSERT … ON CONFLICT DO UPDATE SET views = views + …`), без read-modify-write.
- Сбой отправки статистики никогда не ломает показ баннера и переход по ссылке.

**Never:**
- Не хранить IP, User-Agent, cookie, id пользователя или сессии — только суммы по дням.
- Не ставить cookie и не гейтить счётчик баннеров согласием на cookie (персональные данные не обрабатываются).
- Не трогать Яндекс Метрику (`frontend/src/components/common/YandexMetrika.tsx`) и не слать в неё ни показы, ни клики.
- Не использовать в пути endpoint слова `banner`, `ad`, `promo`, `collect` (списки блокировщиков).
- Не интегрироваться с API конкретного ОРД — только CSV для ручной передачи.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Пачка событий | `POST {events:[{banner_id:5,kind:"view"},{banner_id:5,kind:"click"}]}` | 204; строка (5, сегодня, erid) `views+1, clicks+1` | — |
| Неизвестный/неактивный баннер | `banner_id` нет, `is_active=False` или вне дат | 204, событие молча отброшено | — |
| Невалидное тело | `kind` вне `view|click`, >50 событий, не JSON | 400 | ничего не пишется |
| Бот | UA содержит `bot|crawl|spider|headless|lighthouse` | 204, ничего не пишется | — |
| Превышен лимит | > лимита scope `site_events` с одного IP | 429 | клиент не повторяет |
| Сменился ERID | баннер получил новый ERID в течение дня | новая строка (баннер, дата, новый erid) | — |
| Баннер удалён | у баннера есть строки статистики | удаление проходит; строки остаются с `banner=NULL` и снимком названия, ERID, рекламодателя, ИНН; попадают в CSV | — |

</frozen-after-approval>

## Code Map

- `backend/apps/banners/models.py` -- `Banner`; `is_scheduled_active` (окно дат), `erid`/`advertiser_*`; `_clean_advertisement_fields` выходит рано при `is_advertisement=False` — ERID у нерекламного баннера может остаться заполненным. Сам `Banner` не менять (impact MEDIUM, 9 зависимых).
- `backend/apps/banners/admin.py` -- `BannerAdmin` (impact LOW): добавить колонки; `marketing_admin.py` наследует его для `/marketing/`.
- `backend/apps/banners/views.py`, `urls.py` -- образец view и роутинга; `freesport/urls.py:71` подключает `apps.banners.urls` под `api/v1/`.
- `backend/apps/common/throttling.py` -- `SubscribeRateThrottle` как образец scope-троттла с `ProxyAwareThrottleIdentMixin`.
- `backend/freesport/settings/{base,development,staging,test}.py` -- `DEFAULT_THROTTLE_RATES`: каждому окружению свой scope.
- `backend/apps/users/migrations/0023_staff_role_groups.py` -- выдача прав группам (`create_permissions` до `post_migrate` + `permissions.add`); образец для data-миграции banners.
- Autouse-фикстуры `role_groups` (зовут функцию `0023` после `flush`): `tests/integration/test_manager_clients_section.py:89`, `tests/integration/test_staff_access_lockdown.py:47`, `tests/unit/{test_manager_admin_site,test_marketing_admin_site,test_rich_editor_upload,test_supervisor_admin_site}.py`; `test_marketing_admin_site.py:148` — `test_marketing_site_has_exactly_seven_models`.
- `frontend/src/components/home/MarketingBannersSection.tsx` -- Embla держит все слайды в DOM; IntersectionObserver учитывает обрезку `overflow-hidden` — наблюдать каждый слайд; картинки `loading="lazy"`, `handleImageError` убирает слайд.
- `frontend/src/components/home/HeroSection.tsx:195-232` (blue), `ElectricHeroSection.tsx:156` (electric) -- один DOM-узел, меняется только `currentIndex` (автопрокрутка 5 с, без `key`) — IO повторно не срабатывает.
- `frontend/src/services/api-client.ts` -- брать оттуда базовый URL API; сам axios-клиент (`withCredentials`, refresh-интерцепторы) для событий НЕ использовать.
- `frontend/vitest.setup.ts` -- мока IntersectionObserver нет (есть только в `StatCounter.test.tsx`).
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- гейт `api-contract.yml` (`check_openapi_sync`, `npm run generate:types`).

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/banners/models.py` -- модель `BannerDailyStat`: `banner` FK `SET_NULL, null=True`; `banner_ref_id` (копия pk, не FK, не обнуляется); `date`; `erid` (пустая строка, если нет); снимок `banner_title`/`advertiser_name`/`advertiser_inn`; `views`, `clicks`; unique `(banner_ref_id, date, erid)`, индекс по `date` -- ключ без NULL, удаление баннера не ломает группировку.
- [x] `backend/apps/banners/services.py` -- `record_events(events)`: агрегировать пачку в Python по `banner_id`; ключи сортировать (без дедлоков); на ключ — raw SQL `INSERT … SELECT … FROM banners WHERE id=%s AND <активен в окне дат> ON CONFLICT (banner_ref_id, date, erid) DO UPDATE SET views = t.views + EXCLUDED.views, clicks = …, снимок = EXCLUDED.…`; ERID и реквизиты в снимок — только при `is_advertisement=True`, иначе пустые; `IntegrityError` от гонки с удалением — проглотить и залогировать -- атомарность и защита от гонок.
- [x] `backend/apps/banners/migrations/0008_*.py`, `0009_*.py` -- схема; data-миграция с зависимостью от `("users","0023_staff_role_groups")`: `create_permissions(banners)`, затем `view_bannerdailystat` группам «Маркетинг» и «Руководители»; функция доступна фикстурам -- права в разделе маркетинга.
- [x] Фикстуры `role_groups` из Code Map + `test_marketing_admin_site.py` -- вызывать и функцию `0009`; реестр раздела — 8 моделей -- иначе тесты получат 403 и упадут на составе.
- [x] `backend/apps/banners/{serializers,views,urls}.py` -- `POST /api/v1/site-events/`: `AllowAny`, `authentication_classes=[]`, парсеры JSON и `text/plain` с JSON-телом, валидация, отсев ботов, 204; `throttle_classes=[SiteEventsThrottle]` явно — глобальные `anon`/`user` из `DEFAULT_THROTTLE_CLASSES` к endpoint не применяются; `@extend_schema(request=…, responses={204: None})` -- приём событий.
- [x] `backend/apps/common/throttling.py` + settings -- `SiteEventsThrottle(ProxyAwareThrottleIdentMixin, SimpleRateThrottle)`, scope `site_events`: base/staging/prod `120/min` на IP, development/test `100000/min` -- защита от накрутки.
- [x] `backend/apps/banners/admin.py` -- колонки «Показы / Клики / CTR за 30 дней» в `BannerAdmin` через `Subquery` (не `Sum` по обратному FK); CTR при 0 показов — «—»; read-only `BannerDailyStatAdmin` (`date_hierarchy`, фильтры по баннеру и ERID); действие «CSV для ОРД»: только строки с непустым ERID, группировка по `(erid, banner_ref_id, TruncMonth("date"))` — выбор через границу месяца даёт строку на каждый месяц, запрета нет; реквизиты — из последней по дате строки группы, начало/конец периода — первая/последняя дата с показами среди выбранных внутри месяца; даты `ДД.ММ.ГГГГ`; ИНН и ERID как текст (`="…"`); ячейки, начинающиеся с `= + - @`, экранировать `'`; UTF-8 с BOM, `;`; регистрация в `admin` и `marketing_site` -- корректный отчёт для ОРД.
- [x] `frontend/src/services/siteEvents.ts` -- очередь: отправка раз в 5 с только при непустой очереди, при `visibilitychange→hidden`/`pagehide` и сразу при клике; `fetch` с `keepalive: true`, `credentials: 'omit'`, `Content-Type: text/plain`; ошибки глотаются; `resetForTests()` -- доставка без влияния на UI.
- [x] `frontend/src/hooks/useBannerViewTracking.ts` -- `(element, activeId, loadedId)`: IO порог 0.5 + таймер 1 с + `document.visibilityState`; смена `activeId` при видимой секции перезапускает таймер; таймер идёт только при `loadedId === activeId` (загрузилась картинка именно этого баннера; `onError` сбрасывает `loadedId`) — в hero `<Image>` один и при смене баннера меняется только `src`, булев `ready` остался бы `true` от прошлого баннера; дедуп по `id` за монтирование (устойчив к двойному mount StrictMode); без `IntersectionObserver` в окружении — no-op -- единое определение показа.
- [x] `frontend/src/components/home/{MarketingBannersSection,HeroSection,ElectricHeroSection}.tsx` -- marketing: хук на каждый слайд; hero: хук на `<section>` с `activeId = currentBanner.id`; `onLoad` картинки → `loadedId = id` баннера, чья картинка загрузилась; `onClick` ссылки → `click` -- все места показа.
- [x] Тесты backend `apps/banners/tests/test_site_events.py`, `test_admin.py`: матрица I/O; пачка с повтором одного баннера; параллельные upsert; смена ERID; ERID у нерекламного баннера не пишется; удаление баннера со статистикой через админку; CSV (фильтр по ERID, группировка, выбор через границу месяца → две строки, ИНН с ведущим нулём, экранирование формул). Frontend `__tests__`: хук (порог, 1 с, скрытая вкладка, смена слайда без нового срабатывания IO, смена `activeId` до загрузки новой картинки — таймер не идёт, ошибка картинки, дедуп), очередь; мок IO в существующих тестах секций.
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- регенерировать -- гейт контракта API.

**Acceptance Criteria:**
- Given маркетинговый баннер с ERID на главной, when он виден ≥ 50 % дольше 1 с, then через ≤ 5 с `views` за сегодня выросло ровно на 1, а при повторной прокрутке в том же монтировании секции — не выросло.
- Given hero-карусель видна, when автопрокрутка сменила баннер и новый провисел ≥ 1 с, then показ засчитан новому баннеру.
- Given баннер виден 0,8 с, вкладка скрыта или картинка не загрузилась, then показ не засчитан.
- Given клик по баннеру, when переход выполнен, then `clicks +1` за сегодня независимо от выбора в баннере cookie, а переход не задерживается отправкой.
- Given сотрудник группы «Маркетинг», when он открывает `/marketing/`, then видит статистику только на просмотр и выгружает CSV, где одна строка на креатив (ERID) и баннер за выбранный месяц.
- Given выбраны строки статистики за два календарных месяца, when выгружен CSV для ОРД, then у креатива по строке на каждый месяц, период каждой строки не выходит за свой месяц.
- Given гость без cookie, when он смотрит баннеры, then новых cookie не появляется, а в БД нет IP и UA.

## Implementation Notes

- IP в БД не пишется. Лимит `site_events` держит IP только в ключе кэша Redis не дольше окна лимита (60 с), как `SubscribeRateThrottle`. Запрет «Не хранить IP» относится к БД.
- Показы сотрудникам (маркетинг, менеджеры на главной) учитываются наравне с остальными. Отделить их можно только по cookie или пользователю, а это запрещено в Never. Баннер им действительно показан.
- Баннеры с ERID на проде уже показываются (владелец, 19.11.2026). Отчёт за месяц выката покрывает только дни после выката: показов до выката сайт не знает.

## Spec Change Log

- 19.11.2026, party-mode, сессия 19 (frozen не тронут): CSV для ОРД группируется по `(ERID, баннер, месяц)` (решение владельца; вариант с запретом многомесячной выгрузки отклонён), добавлены AC и тест; в hero вместо булева `ready` теперь `loadedId === activeId`; в спеке явно указан `throttle_classes=[SiteEventsThrottle]`; добавлены Implementation Notes (IP только в Redis, показы сотрудникам, неполный месяц выката), строка в Design Notes о составе CSV и ручная проверка 429.

## Review Triage Log

Ревью спецификации субагентом, 19.11.2026 (до утверждения), все находки приняты:
- high: hero не меняет DOM-узел при смене баннера — `activeId` в хуке.
- high: права из `0009` не попадут в тесты (`flush` + фикстуры `role_groups`), реестр на 7 моделей — подтверждено по коду; фикстуры и реестр в задачах.
- high: multi-row upsert с повтором ключа и дедлоки — агрегация и сортировка ключей.
- medium-high: группировка CSV по снимку дробит креатив — `banner_ref_id`.
- medium: ИНН в Excel и CSV-инъекция — текстовые ячейки и экранирование.
- medium: ERID у нерекламного баннера — в снимок только при `is_advertisement`, в CSV только строки с ERID.
- medium: показ пустого блока до загрузки картинки — `ready` по `onLoad`.
- medium: нет мока IO, таймер очереди в тестах — no-op без IO, `resetForTests()`.
- low: гонка с удалением баннера — `INSERT … SELECT` + перехват `IntegrityError`.
- low: `Sum` по обратному FK в админке, CTR при 0 — `Subquery`, «—».
- low: пустые отправки, лимит staging, URL API — учтено.
- low: пробелы Verification — добавлены `makemigrations --check`, `spectacular`, линтеры, тесты фикстур.

Ревью кода, 19.11.2026, итерация 0 (слои blind-hunter, edge-case-hunter, verification-gap, graph-impact):
- patch · low (verification-gap): фильтры `BannerRefFilter`/`EridFilter` без тестов — регрессия в фильтре по удалённому баннеру опустошила бы CSV; тесты фильтров добавлены.
- patch · low: перечисление `kind` в схеме под общим именем `KindEnum` — будущее поле `kind` переименует оба в хэш-имена и сломает `api.generated.ts`; `ENUM_NAME_OVERRIDES` → `SiteEventKindEnum`.
- patch · low: описание OpenAPI «Ответ всегда пустой», а 400/429 возвращают JSON — формулировка исправлена.
- patch · low: открытие ссылки баннера средней кнопкой (`auxclick`) не считалось кликом — `onAuxClick` при `button === 1` в трёх секциях.
- reject · low: отложенная проверка FK при внешней транзакции (`ATOMIC_REQUESTS`) всплывает на коммите запроса — на production `ATOMIC_REQUESTS` не включён (только `settings/test.py`), там `atomic()` в `record_events` внешний и ошибка ловится; защита добавила бы `SET CONSTRAINTS`.
- reject · low: удаление баннера в админке падает с `IntegrityError`, если первая за день строка статистики закоммитится между `UPDATE … SET NULL` и `DELETE` коллектора — окно в миллисекунды при удалении под трафиком, повтор удаления проходит; лечение — блокировки в `delete_model`.
- reject · low: пустой User-Agent засчитывается — браузеры UA шлют всегда, скрипт подделает любой UA; матрица определяет бота только по списку слов.
- reject · low: `bot` без границ слова отсекает телефоны Cubot — регулярка дословно из замороженной матрицы I/O; изменение — пересмотр намерения, доля таких устройств ничтожна.
- reject · false: накрутка 120 запросов × 50 событий в минуту и урезание до одного показа на баннер в запросе — лимит выбран владельцем в спеке; урезание теряло бы настоящие показы (очередь переживает клиентскую навигацию, повторное монтирование главной даёт второй показ в той же пачке).
- reject · low: отброшенные события и 429 не логируются, лимит по IP бьёт по NAT — ручная проверка 429 после выката записана в Verification.
- reject · low: тест `IntegrityError` подменяет `execute`, а не воспроизводит отложенный FK — на production ошибка всплывает на выходе внешнего `atomic()` внутри `try`; реальный параллельный тест — лишняя сложность.
- reject · low: `BannerRefFilter.lookups` читает всю таблицу — строк «баннеры × дни», десятки тысяч за годы; `DISTINCT ON` можно сделать при росте.
- reject · low: в OpenAPI нет `maxItems: 50` — ограничение drf-spectacular для `many=True`, лимит проверяет сервер.
- reject · low: типы событий продублированы в сериализаторе и `services`, `record_events` считает кликом любой не-`view` — `kind` валидирует сериализатор, другой вызывающей стороны нет.
- reject · false: высокий баннер (выше двух вьюпортов) не набирает 50 % — hero 400–600 px ниже двух высот любого вьюпорта; порог 50 % площади задан намерением.
- reject · low: electric-hero без картинки засчитывается по `/hero-fallback.jpg` — hero не может быть рекламой (`is_advertisement` только у marketing), ERID у него нет, в CSV не попадает; текст креатива при этом виден.
- reject · low: два hero-баннера подряд с одинаковым `src` — `onLoad` не повторится, второй не засчитается — загрузки получают уникальные пути, в CSV hero не попадает.
- reject · low: ветка `imageRef` (картинка из кэша) без теста — страховка поверх `onLoad`, который React вешает до вставки узла.
- reject · false: в CSV нет площадки и стоимости — Design Notes: маркетинг вносит их в кабинете ОРД.
- reject · false: рекламный баннер без ERID выпадает из CSV — ERID у рекламы необязателен (`_clean_advertisement_fields`), без ERID креатив в ОРД не передаётся; правило «только строки с ERID» задано спекой.
- reject · low: дубли `get_cache_key` троттлов и `_csv_cell` из `orders` — вынос в `apps.common` трогает `orders`, вне задачи.
- reject · low: тело без ограничения размера до проверки 50 событий — общий для всех анонимных DRF-endpoint режим, размер режет nginx.
- graph-impact, первый запуск: индекс GitNexus устарел (рабочее дерево не проиндексировано) — слой не выполнен; после `analyze --force` перезапущен на diff с патчами.
- graph-impact, повтор: находок нет — `BannerAdmin` MEDIUM (наследник `MarketingBannerAdmin` согласован), секции главной LOW, новых циклов импорта нет (базовая линия из двух), scope `site_events` наследуется production из `base`.

## Design Notes

Почему `text/plain`: локально страница на `:3000`, API на `localhost/api/v1` — запрос кросс-доменный; `application/json` вызывает preflight, с которым `keepalive` на выгрузке страницы ненадёжен. `text/plain` — CORS-safelisted, сервер разбирает тело как JSON. CSP (`default-src 'self' http: https:`) и nginx запрос не блокируют.

Почему счётчик без согласия: в БД попадают только дневные суммы по баннеру; идентификаторов субъекта нет, cookie не ставятся — это не обработка ПДн. Трафик B2B-сайта мал, поэтому прямой upsert в Postgres без Redis-буфера.

`clicks > views` за день возможно (клик раньше 1 с видимости) — это не ошибка.

CSV содержит только то, что знает сайт: креатив, рекламодатель, период, показы, клики. Площадку и денежную часть (стоимость, сумму по акту) маркетинг вносит в кабинете ОРД по договору. Добавлять их в выгрузку не нужно.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend sh -c "python manage.py makemigrations --check --dry-run && pytest -q -p no:sugar apps/banners tests/integration/test_marketing_section.py tests/integration/test_staff_access_lockdown.py tests/integration/test_manager_clients_section.py tests/unit/test_marketing_admin_site.py tests/unit/test_manager_admin_site.py tests/unit/test_supervisor_admin_site.py tests/unit/test_rich_editor_upload.py tests/unit/test_staff_role_groups_migration.py"` -- expected: миграции не нужны, тесты зелёные.
- После pytest, не параллельно: навык `backend-lint` (black, flake8, isort) -- expected: чисто.
- `python manage.py spectacular --file ../docs/api/openapi.yaml --validate`, затем `check_openapi_sync` в контейнере и `cd frontend && npm run generate:types` без диффа -- expected: контракт синхронен.
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run src/components/home src/hooks src/services` -- expected: без ошибок.

**Manual checks:**
- Локально: главная → баннер в зоне видимости 1 с → строка в `/marketing/banners/bannerdailystat/`; DevTools — запрос `site-events` 204, новых cookie нет; CSV открывается в Excel с целыми ИНН.
- После выката на проде: ответы 429 на `/api/v1/site-events/` в логах nginx. Если они есть, лимит теряет показы, и `site_events` в settings нужно поднять.
