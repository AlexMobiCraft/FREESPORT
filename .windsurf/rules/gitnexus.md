---
trigger: model_decision
description: GitNexus CLI — анализ кода перед правками и коммитом, свежесть индекса, команды, границы графа и встраивание в BMAD-воркфлоу
---

# GitNexus: граф кода (только CLI)

Единственный источник правил GitNexus. `AGENTS.md` держит только обязательный минимум и ссылку сюда,
`project-context.md` и `_bmad/custom/*.toml` подключают этот файл, а не копируют его текст.

## Установка и индекс

- GitNexus **1.6.12** стоит глобально (`npm i -g gitnexus@1.6.12`), `npx gitnexus` берёт её.
  Не вызывай `npx -y gitnexus@latest` — падает на резолве `@latest`.
- **MCP-сервер отключён у всех агентов** (пилот MCP отложен): инструментов `gitnexus_*` и ресурсов
  `gitnexus://` нет, всё — через Bash. Поэтому недоступны `rename`, `route_map`, `api_impact`,
  `shape_check`. У Devin Desktop запись `gitnexus` оставлена с `"disabled": true` в
  `%APPDATA%\Devin\mcp_config.json` и `~/.codeium/windsurf/mcp_config.json` — не включай её
  без решения о пилоте: долгоживущий `gitnexus mcp` держит базу индекса (см. «Обновление и сбои»).
- Флаги `analyze` лежат в `.gitnexusrc` (`skipAgentsMd`, `skipSkills`): `npx gitnexus analyze --force`
  не пишет в `AGENTS.md`/`CLAUDE.md` и в навыки. Переиндексируй **только с `--force`** — см. первый
  пункт «Границ графа»; полная сборка переиспользует кэш разбора и идёт около минуты.
  Появился блок `<!-- gitnexus:start -->` — удали его вместе с маркерами.
- Состав индекса задаёт `.gitnexusignore`: код `backend/` и `frontend/` вместе с тестами и
  `__init__.py`; без миграций, `docs/`, `scripts/`, `_bmad*/`, `.claude/`, `.agents/`, `.windsurf/`.
## Обновление и сбои

Обновление GitNexus — только по решению владельца, на закреплённую стабильную версию (не `rc`):

1. **Нет живых MCP-серверов.** Запущенный `gitnexus mcp` (его поднимает агент, у которого MCP
   включён) держит загруженную LadybugDB: `npm i -g` падает на `EPERM`, а `analyze` не загружает
   расширение поиска. Проверка в PowerShell:
   `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'gitnexus' }`.
   Нашлись — закрой агента-владельца или заверши процессы.
2. `npm i -g gitnexus@<версия>`, затем `npx gitnexus doctor`.
3. Первый прогон — `GITNEXUS_LBUG_EXTENSION_INSTALL=auto npx gitnexus analyze --force`: без переменной
   LadybugDB не скачивает расширение полнотекстового поиска. Схема индекса меняется между версиями,
   поэтому сборка будет полной.
4. Проверка: `doctor` → `Full-text search: available`; `query` по известной теме возвращает
   символы; `cypher "MATCH (m:Method) RETURN m.filePath = '' AS e, count(m)"` — только `false`.
5. Пересмотри «Границы графа» и сверь новые ключи `.gitnexusrc`: неизвестный ключ роняет `analyze`.

Сбои:

- **`query` пустой**, в ответе `"warning": "FTS indexes missing"`, а в выводе `analyze` было
  `LOAD fts failed ... IO exception` — расширение не загрузилось, обычно из-за живого
  `gitnexus mcp` (пункт 1). Убери процессы и выполни `npx gitnexus analyze --repair-fts`:
  пересобирает только поисковые индексы.
- **`Target ... not found` для метода, который есть в коде** — индекс собран без `--force`
  (первый пункт «Границ графа»).
