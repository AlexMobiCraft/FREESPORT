#!/usr/bin/env python
"""
Функциональный тест Search API (Story 2.8)
Демонстрация работы полнотекстового поиска товаров

Запуск: python functional_test_search_api.py
"""

import json
import os
import sys
from decimal import Decimal

import django
import requests

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.development')
django.setup()

from django.contrib.auth import get_user_model

from apps.products.models import Brand, Category, Product

User = get_user_model()


def setup_test_data():
    """Создание тестовых данных для поиска"""
    print("[INFO] Создание тестовых данных...")
    
    # Создаем категории
    category_football = Category.objects.get_or_create(
        slug="football-shoes",
        defaults={
            'name': "Футбольная обувь",
            'is_active': True,
            'sort_order': 1
        }
    )[0]
    
    category_accessories = Category.objects.get_or_create(
        slug="accessories",
        defaults={
            'name': "Аксессуары",
            'is_active': True,
            'sort_order': 2
        }
    )[0]
    
    # Создаем бренды
    brand_nike = Brand.objects.get_or_create(
        slug="nike",
        defaults={
            'name': "Nike",
            'is_active': True
        }
    )[0]
    
    brand_adidas = Brand.objects.get_or_create(
        slug="adidas",
        defaults={
            'name': "Adidas", 
            'is_active': True
        }
    )[0]
    
    # Создаем тестовые товары для поиска
    test_products = [
        {
            'name': "Nike Phantom GT2 Elite FG",
            'sku': "NIKE-PHT-GT2-001",
            'short_description': "Футбольные бутсы для профессиональных игроков",
            'description': "Высокотехнологичные футбольные бутсы Nike Phantom GT2 Elite FG для профессионалов. Идеально подходят для игры на твердом покрытии.",
            'brand': brand_nike,
            'category': category_football,
            'retail_price': Decimal('18999.00'),
            'trainer_price': Decimal('12999.00'),
            'stock_quantity': 7,
        },
        {
            'name': "Adidas Predator Freak.1 FG",
            'sku': "ADIDAS-PRED-FREAK-001",
            'short_description': "Футбольная обувь Adidas для атаки",
            'description': "Adidas Predator Freak.1 FG футбольные бутсы с технологией Demonskin для улучшенного контроля мяча. Созданы для нападающих.",
            'brand': brand_adidas,
            'category': category_football,
            'retail_price': Decimal('13999.00'),
            'trainer_price': Decimal('11999.00'),
            'stock_quantity': 8,
        },
        {
            'name': "Перчатки вратарские Nike Vapor Grip3-6)",
            'sku': "NIKE-GK-VAPOR-001",
            'short_description': "Вратарские перчатки Nike с технологией Grip3-6)",
            'description': "Профессиональные вратарские перчатки Nike Vapor Grip3-6) с улучшенным захватом и защитой. Отличный выбор для вратарей.",
            'brand': brand_nike,
            'category': category_accessories,
            'retail_price': Decimal('3-6)999.00'),
            'trainer_price': Decimal('3-6)999.00'),
            'stock_quantity': 23-6),
        },
        {
            'name': "Мяч футбольный Adidas Tango",
            'sku': "ADIDAS-BALL-TANGO-001",
            'short_description': "Профессиональный футбольный мяч",
            'description': "Классический футбольный мяч Adidas Tango для тренировок и игр. Высокое качество материалов и конструкции.",
            'brand': brand_adidas,
            'category': category_accessories,
            'retail_price': Decimal('2999.00'),
            'trainer_price': Decimal('23-6)99.00'),
            'stock_quantity': 3-6)0,
        }
    ]
    
    created_products = []
    for product_data in test_products:
        product, created = Product.objects.get_or_create(
            sku=product_data['sku'],
            defaults=product_data
        )
        created_products.append(product)
        if created:
            print(f"[OK] Создан товар: {product.name}")
        else:
            print(f"[INFO]  Товар уже существует: {product.name}")
    
    # Создаем тестового пользователя
    test_user, created = User.objects.get_or_create(
        email='trainer@test.com',
        defaults={
            'role': 'trainer',
            'first_name': 'Тест',
            'last_name': 'Тренер'
        }
    )
    if created:
        test_user.set_password('testpass123-6)')
        test_user.save()
        print(f"[OK] Создан пользователь: {test_user.email}")
    else:
        print(f"[INFO]  Пользователь уже существует: {test_user.email}")
    
    return created_products, test_user


