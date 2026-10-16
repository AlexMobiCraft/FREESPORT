---
name: gitnexus-impact-analysis
description: "Use when the user wants to know what will break if they change something, or needs safety analysis before editing code. Examples: \"Is it safe to change X?\", \"What depends on this?\", \"What will break?\""
---

# Анализ последствий через GitNexus CLI

Команды — `npx gitnexus ...` в Bash, всегда с `-r "C:\Users\1\DEV\FREESPORT"` (правила —
`.windsurf/rules/gitnexus.md`). Инструментов `gitnexus_*` и ресурсов `gitnexus://` нет — MCP отключён.
По правилам AGENTS.md `impact` обязателен перед правкой любого символа, `detect-changes` — перед коммитом.

## Workflow

```
1. npx gitnexus impact -r <repo> <symbol>              → кто зависит от символа (upstream)
2. cypher: процессы из affected_processes              → какие потоки задеты
3. npx gitnexus detect-changes -r <repo> --scope all   → перед коммитом: что задевает diff
4. Оценить риск и сообщить пользователю
```

> `stale` → попроси пользователя выполнить `! npx gitnexus analyze --force`.
> На устаревшем индексе `impact` не видит новых вызывающих — занижает риск.

## Чеклист

```
- [ ] impact (по умолчанию upstream, depth 3)
- [ ] Сначала depth 1 — это сломается точно
- [ ] Связи с низким confidence перепроверить чтением кода
- [ ] affected_processes: какие потоки задеты
- [ ] --include-tests, если нужно знать, какие тесты прогнать
- [ ] Сообщить пользователю: прямые вызывающие, процессы, risk
- [ ] Перед коммитом: detect-changes --scope all и check --cycles
```

## Вывод impact

```json
{
  "risk": "LOW",
  "impactedCount": 3,
  "summary": {"direct": 2, "processes_affected": 0, "modules_affected": 1},
  "affected_processes": [],
  "affected_modules": [{"name": "Orders", "hits": 3, "impact": "direct"}],
  "byDepth": {
    "1": [{"name": "_build_order_email_text", "filePath": "backend/apps/orders/tasks.py", "relationType": "CALLS", "confidence": 0.85}],
    "2": [{"name": "send_order_confirmation_to_customer", "...": "..."}]
  }
}
```

| Глубина | Значение |
| --- | --- |
| `byDepth.1` | Прямые вызывающие и импортёры — **сломается** |
| `byDepth.2` | Косвенные зависимости — вероятно затронуто |
| `byDepth.3` | Транзитивно — стоит проверить тестами |

`risk` считает сам CLI. Если вернул `HIGH` или `CRITICAL` — **предупреди пользователя до правок**.
Код в критических путях (заказы, оплата, обмен с 1С, цены) повышает риск независимо от числа вызывающих.

`-d downstream` показывает обратное — от чего зависит сам символ. `--summary-only` оставляет только
`risk` и счётчики — удобно для таблицы в стори; `--include-tests` добавляет тесты, зависящие от символа.

## Неоднозначные имена

Если символов с таким именем несколько, `impact` вернёт `ambiguous` — это **не** «ничего не
затронуто». Уточни файл, тип или uid из списка `candidates`:

```bash
npx gitnexus impact get -r "C:\Users\1\DEV\FREESPORT" --file backend/apps/bonuses/views.py --kind Method
```

## Перед коммитом

```bash
npx gitnexus detect-changes -r "C:\Users\1\DEV\FREESPORT" --scope all          # staged + unstaged
npx gitnexus detect-changes -r "C:\Users\1\DEV\FREESPORT" --scope compare -b develop  # вся ветка
```

Вывод текстовый: изменённые символы и задетые процессы. `No changes detected` при правках только
в документации или конфигах — нормально: там нет проиндексированных символов.

```bash
npx gitnexus check --cycles -r "C:\Users\1\DEV\FREESPORT"
```

Новых циклов импорта быть не должно. Базовая линия и код выхода — правило 3 в `.windsurf/rules/gitnexus.md`.
