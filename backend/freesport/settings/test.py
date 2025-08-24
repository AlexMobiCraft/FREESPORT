from .base import *
import tempfile
from datetime import timedelta

# Отключаем DEBUG для тестов
DEBUG = False

# Тестовая база данных - поддерживаем как SQLite так и PostgreSQL
import os

# Если запускается в Docker, используем PostgreSQL, иначе SQLite
if os.environ.get('DB_HOST'):
    # PostgreSQL для Docker тестов
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'freesport_test'),
            'USER': os.environ.get('DB_USER', 'freesport_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'password123'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'TEST': {
                'NAME': 'test_' + os.environ.get('DB_NAME', 'freesport_test'),
            },
        }
    }
else:
    # SQLite в памяти для локальных тестов
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
            'TEST': {
                'NAME': ':memory:',
            },
        }
    }

# Отключаем миграции для быстрых тестов
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Простой хешер паролей для скорости
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Настройки кеширования для тестов
if os.environ.get('REDIS_URL'):
    # Redis кеш для Docker тестов
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'freesport_test'
        }
    }
else:
    # Локальный кеш в памяти для локальных тестов
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Отключаем логирование для тестов
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
        },
        'freesport': {
            'handlers': ['null'],
            'propagate': False,
        },
    }
}

# Медиа файлы во временной директории
MEDIA_ROOT = tempfile.mkdtemp()

# Статические файлы во временной директории
STATIC_ROOT = tempfile.mkdtemp()

# Отключаем email отправку
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Тестовый SECRET_KEY
SECRET_KEY = 'test-secret-key-for-testing-only-do-not-use-in-production'

# Упрощенная настройка middleware для тестов
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Настройки для тестирования JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=10),
    'SIGNING_KEY': SECRET_KEY,
    'ALGORITHM': 'HS256',
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

# Разрешаем все домены для тестов
ALLOWED_HOSTS = ['*']

# Отключаем CORS проверки
CORS_ALLOW_ALL_ORIGINS = True

# Настройки для factory_boy
FACTORY_FOR_DJANGO_FILE_FIELD = True

# Настройки для pytest-django
USE_TZ = True

# Отключаем django-ratelimit для тестов
RATELIMIT_ENABLE = False