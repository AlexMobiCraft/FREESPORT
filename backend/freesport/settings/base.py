"""
Базовые настройки Django для платформы FREESPORT
Общая конфигурация для всех окружений
"""
from pathlib import Path
from datetime import timedelta
from decouple import config
import os
import sys

# Настройка кодировки для Windows консоли
if sys.platform == "win32":
    import locale

    # Попытка установить UTF-8 кодировку
    try:
        locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, "Russian_Russia.1251")
        except locale.Error:
            pass

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ВНИМАНИЕ: секретный ключ должен быть изменен в продакшене!
SECRET_KEY = config(
    "SECRET_KEY", default="django-insecure-development-key-change-in-production"
)

# Основные Django приложения
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Сторонние приложения
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_redis",
    "drf_spectacular",
    "django_ratelimit",
    "django_filters",
]

# Локальные приложения FREESPORT
LOCAL_APPS = [
    "apps.users",
    "apps.products",
    "apps.orders",
    "apps.cart",
    "apps.pages",
    "apps.common",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware в порядке выполнения
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
]

ROOT_URLCONF = "freesport.urls"

# Конфигурация шаблонов
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "freesport.wsgi.application"

# Конфигурация базы данных PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="freesport"),
        "USER": config("DB_USER", default="freesport_user"),
        "PASSWORD": config("DB_PASSWORD", default="password"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432", cast=int),
    }
}

# Кастомная модель пользователя
AUTH_USER_MODEL = "users.User"

# Валидаторы паролей
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Конфигурация Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "PAGE_SIZE_QUERY_PARAM": "page_size",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Конфигурация JWT согласно Story 1.3
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
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
}

# Конфигурация Redis кеша
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Интернационализация
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Статические файлы
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Медиа файлы
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Тип первичного ключа по умолчанию
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Настройки документации API с drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "FREESPORT API",
    "DESCRIPTION": "RESTful API для B2B/B2C платформы спортивных товаров FREESPORT",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "ENABLE_DJANGO_DEPLOY_CHECK": False,
    "DISABLE_ERRORS_AND_WARNINGS": True,
    # OpenAPI 3.1 настройки согласно architecture.md
    "OAS_VERSION": "3.1.0",
    "SCHEMA_COERCE_METHOD_NAMES": {
        "retrieve": "get",
        "list": "list",
        "create": "create",
        "update": "update",
        "partial_update": "partial_update",
        "destroy": "delete",
    },
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
    },
    "REDOC_UI_SETTINGS": {
        "nativeScrollbars": True,
        "theme": {"colors": {"primary": {"main": "#1976d2"}}},
        "expandResponses": "200,201",
        "jsonSampleExpandLevel": 2,
    },
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "SERVE_AUTHENTICATION": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "POSTPROCESSING_HOOKS": ["drf_spectacular.hooks.postprocess_schema_enums"],
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": "drf_spectacular.utils.validation_error_enum_class",
    },
    "TAGS": [
        {"name": "Authentication", "description": "Аутентификация и JWT токены"},
        {"name": "Users", "description": "Управление пользователями и профилями"},
        {
            "name": "Products",
            "description": "Каталог товаров и управление ассортиментом",
        },
        {"name": "Cart", "description": "Корзина покупок"},
        {"name": "Orders", "description": "Управление заказами и их статусами"},
        {"name": "Search", "description": "Поиск и фильтрация товаров"},
        {"name": "System", "description": "Системные эндпоинты для мониторинга"},
        {"name": "Webhooks", "description": "Уведомления от внешних сервисов"},
    ],
    "SERVERS": [
        {"url": "http://127.0.0.1:8001", "description": "Development server"},
        {"url": "https://api.freesport.ru", "description": "Production server"},
    ],
    # OpenAPI 3.1 Extensions для будущих webhooks (ЮКасса)
    "EXTENSIONS_INFO": {
        "x-logo": {
            "url": "https://api.freesport.ru/static/logo.png",
            "altText": "FREESPORT API",
        }
    },
}

# Настройки безопасности (переопределяются в продакшене)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
