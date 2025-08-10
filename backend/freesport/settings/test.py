"""
Настройки Django для тестового окружения FREESPORT Platform
Оптимизированы для быстрого выполнения тестов
"""
from .base import *
import tempfile

# Отключаем DEBUG для тестов
DEBUG = False

# Тестовая база данных в памяти для скорости
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

# Отключаем кеширование
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
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
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=10),
    'SIGNING_KEY': SECRET_KEY,
})

# Разрешаем все домены для тестов
ALLOWED_HOSTS = ['*']

# Отключаем CORS проверки
CORS_ALLOW_ALL_ORIGINS = True

# Настройки для factory_boy
FACTORY_FOR_DJANGO_FILE_FIELD = True

# Настройки для pytest-django
USE_TZ = True