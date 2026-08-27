# Проверка

## Прогон тестов

```bash
cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend \
  pytest -xvs apps/products/tests/<файл>
```

`--env-file` тестовому compose не передаётся; `run --rm`, не `exec`. **Параллельные прогоны по одному compose-проекту невозможны** — одна БД на проект, две сессии дерутся на `TRUNCATE` и дают лавину ложных падений.

Каждый новый тест сначала прогоняется **до** правки и должен упасть (RED). Прогон без RED не доказывает ничего.

## Проверка на проде после выката

```sql
-- 1. Ошибки изображений упали (было 253 на каждую goods-сессию)
SELECT id, created_at,
       report_details->>'images_copied'  AS copied,
       report_details->>'images_skipped' AS skipped,
       report_details->>'images_errors'  AS errors
FROM import_sessions
WHERE report_details ? 'images_copied' ORDER BY created_at DESC LIMIT 10;

-- 2. Контрольный товар
SELECT base_images FROM products WHERE id = 9194;
```

Перекос «мелкая картинка первая» считать скриптом: путь → `os.path.getsize` в `MEDIA_ROOT`, было 104.

Главное изображение через API:

```bash
curl -s https://optisport.ru/api/v1/products/<slug>/ | jq .main_image
```

Для товара 9194 главным должен стать файл `…_fb2f7292-….jpg` (розовая гантель 1,0 кг).

## После выката

После пересборки backend обязателен `restart nginx` — иначе весь внешний API и обмен 1С уходят в 502. Деплой ручной, CI-шаг всегда skipped.
