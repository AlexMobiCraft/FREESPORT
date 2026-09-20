# CLAUDE.md

Всегда отвечай на русском языке.

Руководство по работе с кодом в репозитории FREESPORT.

## Обзор проекта

**FREESPORT** — API-First E-commerce платформа для B2B/B2C продаж спортивных товаров. Monorepo: Django REST API backend + Next.js frontend.

### КРИТИЧНЫЕ правила проекта

1. **Только PostgreSQL.** Другие СУБД НЕ поддерживаются — проект использует JSONB (спецификации товаров), партиционирование, полнотекстовый поиск.
2. **Только Docker.** Вся разработка, тестирование и деплой — через Docker Compose. Локальная установка БД не поддерживается.
3. **Django backend работает на порту 8001** (не 8000 — для избежания конфликтов).
4. **Файлы docker-compose\*.yml находятся в `docker/`**, не в корне репозитория.

## Неочевидное в коде

- `orders/` — Email-уведомления (customer + admin) ставятся в очередь **только для `is_master=True`** (`signals.py` guard); items для отображения агрегируются из `sub_orders` через helper `_get_order_display_items`.
- `data/import_1c/` — РЕАЛЬНЫЕ XML-выгрузки из 1С, используются в тестах импорта (см. раздел «Интеграция с 1С»).

## Команды разработки

### Docker (основной способ)

```bash
# Запуск всех сервисов (db, redis, backend, frontend, nginx, celery, celery-beat)
docker compose --env-file .env -f docker/docker-compose.yml up -d --build

# Остановка
docker compose --env-file .env -f docker/docker-compose.yml down

# Production
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d
```

### Тестирование (ТОЛЬКО через Docker с PostgreSQL)

Таргеты — в `Makefile` (цели `test`, `test-unit`, `test-integration`, `test-performance`, `test-slow`, `test-fast`). Конкретный backend-тест:

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/test_product_variant_models.py::TestProductVariant::test_create_variant_with_valid_data
```

**`--env-file` тестовому compose не передаётся:** файла `docker/.env` нет, и с ним команда падает на `couldn't find env file`. Он и не нужен — в `docker-compose.test.yml` нет подстановок переменных. **`run --rm`, а не `exec`:** у сервиса `backend` команда по умолчанию `pytest`, контейнер отрабатывает и выходит, поэтому после test-таргетов подключаться `exec` не к чему.

**Покрытие:** общее ≥ 70%, критические модули ≥ 90%. Порог в CI и то, какой прогон его считает, — в `backend/docs/testing-standards.md`.

### Python: виртуальное окружение

- Всегда проверяй индикатор `(venv)` перед запуском `python`/`pip`.
- После `pip install` **обязательно** обновляй `requirements.txt`: `pip freeze > requirements.txt`.

## Интеграция с 1С (CommerceML 3.1)

### Реальные данные для тестов — КРИТИЧНО

- ❌ **НЕ создавай** синтетические XML для тестов импорта 1С.
- ✅ **Всегда используй** файлы из `data/import_1c/`:
  - `contragents/` — контрагенты (7 файлов, ООО/ИП/физлица, edge cases)
  - `goods/` — товары + `import_files/` изображения
  - `offers/`, `prices/`, `rests/`, `units/`, `storages/`, `priceLists/`

### Команды импорта

Команды импорта товаров и контрагентов — в навыке `import-1c` (`.claude/skills/import-1c/SKILL.md`).

## Внешние интеграции

- **1С (ERP):** двусторонний обмен (товары, заказы, остатки) через Celery, CommerceML 3.1 (см. `docs/integrations/`)
- **Платежи:** YuKassa
- **Доставка:** CDEK, Boxberry (см. `docs/integrations/`)

## Git Workflow

- `main` — production (прямой push, без PR и required-чеков; force-push запрещён)
- `develop` — основная ветка разработки (защищена, base для PR, 5 required-чеков)
- `feature/*` — новые функции
- `hotfix/*` — критические исправления
- Синк `develop` → `main`: `git push origin origin/develop:refs/heads/main` (fast-forward, только по команде владельца). **Этот push и есть релиз:** он запускает `deploy.yml` (сборка образов → approval на environment `production` → SSH-деплой). Тестов на push нет ни в `develop`, ни в `main` — тот же SHA уже зелёный на PR.
- Мёрдж PR **только merge commit**, предпочтительно на автомёрдже: `gh pr merge N --auto --merge` — сольётся сам по зелёным чекам, head-ветка удалится автоматически. Squash/rebase разводят историю и ломают fast-forward синк (отключены в настройках репозитория).
- Откат релиза: `gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>` — без пересборки и тестов. Подробности и откат самой схемы — `.windsurf/rules/git-sync-workflow.md`

## Документация проекта

Подробности ищи в `docs/`:

