---
name: gitnexus-cli
description: "Use when the user needs to run GitNexus CLI commands like analyze/index a repo, check status, clean the index, generate a wiki, or list indexed repos. Examples: \"Index this repo\", \"Reanalyze the codebase\", \"Generate a wiki\""
---

# GitNexus CLI: индекс и обслуживание

GitNexus 1.6.12 стоит глобально, `npx gitnexus ...` в Bash берёт эту установку. Без тега версии:
`npx -y gitnexus@latest ...` падает на резолве `@latest`. MCP-сервер `gitnexus` отключён —
инструментов `gitnexus_*` и ресурсов `gitnexus://` в сессии нет. Правила — `.windsurf/rules/gitnexus.md`.

## Путь к репозиторию

Во все команды анализа (`context`, `impact`, `query`, `cypher`, `trace`, `detect-changes`, `check`)
передавай путь:

```bash
npx gitnexus impact <symbol> -r "C:\Users\1\DEV\FREESPORT"
```

Сейчас индекс один, но клон или worktree со своим индексом регистрируется под тем же именем
`FREESPORT`, и тогда команды без пути падают на «Multiple repositories indexed», а `-r FREESPORT`
молча берёт один из двух.

## status — свежесть индекса

```bash
npx gitnexus status          # текст
npx gitnexus status --json   # поле status: up-to-date | stale
```

Сравнивает индекс с проиндексированными файлами рабочего дерева. `⚠️ stale` — индекс не видит
свежий код: символы, добавленные после индексации, не находятся (`context` вернёт `Symbol ... not found`).

## analyze — построить или обновить индекс

```bash
npx gitnexus analyze --force
```

Только с `--force`: инкрементальная сборка в 1.6.12 теряет у методов `id` и `filePath`, после чего
`impact <метод> --file ...` отвечает `not found`. Полная сборка переиспользует кэш разбора и идёт
около минуты. **Сам не запускай**: попроси пользователя выполнить `! npx gitnexus analyze --force`.

Флаги лежат в `.gitnexusrc` (`skipAgentsMd`, `skipSkills`), поэтому `analyze` не пишет в `CLAUDE.md`,
`AGENTS.md` и навыки. Если всё же появился блок `<!-- gitnexus:start -->` — удали его вместе с маркерами.
Что попадает в индекс — `.gitnexusignore`.

| Флаг | Эффект |
| --- | --- |
| `--force` | Полная переиндексация — обязательна (см. выше) |
| `--repair-fts` | Пересобрать полнотекстовый поиск без полной переиндексации |
| `--embeddings` | Эмбеддинги для семантического поиска (по умолчанию выключены) |
| `--drop-embeddings` | Удалить имеющиеся эмбеддинги при пересборке |

Обновление GitNexus и разбор сбоев — раздел «Обновление и сбои» в `.windsurf/rules/gitnexus.md`.
Самый частый сбой: `query` пустой с `"warning": "FTS indexes missing"` — живой `gitnexus mcp` не дал
загрузить расширение поиска; после остановки процессов лечится `npx gitnexus analyze --repair-fts`.

## doctor — возможности среды

```bash
npx gitnexus doctor
```

Версии Node, GitNexus, LadybugDB и доступность расширений. После `analyze` строка
`Full-text search` должна быть `available`; `VECTOR extension: unavailable` на Windows — норма.

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

`query`, `context`, `impact`, `trace`, `cypher`, `detect-changes`, `check` — в skill-файлах
`gitnexus-exploring`, `gitnexus-impact-analysis`, `gitnexus-debugging`, `gitnexus-refactoring`;
справочник — `gitnexus-guide`.
