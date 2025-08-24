
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models import User
from apps.products.models import Product, Brand, Category

# Используем маркер pytest для доступа к БД во всех тестах этого модуля
pytestmark = pytest.mark.django_db

TEST_USER_PASSWORD = 'TestPassword123!'

@pytest.fixture(scope='module')
def api_client():
    """Фикстура для создания клиента API."""
    return APIClient()

@pytest.fixture
def setup_test_data():
    """
    Фикстура для создания тестовых данных для каждого теста.
    """
    import uuid
    import time
    
    # Создаем уникальные имена с timestamp для избежания конфликтов
    unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    
    # Создаем бренд
    brand = Brand.objects.create(
        name=f'Nike-Test-{unique_suffix}',
        slug=f'nike-test-{unique_suffix}',
        description='Тестовый бренд Nike'
    )
    
    # Создаем категории
    parent_category = Category.objects.create(
        name=f'Спортивная-одежда-{unique_suffix}',
        slug=f'sportswear-{unique_suffix}',
        description='Одежда для спорта'
    )
    
    child_category = Category.objects.create(
        name=f'Футболки-{unique_suffix}',
        slug=f'tshirts-{unique_suffix}',
        description='Спортивные футболки',
        parent=parent_category
    )
    
    # Создаем товары
    products_data = [
        {
            'name': f'Nike Dri-FIT Футболка {unique_suffix}',
            'slug': f'nike-dri-fit-tshirt-{unique_suffix}',
            'sku': f'NIKE001-{unique_suffix}',
            'retail_price': 2500.00,
            'opt1_price': 2000.00,
            'trainer_price': 1900.00,
            'stock_quantity': 50
        },
        {
            'name': f'Nike Pro Футболка {unique_suffix}',
            'slug': f'nike-pro-tshirt-{unique_suffix}',
            'sku': f'NIKE002-{unique_suffix}',
            'retail_price': 3000.00,
            'stock_quantity': 0
        },
        {
            'name': f'Nike Club Футболка {unique_suffix}',
            'slug': f'nike-club-tshirt-{unique_suffix}',
            'sku': f'NIKE003-{unique_suffix}',
            'retail_price': 1800.00,
            'stock_quantity': 25,
            'is_featured': True
        }
    ]
    
    products = []
    for product_data in products_data:
        product = Product.objects.create(
            **product_data,
            brand=brand,
            category=child_category
        )
        products.append(product)
    
    return {
        'brand': brand,
        'category': child_category,
        'products': products,
        'unique_suffix': unique_suffix
    }

def register_and_login_user(api_client, role='retail'):
    """
    Регистрирует и авторизует пользователя с указанной ролью, возвращая токен.
    """
    api_client.credentials() # Сбрасываем аутентификацию перед регистрацией
    email = f'test_catalog_{role}@example.com'
    
    # Удаляем пользователя, если он существует, для чистоты теста
    User.objects.filter(email=email).delete()
    
    registration_data = {
        'email': email, 'password': TEST_USER_PASSWORD, 'password_confirm': TEST_USER_PASSWORD,
        'first_name': 'Тест', 'last_name': f'Пользователь {role}', 'role': role
    }
    if role != 'retail':
        registration_data.update({'company_name': f'Тестовая компания {role}', 'tax_id': '1234567890'})

    # Регистрация
    url = reverse('users:register') # Предполагается, что у вас есть именованный URL 'register'
    response = api_client.post(url, registration_data, format='json')
    assert response.status_code == 201, f"Registration failed for role {role} with status {response.status_code}"

    # Авторизация
    url = reverse('users:login') # Предполагается, что у вас есть именованный URL 'login'
    response = api_client.post(url, {'email': email, 'password': TEST_USER_PASSWORD}, format='json')
    assert response.status_code == 200, f"Login failed for role {role} with status {response.status_code}"
    
    return response.data['access']