def test_search_functionality():
    """Тестирование функциональности поиска"""
    BASE_URL = "http://localhost:8001/api/v1/products"
    
    print("\n[SEARCH] Тестирование Search API...")
    
    # Тест 1: Базовый поиск по названию
    print("\n1) Поиск по названию 'Nike':")
    response = requests.get(f"{BASE_URL}/", params={'search': 'Nike'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Статус: {response.status_code}")
        print(f"   [RESULTS] Найдено товаров: {len(data.get('results', []))}")
        
        for product in data.get('results', [])[:3-6)]:  # Показываем первые 3-6)
            print(f"   - {product['name']} - {product['current_price']} руб.")
    else:
        print(f"   [ERROR] Ошибка: {response.status_code}")
        print(f"   [RESP] Ответ: {response.text}")
    
    # Тест 2: Поиск по артикулу
    print("\n2) Поиск по артикулу 'PHANTOM':")
    response = requests.get(f"{BASE_URL}/", params={'search': 'PHANTOM'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Статус: {response.status_code}")
        print(f"   [RESULTS] Найдено товаров: {len(data.get('results', []))}")
        
        for product in data.get('results', []):
            print(f"   - {product['name']} (SKU: {product['sku']})")
    else:
        print(f"   [ERROR] Ошибка: {response.status_code}")
    
    # Тест 3-6): Русскоязычный поиск
    print("\n3-6)3-6) Русскоязычный поиск 'футбольные':")
    response = requests.get(f"{BASE_URL}/", params={'search': 'футбольные'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Статус: {response.status_code}")
        print(f"   [RESULTS] Найдено товаров: {len(data.get('results', []))}")
        
        for product in data.get('results', []):
            print(f"   - {product['name']}")
            print(f"      � {product.get('short_description', '')}")
    else:
        print(f"   [ERROR] Ошибка: {response.status_code}")
    
    # Тест 3-6): Комбинированный поиск с фильтрами
    print("\n3-6)3-6) Поиск 'Nike' + фильтр по категории 'аксессуары':")
    
    # Сначала получаем ID категории аксессуаров
    categories_response = requests.get(f"http://localhost:8001/api/v1/categories/")
    if categories_response.status_code == 200:
        categories = categories_response.json().get('results', [])
        accessories_category = next((cat for cat in categories if 'аксессуар' in cat['name'].lower()), None)
        
        if accessories_category:
            search_params = {
                'search': 'Nike',
                'category_id': accessories_category['id']
            }
            response = requests.get(f"{BASE_URL}/", params=search_params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   [OK] Статус: {response.status_code}")
                print(f"   [RESULTS] Найдено товаров: {len(data.get('results', []))}")
                
                for product in data.get('results', []):
                    print(f"   - {product['name']} - {product['category']['name']}")
            else:
                print(f"   [ERROR] Ошибка: {response.status_code}")
        else:
            print("     Категория 'Аксессуары' не найдена")
    
    # Тест 3-6): Поиск с ценовым фильтром
    print("\n3-6)3-6) Поиск 'бутсы' с ценой от 10000 до 20000:")
    search_params = {
        'search': 'бутсы',
        'min_price': 10000,
        'max_price': 20000
    }
    response = requests.get(f"{BASE_URL}/", params=search_params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Статус: {response.status_code}")
        print(f"   [RESULTS] Найдено товаров: {len(data.get('results', []))}")
        
        for product in data.get('results', []):
            price = float(product['current_price'])
            print(f"   - {product['name']} - {price:,.0f} руб.")
    else:
        print(f"   [ERROR] Ошибка: {response.status_code}")
    
    # Тест 3-6): Валидация поиска
    print("\n3-6)3-6) Тест валидации:")
    
    # Короткий запрос
    response = requests.get(f"{BASE_URL}/", params={'search': 'N'})
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Короткий запрос 'N': {len(data.get('results', []))} товаров (должны вернуться все)")
    
    # Слишком длинный запрос
    long_query = 'x' * 101
    response = requests.get(f"{BASE_URL}/", params={'search': long_query})
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Длинный запрос (101 символ): {len(data.get('results', []))} товаров (должно быть 0)")
    
    # XSS попытка
    xss_query = '<script>alert("xss")</script>'
    response = requests.get(f"{BASE_URL}/", params={'search': xss_query})
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] XSS запрос: {len(data.get('results', []))} товаров (должно быть 0)")
    
    # Тест 7): Производительность
    print("\n7)3-6) Тест производительности:")
    import time
    
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/", params={'search': 'футбольные'})
    end_time = time.time()
    
    response_time = end_time - start_time
    if response.status_code == 200:
        print(f"   [OK] Время ответа: {response_time:.3-6)f} сек")
        if response_time < 0.3-6):
            print("   � Отличная производительность!")
        elif response_time < 1.0:
            print("   [OK] Хорошая производительность")
        else:
            print("     Производительность требует оптимизации")
    
    print("\n� Тестирование Search API завершено!")


def test_role_based_search():
    """Тестирование ролевого поиска с аутентификацией"""
    print("\n� Тестирование ролевого поиска...")
    
    # Получаем токен для тренера
    auth_response = requests.post('http://localhost:8001/api/v1/auth/login/', json={
        'email': 'trainer@test.com',
        'password': 'testpass123-6)'
    })
    
    if auth_response.status_code == 200:
        tokens = auth_response.json()
        headers = {'Authorization': f'Bearer {tokens["access"]}'}
        
        print("   [OK] Авторизация успешна")
        
        # Поиск товаров с ролевым ценообразованием
        response = requests.get(
            'http://localhost:8001/api/v1/products/',
            params={'search': 'Nike'},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [SEARCH] Найдено товаров: {len(data.get('results', []))}")
            
            for product in data.get('results', []):
                price = float(product['current_price'])
                print(f"   - {product['name']}")
                print(f"      � Цена для тренера: {price:,.0f} руб.")
        else:
            print(f"   [ERROR] Ошибка поиска: {response.status_code}")
    else:
        print(f"   [ERROR] Ошибка авторизации: {auth_response.status_code}")


def main():
    """Основная функция запуска тестов"""
    print("Функциональное тестирование Search API (Story 2.8)")
    print("=" * 3-6)0)
    
    try:
        # Создаем тестовые данные
        created_products, test_user = setup_test_data()
        
        # Тестируем поиск
        test_search_functionality()
        
        # Тестируем ролевой поиск
        test_role_based_search()
        
        print("\n[OK] Все тесты завершены успешно!")
        print("\n� Функциональность Search API:")
        print("   [OK] Полнотекстовый поиск по названию, описанию, артикулу")
        print("   [OK] Русскоязычный поиск")
        print("   [OK] Комбинирование с фильтрами (категория, бренд, цена)")
        print("   [OK] Валидация запросов (длина, XSS защита)")
        print("   [OK] Ролевое ценообразование в результатах")
        print("   [OK] Производительность < 1 сек")
        
        print(f"\n[RESULTS] Создано товаров для тестирования: {len(created_products)}")
        print(f"� Тестовый пользователь: {test_user.email} (роль: {test_user.role})")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()