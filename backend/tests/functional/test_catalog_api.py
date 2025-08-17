#!/usr/bin/env python
"""
Тестирование Catalog API (Story 2.4)
"""
import os
import sys
import django
import requests
import json

# Настройка Django environment
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings')
django.setup()

from apps.users.models import User
from apps.products.models import Product, Brand, Category

# Конфигурация для тестов
BASE_URL = 'http://127.0.0.1:8001/api/v1'
TEST_USER_PASSWORD = 'TestPassword123!'

def print_test_result(test_name, success, details=""):
    """Вывод результата теста"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

def setup_test_data():
    """Создание тестовых данных для каталога"""
    print("\n=== Подготовка тестовых данных ===")
    
    # Создаем бренд
    brand, created = Brand.objects.get_or_create(
        name='Nike Test',
        defaults={'slug': 'nike-test', 'description': 'Тестовый бренд Nike'}
    )
    print(f"Бренд: {'создан' if created else 'найден'} - {brand.name}")
    
    # Создаем категории
    parent_category, created = Category.objects.get_or_create(
        name='Спортивная одежда',
        defaults={'slug': 'sportswear', 'description': 'Одежда для спорта'}
    )
    print(f"Родительская категория: {'создана' if created else 'найдена'} - {parent_category.name}")
    
    child_category, created = Category.objects.get_or_create(
        name='Футболки',
        defaults={
            'slug': 'tshirts',
            'description': 'Спортивные футболки',
            'parent': parent_category
        }
    )
    print(f"Дочерняя категория: {'создана' if created else 'найдена'} - {child_category.name}")
    
    # Создаем товары с разными ценами
    products_data = [
        {
            'name': 'Nike Dri-FIT Футболка',
            'slug': 'nike-dri-fit-tshirt',
            'sku': 'NIKE001',
            'retail_price': 2500.00,
            'opt1_price': 2000.00,
            'opt2_price': 1800.00,
            'opt3_price': 1600.00,
            'trainer_price': 1900.00,
            'federation_price': 1500.00,
            'stock_quantity': 50
        },
        {
            'name': 'Nike Pro Футболка',
            'slug': 'nike-pro-tshirt',
            'sku': 'NIKE002',
            'retail_price': 3000.00,
            'opt1_price': 2400.00,
            'stock_quantity': 0  # Нет в наличии
        },
        {
            'name': 'Nike Club Футболка',
            'slug': 'nike-club-tshirt',
            'sku': 'NIKE003',
            'retail_price': 1800.00,
            'opt2_price': 1400.00,
            'stock_quantity': 25,
            'is_featured': True
        }
    ]
    
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            sku=product_data['sku'],
            defaults={
                **product_data,
                'brand': brand,
                'category': child_category,
                'description': f"Описание {product_data['name']}",
                'short_description': f"Краткое описание {product_data['name']}"
            }
        )
        print(f"Товар: {'создан' if created else 'найден'} - {product.name}")
    
    return brand, parent_category, child_category

def register_and_login_user(role='retail'):
    """Регистрация и авторизация пользователя с указанной ролью"""
    email = f'test_catalog_{role}@example.com'
    
    # Удаляем если существует
    if User.objects.filter(email=email).exists():
        User.objects.filter(email=email).delete()
    
    registration_data = {
        'email': email,
        'password': TEST_USER_PASSWORD,
        'password_confirm': TEST_USER_PASSWORD,
        'first_name': 'Тест',
        'last_name': f'Пользователь {role}',
        'role': role
    }
    
    # Добавляем B2B поля для соответствующих ролей
    if role in ['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer', 'federation_rep']:
        registration_data.update({
            'company_name': f'Тестовая компания {role}',
            'tax_id': '1234567890'
        })
    
    # Регистрация
    response = requests.post(f"{BASE_URL}/auth/register/", json=registration_data)
    if response.status_code != 201:
        print(f"[ERROR] Регистрация пользователя {role}: {response.status_code}")
        return None
    
    # Авторизация
    login_data = {'email': email, 'password': TEST_USER_PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    if response.status_code == 200:
        return response.json()['access']
    
    print(f"[ERROR] Авторизация пользователя {role}: {response.status_code}")
    return None

def test_products_list():
    """Тестирование GET /products/"""
    print("\n=== Тестирование списка товаров ===")
    
    response = requests.get(f"{BASE_URL}/products/")
    success = response.status_code == 200
    print_test_result("GET /products/ (список товаров)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        count = data.get('count', 0)
        results = data.get('results', [])
        print(f"   Найдено товаров: {count}")
        print(f"   Возвращено в результате: {len(results)}")
        
        if results:
            first_product = results[0]
            print(f"   Первый товар: {first_product.get('name')} - {first_product.get('current_price')} руб.")
    
    return success

def test_products_filtering():
    """Тестирование фильтрации товаров"""
    print("\n=== Тестирование фильтрации товаров ===")
    
    # Проверяем фильтр по наличию
    response = requests.get(f"{BASE_URL}/products/?in_stock=true")
    success = response.status_code == 200
    print_test_result("GET /products/?in_stock=true", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        in_stock_count = data.get('count', 0)
        print(f"   Товаров в наличии: {in_stock_count}")
    
    # Проверяем фильтр по цене
    response = requests.get(f"{BASE_URL}/products/?min_price=2000&max_price=3000")
    success = response.status_code == 200
    print_test_result("GET /products/?min_price=2000&max_price=3000", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        filtered_count = data.get('count', 0)
        print(f"   Товаров в ценовом диапазоне 2000-3000: {filtered_count}")
    
    # Проверяем фильтр рекомендуемых товаров
    response = requests.get(f"{BASE_URL}/products/?is_featured=true")
    success = response.status_code == 200
    print_test_result("GET /products/?is_featured=true", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        featured_count = data.get('count', 0)
        print(f"   Рекомендуемых товаров: {featured_count}")

def test_products_sorting():
    """Тестирование сортировки товаров"""
    print("\n=== Тестирование сортировки товаров ===")
    
    # Сортировка по названию
    response = requests.get(f"{BASE_URL}/products/?ordering=name")
    success = response.status_code == 200
    print_test_result("GET /products/?ordering=name", success, 
                     f"Status: {response.status_code}")
    
    # Сортировка по цене (убывание)
    response = requests.get(f"{BASE_URL}/products/?ordering=-retail_price")
    success = response.status_code == 200
    print_test_result("GET /products/?ordering=-retail_price", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        results = data.get('results', [])
        if len(results) >= 2:
            print(f"   Первый товар: {results[0].get('name')} - {results[0].get('current_price')} руб.")
            print(f"   Второй товар: {results[1].get('name')} - {results[1].get('current_price')} руб.")

def test_role_based_pricing():
    """Тестирование ролевого ценообразования"""
    print("\n=== Тестирование ролевого ценообразования ===")
    
    # Получаем конкретный товар для проверки цен
    product_sku = 'NIKE001'
    
    # Тест для retail пользователя
    retail_token = register_and_login_user('retail')
    if retail_token:
        headers = {'Authorization': f'Bearer {retail_token}'}
        response = requests.get(f"{BASE_URL}/products/?search={product_sku}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                product = data['results'][0]
                retail_price = product['current_price']
                print_test_result("Ценообразование для retail", True, 
                                 f"Цена: {retail_price} руб.")
    
    # Тест для wholesale_level1 пользователя
    wholesale_token = register_and_login_user('wholesale_level1')
    if wholesale_token:
        headers = {'Authorization': f'Bearer {wholesale_token}'}
        response = requests.get(f"{BASE_URL}/products/?search={product_sku}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                product = data['results'][0]
                wholesale_price = product['current_price']
                rrp = product.get('recommended_retail_price')
                print_test_result("Ценообразование для wholesale_level1", True, 
                                 f"Цена: {wholesale_price} руб., RRP: {rrp}")
    
    # Тест для trainer пользователя
    trainer_token = register_and_login_user('trainer')
    if trainer_token:
        headers = {'Authorization': f'Bearer {trainer_token}'}
        response = requests.get(f"{BASE_URL}/products/?search={product_sku}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                product = data['results'][0]
                trainer_price = product['current_price']
                print_test_result("Ценообразование для trainer", True, 
                                 f"Цена: {trainer_price} руб.")

def test_categories():
    """Тестирование категорий"""
    print("\n=== Тестирование категорий ===")
    
    # Тест списка категорий
    response = requests.get(f"{BASE_URL}/categories/")
    success = response.status_code == 200
    print_test_result("GET /categories/ (список категорий)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        categories = data.get('results', data) if isinstance(data, dict) and 'results' in data else data
        print(f"   Найдено категорий: {len(categories) if isinstance(categories, list) else 1}")
        
        if isinstance(categories, list) and categories:
            first_category = categories[0]
            print(f"   Первая категория: {first_category.get('name')}")
            if first_category.get('children'):
                print(f"   Дочерних категорий: {len(first_category['children'])}")
    
    # Тест дерева категорий
    response = requests.get(f"{BASE_URL}/categories-tree/")
    success = response.status_code == 200
    print_test_result("GET /categories-tree/ (дерево категорий)", success, 
                     f"Status: {response.status_code}")

def test_brands():
    """Тестирование брендов"""
    print("\n=== Тестирование брендов ===")
    
    response = requests.get(f"{BASE_URL}/brands/")
    success = response.status_code == 200
    print_test_result("GET /brands/ (список брендов)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        brands = data.get('results', data) if isinstance(data, dict) and 'results' in data else data
        print(f"   Найдено брендов: {len(brands) if isinstance(brands, list) else 1}")

def test_product_detail():
    """Тестирование детального просмотра товара"""
    print("\n=== Тестирование детального просмотра товара ===")
    
    # Получаем список товаров для получения ID
    response = requests.get(f"{BASE_URL}/products/")
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        if results:
            product_id = results[0]['id']
            
            # Тестируем детальный просмотр
            response = requests.get(f"{BASE_URL}/products/{product_id}/")
            success = response.status_code == 200
            print_test_result(f"GET /products/{product_id}/ (детали товара)", success, 
                             f"Status: {response.status_code}")
            
            if success:
                product = response.json()
                print(f"   Товар: {product.get('name')}")
                print(f"   Описание: {product.get('description', 'Нет')[:50]}...")
                print(f"   Категории в breadcrumbs: {len(product.get('category_breadcrumbs', []))}")

def main():
    """Основная функция тестирования"""
    print("Тестирование Catalog API (Story 2.4)")
    print("=" * 50)
    
    # Подготавливаем тестовые данные
    setup_test_data()
    
    # Запуск тестов
    test_products_list()
    test_products_filtering()
    test_products_sorting()
    test_role_based_pricing()
    test_categories()
    test_brands()
    test_product_detail()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Тестирование Catalog API завершено!")

if __name__ == '__main__':
    main()