# Архив отложенной работы

Закрытые и неактуальные пункты, перенесённые из `deferred-work.md`. Каждый пункт сверен с кодом `develop` на дату переноса; причина указана строкой «Перенесено». Разделы сохраняют исходные заголовки и порядок.

## Deferred: товары каталога не попадают в серверный HTML (2026-09-25)

- source_spec: none
  summary: **`/catalog` отдаёт в серверном HTML шапку, дерево категорий и футер, но не товары: выдачу загружает клиент.** Серверный `page.tsx` запрашивает только `categories-tree` (для метаданных) и рендерит `<CatalogPageClient />` без данных. Товары приходят из `productsService.getAll(filters)` в эффекте клиента. Поисковик без JS видит каталог без карточек, цен и ссылок на товары. В серверном HTML есть только заглушка фильтра брендов «Загрузка...».
  evidence: Замер прода 2026-09-25 после релиза `2aa8eb0b` (исправление SSR-спиннера `AuthProvider`, `spec-authprovider-ssr-children.md`): в `<body>` `/catalog` 1061 символ текста, карточек товаров нет. Код: `frontend/src/app/(blue)/catalog/page.tsx:143` (`return <CatalogPageClient />`), `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1190` (клиентский запрос товаров), `:1703` (заглушка брендов). Родственный маршрут `/electric/catalog` при сборке пререндерится статически (`○`), его стоит сверить тем же замером.

  **Что учесть.** Первую страницу выдачи нужно загружать на сервере по `searchParams` и передавать в клиент как начальное состояние, а клиент дальше управляет фильтрами. Цены зависят от роли: серверный запрос анонимный, если не пробрасывать токен из cookie так, как это делает страница товара. Анонимно полученную выдачу у вошедшего оптовика клиент должен перезапросить после восстановления сессии, иначе он увидит розничные цены. Кроме того, серверная выдача не должна расходиться с тем, что клиент покажет после гидрации (фильтры из URL, `in_stock`, сортировка), иначе будет мигание или hydration mismatch. **Проверка:** `curl -s https://optisport.ru/catalog` содержит в `<body>` названия товаров первой страницы и ссылки `/product/<slug>`.
  **Перенесено 2026-09-25:** Исправлено спекой `spec-catalog-ssr-first-page.md` (PR #260, релиз `15eea2d0`): серверная страница `/catalog` загружает первую страницу выдачи по `searchParams` и передаёт её клиенту с ключом фильтров; клиент рендерит её сразу и не повторяет запрос. Навигации роутера, сессия в cookie и ссылки с брендом серверный запрос не делают. Замер прода после релиза: в `<body>` `/catalog` 12 ссылок `/product/<slug>` из 910 товаров, `?category=<slug>` — 12 из 15, `?is_new=true` — 5 из 5, «Товары не найдены» нет. Остаток — двойной запрос выдачи на подборках — отдельной записью в `deferred-work.md`.

## Deferred: серверный HTML всех страниц — спиннер `AuthProvider` вместо содержимого (2026-09-24)

- source_spec: none
  summary: **Сервер отдаёт вместо содержимого любой страницы спиннер «Загрузка...»: публичные страницы не рендерятся на сервере.** `AuthProvider` начинает с `isLoading = true` и, пока флаг не снят, возвращает спиннер вместо `children` (`frontend/src/providers/AuthProvider.tsx:164-173`). Снимает флаг только `useEffect`, а на сервере эффекты не выполняются, поэтому SSR каждой страницы заканчивается спиннером. Провайдер оборачивает всё приложение через `Providers.tsx`, который подключён в `(blue)/layout.tsx` и `(electric)/layout.tsx`. Содержимое страниц доходит до браузера только RSC-пейлоадом и появляется после гидрации и инициализации авторизации. Поведение существует с `3ec347b2` (10.12.2025, стори 28.4).
  evidence: Вскрыто 2026-09-24 при проверке JSON-LD товара после релиза `b266216f`: в серверном HTML страницы товара нет ни `Product`, ни `Offer`, ни хлебных крошек, ни названия в теле страницы. Замер `curl` по `/home`, `/catalog`, `/electric`, `/delivery` и `/product/<slug>`: в `<body>` без скриптов только спиннер (432–2436 байт), содержимого нет. Метаданные не страдают: `<title>`, `description`, `canonical`, Open Graph и JSON-LD организации отдаются в HTML, их Next выводит вне дерева провайдера.

  **Последствия.** Поисковик, который не исполняет JS, видит пустые страницы: без текста, товаров, цен, ссылок каталога и разметки `Product`/`BreadcrumbList`. Google рендерит JS и увидит страницу после отрисовки в браузере, Яндекс рендерит JS не всегда. Пользователь до гидрации видит спиннер на весь экран вместо уже полученного содержимого (хуже LCP). Соседняя запись о зависании на этом же спиннере при заблокированном `localStorage` — в разделе «code review of spec-unsubscribe-page-layout (2026-09-16)».

  **Направление.** Не блокировать рендер `children` на время инициализации: провайдер отдаёт детей сразу и публикует `isInitialized`/`isLoading` через контекст. Ждать авторизацию должны только потребители, которым она нужна (защищённые маршруты `/profile/*`, `/checkout`, шапка с состоянием входа); у них уже есть `useAuth()`. Перед правкой — blast radius по потребителям `useAuth` и `useAuthStore`: часть компонентов может неявно рассчитывать, что к их монтированию store уже гидрирован. **Проверка после исправления:** `curl -s https://optisport.ru/product/<slug>` содержит название товара в `<body>` и `"@type":"Offer"` в HTML, а не только в RSC-пейлоаде.
  **Перенесено 2026-09-24:** Исправлено спекой `spec-authprovider-ssr-children.md`: `AuthProvider` рендерит `children` сразу и публикует настоящие `isInitialized`/`isLoading`; запросы, начатые до восстановления сессии, ждут его в request interceptor `apiClient` (`frontend/src/services/authReadyGate.ts`), шапка и `/profile/*` (`AuthGate`) ждут `isInitialized` сами. Локальный замер: в `<body>` `/home`, `/catalog`, `/electric`, `/delivery` и страницы товара есть содержимое, на странице товара `<h1>` с названием и `"@type":"Offer"`. Проверку `curl` на проде сделать после релиза.

## Deferred from: code review of spec-unsubscribe-page-layout (2026-09-16)

- source_spec: `_bmad-output/implementation-artifacts/spec-unsubscribe-page-layout.md`
  summary: **`role="status"` + `aria-live="assertive"` — противоречивая ARIA-разметка на error-состояниях `UnsubscribeClient`.** `role="status"` подразумевает `aria-live="polite"`; для assertive-анонсов идиоматичен `role="alert"`. Паттерн унаследован от исходной реализации страницы и намеренно сохранён спекой («сохранить a11y-поведение»).
  evidence: `frontend/src/app/(blue)/unsubscribe/UnsubscribeClient.tsx` — блоки invalid_token и generic error. Работает в скринридерах, но семантически смешанная конструкция.
  **Перенесено 2026-09-24:** Исправлено: error-состояния `UnsubscribeClient` теперь `role="status" aria-live="polite"`, противоречия нет.
- source_spec: `_bmad-output/implementation-artifacts/spec-unsubscribe-page-layout.md`
  summary: **`AuthProvider`: throw при доступе к `localStorage` вне try-блока → необработанный rejection и `isLoading` навсегда в true (страница виснет на «Загрузка...»).** Баг провайдера, затрагивает все `(blue)`-страницы; вскрыт при анализе гейтинга `/unsubscribe`.
  evidence: `frontend/src/providers/AuthProvider.tsx:66-80` — `localStorage.getItem/setItem` вызываются до try/catch; при заблокированном хранилище `initializeAuth` реджектится.
  **Перенесено 2026-09-24:** Исправлено спекой `spec-authprovider-ssr-children.md`: чтение и запись `localStorage` в `AuthProvider` обёрнуты в try, инициализация — в try/finally, которое всегда снимает ожидание и выставляет флаги; спиннера в провайдере больше нет.

## Deferred from: code review of 41-9-consent-journal-text-version-and-source (2026-09-09)

- **POST подписки отправляется без канонического завершающего slash.** `subscribeService` вызывает `/subscribe`, тогда как Django route и OpenAPI объявляют `/subscribe/`. При стандартном `APPEND_SLASH=True` промежуточный redirect для POST может потерять метод или тело; поведение зависит от прокси/клиента и не должно быть частью контракта. Дефект существовал до Story 41.9; исправление — использовать `'/subscribe/'` и добавить интеграционную проверку реального URL без мокирования транспорта. [`frontend/src/services/subscribeService.ts:75-78`, `backend/apps/common/urls.py:19`, `docs/api/openapi.yaml:85`]
  **Перенесено 2026-09-24:** Исправлено стори 41.11: `subscribeService` шлёт на `/subscribe/` (`frontend/src/services/subscribeService.ts:79`).

## Deferred from: spec-tech-debt-19-followups — порог покрытия `backend-ci.yml` (2026-08-06)

> **Перенесено 2026-09-24:** Закрыт 2026-08-06 (отметка в самой записи).

> ✅ **ЗАКРЫТ 2026-08-06 в тот же день.** Решение Alex: мерить продакшен-код на полном наборе. Подсчёт покрытия перенесён из `backend-ci.yml` в `main.yml` (`--cov=apps --cov=freesport`, порог 75), знаменатель очищен от тестов и миграций через `[tool.coverage.run] omit` в `backend/pyproject.toml`, пороги в `backend-ci.yml` и `deploy.yml` сняты. Замер на полном наборе: 13832 оператора, 3260 непокрытых — **76,4 %**, то есть проектный стандарт «≥ 70 %» выполнялся всё это время и просто не был виден. Подробности — в разделе «Покрытие» файла `backend/docs/testing-standards.md`.

- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md`
  summary: **`backend-ci.yml` красный на `develop` с 2026-08-05: покрытие 64,92 % против порога `--cov-fail-under=65`.** Тесты зелёные (`1930 passed, 2 skipped`) — падает исключительно порог. Требуется решение человека: поднять покрытие, понизить порог или сузить `--cov=.` так, чтобы тестовые файлы не попадали в знаменатель.
  evidence: Pre-existing, началось на стори 40.4 (2026-08-05 17:42, 4 прогона подряд `failure`). Правки 2026-08-06 к этому не причастны: замер на одном дереве дал 64,99 % без `and not slow` и 64,93 % с ним — порог не берётся в обоих случаях. Отдельно опровергнут вывод от 2026-08-03 «порог берётся благодаря округлению»: порог проверяет pytest-cov сырым сравнением `self.cov_total < cov_fail_under` (`pytest_cov/plugin.py:283`), округления там нет вовсе, поэтому запаса не было никогда.
  what_to_do: (1) решить, чем закрывать разрыв в 0,01–0,07 п.п. — новыми тестами или пересмотром порога; (2) отдельно рассмотреть `--cov=.`: он держит в знаменателе сами тестовые файлы, из-за чего исключение любого теста из гейта механически понижает метрику, хотя покрытие продакшен-кода не меняется; (3) до принятия решения помнить, что зелёный `backend-ci.yml` сейчас недостижим и его краснота не сигнализирует о регрессии.
  risk_if_skipped: Постоянно красный гейт перестаёт быть сигналом — следующая настоящая регрессия покрытия или упавший тест утонут в привычной красноте. Защита веток отсутствует (см. `project_branch_protection_absent`), поэтому мержу это не мешает и заметить проблему больше нечем.

## Deferred: тесты импорта 1С не исполняются ни в одном прогоне CI (2026-08-07)

> **Перенесено 2026-09-24:** Закрыт 2026-08-15 (отметка в самой записи).

> ✅ **ЗАКРЫТ 2026-08-15.** Решение: приватный data-репо `FREESPORT-1c-test-data`. Шаг checkout в `main.yml` (секрет `ONEC_DATA_TOKEN`) подключает реальные XML-выгрузки в `backend/data/import_1c/` на раннере. ~32 теста импорта 1С теперь исполняются в CI, а не скипаются. Порог покрытия поднят 73 → 75. Скрипт обновления данных: `scripts/prep-1c-test-data.sh`. Дополнительно исправлены баги путей в 3 тестах (`test_customer_parser.py`, `test_import_customers.py`, `test_link_then_import_1c.py` — `parent^5`/`parents[3]` указывали на корень репо вместо `backend/`), `test_import_customers.py` получил маркер `data_dependent` и skip-механизм, `--ignore` снят со всех workflow. Guard-тесты в `test_pytest_marker_autotagging.py` детектят пропажу шага checkout и возврат `--ignore`.

- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md`
  summary: **~32 теста импорта 1С пропускаются на раннере во всех workflow — не только их покрытие, но и сама проверка импорта в CI отсутствует.** Каталог `backend/data/import_1c/` явно перечислен в `.gitignore` (строки 204-206) и в репозиторий не попадает, а правило проекта требует тестировать импорт только на реальных выгрузках.
  evidence: Вскрыто 2026-08-07 при калибровке порога покрытия. Прогон `main.yml`: 50 skipped против 18 локально; в пропущенных — `tests/unit/test_services/test_customer_processor.py` (23), `tests/integration/test_import_role_from_1c.py` (8), `test_import_opt4_prices.py` (5), `test_import_customers_price_type.py` (4), `test_customers_price_type_detector.py` (4) и другие. Это ровно та область, которую правили стори 40.2–40.5. Следствие для метрики: покрытие в CI структурно на 1,5 п.п. ниже локального (74,92 % против 76,43 %), и порог пришлось калибровать по CI.
  what_to_do: (1) решить, чем питать эти тесты на раннере — обезличенным набором фикстур, сокращённой выгрузкой в репозитории или секретом с архивом; прямой коммит реальных выгрузок исключён (персональные данные контрагентов + репозиторий зеркалится в публичный через `sync-to-public.yml`); (2) до этого не считать зелёный CI подтверждением работоспособности импорта 1С — проверять локально; (3) после появления данных в CI поднять `--cov-fail-under` до локального уровня.
  risk_if_skipped: Регрессия в парсере, процессоре контрагентов или оркестраторе импорта проходит все гейты незамеченной. Именно этот код активнее всего менялся в эпике 40, и именно он даёт самые низкие показатели покрытия среди продакшен-модулей.

## Deferred from: code review of spec-tech-debt-19-followups (2026-08-06)

> **Перенесено 2026-09-24:** Все три пункта закрыты: `UnmarkedTestWarning` — 2026-08-14 (spec-unmarked-test-warning-gate), оповещение nightly — spec-nightly-failure-notification (job `notify` в `performance-tests.yml`), документация — 2026-08-13 коммитом `7a83ce30`.

- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md`
  summary: `UnmarkedTestWarning` — предупреждение, а не гейт: оно не влияет на exit code, тонет в общей сводке рядом с `RemovedInDjango60Warning` и в CI-логе на несколько тысяч строк прочитано не будет. Внутри `backend/` за ту же ошибку хук рвёт сбор `UsageError`, снаружи — шепчет.
  evidence: Асимметрия намеренная (обрывать чужой сбор нельзя), но промежуточные варианты не рассмотрены: `-W error::conftest.UnmarkedTestWarning` в CI-вызовах, `filterwarnings` в обоих `pytest.ini`, ужесточение при явном `-m`, отдельный CI-шаг с `grep -q UnmarkedTestWarning`. Плюс предупреждение глушится `-p no:warnings` и `--disable-warnings` — сейчас их никто не использует, но ничто не мешает.
- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md`
  summary: Nightly `performance-tests.yml` — единственное место исполнения перф- и медленных тестов — не имеет никакого оповещения о падении: ни `if: failure()`, ни issue, ни сообщения в мессенджер.
  evidence: Pre-existing (workflow создан спекой tech-debt-19 2026-08-03), но правки 2026-08-06 повысили ставку: теперь туда же выведены `slow`, а `deploy.yml` деплоит в прод, не выполнив ни одного тайминг-теста. С учётом отсутствия защиты веток (`project_branch_protection_absent`) красный nightly не заметит никто, и «вывели из гейта в nightly» рискует означать «вывели в никуда».
- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md`
  summary: Документация вне `project-context.md` продолжает учить старому вызову тестов — `CLAUDE.md` раздел «Тестирование», `.claude/skills/docker-test-run/` и его зеркало в `.agents/skills/docker-test-run/` содержат `--env-file .env` и `exec` вместо `run --rm`.
  evidence: Из корня репозитория `--env-file .env` резолвится (файл там есть), поэтому команда не сломана — но `exec` требует запущенного контейнера, которого после любого test-таргета нет. Это первые файлы, которые читает агент; расхождение с Makefile гарантирует повторное появление вопроса.

## Deferred from: code review of spec-tech-debt-19-pytest-marker-autotagging (2026-08-03)

> **Перенесено 2026-09-24:** Все четыре пункта закрыты 2026-08-06. Остаток по Makefile вне test-таргетов перенесён в `deferred-work.md` отдельной записью.

> ✅ **ВСЕ ЧЕТЫРЕ ПУНКТА ЗАКРЫТЫ 2026-08-06** спекой `_bmad-output/implementation-artifacts/spec-tech-debt-19-followups.md` (baseline `22b99629`). Записи оставлены с отметками — они объясняют, почему механизм выглядел доведённым наполовину.

- ~~source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-pytest-marker-autotagging.md`~~ ✅ **ЗАКРЫТ**
  summary: «Перф-тест» определён местоположением файла, а не свойством теста — стресс-тесты `PagesCachePerformanceTest` и `PagesAPIStressTest` в `tests/integration/test_pages_performance.py` имеют явный `@pytest.mark.integration` и потому остаются в обычном гейте, тогда как `tests/performance/` из него выведен.
  evidence: Pre-existing классификация, авторазметкой не вводится (явный маркер она не трогает). Но цель «перф-тесты не гоняются на каждом PR» достигнута лишь наполовину. Кандидат на явный `@pytest.mark.performance` на этом файле — механизм для этого уже есть.
  **Как закрыт:** маркеры расставлены **по методам**, а не по классам. Шесть тестов с жёстким ассертом на время получили `performance` и ушли в nightly; `test_cache_invalidation_accuracy_under_load` оставлен `integration` — ассертов на время в нём нет вовсе, он проверяет корректность инвалидации кэша при конкурентной записи, и вывод его из PR-гейтов был бы потерей покрытия (одиночную инвалидацию покрывает `test_pages_api.py::PagesAPICachingTest`, конкурентную — больше ничто). Файл оставлен в `tests/integration/`: маркер задаёт свойство теста и побеждает каталог.
- ~~source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-pytest-marker-autotagging.md`~~ ✅ **ЗАКРЫТ**
  summary: Маркер `slow` объявлен в обоих `pytest.ini`, но не используется ни одним make-таргетом и ни одним workflow — отсечение медленных тестов работает только по каталогу.
  evidence: Наблюдалось на практике 2026-08-03: `apps/products/tests/test_api_products.py::TestProductAPIPerformance::test_retrieve_product_with_100_variants_under_500ms` (помечен `slow`, лежит в `apps/` → получает `unit`) прошёл в полном прогоне и **упал** в замере покрытия часом позже на той же ревизии — тест таймингозависимый и флакует под нагрузкой машины. Он был в быстром гейте и до авторазметки, то есть это pre-existing, но `slow` даёт готовый рычаг вывести такие тесты из PR-гейта, и рычаг не подключён.
  **Как закрыт:** `and not slow` добавлен в `backend-ci.yml`, `deploy.yml`, `main.yml`; nightly `performance-tests.yml` переведён на `-m "performance or slow"`; добавлен таргет `make test-slow`. Флак покинул PR-гейт, но продолжает исполняться ночью.
- ~~source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-pytest-marker-autotagging.md`~~ ✅ **ЗАКРЫТ**
  summary: Тест, чей путь уходит за пределы `backend/` (симлинк наружу, `--pyargs`, явно переданный путь), хук молча пропускает — маркера не получает и в фильтры не попадает.
  evidence: Ветка `except ValueError: return None` в `_relative_parts` не отличает «чужое дерево» от «сломался расчёт пути». Воспроизведено ревьюером: `pytest -m unit /tmp/exttests/test_outside.py ...` отбирает файл без маркера. Вероятность в этом проекте низкая (тесты живут внутри `backend/`), но это ровно тот класс тихого выпадения, ради которого хук написан.
  **Как закрыт (частично — читай границу):** `_relative_parts` возвращает сентинел `OUTSIDE_BACKEND` вместо второго `None`; хук копит такие элементы и выдаёт `UnmarkedTestWarning` со списком файлов и числом тестов в каждом. `UsageError` для непокрытых путей внутри `backend/` не тронут: обрывать чужой сбор своим правилом нельзя.
  **⚠️ Граница, вскрытая состязательным ревью и проверенная на месте:** предупреждение появляется только там, где `backend/conftest.py` вообще загружен — то есть когда rootdir равен `backend/` либо среди аргументов есть хотя бы один путь внутри него. Вызов `pytest /tmp/ext/test_x.py` **без единого внутреннего пути** даёт другой rootdir, conftest не подхватывается, и ни одна наша строка не исполняется — предупреждения нет. Проверено: смешанные аргументы → предупреждение есть; только внешний путь → нет. Закрыть этот случай из conftest невозможно в принципе, он требует плагина, установленного в окружение (entry point или `-p`). Ограничение задокументировано в шапке `backend/conftest.py`.
- ~~source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-19-pytest-marker-autotagging.md`~~ ✅ **ЗАКРЫТ**
  summary: Все таргеты `make test-*`, включая новый `test-performance`, неработоспособны — они ищут `docker/.env`, которого в репозитории нет.
  evidence: Pre-existing и явно выведено за объём спеки. Но `test-performance` заявлен в документации как локальная точка входа в перф-тесты, поэтому пока перф-тесты запускаются только через `performance-tests.yml` или прямой вызов pytest в контейнере.
  **Как закрыт:** `--env-file` снят со всех вызовов `docker-compose.test.yml` (`test`, `test-unit`, `test-integration`, `test-performance`, `test-slow`, `test-fast`, `logs`, `shell`, `db-shell`). Файл не нужен: в `docker-compose.test.yml` нет ни одной подстановки переменных — теперь это не обещание в комментарии, а тест `test_test_compose_has_no_variable_substitution`. Побочная выгода — таргеты работают в worktree без `.env`.
  **Ревью показало, что снятия `--env-file` мало:** `db-shell` ходил под `-U freesport_user -d freesport`, тогда как тестовый контейнер поднимает `postgres`/`freesport_test` — исправлено. `shell` и `db-shell` использовали `exec`, хотя у сервиса `backend` команда по умолчанию `pytest` и все test-таргеты завершаются `down`, то есть подключаться обычно не к чему — переведены на `run --rm`. Первоначальное заявление «побочно исправлены logs/shell/db-shell» было верно синтаксически и неверно по факту.
  **Осталось за объёмом (проверено, не чинилось):** `clean` (строка с `cd docker && docker compose --env-file .env -f docker-compose.yml`) падает ровно с тем же `couldn't find env file`; `format`/`lint` указывают на `-f docker-compose.yml` из корня, где файла нет; `lint` зовёт устаревший `docker-compose`; `createsuperuser`/`collectstatic` — та же ошибка пути; у таргета `migrate` вообще нет тела; `.PHONY` не перечисляет `test-fast`, `test-fast-tools`, `test-local`, `logs`, `shell`, `db-shell`, `clean`. Отдельная задача — «привести Makefile целиком в рабочее состояние».

## Deferred from: code review of spec-1c-unregistered-role (2026-07-26)

- source_spec: `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md`
  summary: Нет индекса на `users.tax_id` — поиск кандидатов по ИНН при каждой B2B-регистрации выполняет seq scan (~4700 строк).
  evidence: `migrations/0003_add_performance_indexes.py:67` индексирует `companies.tax_id`, но не `users.tax_id`. Pre-existing (прежний `.get()` тоже сканировал), объём пока небольшой; при росте базы контрагентов потребуется индекс.
  **Перенесено 2026-09-24:** Закрыто спекой spec-1c-manager-link-counterparty: индекс `users_tax_id_idx`, миграция `0019_add_users_tax_id_index`.

## Ревизия отложенных пунктов spec-trainer-registration-inn (2026-07-26, по данным прод-БД)

- **ОТМЕНЕНО: partial unique constraint на `User.tax_id` накладывать НЕЛЬЗЯ.** Замеры прод-БД
  (`5.35.124.149`, БД `freesport`, 2026-07-26): 65 групп дублей `tax_id`, 502 строки, до **74**
  аккаунтов на один ИНН (например `6952003172` — 74 записи, у каждой свой `company_name`, все с
  `onec_id`). Это не грязь: одно юрлицо ведётся в 1С как несколько контрагентов (филиалы, точки,
  договоры). Миграция с `UniqueConstraint(condition=~Q(tax_id=''))` упадёт и не должна
  накладываться. Не брать в работу пункт ниже в исходной формулировке — устранять надо
  `MultipleObjectsReturned` в `_find_by_tax_id`, а не уникальность.
  Дополнительно: 13 записей имеют ИНН длиной 1/8/9/11 символов — не проходят валидатор `len in [10, 12]`.
  **Перенесено 2026-09-24:** Пункт, к которому относилось решение (`MultipleObjectsReturned` в поиске по ИНН), закрыт: `find_by_tax_id` возвращает список кандидатов. Само решение действует: unique на `tax_id` НЕ накладывать.
- **Первопричина найдена и вынесена в отдельную спеку `spec-1c-unregistered-role`** — импорт 1С
  присваивает всем контрагентам `role='retail'` (рассинхрон `parser._determine_customer_type` →
  `legal_entity|individual_entrepreneur|individual` и `processor.ROLE_MAPPING` → `Опт 1|Тренерская|РРЦ`,
  всегда fallback). Из-за этого ветка привязки в `UserRegistrationSerializer.validate` (требует
  `role != "retail"`) мертва, и B2B-регистрация с любым из 3712 известных 1С ИНН отклоняется.
  **Перенесено 2026-09-24:** Первопричина вынесена и закрыта спекой spec-1c-unregistered-role.

## Deferred from: code review of spec-trainer-registration-inn (2026-07-26)

- **`tax_id` не уникален в БД, а `_find_by_tax_id` использует `.get()`** — при наличии двух `User` с одинаковым ИНН (импорт из 1С + легаси-портальный аккаунт) любая регистрация с этим ИНН падает в `MultipleObjectsReturned` → HTTP 500 вместо 400. Pre-existing: поле `tax_id = CharField(blank=True)` без `unique`/`UniqueConstraint`, проверка дубля выполняется вне транзакции, поэтому две одновременные регистрации с одним ИНН тоже создадут дубль. Требует миграции с частичным unique-констрейнтом (`condition=~Q(tax_id='')`) + `select_for_update`. Обязательность ИНН для всех B2B-ролей повышает плотность значений в колонке и, соответственно, вероятность срабатывания. [`backend/apps/users/models.py:122`, `backend/apps/users/services/identity_resolution.py:93-98`, `backend/apps/users/serializers.py:114-124`]
  **Перенесено 2026-09-24:** Исправлено: `CustomerIdentityResolver.find_by_tax_id` возвращает список кандидатов (`backend/apps/users/services/identity_resolution.py:116`), `.get()` по ИНН больше нет.

## Deferred from: code review of security-subscribe-status-unification — pass 3 (2026-05-17)

- **`ElectricSubscribeForm.tsx` не имеет тестового файла** — `SubscribeForm` и `ElectricSubscribeForm` имеют идентичную логику обработки ошибок, но тест существует только для `SubscribeForm` (`SubscribeForm.test.tsx`). Ветки `validation_error`/`throttled`/`server_error`/`else` Electric-варианта не верифицированы. Эта story удалила из файла ветку `already_subscribed`; отсутствие тестов — pre-existing. [`frontend/src/components/home/ElectricSubscribeForm.tsx`]
  **Перенесено 2026-09-24:** Тест заведён: `frontend/src/components/home/__tests__/ElectricSubscribeForm.test.tsx`.

## Deferred from: code review of security-subscribe-status-unification (2026-05-17)

- **Коммит `83f30fb0` содержит изменения вне scope story** — помимо 7 файлов из File List коммит изменил файл story-предшественника `security-email-enumeration-hardening.md` (смена статуса + блок re-review pass 4, ~27 строк). Смена статуса предшественника оправдана как prerequisite, но добавление re-review-блока — отдельная работа, замешанная в коммит унификации. Гигиена коммита; уже закоммичено. Дополнительно (выявлено повторным ревью): коммит затронул `AGENTS.md`/`CLAUDE.md` (авто-счётчик символов GitNexus `8502→8503`), не указанные ни в File List, ни в Review Findings; таблица «Структура файлов» story (7 файлов) рассинхронена с фактическим File List (11 файлов). [`_bmad-output/implementation-artifacts/Story/security-email-enumeration-hardening.md`]
- **Регенерация `docs/api/openapi.yaml` (AC-7) внесла out-of-scope изменения** — обязательная регенерация схемы проявила pre-existing drift: перестановка `operationId` внутри `/users/addresses/{id}/`, `/users/favorites/{id}/`, `/orders/{id}/`, `/cart/items/{id}/`; рассинхрон тега `Users`/`users` у `/users/favorites/{id}/` (DELETE → `Users`, GET/PATCH/PUT → `users`); смена типа path-параметра `categories-tree {id}` `integer`→`string` с потерей `description`. Контракт `/subscribe/` не затронут. Функционально безопасно, но раздувает diff и ослабляет контракт; рассинхрон тега и тип `id` стоит вычистить отдельной story. [`docs/api/openapi.yaml`]
- **Story-файл «Текущее состояние кода» описывает несуществующий код** — раздел (строки 72-104) цитирует `views.py` с `status.HTTP_201_CREATED` и `@extend_schema` на два ответа; фактически в `develop` этого уже не было на момент начала story. Tasks 1.1/2.1 помечены `[x]`, хотя были no-op (backend приведён к `200` предшественником `security-email-enumeration-hardening`). Completion Notes это признаёт постфактум, но Tasks-чеклист вводит в заблуждение. [`_bmad-output/implementation-artifacts/Story/security-subscribe-status-unification.md`]
  **Перенесено 2026-09-24:** Неактуально: гигиена уже влитых коммитов и story-файлов; шум регенерации OpenAPI; с 2026-08-04 синхронность контракта с кодом держит CI-гейт «Контракт синхронен с кодом», тег `users` у `/users/favorites/{id}/` теперь единый.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-15, Pass 9)

