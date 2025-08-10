"""
Глобальные фикстуры pytest для проекта FREESPORT
Настройка базовых объектов и утилит для тестирования
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from tests.factories import UserFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Клиент DRF API для тестирования endpoints
    """
    return APIClient()


@pytest.fixture
def client():
    """
    Стандартный Django тест клиент
    """
    return Client()


@pytest.fixture
def user_factory():
    """
    Фабрика для создания пользователей
    """
    return UserFactory


@pytest.fixture
def retail_user(db):
    """
    Розничный пользователь
    """
    return UserFactory.create(role='retail')


@pytest.fixture
def wholesale_user(db):
    """
    Оптовый пользователь уровень 1
    """
    return UserFactory.create(role='wholesale_level1', is_verified=True)


@pytest.fixture
def trainer_user(db):
    """
    Пользователь-тренер
    """
    return UserFactory.create(role='trainer', is_verified=True)


@pytest.fixture
def admin_user(db):
    """
    Пользователь-администратор
    """
    return UserFactory.create(
        role='admin', 
        is_staff=True, 
        is_superuser=True, 
        is_verified=True
    )


@pytest.fixture
def authenticated_client(retail_user):
    """
    Создает и возвращает аутентифицированный API-клиент с retail пользователем
    """
    client = APIClient()
    refresh = RefreshToken.for_user(retail_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = retail_user  # Добавляем ссылку на пользователя для удобства
    return client


@pytest.fixture
def admin_client(admin_user):
    """
    Создает и возвращает API-клиент с правами администратора
    """
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    client.user = admin_user  # Добавляем ссылку на пользователя для удобства
    return client


@pytest.fixture
def mock_redis():
    """
    Mock для Redis в тестах
    """
    with patch('django_redis.cache.RedisCache') as mock:
        yield mock


@pytest.fixture
def mock_email():
    """
    Mock для отправки email в тестах
    """
    with patch('django.core.mail.send_mail') as mock:
        yield mock


@pytest.fixture
def sample_image():
    """
    Создает образец изображения для тестов
    """
    from PIL import Image
    from io import BytesIO
    from django.core.files.uploadedfile import InMemoryUploadedFile
    
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    
    return InMemoryUploadedFile(
        img_io, None, 'test.png', 'image/png', len(img_io.getvalue()), None
    )