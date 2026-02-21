---
name: production-update
description: Используй этот навык для автоматизации развертывания обновлений на продакшен-сервере FREESPORT. Активируй при запросах "обнови сервер", "deploy to production", "выполни деплой", "быстрый фикс на проде", "обнови фронтенд/бекенд на сервере".
---

# Production Update Skill

Этот навык предназначен для управления процессом обновления проекта FREESPORT на продакшен-сервере через SSH.

## Параметры среды
*   **Host:** `5.35.124.149`
*   **User:** `root`
*   **Project Path:** `/home/freesport/freesport/`
*   **Production Repo:** `https://github.com/AlexMobiCraft/FREESPORT-B2B.git`
*   **Compose File:** `docker/docker-compose.prod.yml`
*   **Env File:** `.env.prod`

## Общий алгоритм (Локальная подготовка)
Перед обновлением сервера необходимо убедиться, что код запушен в правильный репозиторий:
1.  Проверь текущую ветку и наличие изменений (`git status`).
2.  Запуш изменения в `develop`: `git push origin develop`.
3.  Перелей в `main` (локально или через PR): `git checkout main; git merge develop --no-edit; git push origin main`.
4.  **ВАЖНО:** Если сервер использует `FREESPORT-B2B`, убедись, что `main` запушен именно туда (`git push production main`).

## Общий алгоритм (Обновление на сервере)
1.  Подключись к серверу по SSH (используй навык `production-server-ssh`).
2.  Перейди в папку проекта: `cd /home/freesport/freesport/`.
3.  **Принудительно** обнови код (чтобы избежать конфликтов с коммитами `Freesport Sync Bot`):
    ```bash
    git fetch origin main
    git reset --hard origin/main
    ```

## Сценарии обновления

### 1. Полное обновление (Full Update)
Используй, когда изменились зависимости (`requirements.txt`, `package.json`), Docker-конфигурация или требуются масштабные изменения.
```bash
# 1. Сборка и запуск всех контейнеров
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build

# 2. Миграции БД
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# 3. Сборка статики
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --no-input
```

### 2. Быстрый фикс (Quick Fix)
Используй для обновления логики (Python/JS код), если не менялись зависимости и структура контейнеров.
```bash
# Перезапуск основных сервисов
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend frontend
```
> [!NOTE]
> Если изменения во фронтенде требуют пересборки статики (Next.js build), используй сценарий "Обновление фронтенда" (с флагом `--build`).

### 3. Обновление только бекенда (Backend Only)
```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
```

### 4. Обновление только фронтенда (Frontend Only)
```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend
```

## Важные замечания
> [!DANGER]
> **PowerShell vs Bash:** На Windows используй `;` для разделения команд вместо `&&`. Пример: `git add .; git commit -m "..."; git push`.

> [!WARNING]
> На сервере часто появляются коммиты от `Freesport Sync Bot`. Поэтому **ВСЕГДА** используй `git reset --hard origin/main` вместо `git pull`, чтобы избежать ошибок слияния ("divergent branches").

> [!IMPORTANT]
> После обновления фронтенда всегда проверяй доступность сайта. Из-за особенностей Docker иногда требуется `restart nginx`, если upstream перестал отвечать.

## Команды для проверки (Post-deployment)
*   `docker compose -f ... ps` — проверить статус контейнеров.
*   `docker compose -f ... logs --tail=50 backend` — проверить логи.