- **W9-5. Сломанный pipeline `npm run generate:types`** — скрипт читает устаревший `docs/api-spec.yaml`, тогда как канонический OpenAPI-файл — `docs/api/openapi.yaml`; типы синхронизировались вручную через `npx openapi-typescript`. Ранее зафиксировано как W5N1 (Pass 1 defer); pipeline остаётся неисправным. [`frontend/package.json`]
  **Перенесено 2026-09-24:** Исправлено: `generate:types` читает `docs/api/openapi.yaml` (`frontend/package.json:23`).

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-15, Pass 8)

- **DN8-1. Email enumeration через 409 «already_subscribed» на `/subscribe/`** — Анонимный атакующий с `pdp_consent: true` и валидным email различает «subscribed/not subscribed» по 201 vs 409. Defer (Alex, 2026-05-15): объединить с WWWW3 Pass 4 (`/unsubscribe/` enumeration) в единую security-story «harden enumeration» — один класс уязвимости, чинить одним паттерном. Смена 409-контракта ломает AC-4 и 7 passes тестов; throttle 30/min ограничивает атаку; маскировка — территория комплаенс-офицера. [`backend/apps/common/views.py:441-451`, `backend/apps/common/serializers.py:120-127`]
  **Перенесено 2026-09-24:** Закрыто security-subscribe-status-unification (2026-05-17): новая и повторная подписка отвечают одинаковым 200.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-15, Pass 7)

- **W7-3. OpenAPI `users` vs `Users` tag case inconsistency в reshuffled blocks** — `/users/favorites/{id}/` GET использует tag `users`, DELETE — `Users`. Swagger UI разделит resource на две секции. drf-spectacular regeneration artifact, pre-existing (= WWW2/WWWW2 Pass 4 deferred); не вводится 35.3. [`docs/api/openapi.yaml:2034-2056`]
  **Перенесено 2026-09-24:** Исправлено: у `/users/favorites/{id}/` все операции под тегом `users`.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-14, Pass 6)

> **Перенесено 2026-09-24:** Неактуально: сопровождение текста story 35.3, runtime не затрагивает.

- **PPPP6-W1. Spec section «Структура файлов» в `story-35-3.md:493-525` отстаёт от Pass 1-5 scope creep** — 9 файлов изменены/созданы без mention в spec list: `backend/apps/common/apps.py`, `throttling.py`, `tests/test_common_config.py`, `users/admin.py`, `users/authentication.py`, settings `base.py/development.py/staging.py/test.py`, `tests/unit/test_users_admin.py`, `tests/unit/test_common_throttling.py`, `services/__tests__/subscribeService.test.ts`. Все задокументированы в Pass 2-5 patch sections, но «Структура файлов» / AC — нет. Косметический spec-maintenance; не блокирует runtime. Симметрично уже-deferred WWW8 Pass 3. [`_bmad-output/implementation-artifacts/Story/35-3-consent-checkbox-in-subscribe-form.md:493-525`]

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-14, Pass 5)

