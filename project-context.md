---
project_name: FREESPORT
user_name: Alex
date: 2026-05-09
sections_completed:
  - environment
  - forbidden_actions
  - domain_invariants
  - testing
  - gitnexus
  - language
  - frontend
  - references
status: complete
optimized_for_llm: true
---

# Project Context for AI Agents — FREESPORT

> Только то, что НЕ выводится из кодовой базы. Технологический стек смотри в `frontend/package.json` и `backend/requirements.txt`. Архитектура — в `_bmad-output/planning-artifacts/architecture.md`. Полный свод правил — в `AGENTS.md` / `CLAUDE.md` (этот файл — их выжимка для context window).

---

## 1. Среда выполнения

- **OS / shell**: Windows + PowerShell. Chain команд только через `;`, **не** через `&&`.
- **Backend работает на порту 8001** (не 8000 — избежание конфликтов).
- **Backend (pytest, Django, миграции, линтеры) — стандартный путь через Docker** (нужны PostgreSQL и Redis). Локальный `pytest` допустим **только** при активированном venv и запущенной базе в Docker:
  ```powershell
  .\backend\venv\Scripts\Activate.ps1
  pytest <путь_к_тесту>
  ```
  Стандарт — `make test`, `make test-unit`.
- **После `pip install`** в backend — обязательно обновить `backend/requirements.txt` через `pip freeze`.
- **Frontend в Docker**: после правки `frontend/src/` обязательно
  ```powershell
  docker compose --env-file .env -f docker/docker-compose.yml restart frontend
  ```
  При изменении зависимостей/конфига — `up -d --build frontend`.
- **`.env`-файлы**: `.env` (root, для всех compose-сервисов), `.env.test` (root) и `backend/.env.test` (тестовое окружение бэкенда), `.env.prod` (прод, не в репозитории; шаблон — `.env.prod.example`). Не путать, не коммитить.
- **Docker compose**: всегда указывать `--env-file .env -f docker/<compose-file>` (см. `docker/`).
- **Nginx после правки конфига** — `docker compose exec nginx nginx -s reload`, не restart контейнера.

## 2. Запреты (необратимые действия)

- **НЕ** выполнять `git push production main` (никогда, даже если просят). Публичный репозиторий FREESPORT-B2B обновляется только через GitHub Actions workflow `sync-to-public.yml`. Прямой push утечёт `.env`, `.mcp.json`, `AGENTS.md`, скрипты и историю коммитов.
- На production-сервере **не** использовать `git pull`. Только:
  ```bash
  git fetch origin main; git reset --hard origin/main
  ```
- После рестарта backend на проде (`docker compose restart backend celery celery-beat`) **обязательно** дополнительный `docker compose restart nginx`, иначе nginx отдаёт 502 на upstream.
- **На проде НИКОГДА** `docker compose down -v` — снесёт volumes с `media/` и `static/` (пользовательские загрузки).
- **НЕ** переименовывать символы через find-and-replace. Команды `rename` в GitNexus CLI нет — собрать все места через `impact`/`context`/`cypher` и править точечно (см. §5).

## 3. Доменные инварианты

- **`onec_id`** — внешний идентификатор 1С (CommerceML), `unique=True`, **immutable**. PK Django остаётся стандартный `id`. Уникален в рамках типа сущности (Product.onec_id и Brand.onec_id могут совпадать) — не строить cross-entity lookups по нему.
- **`OrderItem` хранит snapshot** цены, названия и атрибутов товара на момент заказа. Не заменять snapshot полями FK на текущий `Product` — сломает исторические заказы при изменении цен/SKU.
- **Role-based pricing**: 6 ценовых полей в `Product` — `retail_price`, `opt1_price`, `opt2_price`, `opt3_price`, `trainer_price`, `federation_price` (всего 7 ролей, но роль `admin` собственной цены не имеет → 6 полей).
  - Маппинг роли → поле: `retail`→`retail_price`, `wholesale_level1/2/3`→`opt1/2/3_price`, `trainer`→`trainer_price`, `federation_rep`→`federation_price`.
  - Сериализаторы отдают цену **по роли `request.user`**, не сырое поле. Гостям — `retail_price`.
  - Инфо-цены B2B (`RRP`, `MSRP`) — отдельные поля, не используются для фактических расчётов.
