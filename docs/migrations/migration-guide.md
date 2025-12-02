# Migration Guide: ProductVariant System

> **Story 13.4**: Миграция данных в production  
> **Version**: 1.0  
> **Last Updated**: 2025-12-02

## Обзор

Этот документ описывает процедуру миграции production БД для внедрения системы ProductVariant. Миграция включает:

1. Создание backup production БД
2. Применение Django миграций
3. Очистка старых данных товаров
4. Полный импорт каталога из 1С
5. Валидация результатов

---

## Pre-Migration Checklist

Перед началом миграции убедитесь:

- [ ] Stories 13.1, 13.2, 13.3 завершены и имеют gate PASS
- [ ] Все автотесты проходят на develop ветке
- [ ] GitHub Actions CI зелёный
- [ ] Staging миграция протестирована
- [ ] Rollback процедура протестирована на staging
- [ ] Команда уведомлена о maintenance window
- [ ] Доступ к production серверу подтверждён

---

## Deployment Window

**Рекомендуемое время**: 2:00 AM - 4:00 AM MSK (низкая нагрузка)

| Время | Действие | Длительность | Ответственный |
|-------|----------|--------------|---------------|
| 01:30 | Уведомление в Slack #tech-alerts | 2 мин | DevOps |
| 01:45 | Pre-deployment meeting | 15 мин | Team |
| 02:00 | Включить maintenance mode | 2 мин | DevOps |
| 02:02 | Создать pre-migration backup | 10 мин | DevOps |
| 02:12 | Deploy новой версии кода | 5 мин | DevOps |
| 02:17 | Запустить Django миграции | 3 мин | DevOps |
| 02:20 | Pre-import validation (1С) | 5 мин | Backend |
| 02:25 | Очистить старые товары | 2 мин | DevOps |
| 02:27 | Импорт каталога из 1С | 30 мин | Backend |
| 02:57 | Post-migration validation | 5 мин | QA |
| 03:02 | Отключить maintenance mode | 2 мин | DevOps |
| 03:04 | Smoke tests | 10 мин | QA |
| 03:14 | Уведомление о завершении | 2 мин | DevOps |

**Общее время**: ~1ч 45мин (buffer до 4:00 AM)

---

## Migration Steps

### Step 1: Pre-Migration Backup

```bash
# На production сервере
cd /var/www/freesport

# Создать backup
./scripts/deploy/backup_production_db.sh

# Или вручную:
pg_dump -h localhost -U freesport_user -Fc freesport_prod > /backups/backup_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# Проверить backup
pg_restore --list /backups/backup_pre_migration_*.dump
sha256sum /backups/backup_pre_migration_*.dump
```

### Step 2: Enable Maintenance Mode

```bash
# Включить maintenance mode (nginx)
sudo ln -sf /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/default
sudo nginx -s reload

# Или через Django
python manage.py maintenance_mode on
```

### Step 3: Deploy New Code

```bash
cd /var/www/freesport

# Pull latest code
git fetch origin
git checkout v13.4.0  # или соответствующий tag

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
```

### Step 4: Run Django Migrations

```bash
# Проверить pending миграции
python manage.py showmigrations | grep "[ ]"

# Применить миграции
python manage.py migrate

# Проверить что все миграции применены
python manage.py showmigrations | grep "[ ]"
# Должен быть пустой вывод
```

### Step 5: Pre-Import Validation

```bash
# Проверить доступность 1С
curl -f $ONEC_HEALTHCHECK_URL

# Проверить XML файлы
ls -la /path/to/1c/data/*.xml

# Проверить ColorMapping
python manage.py shell -c "from apps.products.models import ColorMapping; print(f'Colors: {ColorMapping.objects.count()}')"
# Должно быть >= 20
```

### Step 6: Flush Old Products

```bash
# Dry run - посмотреть что будет удалено
python manage.py flush_products --dry-run

# Выполнить очистку
python manage.py flush_products --confirm --skip-interactive
```

### Step 7: Import from 1C

```bash
# Полный импорт каталога
python manage.py import_products_from_1c --full

# Мониторинг прогресса
tail -f /var/log/freesport/import_products.log
```

### Step 8: Post-Migration Validation

