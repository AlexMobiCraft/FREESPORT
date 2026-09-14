---
name: gitnexus-refactoring
description: "Use when the user wants to rename, extract, split, move, or restructure code safely. Examples: \"Rename this function\", \"Extract this into a module\", \"Refactor this class\", \"Move this to a separate file\""
---

# Рефакторинг через GitNexus CLI

Команды — `npx gitnexus ...` в Bash, всегда с `-r "C:\Users\1\DEV\FREESPORT"` (индексов
FREESPORT два). Инструментов `gitnexus_*` и ресурсов `gitnexus://` нет — MCP отключён.

**Команды `rename` в CLI нет.** Переименование — вручную: собери все места через `impact`,
`context` и grep, затем правь точечно. Find-and-replace по всему репозиторию запрещён (CLAUDE.md).

## Workflow

```
1. npx gitnexus impact -r <repo> <X>          → все зависимые (сообщить risk пользователю)
2. npx gitnexus context -r <repo> <X>         → входящие и исходящие ссылки
3. npx gitnexus query -r <repo> "<X>"          → потоки, где участвует X
4. Порядок правок: интерфейсы → реализации → вызывающие → тесты
5. npx gitnexus detect-changes -r <repo> --scope all → затронуто только ожидаемое
```

> `stale` → попроси пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
> На устаревшем индексе список мест неполный.

## Переименование символа

```
- [ ] impact <старое имя> --include-tests: список вызывающих по byDepth
- [ ] context <старое имя>: incoming / outgoing (при ambiguous — -f <файл> или -u <uid>)
- [ ] Grep по старому имени: граф не видит строковые и динамические ссылки
      (getattr, строки в urls.py, сериализаторы, фронтенд, шаблоны писем, миграции)
- [ ] Править каждое место осознанно, не массовой заменой
- [ ] detect-changes --scope all: изменены только ожидаемые символы
- [ ] Прогнать тесты затронутых модулей (через Docker)
```

## Вынос в модуль

```
- [ ] context <target>: все входящие и исходящие ссылки
- [ ] impact <target>: внешние вызывающие
- [ ] Определить интерфейс нового модуля
- [ ] Перенести код, обновить импорты
- [ ] detect-changes --scope all
- [ ] Прогнать тесты
```

## Разделение функции или сервиса

```
- [ ] context <target>: все вызываемые (outgoing)
- [ ] Сгруппировать вызываемые по ответственности
- [ ] impact <target>: вызывающие, которые придётся обновить
- [ ] Создать новые функции, обновить вызывающих
- [ ] detect-changes --scope all
- [ ] Прогнать тесты
```

## Все места использования

```bash
# прямые вызывающие
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: '_get_order_display_items'}) RETURN caller.name, caller.filePath ORDER BY caller.filePath"
# импорты файла
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH (a:File)-[:CodeRelation {type: 'IMPORTS'}]->(b:File {filePath: 'backend/apps/orders/tasks.py'}) RETURN a.filePath"
```

## Риски

| Фактор | Что делать |
| --- | --- |
| Много вызывающих (>5) | Правь пакетами по модулям, после каждого — тесты |
| Ссылки между областями | `detect-changes` после правок |
| Строковые и динамические ссылки | Grep: граф их не видит |
| Публичный API, эндпоинты, поля моделей | Сохранить совместимость, миграция, OpenAPI |

## Пример: переименовать `_get_order_display_items`

```
1. npx gitnexus impact -r "C:\Users\1\DEV\FREESPORT" _get_order_display_items --include-tests
   → risk LOW; depth 1: _build_order_email_text, send_order_notification_email
2. Grep "_get_order_display_items" → ещё места в тестах и документации
3. Переименовать определение и каждый вызов вручную
4. npx gitnexus detect-changes -r "C:\Users\1\DEV\FREESPORT" --scope all
   → изменены только символы backend/apps/orders/tasks.py
5. Прогнать тесты orders в Docker
```
