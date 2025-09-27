"""
Django management команда для загрузки тестового каталога товаров

Пример использования:
    python manage.py load_test_catalog --count=100
    python manage.py load_test_catalog --count=50 --with-categories --with-brands
    python manage.py load_test_catalog --clear-existing
"""

import random
from decimal import Decimal
from typing import Dict, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from apps.products.models import Brand, Category, Product


class Command(BaseCommand):
    """
    Команда загрузки тестового каталога товаров для разработки и тестирования
    """

    help = "Загрузка тестового каталога товаров с реалистичными данными"

    def add_arguments(self, parser):
        """Добавление аргументов команды"""
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Количество товаров для создания (по умолчанию: 50)",
        )

        parser.add_argument(
            "--with-categories", action="store_true", help="Создать категории товаров"
        )

        parser.add_argument(
            "--with-brands", action="store_true", help="Создать бренды товаров"
        )

        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Очистить существующие тестовые данные перед загрузкой",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без сохранения данных",
        )

    def handle(self, *args, **options):
        """Основная логика команды"""

        self.count = options["count"]
        self.with_categories = options["with_categories"]
        self.with_brands = options["with_brands"]
        self.clear_existing = options["clear_existing"]
        self.dry_run = options["dry_run"]

        # Заголовок
        self.stdout.write(
            self.style.SUCCESS("🚀 Запуск загрузки тестового каталога товаров")  # type: ignore
        )

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  РЕЖИМ DRY-RUN: изменения НЕ будут сохранены")  # type: ignore
            )

        try:
            with transaction.atomic():
                if self.dry_run:
                    savepoint = transaction.savepoint()

                # Очистка существующих данных
                if self.clear_existing:
                    self._clear_existing_data()

                # Создание справочников
                brands = self._create_brands() if self.with_brands else []
                categories = self._create_categories() if self.with_categories else []

                # Создание товаров
                created_count = self._create_products(brands, categories)

                if self.dry_run:
                    transaction.savepoint_rollback(savepoint)
                    self.stdout.write(
                        self.style.SUCCESS(  # type: ignore
                            f"✅ DRY-RUN завершен: {created_count} товаров обработано"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(  # type: ignore
                            f"✅ Тестовый каталог загружен: {created_count} "
                            f"товаров создано"
                        )
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка загрузки каталога: {str(e)}"))  # type: ignore
            raise

    def _clear_existing_data(self):
        """Очистка существующих тестовых данных"""
        self.stdout.write("🧹 Очистка существующих тестовых данных...")

        # Удаляем товары с тестовыми onec_id
        deleted_products = Product.objects.filter(  # type: ignore
            onec_id__startswith="TEST-PRODUCT-"
        ).delete()[0]

        # Удаляем тестовые бренды
        deleted_brands = Brand.objects.filter(  # type: ignore
            name__startswith="Тестовый бренд"
        ).delete()[0]

        # Удаляем тестовые категории
        deleted_categories = Category.objects.filter(  # type: ignore
            name__startswith="Тестовая категория"
        ).delete()[0]

        self.stdout.write(
            f"📊 Удалено: {deleted_products} товаров, "
            f"{deleted_brands} брендов, {deleted_categories} категорий"
        )

    def _create_brands(self) -> List[Brand]:
        """Создание тестовых брендов"""
        self.stdout.write("🏷️  Создание тестовых брендов...")

        brand_names = [
            "Nike Test",
            "Adidas Test",
            "Puma Test",
            "Reebok Test",
            "Under Armour Test",
            "New Balance Test",
            "ASICS Test",
            "Wilson Test",
            "Head Test",
            "Babolat Test",
        ]

        brands = []
        for name in brand_names:
            brand, created = Brand.objects.get_or_create(  # type: ignore
                name=name, defaults={"is_active": True}
            )
            brands.append(brand)
            if created:
                self.stdout.write(f"  ✅ Создан бренд: {name}")

        return brands

    def _create_categories(self) -> List[Category]:
        """Создание тестовых категорий"""
        self.stdout.write("📂 Создание тестовых категорий...")

        category_names = [
            "Обувь тестовая",
            "Одежда тестовая",
            "Аксессуары тестовая",
            "Инвентарь тестовая",
            "Мячи тестовая",
            "Ракетки тестовая",
            "Защита тестовая",
            "Тренажеры тестовая",
        ]

        categories = []
        for name in category_names:
            category, created = Category.objects.get_or_create(  # type: ignore
                name=name, defaults={"is_active": True}
            )
            categories.append(category)
            if created:
                self.stdout.write(f"  ✅ Создана категория: {name}")

        return categories

    def _create_products(self, brands: List[Brand], categories: List[Category]) -> int:
        """Создание тестовых товаров"""
        self.stdout.write(f"📦 Создание {self.count} тестовых товаров...")

        # Получаем существующие бренды и категории если не создавали новые
        if not brands:
            brands = list(Brand.objects.filter(is_active=True)[:10])  # type: ignore
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если нет брендов, создаем дефолтный
            if not brands:
                default_brand, _ = Brand.objects.get_or_create(  # type: ignore
                    name="Тестовый бренд",
                    defaults={
                        "slug": "testovyj-brend",
                        "description": "Автоматически созданный бренд для тестов",
                        "is_active": True,
                    },
                )
                brands = [default_brand]

        if not categories:
            categories = list(Category.objects.filter(is_active=True)[:10])  # type: ignore
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если нет категорий, создаем дефолтную
            if not categories:
                default_category, _ = Category.objects.get_or_create(  # type: ignore
                    name="Тестовая категория",
                    defaults={
                        "slug": "testovaya-kategoriya",
                        "description": "Автоматически созданная категория для тестов",
                        "is_active": True,
                    },
                )
                categories = [default_category]

        created_count = 0

        # Progress bar
        progress_bar = tqdm(
            range(self.count),
            desc="Создание товаров",
            unit="товаров",
            ncols=100,
            leave=True,
        )

        for i in progress_bar:
            try:
                product_data = self._generate_product_data(i + 1, brands, categories)

                product, created = Product.objects.get_or_create(  # type: ignore
                    onec_id=product_data["onec_id"], defaults=product_data
                )

                if created:
                    created_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Ошибка создания товара #{i + 1}: {str(e)}")  # type: ignore
                )
                continue

        progress_bar.close()
        return created_count

    def _generate_product_data(
        self, index: int, brands: List[Brand], categories: List[Category]
    ) -> Dict:
        """Генерация данных для одного товара"""

        # Базовые данные
        base_price = Decimal(random.randint(500, 5000))

        # Случайные материалы и характеристики
        materials = [
            "Cotton",
            "Polyester",
            "Nylon",
            "Leather",
            "Synthetic",
            "Mesh",
            "Canvas",
        ]
        colors = [
            "Black",
            "White",
            "Blue",
            "Red",
            "Green",
            "Yellow",
            "Gray",
            "Navy",
            "Pink",
        ]
        sizes = ["XS", "S", "M", "L", "XL", "XXL"]

        product_types = [
            "Кроссовки",
            "Футболка",
            "Шорты",
            "Куртка",
            "Мяч",
            "Ракетка",
            "Перчатки",
            "Очки",
            "Сумка",
            "Бутылка",
        ]

        product_type = random.choice(product_types)

        return {
            "onec_id": f"TEST-PRODUCT-{index:05d}",
            "name": f"{product_type} тестовый #{index}",
            "brand": random.choice(brands) if brands else None,
            "category": random.choice(categories) if categories else None,
            "description": f"Описание тестового товара {product_type} #{index} "
            f"для демонстрации и тестирования системы каталога",
            "short_description": f"Краткое описание {product_type} #{index}",
            "sku": f"TEST-SKU-{index:05d}",
            "stock_quantity": random.randint(0, 200),
            "reserved_quantity": random.randint(0, 10),
            "min_order_quantity": random.choice(
                [1, 1, 1, 5, 10]
            ),  # 60% - штучные товары
            "specifications": {
                "material": random.choice(materials),
                "color": random.choice(colors),
                "size": random.choice(sizes),
                "weight": f"{random.randint(100, 2000)}g",
                "country": random.choice(["Китай", "Вьетнам", "Индонезия", "Турция"]),
                "gender": random.choice(["Мужской", "Женский", "Унисекс"]),
            },
            # Цены для всех ролей
            "retail_price": base_price,
            "opt1_price": base_price * Decimal("0.90"),  # 10% скидка
            "opt2_price": base_price * Decimal("0.85"),  # 15% скидка
            "opt3_price": base_price * Decimal("0.80"),  # 20% скидка
            "trainer_price": base_price * Decimal("0.75"),  # 25% скидка
            "federation_price": base_price * Decimal("0.70"),  # 30% скидка
            "recommended_retail_price": base_price * Decimal("1.20"),  # +20% RRP
            "max_suggested_retail_price": base_price * Decimal("1.50"),  # +50% MSRP
            "is_active": random.choice([True, True, True, True, False]),  # 80% активных
            "sync_status": random.choice(
                ["synced", "synced", "pending"]
            ),  # 70% синхронизированных
            "last_sync_at": timezone.now(),
            "error_message": "",
        }
