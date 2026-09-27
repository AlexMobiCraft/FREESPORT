# Руководство для AI-агентов проекта FREESPORT

Единый источник правил для всех агентов (Claude Code, Codex, Devin Desktop). `CLAUDE.md` только импортирует этот файл через `@AGENTS.md` — новые правила добавляй сюда.

- **Навыки** — `.claude/skills/` (Claude Code) и `.agents/skills/` (Codex, Devin Desktop). Собственные навыки правь в `.claude/skills/`, затем запусти `python scripts/dev/sync_agent_skills.py`: он повторит их в `.agents/skills/`, а `pre-merge-checks.yml` падает, если копии разошлись. Навыки BMAD (`bmad*`) и Vercel (`vercel-*`) раскладывает `npx skills` — вручную их не правь.
- **Правила по темам** — `.windsurf/rules/`: Devin подключает их сам по `description`, остальные агенты читают по ссылкам из раздела «Критические правила и runbook'и».
- **Правила каталога `backend/`** — `backend/AGENTS.md`.

- Отвечай и веди документацию исключительно на русском языке
- communication_language: Russian
- document_output_language: Russian

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

### Тестирование backend (ТОЛЬКО через Docker с PostgreSQL)

Конкретный backend-тест:

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/test_product_variant_models.py::TestProductVariant::test_create_variant_with_valid_data
```

**`--env-file` тестовому compose не передаётся:** файла `docker/.env` нет, и с ним команда падает на `couldn't find env file`. Он и не нужен — в `docker-compose.test.yml` нет подстановок переменных. **`run --rm`, а не `exec`:** у сервиса `backend` команда по умолчанию `pytest`, контейнер отрабатывает и выходит, поэтому после прогона подключаться `exec` не к чему.

**В уже поднятой dev-среде** можно через `exec`:
`docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту>`

**Покрытие:** CI (`main.yml`) падает ниже 75% общего покрытия; критические модули — цель ≥ 90%. Какой прогон считает порог и почему — в `backend/docs/testing-standards.md`.

**Маркеры pytest** (`unit`, `integration`, `data_dependent`, `slow`, `performance`) объявлены в `backend/pytest.ini`; что из них исключают PR-гейты — в `backend/docs/testing-standards.md`.

**Структура тестов:**

- Юнит-тесты располагаются внутри каждого Django-приложения
- Интеграционные тесты находятся в директории `/backend/tests`
- Тесты для компонентов frontend находятся рядом с ними в директориях `__tests__`

### Python-зависимости backend

`backend/requirements.txt` — полный закреплённый список (вместе с транзитивными пакетами), из которого собираются все образы на `python:3.12-slim`. Локальный `backend/venv` работает на другой версии Python, поэтому пакеты через него не ставь и `pip freeze` из него не делай: pip подберёт версии под чужой интерпретатор. Venv нужен только для линтеров (навык `backend-lint`).

Новая зависимость:

1. Допиши `пакет==версия` в `backend/requirements.txt`.
2. Пересобери образ и перегенерируй файл из контейнера, чтобы попали транзитивные зависимости:
   ```bash
   docker compose --env-file .env -f docker/docker-compose.yml build backend
   docker compose --env-file .env -f docker/docker-compose.yml run --rm --no-deps -T backend pip freeze > backend/requirements.txt
   ```
3. Проверь `git diff backend/requirements.txt`: меняться должны только новый пакет и его зависимости.

### Frontend

Конфиги — `frontend/.prettierrc` и `frontend/eslint.config.mjs`. При сборке форматирование не применяется: `prettier --check` — отдельный гейт в `frontend-ci.yml`. Форматирование фронтенда — `npm run format` в `frontend/`; backend — навык `backend-lint`.

- После правок `frontend/src/` перед коммитом прогони локально:
  ```bash
  cd frontend
  npm run format:check   # prettier --check .  — гейт в frontend-ci.yml
  npm run lint           # eslint . --max-warnings=0
  npx tsc --noEmit
  ```
  Pre-commit хук `.husky/pre-commit` (lint-staged → prettier+eslint) на этой машине НЕ активен — `core.hooksPath` не установлен, корневого `package.json` нет. Полагаться на автоформатирование при коммите нельзя.

- Контейнер `frontend` работает на `npm run dev` с примонтированным `frontend/`. Если правка не появилась в браузере (hot-reload через bind-mount на Windows срабатывает не всегда), перезапусти его:

  ```bash
  # Обычный перезапуск (для проблем с hot-reload)
  docker compose --env-file .env -f docker/docker-compose.yml restart frontend

  # Полная пересборка (при изменении зависимостей или конфига)
  docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend
  ```

## Работа в среде Windows и Terminal

### PowerShell Chaining

В среде Windows PowerShell для объединения команд используй `;` вместо `&&`.
_Например:_ `git add .; git commit -m "..."; git push`

