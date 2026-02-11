---
name: production-server-ssh
description: Используй этот навык для быстрого подключения к продакшен-серверу FREESPORT по SSH и выполнения критических команд (просмотр логов, перезапуск и пересборка контейнеров, работа с nginx, проверка статуса Celery).
---

# Production Server SSH Skill

Этот навык предоставляет инструкции и параметры для безопасного подключения к продакшен-серверу проекта FREESPORT.

## Параметры подключения

*   **Host:** `5.35.124.149`
*   **User:** `root`
*   **Password:** `0301`
*   **Project Path:** `/home/freesport/freesport/`

## Команды подключения

### Из PowerShell (Windows)
```powershell
ssh root@5.35.124.149
```
*После ввода команды используй пароль `0301`.*

### Автоматизированное подключение (через существующий скрипт)
```powershell
pwsh ./scripts/server/ssh_server.ps1
```

## Основные команды на сервере

После подключения (в директории `/home/freesport/freesport/`):

### Просмотр логов
```bash
# Логи бэкенда в реальном времени
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs -f backend

# Логи nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml logs -f nginx
```

### Управление сервисами и пересборка
```bash
# Перезапуск Nginx
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml restart nginx

# Обновление и пересборка фронтенда
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend

# Обновление и пересборка бэкенда (с миграциями)
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# Полная пересборка и запуск проекта
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build
```

## Обновление проекта (CI/CD вручную)

Если нужно подтянуть свежий код из репозитория и обновить проект:

```bash
# 1. Зайти в папку проекта
cd /home/freesport/freesport/

# 2. Подтянуть изменения
git pull origin main

# 3. Применить миграции (если были изменения в моделях)
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# 4. Пересобрать нужные контейнеры
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend frontend
```

### Работа с базой данных
```bash
# Просмотр статуса миграций
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py showmigrations

# Создание суперпользователя
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

> [!WARNING]
> Будь крайне осторожен при выполнении команд на продакшен-сервере. Всегда проверяй флаги и пути перед выполнением команд удаления или сброса данных.
