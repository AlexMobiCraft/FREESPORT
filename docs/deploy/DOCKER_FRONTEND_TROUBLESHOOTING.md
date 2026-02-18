# Устранение неполадок Frontend в Docker

## Проблема: Module not found (модуль не найден)

### Симптомы

Ошибка в браузере или консоли:
```
Module not found: Can't resolve 'embla-carousel-autoplay'
```

### Причина

Docker-контейнер `freesport-frontend` использует **именованный том** для `node_modules`:

```yaml
volumes:
  - ../frontend:/app
  - frontend_node_modules:/app/node_modules  # Именованный том!
```

Это означает, что:
- Локальный `node_modules` **не синхронизирован** с контейнером
- При добавлении новой зависимости в `package.json` она не появляется в контейнере автоматически
- `npm install` должен выполняться **внутри контейнера** или том нужно пересоздать

### Решение 1: Пересоздание тома node_modules (рекомендуется)

```bash
# 1. Остановить и удалить контейнер frontend
docker compose --env-file .env -f docker/docker-compose.yml stop frontend
docker compose --env-file .env -f docker/docker-compose.yml rm -f frontend

# 2. Удалить устаревший том
docker volume rm docker_frontend_node_modules

# 3. Пересоздать контейнер (том создастся автоматически)
docker compose --env-file .env -f docker/docker-compose.yml up -d frontend
```

### Решение 2: Установка зависимостей внутри контейнера

```bash
# Войти в контейнер
docker compose --env-file .env -f docker/docker-compose.yml exec frontend sh

# Установить зависимости
npm install

# Выйти из контейнера
exit
```

### Решение 3: Полная пересборка образа

```bash
# Пересборка с очисткой кэша
docker compose --env-file .env -f docker/docker-compose.yml build --no-cache frontend

# Перезапуск
docker compose --env-file .env -f docker/docker-compose.yml up -d frontend
```

---

## Проблема: ECONNREFUSED (backend недоступен)

### Симптомы

```
Error: connect ECONNREFUSED 172.18.0.8:8000
```

### Причина

Backend-контейнер ещё не полностью запущен (статус `health: starting`).

### Решение

Подождать 30-60 секунд или проверить статус:

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

Backend должен иметь статус `healthy`.

---

## Полезные команды

### Просмотр логов

```bash
# Логи frontend
docker compose --env-file .env -f docker/docker-compose.yml logs frontend --tail 100

# Логи в реальном времени
docker compose --env-file .env -f docker/docker-compose.yml logs frontend -f
```

### Проверка статуса контейнеров

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

### Вход в контейнер frontend

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec frontend sh
```

### Проверка установленных пакетов в контейнере

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec frontend npm list embla-carousel-autoplay
```

### Полный перезапуск всех сервисов

```bash
docker compose --env-file .env -f docker/docker-compose.yml down
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

---

## Профилактика

### После добавления новой зависимости

При добавлении новой зависимости в `package.json`:

1. **Вариант A:** Выполнить `npm install` внутри контейнера
2. **Вариант B:** Пересоздать том `frontend_node_modules`

### После обновления зависимостей локально

Если зависимости были обновлены локально (`npm install` в папке `frontend/`):

```bash
# Пересоздать том для синхронизации
docker compose --env-file .env -f docker/docker-compose.yml stop frontend
docker volume rm docker_frontend_node_modules
docker compose --env-file .env -f docker/docker-compose.yml up -d frontend
```

---

## Структура томов Docker

| Том | Описание |
|-----|----------|
| `docker_frontend_node_modules` | Зависимости npm для frontend |
| `postgres_data` | Данные PostgreSQL |
| `redis_data` | Данные Redis |
| `backend_media` | Загруженные файлы |
| `backend_static` | Статические файлы Django |

---

## Ссылки

- [Локальная установка Docker](./LOCAL_DOCKER_SETUP.md)
- [Docker Compose конфигурация](../../docker/docker-compose.yml)
