"""
Django settings for FREESPORT backend project.
"""

import os
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

# ВНИМАНИЕ: Секретный ключ должен храниться в переменных окружения и никогда
# не должен попадать в систему контроля версий (Git).
SECRET_KEY = os.environ.get('SECRET_KEY')

# ВНИМАНИЕ: DEBUG должен быть False в продакшене.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Хосты, с которых разрешены запросы. Для продакшена нужно указать ваш домен.
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

    # Сторонние библиотеки
    'rest_framework',
    'rest_framework_simplejwt',

    # Ваши приложения
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}


# ==============================================================================
# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ (AUTH USER MODEL)
# ==============================================================================

# Указываем Django использовать вашу кастомную модель пользователя
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
    # Аутентификация по умолчанию через JWT
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Разрешения по умолчанию (требуется аутентификация для доступа к API)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}


# ==============================================================================
# НАСТРОЙКИ SIMPLE JWT
# ==============================================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}


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

