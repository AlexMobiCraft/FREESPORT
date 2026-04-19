---
name: backend-local-update
description: Используй этот навык для остановки, пересборки и запуска бекенд-контейнера на локальной машине, а также для выполнения миграций и сборки статики. Активируй при запросах "обнови бекенд", "пересобери docker", "выполни миграции".
---

# Backend Local Update Skill

Этот навык автоматизирует рутинные задачи по обслуживанию локального Docker-окружения бэкенда.

## ⚠️ Важное примечание
Все команды должны выполняться из корня проекта. Команды используют флаг `--env-file .env` и путь к файлу конфигурации `docker/docker-compose.yml`.

## Основные команды

### 1. Пересборка и перезапуск бекенда
Используй, если изменились зависимости (`requirements.txt`), `Dockerfile` или нужно гарантированно сбросить состояние контейнера.

```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d --build backend
```

### 2. Применение миграций базы данных
Используй после изменения моделей или при обновлении кода из репозитория.

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate
```

### 3. Сбор статических файлов
Используй, если были внесены изменения в админку Django или статические ассеты бэкенда.

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input
```

## Рабочие процессы (Workflows)

### Сценарий "Полное обновление"
Если пользователь просит "полностью обновить бекенд" или "синхронизировать локалку после git pull", выполняй команды последовательно:

1.  **Пересборка**: `docker compose --env-file .env -f docker/docker-compose.yml up -d --build backend`
2.  **Миграции**: `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate`
3.  **Статика**: `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input`

### Сценарий "Быстрый фикс"
Если нужно просто применить миграцию без перезапуска:
1.  **Миграции**: `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate`

## Устранение неполадок
- Если контейнер не запускается после пересборки, проверь логи:
  `docker compose --env-file .env -f docker/docker-compose.yml logs backend`
- Если возникают ошибки прав доступа при `collectstatic`, убедись, что Docker запущен с правами администратора (на Windows).
