#!/bin/bash

# Скрипт автоматического развертывания FREESPORT Platform
# Использование: ./scripts/deploy/deploy.sh [init|update|backup]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия необходимых утилит
check_requirements() {
    log_info "Проверка системных требований..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен. Пожалуйста, установите Docker."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose не установлен. Пожалуйста, установите Docker Compose."
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git не установлен. Пожалуйста, установите Git."
        exit 1
    fi
    
    log_info "Все требования выполнены."
}

# Инициализация проекта
init_project() {
    log_info "Инициализация проекта..."
    
    # Проверка наличия файла .env.prod
    if [ ! -f .env.prod ]; then
        log_warn "Файл .env.prod не найден. Создание из шаблона..."
        cp .env.prod.example .env.prod
        log_warn "Пожалуйста, отредактируйте файл .env.prod и установите реальные значения."
        log_warn "Особенно обратите внимание на SECRET_KEY, пароли и доменные имена."
        read -p "Нажмите Enter после редактирования .env.prod..."
    fi
    
    # Создание необходимых директорий
    log_info "Создание директорий..."
    mkdir -p data/import_1c
    mkdir -p logs/{nginx,backend,frontend}
    mkdir -p docker/ssl
    
    # Сборка и запуск контейнеров
    log_info "Сборка Docker образов..."
    docker compose -f docker/docker-compose.prod.yml build
    
    log_info "Запуск контейнеров..."
    docker compose -f docker/docker-compose.prod.yml up -d
    
    # Ожидание запуска базы данных
    log_info "Ожидание запуска базы данных..."
    sleep 30
    
    # Выполнение миграций
    log_info "Выполнение миграций базы данных..."
    docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py migrate
    
    # Создание суперпользователя
    log_info "Создание суперпользователя..."
    docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py createsuperuser || log_warn "Не удалось создать суперпользователя. Вы можете сделать это позже с помощью команды: docker compose -f docker/docker-compose.prod.yml exec backend python manage.py createsuperuser"
    
    # Сбор статических файлов
    log_info "Сбор статических файлов..."
    docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
    
    log_info "Инициализация завершена!"
    log_info "Проверьте работу сайта по адресу: https://freesport.ru"
}

# Обновление проекта
update_project() {
    log_info "Обновление проекта..."
    
    # Скачивание последних изменений
    log_info "Скачивание последних изменений из репозитория..."
    git pull origin main
    
    # Создание резервной копии
    log_info "Создание резервной копии..."
    backup_project
    
    # Пересборка и перезапуск контейнеров
    log_info "Пересборка Docker образов..."
    docker compose -f docker/docker-compose.prod.yml build
    
    log_info "Перезапуск контейнеров..."
    docker compose -f docker/docker-compose.prod.yml up -d
    
    # Ожидание запуска сервисов
    log_info "Ожидание запуска сервисов..."
    sleep 30
    
    # Выполнение миграций
    log_info "Выполнение миграций базы данных..."
    docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py migrate
    
    # Сбор статических файлов
    log_info "Сбор статических файлов..."
    docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
    
    log_info "Обновление завершено!"
}

# Создание резервной копии
backup_project() {
    log_info "Создание резервной копии..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Резервное копирование базы данных
    log_info "Резервное копирование базы данных..."
    docker compose -f docker/docker-compose.prod.yml exec -T db pg_dump -U postgres freesport > "$BACKUP_DIR/database.sql"
    
    # Резервное копирование медиа файлов
    log_info "Резервное копирование медиа файлов..."
    tar -czf "$BACKUP_DIR/media.tar.gz" data/ || log_warn "Не удалось создать архив медиа файлов"
    
    # Резервное копирование конфигурации
    log_info "Резервное копирование конфигурации..."
    cp .env.prod "$BACKUP_DIR/"
    
    log_info "Резервная копия создана в директории: $BACKUP_DIR"
}

# Восстановление из резервной копии
restore_project() {
    if [ -z "$1" ]; then
        log_error "Укажите директорию резервной копии. Использование: $0 restore /path/to/backup"
        exit 1
    fi
    
    BACKUP_DIR="$1"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Директория резервной копии не найдена: $BACKUP_DIR"
        exit 1
    fi
    
    log_info "Восстановление из резервной копии: $BACKUP_DIR"
    
    # Остановка контейнеров
    log_info "Остановка контейнеров..."
    docker compose -f docker/docker-compose.prod.yml down
    
    # Восстановление конфигурации
    if [ -f "$BACKUP_DIR/.env.prod" ]; then
        log_info "Восстановление конфигурации..."
        cp "$BACKUP_DIR/.env.prod" .env.prod
    fi
    
    # Запуск контейнеров
    log_info "Запуск контейнеров..."
    docker compose -f docker/docker-compose.prod.yml up -d
    
    # Ожидание запуска базы данных
    log_info "Ожидание запуска базы данных..."
    sleep 30
    
    # Восстановление базы данных
    if [ -f "$BACKUP_DIR/database.sql" ]; then
        log_info "Восстановление базы данных..."
        docker compose -f docker/docker-compose.prod.yml exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS freesport;"
        docker compose -f docker/docker-compose.prod.yml exec -T db psql -U postgres -c "CREATE DATABASE freesport;"
        docker compose -f docker/docker-compose.prod.yml exec -T db psql -U postgres freesport < "$BACKUP_DIR/database.sql"
    fi
    
    # Восстановление медиа файлов
    if [ -f "$BACKUP_DIR/media.tar.gz" ]; then
        log_info "Восстановление медиа файлов..."
        tar -xzf "$BACKUP_DIR/media.tar.gz"
    fi
    
    log_info "Восстановление завершено!"
}

# Проверка статуса
check_status() {
    log_info "Проверка статуса сервисов..."
    
    # Проверка статуса контейнеров
    docker compose -f docker/docker-compose.prod.yml ps
    
    # Проверка доступности сайта
    if command -v curl &> /dev/null; then
        log_info "Проверка доступности сайта..."
        if curl -f -s https://freesport.ru > /dev/null; then
            log_info "Сайт доступен"
        else
            log_warn "Сайт недоступен"
        fi
        
        # Проверка работы API
        log_info "Проверка работы API..."
        if curl -f -s https://freesport.ru/api/v1/health/ > /dev/null; then
            log_info "API доступен"
        else
            log_warn "API недоступен"
        fi
    fi
}

# Очистка
cleanup() {
    log_info "Очистка системы..."
    
    # Остановка контейнеров
    docker compose -f docker/docker-compose.prod.yml down
    
    # Удаление неиспользуемых образов
    docker image prune -f
    
    # Удаление неиспользуемых томов
    docker volume prune -f
    
    log_info "Очистка завершена!"
}

# Показать справку
show_help() {
    echo "Использование: $0 [КОМАНДА]"
    echo ""
    echo "Команды:"
    echo "  init     - Инициализация проекта"
    echo "  update   - Обновление проекта"
    echo "  backup   - Создание резервной копии"
    echo "  restore  - Восстановление из резервной копии"
    echo "  status   - Проверка статуса сервисов"
    echo "  cleanup  - Очистка системы"
    echo "  help     - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 init"
    echo "  $0 update"
    echo "  $0 restore backups/20231201_120000"
}

# Основная логика
case "$1" in
    init)
        check_requirements
        init_project
        ;;
    update)
        check_requirements
        update_project
        ;;
    backup)
        check_requirements
        backup_project
        ;;
    restore)
        check_requirements
        restore_project "$2"
        ;;
    status)
        check_requirements
        check_status
        ;;
    cleanup)
        check_requirements
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac