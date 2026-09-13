---
name: gitnexus-guide
description: "Use when the user asks about GitNexus itself — available CLI commands, how to query the knowledge graph, graph schema, or workflow reference. Examples: \"What GitNexus commands are available?\", \"How do I use GitNexus?\""
---

# GitNexus: справочник по CLI и схеме графа

MCP-сервер `gitnexus` отключён: инструментов `gitnexus_*` и ресурсов `gitnexus://` нет.
Всё — через `npx gitnexus <команда>` в Bash.

## С чего начинать

1. `npx gitnexus status` — если `stale`, попроси пользователя выполнить
   `! npx gitnexus analyze --skip-agents-md` (сам не запускай).
2. Выбери skill-файл под задачу и следуй его workflow.
3. Во все команды анализа передавай `-r "C:\Users\1\DEV\FREESPORT"`: индексов с именем
   FREESPORT два (второй — `FREESPORT-pr117`), без пути команды падают.

| Задача | Skill |
| --- | --- |
| «Как работает X?», архитектура | `gitnexus-exploring` |
| «Что сломается, если поменять X?» | `gitnexus-impact-analysis` |
| «Почему X падает?» | `gitnexus-debugging` |
| Переименование, вынос, разделение | `gitnexus-refactoring` |
| Индекс, status, clean, wiki | `gitnexus-cli` |

## Команды

| Команда | Что даёт | Вывод |
| --- | --- | --- |
| `query "<концепция>" [-l N] [-g <цель>] [-c <контекст>] [--content]` | Процессы и символы по теме | JSON: `processes`, `process_symbols`, `definitions` |
| `context <name> [-f <file>] [-u <uid>] [--content]` | Символ: вызывающие, вызываемые, процессы | JSON: `symbol`, `incoming`, `outgoing`, `processes` |
| `impact <target> [-d upstream\|downstream] [--depth N] [--include-tests]` | Blast radius по глубинам + риск | JSON: `risk`, `summary`, `byDepth`, `affected_processes` |
| `detect-changes [-s unstaged\|staged\|all\|compare] [-b <ref>]` | Какие символы и процессы задевает git diff | текст |
| `cypher "<query>"` | Произвольный запрос к графу | JSON: `markdown` (таблица), `row_count` |
| `status`, `list` | Свежесть индекса, список репозиториев | текст |

Команды `rename` нет. Переименование — вручную по списку из `impact` и `context`
(см. `gitnexus-refactoring`).

## Неоднозначные имена

`context get` вернёт `"status": "ambiguous"` и список `candidates` с `uid`. Уточни через
`-f <путь к файлу>` или `-u <uid>`. `ambiguous` у `impact` — не «0 затронутых»: у `impact` нет
`--file`, поэтому для частых имён ищи вызывающих через `cypher` по `filePath`.

## Схема графа

**Узлы:** `Function`, `Method`, `Class`, `Interface`, `Property`, `Variable`, `Const`, `File`,
`Folder`, `Section`, `Route`, `Community` (функциональная область), `Process` (поток выполнения).

**Связи** — одна таблица `CodeRelation`, тип в свойстве `type`: `DEFINES`, `CALLS`, `MEMBER_OF`,
`STEP_IN_PROCESS`, `IMPORTS`, `CONTAINS`, `HAS_METHOD`, `HAS_PROPERTY`, `ACCESSES`, `EXTENDS`,
`HANDLES_ROUTE`. У `STEP_IN_PROCESS` есть `step` (номер шага), у всех — `confidence`.

**Свойства:** у символов `name`, `filePath`, `startLine`, `endLine`; у `Process` — `id`, `label`,
`stepCount`, `processType`; у `Community` — `label`, `symbolCount`, `cohesion`.

## Проверенные запросы

Кто вызывает функцию:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: 'send_order_notification_email'}) RETURN caller.name, caller.filePath"
```

Цепочки вызовов глубиной до 2. Синтаксис `[:CodeRelation {type: 'CALLS'}*1..2]` здесь
**не парсится** — фильтруй связи через `rels()`:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH p = (a)-[r:CodeRelation*1..2]->(b:Function {name: '_get_order_display_items'}) WHERE all(x IN rels(p) WHERE x.type = 'CALLS') RETURN properties(nodes(p), 'name') AS chain"
```

Список процессов и трассировка одного по шагам:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (p:Process) RETURN p.id, p.label, p.stepCount ORDER BY p.stepCount DESC LIMIT 20"
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (s)-[r:CodeRelation {type: 'STEP_IN_PROCESS'}]->(p:Process {id: 'proc_0_handle_init'}) RETURN r.step AS step, s.name AS name, s.filePath AS file ORDER BY step"
```

В каких процессах участвует символ:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (s {name: 'handle_init'})-[r:CodeRelation {type: 'STEP_IN_PROCESS'}]->(p:Process) RETURN p.id, p.label, r.step, p.stepCount"
```

Функциональные области и их состав:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (c:Community) RETURN c.label AS area, c.symbolCount AS n ORDER BY n DESC LIMIT 20"
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (s)-[:CodeRelation {type: 'MEMBER_OF'}]->(c:Community {label: 'Orders'}) RETURN s.name, s.filePath"
```