- **Номер заказа** — канонический формат `CCCCCYYNNN` (10 цифр: 5-значный customer_code + `YY` + `NNN`), хранится только в полном виде, **immutable** после создания. UI мастер-заказа: `CCCC-YYNNN` — **последние 4** цифры customer_code (первая отбрасывается) + `YYNNN`. Субзаказы: `CCCCCYYNNNS` (UI: `CCCCC-YYNNN-S`) — здесь customer_code показывается **целиком (5 цифр)**, `S` ≥ 1 и может быть многозначным. Асимметрия 4 vs 5 цифр между мастером и субзаказом **намеренная** (см. `format_order_number` в `apps/orders/services/order_numbering.py`) — не «исправлять». Пример: customer_code `12345`, год `2026`, счётчик `7` → хранится `1234526007`, UI мастера `2345-26007`, UI субзаказа `12345-26007-1`. Поиск в админке принимает оба формата и нормализует к каноническому.
- **Гости не оформляют заказы** — checkout требует JWT-аутентификации.
- **DRF defaults** (канонические значения — в `backend/freesport/settings/base.py`, точные классы не дублировать здесь):
  - Аутентификация по умолчанию — JWT с проверкой Redis-blacklist (+ session auth).
  - `DEFAULT_PERMISSION_CLASSES` = `AllowAny` — осознанное решение для публичных endpoints. **Защищённые view ОБЯЗАНЫ явно указывать** `permission_classes = [IsAuthenticated]`. Не полагаться на default.
- **B2B verification**: оптовые цены (`opt1/2/3_price`) и B2B-функции доступны **только верифицированным** пользователям с ролью wholesale/trainer/federation_rep. Неверифицированный B2B видит retail-цены. Проверять флаг верификации в сериализаторах/permissions.
- **Master/sub-order email**: customer- и admin-уведомления ставятся в очередь **только для `is_master=True`** (guard в `apps/orders/signals.py`). Items для отображения берутся из `sub_orders` через `_get_order_display_items` — не из прямых `OrderItem` мастера.
- **Критические операции** (генерация номера заказа, decrement остатков, создание `Order` + `OrderItem` snapshot) — обязательно в `transaction.atomic()` с `select_for_update()`. Не разносить по двум вызовам.
- **Celery-задачи идемпотентны** — могут ретраиться при сбоях 1С/сети. Не предполагать «выполнится ровно один раз».

## 4. Тестирование

- **Pytest markers проставляются автоматически по каталогу** — руками ставить не нужно. Хук `pytest_collection_modifyitems` в `backend/conftest.py` размечает каждый собранный тест по самому глубокому каталогу-категории в пути (работает на любой глубине, и в `tests/`, и внутри `apps/`):
  - `unit/` → `unit`; `integration/`, `functional/`, `regression/` → `integration`; `performance/` → `performance`.
  - Каталога-категории нет → умолчание: всё под `apps/` — `unit`. Для `tests/` умолчания нет: новый каталог там обрывает сбор с `UsageError`. Асимметрия осознанная (см. `backend/docs/testing-standards.md`).
  - `unit` означает «модульный тест приложения», **не** «без БД»: тест с `django_db` внутри `apps/` штатно получает `unit`.
  **Явный маркер в файле переопределяет автоматический** и задаёт свойство теста, а не каталог: перф-тест в `tests/integration/` достаточно пометить `@pytest.mark.performance`, переносить файл не нужно. `@pytest.mark.data_dependent` и `@pytest.mark.slow` ортогональны и ставятся вручную; `slow` — рычаг вывода таймингозависимого теста из PR-гейта.
  Тест вне дерева `backend/` разметить нечем — хук его пропускает, но выдаёт `UnmarkedTestWarning` со списком: молча выпасть из прогонов по `-m` он не должен.
- **Где что исполняется:** `backend-ci.yml` — быстрый unit-гейт (`not integration and not data_dependent and not performance and not slow`), покрытие не считает; `main.yml` — весь остальной набор (`not performance and not slow`) на каждом push/PR в `main`/`develop`, ловит регрессии интеграционных тестов, единственный гоняет `data_dependent` **и считает покрытие**; `performance-tests.yml` — `performance or slow` по расписанию (nightly) и вручную.
- **Покрытие меряет `main.yml`, порог 75** (`--cov=apps --cov=freesport`, тесты/миграции исключены через `[tool.coverage.run] omit` в `backend/pyproject.toml`). Фактическое покрытие продакшен-кода — 76,4 % (замер 2026-08-06). **Не возвращать подсчёт в быстрый гейт:** он запускает ~1900 тестов из ~3000 и даёт 62,5 % на том же коде, из-за чего порог ломался от каждой стори с интеграционными тестами.
- **Команды запуска** (через Docker):
  ```bash
  make test                 # все тесты
  make test-unit            # только unit
  make test-integration     # только integration
  make test-performance     # только перф-тесты
  make test-slow            # только медленные (маркер slow)
  # Прямой запуск конкретного теста в test-контейнере (--env-file не нужен:
  # в docker-compose.test.yml нет подстановок переменных, всё зашито литералами):
  cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest <путь>
  ```
