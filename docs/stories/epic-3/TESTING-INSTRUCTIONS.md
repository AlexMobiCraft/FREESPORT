# Инструкции по запуску integration тестов Story 3.1.3

## Быстрый старт (Docker)

```powershell
# 1. Запустить backend с данными
docker-compose up -d backend

# 2. Запустить тесты (ВАЖНО: с флагом --migrations)
docker-compose exec backend pytest tests/integration/test_real_catalog_import.py -v --migrations

# 3. Проверить результаты
# - Если данные в data/import_1c/ присутствуют: тесты выполнятся полностью
# - Если данных нет: 8 тестов будут пропущены (skipped) - это нормально
```

## Что проверяют тесты

8 integration тестов валидируют:

1. **test_import_real_goods** - Импорт ≥1900 товаров из goods_*.xml (~1916 товаров в реальных данных)
2. **test_import_real_categories** - Иерархия категорий из groups_*.xml
3. **test_import_real_prices** - Цены для всех 7 ролей из prices_*.xml
4. **test_real_data_integrity** - Целостность данных (связи, orphan records, onec_id)
5. **test_specifications_from_properties** - Характеристики из propertiesGoods_*.xml
6. **test_api_returns_real_products** - API с реальными данными
7. **test_admin_displays_real_catalog** - Админка с реальным каталогом
8. **test_price_fallback_with_real_data** - Fallback логика цен

## Структура данных

Тесты ожидают данные в:
```
data/import_1c/
├── goods/          # 4 файла goods_1_*.xml (~31 MB, ~1916 товаров)
├── groups/         # 1 файл groups_1_*.xml
├── prices/         # 5 файлов prices_1_*.xml
├── offers/         # 10 файлов offers_1_*.xml (~4932 предложения)
├── propertiesGoods/# 9 файлов propertiesGoods_1_*.xml
├── rests/          # 5 файлов rests_1_*.xml (~9904 записи)
└── priceLists/     # 1 файл priceLists_1_*.xml (6 типов цен)
```

## Ожидаемые результаты

### С данными (data/import_1c/ заполнена)
```
8 passed in ~30-60s
```

### Без данных (data/import_1c/ пустая или отсутствует)
```
8 skipped in ~5s
```

## Troubleshooting

### Тесты пропускаются (skipped)
✅ **Это нормально!** Означает что данные не найдены в `data/import_1c/`

### Ошибка "database test_freesport is being accessed by other users"
```powershell
# Удалить зависшую тестовую БД
docker-compose exec db dropdb -U postgres test_freesport --force

# Запустить тесты снова
docker-compose exec backend pytest tests/integration/test_real_catalog_import.py -v --migrations
```

### Ошибки подключения к БД
```powershell
# Проверить что PostgreSQL запущен
docker ps | grep freesport-db

# Перезапустить если нужно
docker-compose restart db
```

### Локальный запуск (Windows)
Используйте PowerShell скрипт:
```powershell
cd backend
.\run_integration_tests.ps1
```

## Дополнительная информация

Подробное руководство: `docs/stories/epic-3/3.1.3-testing-guide.md`
