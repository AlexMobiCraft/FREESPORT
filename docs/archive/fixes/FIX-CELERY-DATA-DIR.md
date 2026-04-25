# Исправление: Celery worker не видит данные 1С

## Проблема

Celery worker выдавал ошибку при попытке импорта:

```
CommandError: Отсутствует обязательная поддиректория: goods
```

## Причина

В конфигурации Docker Compose для Celery worker отсутствовали:

1. ❌ Переменная окружения `ONEC_DATA_DIR`
2. ❌ Volume mount с данными 1С (`../data:/app/data`)

## Решение

### Изменены файлы

1. **`docker/docker-compose.yml`** (локальная разработка)
   - Добавлен volume: `- ../data:/app/data`
   - Добавлена переменная: `- ONEC_DATA_DIR=/app/data/import_1c`

2. **`docker/docker-compose.prod.yml`** (продакшн)
   - Добавлен volume: `- ${ONEC_DATA_DIR:-../data/import_1c}:/app/data/import_1c`
   - Добавлена переменная: `- ONEC_DATA_DIR=${ONEC_DATA_DIR:-/app/data/import_1c}`

## Инструкции для применения

### Локальная разработка

```powershell
# Остановить контейнеры
cd c:\Users\38670\DEV_WEB\FREESPORT
docker-compose -f docker/docker-compose.yml down

# Пересобрать и запустить
docker-compose -f docker/docker-compose.yml up -d --build celery

# Проверить логи
docker-compose -f docker/docker-compose.yml logs -f celery
```

### Продакшн сервер

**ВАЖНО:** Выполнять на сервере `5.35.124.149`

```bash
# Подключиться к серверу
ssh root@5.35.124.149

# Перейти в директорию проекта
cd /root/freesport

# Убедиться, что директория с данными 1С существует
mkdir -p /root/freesport/data/import_1c

# Остановить Celery worker
docker-compose -f docker/docker-compose.prod.yml stop celery

# Пересобрать образ (если нужно)
docker-compose -f docker/docker-compose.prod.yml build backend

# Запустить Celery worker с новой конфигурацией
docker-compose -f docker/docker-compose.prod.yml up -d celery

# Проверить логи
docker-compose -f docker/docker-compose.prod.yml logs -f celery
```

### Проверка переменной окружения

```bash
# Проверить, что ONEC_DATA_DIR установлена
docker exec freesport-celery-worker env | grep ONEC_DATA_DIR

# Должно вывести:
# ONEC_DATA_DIR=/app/data/import_1c

# Проверить, что директория существует
docker exec freesport-celery-worker ls -la /app/data/import_1c
```

## Структура данных 1С

Убедитесь, что в директории `data/import_1c` присутствуют поддиректории:

```
data/import_1c/
├── goods/          # Товары
├── offers/         # Предложения
├── prices/         # Цены
├── rests/          # Остатки
├── priceLists/     # Типы цен
└── contragents/    # Клиенты
```

## Тестирование

После применения исправлений:

1. Откройте админ-панель: `http://localhost:8001/admin` (локально) или `https://5.35.124.149/admin` (продакшн)
2. Перейдите в "Интеграции" → "Сессии импорта"
3. Запустите импорт через action "🚀 Запустить импорт из 1С"
4. Выберите "Каталог товаров" и нажмите "▶️ Запустить импорт"
5. Проверьте логи Celery - не должно быть ошибки "Отсутствует обязательная поддиректория"

## Откат (если потребуется)

```bash
# Вернуться к предыдущей версии docker-compose
git checkout HEAD~1 docker/docker-compose.yml docker/docker-compose.prod.yml

# Перезапустить контейнеры
docker-compose -f docker/docker-compose.yml restart celery
```

## Связанные файлы

- ✅ `docker/docker-compose.yml` - обновлен
- ✅ `docker/docker-compose.prod.yml` - обновлен
- 📄 `backend/freesport/settings/base.py` - определение ONEC_DATA_DIR (без изменений)
- 📄 `backend/apps/integrations/tasks.py` - использует ONEC_DATA_DIR (без изменений)