### Терминал и SSH

- **SSH Authentication**: Используй только SSH-ключи через `ssh-agent` — интерактивный запрос пароля подвешивает агента.
- **Production Git Updates**: На продакшене — `git fetch origin main; git reset --hard origin/main`, не `git pull`: на сервере есть коммиты Sync Bot, и pull падает с `divergent branches`.

## Интеграция с 1С (CommerceML 3.1)

### Реальные данные для тестов

Тесты импорта 1С работают на реальных выгрузках, синтетические XML для них не создавай. Файлы — в `data/import_1c/`:
  - `contragents/` — контрагенты (ООО/ИП/физлица, edge cases)
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
- `develop` — основная ветка разработки (защищена, base для PR, 6 required-чеков)
- `feature/*` — новые функции
- `hotfix/*` — критические исправления
- Синк `develop` → `main`: `git push origin origin/develop:refs/heads/main` (fast-forward, только по команде владельца). **Этот push и есть релиз:** он запускает `deploy.yml` (сборка образов → approval на environment `production` → SSH-деплой). Тестов на push нет ни в `develop`, ни в `main` — тот же SHA уже зелёный на PR.
- Мёрдж PR **только merge commit**, предпочтительно на автомёрдже: `gh pr merge N --auto --merge` — сольётся сам по зелёным чекам, head-ветка удалится автоматически. Squash/rebase разводят историю и ломают fast-forward синк (отключены в настройках репозитория).
- Откат релиза: `gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>` — без пересборки и тестов. Подробности и откат самой схемы — `.windsurf/rules/git-sync-workflow.md`

## Критические правила и runbook'и

Постоянные инварианты и продакшен-инструкции вынесены в отдельные rule-файлы:

- [`.windsurf/rules/security-and-git.md`](.windsurf/rules/security-and-git.md) — запрет прямого пуша в public remote, обновление продакшена.
- [`.windsurf/rules/git-sync-workflow.md`](.windsurf/rules/git-sync-workflow.md) — порядок сохранения изменений: PR в develop (единственный гейт, 6 чеков), синк в main fast-forward пушем без PR (этот push = релиз), откат релиза и откат самой схемы.
- [`.windsurf/rules/production-operations.md`](.windsurf/rules/production-operations.md) — типовые инциденты: 502, Server Action mismatch, restart nginx.
- [`.windsurf/rules/order-numbering.md`](.windsurf/rules/order-numbering.md) — форматы мастер/субзаказов и поиск в админке.
- [`.windsurf/rules/1c-import-diagnostics.md`](.windsurf/rules/1c-import-diagnostics.md) — диагностика ошибок полной выгрузки 1С.

## Документация проекта

Подробности ищи в `docs/`:

- `docs/index.md` — главная документации
- `docs/PROJECT_INFO.md` — справочная информация о проекте (архитектура, стек, команды запуска и тесты)
- `_bmad-output/planning-artifacts/refined-prd.md` — Product Requirements (PRD)
- `docs/architecture/index.md` — архитектура системы
- `docs/integrations/1c/import-process.md` — архитектура импорта 1С
- `docs/api/openapi.yaml` — OpenAPI спецификация
- `docs/api/views-documentation.md` — документация API endpoints
- `_bmad-output/implementation-artifacts/` — текущие стори, контексты эпиков, deferred-work
- `docs/archive/v4/stories/epic-*/` — архив user stories (epic-1 … epic-31)
- `docs/decisions/` — архитектурные решения
- `docs/guides/` — руководства
- `docs/testing-docker.md` — тестирование в Docker
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
- **Переименование** — не через find-and-replace: собери все места через `impact` и `context`, затем правь точечно.

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
- `analyze` при каждом запуске (и с `--skip-agents-md` тоже) перезаписывает `.claude/skills/gitnexus/` своими MCP-шаблонами — флага, чтобы это отключить, нет. Каталог в `.gitignore`, не используй его; рабочие CLI-версии skills — `gitnexus-*/` в `.claude/skills/` и `.agents/skills/`.

### Skill-файлы

Каждый навык лежит в двух копиях — `.claude/skills/` (Claude Code) и `.agents/skills/` (Codex, Devin Desktop); бери каталог своего агента.

| Задача | Навык |
|---|---|
| Понять архитектуру / «Как работает X?» | `gitnexus-exploring/SKILL.md` |
| Blast radius / «Что сломается, если поменять X?» | `gitnexus-impact-analysis/SKILL.md` |
| Отладка / «Почему X падает?» | `gitnexus-debugging/SKILL.md` |
| Переименование и рефакторинг | `gitnexus-refactoring/SKILL.md` |
| Справочник по командам и схеме графа | `gitnexus-guide/SKILL.md` |
| Индекс, статус, очистка, wiki | `gitnexus-cli/SKILL.md` |
