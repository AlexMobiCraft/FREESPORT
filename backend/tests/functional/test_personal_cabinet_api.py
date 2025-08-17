#!/usr/bin/env python
"""
Тестирование API личного кабинета Story 2.3
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
TEST_USER_EMAIL = 'test_cabinet@example.com'
TEST_USER_PASSWORD = 'TestPassword123!'

def print_test_result(test_name, success, details=""):
    """Вывод результата теста"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

def register_test_user():
    """Регистрация тестового пользователя"""
    print("\n=== Регистрация тестового пользователя ===")
    
    # Проверяем существование пользователя
    if User.objects.filter(email=TEST_USER_EMAIL).exists():
        User.objects.filter(email=TEST_USER_EMAIL).delete()
    
    registration_data = {
        'email': TEST_USER_EMAIL,
        'password': TEST_USER_PASSWORD,
        'password_confirm': TEST_USER_PASSWORD,
        'first_name': 'Тест',
        'last_name': 'Пользователь',
        'role': 'retail'
    }
    
    response = requests.post(f"{BASE_URL}/auth/register/", json=registration_data)
    success = response.status_code == 201
    print_test_result("Регистрация пользователя", success, 
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

def test_dashboard(access_token):
    """Тестирование дашборда"""
    print("\n=== Тестирование дашборда ===")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"{BASE_URL}/users/profile/dashboard/", headers=headers)
    
    success = response.status_code == 200
    print_test_result("GET /users/profile/dashboard/", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        print(f"   Счетчики: заказы={data.get('orders_count', 0)}, "
              f"избранное={data.get('favorites_count', 0)}, "
              f"адреса={data.get('addresses_count', 0)}")

def test_addresses(access_token):
    """Тестирование управления адресами"""
    print("\n=== Тестирование адресов ===")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Тест создания адреса
    address_data = {
        'address_type': 'shipping',
        'full_name': 'Тест Пользователь',
        'phone': '+79001234567',
        'city': 'Москва',
        'street': 'Тестовая улица',
        'building': '1',
        'apartment': '10',
        'postal_code': '123456',
        'is_default': True
    }
    
    response = requests.post(f"{BASE_URL}/users/addresses/", 
                           json=address_data, headers=headers)
    success = response.status_code == 201
    print_test_result("POST /users/addresses/ (создание)", success, 
                     f"Status: {response.status_code}")
    
    address_id = None
    if success:
        address_id = response.json()['id']
    
    # Тест получения списка адресов
    response = requests.get(f"{BASE_URL}/users/addresses/", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /users/addresses/ (список)", success, 
                     f"Status: {response.status_code}")
    
    if success and address_id:
        addresses = response.json()['results'] if 'results' in response.json() else response.json()
        print(f"   Найдено адресов: {len(addresses) if isinstance(addresses, list) else 1}")
        
        # Тест обновления адреса
        update_data = {'city': 'Санкт-Петербург'}
        response = requests.patch(f"{BASE_URL}/users/addresses/{address_id}/", 
                                json=update_data, headers=headers)
        success = response.status_code == 200
        print_test_result("PATCH /users/addresses/{id}/ (обновление)", success, 
                         f"Status: {response.status_code}")

def test_favorites(access_token):
    """Тестирование избранного"""
    print("\n=== Тестирование избранного ===")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Создаем тестовый товар если его нет
    if not Product.objects.exists():
        # Создаем бренд и категорию
        brand, _ = Brand.objects.get_or_create(name='Test Brand', defaults={'slug': 'test-brand'})
        category, _ = Category.objects.get_or_create(name='Test Category', defaults={'slug': 'test-category'})
        
        Product.objects.create(
            name='Тестовый товар',
            slug='test-product',
            brand=brand,
            category=category,
            description='Описание тестового товара',
            retail_price=1000.00,
            sku='TEST001',
            main_image='test.jpg'
        )
    
    product = Product.objects.first()
    
    # Тест добавления в избранное
    favorite_data = {'product': product.id}
    response = requests.post(f"{BASE_URL}/users/favorites/", 
                           json=favorite_data, headers=headers)
    success = response.status_code == 201
    print_test_result("POST /users/favorites/ (добавление)", success, 
                     f"Status: {response.status_code}")
    
    # Тест получения избранного
    response = requests.get(f"{BASE_URL}/users/favorites/", headers=headers)
    success = response.status_code == 200
    print_test_result("GET /users/favorites/ (список)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        favorites = response.json()['results'] if 'results' in response.json() else response.json()
        if isinstance(favorites, list) and len(favorites) > 0:
            print(f"   Товаров в избранном: {len(favorites)}")
            favorite_id = favorites[0]['id']
            
            # Тест удаления из избранного
            response = requests.delete(f"{BASE_URL}/users/favorites/{favorite_id}/", headers=headers)
            success = response.status_code == 204
            print_test_result("DELETE /users/favorites/{id}/ (удаление)", success, 
                             f"Status: {response.status_code}")

def test_orders_history(access_token):
    """Тестирование истории заказов"""
    print("\n=== Тестирование истории заказов ===")
    
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"{BASE_URL}/users/orders/", headers=headers)
    
    success = response.status_code == 200
    print_test_result("GET /users/orders/ (история заказов)", success, 
                     f"Status: {response.status_code}")
    
    if success:
        data = response.json()
        print(f"   Заказов найдено: {data.get('count', 0)} (ожидается 0 - заглушка)")

def main():
    """Основная функция тестирования"""
    print("Тестирование Personal Cabinet API (Story 2.3)")
    print("=" * 50)
    
    # Регистрация пользователя
    if not register_test_user():
        print("[ERROR] Не удалось зарегистрировать пользователя. Тесты прерваны.")
        return
    
    # Авторизация
    access_token = login_and_get_tokens()
    if not access_token:
        print("[ERROR] Не удалось получить токен доступа. Тесты прерваны.")
        return
    
    # Запуск тестов
    test_dashboard(access_token)
    test_addresses(access_token)
    test_favorites(access_token)
    test_orders_history(access_token)
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Тестирование завершено!")

if __name__ == '__main__':
    main()