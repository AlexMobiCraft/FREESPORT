---
description: Критические правила работы с git и публичным репозиторием FREESPORT-B2B
---

# Безопасность git и публичный репозиторий

## Запрет прямого пуша в production remote

НИКОГДА не выполняй `git push production main` вручную, особенно с `--force`.

Публичный репозиторий FREESPORT-B2B обновляется ТОЛЬКО через GitHub Actions workflow `sync-to-public.yml`, который:

1. Удаляет конфиденциальные файлы (`.env`, `.mcp.json`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` и т.д.).
2. Удаляет AI-инструменты (`_bmad/`, `.agents/`, `.windsurf/`, `.claude/` и т.д.).
3. Удаляет скрипты (`scripts/`).
4. Удаляет внутреннюю документацию.
5. Удаляет `.git` историю (предотвращает Secret Scanning на старые коммиты).
6. Создаёт чистый коммит от Freesport Sync Bot.

Прямой force push сливает ВСЮ историю коммитов и ВСЕ конфиденциальные файлы в публичный репозиторий.

## Обновление продакшн-сервера

- Локально: `git push origin main` (только в приватный репозиторий) → workflow сработает автоматически.
- На сервере: `git fetch origin main; git reset --hard origin/main` + пересборка Docker.

НИКОГДА не используй `git pull` на продакшене.