- **W5N1. `docs/api-spec.yaml` рассинхронизирован с `docs/api/openapi.yaml` — frontend codegen читает первый файл** — `frontend/package.json:22` команда `npm run generate:types` указывает на `../docs/api-spec.yaml`, но stories 35.1/35.2/35.3 обновляли `docs/api/openapi.yaml`. Codegen может видеть устаревший контракт. Pre-existing inconsistency (= уже зафиксировано в Pass 1 defer от 2026-05-13: «`frontend/package.json:22 generate:types` указывает на устаревший путь»). Решение: либо мигрировать package.json на `docs/api/openapi.yaml`, либо удалить один из файлов как канонический. [frontend/package.json:22, docs/api-spec.yaml vs docs/api/openapi.yaml]
  **Перенесено 2026-09-24:** Исправлено: `generate:types` читает `docs/api/openapi.yaml` (`frontend/package.json:23`).

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-14, Pass 4)

- **WWWW2. OpenAPI yaml: массовая перестановка get/patch операций для unrelated endpoints** — drf-spectacular regenerated с другим порядком ключей (`/users/addresses`, `/users/favorites`, `/orders/{id}`, `/cart/items/{id}` и др.). Blind Hunter подсветил возможную утрату описаний `'401'`/`'404'` для `/orders/{id}` — требуется сверка с прошлой версией. Если действительно утрачены — regression в API контракте, не связанный со story 35.3. Отдельная задача audit. [`docs/api/openapi.yaml`]
- **WWWW3. `/unsubscribe/` не обвешан throttle — email enumeration vector** — После DDN2 Pass 3 `/subscribe/` ограничен 30/min, `/unsubscribe/` остался под global anon 6000/min. Массовые запросы `/unsubscribe/` с разными email-ами различают 200 (was subscribed) vs 404 (not subscribed) → пассивное email enumeration. Pre-existing — endpoint не менялся в 35.3. Security-story «harden unsubscribe enumeration». [`backend/apps/common/views.py:518-554`]
  **Перенесено 2026-09-24:** WWWW2 — шум регенерации OpenAPI; с 2026-08-04 синхронность контракта с кодом держит CI-гейт «Контракт синхронен с кодом». WWWW3 — закрыто: `/unsubscribe/` под `UnsubscribeRateThrottle` и отвечает одинаковым 200.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-14, Pass 3)

- **WWW3. `_has_error_code` рекурсивная без depth-limit** — Глубоко вложенный сериализатор или вредоносный nested-error может вызвать stack overflow. Маловероятно для текущего сериализатора (глубина 1-2), но code smell. [`backend/apps/common/views.py:13-19`]
  **Перенесено 2026-09-24:** Неактуально: `_has_error_code` удалён из `backend/apps/common/views.py`.
- **WWW8. Spec разделы «Структура файлов (изменения)» и «API контракт» отстают от Pass 1/Pass 2 scope creep** — `apps/common/throttling.py`, `apps/users/admin.py`, `apps/users/authentication.py`, `settings/base.py+production.py`, `tests/unit/test_common_throttling.py`, `tests/unit/test_users_admin.py`, `frontend/src/services/__tests__/subscribeService.test.ts` — все реально изменены/созданы, но не в spec-списке. API contract не упоминает 503 (PP2). [`spec lines 493-525, 466-480`]
  **Перенесено 2026-09-24:** Неактуально: сопровождение текста story 35.3, runtime не затрагивает.
- **WWW11. `serializer.save()` бросает `serializers.ValidationError` — нарушение DRF-конвенции** — DRF expects ValidationError только в `is_valid()`. View ловит её специально, но middleware/wrapper, ожидающий стандартного flow (exception_handler с auto-400 mapping), может неверно обработать race. `from exc` теряет traceback в логах. Pass 2 PP2 pattern. [`backend/apps/common/serializers.py:120-127` `already_subscribed_error()`]
  **Перенесено 2026-09-24:** Неактуально: `already_subscribed_error()` удалён вместе с 409-веткой.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-13, Pass 2)

- **WW1. Stale Redis throttle-ключи после deploy** — Pass 2 ввёл `ProxyAwareUserRateThrottle` (см. DN3), что меняет cache-key для authenticated throttle (REMOTE_ADDR → X-Real-IP/X-Forwarded-For first hop). В первое окно после deploy старые ключи остаются параллельно — временные stale rate limits возможны для уже-throttled пользователей. Не код-issue, ops-concern. Решение: `redis-cli` пройтись по throttle namespace при deploy или принять transient окно. [ops/deploy]
  **Перенесено 2026-09-24:** Неактуально: разовое окно после деплоя мая 2026 давно прошло.

## Deferred from: code review of 35-3-consent-checkbox-in-subscribe-form (2026-05-13)

- **`frontend/package.json:22 generate:types` указывает на устаревший путь `../docs/api-spec.yaml`** — реальный файл `docs/api/openapi.yaml`. Скрипт сломан, dev обходит ручным `npx openapi-typescript ../docs/api/openapi.yaml -o ./src/types/api.generated.ts`. Pre-existing, починить отдельной задачей. [frontend/package.json:22]
- **Шум в `docs/api/openapi.yaml` (перестановка get/patch для unrelated endpoints — Orders/Cart/Favorites/Addresses)** — артефакт перегенерации drf-spectacular в commit 35.3. Не связано с consent-changes, но раздуло diff. Решение: коммитить регенерацию OpenAPI отдельным PR, либо стабилизировать порядок ключей в spectacular settings. [docs/api/openapi.yaml]
  **Перенесено 2026-09-24:** Исправлено: `generate:types` читает `docs/api/openapi.yaml` (`frontend/package.json:23`). Второй пункт — шум регенерации OpenAPI; с 2026-08-04 синхронность контракта с кодом держит CI-гейт «Контракт синхронен с кодом».

## Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-11, Pass 8)

> **Перенесено 2026-09-24:** Неактуально: перекрёстные ссылки на пункты, которые ведутся в других разделах.

- **`validate_email` case-sensitive uniqueness race** — pre-existing (см. Pass 3 entry ниже); не введено 35.2. Подтверждено в Pass 8.
- **Celery `.delay()` внутри `transaction.atomic()`** — pre-existing tech debt (см. Pass 5 + Pass 7 entries); подтверждено в Pass 8.
- **B2B `ogrn`/`legal_address` silent-drop** — pre-existing Pass 4 product decision (см. Pass 4 decision entry ниже); подтверждено в Pass 8.

## Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-11, Pass 5)

- **Cross-cutting изменение `get_client_ip` (blank XFF → REMOTE_ADDR fallback) не задокументировано в Change Log story** — Функция используется не только consent flow (LogoutView и др. callers); поведение изменилось: blank first hop XFF (`", 5.6.7.8"`) теперь возвращает `REMOTE_ADDR` вместо `""`. Strict improvement (избегает пустой строки), но cross-cutting side-effect не отмечен в commit message. Решение: при следующем заходе на authentication.py явно описать поведение в Change Log/commit. [backend/apps/users/views/authentication.py:548-557]
  **Перенесено 2026-09-24:** Неактуально: замечание к Change Log уже влитой стори 35.2.

## Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-10, Pass 2)

- **`get_consent_ip_address` location для Story 35.3 reuse** — Helper лежит в `apps/users/views/authentication.py`, но Story 35.3 (`SubscribeForm` consent для анонимов через `session_key`) тоже будет писать `UserConsent.ip_address` и нуждается в той же валидации. Два варианта: (a) re-implement в subscribe-view (DRY violation); (b) импортировать из auth-views (awkward layering — common module зависит от users). Решение: при старте 35.3 переехать в `apps/common/utils.py` (или `apps/common/audit.py`). [backend/apps/users/views/authentication.py:524-544]
  **Перенесено 2026-09-24:** Выполнено: helper живёт в `backend/apps/common/utils/consent_audit.py`.

## Deferred from: code review of 35-1-privacy-policy-page-and-consent-model (2026-05-09)

- **`cache_page` invalidation на `pages/views.py:retrieve` сломан** — Signal `invalidate_page_cache` (`apps/pages/signals.py:12-19`) удаляет ключи `pages_list` и `page_detail_{slug}`, но `@cache_page(60*60*24)` декоратор использует URL-based ключ (Django middleware-style cache_page). После публикации/изменения `Page` через admin фронтенд продолжает получать stale-ответ до 24ч. Pre-existing, не введено этой story. Разобрать архитектурно: либо унифицировать cache-стратегию (manual cache.set/get с консистентным ключом), либо использовать `varying_cache_key` + signal-driven `cache.delete` правильного ключа. [backend/apps/pages/views.py:49 + apps/pages/signals.py:12-19]
  **Перенесено 2026-09-24:** Исправлено стори 41.0: `retrieve` кэширует вручную по ключу `page_detail_{slug}` (`backend/apps/pages/views.py:118`), сигнал удаляет тот же ключ.
- **`revalidate: 3600` = до 1ч stale legal text после публикации/обновления** — Спека мандатирует 3600. Для 152-ФЗ это серая зона: пользователь может видеть устаревший текст до часа после изменения. Решение требует координации backend ↔ frontend: при сохранении `Page` через admin делать `revalidatePath("/privacy-policy")` через webhook или management command. Архитектурное изменение — отдельная story.
  **Перенесено 2026-09-24:** Реализовано: сохранение `Page` вызывает `_revalidate_nextjs` (`backend/apps/pages/signals.py`); прод-конфигурация — PR #249, сквозная проверка ведётся в записи «выкат стори 41.7».
- **`Card`/`Breadcrumb` prop validation, accessibility** — Privacy policy — legally-required страница. Если `Breadcrumb` не выставляет `aria-current="page"` для последнего элемента, accessibility-аудит провалится. Не верифицировано в этой story (компонентный уровень). Поднять при общем accessibility-audit. [frontend/src/components/ui/Breadcrumb.tsx]
  **Перенесено 2026-09-24:** Проверено: `Breadcrumb` ставит `aria-current="page"` последнему элементу (`frontend/src/components/ui/Breadcrumb/Breadcrumb.tsx:70`).

## Deferred from: code review of brand-viewset-filter-normalization (2026-05-07)

- **Все три subagent упали с API 529 Overloaded** (run 1) — Blind Hunter, Edge Case Hunter, Acceptance Auditor запущены параллельно и завершились с `API Error: 529 Overloaded`. Ревью выполнено вручную в основной сессии с тем же набором ролей и контекстом, но без диверсификации LLM. При желании дополнительной верификации перезапустить ревью отдельной сессией (предпочтительно другой LLM).
  **Перенесено 2026-09-24:** Неактуально: разовый сбой инструмента ревью.
- **`test_visible_brands.py::test_returns_empty_brand_ids_for_nonexistent_category_id` out-of-scope для текущей story** (run 2) — Тест добавлен в коммит `265a2862` brand-viewset-filter-normalization, но защищает поведение `visible_brands` action на `ProductViewSet`, явно в `НЕ затрагивается` секции story (line 161). Тест функционально корректен и защищает реальное поведение (`?category_id=999999` возвращает 200 OK с пустым `brand_ids`). Удалять не нужно — добавить в File List предшественника `catalog-hide-out-of-stock-brands` при ретроспективе для traceability. [backend/apps/products/tests/test_visible_brands.py:84-89]
  **Перенесено 2026-09-24:** Неактуально: замечание к traceability закрытой стори.

## Deferred from: review of fix-1c-import-cleanup-race (2026-05-06)

- **Edge case hunter не отработал из-за account rate limit** — Acceptance auditor вернул SPEC_FULLY_SATISFIED, Blind hunter дал 9 findings (3 patched, 2 deferred, 4 rejected), но Edge case hunter (детальный обход всех branching path с акцентом на конкурентность транзакций, исключения в Celery dispatch, edge-input) не запускался. При желании дополнительной верификации запустить отдельной сессией с `bmad-review-edge-case-hunter` skill.
  **Перенесено 2026-09-24:** Неактуально: разовый сбой инструмента ревью.

## Deferred from: review of tech-spec-catalog-category-sort-and-hide-empty (2026-04-30)

- **Race condition `getVisibleCategories` без AbortController**: при быстрой смене фильтров устаревший ответ может перезаписать актуальный `sidebarVisibleIds`. Добавить счётчик версий или AbortController по аналогии с основным списком продуктов. [frontend/src/app/(blue)/catalog/page.tsx — `fetchProducts`]
  **Перенесено 2026-09-24:** Исправлено: `isCurrent()` в `fetchProducts` (`frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1187-1210`) применяет ответ сайдбара только при актуальной версии запроса.

## Deferred from: code review of catalog-hide-out-of-stock-brands run 3 (2026-05-07)

- **Race-manifest при снятии `inStock=false`: stale `getVisibleBrands` ответ перезаписывает `null`** — При быстром снятии чекбокса «В наличии» в полёте может быть `getVisibleBrands(filters_v1)` от предыдущего рендера. После reset (`setSidebarVisibleBrandIds(null)`) и re-fire `fetchProducts` с `inStock=false` старый ответ всё ещё применяется через `.then(ids => setSidebarVisibleBrandIds(new Set(ids)))` — UI вернётся к narrowed списку, нарушая AC11 в окне race. Специфичный manifest уже-deferred общей race-проблемы. Решать единой story по race-protection visible-* запросов с AbortController/version-counter. [`frontend/src/app/(blue)/catalog/page.tsx:653-661, 1109-1116`]
  **Перенесено 2026-09-24:** Исправлено: `isCurrent()` в `fetchProducts` (`frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1187-1210`) применяет ответ сайдбара только при актуальной версии запроса.

## Deferred from: code review of catalog-hide-out-of-stock-brands (2026-05-06)

- AbortController для `getVisibleBrands` — race на быстрых сменах фильтров. Симметрично уже задеферренной проблеме `getVisibleCategories`. Решать единой story по race-protection обоих visible-* запросов. [`frontend/src/app/(blue)/catalog/page.tsx:653`]
  **Перенесено 2026-09-24:** Исправлено: `isCurrent()` в `fetchProducts` (`frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1187-1210`) применяет ответ сайдбара только при актуальной версии запроса.

## Deferred from: code review of catalog-hide-out-of-stock-brands (2026-05-07)

> **Перенесено 2026-09-24:** Дубликат раздела «code review of catalog-hide-out-of-stock-brands (2026-05-06)»; открытые пункты ведутся там.

- AbortController для `getVisibleBrands` — race на быстрых сменах фильтров. Симметрично уже задеферренной проблеме `getVisibleCategories`. Решать единой story по race-protection обоих visible-* запросов. [`frontend/src/app/(blue)/catalog/page.tsx:653`]
- `Promise.all` failure mode в `fetchProducts`: при падении `productsService.getAll` `getVisibleCategories`/`getVisibleBrands` уже могут успеть обновить sidebar — рассинхрон с грид'ом продуктов. Pre-existing паттерн (тот же эффект у `visible-categories`). [`frontend/src/app/(blue)/catalog/page.tsx:645`]
- `BrandViewSet.featured` использует фиксированный `FEATURED_BRANDS_CACHE_KEY` без измерения по query-параметрам. Сейчас `get_queryset` корректно short-circuit'ит `has_stock` для featured, но любое будущее добавление query-фильтрации к `featured` приведёт к poisoning'у кэша. Зафиксировать как ограничение. [`backend/apps/products/views.py`]
- Variant `is_active=True` не проверяется в `Exists`-subquery `has_stock`-фильтра. Соответствует существующему паттерну `Product.has_stock`-аннотации (`views.py:102`). Кейс «активный продукт + неактивный вариант с stock>0» консистентен с продуктовым фильтром. Менять — отдельной story с пересмотром `is_in_stock`/`can_be_ordered`. [`backend/apps/products/views.py:397-401`]

## Deferred from: code review of story-35.4-cookie-banner run 2 (2026-05-16)

- Нет синхронизации согласия между вкладками — `useCookieConsent` читает `localStorage` только при монтировании, нет слушателя события `storage`. Если принять cookie в одной вкладке, на других открытых вкладках баннер останется висеть до перезагрузки. Спека описывает информационный баннер и multi-tab sync не требует — минорный UX. [`frontend/src/hooks/useCookieConsent.ts:14-24`]
  **Перенесено 2026-09-24:** Исправлено: `useCookieConsent` слушает событие `storage`.

## Deferred from: code review of security-email-enumeration-hardening (2026-05-17)

- В коммит security-фикса `e76b7e6c` попали несвязанные правки документации (Next.js 14→15 в `docs/architecture/04-component-structure.md`, счётчик символов GitNexus 8500→8499 в `AGENTS.md`/`CLAUDE.md`). Гигиена коммита — несвязанные изменения затрудняют ревью и откат. Уже закоммичено.
- Full regression при переводе story в review: `2270 passed, 11 failed`. 10 падений — `tests/integration/test_management_commands/test_import_customers.py` из-за отсутствия `/app/data/import_1c/contragents`; 1 — `test_retrieve_product_with_100_variants_under_500ms` (562ms vs порог 500ms, деградация производительности без отдельного тикета). Заявлены вне scope в Dev Agent Record.
  **Перенесено 2026-09-24:** Неактуально: гигиена влитого коммита; падения закрыты — данные 1С в CI с 2026-08-15, перф-тест помечен `slow` и выведен в nightly.
