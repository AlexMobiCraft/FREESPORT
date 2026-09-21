---
name: import-1c
description: Команды импорта данных из 1С (CommerceML 3.1) в FREESPORT — товары, цены, остатки, контрагенты. Активируй при запросах "импортируй товары из 1С", "импорт контрагентов", "запусти import_products_from_1c", "загрузи выгрузку 1С".
---

# Импорт данных из 1С (CommerceML 3.1)

Все команды выполняются внутри backend-контейнера.

## Товары, цены, остатки

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py import_products_from_1c --file-type=all
```

`--file-type`: `all` | `goods` | `offers` | `prices` | `rests`. `--dry-run` — без записи в БД.

## Контрагенты

Сначала прогон с `--dry-run`, затем тот же вызов без флага:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec backend \
  python manage.py import_customers_from_1c --dry-run \
  --file=/app/data/import_1c/contragents/<файл из data/import_1c/contragents/>
```

## Данные для тестов

❌ **НЕ создавай** синтетические XML для тестов импорта — используй реальные выгрузки из `data/import_1c/`:

- `contragents/` — контрагенты (ООО/ИП/физлица, edge cases)
- `goods/` — товары + `import_files/` изображения
- `offers/`, `prices/`, `rests/`, `units/`, `storages/`, `priceLists/`

## Архитектура импорта

Процессинг — `VariantImportProcessor`, парсинг — `XMLDataParser`.
Подробности: `docs/integrations/1c/import-process.md`.
