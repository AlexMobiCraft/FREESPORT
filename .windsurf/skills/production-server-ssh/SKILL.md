---
name: production-server-ssh
description: Используй этот навык для быстрого подключения к продакшен-серверу FREESPORT по SSH и выполнения критических команд (просмотр логов, перезапуск и пересборка контейнеров, работа с nginx, проверка статуса Celery).
---

# Production Server SSH Skill

Этот навык предоставляет инструкции и параметры для безопасного подключения к продакшен-серверу проекта FREESPORT.

## Параметры подключения

- **Host:** `5.35.124.149`
- **User:** `root`
- **Project Path:** `/home/freesport/freesport/`
- **Аутентификация:** SSH ключ

## Команды подключения

### Из PowerShell (Windows)

```powershell
ssh root@5.35.124.149
```

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

# 2. Подтянуть изменения (принудительно, во избежание конфликтов)
git fetch origin main
git reset --hard origin/main

# 3. Применить миграции (если были изменения в моделях)
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec backend python manage.py migrate

# 4. Пересобрать нужные контейнеры
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build backend frontend
```

## Экранирование кавычек и сложные команды (PowerShell → SSH → bash)

При выполнении команд через SSH из PowerShell строка проходит 3 уровня интерпретации. Основное правило:

- **Одинарные кавычки `'...'`** на уровне PowerShell — bash получает строку как есть.
- **Двойные кавычки `"..."`** на уровне PowerShell — PowerShell интерпретирует переменные и подстановки.

### Правильный шаблон (простые команды)

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=30 backend'
```

### Команды с переменными bash

Используйте двойные кавычки внутри одинарных, экранируя `$` через `\$`:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend sh -c "echo \$HOME"'
```

### Сложные команды: временный скрипт (here-document)

Для Python-скриптов, `curl` с переменными или многострочных команд — создавайте временный файл:

```powershell
ssh root@5.35.124.149 'cat > /tmp/check_api.py << "EOF"
import urllib.request
r = urllib.request.urlopen("http://localhost:8000/api/v1/brands/")
print(r.status, len(r.read()))
EOF
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python /tmp/check_api.py'
```

После выполнения удалите временный файл:

```powershell
ssh root@5.35.124.149 'rm /tmp/check_api.py'
```

### Важные замечания по docker compose

- **Рабочая директория:** `docker compose exec` ищет `.env.prod` относительно **текущей директории**. Всегда делайте `cd /home/freesport/freesport &&` перед командой.
- **Абсолютный путь:** используйте `--env-file /home/freesport/freesport/.env.prod` для надёжности, даже если `cd` выполнен.
- **Разделитель команд в PowerShell:** используйте `;` вместо `&&` для разделения команд PowerShell, а `&&` — уже внутри строки, передаваемой SSH.

### Логи без обрезки

Docker обрезает длинные строки. Для полных логов:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 --no-trunc backend 2>&1 | cat'
```

### Работа с базой данных

```bash
# Просмотр статуса миграций
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec backend python manage.py showmigrations

# Создание суперпользователя
docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser
```

> [!WARNING]
> Будь крайне осторожен при выполнении команд на продакшен-сервере. Всегда проверяй флаги и пути перед выполнением команд удаления или сброса данных.
