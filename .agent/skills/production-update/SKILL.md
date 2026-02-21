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
*   **Compose File:** `docker/docker-compose.prod.yml`
*   **Env File:** `.env.prod`

## Общий алгоритм (Перед любым обновлением)
1. Подключись к серверу по SSH (используй навык `production-server-ssh` для деталей).
2. Перейди в папку проекта: `cd /home/freesport/freesport/`.
3. Подтяни свежий код: `git pull origin main`.

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
# Перезапуск основных сервисов (код подтягивается через волюмы или образы уже обновлены)
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart backend frontend nginx
```
> [!NOTE]
> Если изменения во фронтенде требуют пересборки статики (Next.js build), используй сценарий "Обновление фронтенда".

### 3. Обновление только бекенда (Backend Only)
```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
```

### 4. Обновление только фронтенда (Frontend Only)
```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx
```

### 5. Обслуживание (Migrations & Static)
```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py collectstatic --no-input
```

## Важные замечания
> [!WARNING]
> Перед выполнением `git pull` убедись, что на сервере нет несохраненных изменений, которые могут вызвать конфликт.

> [!IMPORTANT]
> После обновления фронтенда всегда проверяй доступность сайта. Из-за особенностей Docker иногда требуется `restart nginx`, если upstream перестал отвечать.

## Команды для проверки (Post-deployment)
*   `docker compose -f ... ps` — проверить статус контейнеров.
*   `docker compose -f ... logs --tail=50 backend` — проверить логи на наличие ошибок запуска.
