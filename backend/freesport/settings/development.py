"""
Настройки Django для локальной разработки FREESPORT
"""
from .base import *

# ВНИМАНИЕ: не используйте debug=True в продакшене!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Дополнительные приложения для разработки
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

# Middleware для отладки
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Настройки базы данных для разработки (используем SQLite для простоты)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Настройки CORS для фронтенда
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Next.js dev server
    'http://127.0.0.1:3000',
]

CORS_ALLOW_CREDENTIALS = True

# Настройки Debug Toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

# Упрощенные настройки безопасности для разработки
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Логирование для разработки
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'freesport': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}