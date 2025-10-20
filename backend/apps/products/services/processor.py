"""
ProductDataProcessor - процессор для обработки данных товаров из 1С
"""
import logging
import uuid
from decimal import Decimal
from typing import Any, Sequence

from django.utils import timezone
from django.utils.text import slugify

from apps.products.models import Brand, Category, ImportSession, PriceType, Product
from apps.products.services.parser import (
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
    - create_product_placeholder() - создание заготовки товара из goods.xml
    - enrich_product_from_offer() - обогащение товара данными из offers.xml
    - update_product_prices() - обновление цен из prices.xml
    - update_product_stock() - обновление остатков из rests.xml
    """

    DEFAULT_PLACEHOLDER_IMAGE = "products/placeholder.png"

    def __init__(
        self, session_id: int, skip_validation: bool = False, chunk_size: int = 1000
    ):
        self.session_id = session_id
        self.skip_validation = skip_validation
        self.chunk_size = chunk_size
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
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

    def create_product_placeholder(self, goods_data: GoodsData) -> Product | None:
        """Создание заготовки товара из goods.xml (parent_onec_id, is_active=False)"""
        try:
            parent_id = goods_data.get("id")
            if not parent_id:
                self._log_error("Missing parent_id in goods_data", goods_data)
                return None

            # Проверка существующего товара
            existing = Product.objects.filter(parent_onec_id=parent_id).first()
            if existing:
                logger.info(f"Product placeholder already exists: {parent_id}")
                self.stats["skipped"] += 1
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

            # Получаем или создаем бренд по умолчанию
            brand, _ = Brand.objects.get_or_create(
                name="No Brand", defaults={"slug": "no-brand", "is_active": True}
            )

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
                parent_onec_id=parent_id,
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
            product.save()

            logger.info(f"Created product placeholder: {parent_id}")
            self.stats["created"] += 1
            return product

        except Exception as e:
            self._log_error(f"Error creating product placeholder: {e}", goods_data)
            return None

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

            logger.info(f"Enriched product from offer: {onec_id}")
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

            logger.info(f"Updated prices for product: {onec_id}")
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

            logger.info(f"Updated stock for product: {onec_id}")
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

        logger.info(f"Processed {count} price types")
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

            logger.info(
                f"Import session {self.session_id} finalized with status: {status}"
            )
        except ImportSession.DoesNotExist:
            logger.error(f"ImportSession {self.session_id} not found")

    def _log_error(self, message: str, data: Any) -> None:
        """Логирование ошибки"""
        logger.error(f"{message}: {data}")
        self.stats["errors"] += 1

    def _log_missing_product(self, onec_id: str, data: Any) -> None:
        if onec_id in self._missing_products_logged:
            logger.debug(f"Product not found (already logged): {onec_id}")
            return

        self._missing_products_logged.add(onec_id)

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
                    logger.warning(
                        f"Skipping category with missing id or name: {category_data}"
                    )
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
                    logger.info(f"Created category: {name} ({onec_id})")
                else:
                    result["updated"] += 1
                    logger.info(f"Updated category: {name} ({onec_id})")

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
                    logger.warning(f"Category not found in map: {onec_id}")
                    continue

                if not parent:
                    logger.warning(
                        f"Parent category not found: {parent_id} for {onec_id}"
                    )
                    continue

                # Валидация циклических ссылок
                if self._has_circular_reference(category, parent, category_map):
                    logger.error(
                        f"Circular reference detected: {onec_id} -> {parent_id}"
                    )
                    result["cycles_detected"] += 1
                    continue

                # Устанавливаем parent
                category.parent = parent
                category.save(update_fields=["parent"])
                logger.debug(f"Set parent {parent.name} for {category.name}")

            except Exception as e:
                logger.error(f"Error setting parent for category {onec_id}: {e}")
                result["errors"] += 1

        logger.info(
            f"Categories processed: {result['created']} created, "
            f"{result['updated']} updated, {result['errors']} errors, "
            f"{result['cycles_detected']} cycles detected"
        )
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
            if current.id == category.id:
                return True

            # Защита от бесконечного цикла
            if current.id in visited:
                logger.warning(
                    f"Existing circular reference detected at {current.name}"
                )
                return True

            visited.add(current.id)

            # Переходим к parent
            current = current.parent

        return False
