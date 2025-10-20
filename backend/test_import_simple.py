#!/usr/bin/env python
"""Простой тест импорта для отладки"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.test')
django.setup()

from django.core.management import call_command
from apps.products.models import ImportSession, Product

print("=" * 60)
print("ТЕСТ ИМПОРТА")
print("=" * 60)

# Проверка таблиц
print("\n1. Проверка таблиц...")
try:
    count = ImportSession.objects.count()
    print(f"   ✅ Таблица ImportSession существует (записей: {count})")
except Exception as e:
    print(f"   ❌ Ошибка с таблицей ImportSession: {e}")
    sys.exit(1)

# Попытка импорта
print("\n2. Запуск импорта...")
try:
    call_command(
        "import_catalog_from_1c",
        "--data-dir",
        "/app/data/import_1c",
        "--skip-backup",
        "--file-type",
        "goods",
    )
    print("   ✅ Импорт завершен успешно")
except SystemExit as e:
    print(f"   ❌ SystemExit: {e.code}")
    sys.exit(e.code)
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Проверка результатов
print("\n3. Проверка результатов...")
products_count = Product.objects.count()
print(f"   Импортировано товаров: {products_count}")

if products_count >= 1900:
    print("\n✅ ТЕСТ ПРОЙДЕН!")
    sys.exit(0)
else:
    print(f"\n❌ ТЕСТ НЕ ПРОЙДЕН: ожидалось ≥1900, получено {products_count}")
    sys.exit(1)