```bash
# Проверить количество записей
python manage.py shell << 'EOF'
from apps.products.models import Product, ProductVariant, ColorMapping
print(f"Products: {Product.objects.count()}")
print(f"ProductVariants: {ProductVariant.objects.count()}")
print(f"ColorMappings: {ColorMapping.objects.count()}")
EOF

# Smoke test API
curl -s http://localhost:8000/api/products/ | jq '.count'
curl -s http://localhost:8000/api/products/some-product-slug/ | jq '.variants | length'
curl -s http://localhost:8000/api/categories/ | jq '.count'
```

### Step 9: Disable Maintenance Mode

```bash
# Отключить maintenance mode
sudo ln -sf /etc/nginx/sites-available/freesport /etc/nginx/sites-enabled/default
sudo nginx -s reload

# Или через Django
python manage.py maintenance_mode off
```

---

## Rollback Procedure

Если миграция failed, выполните rollback:

```bash
# Автоматический rollback
./scripts/deploy/rollback_production.sh /backups/backup_pre_migration_YYYYMMDD_HHMMSS.dump

# Или вручную:

# 1. Остановить приложение
supervisorctl stop freesport:*

# 2. Восстановить БД
dropdb freesport_prod
createdb freesport_prod
pg_restore -h localhost -U freesport_user -d freesport_prod /backups/backup_pre_migration_*.dump

# 3. Откатить код
cd /var/www/freesport
git checkout v13.3.0  # предыдущий release

# 4. Перезапустить приложение
supervisorctl start freesport:*
```

**Ожидаемое время rollback**: ~15 минут

---

## Rollback Decision Matrix

| Проблема | Severity | Rollback? | Действие |
|----------|----------|-----------|----------|
| Django миграция failed | 🔴 Critical | ✅ YES | Немедленный rollback |
| Импорт 1С failed | 🔴 Critical | ✅ YES | Rollback + расследование |
| Response time > 1000ms | 🟡 High | ⚠️ MAYBE | Мониторинг 1ч, затем решение |
| Error rate > 5% | 🔴 Critical | ✅ YES | Немедленный rollback |
| Error rate 1-5% | 🟡 High | ⚠️ MAYBE | Мониторинг + hotfix |
| Missing ColorMapping | 🟢 Low | ❌ NO | Hotfix (добавить цвета) |

---

## Troubleshooting

### Миграция Django failed

```bash
# Проверить ошибку
python manage.py migrate --plan

# Откатить последнюю миграцию
python manage.py migrate products 0001_previous_migration

# Проверить состояние
python manage.py showmigrations products
```

### Импорт 1С failed

```bash
# Проверить логи
tail -100 /var/log/freesport/import_products.log

# Проверить XML файлы
python manage.py shell -c "
from apps.products.services.parser import XMLDataParser
parser = XMLDataParser('/path/to/1c/data')
print(parser.validate_files())
"
```

### ColorMapping не найден

```bash
# Добавить недостающий цвет
python manage.py shell << 'EOF'
from apps.products.models import ColorMapping
ColorMapping.objects.create(name='Новый цвет', hex_code='#RRGGBB')
EOF
```

### API возвращает 500

```bash
# Проверить логи Django
tail -100 /var/log/freesport/django.log

# Проверить подключение к БД
python manage.py dbshell -c "SELECT 1;"

# Перезапустить gunicorn
supervisorctl restart freesport:gunicorn
```

---

## Post-Migration Monitoring

После миграции мониторить 24 часа:

1. **Error rate** в логах (должен быть < 1%)
2. **Response time** API (должен быть < 500ms)
3. **CPU/Memory** (должен остаться в пределах нормы)
4. **Slack #tech-alerts** на критические ошибки

```bash
# Мониторинг error rate
grep -c "ERROR" /var/log/freesport/django.log

# Мониторинг response time
grep "request_time" /var/log/nginx/access.log | awk '{sum+=$NF; count++} END {print sum/count}'
```

---

## Contacts

| Роль | Имя | Контакт |
|------|-----|---------|
| DevOps Lead | - | Slack: @devops |
| Backend Lead | - | Slack: @backend |
| QA Lead | - | Slack: @qa |
| On-Call | - | PagerDuty |

---

## Revision History

| Дата | Версия | Описание | Автор |
|------|--------|----------|-------|
| 2025-12-02 | 1.0 | Создание документа | James (Dev) |
