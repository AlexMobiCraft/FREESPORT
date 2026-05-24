#!/bin/bash

# Скрипт для развертывания проекта FREESPORT на сервере.
# Запускается непосредственно на сервере в директории проекта.
#
# Использование:
#   ./scripts/deploy/deploy.sh
#   ./scripts/deploy/deploy.sh develop
#   BRANCH=feature/x ./scripts/deploy/deploy.sh

# --- Конфигурация ---
# Ветка Git по умолчанию
DEFAULT_BRANCH="develop"
# Файл для сборки образов
COMPOSE_BUILD_FILE="docker/docker-compose.build.yml"
# Файл для запуска контейнеров
COMPOSE_PROD_FILE="docker/docker-compose.prod.yml"
# Файл с переменными окружения
ENV_FILE=".env.prod"

# --- Функции ---
# Вывод сообщений
log() {
  echo "--- $1 ---"
}

# --- Логика скрипта ---
set -e # Прерывать выполнение при любой ошибке

# 1. Определение ветки
if [ -z "$1" ]; then
    BRANCH=$DEFAULT_BRANCH
else
    BRANCH=$1
fi
log "Используется ветка: $BRANCH"

# 2. Проверка файла .env
if [ ! -f "$ENV_FILE" ]; then
    log "Файл окружения '$ENV_FILE' не найден. Пожалуйста, создайте его."
    exit 1
fi
log "Используется файл окружения: $ENV_FILE"

# 3. Обновление из Git
log "Обновление кода из Git (ветка $BRANCH)..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
log "Код успешно обновлен."

# 3.5. Настройка прав доступа (Fix for PermissionError)
log "Настройка прав доступа к директориям данных..."
# Создаем директории, если они не существуют
DATA_DIRS=(
    data/prod/static
    data/prod/media
    data/prod/onec_private
    data/prod/onec_private/1c_temp
    data/prod/onec_private/1c_import
    backend/logs
)

# Устанавливаем владельца 1000:1000 (пользователь внутри контейнера)
# Используем sudo, так как скрипт может быть запущен от пользователя freesport
if command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p "${DATA_DIRS[@]}"
    sudo chown -R 1000:1000 "${DATA_DIRS[@]}"
    sudo chmod -R u+rwX,g+rwX "${DATA_DIRS[@]}"
else
    # Если sudo нет (например, запущен от root), выполняем напрямую
    mkdir -p "${DATA_DIRS[@]}"
    chown -R 1000:1000 "${DATA_DIRS[@]}"
    chmod -R u+rwX,g+rwX "${DATA_DIRS[@]}"
fi
log "Права доступа настроены."

# 4. Сборка новых Docker образов
log "Сборка Docker образов из '$COMPOSE_BUILD_FILE'..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_BUILD_FILE" build --no-cache
log "Образы успешно собраны."

# 5. Остановка старых контейнеров и запуск новых
log "Перезапуск сервисов из '$COMPOSE_PROD_FILE'..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PROD_FILE" down -v
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PROD_FILE" up -d
log "Сервисы успешно перезапущены."

log "Проверка доступа backend к директориям обмена 1С..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PROD_FILE" exec -T backend sh -c 'test -w /app/var/onec/1c_temp && test -w /app/var/onec/1c_import && touch /app/var/onec/1c_temp/.deploy_write_test && rm -f /app/var/onec/1c_temp/.deploy_write_test'
log "Доступ backend к директориям обмена 1С подтвержден."

# 6. Выполнение миграций базы данных
log "Выполнение миграций Django..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PROD_FILE" exec -T backend python manage.py migrate --no-input
log "Миграции успешно выполнены."

# 7. Сбор статических файлов (опционально, но рекомендуется)
log "Сбор статических файлов Django..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_PROD_FILE" exec -T backend python manage.py collectstatic --no-input
log "Статические файлы собраны."

# 8. Очистка старых образов
log "Очистка неиспользуемых Docker образов..."
docker image prune -f
log "Очистка завершена."

log "Развертывание успешно завершено!"
