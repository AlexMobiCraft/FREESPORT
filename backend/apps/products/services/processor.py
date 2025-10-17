"""
ProductDataProcessor - процессор для обработки данных товаров из 1С
"""
import logging
import uuid
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.products.models import Brand, Category, ImportSession, PriceType, Product

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

    def create_product_placeholder(self, goods_data: dict[str, Any]) -> Product | None:
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
                    placeholder_name = goods_data.get("category_name") or f"Категория {category_id}"
                    placeholder_slug = slugify(placeholder_name) or slugify(str(category_id))
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

            # Создание заготовки
            product = Product(
                parent_onec_id=parent_id,
                name=goods_data.get("name", "Product Placeholder"),
                description=goods_data.get("description", ""),
                brand=brand,
                category=category,
                retail_price=Decimal("0.00"),  # Будет обновлено из prices.xml
                is_active=False,  # Неактивен до обогащения данными
                sync_status=Product.SyncStatus.PENDING,
            )
            product.save()

            logger.info(f"Created product placeholder: {parent_id}")
            self.stats["created"] += 1
            return product

        except Exception as e:
            self._log_error(f"Error creating product placeholder: {e}", goods_data)
            return None

    def enrich_product_from_offer(self, offer_data: dict[str, Any]) -> bool:
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
            product.onec_id = onec_id
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

    def update_product_prices(self, price_data: dict[str, Any]) -> bool:
        """Обновление цен товара из prices.xml"""
        try:
            onec_id = price_data.get("id")
            if not onec_id:
                self._log_error("Missing id in price_data", price_data)
                return False

            # Находим товар
            try:
                product = Product.objects.get(onec_id=onec_id)
            except Product.DoesNotExist:
                self._log_error(f"Product not found: {onec_id}", price_data)
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

    def update_product_stock(self, rest_data: dict[str, Any]) -> bool:
        """Обновление остатков товара из rests.xml"""
        try:
            onec_id = rest_data.get("id")
            quantity = rest_data.get("quantity", 0)

            if not onec_id:
                self._log_error("Missing id in rest_data", rest_data)
                return False

            # Находим товар
            try:
                product = Product.objects.get(onec_id=onec_id)
            except Product.DoesNotExist:
                self._log_error(f"Product not found: {onec_id}", rest_data)
                return False

            # Обновляем остаток (суммируем если товар на разных складах)
            product.stock_quantity = quantity
            product.sync_status = Product.SyncStatus.COMPLETED
            product.last_sync_at = timezone.now()
            product.save()

            logger.info(f"Updated stock for product: {onec_id}")
            self.stats["updated"] += 1
            return True

        except Exception as e:
            self._log_error(f"Error updating stock: {e}", rest_data)
            return False

    def process_price_types(self, price_types_data: list[dict[str, Any]]) -> int:
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

            logger.info(f"Import session {self.session_id} finalized with status: {status}")
        except ImportSession.DoesNotExist:
            logger.error(f"ImportSession {self.session_id} not found")

    def _log_error(self, message: str, data: dict[str, Any]) -> None:
        """Логирование ошибки"""
        logger.error(f"{message}: {data}")
        self.stats["errors"] += 1
