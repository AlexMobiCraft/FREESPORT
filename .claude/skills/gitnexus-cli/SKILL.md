---
name: gitnexus-cli
description: "Use when the user needs to run GitNexus CLI commands like analyze/index a repo, check status, clean the index, generate a wiki, or list indexed repos. Examples: \"Index this repo\", \"Reanalyze the codebase\", \"Generate a wiki\""
---

# GitNexus CLI: индекс и обслуживание

Всё через `npx gitnexus ...` в Bash, глобальная установка не нужна. Без тега версии:
`npx -y gitnexus@latest ...` падает на резолве `@latest`. MCP-сервер `gitnexus` отключён —
инструментов `gitnexus_*` и ресурсов `gitnexus://` в сессии нет.

## Два индекса с именем FREESPORT

`npx gitnexus list` показывает два репозитория `FREESPORT`: основной клон и
`C:\Users\1\DEV\FREESPORT-pr117`. Поэтому `context`, `impact`, `query`, `cypher`, `detect-changes`
без `-r` падают на «Multiple repositories indexed», а `-r FREESPORT` молча берёт один из двух индексов (сейчас основной, но это зависит от реестра).
Всегда передавай путь:

```bash
npx gitnexus impact <symbol> -r "C:\Users\1\DEV\FREESPORT"
```

## status — свежесть индекса

```bash
npx gitnexus status
```

Сравнивает `Indexed commit` с `Current commit`. `⚠️ stale` — индекс не видит свежий код:
символы, добавленные после индексации, не находятся (`context` вернёт `Symbol ... not found`).

## analyze — построить или обновить индекс

```bash
npx gitnexus analyze --skip-agents-md
```

**Сам не запускай** — долго (до пары минут) и блокирует сессию. Попроси пользователя
выполнить `! npx gitnexus analyze --skip-agents-md`.

`--skip-agents-md` в этом репозитории обязателен: без него `analyze` допишет в `CLAUDE.md` и
`AGENTS.md` блок `<!-- gitnexus:start -->` с MCP-инструкциями, противоречащими разделу GitNexus.
Если блок появился — удали его вместе с маркерами.

`analyze` также **каждый раз** перезаписывает `.claude/skills/gitnexus/` своими MCP-шаблонами
(флага, чтобы это отключить, нет). Каталог в `.gitignore` — не читай и не правь его; рабочие
CLI-версии skills лежат в `.claude/skills/gitnexus-*/`.

| Флаг | Эффект |
| --- | --- |
| `--skip-agents-md` | Не трогать CLAUDE.md / AGENTS.md (обязателен здесь) |
| `--force` | Полная переиндексация, даже если индекс свежий |
| `--embeddings` | Эмбеддинги для семантического поиска (по умолчанию выключены) |
| `--drop-embeddings` | Удалить имеющиеся эмбеддинги при пересборке |

## list — все проиндексированные репозитории

```bash
npx gitnexus list
```

## clean — удалить индекс

```bash
npx gitnexus clean
```

Удаляет `.gitnexus/` и снимает репозиторий с регистрации. Только с согласия пользователя —
после этого нужен полный `analyze`. `--force` пропускает подтверждение, `--all` чистит все репозитории.

## wiki

`npx gitnexus wiki` генерирует документацию через LLM и требует API-ключ — это не локальная
бесплатная команда. Не запускай без явной просьбы.

## Команды анализа кода

`query`, `context`, `impact`, `cypher`, `detect-changes` — в skill-файлах `gitnexus-exploring`,
`gitnexus-impact-analysis`, `gitnexus-debugging`, `gitnexus-refactoring`; справочник — `gitnexus-guide`.
