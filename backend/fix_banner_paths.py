"""
Скрипт для обновления путей изображений баннеров
с banners/ на promos/ для обхода блокировки AdBlock
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.development')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("UPDATE banners SET image = REPLACE(image, 'banners/', 'promos/')")
print(f'Updated rows: {cursor.rowcount}')
connection.commit()