def test_products_list(api_client, setup_test_data):
    """Тестирование GET /products/ (AC 1)"""
    url = reverse('products:product-list') # Предполагается имя URL 'product-list'
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data['count'] > 0
    assert len(data['results']) > 0
    assert 'current_price' in data['results'][0]

def test_products_filtering(api_client, setup_test_data):
    """Тестирование фильтрации товаров (AC 3)"""
    url = reverse('products:product-list')
    
    # Фильтр по наличию
    response = api_client.get(url, {'in_stock': 'true'})
    assert response.status_code == 200
    assert response.json()['count'] == 2 # 2 из 3 товаров в наличии

    # Фильтр по цене
    response = api_client.get(url, {'min_price': 2000, 'max_price': 3000})
    assert response.status_code == 200
    assert response.json()['count'] == 2 # 2 из 3 товаров в наличии

def test_products_sorting(api_client, setup_test_data):
    """Тестирование сортировки товаров (AC 4)"""
    url = reverse('products:product-list')
    
    # Сортировка по названию (A-Z)
    response = api_client.get(url, {'ordering': 'name'})
    assert response.status_code == 200
    names = [p['name'] for p in response.json()['results']]
    assert names == sorted(names)

    # Сортировка по цене (убывание)
    response = api_client.get(url, {'ordering': '-retail_price'})
    assert response.status_code == 200
    prices = [p['retail_price'] for p in response.json()['results']]
    assert prices == sorted(prices, reverse=True)

def test_role_based_pricing(api_client, setup_test_data):
    """Тестирование ролевого ценообразования (AC 5)"""
    url = reverse('products:product-list')
    product_sku = setup_test_data['products'][0].sku  # Используем динамический SKU

    # 1. Анонимный пользователь (видит розничную цену)
    response = api_client.get(url, {'search': product_sku})
    assert response.status_code == 200
    assert response.json()['results'][0]['current_price'] == '2500.00'

    # 2. Пользователь 'retail'
    token = register_and_login_user(api_client, 'retail')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    response = api_client.get(url, {'search': product_sku})
    assert response.status_code == 200
    assert response.json()['results'][0]['current_price'] == '2500.00'
    
    # 3. Пользователь 'wholesale_level1'
    token = register_and_login_user(api_client, 'wholesale_level1')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    response = api_client.get(url, {'search': product_sku})
    assert response.status_code == 200
    assert response.json()['results'][0]['current_price'] == '2000.00'

    # 4. Пользователь 'trainer'
    token = register_and_login_user(api_client, 'trainer')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    response = api_client.get(url, {'search': product_sku})
    assert response.status_code == 200
    assert response.json()['results'][0]['current_price'] == '1900.00'

def test_categories_api(api_client, setup_test_data):
    """Тестирование GET /categories/ (AC 2)"""
    token = register_and_login_user(api_client, 'retail')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    url = reverse('products:category-list') # Предполагается имя URL 'category-list'
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()['results']
    # Проверяем, что есть хотя бы одна категория
    assert len(data) > 0
    # Проверяем иерархию
    parent_category = next(c for c in data if c['parent'] is None)
    assert len(parent_category['children']) > 0

def test_brands_api(api_client, setup_test_data):
    """Тестирование GET /brands/"""
    api_client.credentials() # Сбрасываем аутентификацию
    url = reverse('products:brand-list') # Предполагается имя URL 'brand-list'
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()['count'] > 0

def test_product_detail_api(api_client, setup_test_data):
    """Тестирование GET /products/{id}/"""
    token = register_and_login_user(api_client, 'retail')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    # Сначала получаем ID продукта
    list_url = reverse('products:product-list')
    product_id = api_client.get(list_url).json()['results'][0]['id']
    
    detail_url = reverse('products:product-detail', kwargs={'pk': product_id})
    response = api_client.get(detail_url)
    assert response.status_code == 200
    assert response.json()['id'] == product_id
    assert 'category_breadcrumbs' in response.json()
