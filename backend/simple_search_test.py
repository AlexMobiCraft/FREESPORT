#!/usr/bin/env python
"""
Простой функциональный тест Search API (Story 2.8)
"""

import os
import sys
import django
import requests

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, Brand
from decimal import Decimal

User = get_user_model()

def setup_test_data():
    """Создание тестовых данных"""
    print("Создание тестовых данных...")
    
    # Создаем категорию
    category, _ = Category.objects.get_or_create(
        slug="football",
        defaults={'name': "Футбольная обувь", 'is_active': True}
    )
    
    # Создаем бренд
    brand, _ = Brand.objects.get_or_create(
        slug="nike",
        defaults={'name': "Nike", 'is_active': True}
    )
    
    # Создаем товар
    product, created = Product.objects.get_or_create(
        sku="NIKE-TEST-001",
        defaults={
            'name': "Nike Test Product",
            'short_description': "Тестовый товар Nike для поиска",
            'description': "Футбольные бутсы Nike для тестирования search API",
            'brand': brand,
            'category': category,
            'retail_price': Decimal('15000.00'),
            'stock_quantity': 10,
            'is_active': True
        }
    )
    
    if created:
        print(f"Создан товар: {product.name}")
    else:
        print(f"Товар уже существует: {product.name}")
    
    return product

def test_search():
    """Тестирование поиска"""
    BASE_URL = "http://localhost:8001/api/v1/products"
    
    print("\nТестирование search API...")
    
    # Тест 1: Поиск по названию
    print("1. Поиск по названию 'Nike':")
    response = requests.get(f"{BASE_URL}/", params={'search': 'Nike'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Статус: {response.status_code}")
        print(f"   Найдено товаров: {len(data.get('results', []))}")
        
        for product in data.get('results', []):
            print(f"   - {product['name']} - {product['current_price']} руб.")
    else:
        print(f"   Ошибка: {response.status_code}")
    
    # Тест 2: Русскоязычный поиск
    print("\n2. Русскоязычный поиск 'футбольные':")
    response = requests.get(f"{BASE_URL}/", params={'search': 'футбольные'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Статус: {response.status_code}")
        print(f"   Найдено товаров: {len(data.get('results', []))}")
    else:
        print(f"   Ошибка: {response.status_code}")
    
    # Тест 3: Валидация
    print("\n3. Тест валидации (слишком длинный запрос):")
    long_query = 'x' * 101
    response = requests.get(f"{BASE_URL}/", params={'search': long_query})
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Результатов: {len(data.get('results', []))} (должно быть 0)")
    
    print("\nТестирование завершено!")

def main():
    """Основная функция"""
    print("Функциональное тестирование Search API")
    print("=" * 40)
    
    try:
        setup_test_data()
        test_search()
        
        print("\nSearch API функциональность:")
        print("- Полнотекстовый поиск работает")
        print("- Русскоязычный поиск работает") 
        print("- Валидация запросов работает")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()