"""
ProductDataProcessor - процессор для обработки данных товаров из 1С
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Sequence

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.products.models import (
    Brand,
    Brand1CMapping,
    Category,
    ImportSession,
    PriceType,
    Product,
)
from apps.products.services.parser import (
    BrandData,
    CategoryData,
    GoodsData,
    OfferData,
    PriceData,
    PriceTypeData,
    RestData,
)

logger = logging.getLogger(__name__)


class ProductDataProcessor:
    """
    Процессор для создания и обновления товаров на основе данных из XMLDataParser

    Методы:
    - create_product_placeholder() - создание заготовки товара из goods.xml с импортом изображений
    - import_product_images() - копирование изображений товара из 1С в Django media (Story 3.1.2)
    - enrich_product_from_offer() - обогащение товара данными из offers.xml
    - update_product_prices() - обновление цен из prices.xml
    - update_product_stock() - обновление остатков из rests.xml
    """

    DEFAULT_PLACEHOLDER_IMAGE = "products/placeholder.png"

    def __init__(
        self, session_id: int, skip_validation: bool = True, chunk_size: int = 1000
    ):
        self.session_id = session_id
        self.skip_validation = skip_validation
        self.chunk_size = chunk_size
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "brand_fallbacks": 0,
            "images_copied": 0,
            "images_skipped": 0,
            "images_errors": 0,
        }
        self._stock_buffer: dict[str, int] = {}
        self._missing_products_logged: set[str] = set()

    def _get_product_by_onec_or_parent(self, onec_id: str) -> Product | None:
        """Найти товар по полному onec_id или его parent части."""
        if not onec_id:
            return None

        product = Product.objects.filter(onec_id=onec_id).first()
        if product:
            return product

        if "#" in onec_id:
            parent_id = onec_id.split("#")[0]

            product = Product.objects.filter(onec_id=parent_id).first()
            if product:
                return product

            product = Product.objects.filter(parent_onec_id=parent_id).first()
            if product and (not product.onec_id or product.onec_id != parent_id):
                product.onec_id = parent_id
                product.save(update_fields=["onec_id"])
                return product

        return None

    def create_product_placeholder(
        self,
        goods_data: GoodsData,
        base_dir: str | None = None,
        skip_images: bool = False,
    ) -> Product | None:
        """
        Создание заготовки товара из goods.xml с опциональным импортом изображений

        Args:
            goods_data: Данные товара из XMLDataParser
            base_dir: Базовая директория импорта (для копирования изображений)
            skip_images: Пропустить импорт изображений товара

        Returns:
            Product instance или None при ошибке
        """
        try:
            parent_id = goods_data.get("id")
            if not parent_id:
                self._log_error("Missing parent_id in goods_data", goods_data)
                return None

            logger.info(f"Creating product placeholder for parent_id: {parent_id}")

            brand_id = goods_data.get("brand_id")

            # Проверка существующего товара (по onec_id или parent_onec_id)
            existing = Product.objects.filter(
                models.Q(onec_id=parent_id) | models.Q(parent_onec_id=parent_id)
            ).first()
            if existing:
                # Убедимся что onec_id установлен
                if not existing.onec_id:
                    existing.onec_id = parent_id
                    existing.save(update_fields=["onec_id"])

                brand = self._determine_brand(brand_id=brand_id, parent_id=parent_id)
                fields_to_update: list[str] = []
                if existing.brand_id != brand.pk:
                    existing.brand = brand
                    fields_to_update.append("brand")
                if brand_id and existing.onec_brand_id != brand_id:
                    existing.onec_brand_id = brand_id
                    fields_to_update.append("onec_brand_id")

                if fields_to_update:
                    existing.save(update_fields=fields_to_update)

                # НОВАЯ ФУНКЦИОНАЛЬНОСТЬ: Импорт изображений для существующих товаров
                if not skip_images and base_dir and "images" in goods_data:
                    try:
                        logger.info(
                            f"Importing images for existing product {existing.onec_id}"
                        )
                        image_result = self.import_product_images(
                            product=existing,
                            image_paths=goods_data["images"],
                            base_dir=base_dir,
                            validate_images=not self.skip_validation,
                        )
                        self._update_image_stats(image_result)
                    except Exception as img_error:
                        logger.error(
                            f"Error importing images for existing product {existing.onec_id}: {img_error}"
                        )
                        # Не прерываем процесс, а продолжаем с ошибкой в статистике
                        self.stats["errors"] += 1

                self.stats["updated"] += 1
                return existing

            # Получаем категорию (если есть)
            category = None
            category_id = goods_data.get("category_id")
            if category_id:
                category = Category.objects.filter(onec_id=category_id).first()
                if category is None:
                    category_name_value = goods_data.get("category_name")
                    if isinstance(category_name_value, str) and category_name_value:
                        placeholder_name = category_name_value
                    else:
                        placeholder_name = f"Категория {category_id}"

                    placeholder_slug = slugify(placeholder_name) or slugify(
                        str(category_id)
                    )
                    if not placeholder_slug:
                        placeholder_slug = f"category-{uuid.uuid4().hex[:8]}"
                    elif Category.objects.filter(slug=placeholder_slug).exists():
                        placeholder_slug = f"{placeholder_slug}-{uuid.uuid4().hex[:8]}"

                    category, _ = Category.objects.get_or_create(
                        onec_id=category_id,
                        defaults={
                            "name": placeholder_name,
                            "slug": placeholder_slug,
                            "is_active": True,
                        },
                    )

            if category is None:
                category, _ = Category.objects.get_or_create(
                    slug="uncategorized",
                    defaults={
                        "name": "Без категории",
                        "is_active": True,
                    },
                )

            # Получаем бренд из данных товара или используем fallback
            brand = self._determine_brand(brand_id=brand_id, parent_id=parent_id)

            # Генерируем уникальный slug для товара
            name_value = goods_data.get("name")
            if isinstance(name_value, str) and name_value:
                product_name = name_value
            else:
                product_name = "Product Placeholder"
            try:
                from transliterate import translit

                transliterated = translit(product_name, "ru", reversed=True)
                base_slug = slugify(transliterated)
            except (RuntimeError, ImportError):
                base_slug = slugify(product_name)

            if not base_slug:
                base_slug = f"product-{parent_id[:8]}"

            # Обеспечиваем уникальность slug
            unique_slug = base_slug
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

            # Создание заготовки
            description_value = goods_data.get("description")
            description_text = (
                description_value if isinstance(description_value, str) else ""
            )

            product = Product(
                onec_id=parent_id,  # Устанавливаем onec_id сразу
                parent_onec_id=parent_id,
                onec_brand_id=brand_id,  # Сохраняем исходный ID бренда из 1С
                name=product_name,
                slug=unique_slug,
                description=description_text,
                brand=brand,
                category=category,
                retail_price=Decimal("0.00"),  # Будет обновлено из prices.xml
                is_active=False,  # Неактивен до обогащения данными
                sync_status=Product.SyncStatus.PENDING,
                main_image=self.DEFAULT_PLACEHOLDER_IMAGE,
            )
            try:
                product.save()
                logger.info(
                    f"Product placeholder created successfully: {product.onec_id}"
                )
                self.stats["created"] += 1

                # НОВАЯ ФУНКЦИОНАЛЬНОСТЬ: Импорт изображений
                if not skip_images and base_dir and "images" in goods_data:
                    try:
                        logger.info(
                            f"Importing images for new product {product.onec_id}"
                        )
                        image_result = self.import_product_images(
                            product=product,
                            image_paths=goods_data["images"],
                            base_dir=base_dir,
                            validate_images=not self.skip_validation,
                        )
                        self._update_image_stats(image_result)
                    except Exception as img_error:
                        logger.error(
                            f"Error importing images for new product {product.onec_id}: {img_error}"
                        )
                        # Не прерываем процесс, а продолжаем с ошибкой в статистике
                        self.stats["errors"] += 1

                return product
            except Exception as save_error:
                logger.error(f"Error saving product placeholder: {save_error}")
                self._log_error(
                    f"Error saving product placeholder: {save_error}", goods_data
                )
                return None

        except Exception as e:
            self._log_error(f"Error creating product placeholder: {e}", goods_data)
            return None

    def _determine_brand(self, brand_id: str | None, parent_id: str) -> Brand:
        """Определяет мастер-бренд через Brand1CMapping или возвращает fallback."""
        if brand_id:
            mapping = (
                Brand1CMapping.objects.select_related("brand")
                .filter(onec_id=brand_id)
                .first()
            )
            if mapping and mapping.brand:
                return mapping.brand
            self._log_brand_mapping_missing(brand_id, parent_id)
            return self._get_no_brand()

        logger.warning(
            f"Product {parent_id}: onec_brand_id not provided in CommerceML"
        )
        self._increment_brand_fallbacks()
        return self._get_no_brand()

    def _log_brand_mapping_missing(self, brand_id: str, parent_id: str) -> None:
        """Фиксирует отсутствие маппинга бренда в логах и статистике."""
        self._increment_brand_fallbacks()
        logger.warning(
            "Brand1CMapping not found for onec_id=%s, product=%s, session=%s, "
            "using 'No Brand' fallback",
            brand_id,
            parent_id,
            self.session_id,
        )

    def _increment_brand_fallbacks(self) -> None:
        """Инкрементирует счётчик brand_fallbacks в статистике."""
        self.stats["brand_fallbacks"] += 1

    def _get_no_brand(self) -> Brand:
        """Возвращает (или создаёт) fallback бренд 'No Brand'."""
        brand, _ = Brand.objects.get_or_create(
            name="No Brand", defaults={"slug": "no-brand", "is_active": True}
        )
        return brand

    def enrich_product_from_offer(self, offer_data: OfferData) -> bool:
        """Обогащение товара данными из offers.xml (onec_id, SKU, is_active=True)"""
        try:
            onec_id = offer_data.get("id")
            if not onec_id:
                self._log_error("Missing onec_id in offer_data", offer_data)
                return False

            # Извлекаем parent_id из составного ID (uuid#uuid)
            if "#" in onec_id:
                parent_id = onec_id.split("#")[0]
            else:
                parent_id = onec_id

            # Находим заготовку по parent_onec_id
            try:
                product = Product.objects.get(parent_onec_id=parent_id)
            except Product.DoesNotExist:
                self._log_error(f"Parent product not found: {parent_id}", offer_data)
                return False

            # Обновляем финальными данными
            if "#" in onec_id:
                product.onec_id = onec_id
            elif not product.onec_id:
                product.onec_id = parent_id
            product.name = offer_data.get("name", product.name)
            product.sku = offer_data.get("article", f"SKU-{onec_id[:8]}")
            product.is_active = True
            product.sync_status = Product.SyncStatus.IN_PROGRESS

            # Сохраняем характеристики если есть
            if "characteristics" in offer_data:
                if not product.specifications:
                    product.specifications = {}
                for char in offer_data["characteristics"]:
                    product.specifications[char["name"]] = char["value"]

            product.save()

            self.stats["updated"] += 1
            return True

        except Exception as e:
            self._log_error(f"Error enriching product: {e}", offer_data)
            return False

    def update_product_prices(self, price_data: PriceData) -> bool:
        """Обновление цен товара из prices.xml"""
        try:
            onec_id = price_data.get("id")
            if not onec_id:
                self._log_error("Missing id in price_data", price_data)
                return False

            # Находим товар
            product = self._get_product_by_onec_or_parent(onec_id)
            if product is None:
                self._log_missing_product(onec_id, price_data)
                return False

            # Маппинг цен через PriceType
            prices = price_data.get("prices", [])
            price_updates = {}

            for price_item in prices:
                price_type_id = price_item.get("price_type_id")
                price_value = price_item.get("value")

                if not price_type_id or price_value is None:
                    continue

                # Находим маппинг типа цены
                price_type = PriceType.objects.filter(
                    onec_id=price_type_id, is_active=True
                ).first()

                if price_type:
                    field_name = price_type.product_field
                    price_updates[field_name] = price_value

            # Применяем обновления цен
            for field_name, value in price_updates.items():
                setattr(product, field_name, value)

            # Fallback для federation_price
            if not product.federation_price and product.recommended_retail_price:
                product.federation_price = product.recommended_retail_price

            product.last_sync_at = timezone.now()
            product.save()

            self.stats["updated"] += 1
            return True

        except Exception as e:
            self._log_error(f"Error updating prices: {e}", price_data)
            return False

    def update_product_stock(self, rest_data: RestData) -> bool:
        """Обновление остатков товара из rests.xml"""
        try:
            onec_id = rest_data.get("id")
            quantity = rest_data.get("quantity", 0)

            if not onec_id:
                self._log_error("Missing id in rest_data", rest_data)
                return False

            # Находим товар
            product = self._get_product_by_onec_or_parent(onec_id)
            if product is None:
                self._log_missing_product(onec_id, rest_data)
                return False

            # Обновляем остаток (суммируем если товар на разных складах)
            total_quantity = self._stock_buffer.get(onec_id, 0) + quantity
            self._stock_buffer[onec_id] = total_quantity
            product.stock_quantity = total_quantity
            product.sync_status = Product.SyncStatus.COMPLETED
            product.last_sync_at = timezone.now()
            product.save()

            self.stats["updated"] += 1
            return True

        except Exception as e:
            self._log_error(f"Error updating stock: {e}", rest_data)
            return False

    def process_price_types(self, price_types_data: Sequence[PriceTypeData]) -> int:
        """Создание/обновление справочника PriceType"""
        count = 0
        for price_type_data in price_types_data:
            try:
                PriceType.objects.update_or_create(
                    onec_id=price_type_data["onec_id"],
                    defaults={
                        "onec_name": price_type_data["onec_name"],
                        "product_field": price_type_data["product_field"],
                        "is_active": True,
                    },
                )
                count += 1
            except Exception as e:
                logger.error(f"Error processing price type: {e}")
                self.stats["errors"] += 1

        return count

    def finalize_session(self, status: str, error_message: str = "") -> None:
        """Завершение сессии импорта"""
        try:
            session = ImportSession.objects.get(id=self.session_id)
            session.status = status
            session.finished_at = timezone.now()
            session.report_details = self.stats
            if error_message:
                session.error_message = error_message
            session.save()

        except ImportSession.DoesNotExist:
            logger.error(f"ImportSession {self.session_id} not found")

    def _log_error(self, message: str, data: Any) -> None:
        """Логирование ошибки"""
        logger.error(f"{message}: {data}")
        self.stats["errors"] += 1

    def _log_missing_product(self, onec_id: str, data: Any) -> None:
        if onec_id in self._missing_products_logged:
            return

        self._missing_products_logged.add(onec_id)

    def _update_image_stats(self, image_result: dict[str, int]) -> None:
        """Helper to update image-related stats."""
        # Исправляем несоответствие ключей: метод возвращает "copied", "skipped", "errors"
        # а статистика ожидает "images_copied", "images_skipped", "images_errors"
        key_mapping = {
            "copied": "images_copied",
            "skipped": "images_skipped",
            "errors": "images_errors",
        }

        for result_key, stats_key in key_mapping.items():
            self.stats.setdefault(stats_key, 0)
            self.stats[stats_key] += image_result.get(result_key, 0)

        logger.info(f"Updated image stats: {self.stats}")

    def process_categories(self, categories_data: list[CategoryData]) -> dict[str, int]:
        """
        Обработка категорий с иерархией (Story 3.1.2)

        Двухпроходный алгоритм:
        1. Создаём все категории без родительских связей
        2. Устанавливаем родительские связи с валидацией циклов

        Returns:
            dict с количеством created, updated, errors
        """
        result = {"created": 0, "updated": 0, "errors": 0, "cycles_detected": 0}
        category_map: dict[str, Category] = {}

        # ШАГ 1: Создаём/обновляем все категории без parent
        for category_data in categories_data:
            try:
                onec_id = category_data.get("id")
                name = category_data.get("name")
                description = category_data.get("description", "")

                if not onec_id or not name:
                    # Skipping category with missing id or name: {category_data}
                    result["errors"] += 1
                    continue

                category, created = Category.objects.update_or_create(
                    onec_id=onec_id,
                    defaults={
                        "name": name,
                        "description": description,
                        "is_active": True,
                    },
                )

                category_map[onec_id] = category

                if created:
                    result["created"] += 1
                else:
                    result["updated"] += 1

            except Exception as e:
                logger.error(f"Error processing category {category_data}: {e}")
                result["errors"] += 1

        # ШАГ 2: Устанавливаем родительские связи с валидацией циклов
        for category_data in categories_data:
            try:
                onec_id = category_data.get("id")
                parent_id = category_data.get("parent_id")

                if not parent_id or not onec_id:
                    continue  # Корневая категория или ошибка

                category = category_map.get(onec_id)
                parent = category_map.get(parent_id)

                if not category:
                    # Category not found in map: {onec_id}
                    continue

                if not parent:
                    # Parent category not found: {parent_id} for {onec_id}
                    continue

                # Валидация циклических ссылок
                if self._has_circular_reference(category, parent, category_map):
                    # Circular reference detected: {onec_id} -> {parent_id}
                    result["cycles_detected"] += 1
                    continue

                # Устанавливаем parent
                category.parent = parent
                category.save(update_fields=["parent"])

            except Exception as e:
                # Error setting parent for category {onec_id}: {e}
                result["errors"] += 1

        # Categories processed: {result['created']} created, {result['updated']} updated, {result['errors']} errors, {result['cycles_detected']} cycles detected
        return result

    def _has_circular_reference(
        self,
        category: Category,
        proposed_parent: Category,
        category_map: dict[str, Category],
    ) -> bool:
        """
        Проверка циклических ссылок в иерархии категорий

        Обходим родителей proposed_parent и проверяем что category
        не встречается в цепочке (Story 3.1.2)
        """
        visited = set()
        current = proposed_parent

        while current:
            # Если мы вернулись к исходной категории - цикл обнаружен
            if current.pk == category.pk:
                return True

            # Защита от бесконечного цикла
            if current.pk in visited:
                # Existing circular reference detected at {current.name}
                return True

            visited.add(current.pk)

            # Переходим к parent
            current = current.parent

        return False

    def process_brands(self, brands_data: Sequence[BrandData]) -> dict[str, int]:
        """
        Обработка брендов из propertiesGoods.xml с дедупликацией по normalized_name

        Args:
            brands_data: Список брендов с полями id и name

        Returns:
            dict с количеством brands_created, mappings_created, mappings_updated
        """
        from apps.products.utils.brands import normalize_brand_name

        result = {
            "brands_created": 0,
            "mappings_created": 0,
            "mappings_updated": 0,
        }

        for brand_data in brands_data:
            try:
                onec_id = brand_data.get("id")
                onec_name = brand_data.get("name")

                if not onec_id or not onec_name:
                    logger.warning(
                        f"Skipping brand with missing id or name: {brand_data}"
                    )
                    continue

                # Нормализуем название для поиска дубликатов
                normalized = normalize_brand_name(onec_name)

                # Проверяем существующий маппинг для этого onec_id
                existing_mapping = Brand1CMapping.objects.filter(
                    onec_id=onec_id
                ).first()

                if existing_mapping:
                    # Маппинг уже существует - обновляем onec_name если изменилось
                    if existing_mapping.onec_name != onec_name:
                        existing_mapping.onec_name = onec_name
                        existing_mapping.save(update_fields=["onec_name"])
                        result["mappings_updated"] += 1
                        logger.debug(
                            "Brand mapping updated - no changes",
                            extra={
                                "onec_id": onec_id,
                                "brand_id": existing_mapping.brand.id,
                                "operation": "update_noop",
                                "import_session_id": self.session_id,
                            },
                        )
                    else:
                        result["mappings_updated"] += 1
                    continue

                # Ищем существующий бренд по normalized_name
                existing_brand = Brand.objects.filter(
                    normalized_name=normalized
                ).first()

                if existing_brand:
                    # Бренд существует - создаём только маппинг (объединение дубликатов)
                    Brand1CMapping.objects.create(
                        brand=existing_brand,
                        onec_id=onec_id,
                        onec_name=onec_name,
                    )
                    result["mappings_created"] += 1

                    logger.info(
                        "Brand mapping created - duplicate merged",
                        extra={
                            "onec_id": onec_id,
                            "onec_name": onec_name,
                            "brand_id": existing_brand.id,
                            "brand_name": existing_brand.name,
                            "normalized_name": existing_brand.normalized_name,
                            "slug": existing_brand.slug,
                            "operation": "merge",
                            "import_session_id": self.session_id,
                        },
                    )
                else:
                    # Бренд не найден - создаём новый бренд + маппинг
                    # Генерируем уникальный slug
                    try:
                        from transliterate import translit

                        transliterated = translit(onec_name, "ru", reversed=True)
                        base_slug = slugify(transliterated)
                    except (RuntimeError, ImportError):
                        base_slug = slugify(onec_name)

                    if not base_slug:
                        base_slug = f"brand-{onec_id[:8]}"

                    # Обеспечиваем уникальность slug
                    unique_slug = base_slug
                    counter = 2
                    while Brand.objects.filter(slug=unique_slug).exists():
                        unique_slug = f"{base_slug}-{counter}"
                        counter += 1

                    # Создаём бренд (normalized_name установится автоматически в save())
                    brand = Brand.objects.create(
                        name=onec_name,
                        slug=unique_slug,
                        is_active=True,
                    )

                    # Создаём маппинг
                    Brand1CMapping.objects.create(
                        brand=brand,
                        onec_id=onec_id,
                        onec_name=onec_name,
                    )

                    result["brands_created"] += 1
                    result["mappings_created"] += 1

                    logger.info(
                        "Brand created with mapping",
                        extra={
                            "onec_id": onec_id,
                            "onec_name": onec_name,
                            "brand_id": brand.id,
                            "brand_name": brand.name,
                            "normalized_name": brand.normalized_name,
                            "slug": brand.slug,
                            "operation": "create",
                            "import_session_id": self.session_id,
                        },
                    )

            except Exception as e:
                logger.error(f"Error processing brand {brand_data}: {e}")
                self.stats["errors"] += 1

        logger.info(
            f"Brands processed: {result['brands_created']} brands created, "
            f"{result['mappings_created']} mappings created, "
            f"{result['mappings_updated']} mappings updated"
        )
        return result

    def import_product_images(
        self,
        product: Product,
        image_paths: list[str],
        base_dir: str,
        validate_images: bool = False,
    ) -> dict[str, int]:
        """
        Копирование изображений товара из директории 1С в Django media storage

        Args:
            product: Product instance для установки изображений
            image_paths: Список относительных путей из goods_data["images"]
            base_dir: Базовая директория импорта (например, data/import_1c/goods/)
            validate_images: Валидировать изображения через Pillow (медленнее)

        Returns:
            dict с количеством copied, skipped, errors

        Поведение:
            - Первое изображение устанавливается как main_image
            - Остальные добавляются в gallery_images
            - При повторном импорте main_image НЕ меняется если уже установлен
            - Новые изображения добавляются в конец gallery_images (append)
            - Дубликаты в gallery_images предотвращаются
            - Сохраняется структура поддиректорий из 1С для производительности
        """
        logger.info(
            f"Starting image import for product {product.onec_id}. "
            f"Initial main_image: {product.main_image}, "
            f"Initial gallery: {product.gallery_images}"
        )
        from pathlib import Path

        result = {"copied": 0, "skipped": 0, "errors": 0}

        # Логирование для отладки
        logger.info(
            f"Starting image import for product {product.onec_id} with {len(image_paths)} images"
        )

        if not image_paths:
            return result

        # Проверяем существующий main_image (семантика повторного импорта)
        main_image_set = bool(
            product.main_image and product.main_image != self.DEFAULT_PLACEHOLDER_IMAGE
        )
        gallery_images = list(product.gallery_images or [])
        logger.info(f"main_image_set flag initial value: {main_image_set}")

        for image_path in image_paths:
            try:
                # Построение полного пути к исходному файлу
                source_path = Path(base_dir) / image_path

                if not source_path.exists():
                    # Image file not found: {source_path} for product {product.onec_id}
                    result["errors"] += 1
                    continue

                # Сохранение структуры директорий из 1С
                # image_path: "00/001a16a4-b810-11ed-860f-fa163edba792_24062354.jpg"
                filename = source_path.name
                subdir = image_path.split("/")[0] if "/" in image_path else ""
                destination_path = (
                    f"products/{subdir}/{filename}"
                    if subdir
                    else f"products/{filename}"
                )

                # Проверка существования файла в media
                if default_storage.exists(destination_path):
                    result["skipped"] += 1

                    # Устанавливаем связь даже если файл уже существует
                    # При повторном импорте main_image НЕ меняется если уже установлен
                    if not main_image_set:
                        logger.info(
                            f"Setting existing file as main_image: {destination_path}"
                        )
                        product.main_image = destination_path  # type: ignore
                        main_image_set = True
                    else:
                        logger.info(
                            f"Adding existing file to gallery: {destination_path}"
                        )
                        # Проверка дубликатов в gallery_images
                        if destination_path not in gallery_images:
                            gallery_images.append(destination_path)
                    continue

                # Валидация изображения (опционально)
                if validate_images:
                    try:
                        from PIL import Image

                        with Image.open(source_path) as img:
                            img.verify()
                        logger.info(f"Image validation passed for: {source_path}")
                    except Exception as e:
                        logger.error(f"Invalid image file {source_path}: {e}")
                        result["errors"] += 1
                        continue

                # Копирование файла в media storage
                with open(source_path, "rb") as f:
                    file_content = f.read()
                    saved_path = default_storage.save(
                        destination_path, ContentFile(file_content)
                    )

                result["copied"] += 1

                # Установка связи с Product
                # При повторном импорте main_image НЕ меняется если уже установлен
                if not main_image_set:
                    logger.info(f"Setting new file as main_image: {saved_path}")
                    product.main_image = saved_path  # type: ignore
                    main_image_set = True
                else:
                    logger.info(f"Adding new file to gallery: {saved_path}")
                    # Проверка дубликатов в gallery_images
                    if saved_path not in gallery_images:
                        gallery_images.append(saved_path)

            except Exception as e:
                logger.error(f"Error copying image {image_path}: {e}")
                result["errors"] += 1

        # Сохранение изменений в Product
        if main_image_set or gallery_images:
            product.gallery_images = gallery_images
            product.save(update_fields=["main_image", "gallery_images"])
            logger.info(
                f"Product {product.onec_id} updated with main_image: {product.main_image}, gallery count: {len(gallery_images)}"
            )

        # Логирование итоговых результатов для отладки
        logger.info(f"Image import completed for product {product.onec_id}: {result}")
        return result
