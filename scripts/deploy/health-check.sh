#!/bin/bash

# Скрипт комплексной проверки работоспособности FREESPORT Platform
# Использование: ./scripts/deploy/health-check.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

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

# Функция проверки сервиса
check_service() {
    local service=$1
    local command=$2
    
    echo -n "Проверка $service... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка статуса контейнеров
check_containers() {
    log_info "Проверка статуса контейнеров..."
    
    # Проверка, что все контейнеры запущены
    local running_containers=$(docker compose -f docker/docker-compose.prod.yml ps -q | wc -l)
    local total_containers=$(docker compose -f docker/docker-compose.prod.yml config | grep -c "^[[:space:]]*[a-zA-Z0-9_-]*:")
    
    if [ "$running_containers" -eq "$total_containers" ]; then
        log_info "Все контейнеры запущены ($running_containers/$total_containers)"
    else
        log_error "Не все контейнеры запущены ($running_containers/$total_containers)"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка базы данных
check_database() {
    log_info "Проверка базы данных PostgreSQL..."
    
    # Проверка подключения к PostgreSQL
    if docker compose -f docker/docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log_info "PostgreSQL доступен"
        
        # Проверка наличия таблиц
        local tables_count=$(docker compose -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        if [ "$tables_count" -gt 0 ]; then
            log_info "База данных содержит таблицы: $tables_count"
        else
            log_warn "База данных не содержит таблиц или недоступна"
        fi
    else
        log_error "PostgreSQL недоступен"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка Redis
check_redis() {
    log_info "Проверка Redis..."
    
    # Проверка подключения к Redis
    if docker compose -f docker/docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis доступен"
        
        # Проверка использования памяти
        local redis_info=$(docker compose -f docker/docker-compose.prod.yml exec -T redis redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        log_info "Использование памяти Redis: $redis_info"
    else
        log_error "Redis недоступен"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка Django Backend
check_django() {
    log_info "Проверка Django Backend..."
    
    # Проверка здоровья Django
    if docker compose -f docker/docker-compose.prod.yml exec -T backend python manage.py check --deploy > /dev/null 2>&1; then
        log_info "Django backend корректно настроен"
    else
        log_error "Проблемы с конфигурацией Django"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Проверка доступности API
    check_service "API Endpoint" "curl -f -s http://localhost:8001/api/v1/health/"
}

# Проверка Frontend
check_frontend() {
    log_info "Проверка Frontend..."
    
    # Проверка здоровья frontend
    if curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
        log_info "Frontend доступен"
    else
        log_error "Frontend недоступен"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка Nginx
check_nginx() {
    log_info "Проверка Nginx..."
    
    # Проверка конфигурации Nginx
    if docker compose -f docker/docker-compose.prod.yml exec -T nginx nginx -t > /dev/null 2>&1; then
        log_info "Конфигурация Nginx корректна"
    else
        log_error "Проблемы с конфигурацией Nginx"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Проверка доступности сайта через Nginx
    if curl -f -s http://localhost/ > /dev/null 2>&1; then
        log_info "Сайт доступен через Nginx"
    else
        log_error "Сайт недоступен через Nginx"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка Celery
check_celery() {
    log_info "Проверка Celery..."
    
    # Проверка статуса Celery worker
    if docker compose -f docker/docker-compose.prod.yml exec -T celery celery -A freesport inspect active > /dev/null 2>&1; then
        log_info "Celery worker работает"
    else
        log_error "Celery worker недоступен"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Проверка статуса Celery beat
    local beat_logs=$(docker compose -f docker/docker-compose.prod.yml logs celery-beat 2>/dev/null | tail -10)
    if echo "$beat_logs" | grep -q "Scheduler"; then
        log_info "Celery beat работает"
    else
        log_warn "Возможны проблемы с Celery beat"
    fi
}

# Проверка дискового пространства
check_disk_space() {
    log_info "Проверка дискового пространства..."
    
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        log_info "Дисковое пространство: ${disk_usage}% использовано"
    elif [ "$disk_usage" -lt 90 ]; then
        log_warn "Дисковое пространство: ${disk_usage}% использовано (рекомендуется очистка)"
    else
        log_error "Дисковое пространство: ${disk_usage}% использовано (требуется немедленная очистка)"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка использования памяти
check_memory() {
    log_info "Проверка использования памяти..."
    
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -lt 80 ]; then
        log_info "Память: ${memory_usage}% использовано"
    elif [ "$memory_usage" -lt 90 ]; then
        log_warn "Память: ${memory_usage}% использовано (рекомендуется оптимизация)"
    else
        log_error "Память: ${memory_usage}% использовано (требуется оптимизация)"
        ERRORS=$((ERRORS + 1))
    fi
}

# Проверка нагрузки на CPU
check_cpu() {
    log_info "Проверка нагрузки на CPU..."
    
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    
    # Сравнение нагрузки с количеством ядер
    if (( $(echo "$load_avg < $cpu_cores" | bc -l) )); then
        log_info "Нагрузка CPU: $load_avg (ядер: $cpu_cores)"
    else
        log_warn "Нагрузка CPU: $load_avg (ядер: $cpu_cores) - высокая нагрузка"
    fi
}

# Проверка SSL сертификата
check_ssl() {
    log_info "Проверка SSL сертификата..."
    
    if command -v curl &> /dev/null; then
        local ssl_expiry=$(curl -sI https://freesport.ru 2>/dev/null | grep -i "start date\|expire date" || echo "SSL не настроен")
        if [[ "$ssl_expiry" == *"SSL не настроен"* ]]; then
            log_warn "SSL сертификат не настроен"
        else
            log_info "SSL сертификат активен"
        fi
    else
        log_warn "curl недоступен для проверки SSL"
    fi
}

# Основная функция
main() {
    echo "========================================"
    echo "  Комплексная проверка работоспособности"
    echo "  FREESPORT Platform"
    echo "========================================"
    echo ""
    
    # Проверка наличия Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен"
        exit 1
    fi
    
    # Проверка наличия docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose не установлен"
        exit 1
    fi
    
    # Проверка наличия docker-compose.prod.yml
    if [ ! -f "docker/docker-compose.prod.yml" ]; then
        log_error "Файл docker/docker-compose.prod.yml не найден"
        exit 1
    fi
    
    # Выполнение проверок
    check_containers
    check_database
    check_redis
    check_django
    check_frontend
    check_nginx
    check_celery
    check_disk_space
    check_memory
    check_cpu
    check_ssl
    
    echo "========================================"
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}Все проверки пройдены успешно!${NC}"
        exit 0
    else
        echo -e "${RED}Обнаружено $ERRORS ошибок${NC}"
        exit 1
    fi
}

# Запуск основной функции
main "$@"