- **Resolved by `security-subscribe-status-unification` (2026-05-17).** `/subscribe/` остаточный вектор enumeration (201 vs 200): новая подписка и already_subscribed унифицированы на нейтральный `200 OK`; backend schema/tests, MSW mock, frontend service и generated API types синхронизированы. [`_bmad-output/implementation-artifacts/Story/security-subscribe-status-unification.md`]
  **Перенесено 2026-09-24:** Resolved (отметка в самой записи).

## Deferred from: code review of security-email-enumeration-hardening (2026-05-17, pass 3)

- `/unsubscribe/` не имеет `@parser_classes([JSONParser])`, который есть у `subscribe` — принимает form-urlencoded/multipart, более широкая поверхность атаки. Pre-existing асимметрия декораторов. [backend/apps/common/views.py:547]
  **Перенесено 2026-09-24:** Дубликат пункта о `parser_classes` из pass 2 (остаётся открытым там).
- Несвязанная регенерация `openapi.yaml` в коммите security-фикса: перестановка блоков `/users/addresses/`, `/users/favorites/`, `/orders/`, `/cart/items/`, смена типа id у `categories-tree` (`string`→`integer`). Также рассинхрон тегов `tags: [users]` vs `[Users]` у `/users/favorites/{id}/` — endpoint размножится по двум tag-группам в Swagger UI. Гигиена коммита. [docs/api/openapi.yaml]
  **Перенесено 2026-09-24:** Неактуально: шум регенерации OpenAPI; с 2026-08-04 синхронность контракта с кодом держит CI-гейт «Контракт синхронен с кодом».

## Deferred from: code review of fix-consent-checkboxes (2026-05-19)

- source_spec: `_bmad-output/implementation-artifacts/spec-1c-client-portal-linking.md`
  summary: `PasswordResetRequestView`/`PasswordResetConfirmView` полностью обходят весь фичер привязки — фильтруют только по `email` + `is_active=True`, не проверяют `verification_status`; любой `created_in_1c=True` клиент (unusable password, `is_active` по умолчанию `True`) может получить рабочий пароль через обычный "forgot password" без знания `tax_id` и без одобрения администратора. Усугубляется тем, что `UserLoginView` блокирует вход только по `verification_status == "pending"` — `"unverified"` не блокируется, т.е. после такого сброса пароля вход происходит немедленно, обходя весь смысл этой фичи.
  evidence: Blind Hunter (2026-07-09, повторное ревью после round 4). Обновляет предыдущую запись этого файла (была про формальный рассинхрон условий) — после ужесточения guard'а в `validate()` до `verification_status == 'unverified'` состояние `pending` для `created_in_1c=True` теперь реально достижимо через саму эту фичу, поэтому рассинхрон условий актуален уже не гипотетически. HIGH — не требует знания `tax_id`, полностью независимый от этой фичи путь обхода B2B-верификации; существовал до этой спеки, этой спекой не введён и не блокируется её acceptance criteria.
  **Перенесено 2026-09-24:** Закрыто во втором раунде spec-1c-unregistered-role: сброс пароля проверяет `is_unlinked_1c_record`. Хвост про вход со статусом `unverified` ведётся в разделе spec-1c-unregistered-role.
- source_spec: `_bmad-output/implementation-artifacts/spec-1c-client-portal-linking.md`
  summary: (Resolved) `UserRegistrationSerializer.validate_email` делал только `.lower()`, а `CustomerIdentityResolver.normalize_email` — `.strip().lower()`.
  evidence: Blind Hunter (2026-07-09), MEDIUM. Устранено в ходе реализации: `validate_email` удалён целиком, нормализация email в `validate()` теперь всегда идёт через `resolver.normalize_email()` — расхождение больше не существует. Запись оставлена для истории, действий не требует.
  **Перенесено 2026-09-24:** Resolved (отметка в самой записи).

## Resolved: spec-trainer-bonus-program (2026-07-25)

> **Перенесено 2026-09-24:** Resolved 2026-07-25.

Все шесть находок ревью закрыты в рамках отдельной итерации. Решения по
двум продуктовым вопросам приняты человеком (Alex, 2026-07-25).

- **РЕШЕНО.** `BonusTransaction.user` — FK с `on_delete=CASCADE`: удаление пользователя молча стирало весь финансовый журнал.
  Решение (вариант «SET_NULL + снимки»): `user` переведён в `SET_NULL` (`null=True`, `blank=False` — формы по-прежнему требуют тренера), добавлены снимки `user_email_snapshot` / `user_name_snapshot`, заполняемые при создании операции. Удаление по запросу ПДн остаётся возможным, финансовая история сохраняется. Операции удалённого тренера в админке доступны только на чтение. [`backend/apps/bonuses/models.py`, миграция `0003_bonus_journal_survives_deletion`]

- **РЕШЕНО.** `BonusTransaction.order` — `SET_NULL` при ключе идемпотентности `UniqueConstraint(order)`: NULL-ы в PostgreSQL различны, после удаления заказа было возможно повторное начисление.
  Решение: ключ идемпотентности перенесён с FK на снимок `order_number_snapshot` (`UniqueConstraint(order_number_snapshot)` при `transaction_type='accrual'` и непустом снимке). `accrue_for_order` проверяет дубликат по снимку, а не по FK. Серializer и админка показывают номер из снимка, когда заказа уже нет.

- **РЕШЕНО.** Гонка двух одновременных выплат обходила лимит баланса; `objects.create()` не выполнял проверку вовсе.
  Решение: `lock_trainer_account()` берёт `SELECT ... FOR UPDATE` по строке тренера перед чтением баланса в `clean()`. POST админки Django выполняет внутри `transaction.atomic()` (`ModelAdmin.changeform_view`), поэтому блокировка держится от валидации формы до сохранения. Для кода добавлен сервис `create_manual_transaction()`, а `save()` принудительно вызывает `full_clean()` для новых ручных операций — прямой `objects.create()` больше не обходит ни лимит, ни требование комментария.

- **РЕШЕНО.** `accrual_status` допускал выбор `cancelled` / `refunded`.
  Решение: список сужен до `ACCRUAL_STATUS_CHOICES` (нетерминальные статусы) + `CheckConstraint` на уровне БД. Отклонение от буквы спеки («choices из `ORDER_STATUSES`») зафиксировано в Spec Change Log.

- **РЕШЕНО.** Три несовпадающих определения «тренера в программе»: API проверял только роль.
  Решение: `IsTrainer` требует `role='trainer'` И `is_verified` — как начисление и как пункт меню. Неподтверждённый тренер получает 403 с отдельным текстом «Учётная запись тренера ещё не подтверждена менеджером». Условие соответствует §3 `docs/guides/bonus-program-trainers.md`.

- **РЕШЕНО.** Обратный переход в УТ 11 («К выполнению» → «На согласовании») отбрасывался молча.
  Решение (вариант «сохранять `status_1c`»): семантика `STATUS_PRIORITY` не тронута — переход по-прежнему блокируется, но `_record_blocked_status_1c()` фиксирует фактический статус 1С и `sent_to_1c_at`. Расхождение с 1С видно в карточке заказа и админке, а не только в счётчике `skipped_status_regression`. Применено к обеим веткам блокировки (финальные статусы и приоритетная регрессия). [`backend/apps/orders/services/order_status_import.py`]

**Попутно исправлено:** `test_bulk_fetch_orders_optimization` (`assertNumQueries(11)`) был сломан ещё коммитом бонусной программы `72c99a51` — сигнал `post_save` добавил 3 запроса (savepoint + чтение настроек + release). Счётчик обновлён до 14 с разбивкой в комментарии.

## Закрыто спекой spec-1c-manager-link-counterparty (2026-07-28)

> **Перенесено 2026-09-24:** Закрыто 2026-07-28.

- **ЗАКРЫТО: индекс на `users.tax_id`** (пункт от 2026-07-26 в разделе «Deferred from: code review of
  spec-1c-unregistered-role», строки 12-14). Индекс добавлен миграцией
  `backend/apps/users/migrations/0019_add_users_tax_id_index.py` (`users_tax_id_idx`, обычный b-tree,
  объявлен в `User.Meta.indexes`). Поводом стала колонка-индикатор «Кандидат 1С» в changelist
  админки: correlated subquery по строкам страницы без индекса давал seq scan на каждую строку.
  Unique-констрейнт по-прежнему запрещён — 65 групп дублей, до 74 строк на один ИНН.

## Deferred from: code review of security-wholesale-price-visibility (2026-08-04)

> **Перенесено 2026-09-24:** Исправлено: фильтры каталога считают `0` отсутствием спеццены (`Q(field__isnull=True) | Q(field=0)`, `backend/apps/products/filters.py:41`).

- Нулевая специальная цена расходится с фильтрами каталога: `ProductVariant.get_price_for_user()` трактует допустимое `0.00` как отсутствие специальной цены и возвращает `retail_price`, но `ProductFilter.filter_min_price` / `filter_max_price` переходят к рознице только при `NULL`. При `opt1_price=0`, `retail_price=1000`, `min_price=500` товар не попадёт в выдачу, хотя отображается по 1000. Предсуществующая проблема; требуется унифицировать fallback для `NULL` и `0`. [`backend/apps/products/filters.py:271-285`, `backend/apps/products/filters.py:306-320`]

## Deferred from: code review of 40-1-parser-price-type-and-export-regression-detector (2026-08-04)

> **Перенесено 2026-09-24:** Дубликат записи «story 40.1 — приёмка AC1», она остаётся открытой.

- Контрольная выгрузка контрагентов с продакшена после переноса второй редакции патча БУС отсутствует, поэтому AC1 Story 40.1 не подтверждён. Task 0.5 и action item CP-4a остаются открытыми; устранение требует действий администратора 1С и получения продового снимка, а не изменений кода.

## Deferred from: code review of spec-tech-debt-20-api-contract-ci-gate (2026-08-04)

- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-20-api-contract-ci-gate.md`
  summary: Защита веток в репозитории не настроена вовсе, а строки required-контекстов в `.github/scripts/setup-branch-protection.sh` не совпадают с реальными именами check-run — применять скрипт как есть нельзя.
  evidence: Проверено 2026-08-04 через `gh api`: `repos/AlexMobiCraft/FREESPORT/branches/{main,develop}/protection` отдают «Branch not protected». Имя чека последнего прогона — `build (3.12)`, тогда как в скрипте записано «Django CI (build)». Джобы в `backend-ci.yml` и `frontend-ci.yml` обе называются `test`, их check-run неразличимы. Плюс общее свойство GitHub: required-контекст у workflow с фильтром `paths` не сообщает статус на PR, не трогающем эти пути, и блокирует мерж бессрочно — нужна джоба-заглушка без `paths`. Предупреждение вписано в шапку скрипта; исправление требует сверки с живым репозиторием и решения человека. Pre-existing, п. 20 лишь вскрыл.

- source_spec: `_bmad-output/implementation-artifacts/spec-tech-debt-20-api-contract-ci-gate.md`
  summary: `CLAUDE.md` называет `main` и `develop` защищёнными ветками — фактически защиты нет ни на одной.
  evidence: Тот же замер `gh api` от 2026-08-04. Раздел «Git Workflow» в `CLAUDE.md` описывает намерение, а не состояние; агент, читающий его как факт, будет исходить из несуществующих гарантий.
  **Перенесено 2026-09-24:** Закрыто 2026-09-08: защита `main` и `develop` включена, пять контекстов совпадают с реальными чеками; `CLAUDE.md` описывает факт.

## Разделение раздела «code review of spec-tech-debt-19-followups» (2026-08-13)

- ~~source_spec: none~~ ✅ **ЗАКРЫТ 2026-08-14** по `spec-unmarked-test-warning-gate.md`.
  summary: **Отложен пункт про `UnmarkedTestWarning` как гейт** (запись от 2026-08-06 выше). ~~Подход, выбранный 2026-08-13: `UsageError` вместо `warnings.warn`, когда среди аргументов есть явный `-m`.~~ **Реализовано иначе (см. «Как закрыт»): гейт по факту выпадения теста из прогона, а не по наличию `-m`** — условие «есть `-m`» оказалось шире своего обоснования и ложно срабатывало на отрицательных выражениях.
  evidence: Отбор кандидатов 2026-08-13. `filterwarnings = error::conftest.UnmarkedTestWarning` в обоих `pytest.ini` отвергнут — ломает локальный прогон и чужой сбор, то есть ту самую намеренную асимметрию. `-W error::…` в CI-вызовах отвергнут — дублируется в четырёх workflow и не защищает от `--disable-warnings`. Отдельный CI-шаг с `grep` отвергнут как хрупкий. Ужесточение при `-m` бьёт точно в цель (тихое выпадение вредно именно при отборе по маркеру), все четыре CI-вызова уже используют `-m`, и `UsageError` не глушится ни `-p no:warnings`, ни `--disable-warnings` — вторая половина находки ревью закрывается тем же изменением.
  **Как закрыт — с поправкой к самому подходу:** условие «есть явный `-m`» оказалось шире собственного обоснования и в первой реализации было заменено. Неразмеченный тест выпадает из отбора **только при положительном выражении**; при отрицательном (`-m "not performance and not slow"` — фильтр `backend-ci`, `main` и `deploy`) он фильтру удовлетворяет и исполняется. Гейт на «непустой `-m`» ложно обрывал бы три прогона CI из четырёх сообщением «тесты выпадают из отбора», неверным ровно в этой ситуации. Найдено обоими ревьюерами независимо, подтверждено экспериментом (`-m "not slow"` на файле без маркеров → тест собран и исполнен).
  **Итоговая реализация:** хук стал обёрткой (`@pytest.hookimpl(wrapper=True)`) — размечает до отбора, а после сверяет состав `items` и видит, кто реально выпал. Гейт требует двух условий: непустой `markexpr` **и** фактический деселект конкретного элемента (одного деселекта мало — без `-m` тест могли отбросить по `-k`, это выбор запускающего). Проверено подпроцессными тестами `TestRealRun`: положительное выражение → ненулевой код возврата даже при `--disable-warnings -p no:warnings`; отрицательное и отсутствие `-m` → прогон зелёный. Ни один workflow не правился.
  **Перенесено 2026-09-24:** Закрыт 2026-08-14 (отметка в самой записи).
- source_spec: `_bmad-output/implementation-artifacts/spec-unmarked-test-warning-gate.md`
  summary: `make test-unit` (`-m unit`) не исключает `slow`, в отличие от всех трёх PR-гейтов CI, — локальный «unit-прогон» захватывает таймингозависимые тесты и краснеет от загрузки машины.
  evidence: Наблюдалось 2026-08-14: полный `-m unit` под нагрузкой шёл 813 с вместо обычных 440 с, и `TestProductAPIPerformance::test_retrieve_product_with_100_variants_under_500ms` упал на ассерте `elapsed_time <= 500`; изолированно тот же класс — `3 passed за 17 с`. **Сам тест размечен правильно** (`@pytest.mark.slow`, `backend/apps/products/tests/test_api_products.py:247`), и в CI он исключён везде — расходится именно локальная цель: `Makefile:95` даёт `-m unit`, тогда как `backend-ci.yml:209` даёт `-m "... and not slow"`. Итог: `make test-unit` шумнее того гейта, который он изображает.
  **Решение Alex 2026-08-14: править обе цели** — `Makefile:95` → `-m "unit and not slow"`, `Makefile:102` → `-m "integration and not slow"`. Замеры: `unit and slow` = **2 теста** (оба в `TestProductAPIPerformance`, оба меряют время), `integration and slow` = **0** (правится ради симметрии). Функциональное покрытие не теряется: `test_prefetch_related_used_no_n_plus_one` маркера `slow` не имеет, считает SQL-запросы, а не время, и остаётся во всех гейтах. Бриф — `intent-make-targets-slow-filter.md`.
  **Перенесено 2026-09-24:** Исправлено: `Makefile:97,106` — `-m "unit and not slow"` и `-m "integration and not slow"`.
- ~~source_spec: `_bmad-output/implementation-artifacts/spec-unmarked-test-warning-gate.md`~~ ✅ **ЗАКРЫТ 2026-08-15** по `spec-unmarked-test-optout.md`.
  summary: У гейта нет легального опт-аута: чужой тест, приехавший через `--pyargs` из установленного пакета, размечать нечем, переносить некуда, маркер в чужой файл не поставить, а `-m` в CI не убрать.
  evidence: Найдено адверсариальным ревью. Предлагаемый в тексте ошибки выход («уберите `-m`») локально означает полный сбор пакета (~6 минут), а в CI неприменим — состав гейтов защищён тестом `test_pr_gates_exclude_performance_and_slow`. После перехода на гейт по факту деселекта проблема сузилась (срабатывает только когда тест реально выпал), но не исчезла.
  **Решение Alex 2026-08-14: механизм опт-аута не строить — только починить текст и записать ограничение в документацию.** Основание: проверено, что `--pyargs` не используется нигде (0 вхождений в workflow, `Makefile`, `docker/`, обоих `pytest.ini`, `pyproject.toml`), и ни один workflow не передаёт pytest внешних путей — значит **в CI случай недостижим** без намеренной правки workflow, которая пройдёт через ревью; локально выход есть всегда (убрать `-m`). Вариант с переменной окружения отвергнут отдельно: он даёт бесшумный способ отключить гейт в CI, не оставив следа в диффе. Бриф — `intent-unmarked-test-optout.md`.
  **Как закрыт:** механизм опт-аута не строился — закрыт честностью текста и записью ограничения. В `_gate_text` (`backend/conftest.py`) безусловное «Либо уберите отбор, если прогон и должен быть полным» заменено на «Локально помогает и снятие отбора, если прогон и должен быть полным: без `-m` ничего не отбрасывается. В CI такого выхода нет — состав фильтров там зафиксирован и застережён тестами.» Поведение гейта не тронуто: условие `dropped and _markexpr(config)`, состав `_advice`, мягкий режим и порядок кусков в `_join` те же — правился один строковый литерал плюс docstring функции. Формулировка закреплена тестом `test_gate_message_scopes_filter_removal_to_local_runs` в `TestDeselectGate` (проверяет оба якоря и отсутствие прежней фразы). В `backend/docs/testing-standards.md`, раздел «Тест вне дерева `backend/`», записано: выходы локальные и их три (явный маркер, перенос под `backend/`, снятие `-m`), в CI не работает ни один, при `--pyargs` в пределах одного вызова остаётся только `-m` — с обоснованием, почему механизм не построен, и с явным отказом от варианта с переменной окружения.
  **Правки по ревью (2026-08-15):** оба ревьюера независимо нашли, что `test_pr_gates_exclude_performance_and_slow` параметризован по трём workflow (`PR_GATES`), а не по четырём — nightly стережёт `test_nightly_runs_what_pr_gates_dropped`; ссылка исправлена в трёх местах. Утверждение «при `--pyargs` обходного пути нет вовсе» опровергалось блоком «ГРАНИЦА ВОЗМОЖНОСТЕЙ» (`backend/conftest.py:16-20`): вызов без путей внутри `backend/` даёт другой rootdir, и хук не исполняется — по решению Alex утверждение сужено до одного вызова pytest. Формулировка «локальный выход ровно один» противоречила `_advice`, предлагающему перенос и явный маркер, — исправлена.
  **Прогоны:** `tests/unit/test_pytest_marker_autotagging.py` — 69 passed, 15 skipped (скипается `TestCIFilters`: в тест-контейнере смонтирован только `backend/`, workflow-файлов нет). `pytest -q -m "unit and not slow"` — 2026 passed, 17 skipped, 0 failed. Сырой `-m unit` дал 1 failed на `TestProductAPIPerformance::test_retrieve_product_with_100_variants_under_500ms` (515,86 мс) — известный таймингозависимый `slow`-тест из записи выше, изолированно 3 passed. `npx gitnexus detect-changes --scope all` — затронут один символ, `_gate_text`, risk low.
  **Перенесено 2026-09-24:** Закрыт 2026-08-15 (отметка в самой записи).
- ~~source_spec: none~~ ✅ **ЗАКРЫТ 2026-08-13** коммитом `7a83ce30`.
  summary: **Отложен пункт про документацию, учащую старому вызову тестов** (запись от 2026-08-06 выше). Объём уточнён: `CLAUDE.md` раздел «Тестирование», `.claude/skills/docker-test-run/SKILL.md` (`--env-file .env` во всех шести блоках, таблица маркеров без `slow`/`performance`, нет `make test-performance`/`test-slow`) и его зеркало `.agents/skills/docker-test-run/SKILL.md`. Канонический вид — `Makefile:85-122`.
  evidence: Проверено 2026-08-13. `AGENTS.md:82` в объём не входит — там `exec -T backend` относится к dev-среде `docker-compose.yml`, где контейнер действительно запущен, и команда корректна. Разделено по решению Alex: пункт независим от двух других и мержится отдельно.
  **Как закрыт:** `--env-file` снят со всех вызовов `docker-compose.test.yml`, `exec` заменён на `run --rm -T`, зеркало в `.agents/` синхронизировано побайтово. В таблицу маркеров добавлены `performance` и `slow` с пояснением, что `unit`/`integration`/`performance` проставляются автоматически по каталогу, плюс цели `make test-performance` / `test-slow`.
  **Вскрыто при проверке (не входило в исходную формулировку):** пример в `CLAUDE.md` ссылался на `apps/products/tests/test_models.py::TestProductModel::test_create_product` — ни файла, ни класса в проекте нет, копирование примера давало `exit 4` с `file or directory not found`. Заменён на существующий узел `test_product_variant_models.py::TestProductVariant::test_create_variant_with_valid_data`; исправленная команда прогнана в контейнере целиком — `1 passed`, код возврата 0.
  **Перенесено 2026-09-24:** Закрыт 2026-08-13 (отметка в самой записи).

## Deferred from: code review of spec-banner-ad-label-rotate (2026-08-22)

- source_spec: `_bmad-output/implementation-artifacts/spec-footer-links-oferta.md`
  summary: Ссылка «Возврат» → `/returns` в колонке «Информация» мертва, и её адрес зафиксирован зелёным тестом.
  evidence: Найдено Blind Hunter, проверено. Маршрута `returns` в `frontend/src/app` нет (`find src/app -ipath "*returns*"` пуст), CMS-записи с таким slug на проде тоже нет — на проде всего три страницы: `oferta`, `privacy-policy`, `requisites`. Адрес уходит в catch-all `(blue)/[slug]/page.tsx` и отдаёт `NotFoundView` с `robots: noindex`. При этом `Footer.test.tsx:62` утверждает `expect(...'Возврат').toHaveAttribute('href', '/returns')`, то есть тестовый набор охраняет неработающий линк. Пресуществующее. Направление: решить — завести CMS-страницу `returns` или убрать пункт; тест привести в соответствие. **ЗАКРЫТО стори 41.4 (2026-09-05):** ссылка переведена на `/partners#returns` (раздел «Рекламации и возвраты», якорь заведён той же стори), `Footer.test.tsx` приведён к новому адресу. CMS-страница `returns` не заводится — решение владельца.
  **Перенесено 2026-09-24:** Закрыто стори 41.4 (отметка в самой записи).
- source_spec: `_bmad-output/implementation-artifacts/spec-footer-links-oferta.md`
  summary: В подвале остался старый бренд: `© 2026 FREESPORT` и соцссылки `vk.com/freesport`, `t.me/freesport`, `youtube.com/@freesport`.
  evidence: Найдено Blind Hunter. Ребрендинг FREESPORT → OPTISPORT прошёл коммитом `866cbe05`, телефон и почта в том же массиве `DEFAULT_COLUMNS` уже переведены на `optisport.ru`, а copyright и соцсети — нет; то же в `ElectricFooter.tsx`. Пресуществующее. Требует решения владельца: реальные адреса аккаунтов OPTISPORT в VK/Telegram/YouTube неизвестны — менять вслепую нельзя.
  **Перенесено 2026-09-24:** Исправлено: подвалы подписаны `© 2026 OPTISPORT`, соцссылки ведут на аккаунты optisport, VK подтверждён владельцем 2026-09-06.

## Deferred from: code review of spec-requisites-page-update (2026-08-22)

- source_spec: `_bmad-output/implementation-artifacts/spec-requisites-page-update.md`
  summary: Страница `/requisites` не покрыта ни одним тестом, хотя содержит юридически значимые данные, а соседняя правовая страница покрыта.
  evidence: Найдено Blind Hunter. В `frontend/src/app/(blue)/privacy-policy/__tests__/page.test.tsx` тест есть, для `requisites` — ни unit, ни e2e. Следующая правка вёрстки или очередной «ребрендинг текстом» может потерять блок или строку с ОГРНИП при зелёном CI. Направление: smoke-тест «оба ИНН и оба ОГРНИП присутствуют в разметке» — около десяти строк.
  **Перенесено 2026-09-24:** Исправлено: у страницы есть тесты (`frontend/src/app/(blue)/requisites/__tests__/`).
- source_spec: `_bmad-output/implementation-artifacts/spec-register-role-placeholder-color.md`
  summary: Соседний select «Страна» ссылается на несуществующий токен `--color-primary-500`, поэтому его кольцо фокуса рисуется currentcolor, а не фирменным цветом.
  evidence: Найдено Blind Hunter, проверено grep: `--color-primary-500` во всём репозитории только используется и нигде не объявлен (есть только `--color-primary: #ff6600`, `frontend/src/app/globals.css:15`). В select роли токен исправлен в рамках этой правки (там он стал регрессией), в select страны — пресуществующий дефект вне объёма.
  **Перенесено 2026-09-24:** Исправлено: select «Страна» не ссылается на `--color-primary-500`, закреплено `RegisterForm.test.tsx:1035`.
- source_spec: none
  summary: `import_products_from_1c.py:322-327` — `except` фиксирует ошибку через полный `session.save()` без `update_fields` и затирает `report`, накопленный `VariantImportProcessor.log_progress` в БД: у failed-сессий пропадает весь прогресс до падения.
  evidence: Отделено от стори `onec-import-cleanup-race-and-followups` решением Alex 2026-08-26 (Split, ядро гонки T1-T5). Дефект C стори; независимо отгружаемая правка на одну строку, к механике гонки отношения не имеет — влияет только на наблюдаемость упавших сессий. Соответствует AC5 исходной стори.
  closed: 2026-08-27. `session.save()` в обработчике ошибки заменён на `session.save(update_fields=["status", "error_message", "updated_at"])`. Объект `session` загружается в начале прогона и в памяти держит пустой `report`, тогда как `VariantImportProcessor.log_progress` всё это время дописывает его прямо в БД F-выражением; полный `save()` записывал строку целиком и стирал прогресс. RED до правки: отчёт упавшей сессии оказывался пустой строкой. Покрыто `apps/products/tests/test_import_session_report.py` (3 теста: шаги до падения уцелели, отчёт не стал короче, причина падения в отчёте есть).
  not_touched: `load_product_stocks.py` использует голый `session.save()`, но дефекта там нет — команда не пишет `report` через `log_progress`, конкурирующего писателя в ту же строку не существует.
  **Перенесено 2026-09-24:** Закрыто 2026-08-27 (отметка в самой записи).
- source_spec: none
  summary: `backup_db.py:48` — `BACKUP_DIR` по умолчанию относительный (`"backend/backup_db"`), в контейнере резолвится от `/app` и падает с `Permission denied`; ошибка проглатывается в `import_products_from_1c.py:195`, полный импорт каталога на проде идёт без бэкапа неизвестно сколько времени.
  evidence: Отделено от стори `onec-import-cleanup-race-and-followups` решением Alex 2026-08-26 (Split, ядро гонки T1-T5). Дефект B стори; независимый деплой-вопрос (абсолютный путь из настроек + права каталога в образе либо явное отключение шага флагом). Соответствует AC6 исходной стори. **ЗАКРЫТО 2026-08-27:** `BACKUP_DIR` вынесен в настройки абсолютным путём (`/app/var/backups` на постоянном bind-mount `data/prod/backups`, владелец 1000:1000), команда `backup_db` отвергает относительный и недоступный на запись каталог явной ошибкой, шаг управляется `BACKUP_BEFORE_IMPORT`, повторы внутри `BACKUP_MIN_INTERVAL_SECONDS` пропускаются, провал идёт ERROR-ом и в отчёт сессии. Замер, изменивший решение: на прод-выгрузке 27.08.2026 из 172 сессий 37 приходили с `file_type=all` и каждая дёргала бэкап — починка «в лоб» дала бы 37 полных `pg_dump` за одну выгрузку.
  verified_on_prod: 2026-08-27, коммит `a0961ea1`. Бэкап реально создаётся: `/app/var/backups/backup_20260827_120024.sql`, 198.56 МБ, дамп полный (маркер `PostgreSQL database dump complete`, 52 `CREATE TABLE`), файл лежит на хосте в `data/prod/backups/` и переживает пересборку контейнера. Дросселирование подтверждено на живом обмене: с момента выката 2 сессии с `file_type=all` → 1 бэкап создан, 1 пропущен, 0 провалов. Настройки в проде: `BACKUP_DIR=/app/var/backups`, `BACKUP_BEFORE_IMPORT=True`, `BACKUP_MIN_INTERVAL_SECONDS=3600`. Ротация оставляет 3 копии (~600 МБ при 21 ГБ свободных).
  **Перенесено 2026-09-24:** Закрыто 2026-08-27, проверено на проде (отметка в самой записи).
- source_spec: none
  summary: `ProductVariant.size_value` (`models.py:858`) — `max_length=50`, на проде `max(length) = 49`: 12 вариантов в окне offers 17:20-17:24 25.08.2026 не сохранились с `value too long for type character varying(50)`.
  evidence: Отделено от стори `onec-import-cleanup-race-and-followups` решением Alex 2026-08-26 (Split, ядро гонки T1-T5). Дефект E стори; требует отдельной миграции схемы либо осознанной нормализации на входе — к гонке cleanup отношения не имеет и ревьюится независимо. Соответствует AC7 исходной стори.
  task_brief: `_bmad-output/implementation-artifacts/tasks/dev-task-size-value-overflow.md` (2026-08-27). Замер прода изменил постановку: длинные значения — не размеры, а комплектация, состав ткани и наименования услуг (9 записей из 16 619 в диапазоне 41-50 символов при типичных `M`/`S`/`L`/`36`/`42`). Расширение колонки сохранило бы мусор в поле размера, в его индексе и в составном ограничении `(color_name, size_value)`; развилка А/Б/В вынесена в бриф на решение Alex.
  **Перенесено 2026-09-24:** Закрыто спекой spec-ac7-size-value-overflow (2026-08-27).

## Deferred from: проверка импорта изображений 1С (2026-08-27)

> **Перенесено 2026-09-24:** Реализовано: зеркалирование состава фото по `goods.xml` (`mirror_composition=True`, `backend/apps/products/services/variant_import.py:781`). Хвосты частичных выгрузок — в разделе onec-exchange-dir-isolation.

- task_brief: `_bmad-output/implementation-artifacts/tasks/dev-task-image-sync-from-1c.md` (2026-08-27)
  summary: Импорт умеет добавлять картинки и не умеет поддерживать состав. `_import_base_images` и `_import_variant_images` аддитивны: снятое в 1С фото не удаляется, порядок `<Картинка>` не применяется, `main_image` варианта не переназначается (`if not main_image_set`). Обновлённое фото приезжает в БД, но ложится в хвост списка, а витрина показывает первый элемент.
  evidence: Товар 9194 (`gantel-vinilovaja-espado-es1119lpk-svetlo-rozovyj-1-para`): главным висит PNG 14 КБ от 27.04 с чужим товаром (белая гантель 0,5 кг), верное фото 147 КБ приехало 25.08 и лежит вторым. На проде 2467 товаров с фото, 1312 с несколькими, у 104 первая мельче 100 КБ при наличии более крупной — нижняя оценка, замену «крупное на крупное» эвристика не ловит. Смежно вскрыто: goods-сессии дают ровно 253 ошибки `Image not found` каждый прогон (194 962 за 27.08) — 1С ссылается на картинки, файлы которых не передаёт, а `_save_image_if_not_exists` считает отсутствие исходника ошибкой даже при живой копии в `media`; тот же обмен гоняет одну и ту же порцию 129 товаров каждые 5 минут (`created=0`, `updated=129`). Развилка «законно ли зеркалить состав по `goods.xml`» и выбор способа исторической чистки (полная выгрузка из 1С против существующей `deduplicate_images --min-size 100`) вынесены в бриф на решение Alex.

## Deferred from: code review of spec-catalog-pagination-url-state (2026-08-29)

- **Устаревшие ответы видимости могут перезаписать сайдбар.** `getVisibleCategories` и `getVisibleBrands` в `frontend/src/app/(blue)/catalog/page.tsx:718-731` меняют state внутри `.then/.catch` до проверки `requestSeq`; медленный ответ прежнего фильтра способен отрисовать неактуальные категории или бренды. Шаблон существовал в baseline `3cbbf1cf`.
  **Перенесено 2026-09-24:** Исправлено: `isCurrent()` в `fetchProducts` (`frontend/src/app/(blue)/catalog/CatalogPageClient.tsx:1187-1210`) применяет ответ сайдбара только при актуальной версии запроса.

## Deferred from: прод-верификация стори 41.5 (2026-08-30)

> **Перенесено 2026-09-24:** Закрыто стори 41.4 (отметка в самой записи).

