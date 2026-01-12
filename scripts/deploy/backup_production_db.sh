#!/bin/bash
# =============================================================================
# Backup production БД перед миграцией
# Story 13.4: Миграция данных в production
# AC1: Pre-migration backup БД создан через pg_dump (NFR3)
# =============================================================================

set -euo pipefail

# Конфигурация (переопределяется через переменные окружения)
BACKUP_DIR="${BACKUP_DIR:-/backups/freesport}"
DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-freesport_prod}"
DB_USER="${DB_USER:-freesport_user}"
S3_BUCKET="${S3_BUCKET:-s3://freesport-backups}"
ENABLE_OFFSITE_BACKUP="${ENABLE_OFFSITE_BACKUP:-true}"

# Timestamp для имени файла
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_pre_migration_$TIMESTAMP.dump"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting production backup ===${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Database: $DB_NAME@$DB_HOST"
echo "Backup file: $BACKUP_FILE"

# Создать директорию для backup если не существует
mkdir -p "$BACKUP_DIR"

# Проверка доступности БД
echo -e "\n${YELLOW}Checking database availability...${NC}"
if ! pg_isready -h "$DB_HOST" -U "$DB_USER" >/dev/null 2>&1; then
  echo -e "${RED}ERROR: Database $DB_NAME is not accessible${NC}"
  echo "Please check:"
  echo "  - PostgreSQL is running"
  echo "  - Host $DB_HOST is reachable"
  echo "  - User $DB_USER has access"
  exit 1
fi
echo -e "${GREEN}✓ Database is accessible${NC}"

# Остановка Celery workers (предотвратить изменения во время backup)
echo -e "\n${YELLOW}Stopping Celery workers...${NC}"
if command -v supervisorctl &> /dev/null; then
  supervisorctl stop celery:* 2>/dev/null || echo "Celery workers not managed by supervisord"
elif command -v docker &> /dev/null; then
  docker compose stop celery celery-beat 2>/dev/null || echo "Celery containers not running"
else
  echo -e "${YELLOW}Warning: Could not stop Celery workers automatically${NC}"
fi
echo -e "${GREEN}✓ Celery workers stopped${NC}"

# Создание backup
echo -e "\n${YELLOW}Creating backup...${NC}"
echo "This may take several minutes depending on database size..."

START_TIME=$(date +%s)
pg_dump -h "$DB_HOST" -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"
END_TIME=$(date +%s)

DURATION=$((END_TIME - START_TIME))
echo -e "${GREEN}✓ Backup created in ${DURATION}s${NC}"

# Валидация backup
echo -e "\n${YELLOW}Validating backup...${NC}"

# Проверка что файл не пустой
if [ ! -s "$BACKUP_FILE" ]; then
  echo -e "${RED}ERROR: Backup file is empty${NC}"
  exit 1
fi

# Проверка структуры backup
if ! pg_restore --list "$BACKUP_FILE" >/dev/null 2>&1; then
  echo -e "${RED}ERROR: Backup file is corrupted${NC}"
  exit 1
fi

# Создание checksum
sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
echo -e "${GREEN}✓ Backup validated${NC}"

# Размер backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup size: $BACKUP_SIZE"

# Offsite backup (S3)
if [[ "$ENABLE_OFFSITE_BACKUP" == "true" ]]; then
  echo -e "\n${YELLOW}Uploading backup to $S3_BUCKET ...${NC}"
  
  if command -v aws &> /dev/null; then
    aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/" --quiet
    aws s3 cp "$BACKUP_FILE.sha256" "$S3_BUCKET/" --quiet
    echo -e "${GREEN}✓ Backup uploaded to S3${NC}"
  elif command -v mc &> /dev/null; then
    mc cp "$BACKUP_FILE" "$S3_BUCKET/"
    mc cp "$BACKUP_FILE.sha256" "$S3_BUCKET/"
    echo -e "${GREEN}✓ Backup uploaded to MinIO${NC}"
  else
    echo -e "${YELLOW}Warning: Neither aws nor mc CLI found. Skipping offsite backup.${NC}"
  fi
fi

# Перезапуск Celery workers
echo -e "\n${YELLOW}Restarting Celery workers...${NC}"
if command -v supervisorctl &> /dev/null; then
  supervisorctl start celery:* 2>/dev/null || echo "Celery workers not managed by supervisord"
elif command -v docker &> /dev/null; then
  docker compose start celery celery-beat 2>/dev/null || echo "Celery containers not configured"
fi
echo -e "${GREEN}✓ Celery workers restarted${NC}"

# Итоговая информация
echo -e "\n${GREEN}=== Backup completed successfully ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo "Backup size: $BACKUP_SIZE"
echo "Checksum: $BACKUP_FILE.sha256"
echo "Duration: ${DURATION}s"

echo -e "\n${YELLOW}To restore this backup:${NC}"
echo "  ./rollback_production.sh $BACKUP_FILE"
