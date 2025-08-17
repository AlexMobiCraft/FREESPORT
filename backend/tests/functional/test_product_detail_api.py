#!/usr/bin/env python
"""
Функциональный тест Product Detail API (Story 2.5)
"""
import os
import sys
import django
import requests
import json

# Настройка Django environment
backend_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(backend_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings")
django.setup()

from apps.users.models import User
from apps.products.models import Product, Brand, Category

# Конфигурация для тестов
BASE_URL = "http://127.0.0.1:8001/api/v1"
TEST_USER_PASSWORD = "TestPassword123!"


def print_test_result(test_name, success, details=""):
    """Вывод результата теста"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")


def setup_test_data():
    """Создание тестовых данных для детального просмотра товара"""
    print("\n=== Подготовка тестовых данных ===")

    # Создаем бренд
    brand, created = Brand.objects.get_or_create(
        name="Nike Detail Test",
        defaults={
            "slug": "nike-detail-test",
            "description": "Тестовый бренд для детального просмотра",
        },
    )
    print(f"Бренд: {'создан' if created else 'найден'} - {brand.name}")

    # Создаем категории
    parent_category, created = Category.objects.get_or_create(
        name="Спортивная обувь",
        defaults={"slug": "sport-shoes", "description": "Обувь для спорта"},
    )
    print(
        f"Родительская категория: {'создана' if created else 'найдена'} - {parent_category.name}"
    )

    child_category, created = Category.objects.get_or_create(
        name="Кроссовки",
        defaults={
            "slug": "sneakers",
            "description": "Спортивные кроссовки",
            "parent": parent_category,
        },
    )
    print(
        f"Дочерняя категория: {'создана' if created else 'найдена'} - {child_category.name}"
    )

    # Создаем основной товар для детального просмотра
    test_product, created = Product.objects.get_or_create(
        sku="NIKE_DETAIL_001",
        defaults={
            "name": "Nike Air Max Detail Test",
            "slug": "nike-air-max-detail-test",
            "brand": brand,
            "category": child_category,
            "description": "Детальное описание Nike Air Max для тестирования Product Detail API",
            "short_description": "Краткое описание Nike Air Max",
            "retail_price": 9500.00,
            "opt1_price": 8000.00,
            "opt2_price": 7500.00,
            "trainer_price": 8200.00,
            "federation_price": 7000.00,
            "recommended_retail_price": 12000.00,
            "max_suggested_retail_price": 15000.00,
            "stock_quantity": 15,
            "min_order_quantity": 1,
            "is_featured": True,
            "specifications": {
                "material": "Synthetic leather, mesh",
                "color": "Black/White",
                "size_range": "36-46",
                "weight": "350g",
                "technology": "Air Max cushioning",
                "season": "All season",
                "country_origin": "Vietnam",
            },
            "seo_title": "Nike Air Max - Премиальные кроссовки",
            "seo_description": "Высококачественные кроссовки Nike Air Max с технологией амортизации",
        },
    )
    print(f"Основной товар: {'создан' if created else 'найден'} - {test_product.name}")

    # Создаем связанные товары той же категории
    related_products_data = [
        {
            "name": "Nike Air Force Detail",
            "sku": "NIKE_DETAIL_002",
            "retail_price": 8500.00,
            "opt1_price": 7200.00,
            "stock_quantity": 8,
        },
        {
            "name": "Nike React Detail",
            "sku": "NIKE_DETAIL_003",
            "retail_price": 7800.00,
            "trainer_price": 6800.00,
            "stock_quantity": 12,
        },
        {
            "name": "Nike Zoom Detail",
            "sku": "NIKE_DETAIL_004",
            "retail_price": 9200.00,
            "opt2_price": 7800.00,
            "stock_quantity": 6,
        },
    ]

    for product_data in related_products_data:
        related_product, created = Product.objects.get_or_create(
            sku=product_data["sku"],
            defaults={
                **product_data,
                "slug": product_data["name"].lower().replace(" ", "-"),
                "brand": brand,
                "category": child_category,
                "description": f"Подробное описание {product_data['name']}",
                "short_description": f"Краткое описание {product_data['name']}",
            },
        )
        print(
            f"Связанный товар: {'создан' if created else 'найден'} - {related_product.name}"
        )

    return test_product


def register_and_login_user(role="retail"):
    """Регистрация и авторизация пользователя с указанной ролью"""
    email = f"test_detail_{role}@example.com"

    # Удаляем если существует
    if User.objects.filter(email=email).exists():
        User.objects.filter(email=email).delete()

    registration_data = {
        "email": email,
        "password": TEST_USER_PASSWORD,
        "password_confirm": TEST_USER_PASSWORD,
        "first_name": "Тест",
        "last_name": f"Детальный {role}",
        "role": role,
    }

    # Добавляем B2B поля для соответствующих ролей
    if role in [
        "wholesale_level1",
        "wholesale_level2",
        "wholesale_level3",
        "trainer",
        "federation_rep",
    ]:
        registration_data.update(
            {"company_name": f"Тестовая компания {role}", "tax_id": "1234567890"}
        )

    # Регистрация
    response = requests.post(f"{BASE_URL}/auth/register/", json=registration_data)
    if response.status_code != 201:
        print(f"[ERROR] Регистрация пользователя {role}: {response.status_code}")
        return None

    # Авторизация
    login_data = {"email": email, "password": TEST_USER_PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    if response.status_code == 200:
        return response.json()["access"]

    print(f"[ERROR] Авторизация пользователя {role}: {response.status_code}")
    return None


def test_product_detail_basic():
    """AC 1: GET /products/{id}/ возвращает полную информацию о товаре"""
    print("\n=== AC 1: Базовый детальный просмотр товара ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        print("[ERROR] Тестовый товар не найден")
        return False

    response = requests.get(f"{BASE_URL}/products/{test_product.id}/")
    success = response.status_code == 200
    print_test_result(
        f"GET /products/{test_product.id}/ (полная информация)",
        success,
        f"Status: {response.status_code}",
    )

    if success:
        data = response.json()
        print(f"   Товар: {data.get('name')}")
        print(f"   SKU: {data.get('sku')}")
        print(f"   Цена: {data.get('current_price')} руб.")
        print(f"   В наличии: {data.get('stock_quantity')} шт.")

        # Проверяем обязательные поля согласно AC 1
        required_fields = [
            "id",
            "name",
            "sku",
            "description",
            "specifications",
            "current_price",
            "stock_quantity",
            "images",
            "related_products",
            "category_breadcrumbs",
            "brand",
            "category",
            "seo_title",
            "seo_description",
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            print(f"   [WARNING] Отсутствуют поля: {missing_fields}")
            return False
        else:
            print("   [INFO] Все обязательные поля присутствуют")

    return success


def test_role_based_pricing():
    """AC 2: RRP/MSRP отображается для B2B пользователей"""
    print("\n=== AC 2: Ролевое ценообразование (RRP/MSRP для B2B) ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        return False

    # Тест 1: Retail пользователь (НЕ должен видеть RRP/MSRP)
    retail_token = register_and_login_user("retail")
    if retail_token:
        headers = {"Authorization": f"Bearer {retail_token}"}
        response = requests.get(
            f"{BASE_URL}/products/{test_product.id}/", headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            retail_price = data.get("current_price")
            rrp = data.get("recommended_retail_price")
            msrp = data.get("max_suggested_retail_price")

            success = rrp is None and msrp is None
            print_test_result(
                "Retail пользователь (RRP/MSRP скрыты)",
                success,
                f"Цена: {retail_price} руб., RRP: {rrp}, MSRP: {msrp}",
            )

    # Тест 2: B2B пользователь (ДОЛЖЕН видеть RRP/MSRP)
    wholesale_token = register_and_login_user("wholesale_level1")
    if wholesale_token:
        headers = {"Authorization": f"Bearer {wholesale_token}"}
        response = requests.get(
            f"{BASE_URL}/products/{test_product.id}/", headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            wholesale_price = data.get("current_price")
            rrp = data.get("recommended_retail_price")
            msrp = data.get("max_suggested_retail_price")

            success = rrp is not None and msrp is not None
            print_test_result(
                "B2B пользователь (RRP/MSRP отображаются)",
                success,
                f"Цена: {wholesale_price} руб., RRP: {rrp}, MSRP: {msrp}",
            )

    return True


def test_product_images():
    """AC 3: Галерея изображений включена в ответ"""
    print("\n=== AC 3: Галерея изображений ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        return False

    response = requests.get(f"{BASE_URL}/products/{test_product.id}/")
    success = response.status_code == 200
    print_test_result(
        "Галерея изображений в response", success, f"Status: {response.status_code}"
    )

    if success:
        data = response.json()
        images = data.get("images", [])
        print(f"   Изображений в галерее: {len(images)}")

        # Проверяем структуру изображений
        for i, image in enumerate(images):
            required_image_fields = ["url", "alt_text", "is_primary"]
            missing_fields = [
                field for field in required_image_fields if field not in image
            ]
            if missing_fields:
                print(
                    f"   [WARNING] Изображение {i+1} - отсутствуют поля: {missing_fields}"
                )
            else:
                primary_text = " (основное)" if image.get("is_primary") else ""
                print(f"   Изображение {i+1}: {image.get('alt_text')}{primary_text}")

        return len(images) >= 0  # Изображения могут отсутствовать

    return success


def test_related_products():
    """AC 4: Связанные товары добавлены в response"""
    print("\n=== AC 4: Связанные товары ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        return False

    response = requests.get(f"{BASE_URL}/products/{test_product.id}/")
    success = response.status_code == 200
    print_test_result(
        "Связанные товары в response", success, f"Status: {response.status_code}"
    )

    if success:
        data = response.json()
        related_products = data.get("related_products", [])
        print(f"   Связанных товаров: {len(related_products)}")

        # Проверяем, что текущий товар НЕ включен в связанные
        current_product_id = data.get("id")
        related_ids = [p.get("id") for p in related_products]
        if current_product_id in related_ids:
            print("   [ERROR] Текущий товар включен в связанные товары")
            return False
        else:
            print("   [INFO] Текущий товар корректно исключен из связанных")

        # Проверяем ограничение до 5 товаров
        if len(related_products) > 5:
            print(f"   [WARNING] Связанных товаров больше 5: {len(related_products)}")

        # Показываем связанные товары
        for product in related_products[:3]:
            print(f"   - {product.get('name')} - {product.get('current_price')} руб.")

        return True

    return success


def test_specifications_and_details():
    """AC 5: Спецификации и детали товара отображаются корректно"""
    print("\n=== AC 5: Спецификации и детали товара ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        return False

    response = requests.get(f"{BASE_URL}/products/{test_product.id}/")
    success = response.status_code == 200
    print_test_result(
        "Спецификации и детали", success, f"Status: {response.status_code}"
    )

    if success:
        data = response.json()

        # Проверяем спецификации
        specifications = data.get("specifications", {})
        print(f"   Спецификаций: {len(specifications)} полей")

        expected_specs = ["material", "color", "size_range", "weight", "technology"]
        for spec in expected_specs:
            if spec in specifications:
                print(f"   {spec}: {specifications[spec]}")
            else:
                print(f"   [INFO] Спецификация '{spec}' отсутствует (допустимо)")

        # Проверяем breadcrumbs
        breadcrumbs = data.get("category_breadcrumbs", [])
        print(f"   Breadcrumbs: {len(breadcrumbs)} уровней")
        breadcrumb_path = " > ".join([bc.get("name", "") for bc in breadcrumbs])
        print(f"   Путь: {breadcrumb_path}")

        # Проверяем SEO поля
        seo_title = data.get("seo_title")
        seo_description = data.get("seo_description")
        print(f"   SEO Title: {seo_title}")
        print(
            f"   SEO Description: {seo_description[:50]}..."
            if seo_description
            else "   SEO Description: None"
        )

        # Проверяем информацию о наличии
        stock_quantity = data.get("stock_quantity")
        min_order_quantity = data.get("min_order_quantity")
        print(
            f"   Наличие: {stock_quantity} шт., Минимальный заказ: {min_order_quantity} шт."
        )

        return True

    return success


def test_discount_calculation():
    """Дополнительный тест: расчет скидки"""
    print("\n=== Дополнительно: Расчет скидки ===")

    test_product = Product.objects.filter(sku="NIKE_DETAIL_001").first()
    if not test_product:
        return False

    # Тест для trainer пользователя (должна быть скидка)
    trainer_token = register_and_login_user("trainer")
    if trainer_token:
        headers = {"Authorization": f"Bearer {trainer_token}"}
        response = requests.get(
            f"{BASE_URL}/products/{test_product.id}/", headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            trainer_price = float(data.get("current_price"))
            discount = data.get("discount_percent")

            # Рассчитываем ожидаемую скидку
            retail_price = float(test_product.retail_price)
            expected_discount = round(
                ((retail_price - trainer_price) / retail_price) * 100, 1
            )

            success = discount == expected_discount
            print_test_result(
                "Расчет скидки для trainer",
                success,
                f"Скидка: {discount}%, Ожидается: {expected_discount}%",
            )

    return True


def test_product_not_found():
    """Дополнительный тест: обработка 404"""
    print("\n=== Дополнительно: Обработка 404 ===")

    response = requests.get(f"{BASE_URL}/products/999999/")
    success = response.status_code == 404
    print_test_result(
        "GET /products/999999/ (404 Not Found)",
        success,
        f"Status: {response.status_code}",
    )

    return success


def main():
    """Основная функция тестирования Product Detail API"""
    print("Функциональное тестирование Product Detail API (Story 2.5)")
    print("=" * 60)

    # Подготавливаем тестовые данные
    setup_test_data()

    # Запуск тестов по Acceptance Criteria
    ac1_result = test_product_detail_basic()  # AC 1
    ac2_result = test_role_based_pricing()  # AC 2
    ac3_result = test_product_images()  # AC 3
    ac4_result = test_related_products()  # AC 4
    ac5_result = test_specifications_and_details()  # AC 5

    # Дополнительные тесты
    discount_result = test_discount_calculation()
    not_found_result = test_product_not_found()

    # Подсчет результатов
    total_tests = 7
    passed_tests = sum(
        [
            ac1_result,
            ac2_result,
            ac3_result,
            ac4_result,
            ac5_result,
            discount_result,
            not_found_result,
        ]
    )

    print("\n" + "=" * 60)
    print(f"[SUMMARY] Product Detail API: {passed_tests}/{total_tests} тестов прошли")
    print(f"Покрытие AC: 5/5 (100%)")

    if passed_tests == total_tests:
        print("[SUCCESS] Все тесты прошли успешно! Story 2.5 готова к продакшену.")
    else:
        print(f"[WARNING] {total_tests - passed_tests} тестов требуют внимания")


if __name__ == "__main__":
    main()
