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

Таргеты — в `Makefile`. Конкретный backend-тест:

```bash
docker compose --env-file .env -f docker/docker-compose.test.yml exec backend \
  pytest -xvs apps/products/tests/test_models.py::TestProductModel::test_create_product
```

**Покрытие:** общее ≥ 70%, критические модули ≥ 90%.

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

- `main` — production (защищена)
- `develop` — основная ветка разработки (защищена, base для PR)
- `feature/*` — новые функции
- `hotfix/*` — критические исправления

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

> **Авторитетный источник правил GitNexus — этот раздел, а не автогенерируемый блок ниже.**
> MCP-сервер `gitnexus` отключён намеренно: его команда `npx -y gitnexus@latest mcp` падает с
> `npm error Invalid Version`, инструменты `gitnexus_*` в сессии не появляются. Всё — через Bash.
> `npx gitnexus analyze` перезапишет блок между маркерами MCP-версией; **игнорируй её** — этот раздел вне маркеров и переживает регенерацию.

Проект проиндексирован GitNexus как **FREESPORT**. Используй CLI, чтобы понимать код,
оценивать последствия правок и безопасно навигировать.

> Если `npx gitnexus status` показывает `stale` — попроси пользователя выполнить `! npx gitnexus analyze`.

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
| Переиндексация | `npx gitnexus analyze` |
| Blast radius | `npx gitnexus impact <symbol> [--direction upstream\|downstream] [--depth N] [--include-tests]` |
| Контекст символа | `npx gitnexus context <symbol> [--file <path>] [--content]` |
| Поиск потоков выполнения | `npx gitnexus query "<концепция>" [--limit N] [--goal <text>]` |
| Символы, затронутые изменениями | `npx gitnexus detect-changes [--scope unstaged\|staged\|all\|compare] [--base-ref <ref>]` |
| Произвольный запрос к графу | `npx gitnexus cypher "<query>"` |

Вызывай без тега версии: `npx -y gitnexus@latest ...` падает на резолве `@latest`.
`impact`, `context`, `query`, `cypher` печатают JSON; `status` и `detect-changes` — текст.

### Ограничения CLI

- Команды `rename` нет — переименование только вручную по списку из `impact`/`context`.
- MCP-ресурсов (`gitnexus://repo/...`) нет; их заменяют `query`, `context` и `cypher`.
- `npx gitnexus wiki` требует LLM-провайдер и API-ключ — это не локальная бесплатная команда.
- Символы, добавленные после последней индексации, не находятся: `context` вернёт
  `{"error": "Symbol ... not found"}`. Это признак устаревшего индекса, а не отсутствия кода.

### Skill-файлы

| Задача | Файл |
|---|---|
| Понять архитектуру / «Как работает X?» | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / «Что сломается, если поменять X?» | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Отладка / «Почему X падает?» | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Переименование и рефакторинг | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Справочник по командам и схеме графа | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Индекс, статус, очистка, wiki | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FREESPORT** (8874 symbols, 14652 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/FREESPORT/context` | Codebase overview, check index freshness |
| `gitnexus://repo/FREESPORT/clusters` | All functional areas |
| `gitnexus://repo/FREESPORT/processes` | All execution flows |
| `gitnexus://repo/FREESPORT/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
