---
name: gitnexus-exploring
description: "Use when the user asks how code works, wants to understand architecture, trace execution flows, or explore unfamiliar parts of the codebase. Examples: \"How does X work?\", \"What calls this function?\", \"Show me the auth flow\""
---

# Исследование кода через GitNexus CLI

Команды — `npx gitnexus ...` в Bash, всегда с `-r "C:\Users\1\DEV\FREESPORT"` (индексов
FREESPORT два). Инструментов `gitnexus_*` и ресурсов `gitnexus://` нет — MCP отключён.
Справочник по командам и схеме — `gitnexus-guide`.

## Когда использовать

- «Как работает X?», «Где логика Y?»
- Знакомство с незнакомым модулем
- Нужны потоки выполнения, а не просто совпадения grep

## Workflow

```
1. npx gitnexus status                                   → свежесть индекса
2. npx gitnexus query -r <repo> "<что понять>" -l 5       → процессы и символы по теме
3. npx gitnexus context -r <repo> <symbol>               → вызывающие / вызываемые / процессы
4. npx gitnexus cypher -r <repo> "<трассировка процесса>" → шаги потока по порядку
5. Read исходников                                       → детали реализации
```

> `stale` в шаге 1 → попроси пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
> Символ, добавленный после индексации, `context` не найдёт — это устаревший индекс, а не отсутствие кода.

## Чеклист

```
- [ ] status: индекс свежий
- [ ] query по концепции (-g <цель> улучшает ранжирование)
- [ ] Разобрать processes и definitions из ответа
- [ ] context на ключевых символах
- [ ] Трассировка процесса через cypher, если нужен порядок шагов
- [ ] Прочитать исходники
```

## Вывод команд

`query` — JSON с `processes` (потоки), `process_symbols` (символы по потокам) и `definitions`
(файлы, функции, классы с `filePath` и строками). Пустой `processes` — нормально: тема может не
попадать в выделенные потоки, тогда опирайся на `definitions`.

`context` — JSON: `symbol` (uid, kind, filePath, строки), `incoming.calls`, `outgoing`, `processes`.
На частом имени (`get`, `save`) вернёт `"status": "ambiguous"` с `candidates` — повтори с
`-f <файл>` или `-u <uid>`. `--content` добавит исходник символа.

## Трассировка процесса

```bash
# в каких процессах участвует символ
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (s {name: 'handle_init'})-[r:CodeRelation {type: 'STEP_IN_PROCESS'}]->(p:Process) RETURN p.id, p.label, r.step, p.stepCount"
# шаги процесса по порядку
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (s)-[r:CodeRelation {type: 'STEP_IN_PROCESS'}]->(p:Process {id: 'proc_0_handle_init'}) RETURN r.step AS step, s.name AS name, s.filePath AS file ORDER BY step"
```

## Пример: «Как 1С передаёт файлы обмена?»

```
1. npx gitnexus query -r "C:\Users\1\DEV\FREESPORT" "обмен с 1С загрузка файлов"
   → процессы proc_0_handle_init «Handle_init → _route_root» и соседние
2. cypher: шаги proc_0_handle_init
   → handle_init → _get_exchange_identity → get → handle_import → execute
     → _transfer_files → move_to_import → _ensure_import_dir → _route_root
3. npx gitnexus context -r "C:\Users\1\DEV\FREESPORT" _transfer_files
   → кто вызывает, что вызывает
4. Read backend/apps/integrations/onec_exchange/import_orchestrator.py
```
