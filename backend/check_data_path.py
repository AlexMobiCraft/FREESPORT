#!/usr/bin/env python
"""Проверка пути к данным для тестов"""
import os
import sys
from pathlib import Path

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.test')
import django
django.setup()

from django.conf import settings

# Проверка пути
data_dir = Path(settings.BASE_DIR).parent / 'data' / 'import_1c'

print(f"BASE_DIR: {settings.BASE_DIR}")
print(f"DATA_DIR (computed): {data_dir}")
print(f"DATA_DIR exists: {data_dir.exists()}")

if data_dir.exists():
    print(f"\nСодержимое {data_dir}:")
    for item in data_dir.iterdir():
        print(f"  - {item.name}")
else:
    print(f"\n❌ Директория {data_dir} не найдена!")
    
# Проверка альтернативного пути
alt_data_dir = Path('/app/data/import_1c')
print(f"\nАльтернативный путь: {alt_data_dir}")
print(f"Альтернативный путь exists: {alt_data_dir.exists()}")

if alt_data_dir.exists():
    print(f"\nСодержимое {alt_data_dir}:")
    for item in alt_data_dir.iterdir():
        print(f"  - {item.name}")
