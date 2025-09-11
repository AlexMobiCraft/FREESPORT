"""
Django settings for FREESPORT backend project.
"""

import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env (для локальной разработки)
load_dotenv()

# BASE_DIR указывает на корневую папку 'backend', где находится manage.py
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ (CORE SETTINGS)
# ==============================================================================
SECRET_KEY = os.environ.get('SECRET_KEY')
# В режиме тестирования, если SECRET_KEY не задан в окружении,
# используем временный ключ, чтобы тесты могли запуститься.
if 'test' in sys.argv and not SECRET_KEY:
    SECRET_KEY = 'dummy-key-for-testing-dont-use-in-prod'

DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')


# ==============================================================================
# ПРИЛОЖЕНИЯ (APPLICATIONS)
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'sport.apps.SportConfig',
    'users.apps.UsersConfig',
]


# ==============================================================================
# ПОСРЕДНИКИ (MIDDLEWARE)
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==============================================================================
# URL И WSGI
# ==============================================================================
ROOT_URLCONF = 'backend.urls'
WSGI_APPLICATION = 'backend.wsgi.application'


# ==============================================================================
# ШАБЛОНЫ (TEMPLATES)
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ==============================================================================
# БАЗА ДАННЫХ (DATABASE)
# ==============================================================================

# Вот исправленный блок, который соответствует вашим .env файлам
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}


# ==============================================================================
# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ (AUTH USER MODEL)
# ==============================================================================
AUTH_USER_MODEL = 'users.User'


# ==============================================================================
# ВАЛИДАТОРЫ ПАРОЛЕЙ (PASSWORD VALIDATION)
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# ==============================================================================
# НАСТРОЙКИ DJANGO REST FRAMEWORK
# ==============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated']
}


# ==============================================================================
# НАСТРОЙКИ SIMPLE JWT
# ==============================================================================
SIMPLE_JWT = { "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5), "REFRESH_TOKEN_LIFETIME": timedelta(days=1), }


# ==============================================================================
# ИНТЕРНАЦИОНАЛИЗАЦИЯ (INTERNATIONALIZATION)
# ==============================================================================
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ (STATIC FILES)
# ==============================================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ==============================================================================
# НАСТРОЙКА ПЕРВИЧНОГО КЛЮЧА (DEFAULT PRIMARY KEY)
# ==============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

