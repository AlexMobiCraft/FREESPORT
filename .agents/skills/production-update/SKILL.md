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

## Основной путь: релиз через deploy.yml

Релиз — это fast-forward `develop` → `main`, и выполняется он только по команде владельца:
`git push origin origin/develop:refs/heads/main`. Push запускает `deploy.yml` (сборка образов →
approval на environment `production` → SSH-деплой) и `sync-to-public.yml`, который обновляет
публичный `FREESPORT-B2B` без конфиденциальных файлов. Не делай merge в локальный `main`: это ломает fast-forward.
Откат: `gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>`.

Ручные сценарии ниже нужны, когда `deploy.yml` недоступен, и для точечных операций на сервере.

> [!DANGER]
> Не пушь в remote `production` (FREESPORT-B2B) вручную: `git push production main` выкладывает полную историю и конфиденциальные файлы (.env, .mcp.json, CLAUDE.md, \_bmad/, scripts/ и др.) в публичный репозиторий. Публичный репозиторий обновляет только `sync-to-public.yml`. Так уже случилось 2026-04-12, понадобился emergency sync.

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

# 4. Очистка старых образов (dangling <none> после пересборки)
docker image prune -f
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
docker image prune -f
```

### 4. Обновление только фронтенда (Frontend Only)

```bash
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml up -d --build frontend
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py migrate
docker image prune -f
```

`migrate` здесь нужен: feature-ветки часто несут backend-миграции (см. «Важные замечания»).

## Важные замечания

> [!WARNING]
> На сервере появляются коммиты от `Freesport Sync Bot`, поэтому код обновляй через `git reset --hard origin/main`, а не `git pull`: иначе получишь "divergent branches".

> [!DANGER]
> **При любом деплое проверяй `showmigrations` и запускай `migrate`, даже если кажется, что backend не менялся.** Feature-ветки часто содержат миграции в backend-коде, которые легко пропустить при «фронтенд-only» деплое. Неприменённая миграция приводит к 500-м ошибкам API (`column ... does not exist`) и недоступности данных для frontend. Инцидент 2026-08-23: деплой feature-ветки с миграцией `banners.0007_banner_ad_disclosure` без `migrate` сломал `/api/v1/banners/`.
>
> **Обязательный шаг после `git reset --hard origin/main` и перед/после пересборки контейнеров:**
> ```bash
> # Проверить статус миграций
> cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py showmigrations | grep -E "\[ \]"
> # Применить миграции (даже если предыдущая команда ничего не вывела — запусти для надёжности)
> cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py migrate
> ```

> [!IMPORTANT]
> После обновления фронтенда всегда проверяй доступность сайта. Из-за особенностей Docker иногда требуется `restart nginx`, если upstream перестал отвечать.

> [!IMPORTANT]
> После **каждой** пересборки (`up -d --build`) выполняй `docker image prune -f` — иначе старые `<none>`-образы копятся и забивают диск (~2GB на каждый frontend-образ). Инцидент 2026-09-18: диск заполнен на 94%, накопилось ~90 старых образов и 41GB build cache. При нехватке места дополнительно: `docker builder prune -f` (кэш сборки) и `journalctl --vacuum-size=500M` (логи journald).

## Экранирование и сложные команды через SSH

Кавычки на трёх уровнях (PowerShell → SSH → bash), here-document для скриптов и логи без обрезки описаны в навыке `production-server-ssh`, раздел «Экранирование кавычек и сложные команды».

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