- **Ссылка «Возврат» в подвале ведёт на несуществующий `/returns`.** `frontend/src/components/layout/Footer.tsx:69` задаёт `{ label: 'Возврат', href: '/returns' }`, но такого адреса нет ни как маршрута в `frontend/src/app/`, ни как опубликованного CMS-слага: на проде 30.08.2026 `GET /api/v1/pages/` отдаёт ровно три — `oferta`, `privacy-policy`, `requisites`. Ссылка стоит в подвале, то есть мёртвая на каждой странице сайта.
  evidence: Найдено при проверке AC6 стори 41.5 — RSC-префетч подвала дал в консоли `returns?_rsc=… 404` на `/delivery`. Дефект предсуществует, но до стори 41.0 был невидим: несуществующий адрес отдавал 200 с `noindex`, и подвал «работал». Настоящий 404 сделал его наблюдаемым — то есть это не регрессия 41.0, а снятая маскировка.
  Контент, на который ссылка должна вести, на сайте ЕСТЬ — проверено 30.08.2026: раздел «Рекламации и возвраты» на `/partners` (`frontend/src/app/(blue)/partners/page.tsx:154-175`) — недовложение и пересортица плюс рекламации по качеству в течение 14 дней. В `/oferta` условий возврата нет вовсе: ни одного вхождения слов «возврат» и «обмен» на 9072 знака текста, только претензионный порядок. То есть посылка эпика «условия возврата опубликованы, FR-41-15 выполним без создания новых документов» верна, а дефект в том, что ссылка ведёт мимо контента.
  Проверены все ссылки подвала: `/returns` — единственная мёртвая, остальные двенадцать адресов существуют.
  Относится к FR-41-15 стори 41.4. Починка тривиальна (`/returns` → `/partners` либо отдельный маршрут), но исходит не из аудита — брать ли её в объём 41.4, решает владелец. Уточнение внесено в эпик, врезка к FR-41-15.
  **ЗАКРЫТО стори 41.4 (2026-09-05):** владелец взял находку в объём. `Footer.tsx` ведёт на `/partners#returns`, якорь `id="returns"` заведён на секции «Рекламации и возвраты», `Footer.test.tsx` обновлён. Дубль этой же записи выше (`spec-footer-links-oferta`) закрыт тем же изменением.

## Deferred from: code review of 41-3-separate-pdn-and-marketing-consents (2026-08-30)

> **Перенесено 2026-09-24:** Закрыто стори 41.11 в части чекбоксов; ARIA email-поля `ElectricSubscribeForm` ведётся отдельной записью.

- **Обязательность чекбокса согласия не объявлена assistive technologies через `required`/`aria-required`.** В обеих формах кнопка отправки блокируется до установки согласия, но checkbox передаёт только `aria-invalid`, `aria-labelledby` и условный `aria-describedby`; скринридер не получает семантику обязательного поля. Проблема существовала до baseline `13917d4a` и текущей сменой текста не внесена. Исправлять отдельно и синхронно в обеих формах с тестом доступного состояния. [`frontend/src/components/home/SubscribeForm.tsx:151-161`, `frontend/src/components/home/ElectricSubscribeForm.tsx:195-207`]
  **ЗАКРЫТО стори 41.11 (2026-09-12) в части чекбоксов:** в обеих формах подписки чекбоксов стало два (ПДн и рассылка), и оба получили `aria-required="true"` — не `required`, иначе нативная валидация браузера перехватила бы отправку до `react-hook-form`. Закреплено тестами обеих форм. ARIA email-поля `ElectricSubscribeForm` — отдельный пункт, этой стори не затронут.

## Deferred from: code review of 41-4-checkout-trade-info-and-policy-link (2026-09-05)

- **Повторно подтверждено существующее ограничение холодного перехода к якорю.** Основная запись и описание находятся ниже, в разделе реализации стори 41.4; нового отдельного дефекта не заводим. Chromium на локальном frontend: прямой вход `/partners#returns` оставляет `scrollY=0`, секция на `y=1186`; переход по ссылке внутри приложения даёт `scrollY=1090`, секцию на `y=96`. Поэтому AC2 подтверждён только для переходов внутри приложения. Если для устранения потери черновика checkout будет выбрана новая вкладка, исправление холодной прокрутки станет необходимой частью этого решения.
  **Перенесено 2026-09-24:** Дубликат записи о холодном переходе к якорю (стори 41.4), она остаётся открытой.
- **Checkout показывает «Корзина пуста» во время загрузки или после ошибки загрузки корзины.** `CheckoutPageClient` запускает `fetchCart()` после монтирования, но `CheckoutForm` выводит empty-state сразу при `items.length === 0`, не учитывая `isLoading` и `error`. На прямом входе пользователь может увидеть ложное сообщение; при ошибке нет retry-интерфейса. Дефект предсуществует Story 41.4. [`frontend/src/app/(blue)/checkout/CheckoutPageClient.tsx:19-25`, `frontend/src/components/checkout/CheckoutForm.tsx:300,328-335`] → **Взято в стори 41.10** (FR-41-25, `sprint-change-proposal-2026-09-10.md`). **ЗАКРЫТО стори 41.10 (2026-09-11):** `CheckoutPageClient` теперь гейтит рендер через `resolveCheckoutView` (`frontend/src/utils/checkout/checkoutView.ts`) — до `isInitialized`/загрузки корзины показывается `checkout-loading`, при ошибке — `checkout-cart-error` с кнопкой «Повторить», пустая корзина отличается от загрузки и ошибки. `CheckoutForm` монтируется только в состоянии `form`, старые защитные ветки внутри неё не удалены (AC11).
  **Перенесено 2026-09-24:** Закрыто стори 41.10 (отметка в самой записи).

## Deferred from: стори 41.4 — торговая информация при оплате (2026-09-05)

- **Плейсхолдер `example@email.com` в форме восстановления пароля не переведён на русскоязычный образец.** FR-41-18 требует убрать англоязычные `example`-заглушки, но объём стори 41.4 ограничен интерфейсом оформления заказа, поэтому поле восстановления пароля осталось нетронутым. Исправление тривиально (`example@email.com` → `pochta@mail.ru`), но требует проверки тестов формы восстановления. [`frontend/src/components/auth/PasswordResetRequestForm.tsx:77`] → **ЗАКРЫТО стори 41.20 (2026-09-17).** Решение владельца (Alex, 17.09.2026, элемент реестра E21) — плейсхолдер **удалить**, а не заменять на `pochta@mail.ru`, как предполагала эта запись: замена оставила бы латиницу в других четырёх формах и повторила бы регресс E10 (стори 41.16 заменила плейсхолдер на `name@example.ru` и сама породила срабатывание). Видимая подпись «Электронная почта» и `type="email"` делают образец адреса избыточным, а плейсхолдер, дублирующий подпись, — антипаттерн доступности. Тест `should have email placeholder` переписан в «поле электронной почты не имеет плейсхолдера»; инвариант охраняет `frontend/src/__tests__/public-forms-no-example-placeholders.test.tsx` по всем пяти публичным формам.
  **Перенесено 2026-09-24:** Закрыто стори 41.20 (отметка в самой записи).

## Deferred from: стори 41.6 — уникальные метаданные, соцпревью и JSON-LD (2026-09-05)

- ~~**Существование сообщества `https://vk.com/optisport` из `sameAs` не подтверждено.**~~ **Закрыто 2026-09-06:** владелец открыл адрес и подтвердил, что сообщество существует. Адрес остаётся в `ORGANIZATION_SAME_AS` и в подвале, правок не потребовалось. Ниже — исходная запись, оставлена как объяснение, почему проверка не автоматизируется. Три адреса `sameAs` взяты из подвала (`Footer.tsx`, `DEFAULT_SOCIAL_LINKS`). Telegram и YouTube проверены и отвечают 200 (`Optisport - YouTube`, `Telegram: Contact @optisport`). VK на запросы из этого окружения отдаёт 418/404 антибот-заглушку, и отличить «страницы нет» от «запрос отклонён» без браузера нельзя. Если аккаунта нет — это дефект **подвала**, а не разметки: адрес нужно убрать в обоих местах синхронно, потому что `sameAs` на несуществующий аккаунт хуже отсутствия `sameAs`. [`frontend/src/config/organization.ts:22-26`, `frontend/src/components/layout/Footer.tsx:83-106`]
  **Перенесено 2026-09-24:** Закрыто 2026-09-06 (отметка в самой записи).
- **Локальный dev-сервер отдаёт 200 вместо 404 на несуществующий статический файл.** Замер 2026-09-05: `GET http://localhost:3000/never-existed-abcxyz.jpg` → 200 `text/html` со страницей «Страница не найдена» и `noindex`. Поведение **предсуществует** стори 41.6 и наблюдается на пути, который она не трогала, — то есть это не следствие переименования `og-image.jpg`. Это известное ограничение Next 15.5.18, уже обойдённое через `noindex` (см. записи по стори 41.0). Зафиксировано здесь как контрольный замер: `GET /og-image.jpg` после переименования отдаёт `text/html`, а не `image/jpeg`, то есть файл действительно исчез. [`frontend/src/app/not-found.tsx`]
  **Перенесено 2026-09-24:** Неактуально: контрольный замер, а не дефект.
- **`ProductPageClient.tsx` хардкодит `https://optisport.ru` вместо `absoluteUrl()`.** В разметке `Product` поле `offers.url` собирается конкатенацией с литералом домена, тогда как весь остальной SEO-код проекта строит абсолютные адреса из `SITE_URL`/`absoluteUrl` (`frontend/src/utils/seo.ts:11,88`). На проде значения совпадают, поэтому дефект латентный; он выстрелит при смене домена или при просмотре разметки на staging. Предсуществует стори 41.6, её AC8 правку запрещает. [`frontend/src/components/product/ProductPageClient.tsx:96`]
  **Перенесено 2026-09-24:** Исправлено в ветке `fix/jsonld-xss-sessid-traversal`: `offers.url` строится через `absoluteUrl()`. Запись оказалась не такой латентной, как описано: «на проде значения совпадают» перестало быть правдой с релиза 20.09.2026. CI-сборка образа в `deploy.yml` не передавала build-arg `NEXT_PUBLIC_APP_URL`, и образ брал дефолт Dockerfile `http://localhost:3000`. Замер 2026-09-24 на `https://optisport.ru/home`: `canonical`, `og:url`, `@id` в JSON-LD, `sitemap.xml` и `Host`/`Sitemap` в `robots.txt` указывали на `http://localhost:3000`. Переменная окружения контейнера этого не исправляет, `NEXT_PUBLIC_*` вкомпилируются на этапе сборки. В той же ветке `deploy.yml` передаёт `NEXT_PUBLIC_APP_URL` и `NEXT_PUBLIC_YM_ID` из переменных репозитория, а сборка падает, если `NEXT_PUBLIC_APP_URL` не задана. Переменная `NEXT_PUBLIC_APP_URL=https://optisport.ru` заведена 2026-09-24. `NEXT_PUBLIC_YM_ID` пуст и в `.env.prod`, поэтому Метрика на проде отключена намеренно. Проверка после релиза: `curl -s https://optisport.ru/sitemap.xml | grep -c localhost` должно вернуть 0.
  **Проверено на проде 2026-09-24**, релиз `b266216f` (`deploy.yml` завершился в 17:00 UTC). `sitemap.xml`: вхождений `localhost` 0 (до релиза 3370). `robots.txt`: `Host: https://optisport.ru`, `Sitemap: https://optisport.ru/sitemap.xml`. `canonical` на `/home` и `canonical`/`og:url` на странице товара указывают на `https://optisport.ru`. Шаг-страж `Check frontend build variables` прошёл. Сам `offers.url` через `curl` не проверить: разметка `Product` не попадает в серверный HTML (см. запись о спиннере `AuthProvider` в `deferred-work.md`).

## Deferred from: code review of 41-6-unique-metadata-og-image-jsonld (2026-09-05)

- **`/electric` хардкодит корневой production URL в `openGraph.url`.** Значение `https://optisport.ru` не учитывает `SITE_URL` и не содержит путь `/electric`, поэтому на staging/localhost карточка указывает на production, а на production — на другой маршрут. Строка существовала до baseline стори; исправление: использовать `absoluteUrl('/electric')` или перевести страницу на `buildMetadata`. [`frontend/src/app/(electric)/electric/page.tsx:55-63`]
  **Перенесено 2026-09-24:** Исправлено: в `(electric)/electric/page.tsx` нет захардкоженного `https://optisport.ru`.

## Deferred from: code review of spec-ci-node24-actions (2026-09-07)

- **✅ Защита веток включена 2026-09-08.** `main` и `develop` защищены, конфигурация одинаковая: контексты `Бэкенд: тесты`, `Фронтенд: тесты`, `build (3.12)`, `Контракт синхронен с кодом`, `Проверки качества кода`; `enforce_admins: true`; одобрения не требуются; `strict` и `required_conversation_resolution` выключены; force-push и удаление запрещены. Прогон `apply` — 34188150742, обе ветки подтверждены чтением. Откат: `gh api --method DELETE repos/AlexMobiCraft/FREESPORT/branches/<ветка>/protection`.

- **В окружение `production` добавлен required reviewer (2026-09-08).** До этого у окружения был только `branch_policy`, а комментарии в `backend-ci.yml:358` и `frontend-ci.yml:239` — «⚠️ Production deployment requires manual approval» — утверждали неправду: на пуш в `main` джобы `Deploy to Production` срабатывали без всякого подтверждения и диспатчили `deploy.yml` с `environment: production, skip_tests: true`. Теперь любая джоба с `environment: production` ждёт одобрения `AlexMobiCraft`. Проверено на релизном пуше `fd9c6f8a`: джоба ушла в состояние `waiting` и `deploy.yml` не запустила.
  **Перенесено 2026-09-24:** Выполнено 2026-09-08 (информационные записи).
- **НЕ РАЗОБРАНО: `needs.setup.outputs.environment` в `deploy.yml` резолвится в пустую строку.** Джоба `setup` выставляет аутпут (`ENV_NAME="production"`, в логе есть `Set output 'environment'`), но `deploy-production` с условием `if: needs.setup.outputs.environment == 'production'` пропускается на КАЖДОМ прогоне — проверены 34087788185, 34088299745, 34091111753 (все с `main`, все с явным входным `environment: production`). Косвенное подтверждение пустоты: соседняя джоба `build` объявлена как `environment: ${{ needs.setup.outputs.environment }}` и отрабатывает без привязки к окружению. **Следствие:** автоматический деплой на прод не работал никогда — прод обновляется вручную по SSH не по замыслу, а из-за этого дефекта. Пока он не разобран, полагаться на «оно всё равно пропустится» нельзя; страхует явный гейт окружения (см. выше). [`.github/workflows/deploy.yml:22-34,225-227`]

- **Висит неодобренная джоба `Deploy to Production`** в прогонах `Backend CI/CD` 34186989372 и `Frontend CI/CD` 34186989340 на коммите `fd9c6f8a`. Требует явного approve или reject — до этого прогоны остаются в состоянии `waiting`.
  **Перенесено 2026-09-24:** Закрыто PR #224 и починкой цепочки деплоя 20.09.2026: `deploy.yml` проходит целиком, push в `main` — релиз; висевшие прогоны неактуальны.
