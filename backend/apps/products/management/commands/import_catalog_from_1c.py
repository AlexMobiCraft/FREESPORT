"""
Django management команда для импорта каталога товаров из 1С

Пример использования:
    python manage.py import_catalog_from_1c --file=catalog.xml
    python manage.py import_catalog_from_1c --file=catalog.json --dry-run
    python manage.py import_catalog_from_1c --mock-data --chunk-size=100
"""

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from apps.products.models import Brand, Category, Product


class Command(BaseCommand):
    """
    Команда импорта каталога товаров из 1С
    """

    help = "Импорт каталога товаров из 1С (XML/JSON)"

    def add_arguments(self, parser):
        """Добавление аргументов команды"""
        parser.add_argument(
            "--file", type=str, help="Путь к файлу данных 1С (XML или JSON)"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без сохранения данных",
        )

        parser.add_argument(
            "--chunk-size",
            type=int,
            default=50,
            help="Размер батча для обработки товаров (по умолчанию: 50)",
        )

        parser.add_argument(
            "--mock-data",
            action="store_true",
            help="Использовать встроенные тестовые данные вместо файла",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Принудительно перезаписать существующие товары",
        )

    def handle(self, *args, **options):
        """Основная логика команды"""

        self.dry_run = options["dry_run"]
        self.chunk_size = options["chunk_size"]
        self.force = options["force"]
        self.file_path = options["file"]
        self.use_mock_data = options["mock_data"]

        # Валидация параметров
        if not self.file_path and not self.use_mock_data:
            raise CommandError(
                "Укажите либо --file для загрузки из файла, либо --mock-data для тестовых данных"
            )

        # Заголовок
        self.stdout.write(self.style.SUCCESS("🚀 Запуск импорта каталога товаров из 1С"))

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  РЕЖИМ DRY-RUN: изменения НЕ будут сохранены")
            )

        try:
            # Получение данных
            if self.use_mock_data:
                products_data = self._get_mock_products_data()
                self.stdout.write(
                    f"📦 Загружены тестовые данные: {len(products_data)} товаров"
                )
            else:
                products_data = self._load_data_from_file()
                self.stdout.write(f"📁 Загружен файл: {len(products_data)} товаров")

            # Импорт данных
            imported_count = self._import_products(products_data)

            # Финальная статистика
            if self.dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ DRY-RUN завершен: {imported_count} товаров обработано"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Импорт завершен успешно: {imported_count} товаров импортировано"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка импорта: {str(e)}"))
            raise

    def _load_data_from_file(self) -> List[Dict]:
        """Загрузка данных из файла"""

        if not Path(self.file_path).exists():
            raise CommandError(f"Файл не найден: {self.file_path}")

        file_path = Path(self.file_path)

        if file_path.suffix.lower() == ".json":
            return self._parse_json_file(file_path)
        elif file_path.suffix.lower() in [".xml"]:
            return self._parse_xml_file(file_path)
        else:
            raise CommandError(
                f"Неподдерживаемый формат файла: {file_path.suffix}. "
                "Поддерживаются: .json, .xml"
            )

    def _parse_json_file(self, file_path: Path) -> List[Dict]:
        """Парсинг JSON файла"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "products" in data:
                return data["products"]
            elif isinstance(data, list):
                return data
            else:
                raise CommandError("Неверная структура JSON файла")

        except json.JSONDecodeError as e:
            raise CommandError(f"Ошибка парсинга JSON: {str(e)}")

    def _parse_xml_file(self, file_path: Path) -> List[Dict]:
        """Парсинг XML файла (заглушка)"""
        # TODO: Реализовать XML парсер после получения образцов от 1С
        raise CommandError(
            "XML парсер будет реализован после получения образцов файлов от 1С. "
            "Используйте --mock-data для тестирования."
        )

    def _get_mock_products_data(self) -> List[Dict]:
        """Генерация тестовых данных товаров"""

        mock_brands = ["Nike", "Adidas", "Puma", "Reebok", "Under Armour"]
        mock_categories = ["Обувь", "Одежда", "Аксессуары", "Инвентарь"]

        products = []

        for i in range(1, 21):  # 20 тестовых товаров
            product = {
                "onec_id": f"1C-PRODUCT-{i:05d}",
                "name": f"Товар тестовый #{i}",
                "brand": mock_brands[i % len(mock_brands)],
                "category": mock_categories[i % len(mock_categories)],
                "description": f"Описание тестового товара #{i} для демонстрации импорта из 1С",
                "short_description": f"Краткое описание товара #{i}",
                "sku": f"SKU-{i:05d}",
                "stock_quantity": (i * 5) % 100,
                "specifications": {
                    "material": "Synthetic" if i % 2 == 0 else "Cotton",
                    "color": "Blue" if i % 3 == 0 else "Red",
                    "size": ["S", "M", "L", "XL"][i % 4],
                },
                "prices": {
                    "retail_price": str(Decimal("1000.00") + Decimal(i * 100)),
                    "opt1_price": str(Decimal("800.00") + Decimal(i * 80)),
                    "opt2_price": str(Decimal("700.00") + Decimal(i * 70)),
                    "opt3_price": str(Decimal("600.00") + Decimal(i * 60)),
                    "trainer_price": str(Decimal("750.00") + Decimal(i * 75)),
                    "federation_price": str(Decimal("500.00") + Decimal(i * 50)),
                    "recommended_retail_price": str(
                        Decimal("1200.00") + Decimal(i * 120)
                    ),
                    "max_suggested_retail_price": str(
                        Decimal("1500.00") + Decimal(i * 150)
                    ),
                },
                "is_active": i % 10 != 0,  # 90% активных товаров
                "min_order_quantity": 1 if i % 5 != 0 else 5,
            }
            products.append(product)

        return products

    def _import_products(self, products_data: List[Dict]) -> int:
        """Импорт товаров в базу данных"""

        imported_count = 0

        # Progress bar
        progress_bar = tqdm(
            products_data, desc="Импорт товаров", unit="товаров", ncols=100, leave=True
        )

        with transaction.atomic():
            if self.dry_run:
                # Создаем savepoint для rollback в dry-run режиме
                savepoint = transaction.savepoint()

            try:
                # Обработка товаров по батчам
                for i in range(0, len(products_data), self.chunk_size):
                    chunk = products_data[i : i + self.chunk_size]
                    imported_count += self._process_products_chunk(chunk, progress_bar)

                if self.dry_run:
                    # Rollback изменений в dry-run режиме
                    transaction.savepoint_rollback(savepoint)

            except Exception as e:
                if not self.dry_run:
                    raise
                else:
                    transaction.savepoint_rollback(savepoint)
                    raise

        progress_bar.close()
        return imported_count

    def _process_products_chunk(self, chunk: List[Dict], progress_bar) -> int:
        """Обработка батча товаров"""

        processed_count = 0

        for product_data in chunk:
            try:
                # Обработка одного товара
                self._process_single_product(product_data)
                processed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Ошибка обработки товара {product_data.get("onec_id", "UNKNOWN")}: {str(e)}'
                    )
                )
                if not self.force:
                    raise

            # Обновление progress bar
            progress_bar.update(1)

            # Небольшая задержка для демонстрации
            if self.use_mock_data:
                time.sleep(0.01)

        return processed_count

    def _process_single_product(self, product_data: Dict):
        """Обработка одного товара"""

        onec_id = product_data.get("onec_id")
        if not onec_id:
            raise ValueError("Отсутствует onec_id товара")

        # Поиск или создание бренда
        brand_name = product_data.get("brand")
        if brand_name:
            brand, _ = Brand.objects.get_or_create(
                name=brand_name, defaults={"is_active": True}
            )
        else:
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: создаем дефолтный бренд если не указан
            brand, _ = Brand.objects.get_or_create(
                name="Неизвестный бренд",
                defaults={
                    "slug": "neizvestnyj-brend",
                    "description": "Автоматически созданный бренд для товаров без указанного бренда",
                    "is_active": True,
                },
            )

        # Поиск или создание категории
        category_name = product_data.get("category")
        if category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name, defaults={"is_active": True}
            )
        else:
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: создаем дефолтную категорию если не указана
            category, _ = Category.objects.get_or_create(
                name="Разное",
                defaults={
                    "slug": "raznoe",
                    "description": "Автоматически созданная категория для товаров без указанной категории",
                    "is_active": True,
                },
            )

        # Данные товара
        product_defaults = {
            "name": product_data.get("name", "Товар без названия"),
            "brand": brand,
            "category": category,
            "description": product_data.get("description", ""),
            "short_description": product_data.get("short_description", ""),
            "sku": product_data.get("sku", ""),
            "stock_quantity": product_data.get("stock_quantity", 0),
            "min_order_quantity": product_data.get("min_order_quantity", 1),
            "specifications": product_data.get("specifications", {}),
            "is_active": product_data.get("is_active", True),
            "sync_status": "synced",
            "last_sync_at": timezone.now(),
            "error_message": "",
        }

        # Добавление цен
        prices = product_data.get("prices", {})
        for price_field in [
            "retail_price",
            "opt1_price",
            "opt2_price",
            "opt3_price",
            "trainer_price",
            "federation_price",
            "recommended_retail_price",
            "max_suggested_retail_price",
        ]:
            if price_field in prices:
                try:
                    product_defaults[price_field] = Decimal(prices[price_field])
                except (ValueError, TypeError):
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Некорректная цена {price_field} для товара {onec_id}"
                        )
                    )

        # Создание или обновление товара
        if self.force:
            product, created = Product.objects.update_or_create(
                onec_id=onec_id, defaults=product_defaults
            )
            action = "создан" if created else "обновлен"
        else:
            # Проверяем существование товара перед созданием
            if Product.objects.filter(onec_id=onec_id).exists():
                if not self.dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Товар {onec_id} уже существует, пропускаем"
                        )
                    )
                return
            else:
                product = Product.objects.create(onec_id=onec_id, **product_defaults)
                action = "создан"

        # Логирование (только в verbose режиме)
        if getattr(self, "verbosity", 1) >= 2:
            self.stdout.write(f"✅ Товар {onec_id} ({product.name}) {action}")