- **`LOAD fts failed ... IO exception: Failed to load library ... Не найден указанный модуль`
  при живом файле `libfts.lbug_extension`** — расширению не хватает OpenSSL 3
  (`libcrypto-3-x64.dll`, `libssl-3-x64.dll`): в `System32` их нет, а LadybugDB ищет зависимости
  в каталоге самого расширения. Лечится копированием обоих DLL из `C:\Program Files\Git\mingw64\bin`
  (или `PostgreSQL 1C\18\bin`) в `%USERPROFILE%\.lbdb\extension\<версия>\win_amd64\fts\`, затем
  `npx gitnexus analyze --repair-fts`. Проверено 17.10.2026: после копирования `doctor` показывает
  `Full-text search: available`. При обновлении LadybugDB расширение скачивается в новый каталог —
  DLL придётся положить заново.

## Обязательно

1. **Свежесть индекса** — `npx gitnexus status`. При `stale` попроси пользователя выполнить
   `! npx gitnexus analyze --force` (до минуты), сам не запускай. Ответ `Symbol ... not found` или
   `Target ... not found` на заведомо существующий код — тоже признак устаревшего индекса
   или индекса, собранного без `--force`.
2. **Перед изменением функции, класса или метода** — `npx gitnexus impact <symbol> --direction upstream`;
   при одноимённых символах добавь `--file <путь>` или `--kind Function|Method|Class`. Сообщи
   пользователю blast radius: прямые вызывающие, затронутые процессы, `risk`. При `HIGH` или
   `CRITICAL` — предупреди до правок.
3. **Перед коммитом** — `npx gitnexus detect-changes --scope all`: затронуты только ожидаемые
   символы и потоки. Затем `npx gitnexus check --cycles`: новых циклов импорта нет. Базовая линия
   на 16.10.2026 — один цикл `frontend/src/components/home/HomePage.tsx → index.ts → HomePage.tsx`,
   из-за него команда завершается с кодом 1; сравнивай список, а не код выхода.
4. **Исследование кода** — `query` и `context` вместо grep по всей базе.
5. **Переименование** — команды `rename` в CLI нет: собери все места через `impact` и `context`,
   правь точечно, без find-and-replace.

Во все команды анализа передавай `-r "C:\Users\1\DEV\FREESPORT"` (в песочнице Codex — только
`-r C:/Users/1/DEV/FREESPORT`, см. «Слой ревью graph-impact»). Сейчас индекс один, но клон или
worktree со своим индексом регистрируется под тем же именем `FREESPORT`, и тогда команды без пути
падают на «Multiple repositories indexed».

## Команды

| Команда | Что даёт | Вывод |
| --- | --- | --- |
| `status [--json]` | Свежесть индекса: `up-to-date` / `stale` | текст; `--json` — поле `status` |
| `analyze [--force]` | Обновить индекс (флаги — в `.gitnexusrc`) | текст |
| `query "<концепция>" [-l N] [-g <цель>] [-c <контекст>]` | Процессы и символы по теме | JSON |
| `context <name> [-f <файл>] [-u <uid>] [--content]` | Вызывающие, вызываемые, процессы | JSON |
| `impact <name> [-d upstream\|downstream] [-f <файл>] [--kind <тип>] [--depth N] [--include-tests] [--summary-only] [-l N]` | Blast radius и `risk` | JSON |
| `trace <откуда> <куда> [--from-file] [--to-file] [--depth N]` | Кратчайший путь вызовов | JSON: `status`, `hops` |
| `detect-changes [-s unstaged\|staged\|all\|compare] [-b <ref>]` | Символы и потоки, задетые git diff | текст |
| `check --cycles [--json]` | Циклические импорты | текст, код 1 при любом цикле |
| `cypher "<запрос>"` | Произвольный запрос к графу | JSON: `markdown`, `row_count` |
| `list`, `doctor` | Реестр индексов, возможности среды | текст |

- `trace` идёт от вызывающего к вызываемому; в обратную сторону вернёт `no_path`.
- `impact --include-tests` показывает тесты, которые зависят от символа, — по ним выбирай, что прогнать.
- `impact` с `"status": "ambiguous"` — это не «0 затронутых»: уточни `--file`, `--kind` или `--uid`.
- `wiki` требует LLM-провайдер и API-ключ — без явной просьбы не запускай.

## Границы графа: чего отсутствие не доказывает

- **Инкрементальный `analyze` портит методы (1.6.12).** Без `--force` у узлов `Method` пропадают `id`
  и `filePath` (16.10.2026: 1129 из 1131 методов, и в Python, и в TypeScript). Признаки:
  `impact <метод> --file <путь>` отвечает `Target ... not found`, одноимённые методы не разобрать
  даже по `--uid`, а `cypher "MATCH (m:Method) RETURN m.filePath = '' AS e, count(m)"` показывает
  `true`. Лечится `analyze --force`.
- **Потоки (`Process`).** Анализатор ранжирует лишь ~200 из ~900 точек входа (лимит станет
  настраиваемым в 1.6.13). Нет потока — не значит, что нет пути вызовов: проверь `trace` или `context`.
- **Маршруты Django.** Узлов `Route` для backend нет: обнаружение идёт
  `manage.py → freesport/settings/__init__.py → ROOT_URLCONF`, а у нас `from .development import *`
  стоит внутри `if`, и GitNexus эту строку не распознаёт. DRF `router.urls` не извлекается в принципе.
  Карта API — `docs/api/openapi.yaml`.
- **Константы и переменные модуля не имеют входящих рёбер.** `impact` по ним вернёт `0` и `UNKNOWN`
  с оговоркой в `riskNote` — смотри `impact` функций, которые их читают.
- **Хуки фреймворков вызываются динамически.** У `clean_<поле>`, `save`, `get_queryset`, обработчиков
  сигналов и задач Celery вызывающих в графе нет — это ожидаемо, а не «код не используется».
- **Поля между Python и TypeScript не связываются.** «Поле никто не читает» в одном языке не значит,
  что поле не используется во втором.
- **`detect-changes` на устаревшем индексе** накладывает изменения на старые номера строк: в списке
  оказываются чужие символы и «Risk level: critical». Сверяй с `git diff` и сначала обнови индекс.
- **`risk` у типов из `frontend/src/types/api.ts` завышен** — рёбра идут от импорта файла целиком.
  Проверь реальных потребителей, прежде чем пугать пользователя.
- **Cypher:** `[:CodeRelation {type: 'CALLS'}*1..2]` не парсится — фильтруй связи через `rels()`
  (примеры в навыке `gitnexus-guide`).

## BMAD-воркфлоу

- **Проверка в начале** (`bmad-create-story`, `bmad-dev-story`, `bmad-quick-dev`, `bmad-build`,
  `bmad-code-review`, агент разработчика) — `npx gitnexus status`, результат показать пользователю.
  На `stale` анализ не начинать: попросить переиндексацию по правилу 1.
- **Исследование кода в воркфлоу** — только через GitNexus CLI; Explore-субагент не запускать.
  `Read` — по путям, которые вернул GitNexus.
- **`bmad-create-story`** — в Dev Notes стори добавь раздел «GitNexus: зона изменений»: для каждого
  символа, который стори меняет, — `impact <symbol> --summary-only` (risk, прямые вызывающие,
  затронутые процессы) и тесты из `impact --include-tests`. Исполнитель стори не повторяет
  исследование, а сверяет таблицу с текущим индексом.
- **`bmad-dev-story`, `bmad-quick-dev`, `bmad-build`** — правила 2 и 3 из раздела «Обязательно».
- **`bmad-code-review` и `bmad-build`** — слой ревью `graph-impact` (подключён в
  `_bmad/custom/bmad-code-review.toml` и `_bmad/custom/bmad-build.toml`) выполняет процедуру ниже.

## Слой ревью graph-impact

Ревьюер только читает: не правит файлы и не запускает git-команды, меняющие состояние.
Вход — unified diff, путь к которому передал воркфлоу.

1. `npx gitnexus status` — без `-r`: с `-r` команда свежесть не проверяет («registered index»).
   - `up-to-date` — продолжай.
   - `stale` при пустом `Current commit` и `Branch: (detached HEAD)` — это песочница исполнителя
     (Codex: вызовы `git` из процесса GitNexus там не работают), а не устаревший индекс. Сравни
     `git rev-parse --short HEAD` с `Indexed commit`: совпали — продолжай, иначе — как ниже.
   - `stale` с заполненным `Current commit` или несовпадение коммитов — выводов по графу не делай:
     верни одну находку «индекс устарел, слой graph-impact не выполнен» и остановись.
2. Выпиши из diff изменённые и удалённые функции, методы и классы. Если их больше 15, бери сначала
   символы с изменённой сигнатурой, возвращаемым значением или исключениями, затем — из
   `backend/apps/orders`, `products`, `integrations`, `users`.
3. Для каждого изменённого символа —
   `npx gitnexus impact <name> --file <путь> --direction upstream --include-tests --depth 2 -r C:/Users/1/DEV/FREESPORT`.
   Путь — прямыми слэшами: в песочнице Codex обратные теряются по дороге в процесс
   (`Repository "C:Users1DEVFREESPORT" not found`).
   - Константа или переменная модуля — `impact` по функциям того же файла, которые её читают.
   - Хук фреймворка (`clean_*`, `save`, `get_queryset`, сигнал, задача Celery) — вызывающих не будет;
     проверь регистрацию хука и тесты.
   - Удалённый символ граф уже не знает — ищи оставшиеся упоминания через `git grep -n <name>`.
   - `Target ... not found` для метода, который есть в коде, — индекс собран без `--force`
     (раздел «Границы графа»): верни находку «индекс повреждён» и остановись.
4. Находки:
   - **Несогласованный вызывающий.** Прямой вызывающий (`byDepth.1`, не тест), файл которого diff не
     трогает, хотя у символа изменились сигнатура, результат, исключения или побочные эффекты.
     Прочитай вызывающий код и покажи, где он несовместим.
   - **Нет проверки.** Изменённый символ, от которого не зависит ни один тест, и в diff тестов на него нет.
   - **Неназванный риск.** `risk` HIGH/CRITICAL или задетые процессы, о которых не говорят ни diff, ни спека.
   - **Новый цикл импорта.** `npx gitnexus check --cycles` показывает цикл, которого нет в базовой
     линии (раздел «Обязательно», правило 3).
5. Каждая находка: заголовок в одну строку, символ и файл, доказательство — выдержка из вывода
   GitNexus и строка кода. Помни раздел «Границы графа»: сигналы Django, задачи Celery, DRF-роутеры
   и динамические вызовы граф не видит — отсутствие связи проверяй поиском по имени.
6. Если исполнитель прогона не может запускать `npx gitnexus` (нет Bash, песочница запрещает запись
   блокировки индекса), сообщи об этом как о сбое слоя — молча пропускать нельзя.

Проверено 16.10.2026 на PR #316 через плагин Codex (read-only): в песочнице работают `impact`,
`check --cycles` и прямой `git rev-parse`; не работает только определение текущего коммита в `status`.
Четыре стандартных слоя `bmad-code-review` GitNexus не вызывают — граф смотрит только этот слой.

## Навыки

Каждый навык лежит в двух копиях — `.claude/skills/` (Claude Code) и `.agents/skills/` (Codex,
Devin Desktop). Правь `.claude/skills/`, затем `python scripts/dev/sync_agent_skills.py`.

| Задача | Навык |
| --- | --- |
| «Как работает X?», архитектура | `gitnexus-exploring` |
| «Что сломается, если поменять X?» | `gitnexus-impact-analysis` |
| «Почему X падает?» | `gitnexus-debugging` |
| Переименование, вынос, разделение | `gitnexus-refactoring` |
| Справочник по командам и схеме графа | `gitnexus-guide` |
| Индекс, `status`, `clean`, `doctor` | `gitnexus-cli` |