- **~~`setup-branch-protection.yml` запускается на каждом изменении собственного файла, но защиту не применяет.~~ Частично исправлено 2026-09-07.** Убраны триггеры `create` (срабатывал на создание любой ветки или тега и заводил issue «настройка выполнена» — накопилось 63 штуки) и `push` по собственным путям; остался только `workflow_dispatch` с режимами `check`/`apply`. Скрипт переписан: тело запроса уходит через `--input -` вместо `--field` (строка вместо объекта давала 422), ошибки больше не глушатся сравнением с `"FAILED"` — оно никогда не срабатывало, потому что `gh api` печатает тело ошибки в stdout, — результат перечитывается после записи, а job краснеет при неудаче. Шаг создания issue удалён.

  **Осталось, пункт 1 — секрет `BRANCH_PROTECTION_TOKEN` не заведён.** Попытка выдать job права через `permissions: administration: write` сломала компиляцию workflow (GitHub создал failed-run без job'ов): области `administration` в блоке `permissions` не существует. Значит GITHUB_TOKEN непригоден в принципе — и чтение, и запись branch protection требуют admin. Нужен classic PAT со scope `repo` либо fine-grained PAT с «Administration: Read and write», положенный в секрет `BRANCH_PROTECTION_TOKEN`. Без него оба режима падают с явным сообщением.

  **Исправлено попутно 2026-09-07 — дедлок ревью.** Payload содержал `required_approving_review_count: 1` вместе с `enforce_admins: true`, а коллаборатор в репозитории один (`AlexMobiCraft`). Свой PR апрувить нельзя, поэтому применение таких правил заблокировало бы мерж любого PR необратимо — снять можно было бы только сняв защиту целиком. Заменено на `required_approving_review_count: 0` и `require_last_push_approval: false`; обязательность самого PR, `strict`-проверки статуса и `enforce_admins` сохранены. При появлении второго мейнтейнера оба значения имеет смысл вернуть к `1`/`true` — отмечено в шапке скрипта.

  **Пункт 2 — контексты. Исправлено 2026-09-07.** Прежний список не совпадал ни с одним реальным чеком (preflight на `849dd3c0` дал 0 из 4). Устранены обе причины: джобы `backend-ci`/`frontend-ci` обе назывались `test` — заданы явные `name` «Бэкенд: тесты» и «Фронтенд: тесты»; у `backend-ci`, `frontend-ci` и `api-contract` снят `paths`-фильтр на `pull_request` (у `push` сохранён). Итоговый список из пяти контекстов: `Бэкенд: тесты`, `Фронтенд: тесты`, `build (3.12)`, `Контракт синхронен с кодом`, `Проверки качества кода`. Preflight на `3a89049a` — 5 из 5. Сам preflight при этом пришлось починить: он смотрел только HEAD ветки, а `pre-merge-checks.yml` срабатывает исключительно на `pull_request` и на push-коммите не оставляет чека вовсе — на HEAD `develop` контекст `Проверки качества кода` отсутствовал, и apply получил бы ложный отказ. Теперь берётся объединение чеков HEAD ветки и head-коммита последнего PR в неё. `E2E Tests` намеренно не включён: красный с 2026-09-05, требование заблокировало бы любой мерж — включать после починки `checkout.spec.ts`.

  **Смягчено 2026-09-07 перед включением.** `strict: false` и `required_conversation_resolution: false` — в репозитории один мейнтейнер: `strict` заставлял бы подтягивать `develop` в каждую ветку перед мержем, а `required_conversation_resolution` блокировал бы мерж из-за незакрытого треда бота `claude-review`. Запрет прямого push, пять обязательных проверок, `enforce_admins`, запрет force-push и удаления ветки сохранены. Обе настройки стоит вернуть к `true`, когда появится второй мейнтейнер.

  **Осталось — порядок включения.** `mode=apply` гоняет preflight по HEAD веток `main` и `develop`, а не по фиче-ветке. На `849dd3c0` (develop) и `9475c243` (main) новых имён чеков ещё нет, поэтому apply откажется. Последовательность: смержить PR #134 → дождаться CI на `develop` → `apply` защитит `develop`; для `main` — то же после следующего релиза. Секрет `BRANCH_PROTECTION_TOKEN` заведён 2026-09-07, режим `check` проверен прогоном 34154017767.

- **~~Issue «🔧 Настройка правил защиты веток выполнена» остались открытыми.~~ Закрыто 2026-09-07.** Их оказалось не 12, а **63** — от #9 (2026-07) до #133; первая оценка была сделана по выдаче `gh issue list --limit 10`. Все созданы удалённым теперь шагом от имени `app/github-actions`, все с одинаковым заголовком, без единого комментария и исполнителя, и все утверждали неправду. Закрыты пачкой с причиной «not planned» и комментарием с разбором. После этого в репозитории не осталось ни одной открытой issue. Побочно вскрылось, что `gh issue list --label branch-protection --state open --limit 300` отдаёт не весь набор (вернул 47 из 63) — полный список надёжнее брать без фильтра по метке. [`GitHub Issues`]
  **Перенесено 2026-09-24:** Закрыто 2026-09-07/08: триггеры убраны, секрет заведён, контексты совпадают, защита включена; 63 issue закрыты.

## Deferred from: стори 41.8 (2026-09-08)

- **Копирование текста выделением дефекта НЕ воспроизводит — план стори 41.8 в этом пункте ошибался.** Проверено 2026-09-08 на проде (старый код) и локально (новый): `window.getSelection().toString()` в обоих случаях разделяет слова, потому что браузер вставляет перевод строки на границах блочных элементов. Дефект виден только при программном извлечении (`element.textContent`) — так текст читают парсеры и сканеры доступности, и именно этот путь закрыт стори 41.8. Не тратить время на ручную проверку «выдели и скопируй» в будущих стори этого класса: она даёт ложноотрицательный результат.

  **Что при этом осталось неизмеренным.** Фактическая речь живого диктора (NVDA/JAWS/VoiceOver) в стори 41.8 не снималась. При этом ожидание «чтение улучшится» проверено на слое, откуда дикторы берут данные, и **не подтвердилось**: в Chromium AX tree и в платформенном Windows UIA бейдж, бренд и название были отдельными текстовыми узлами уже до правки, а разделитель в эти деревья не попадает. Не ссылаться на «скринридер теперь читает правильно» как на результат стори: правка даёт корректное `textContent`, и это всё, что замерено. Про произношение наблюдено только состояние деревьев — набор и порядок текстовых узлов до и после совпадают, разделителя в них нет, а структура контейнеров отличается на один уровень `[группа]` в UIA; фактическая речь не снималась, поэтому «произношение не ухудшилось» — тоже утверждение, которого стори не делает. Если гарантия по фактической речи понадобится — нужен отдельный прогон с живым диктором (см. пункт ниже), это самостоятельная задача.
  **Перенесено 2026-09-24:** Неактуально: методическое замечание к стори 41.8, не дефект.

## Deferred from: code review of 41-8-text-separator-badge-brand-product-name (2026-09-08)

- **Прогон карточки товара живым экранным диктором (NVDA/JAWS/VoiceOver) — отдельная задача.** В стори 41.8
  произношение измерялось только по деревьям доступности: Chromium AX tree (CDP) и платформенный
  Windows UI Automation — тот API, из которого дикторы строят речь. Оба слоя показали, что «Акция»,
  «Espado» и название товара были **тремя отдельными текстовыми узлами в отдельных контейнерах ещё до
  правки**, то есть склейка живёт только в `element.textContent`, и `TextSeparator` произношение не меняет
  (в AX tree он `ignored:uninteresting`, в UIA-дереве отсутствует вовсе). Этого достаточно, чтобы
  утверждать «набор и порядок текстовых узлов не изменились», но **не** достаточно, чтобы утверждать
  что-либо о фактической речи — в том числе и что она не ухудшилась: в UIA после правки появился
  дополнительный уровень `[группа]` (фрагмент вокруг `<Badge>`), и как диктор его отрабатывает,
  не проверялось. Живой замер не сделан по инфраструктурной причине: на рабочей машине есть только Windows Narrator,
  чей речевой вывод программно не захватывается, а NVDA — внешняя зависимость, ставить её ради одного
  замера владелец не стал (решение Alex, 2026-09-08). Если гарантия по произношению понадобится —
  нужен отдельный прогон: NVDA portable + speech-лог, карточка до/после, на всех трёх layout'ах.
  **Перенесено 2026-09-24:** Неактуально: решение Alex 2026-09-08 — замер живым диктором не проводить.

## Deferred from: code review of 41-10-checkout-and-cart-for-anonymous (2026-09-11)

> **Перенесено 2026-09-24:** Счётчики GitNexus — шум влитого коммита; вложенный `main` в корзине закрыт 2026-09-12.

- **Автогенерированные счётчики GitNexus попали в R2 changeset вне File List.** Коммит `dccc638a` меняет только числовые счётчики в `AGENTS.md` и `CLAUDE.md`; story прямо отмечает эти файлы как регенерацию, не относящуюся к стори. Runtime не затронут, но изменения создают шум и потенциальные конфликты при следующем `npx gitnexus analyze`. Исправление касается agent-context файлов, поэтому вынесено из code review. [`AGENTS.md:164`, `CLAUDE.md:168`]
- **Изолированный axe-тест `CartSkeleton` не воспроизводит landmark-разметку реальной страницы.** `LayoutWrapper` темы blue уже оборачивает children во внешний `<main>`, а `CartSkeleton`, `EmptyCart`, `CartError` и основная ветка `CartPage` рендерят собственный внутренний `<main>`. Добавленный R2-тест проверяет `CartSkeleton` без layout и потому не может обнаружить вложенный main-landmark. Дефект предсуществует R2 и требует отдельного согласованного изменения всех состояний корзины с интеграционным axe-тестом внутри layout. [`frontend/src/components/layout/LayoutWrapper.tsx:36-41`, `frontend/src/components/cart/CartSkeleton.tsx:65-102`, `frontend/src/components/cart/__tests__/accessibility.test.tsx:338-356`] — **ЗАКРЫТО** (2026-09-12, ветка `fix/blue-nested-main-landmark`, спека `spec-blue-nested-main-landmark.md`): внутренний `<main>` убран из всех 7 мест темы blue — 4 состояния корзины, `HomePage`, `ProfileLayout`, `/search`. Контейнер без имени стал `div`, с именем — `section aria-label`. Axe-тест четырёх состояний корзины внутри настоящего `LayoutWrapper` на старом коде падает, на новом зелёный.

## Deferred from: quick-dev spec-blue-nested-main-landmark (2026-09-12)

- **Вложенный `<main>` в теме electric.** `(electric)/layout.tsx` оборачивает страницы в `<main>`, а `electric/page.tsx` и `electric/catalog/page.tsx` рендерят внутри него собственный `<main>`. Это те же нарушения `landmark-main-is-top-level` и `landmark-no-duplicate-main`, что закрыты в теме blue. Вне охвата спеки: electric — отдельная ветка вёрстки вне `LayoutWrapper` blue. Тема живая для пользователей: маршруты `/electric*` открываются по прямому адресу при любой теме, а при `ACTIVE_THEME=electric_orange` на `/electric` уводит и корень сайта (`app/page.tsx:7`). Значит, двойной `main` получает каждый, кто откроет эти адреса. Направление то же: внутренний `<main>` заменить на `div` или `section aria-label`, стражем поставить axe внутри layout. [`frontend/src/app/(electric)/layout.tsx:11`, `frontend/src/app/(electric)/electric/page.tsx:74`, `frontend/src/app/(electric)/electric/catalog/page.tsx:561`] — **ЗАКРЫТО** (2026-09-12, ветка `fix/electric-nested-main-landmark`, спека `spec-electric-nested-main-landmark.md`): внутренний `<main>` на `/electric` и `/electric/catalog` стал `div`. В каталоге заодно снят вложенный `aside`: колонка фильтров — `aside`, а `ElectricSidebar` внутри неё рендерил свой (axe `landmark-complementary-is-top-level`). Корень `ElectricSidebar` стал `div`, колонка осталась единственным complementary с деревом категорий, фильтрами и «Сбросить фильтры». Страж — axe обеих страниц внутри настоящего `ElectricLayout`; на старом коде он падает.
  **Перенесено 2026-09-24:** Закрыто 2026-09-12 (отметка в самой записи).

## Deferred from: create-story 41.19 — гигиена публичной поверхности (2026-09-17)

> **Перенесено 2026-09-24:** Закрыт 2026-09-22 (отметка в самой записи).

- ✅ **ЗАКРЫТ 2026-09-22** по `spec-remove-dead-electric-components.md`. ~~**Одиннадцать компонентов темы Electric станут мёртвым кодом после удаления `/electric-orange-test`.**~~ Демо-страница `src/app/electric-orange-test/page.tsx` — единственный потребитель `ElectricTabs`, `ElectricHeroBanner`, `ElectricSectionHeader`, `ElectricModal`, `ElectricToast`, `ElectricAccordion`, `ElectricTooltip`, `ElectricTable`, `ElectricFeaturesBlock`, `ElectricCartWidget`, `ElectricSearchResults`. Кроме неё, на `e7a19053` их упоминают только собственные файлы и реэкспорт в `index.ts` своих каталогов (у `ElectricHeroBanner` нет и его); тестов у них нет. Стори 41.19 удаляет страницу (D6), но компоненты не трогает: их чистка в решение D6 не входит и расширила бы дифф стори, которую потом ребейзит 41.18. Решение Alex 2026-09-17: отдельная запись, стори не заводить. Направление: после мёрджа 41.19 повторить `grep -rlw <Имя> frontend/src` и `npx gitnexus impact`, удалить файлы и строки реэкспорта, прогнать `npm test`, `npx tsc --noEmit`, `npm run lint`. Остальные компоненты, которые импортировала демо-страница (`ElectricNewsCard`, `ElectricProductCard`, `ElectricSidebar`, `ElectricBreadcrumbs`, `ElectricPagination`, `ElectricSelect`, `ElectricRadioGroup`, `ElectricSpinner`, `ElectricHeader`, `ElectricFooter`), используются темой `/electric` и остаются. [`frontend/src/app/electric-orange-test/page.tsx:19-41`, `frontend/src/components/ui/{Tabs,Hero,SectionHeader,Modal,Toast,Accordion,Tooltip,Table,Features,Cart,Search}/`]

## Закрыто задачей «транзакционная целостность регистрации» (2026-09-24)

_Из раздела «Deferred from: code review of 41-9-consent-journal-text-version-and-source (2026-09-09)»_

- **Регистрация принимает truthy-значения `pdp_consent`, не являющиеся JSON boolean `true`.** `UserRegistrationSerializer` использует DRF `BooleanField`, после чего проверяет только truthiness нормализованного значения; строки `"true"`, `"on"`, `"yes"` и число `1` могут стать `True` и привести к записи юридически значимого согласия. Эндпоинт подписки уже требует исходное `self.initial_data.get("pdp_consent") is True`, но регистрационная асимметрия существовала до Story 41.9. Исправление: применить такую же проверку исходного JSON boolean и добавить параметризованные regression-тесты. [`backend/apps/users/serializers.py:81-89,193-194`, `backend/apps/common/serializers.py:95-102`]
  **Перенесено 2026-09-24:** `validate_pdp_consent` принимает только исходный JSON `true`, как подписка; тест `test_registration_rejects_non_boolean_truthy_pdp_consent`. Необязательный `marketing_consent` регистрации остаётся на коэрсии DRF — отмечено в `docs/architecture/11-security-performance.md`.

_Из раздела «Deferred from: code review of 41-9-consent-journal-text-version-and-source (2026-09-09)»_

- **Celery-задачи B2B-регистрации публикуются до фиксации транзакции и могут получить ID откатившегося пользователя.** `UserRegistrationSerializer.create()` вызывает три `.delay(user.id)` внутри внешнего `transaction.atomic()` из `UserRegistrationView.post`. Любая последующая ошибка, включая недоступный или повреждённый реестр текстов согласий, откатывает пользователя, но уже опубликованные задачи не откатываются. Дефект существовал до Story 41.9; исправление — ставить задачи через `transaction.on_commit()`. [`backend/apps/users/serializers.py:266-271`, `backend/apps/users/views/authentication.py:130-174`]
  **Перенесено 2026-09-24:** Исправлено: письма B2B-заявки ставятся через `transaction.on_commit` (`UserRegistrationSerializer.create`), откат регистрации их не публикует — тест `test_b2b_notification_tasks_are_not_queued_when_registration_rolls_back`.

_Из раздела «Deferred from: code review of 41-9-consent-journal-text-version-and-source (2026-09-09)»_

- **TOCTOU-гонка регистрации по email возвращает 500 одному из параллельных запросов.** `UserRegistrationSerializer.validate()` отдельно проверяет `User.objects.filter(email=...).exists()`, а затем `create()` вызывает `User.objects.create_user()`. Два одновременных запроса с одним email могут пройти предварительную проверку; второй упрётся в уникальность БД и получит необработанный `IntegrityError` вместо контролируемого ответа «Пользователь с таким email уже существует». Дефект существовал до Story 41.9; исправление требует перехватить конфликт уникальности на атомарной вставке, не полагаясь только на `exists()`. [`backend/apps/users/serializers.py:240-246,289-305`]
  **Перенесено 2026-09-24:** Исправлено: вставка пользователя идёт в savepoint, `IntegrityError` по занятому email превращается в 400 `{"email": [...]}`, иной конфликт уникальности пробрасывается — тесты `test_concurrent_registration_with_same_email_returns_400`, `test_integrity_error_not_about_email_is_not_masked`.

_Из раздела «Deferred from: code review of spec-1c-unregistered-role (2026-07-26)»_

- source_spec: `_bmad-output/implementation-artifacts/spec-1c-unregistered-role.md`
  summary: Гонка при одновременной регистрации — между чтением в `validate()` и записью в `create()` нет `select_for_update`, два параллельных запроса с одним email проходят проверку дубля.
  evidence: Pre-existing (тот же паттерн отмечен в отложенных пунктах spec-trainer-registration-inn). После отключения автопривязки последствие ослаблено: запись 1С больше не изменяется, конкурируют только вставки нового пользователя, где ловит `unique` на `email`.
  **Перенесено 2026-09-24:** Исправлено: вставка пользователя идёт в savepoint, `IntegrityError` по занятому email превращается в 400 `{"email": [...]}`, иной конфликт уникальности пробрасывается — тесты `test_concurrent_registration_with_same_email_returns_400`, `test_integrity_error_not_about_email_is_not_masked`.

_Из раздела «Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-11, Pass 5)»_

- **Atomic-wrapper расширил окно pre-existing Celery race** — `serializer.create()` ставит `send_admin_verification_email.delay` / `send_user_pending_email.delay` ВНУТРИ `transaction.atomic()` блока. Между .delay() и commit теперь два дополнительных `UserConsent` INSERT — окно для worker pickup до commit расширилось. Pre-existing tech debt, явно out of scope 35.2 (Dev Notes 477-479, Pass 1 defer #6, Pass 3 deferred-work entry). Решение: обернуть delay() в `transaction.on_commit(lambda: ...)` отдельной story. [backend/apps/users/serializers.py:113-125, backend/apps/users/views/authentication.py:143-166]
  **Перенесено 2026-09-24:** Исправлено: письма B2B-заявки ставятся через `transaction.on_commit` (`UserRegistrationSerializer.create`), откат регистрации их не публикует — тест `test_b2b_notification_tasks_are_not_queued_when_registration_rolls_back`.

_Из раздела «Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-11, Pass 3)»_

