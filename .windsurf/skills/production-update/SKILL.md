---
name: production-update
description: Используй этот навык для автоматизации развертывания обновлений на продакшен-сервере FREESPORT. Активируй при запросах "обнови сервер", "deploy to production", "выполни деплой", "быстрый фикс на проде", "обнови фронтенд/бекенд на сервере".
---

# Production Update Skill

Этот навык предназначен для управления процессом обновления проекта FREESPORT на продакшен-сервере через SSH.

## Параметры среды

- **Host:** `5.35.124.149`
- **User:** `root`
- **Project Path:** `/home/freesport/freesport/`
- **Production Repo:** `https://github.com/AlexMobiCraft/FREESPORT-B2B.git`
- **Compose File:** `docker/docker-compose.prod.yml`
- **Env File:** `.env.prod`

## Общий алгоритм (Локальная подготовка)

Перед обновлением сервера необходимо убедиться, что код запушен в правильный репозиторий:

1.  Проверь текущую ветку и наличие изменений (`git status`).
2.  Запуш изменения в `develop`: `git push origin develop`.
3.  Перелей в `main` (локально или через PR): `git checkout main; git merge develop --no-edit; git push origin main`.
4.  Публичный репозиторий `FREESPORT-B2B` обновится **автоматически** через GitHub Actions workflow `sync-to-public.yml` при пуше в `origin/main`. Этот workflow удаляет конфиденциальные файлы и пересоздаёт чистую историю.

> [!DANGER]
> **НИКОГДА не выполняй `git push production main` вручную!** Это сливает полную git-историю и конфиденциальные файлы (.env, .mcp.json, AGENTS.md, CLAUDE.md, \_bmad/, .agents/, .windsurf/, scripts/ и др.) в публичный репозиторий. Публичный репозиторий обновляется ТОЛЬКО через workflow `sync-to-public.yml`.

## Общий алгоритм (Обновление на сервере)

1.  Подключись к серверу по SSH (используй навык `production-server-ssh`).
2.  Перейди в папку проекта: `cd /home/freesport/freesport/`.
3.  **Проверь remote origin** — он должен указывать на **приватный** репозиторий:
    ```bash
    git remote -v
    # Должно быть: origin https://github.com/AlexMobiCraft/FREESPORT.git
    # Если указывает на FREESPORT-B2B — исправь:
    git remote set-url origin https://github.com/AlexMobiCraft/FREESPORT.git
    ```
4.  **Принудительно** обнови код (чтобы избежать конфликтов с коммитами `Freesport Sync Bot`):
    ```bash
    git fetch origin main
    git reset --hard origin/main
    ```

## Сценарии обновления

### 1. Полное обновление (Full Update)

Используй, когда изменились зависимости (`requirements.txt`, `package.json`), Docker-конфигурация или требуются масштабные изменения.

```bash
# 1. Перейти в папку проекта и собрать/запустить все контейнеры
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml up -d --build

# 2. Миграции БД
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# 3. Сборка статики
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --no-input
```

> [!IMPORTANT]
> Всегда используйте `cd /home/freesport/freesport &&` перед `docker compose` — команда ищет `.env.prod` относительно текущей директории. Абсолютный путь `--env-file /home/freesport/freesport/.env.prod` обеспечивает надёжность.

### 2. Быстрый фикс (Quick Fix)

Используй для обновления логики (Python/JS код), если не менялись зависимости и структура контейнеров.

```bash
# Перезапуск основных сервисов
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml restart backend frontend
```

> [!NOTE]
> Если изменения во фронтенде требуют пересборки статики (Next.js build), используй сценарий "Обновление фронтенда" (с флагом `--build`).

### 3. Обновление только бекенда (Backend Only)

```bash
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml up -d --build backend
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
```

### 4. Обновление только фронтенда (Frontend Only)

```bash
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml up -d --build frontend
```

## Важные замечания

> [!DANGER]
> **НИКОГДА не пушь напрямую в `production` remote (FREESPORT-B2B)!** Публичный репозиторий обновляется только через workflow `sync-to-public.yml` (срабатывает автоматически при пуше в `origin/main`). Прямой пуш сливает конфиденциальные данные и полную историю коммитов в публичный доступ. Инцидент 2026-04-12: ручной `git push production main --force` утек данные, потребовался emergency sync.

> [!DANGER]
> **PowerShell vs Bash:** На Windows используй `;` для разделения команд PowerShell вместо `&&`. Пример: `git add .; git commit -m "..."; git push`. Внутри SSH-строки (одинарные кавычки) используйте `&&` для bash.

> [!WARNING]
> На сервере часто появляются коммиты от `Freesport Sync Bot`. Поэтому **ВСЕГДА** используй `git reset --hard origin/main` вместо `git pull`, чтобы избежать ошибок слияния ("divergent branches").

> [!IMPORTANT]
> После обновления фронтенда всегда проверяй доступность сайта. Из-за особенностей Docker иногда требуется `restart nginx`, если upstream перестал отвечать.

## Экранирование и сложные команды через SSH

При выполнении команд из PowerShell через SSH строка проходит 3 уровня интерпретации. Основное правило:

- **Одинарные кавычки `'...'`** на уровне PowerShell — bash получает строку как есть.
- **Двойные кавычки `"..."`** на уровне PowerShell — PowerShell интерпретирует переменные.

### Правильный шаблон

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml ps'
```

### Команды с переменными bash

Экранируйте `$` через `\$` внутри двойных кавычек:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend sh -c "echo \$HOME"'
```

### Сложные скрипты: here-document (рекомендуется)

Для Python-скриптов, curl с переменными или многострочных команд:

```powershell
ssh root@5.35.124.149 'cat > /tmp/deploy_check.py << "EOF"
import urllib.request
r = urllib.request.urlopen("http://localhost:8000/api/v1/health/")
print(r.status, len(r.read()))
EOF
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python /tmp/deploy_check.py'
```

Удалите временный файл после выполнения:

```powershell
ssh root@5.35.124.149 'rm /tmp/deploy_check.py'
```

### Логи без обрезки

Docker обрезает длинные строки. Для полных логов:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 --no-trunc backend 2>&1 | cat'
```

## Команды для проверки (Post-deployment)

```powershell
# Проверить статус контейнеров
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml ps'

# Проверить логи бэкенда
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 backend'

# Проверить логи nginx
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 nginx'

# Проверить логи фронтенда
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 frontend'
```
