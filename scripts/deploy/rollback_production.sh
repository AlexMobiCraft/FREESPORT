#!/bin/bash
# =============================================================================
# Rollback production к pre-migration состоянию
# Story 13.4: Миграция данных в production
# AC6: Rollback процедура протестирована на staging
# =============================================================================

set -euo pipefail

# Конфигурация (переопределяется через переменные окружения)
BACKUP_FILE=${1:-}
APP_DIR=${APP_DIR:-/var/www/freesport}
PREVIOUS_TAG=${PREVIOUS_TAG:-}
SUPERVISOR_APP_GROUP=${SUPERVISOR_APP_GROUP:-freesport}
DB_NAME=${DB_NAME:-freesport_prod}
DB_HOST=${DB_HOST:-localhost}
DB_USER=${DB_USER:-freesport_user}

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [[ -z "$BACKUP_FILE" ]]; then
  echo -e "${RED}Usage: ./rollback_production.sh <backup_file>${NC}"
  echo ""
  echo "Environment variables:"
  echo "  APP_DIR              - Application directory (default: /var/www/freesport)"
  echo "  PREVIOUS_TAG         - Git tag to rollback to (default: auto-detect)"
  echo "  SUPERVISOR_APP_GROUP - Supervisor group name (default: freesport)"
  echo "  DB_NAME              - Database name (default: freesport_prod)"
  echo "  DB_HOST              - Database host (default: localhost)"
  echo "  DB_USER              - Database user (default: freesport_user)"
  echo ""
  echo "Example:"
  echo "  APP_DIR=/var/www/freesport ./rollback_production.sh /backups/backup_pre_migration_20251202.dump"
  exit 1
fi

# Проверка существования backup файла
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo -e "${RED}ERROR: Backup file not found: $BACKUP_FILE${NC}"
  exit 1
fi

# Начало rollback
echo -e "${RED}=== ROLLBACK PRODUCTION ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo "Application: $APP_DIR"
echo "Database: $DB_NAME@$DB_HOST"

# Подтверждение
echo -e "\n${YELLOW}⚠️  WARNING: This will:${NC}"
echo "  1. Stop the application"
echo "  2. DROP and recreate the database"
echo "  3. Restore from backup"
echo "  4. Revert code to previous release"
echo "  5. Restart the application"

echo -e "\n${RED}This action is DESTRUCTIVE and cannot be undone!${NC}"
read -p "Are you sure you want to rollback? (yes/no): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
  echo -e "${YELLOW}Rollback cancelled${NC}"
  exit 0
fi

# Засекаем время
START_TIME=$(date +%s)

# 1. Остановка приложения
echo -e "\n${YELLOW}[1/5] Stopping application...${NC}"
if command -v supervisorctl &> /dev/null; then
  supervisorctl stop "$SUPERVISOR_APP_GROUP":* 2>/dev/null || true
elif command -v docker &> /dev/null; then
  docker compose down 2>/dev/null || true
fi
echo -e "${GREEN}✓ Application stopped${NC}"

# 2. Восстановление БД
echo -e "\n${YELLOW}[2/5] Restoring database...${NC}"

# Закрыть все соединения к БД
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "
  SELECT pg_terminate_backend(pg_stat_activity.pid)
  FROM pg_stat_activity
  WHERE pg_stat_activity.datname = '$DB_NAME'
    AND pid <> pg_backend_pid();
" 2>/dev/null || true

# Drop и создание БД
echo "  Dropping database..."
dropdb -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" --if-exists

echo "  Creating database..."
createdb -h "$DB_HOST" -U "$DB_USER" "$DB_NAME"

echo "  Restoring from backup..."
pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" "$BACKUP_FILE" --no-owner --no-acl

echo -e "${GREEN}✓ Database restored${NC}"

# 3. Revert code
echo -e "\n${YELLOW}[3/5] Reverting code...${NC}"
cd "$APP_DIR"

# Определить предыдущий tag если не указан
if [[ -z "$PREVIOUS_TAG" ]]; then
  PREVIOUS_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
  
  if [[ -z "$PREVIOUS_TAG" ]]; then
    echo -e "${YELLOW}Warning: Could not auto-detect previous tag${NC}"
    echo "Please specify PREVIOUS_TAG environment variable"
    echo "Skipping code revert..."
  fi
fi

if [[ -n "$PREVIOUS_TAG" ]]; then
  echo "  Checking out: $PREVIOUS_TAG"
  git fetch --tags
  git checkout "$PREVIOUS_TAG"
  echo -e "${GREEN}✓ Code reverted to $PREVIOUS_TAG${NC}"
fi

# 4. Перезапуск приложения
echo -e "\n${YELLOW}[4/5] Restarting application...${NC}"
if command -v supervisorctl &> /dev/null; then
  supervisorctl start "$SUPERVISOR_APP_GROUP":*
elif command -v docker &> /dev/null; then
  docker compose up -d
fi
echo -e "${GREEN}✓ Application restarted${NC}"

# 5. Проверка здоровья
echo -e "\n${YELLOW}[5/5] Health check...${NC}"
sleep 5  # Даём приложению время на запуск

# Проверка API
if command -v curl &> /dev/null; then
  if curl -sf http://localhost:8000/api/health/ >/dev/null 2>&1; then
    echo -e "${GREEN}✓ API is responding${NC}"
  else
    echo -e "${YELLOW}Warning: API health check failed (may need more time)${NC}"
  fi
fi

# Итоги
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

echo -e "\n${GREEN}=== Rollback completed successfully ===${NC}"
echo "Total time: ${DURATION_MIN}m ${DURATION_SEC}s"
echo ""
echo "Next steps:"
echo "  1. Verify application is working correctly"
echo "  2. Check logs for errors: tail -f /var/log/freesport/*.log"
echo "  3. Notify team about rollback"
echo "  4. Investigate root cause of migration failure"