- **Race на duplicate email → HTTP 500 вместо 409** — `validate_email` делает `User.objects.filter(email=value).exists()` без блокировки; два concurrent POST с одним email — один проходит, второй ловит `IntegrityError` на unique constraint → API возвращает 500 (нет `except IntegrityError`), frontend `getValidationMessage` не понимает 500. Pre-existing, не введено 35.2. Решение: `try { user = create_user(...) } except IntegrityError: raise ValidationError({"email": [...]})` либо `select_for_update` на user-level. [backend/apps/users/views/authentication.py:115-163, serializers.py:62-66]
  **Перенесено 2026-09-24:** Исправлено: вставка пользователя идёт в savepoint, `IntegrityError` по занятому email превращается в 400 `{"email": [...]}`, иной конфликт уникальности пробрасывается — тесты `test_concurrent_registration_with_same_email_returns_400`, `test_integrity_error_not_about_email_is_not_masked`.

_Из раздела «Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-11, Pass 3)»_

- **Celery `.delay()` в `serializer.create()` без `transaction.on_commit`** — `send_admin_verification_email.delay(user.id)` и `send_user_pending_email.delay(user.id)` ставятся в очередь синхронно ВНУТРИ `transaction.atomic()`. При откате транзакции (например, ошибка `UserConsent.create(...)`) worker подберёт task с несуществующим `user.id` → `User.DoesNotExist` exception, или admin получит email о rolled-back пользователе. Pre-existing техдолг, явно out of scope 35.2 (см. Dev Notes line 477-479 + Pass 1 defer #6). Уже в `_bmad-output/planning-artifacts/tech-debt.md`. Решение: обернуть в `transaction.on_commit(lambda: send_admin_verification_email.delay(user.id))`. [backend/apps/users/serializers.py:113-125]
  **Перенесено 2026-09-24:** Исправлено: письма B2B-заявки ставятся через `transaction.on_commit` (`UserRegistrationSerializer.create`), откат регистрации их не публикует — тест `test_b2b_notification_tasks_are_not_queued_when_registration_rolls_back`.

_Из раздела «Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-10)»_

- **B2B email Celery tasks are queued before transaction commit**: `UserRegistrationSerializer.create()` still calls `send_admin_verification_email.delay()` / `send_user_pending_email.delay()` while `UserRegistrationView.post()` now wraps user + consent creation in `transaction.atomic()`. If later consent insert fails, the transaction rolls back but tasks may already be queued. Story 35.2 explicitly marked moving these calls to `transaction.on_commit()` as out of scope. [backend/apps/users/serializers.py:113]
  **Перенесено 2026-09-24:** Исправлено: письма B2B-заявки ставятся через `transaction.on_commit` (`UserRegistrationSerializer.create`), откат регистрации их не публикует — тест `test_b2b_notification_tasks_are_not_queued_when_registration_rolls_back`.

_Из раздела «Deferred from: code review of 35-2-consent-checkboxes-in-registration-forms (2026-05-10)»_

- **Pass 7 уточнение по Celery race**: Story 35.2 расширила окно pre-existing race именно за счёт Pass 1 `transaction.atomic()` around user + consent creation: после `.delay()` внутри `serializer.create()` до final COMMIT теперь выполняются 1-2 `UserConsent.objects.create()`. Если consent INSERT упадёт, worker может получить задачу на откатанного user. Исправление остаётся отдельной backend-story: перенос email `.delay()` в `transaction.on_commit()` и проверка registration email tests. [backend/apps/users/views/authentication.py:143-166, backend/apps/users/serializers.py:113-125]
  **Перенесено 2026-09-24:** Исправлено: письма B2B-заявки ставятся через `transaction.on_commit` (`UserRegistrationSerializer.create`), откат регистрации их не публикует — тест `test_b2b_notification_tasks_are_not_queued_when_registration_rolls_back`.

## Deferred from: выкат стори 41.7 (2026-09-08)

> **Перенесено 2026-09-24:** Закрыто. Исправление влито PR #249 и выкачено релизом `ab673086` (24.09.2026 03:17 UTC). Проверено на проде: у backend `FRONTEND_INTERNAL_URL=http://frontend:3000` и `REVALIDATE_SECRET` (64 символа, как у frontend); вызов `_revalidate_nextjs('/privacy-policy')` из Django shell дал в логе `Next.js revalidation triggered for /privacy-policy` (при не-2xx функция теперь пишет WARNING), следующий запрос страницы — `x-nextjs-cache: MISS`, то есть ISR-кэш сброшен. Путь «сохранение в админке → сигнал → `_revalidate_nextjs`» покрыт `apps/pages/tests.py::RevalidateNextjsTest`. Ручная ревалидация через `x-prerender-revalidate` больше не нужна; рецепт остаётся в памяти агента.

- **Автоматическая ревалидация ISR Next.js на проде не работает вообще: `FRONTEND_INTERNAL_URL` и `REVALIDATE_SECRET` не объявлены в `docker-compose.prod.yml`.** Найдено при внесении номера `26-22-003980` в текст политики через админку прода: `GET /api/v1/pages/privacy-policy/` показал номер сразу, а `GET /privacy-policy` — нет. Замер на проде: `FRONTEND_INTERNAL_URL = ''`, `REVALIDATE_SECRET` не задан. `_revalidate_nextjs` выходит по guard'у `if not frontend_url or not secret: return` — **до** строки логирования, поэтому в логах нет ни успеха, ни ошибки, и сбой ничем себя не проявляет. Django-часть инвалидации при этом отрабатывает штатно (ключ `page_detail_<slug>` удаляется, версия списка растёт) — именно поэтому API обновляется, а страница нет, и дефект выглядит как «залипший Next», а не как отсутствующая конфигурация.

  **Следствие:** любая правка CMS-текста на проде (`privacy-policy`, `oferta`, `requisites` и будущие страницы) не видна пользователям до ручной ревалидации через `x-prerender-revalidate`. Утверждение плана выката стори 41.7 «Сохранение записи само сбрасывает кэши… Отдельных действий не требуется» на текущей конфигурации прода **неверно** — оно описывает dev-окружение, где обе переменные объявлены (`docker/docker-compose.yml:77-78,122`).

  **Исправление:** добавить в `docker/docker-compose.prod.yml` `FRONTEND_INTERNAL_URL=http://frontend:3000` и `REVALIDATE_SECRET=${REVALIDATE_SECRET}` в окружение сервиса `backend` и `REVALIDATE_SECRET=${REVALIDATE_SECRET}` — сервису `frontend` (route `/api/revalidate` сверяет заголовок именно с `process.env.REVALIDATE_SECRET`), завести значение в `.env.prod` и в `.env.prod.example`. Затем проверить сквозняком: сохранить страницу в админке → страница на сайте обновилась без ручных действий. В объём стори 41.7 не входило (AC6 запрещает трогать бэкенд и конфигурацию). [`docker/docker-compose.prod.yml:9-95`, `backend/apps/pages/signals.py:69-90`, `backend/freesport/settings/base.py:644-645`, `frontend/src/app/api/revalidate/route.ts`]

  **ИСПРАВЛЕНО В КОДЕ 2026-09-23, ветка `fix/prod-isr-revalidation`; сквозная проверка на проде — после релиза.** Замер прода 23.09 уточнил картину: `REVALIDATE_SECRET` в `.env.prod` уже был, и frontend его видел (64 символа). Не хватало только объявления обеих переменных у сервиса `backend` — они добавлены в `docker-compose.prod.yml`, правка сервера не нужна. Заодно убраны оба источника тишины: `_revalidate_nextjs` пишет WARNING при отсутствии настроек и при не-2xx ответе (раньше ответ 401 логировался как успех), а маршрут `/api/revalidate` при пустом секрете на сервере отвечает 401 — прежний код пропускал пустой заголовок при пустой переменной. Тесты: `apps/pages/tests.py::RevalidateNextjsTest` (3 из 5 падают на старом коде), `frontend/src/app/api/revalidate/__tests__/route.test.ts` (1 из 6 падает на старом коде). Проверка после релиза: сохранить страницу в админке → в логе backend `Next.js revalidation triggered for /<slug>` → страница на сайте обновилась без `x-prerender-revalidate`.

- **Обходной путь на сегодня — ручная ревалидация ISR.** Токен и вызов (проверено 2026-09-08, ответ `x-nextjs-cache: REVALIDATED`):

  ```bash
  ssh root@5.35.124.149 'docker exec freesport-frontend node -e "console.log(require(\"/app/.next/prerender-manifest.json\").preview.previewModeId)"'
  ssh root@5.35.124.149 'docker exec freesport-frontend sh -c "wget -q -S -O /dev/null --header=\"x-prerender-revalidate: <TOKEN>\" http://localhost:3000/<путь> 2>&1 | grep x-nextjs-cache"'
  ```

  Токен меняется при каждой пересборке контейнера — брать заново, не сохранять.

## Deferred from: пропажа блока брендов на главной после деплоя (2026-09-07)

> **Перенесено 2026-09-24:** Закрыто. Исправление влито PR #253 и выкачено релизом `617d216d` (24.09.2026 14:58 UTC). Проверено на проде через 6 секунд после выката: в `/home` все 6 брендов (`boybo`, `cosmoride`, `eclectica`, `elous`, `espado`, `ingame`) при `x-nextjs-cache: HIT`, то есть бренды вморожены в пререндер на этапе сборки, а не подтянуты ревалидацией. Контрольный замер: предыдущий релиз `a82c5592` (14:47 UTC, без исправления) на той же команде отдал пустой список.

- source_spec: none
  summary: **После каждой пересборки frontend блок логотипов брендов на `/home` исчезает до первой ISR-ревалидации (до часа).** На этапе `npm run build` внутри `docker build` переменной `INTERNAL_API_URL` нет — она задана только в `environment:` компоуза, то есть в рантайме. Поэтому `api-client.ts:24-27` уходит на заглушку `http://localhost:8001/api/v1`, где в билд-контейнере никто не слушает. Запрос падает, `catch` в `frontend/src/app/(blue)/home/page.tsx:21-25` глушит ошибку и отдаёт `featuredBrands = []`, а `HomePage.tsx:59` при пустом массиве блок не рендерит — и это вмораживается в пререндер `home.html`. Замер в рантайм-контейнере: `http://backend:8000/api/v1/brands/featured/` → OK 599 байт, `http://localhost:8001/api/v1/brands/featured/` → `ERR fetch failed`. Тайминги деплоя 2026-09-07: билд `home.html` 05:30:10 UTC, старт контейнера 05:30:38, `revalidate = 3600` → самопочинка только к 06:30.
  evidence: Вскрыто по жалобе «после деплоя раздел с логотипами брендов совсем пропал». Симптом снят вручную форсированной ревалидацией (`x-prerender-revalidate` → `x-nextjs-cache: REVALIDATED`), бренды вернулись в пейлоад. Владелец решил причину пока не чинить.

  **Варианты решения, когда дойдут руки:** (а) в `api-client.ts` при отсутствии `INTERNAL_API_URL` использовать `NEXT_PUBLIC_API_URL` (публичный адрес, на билде доступен) вместо заглушки `localhost:8001` — правит корень, но трогает общий клиент и влияет на все SSR-запросы; (б) добавить в навык `production-update` шаг форсированной ревалидации `/home` после подъёма контейнера — безопасно, но лечит симптом и только для одной страницы; (в) вынести получение featured-брендов из пререндера (клиентская загрузка или `Suspense` с динамическим сегментом).

  **Диагностика на будущее:** блок отсутствует ⇒ `featuredBrands` пуст на момент пререндера. Проверять не HTML (`BrandsBlock` клиентский, его разметки нет ни в `home.html`, ни в `home.rsc`), а наличие slug'ов брендов в пейлоаде: `curl -s https://optisport.ru/home | grep -o '\\"slug\\":\\"[a-z0-9-]*\\"' | sort -u` — должно быть 6 брендов.

  **ИСПРАВЛЕНО В КОДЕ 2026-09-24, ветка `fix/home-brands-build-prerender`, вариант (а); проверка на проде — после релиза.** Последним звеном серверной цепочки в `api-client.ts` стал `API_URL_PUBLIC`, а не заглушка `localhost:8001`: `INTERNAL_API_URL` → `NEXT_PUBLIC_API_URL_INTERNAL` → `NEXT_PUBLIC_API_URL`. Та же цепочка уже работала в `sitemap.ts` и `catalog/page.tsx`. В рантайме прода `INTERNAL_API_URL` задан, поэтому SSR по-прежнему идёт во внутреннюю сеть. Меняется только этап `next build`: образ собирается в CI (`deploy.yml`, build-arg `NEXT_PUBLIC_API_URL=https://optisport.ru/api/v1` из `vars`), и пререндер берёт бренды с публичного API прода. Проверено локальной сборкой в тех же условиях (`NEXT_PUBLIC_API_URL` задан, `INTERNAL_API_URL` нет): в `.next/server/app/home.rsc` все 6 брендов (`boybo`, `cosmoride`, `eclectica`, `elous`, `espado`, `ingame`), ошибок загрузки в логе сборки нет. Тест `frontend/src/services/__tests__/api-client-base-url.test.ts`: 1 из 3 падает на старом коде. Остаточный риск: если прод-API во время сборки недоступен, пустой список по-прежнему вмораживается, до часа. Проверка после релиза: сразу после выката выполнить команду диагностики выше, должно быть 6 брендов.

## Deferred from: code review of 41-6-unique-metadata-og-image-jsonld (2026-09-06)

- **Product JSON-LD допускает закрытие script-тега данными товара и XSS при SSR.** `product.name` и `product.description` сериализуются через сырой `JSON.stringify` и вставляются в `<script type="application/ld+json">` через `dangerouslySetInnerHTML`. Значение с `</script>` завершает элемент до конца JSON и превращает остаток в HTML. Дефект присутствует в baseline Story 41.6 и не внесён её changeset. Исправление: сериализованный JSON перед вставкой должен заменять каждый `<` на литеральную JSON escape-последовательность `\\u003c`, по уже безопасному паттерну `SiteJsonLd.tsx`, с регрессионным тестом на данные товара, содержащие `</script>`. [`frontend/src/components/product/ProductPageClient.tsx:79-120`]
  **Перенесено 2026-09-24:** Исправлено в ветке `fix/jsonld-xss-sessid-traversal`. Сериализованный JSON разметки `Product` перед вставкой проходит `.replaceAll('<', '\\u003c')` по образцу `SiteJsonLd.tsx`. Регрессионный тест `frontend/src/components/product/__tests__/ProductPageClient.jsonld.test.tsx` рендерит компонент через `renderToStaticMarkup` с `</script><img src=x onerror=alert(1)>` в названии и описании. На старом коде SSR-вывод обрывался на `"name":"Мяч "`, то есть дефект воспроизводился; на новом JSON разбирается целиком и возвращает исходные строки.
  **Выкачено 2026-09-24** релизом `b266216f` (`deploy.yml` завершился в 17:00 UTC). На проде через `curl` не проверяется: `AuthProvider` отдаёт в серверном HTML спиннер, и разметка `Product` появляется только после гидрации (см. запись о спиннере `AuthProvider` в `deferred-work.md`). По той же причине вектор на проде фактически не срабатывал: в серверном HTML разметки товара нет, а на клиенте React вставляет её через `innerHTML` элемента `<script>`, где `</script>` остаётся текстом. Экранирование становится несущим, как только SSR публичных страниц починят.

## Deferred from: code review of onec-exchange-dir-isolation (2026-08-28)

- **`mode=file` допускает path traversal через `sessid` до вызова нового валидатора.** `FileStreamService` напрямую строит `TEMP_DIR / session_id`, поэтому `../outside` может записать файл вне временного корня. Произвольная запись существовала до текущего diff; исправить отдельной security-задачей с общей валидацией на входе протокола. [`backend/apps/integrations/onec_exchange/file_service.py:139-160`]
  **Перенесено 2026-09-24:** Исправлено в ветке `fix/jsonld-xss-sessid-traversal`. `FileStreamService.__init__` пропускает `sessid` через `validate_session_segment` из `routing_service.py`, поэтому проверку получили все четыре входа: `mode=init`, `mode=file`, `mode=import`/`complete` через оркестратор и распаковка ZIP в `products/tasks.py`. `handle_file_upload` дополнительно проверяет `sessid` до записи и отвечает `failure\nInvalid session`, а не «Internal error» с трейсбеком. Тесты в `backend/tests/integration/test_1c_file_upload.py` (`test_upload_sessid_traversal_rejected`, `test_rejects_unsafe_session_id`): 9 из 9 падают на старом коде.
  **Выкачено 2026-09-24** релизом `b266216f` (`deploy.yml` завершился в 17:00 UTC). Штатный `sessid` 1С (ключ Django-сессии) проходит валидатор без изменений. Контрольная точка — ближайший обмен 1С после релиза: в логе backend не должно быть `Upload rejected: unsafe sessid`.