- `docs/index.md` — главная документации
- `_bmad-output/planning-artifacts/refined-prd.md` — Product Requirements (PRD)
- `docs/architecture/index.md` — архитектура системы
- `docs/integrations/1c/import-process.md` — архитектура импорта 1С
- `docs/api/openapi.yaml` — OpenAPI спецификация
- `docs/api/views-documentation.md` — документация API endpoints
- `docs/stories/epic-*/` — user stories по эпикам (epic-1 … epic-26)
- `docs/decisions/` — архитектурные решения
- `docs/guides/` — руководства
- `docs/qa/` — тестирование и QA
- `docs/integrations/` — интеграции (1С,CDEK, YuKassa и др.)
- `backend/docs/testing-standards.md` — стандарты тестирования
- API Swagger UI: `/api/schema/swagger/` (на dev сервере)

## GitNexus — Code Intelligence (CLI)

> **Авторитетный источник правил GitNexus — этот раздел.**
> MCP-сервер `gitnexus` отключён намеренно: его команда `npx -y gitnexus@latest mcp` падает с
> `npm error Invalid Version`, инструменты `gitnexus_*` в сессии не появляются. Всё — через Bash.
> Переиндексация — **только** `npx gitnexus analyze --skip-agents-md`: без флага `analyze` допишет в конец файла
> блок `<!-- gitnexus:start -->` с MCP-инструкциями, противоречащими этому разделу. Появился — удали его.

Проект проиндексирован GitNexus как **FREESPORT**. Используй CLI, чтобы понимать код,
оценивать последствия правок и безопасно навигировать.

> Если `npx gitnexus status` показывает `stale` — попроси пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.

### Обязательно

- **Перед изменением любого символа** (функции, класса, метода) — `npx gitnexus impact <symbol> --direction upstream`;
  сообщи пользователю blast radius: прямые вызывающие, затронутые процессы, уровень риска.
- **Перед коммитом** — `npx gitnexus detect-changes --scope all`: убедись, что затронуты только ожидаемые символы и потоки.
- **Предупреди пользователя**, если impact вернул `"risk": "HIGH"` или `"CRITICAL"`, — до внесения правок.
- **Для исследования незнакомого кода** — `npx gitnexus query "<концепция>"` вместо grep по всей базе.
- **Полный контекст символа** (вызывающие, вызываемые, процессы) — `npx gitnexus context <symbol>`.

### Запрещено

- НЕ редактировать функцию/класс/метод, не выполнив `impact`.
- НЕ игнорировать риск HIGH или CRITICAL.
- НЕ переименовывать символы через find-and-replace. Команды `rename` в CLI нет:
  собери все места через `impact` и `context`, затем правь точечно и осознанно.
- НЕ коммитить без `detect-changes`.
- НЕ вызывать инструменты `gitnexus_*` — MCP-сервер отключён, вызов гарантированно провалится.

### Команды

| Задача | Команда |
|---|---|
| Статус и свежесть индекса | `npx gitnexus status` |
| Переиндексация | `npx gitnexus analyze --skip-agents-md` |
| Blast radius | `npx gitnexus impact <symbol> [--direction upstream\|downstream] [--depth N] [--include-tests]` |
| Контекст символа | `npx gitnexus context <symbol> [--file <path>] [--content]` |
| Поиск потоков выполнения | `npx gitnexus query "<концепция>" [--limit N] [--goal <text>]` |
| Символы, затронутые изменениями | `npx gitnexus detect-changes [--scope unstaged\|staged\|all\|compare] [--base-ref <ref>]` |
| Произвольный запрос к графу | `npx gitnexus cypher "<query>"` |

Вызывай без тега версии: `npx -y gitnexus@latest ...` падает на резолве `@latest`.
**Индексов с именем FREESPORT два** (второй — `C:\Users\1\DEV\FREESPORT-pr117`): `impact`, `context`, `query`, `cypher`, `detect-changes` без `-r "C:\Users\1\DEV\FREESPORT"` падают на «Multiple repositories indexed». `-r FREESPORT` молча берёт один из двух индексов (сейчас основной, но это зависит от реестра) — всегда передавай путь.
`impact`, `context`, `query`, `cypher` печатают JSON; `status` и `detect-changes` — текст.

### Ограничения CLI

- Команды `rename` нет — переименование только вручную по списку из `impact`/`context`.
- MCP-ресурсов (`gitnexus://repo/...`) нет; их заменяют `query`, `context` и `cypher`.
- `npx gitnexus wiki` требует LLM-провайдер и API-ключ — это не локальная бесплатная команда.
- Символы, добавленные после последней индексации, не находятся: `context` вернёт
  `{"error": "Symbol ... not found"}`. Это признак устаревшего индекса, а не отсутствия кода.
- `analyze` при каждом запуске (и с `--skip-agents-md` тоже) перезаписывает `.claude/skills/gitnexus/` своими MCP-шаблонами — флага, чтобы это отключить, нет. Каталог в `.gitignore`, не используй его; рабочие CLI-версии skills — `.claude/skills/gitnexus-*/`.

### Skill-файлы

| Задача | Файл |
|---|---|
| Понять архитектуру / «Как работает X?» | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / «Что сломается, если поменять X?» | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Отладка / «Почему X падает?» | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Переименование и рефакторинг | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Справочник по командам и схеме графа | `.claude/skills/gitnexus-guide/SKILL.md` |
| Индекс, статус, очистка, wiki | `.claude/skills/gitnexus-cli/SKILL.md` |
