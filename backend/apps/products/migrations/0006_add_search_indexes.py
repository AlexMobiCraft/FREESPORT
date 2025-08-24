# Generated manually for Story 2.8: search-api optimization

from django.db import migrations, connection


def add_search_indexes(apps, schema_editor):
    """Добавляет поисковые индексы в зависимости от типа БД"""
    try:
        # Получаем модель Product
        Product = apps.get_model('products', 'Product')
        
        # Проверяем, существует ли таблица
        from django.db import connection
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM products_product LIMIT 1")
                table_exists = True
            except:
                table_exists = False
        
        if not table_exists:
            return  # Таблица ещё не создана, пропускаем создание индексов
        
        db_vendor = connection.vendor
        
        with connection.cursor() as cursor:
            if db_vendor == 'postgresql':
                # PostgreSQL - полнотекстовые индексы
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_gin_idx ON products_product 
                    USING GIN(to_tsvector('russian', 
                    COALESCE(name, '') || ' ' || COALESCE(short_description, '') || ' ' || 
                    COALESCE(description, '') || ' ' || COALESCE(sku, '')))
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_category_idx ON products_product 
                    (category_id, is_active) WHERE name IS NOT NULL
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_brand_idx ON products_product 
                    (brand_id, is_active) WHERE name IS NOT NULL
                """)
            else:
                # SQLite/other databases - обычные индексы
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_name_idx ON products_product (name)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_sku_idx ON products_product (sku)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_category_idx ON products_product 
                    (category_id, is_active)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_search_brand_idx ON products_product 
                    (brand_id, is_active)
                """)
    except Exception as e:
        # В случае ошибки просто пропускаем создание индексов
        pass


def remove_search_indexes(apps, schema_editor):
    """Удаляет поисковые индексы"""
    with connection.cursor() as cursor:
        indexes = [
            'products_search_gin_idx',
            'products_search_category_idx', 
            'products_search_brand_idx',
            'products_search_name_idx',
            'products_search_sku_idx'
        ]
        
        for index in indexes:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {index}")
            except:
                pass  # Ignore errors if index doesn't exist


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_product_specifications'),
    ]

    operations = [
        migrations.RunPython(add_search_indexes, remove_search_indexes),
    ]