- **API-контракт sync**: после правки serializer/view → обновить `docs/api/openapi.yaml` и регенерировать типы фронта `npm run generate:types`. Рассинхрон ломает TypeScript-сборку frontend.
- **Frontend**: Vitest (`npm run test`, не Jest), E2E — Playwright (`npm run test:e2e`). API-моки — MSW (`__mocks__/handlers.ts`). A11y — axe-core / vitest-axe.
- **Миграции тестируются на PostgreSQL в Docker**, не на локальном SQLite (расхождения JSONB, partitioning, constraints).
- **Покрытие**: общее ≥ 70%, критические модули (orders, products, integrations) ≥ 90%.
- **Тесты импорта 1С** — только реальные XML из `data/import_1c/` (`contragents/`, `goods/`, `offers/`, `prices/`, `rests/`, `units/`, `storages/`, `priceLists/`). Не генерировать синтетические XML.

## 5. GitNexus-дисциплина (только CLI)

**MCP-сервер GitNexus в проекте не подключён** — `.mcp.json` отсутствует, инструментов `gitnexus_*` нет. Всё выполняется через Bash.

- **Перед редактированием** функции/класса/метода: `npx gitnexus impact <symbol> --direction upstream`. Сообщить blast radius (callers, processes, risk) пользователю. При HIGH/CRITICAL — предупредить и подтвердить.
- **Перед коммитом**: `npx gitnexus detect-changes --scope all` — убедиться, что затронуты только ожидаемые символы и flows.
- **Поиск/исследование** — `npx gitnexus query "<concept>"` вместо grep по большой кодовой базе.
- **Контекст символа** (callers + callees + processes) — `npx gitnexus context <symbol>`; `--file <path>` снимает неоднозначность одинаковых имён.
- **Rename** — команды `rename` в CLI нет. Собрать все места через `impact` и `context`, затем править точечно; текстовая замена по-прежнему запрещена.
- **Свежесть индекса**: `npx gitnexus status`. При `stale` — попросить пользователя выполнить `! npx gitnexus analyze`. Ответ `{"error": "Symbol ... not found"}` на существующий код означает устаревший индекс.
- `impact`, `context`, `query`, `cypher` печатают JSON; `status` и `detect-changes` — текст.

## 6. Язык

- **Общение с пользователем и вся документация — на русском.**
- **Комментарии и docstrings в новом коде — на русском** (соответствует существующему стилю проекта). Не «исправлять» русские комментарии на английский.

## 7. Frontend-специфика (Next.js 15 App Router / React 19)

- **Server vs Client Components** — по умолчанию все компоненты Server. `'use client'` **обязателен** в любом файле с `useState`/`useEffect`/event handlers/Zustand. Без директивы — runtime-error при гидрации.
- **HTTP только через общий `api-client`** (`frontend/src/services/api-client.ts`, axios + JWT interceptor + auto-refresh). Не использовать голый `fetch`/`axios` в компонентах/сервисах.
- **Изображения** — `next/image` (`<Image>`), не `<img>`. Domains прописаны в `next.config.js`. Для backend-URL — обязательно `normalizeImageUrl()` (поддержка относительных и absolute paths).
- **`fetch` в Server Components кэшируется по умолчанию в Next 15** — для динамических данных явно `{ cache: 'no-store' }` или `revalidate: N`.
- **Деплой-консистентность**: ошибка `Failed to find Server Action` в проде = несовпадение `BUILD_ID` между prerendered HTML и рабочей сборкой. Деплой frontend — только через полный rebuild контейнера (`up -d --build frontend`), не копировать часть `.next/` поверх старого билда.
- **React 19 паттерны** — `ref` передаётся как обычный prop (без `forwardRef`), `use()` hook вместо `Suspense + fetch`-обёрток. Не писать React 18 паттерны.
- **Zustand store — только в Client Components**. Persist middleware требует `skipHydration` или динамического импорта, иначе hydration mismatch.

## 8. Ссылки

- **Авторитетные правила:** `AGENTS.md`, `CLAUDE.md` (этот файл — их выжимка для context window).
- **Master index docs:** `docs/index.md`
- **Architecture (история изменений, модели, API):** `docs/architecture/index.md`
- **Architecture (BMAD):** `_bmad-output/planning-artifacts/architecture.md`
- **PRD:** `_bmad-output/planning-artifacts/refined-prd.md`

_При сомнениях — выбирать более ограничительную опцию. Обновлять файл при смене стека, доменных инвариантов или deploy-протокола._

_Last Updated: 2026-05-22_
