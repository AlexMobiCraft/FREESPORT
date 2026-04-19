# Примеры использования навыка backend-local-update

## Пример 1: Пользователь просит обновить бекенд после git pull
**Запрос:** "Я стянул изменения из гита, обнови теперь локальный бекенд"
**Действие:**
1. Выполнить `docker compose --env-file .env -f docker/docker-compose.yml up -d --build backend`
2. После успешного завершения выполнить `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate`
3. Затем `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input`

## Пример 2: Только миграции
**Запрос:** "Примени миграции в докере"
**Действие:**
1. Выполнить `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate`

## Пример 3: Пересборка при ошибке зависимостей
**Запрос:** "Кажется, не хватает библиотеки в контейнере, пересобери его"
**Действие:**
1. Выполнить `docker compose --env-file .env -f docker/docker-compose.yml up -d --build backend`
