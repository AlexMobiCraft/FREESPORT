#!/usr/bin/env python
"""
Тестирование Catalog API Story 2.4
"""
import os
import sys
import django
import requests
import json

# Настройка Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.users.models import User
from apps.products.models import Product, Brand, Category

# Конфигурация для тестов
BASE_URL = 'http://127.0.0.1:8001/api/v1'
TEST_USER_EMAIL = 'test_catalog@example.com'
TEST_USER_PASSWORD = 'TestPassword123!'

def print_test_result(test_name, success, details=""):
    """Вывод результата теста"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

def create_test_data():
    """Создание тестовых данных для каталога"""
    print("\n=== Создание тестовых данных ===")
    
    # Создаем бренды
    brand1, _ = Brand.objects.get_or_create(
        name='Nike',
        defaults={'slug': 'nike', 'description': 'Спортивная одежда Nike'}
    )
    brand2, _ = Brand.objects.get_or_create(
        name='Adidas', 
        defaults={'slug': 'adidas', 'description': 'Спортивная одежда Adidas'}
    )
    
    # Создаем категории
    cat_sport, _ = Category.objects.get_or_create(
        name='Спорт',
        defaults={'slug': 'sport', 'description': 'Спортивные товары'}
    )
    cat_shoes, _ = Category.objects.get_or_create(
        name='Обувь',
        defaults={'slug': 'shoes', 'parent': cat_sport, 'description': 'Спортивная обувь'}
    )
    
    # Создаем товары с разными ценами для ролей
    products_data = [
        {
            'name': 'Nike Air Max',
            'slug': 'nike-air-max',
            'sku': 'NIKE001',
            'brand': brand1,
            'category': cat_shoes,
            'description': 'Классические кроссовки Nike Air Max',
            'retail_price': 8000.00,
            'opt1_price': 7000.00,
            'opt2_price': 6500.00,
            'opt3_price': 6000.00,
            'trainer_price': 7200.00,
            'federation_price': 6800.00,
            'stock_quantity': 50,
            'main_image': 'nike-air-max.jpg'
        },
        {
            'name': 'Adidas Superstar',
            'slug': 'adidas-superstar',
            'sku': 'ADIDAS001',
            'brand': brand2,
            'category': cat_shoes,
            'description': 'Легендарные кроссовки Adidas Superstar',
            'retail_price': 7000.00,
            'opt1_price': 6200.00,
            'opt2_price': 5800.00,
            'opt3_price': 5400.00,
            'trainer_price': 6300.00,
            'federation_price': 5900.00,
            'stock_quantity': 0,  # Нет в наличии
            'main_image': 'adidas-superstar.jpg'
        },
        {
            'name': 'Nike Running Shorts',
            'slug': 'nike-running-shorts',
            'sku': 'NIKE002',
            'brand': brand1,
            'category': cat_sport,
            'description': 'Спортивные шорты для бега',
            'retail_price': 3000.00,
            'opt1_price': 2700.00,
            'opt2_price': 2500.00,
            'opt3_price': 2300.00,
            'trainer_price': 2600.00,
            'federation_price': 2400.00,
            'stock_quantity': 100,
            'is_featured': True,
            'main_image': 'nike-shorts.jpg'
        }
    ]
    
    for product_data in products_data:
        Product.objects.get_or_create(
            sku=product_data['sku'],
            defaults=product_data
        )
    
    print(f"   Создано брендов: {Brand.objects.count()}")
    print(f"   Создано категорий: {Category.objects.count()}")
    print(f"   Создано товаров: {Product.objects.count()}")

def register_test_user():
    """Регистрация тестового пользователя"""
    print("\n=== Регистрация B2B пользователя ===")
    
    # Проверяем существование пользователя
    if User.objects.filter(email=TEST_USER_EMAIL).exists():
        User.objects.filter(email=TEST_USER_EMAIL).delete()
    
    registration_data = {
        'email': TEST_USER_EMAIL,
        'password': TEST_USER_PASSWORD,
        'password_confirm': TEST_USER_PASSWORD,
        'first_name': 'Тест',
        'last_name': 'Оптовик',
        'role': 'wholesale_level2',
        'company_name': 'Тестовая компания',
        'tax_id': '1234567890'
    }
    
    response = requests.post(f"{BASE_URL}/auth/register/", json=registration_data)
    success = response.status_code == 201
    print_test_result("Регистрация B2B пользователя", success, 
                     f"Status: {response.status_code}")
    
    return success

def login_and_get_tokens():
    """Авторизация и получение токенов"""
    print("\n=== Авторизация ===")
    
    login_data = {
        'email': TEST_USER_EMAIL,
        'password': TEST_USER_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    success = response.status_code == 200
    print_test_result("Авторизация", success, f"Status: {response.status_code}")
    
    if success:
        tokens = response.json()
        return tokens['access']
    return None

def test_products_list(access_token=None):
    """Тестирование списка товаров"""
    print("\n=== Тестирование Products API ===")
    
    headers = {}
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    
    # Тест получения списка товаров
    response = requests.get(f"{BASE_URL}/products/", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/ (список товаров)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        products = data.get('results', [])
        print(f"   Найдено товаров: {len(products)}")
        
        if products:
            product = products[0]
            print(f"   Первый товар: {product.get('name')} - {product.get('current_price')} руб.")
            print(f"   Тип цены: {product.get('price_type')}")
            
            if access_token and product.get('price_type') == 'wholesale_level2':
                print(f"   RRP: {product.get('recommended_retail_price')}")
    
    # Тест фильтрации по категории
    response = requests.get(f"{BASE_URL}/products/?category_id=1", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/?category_id=1 (фильтр по категории)", success, 
                     f"Status: {response.status_code}")
    
    # Тест фильтрации по цене
    response = requests.get(f"{BASE_URL}/products/?min_price=5000&max_price=8000", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/?min_price=5000&max_price=8000 (ценовой фильтр)", success, 
                     f"Status: {response.status_code}")
    
    # Тест фильтрации по наличию
    response = requests.get(f"{BASE_URL}/products/?in_stock=true", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/?in_stock=true (товары в наличии)", success, 
                     f"Status: {response.status_code}")
    
    # Тест сортировки
    response = requests.get(f"{BASE_URL}/products/?ordering=-retail_price", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/?ordering=-retail_price (сортировка по цене)", success, 
                     f"Status: {response.status_code}")
    
    # Тест поиска
    response = requests.get(f"{BASE_URL}/products/?search=Nike", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /products/?search=Nike (поиск)", success, 
                     f"Status: {response.status_code}")

def test_categories():
    """Тестирование категорий"""
    print("\n=== Тестирование Categories API ===")
    
    # Тест получения списка категорий
    response = requests.get(f"{BASE_URL}/categories/")
    success = response.status_code == 200
    print_test_result("GET /categories/ (список категорий)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        categories = data.get('results', [])
        print(f"   Найдено категорий: {len(categories)}")
        
        if categories:
            category = categories[0]
            print(f"   Первая категория: {category.get('name')} ({category.get('products_count')} товаров)")
    
    # Тест дерева категорий
    response = requests.get(f"{BASE_URL}/categories-tree/")
    success = response.status_code == 200
    print_test_result("GET /categories-tree/ (дерево категорий)", success, 
                     f"Status: {response.status_code}")

def test_brands():
    """Тестирование брендов"""
    print("\n=== Тестирование Brands API ===")
    
    # Тест получения списка брендов
    response = requests.get(f"{BASE_URL}/brands/")
    success = response.status_code == 200
    print_test_result("GET /brands/ (список брендов)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        brands = data.get('results', [])
        print(f"   Найдено брендов: {len(brands)}")

def test_anonymous_vs_authenticated():
    """Тестирование ролевого ценообразования"""
    print("\n=== Тестирование ролевого ценообразования ===")
    
    # Анонимный пользователь (розничные цены)
    response_anon = requests.get(f"{BASE_URL}/products/")
    
    # B2B пользователь с токеном
    access_token = login_and_get_tokens()
    headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
    response_b2b = requests.get(f"{BASE_URL}/products/", headers=headers)
    
    if response_anon.status_code == 200 and response_b2b.status_code == 200:
        anon_products = response_anon.json().get('results', [])
        b2b_products = response_b2b.json().get('results', [])
        
        if anon_products and b2b_products:
            anon_price = anon_products[0].get('current_price')
            b2b_price = b2b_products[0].get('current_price')
            
            print(f"   Анонимный пользователь: {anon_price} руб. (retail)")
            print(f"   B2B пользователь: {b2b_price} руб. (wholesale_level2)")
            
            # Проверяем наличие RRP/MSRP для B2B
            rrp = b2b_products[0].get('recommended_retail_price')
            if rrp:
                print(f"   RRP для B2B: {rrp} руб.")
            
            success = anon_price != b2b_price
            print_test_result("Ролевое ценообразование работает", success)

def main():
    """Основная функция тестирования"""
    print("Тестирование Catalog API (Story 2.4)")
    print("=" * 50)
    
    # Создание тестовых данных
    create_test_data()
    
    # Регистрация пользователя
    if not register_test_user():
        print("[ERROR] Не удалось зарегистрировать пользователя")
    
    # Авторизация
    access_token = login_and_get_tokens()
    
    # Запуск тестов
    test_products_list()  # Без токена (анонимно)
    test_products_list(access_token)  # С токеном (B2B)
    test_categories()
    test_brands()
    test_anonymous_vs_authenticated()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Тестирование завершено!")

if __name__ == '__main__':
    main()