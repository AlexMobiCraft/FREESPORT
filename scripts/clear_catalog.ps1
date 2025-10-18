param(
    [string]$ComposeFile = "docker-compose.test.yml"
)

Write-Host "Остановка зависимых контейнеров (если запущены)..."
docker compose -f $ComposeFile down --remove-orphans

Write-Host "Очистка таблиц каталога в PostgreSQL..."
docker compose -f $ComposeFile run --rm backend python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('TRUNCATE products_product CASCADE'); cursor.execute('TRUNCATE products_brand CASCADE'); cursor.execute('TRUNCATE products_category CASCADE'); cursor.execute('TRUNCATE products_productimage CASCADE'); cursor.execute('TRUNCATE products_pricetype CASCADE'); cursor.execute('TRUNCATE products_importsession CASCADE'); connection.commit(); cursor.close(); print('Каталог очищен.')"

Write-Host "Очистка кэша Django..."
docker compose -f $ComposeFile run --rm backend python manage.py clearsessions

Write-Host "Готово. Таблицы каталога очищены."
