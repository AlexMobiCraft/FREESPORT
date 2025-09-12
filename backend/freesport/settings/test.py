from .base import * # noqa: F403, F401 # pylint: disable=wildcard-import,unused-wildcard-import
import os
from typing import Any

# ==============================================================================
# НАСТРОЙКИ ДЛЯ ТЕСТИРОВАНИЯ (TESTING SETTINGS)
# ==============================================================================

# Отключаем отладку в тестах для производительности и безопасности
DEBUG = False

# Используем временный ключ, чтобы не раскрывать продакшен-ключ
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-test-key-for-ci")


# ==============================================================================
# БАЗА ДАННЫХ (DATABASE)
# ==============================================================================
#
# Максимально простая конфигурация БД, совместимая с pytest-django.
# Все значения берутся напрямую из переменных окружения, которые
# мы устанавливаем в .github/workflows/main.yml.
#
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}


# ==============================================================================
# УСКОРЕНИЕ ТЕСТОВ (TESTING SPEEDUPS)
# ==============================================================================

# Используем быстрый (небезопасный) хешер паролей для ускорения
# создания пользователей в тестах.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Отключаем email-отправку, заменяя её на "заглушку",
# которая хранит письма в памяти.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Отключаем логирование в консоль, чтобы вывод тестов был чистым.
LOGGING: dict[str, Any] = {}