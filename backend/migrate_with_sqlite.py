"""
Скрипт для выполнения миграций с использованием SQLite вместо PostgreSQL
для обхода проблемы с кодировкой на Windows
"""
import os
import sys
import django
from pathlib import Path

# Устанавливаем переменные окружения
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.base")
os.environ.setdefault("FREESPORT_DISABLE_CELERY", "1")

# Добавляем текущую директорию в Python path
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем и настраиваем Django
django.setup()

from django.conf import settings
from django.core.management import execute_from_command_line
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper

# Создаем временную конфигурацию базы данных SQLite
temp_db_config = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": Path(__file__).parent / "temp_migration.db",
    "OPTIONS": {
        "timeout": 20,
    },
}

# Временно заменяем конфигурацию базы данных
original_db_config = settings.DATABASES["default"]
settings.DATABASES["default"] = temp_db_config

print("Using temporary SQLite database for migration...")
print(f"Database file: {temp_db_config['NAME']}")

try:
    # Выполняем миграции
    execute_from_command_line(["manage.py", "migrate"])
    print("Migration completed successfully with SQLite!")

except Exception as e:
    print(f"Migration failed: {e}")
    sys.exit(1)

finally:
    # Восстанавливаем оригинальную конфигурацию
    settings.DATABASES["default"] = original_db_config
    print("Restored original database configuration")
