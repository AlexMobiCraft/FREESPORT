"""
Сервис импорта статусов заказов из 1С в формате CommerceML 3.1.

Реализует Service Layer паттерн с разделением Parser/Processor:
- _parse_orders_xml() — чистый парсинг XML, возврат dataclass
- _process_order_update() — бизнес-логика обновления Order
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import defusedxml.ElementTree as ET
from datetime import datetime
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

if TYPE_CHECKING:
    from apps.orders.models import Order

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class OrderUpdateData:
    """Данные для обновления заказа, извлечённые из XML."""

    order_id: str  # Значение <Ид>, формат: 'order-{id}'
    order_number: str  # Значение <Номер>
    status_1c: str  # Оригинальный статус из 1С (СтатусЗаказа)
    paid_at: datetime | None = None  # Дата оплаты (ДатаОплаты)
    shipped_at: datetime | None = None  # Дата отгрузки (ДатаОтгрузки)


@dataclass
class ImportResult:
    """Результат импорта статусов заказов."""

    processed: int = 0  # Всего обработано документов
    updated: int = 0  # Успешно обновлено заказов
    skipped: int = 0  # Пропущено (неизвестный статус, уже актуальный)
    not_found: int = 0  # Заказ не найден в БД
    errors: list[str] = field(default_factory=list)  # Ошибки парсинга/обработки


# =============================================================================
# Status Mapping
# =============================================================================

# Маппинг статусов 1С → FREESPORT (AC3)
STATUS_MAPPING: dict[str, str] = {
    "ОжидаетОбработки": "processing",
    "Подтвержден": "confirmed",
    "Отгружен": "shipped",
    "Доставлен": "delivered",
    "Отменен": "cancelled",
    "Возвращен": "refunded",
}


# =============================================================================
# Service
# =============================================================================


class OrderStatusImportService:
    """
    Сервис импорта статусов заказов из XML 1С (CommerceML 3.1).

    Реализует Service Layer паттерн — вся бизнес-логика обновления статусов
    инкапсулирована в этом классе.

    Usage:
        service = OrderStatusImportService()
        result = service.process(xml_data)
        print(f"Updated: {result.updated}, Skipped: {result.skipped}")
    """

    def process(self, xml_data: str | bytes) -> ImportResult:
        """
        Основная точка входа: парсить XML и обновить статусы заказов.

        Args:
            xml_data: XML-строка или bytes в формате CommerceML 3.1.

        Returns:
            ImportResult с подробной статистикой обработки.
        """
        result = ImportResult()

        # PARSE: извлечь данные из XML
        try:
            order_updates = self._parse_orders_xml(xml_data)
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            result.errors.append(f"XML parse error: {e}")
            return result

        result.processed = len(order_updates)

        # BULK FETCH: загрузить все заказы одним запросом (оптимизация N+1)
        orders_cache = self._bulk_fetch_orders(order_updates)

        # PROCESS: обновить каждый заказ
        for order_data in order_updates:
            status = self._process_order_update(order_data, orders_cache)
            if status == "updated":
                result.updated += 1
            elif status == "skipped":
                result.skipped += 1
            elif status == "not_found":
                result.not_found += 1
            # errors добавляются внутри _process_order_update

        return result

    # =========================================================================
    # Parser Methods
    # =========================================================================

    def _parse_orders_xml(self, xml_data: str | bytes) -> list[OrderUpdateData]:
        """
        Парсинг XML orders.xml в формате CommerceML 3.1.

        XML структура (ожидаемая):
            <КоммерческаяИнформация>
                <Контейнер>
                    <Документ>
                        <Ид>order-123</Ид>
                        <Номер>FS-20260202-001</Номер>
                        <ЗначенияРеквизитов>
                            <ЗначениеРеквизита>
                                <Наименование>СтатусЗаказа</Наименование>
                                <Значение>Отгружен</Значение>
                            </ЗначениеРеквизита>
                            ...
                        </ЗначенияРеквизитов>
                    </Документ>
                </Контейнер>
            </КоммерческаяИнформация>

        Args:
            xml_data: XML-строка или bytes.

        Returns:
            Список OrderUpdateData для каждого документа.

        Raises:
            ET.ParseError: при невалидном XML.
        """
        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8")

        root = ET.fromstring(xml_data)
        order_updates: list[OrderUpdateData] = []

        # Найти все <Документ> внутри <Контейнер>
        for container in root.findall(".//Контейнер"):
            for document in container.findall("Документ"):
                order_data = self._parse_document(document)
                if order_data:
                    order_updates.append(order_data)

        return order_updates

    def _parse_document(self, document: ET.Element) -> OrderUpdateData | None:
        """
        Парсинг одного элемента <Документ>.

        Args:
            document: XML элемент <Документ>.

        Returns:
            OrderUpdateData или None если нет нужных данных.
        """
        order_id_elem = document.find("Ид")
        order_number_elem = document.find("Номер")

        order_id = order_id_elem.text if order_id_elem is not None else ""
        order_number = order_number_elem.text if order_number_elem is not None else ""

        if not order_id and not order_number:
            logger.warning("Document without <Ид> and <Номер>, skipping")
            return None

        # Извлечь статус из реквизитов
        status_1c = self._extract_requisite_value(document, "СтатусЗаказа")
        if not status_1c:
            logger.warning(
                f"Document {order_id or order_number}: no СтатусЗаказа requisite"
            )
            return None

        # Извлечь даты из реквизитов (AC5)
        paid_at = self._parse_requisite_date(document, "ДатаОплаты")
        shipped_at = self._parse_requisite_date(document, "ДатаОтгрузки")

        return OrderUpdateData(
            order_id=order_id or "",
            order_number=order_number or "",
            status_1c=status_1c,
            paid_at=paid_at,
            shipped_at=shipped_at,
        )

    def _extract_requisite_value(
        self, document: ET.Element, requisite_name: str
    ) -> str | None:
        """
        Извлечь значение реквизита по имени.

        Args:
            document: XML элемент <Документ>.
            requisite_name: Наименование реквизита (например, 'СтатусЗаказа').

        Returns:
            Значение реквизита или None.
        """
        requisites = document.find("ЗначенияРеквизитов")
        if requisites is None:
            return None

        for req in requisites.findall("ЗначениеРеквизита"):
            name_elem = req.find("Наименование")
            value_elem = req.find("Значение")
            if name_elem is not None and name_elem.text == requisite_name:
                return value_elem.text if value_elem is not None else None

        return None

    def _parse_requisite_date(
        self, document: ET.Element, requisite_name: str
    ) -> datetime | None:
        """
        Извлечь и распарсить дату/время из реквизита.

        Поддерживаемые форматы:
        - YYYY-MM-DDTHH:MM:SS (ISO datetime)
        - YYYY-MM-DD (только дата, время = 00:00:00)

        Args:
            document: XML элемент <Документ>.
            requisite_name: Наименование реквизита ('ДатаОплаты', 'ДатаОтгрузки').

        Returns:
            datetime с timezone или None.
        """
        date_str = self._extract_requisite_value(document, requisite_name)
        if not date_str:
            return None

        # 1. Попытка парсинга как datetime (YYYY-MM-DDTHH:MM:SS)
        parsed_datetime = parse_datetime(date_str)
        if parsed_datetime:
            if timezone.is_naive(parsed_datetime):
                return timezone.make_aware(parsed_datetime)
            return parsed_datetime

        # 2. Fallback: парсинг только даты (YYYY-MM-DD)
        parsed_date = parse_date(date_str)
        if parsed_date:
            # Конвертируем date в datetime с началом дня
            return timezone.make_aware(
                datetime.combine(parsed_date, datetime.min.time())
            )

        logger.warning(f"Could not parse {requisite_name} date: {date_str}")
        return None

    # =========================================================================
    # Bulk Fetch Methods (N+1 Optimization)
    # =========================================================================

    def _bulk_fetch_orders(
        self, order_updates: list[OrderUpdateData]
    ) -> dict[str, "Order"]:
        """
        Загрузить все заказы одним запросом для оптимизации N+1.

        Создаёт кэш заказов по order_number и pk для быстрого поиска.

        Args:
            order_updates: Список данных для обновления.

        Returns:
            Словарь {ключ: Order}, где ключ — order_number или 'pk:{id}'.
        """
        from django.db.models import Q

        from apps.orders.models import Order

        if not order_updates:
            return {}

        # Собираем все order_numbers и pk из order_id
        order_numbers: list[str] = []
        order_pks: list[int] = []

        for data in order_updates:
            if data.order_number:
                order_numbers.append(data.order_number)
            if data.order_id and data.order_id.startswith("order-"):
                try:
                    pk = int(data.order_id.replace("order-", ""))
                    order_pks.append(pk)
                except ValueError:
                    pass

        # Один запрос с OR условиями
        query = Q()
        if order_numbers:
            query |= Q(order_number__in=order_numbers)
        if order_pks:
            query |= Q(pk__in=order_pks)

        if not query:
            return {}

        orders = Order.objects.filter(query)

        # Строим кэш по order_number и pk
        cache: dict[str, Order] = {}
        for order in orders:
            if order.order_number:
                cache[order.order_number] = order
            cache[f"pk:{order.pk}"] = order

        logger.debug(
            f"Bulk fetched {len(cache)} orders for {len(order_updates)} updates"
        )
        return cache

    # =========================================================================
    # Processor Methods
    # =========================================================================

    def _process_order_update(
        self,
        order_data: OrderUpdateData,
        orders_cache: dict[str, "Order"] | None = None,
    ) -> str:
        """
        Обработка обновления одного заказа.

        Поиск заказа:
        1. По <Номер> (order_number) — приоритет
        2. По <Ид> в формате 'order-{id}' — fallback

        Args:
            order_data: Данные для обновления.
            orders_cache: Кэш заказов из bulk fetch (опционально).

        Returns:
            Статус: 'updated', 'skipped', 'not_found'
        """
        order = self._find_order(order_data, orders_cache)
        if order is None:
            logger.error(
                f"Order not found: number='{order_data.order_number}', "
                f"id='{order_data.order_id}'"
            )
            return "not_found"

        # Проверить маппинг статуса (AC6)
        new_status = STATUS_MAPPING.get(order_data.status_1c)
        if new_status is None:
            logger.warning(
                f"Order {order.order_number}: unknown 1C status "
                f"'{order_data.status_1c}', skipping update"
            )
            return "skipped"

        # Проверяем, нужно ли обновление (идемпотентность AC8)
        status_changed = order.status != new_status or order.status_1c != order_data.status_1c
        dates_changed = (
            (order_data.paid_at and order.paid_at != order_data.paid_at)
            or (order_data.shipped_at and order.shipped_at != order_data.shipped_at)
        )

        if not status_changed and not dates_changed:
            logger.debug(
                f"Order {order.order_number}: already up-to-date, skipping"
            )
            return "skipped"

        # Обновление заказа
        update_fields = ["updated_at"]

        if status_changed:
            order.status = new_status
            order.status_1c = order_data.status_1c  # AC4
            update_fields.extend(["status", "status_1c"])

        # Обновление дат (AC5) — всегда обновляем если есть новые значения
        if order_data.paid_at and order.paid_at != order_data.paid_at:
            order.paid_at = order_data.paid_at
            update_fields.append("paid_at")
        if order_data.shipped_at and order.shipped_at != order_data.shipped_at:
            order.shipped_at = order_data.shipped_at
            update_fields.append("shipped_at")

        order.save(update_fields=update_fields)

        logger.info(
            f"Order {order.order_number}: status updated to "
            f"'{new_status}' (1C: '{order_data.status_1c}')"
        )
        return "updated"

    def _find_order(
        self,
        order_data: OrderUpdateData,
        orders_cache: dict[str, "Order"] | None = None,
    ) -> "Order | None":
        """
        Поиск заказа по номеру или ID (AC2).

        Стратегия:
        1. Поиск в кэше (если доступен) — быстрый путь
        2. Fallback на БД запрос (для backward compatibility)

        Args:
            order_data: Данные с order_number и order_id.
            orders_cache: Кэш заказов из bulk fetch (опционально).

        Returns:
            Order или None.
        """
        # Быстрый путь через кэш
        if orders_cache:
            # 1. Поиск по order_number в кэше
            if order_data.order_number and order_data.order_number in orders_cache:
                return orders_cache[order_data.order_number]

            # 2. Поиск по pk в кэше
            if order_data.order_id and order_data.order_id.startswith("order-"):
                try:
                    pk = int(order_data.order_id.replace("order-", ""))
                    cache_key = f"pk:{pk}"
                    if cache_key in orders_cache:
                        return orders_cache[cache_key]
                except ValueError:
                    logger.warning(f"Invalid order_id format: '{order_data.order_id}'")

            return None

        # Fallback на БД (backward compatibility, когда кэш не передан)
        from apps.orders.models import Order

        # 1. Поиск по order_number
        if order_data.order_number:
            order = Order.objects.filter(
                order_number=order_data.order_number
            ).first()
            if order:
                return order

        # 2. Поиск по order_id формата 'order-{id}'
        if order_data.order_id and order_data.order_id.startswith("order-"):
            try:
                order_pk = int(order_data.order_id.replace("order-", ""))
                order = Order.objects.filter(pk=order_pk).first()
                if order:
                    return order
            except ValueError:
                logger.warning(
                    f"Invalid order_id format: '{order_data.order_id}'"
                )

        return None
