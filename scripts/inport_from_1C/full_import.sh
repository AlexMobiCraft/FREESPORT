#!/bin/bash
# =============================================================================
# FREESPORT: Полный импорт данных из 1С
# =============================================================================
# Использование:
#   ./full_import.sh                    # Полный импорт (с изображениями)
#   ./full_import.sh --dry-run          # Тестовый запуск
#   ./full_import.sh --skip-backup      # Без backup
#   ./full_import.sh --skip-images      # Без изображений
#   ./full_import.sh --images-only      # Только изображения (без каталога)
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DATA_DIR="/app/data/import_1c"
DOCKER_COMPOSE_FILE="docker/docker-compose.prod.yml"
ENV_FILE=".env.prod"

# Параметры по умолчанию
DRY_RUN=""
SKIP_BACKUP=""
SKIP_IMAGES=""
SKIP_CUSTOMERS=""
CLEAR_EXISTING=""
IMAGES_ONLY=""

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP="--skip-backup"
            shift
            ;;
        --skip-images)
            SKIP_IMAGES="--skip-images"
            shift
            ;;
        --skip-customers)
            SKIP_CUSTOMERS="true"
            shift
            ;;
        --clear-existing)
            CLEAR_EXISTING="--clear-existing"
            shift
            ;;
        --images-only)
            IMAGES_ONLY="true"
            shift
            ;;
        --help|-h)
            echo "Использование: $0 [опции]"
            echo ""
            echo "Опции:"
            echo "  --dry-run         Тестовый запуск без записи в БД"
            echo "  --skip-backup     Пропустить создание backup"
            echo "  --skip-images     Пропустить импорт изображений в каталоге"
            echo "  --images-only     Запустить ТОЛЬКО импорт изображений (без каталога)"
            echo "  --skip-customers  Пропустить импорт клиентов"
            echo "  --clear-existing  Очистить данные перед импортом (ОСТОРОЖНО!)"
            echo "  --help, -h        Показать эту справку"
            exit 0
            ;;
        *)
            echo -e "${RED}Неизвестный аргумент: $1${NC}"
            exit 1
            ;;
    esac
done

# Функции
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_django_command() {
    local cmd=$1
    log_info "Выполнение: python manage.py $cmd"
    docker compose --env-file $ENV_FILE -f $DOCKER_COMPOSE_FILE exec -T backend python manage.py $cmd
}

# =============================================================================
# Начало скрипта
# =============================================================================

echo ""
echo "============================================================"
echo -e "${GREEN}  FREESPORT: Полный импорт данных из 1С${NC}"
echo "============================================================"
echo ""

cd "$PROJECT_ROOT"

# Проверка файлов
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    log_error "Не найден $DOCKER_COMPOSE_FILE"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    log_error "Не найден $ENV_FILE"
    exit 1
fi

# Проверка работающих контейнеров
log_info "Проверка Docker контейнеров..."
if ! docker compose --env-file $ENV_FILE -f $DOCKER_COMPOSE_FILE ps | grep -q "backend.*Up"; then
    log_error "Backend контейнер не запущен!"
    log_info "Запустите: docker compose --env-file $ENV_FILE -f $DOCKER_COMPOSE_FILE up -d"
    exit 1
fi
log_success "Docker контейнеры работают"

# Вывод параметров
echo ""
log_info "Параметры импорта:"
echo "   - Директория данных: $DATA_DIR"
echo "   - Dry run: ${DRY_RUN:-нет}"
echo "   - Skip backup: ${SKIP_BACKUP:-нет}"
echo "   - Skip images: ${SKIP_IMAGES:-нет}"
echo "   - Skip customers: ${SKIP_CUSTOMERS:-нет}"
echo "   - Clear existing: ${CLEAR_EXISTING:-нет}"
echo "   - Images only: ${IMAGES_ONLY:-нет}"
echo ""

if [ -z "$DRY_RUN" ]; then
    if [ -n "$IMAGES_ONLY" ]; then
        log_warning "Будет выполнен ТОЛЬКО импорт изображений."
    else
        log_warning "Это РЕАЛЬНЫЙ импорт! Данные будут изменены."
    fi
    read -p "Продолжить? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Импорт отменён"
        exit 0
    fi
fi

START_TIME=$(date +%s)

# =============================================================================
# Режим: только изображения
# =============================================================================
if [ -n "$IMAGES_ONLY" ]; then
    echo ""
    echo "============================================================"
    log_info "РЕЖИМ: Только импорт изображений"
    echo "============================================================"
    
    IMAGES_ARGS="$DRY_RUN"
    run_django_command "import_images_from_1c $IMAGES_ARGS"
    log_success "Изображения импортированы"

else
# =============================================================================
# Полный импорт: ШАГ 1 - Атрибуты
# =============================================================================
echo ""
echo "============================================================"
log_info "ШАГ 1/4: Импорт атрибутов товаров..."
echo "============================================================"

run_django_command "import_attributes --data-dir $DATA_DIR $DRY_RUN"
log_success "Атрибуты импортированы"

# =============================================================================
# ШАГ 2: Импорт каталога (товары, варианты, цены, остатки)
# =============================================================================
echo ""
echo "============================================================"
log_info "ШАГ 2/4: Импорт каталога товаров..."
echo "============================================================"

CATALOG_ARGS="--data-dir $DATA_DIR $DRY_RUN $SKIP_BACKUP $SKIP_IMAGES $CLEAR_EXISTING"
run_django_command "import_products_from_1c $CATALOG_ARGS"
log_success "Каталог импортирован"

# =============================================================================
# ШАГ 3: Импорт изображений (если не пропущен)
# =============================================================================
if [ -z "$SKIP_IMAGES" ]; then
    echo ""
    echo "============================================================"
    log_info "ШАГ 3/4: Импорт изображений товаров..."
    echo "============================================================"
    
    IMAGES_ARGS="$DRY_RUN"
    run_django_command "import_images_from_1c $IMAGES_ARGS"
    log_success "Изображения импортированы"
else
    log_info "ШАГ 3/4: Импорт изображений пропущен (--skip-images)"
fi

# =============================================================================
# ШАГ 4: Импорт клиентов (опционально)
# =============================================================================
if [ -z "$SKIP_CUSTOMERS" ]; then
    echo ""
    echo "============================================================"
    log_info "ШАГ 4/4: Импорт клиентов..."
    echo "============================================================"
    
    run_django_command "import_customers_from_1c --data-dir $DATA_DIR $DRY_RUN"
    log_success "Клиенты импортированы"
else
    log_info "ШАГ 4/4: Импорт клиентов пропущен (--skip-customers)"
fi

fi  # Конец условия IMAGES_ONLY

# =============================================================================
# Завершение
# =============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "============================================================"
log_success "ИМПОРТ ЗАВЕРШЁН УСПЕШНО!"
echo "============================================================"
echo ""
echo "   Время выполнения: ${MINUTES}м ${SECONDS}с"
echo ""

if [ -n "$DRY_RUN" ]; then
    log_warning "Это был тестовый запуск. Данные НЕ были изменены."
    log_info "Для реального импорта запустите без --dry-run"
fi

echo ""

