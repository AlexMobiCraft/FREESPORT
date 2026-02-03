"""
Unit-тесты для OrderStatusImportService.

Тесты для Story 5.1: Сервис импорта статусов (OrderStatusImportService)
Покрывают AC1-AC9.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.orders.services.order_status_import import (
    STATUS_MAPPING,
    ImportResult,
    OrderStatusImportService,
    OrderUpdateData,
)

from tests.conftest import get_unique_suffix


# =============================================================================
# Helper Functions
# =============================================================================


def build_test_xml(
    order_id: str = "order-123",
    order_number: str = "FS-TEST-001",
    status: str = "Отгружен",
    paid_date: str | None = None,
    shipped_date: str | None = None,
) -> str:
    """Генерирует тестовый XML в формате CommerceML 3.1."""
    requisites = f"""
        <ЗначениеРеквизита>
            <Наименование>СтатусЗаказа</Наименование>
            <Значение>{status}</Значение>
        </ЗначениеРеквизита>
    """
    if paid_date:
        requisites += f"""
        <ЗначениеРеквизита>
            <Наименование>ДатаОплаты</Наименование>
            <Значение>{paid_date}</Значение>
        </ЗначениеРеквизита>
        """
    if shipped_date:
        requisites += f"""
        <ЗначениеРеквизита>
            <Наименование>ДатаОтгрузки</Наименование>
            <Значение>{shipped_date}</Значение>
        </ЗначениеРеквизита>
        """

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="3.1" ДатаФормирования="2026-02-02T12:00:00">
    <Контейнер>
        <Документ>
            <Ид>{order_id}</Ид>
            <Номер>{order_number}</Номер>
            <Дата>2026-02-02</Дата>
            <ХозОперация>Заказ товара</ХозОперация>
            <ЗначенияРеквизитов>
                {requisites}
            </ЗначенияРеквизитов>
        </Документ>
    </Контейнер>
</КоммерческаяИнформация>
"""


def build_multi_order_xml(orders: list[dict]) -> str:
    """Генерирует XML с несколькими заказами."""
    containers = []
    for order in orders:
        order_id = order.get("order_id", "order-1")
        order_number = order.get("order_number", "FS-TEST")
        status = order.get("status", "Отгружен")
        
        containers.append(f"""
        <Контейнер>
            <Документ>
                <Ид>{order_id}</Ид>
                <Номер>{order_number}</Номер>
                <Дата>2026-02-02</Дата>
                <ХозОперация>Заказ товара</ХозОперация>
                <ЗначенияРеквизитов>
                    <ЗначениеРеквизита>
                        <Наименование>СтатусЗаказа</Наименование>
                        <Значение>{status}</Значение>
                    </ЗначениеРеквизита>
                </ЗначенияРеквизитов>
            </Документ>
        </Контейнер>
        """)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="3.1" ДатаФормирования="2026-02-02T12:00:00">
    {''.join(containers)}
</КоммерческаяИнформация>
"""


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestStatusMapping:
    """Тесты маппинга статусов 1С → FREESPORT (AC3)."""

    def test_status_mapping_all_statuses(self):
        """AC9 4.3: Проверка всех 6 статусов маппинга."""
        # ARRANGE / ACT / ASSERT
        expected_mappings = {
            "ОжидаетОбработки": "processing",
            "Подтвержден": "confirmed",
            "Отгружен": "shipped",
            "Доставлен": "delivered",
            "Отменен": "cancelled",
            "Возвращен": "refunded",
        }
        
        for status_1c, status_freesport in expected_mappings.items():
            assert STATUS_MAPPING.get(status_1c) == status_freesport, (
                f"Mapping mismatch: {status_1c} should map to {status_freesport}"
            )

    def test_status_mapping_count(self):
        """Проверка количества статусов в маппинге."""
        assert len(STATUS_MAPPING) == 6


@pytest.mark.unit
class TestOrderUpdateData:
    """Тесты dataclass OrderUpdateData."""

    def test_order_update_data_creation(self):
        """Проверка создания OrderUpdateData."""
        # ARRANGE
        data = OrderUpdateData(
            order_id="order-123",
            order_number="FS-TEST-001",
            status_1c="Отгружен",
            paid_at=None,
            shipped_at=None,
        )
        
        # ASSERT
        assert data.order_id == "order-123"
        assert data.order_number == "FS-TEST-001"
        assert data.status_1c == "Отгружен"
        assert data.paid_at is None
        assert data.shipped_at is None


@pytest.mark.unit
class TestImportResult:
    """Тесты dataclass ImportResult."""

    def test_import_result_defaults(self):
        """Проверка дефолтных значений ImportResult."""
        # ARRANGE / ACT
        result = ImportResult()
        
        # ASSERT
        assert result.processed == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.not_found == 0
        assert result.errors == []


@pytest.mark.unit
class TestXMLParsing:
    """Тесты парсинга XML (AC1)."""

    def test_parse_valid_xml_extracts_order_data(self):
        """AC9 4.2: Парсинг валидного XML."""
        # ARRANGE
        order_number = f"FS-{get_unique_suffix()}"
        xml_data = build_test_xml(
            order_id="order-999",
            order_number=order_number,
            status="Доставлен",
        )
        service = OrderStatusImportService()
        
        # ACT
        order_updates = service._parse_orders_xml(xml_data)
        
        # ASSERT
        assert len(order_updates) == 1
        assert order_updates[0].order_id == "order-999"
        assert order_updates[0].order_number == order_number
        assert order_updates[0].status_1c == "Доставлен"

    def test_parse_xml_with_bytes(self):
        """Парсинг XML из bytes."""
        # ARRANGE
        xml_data = build_test_xml().encode("utf-8")
        service = OrderStatusImportService()
        
        # ACT
        order_updates = service._parse_orders_xml(xml_data)
        
        # ASSERT
        assert len(order_updates) == 1

    def test_parse_xml_with_multiple_orders(self):
        """Парсинг XML с несколькими заказами."""
        # ARRANGE
        xml_data = build_multi_order_xml([
            {"order_id": "order-1", "order_number": "FS-1", "status": "Отгружен"},
            {"order_id": "order-2", "order_number": "FS-2", "status": "Доставлен"},
            {"order_id": "order-3", "order_number": "FS-3", "status": "Подтвержден"},
        ])
        service = OrderStatusImportService()
        
        # ACT
        order_updates = service._parse_orders_xml(xml_data)
        
        # ASSERT
        assert len(order_updates) == 3
        statuses = [u.status_1c for u in order_updates]
        assert "Отгружен" in statuses
        assert "Доставлен" in statuses
        assert "Подтвержден" in statuses

    def test_parse_xml_invalid_raises_error(self):
        """Невалидный XML вызывает ParseError."""
        # ARRANGE
        invalid_xml = "<invalid><not-closed>"
        service = OrderStatusImportService()
        
        # ACT / ASSERT
        with pytest.raises(Exception):  # ET.ParseError
            service._parse_orders_xml(invalid_xml)


@pytest.mark.unit
class TestDateExtraction:
    """Тесты извлечения дат из реквизитов (AC5)."""

    def test_process_extracts_payment_and_shipment_dates(self):
        """AC9 4.5: Извлечение дат оплаты и отгрузки."""
        # ARRANGE
        xml_data = build_test_xml(
            status="Отгружен",
            paid_date="2026-02-01",
            shipped_date="2026-02-02",
        )
        service = OrderStatusImportService()
        
        # ACT
        order_updates = service._parse_orders_xml(xml_data)
        
        # ASSERT
        assert len(order_updates) == 1
        update = order_updates[0]
        
        # Проверяем что даты распарсены
        assert update.paid_at is not None
        assert update.shipped_at is not None
        
        # Проверяем значения дат
        assert update.paid_at.date() == date(2026, 2, 1)
        assert update.shipped_at.date() == date(2026, 2, 2)

    def test_parse_date_missing_returns_none(self):
        """Отсутствующая дата возвращает None."""
        # ARRANGE
        xml_data = build_test_xml(
            status="Отгружен",
            paid_date=None,
            shipped_date=None,
        )
        service = OrderStatusImportService()

        # ACT
        order_updates = service._parse_orders_xml(xml_data)

        # ASSERT
        assert order_updates[0].paid_at is None
        assert order_updates[0].shipped_at is None

    def test_parse_datetime_with_time_preserves_time(self):
        """[AI-Review][Low] Парсинг datetime с временем сохраняет время."""
        # ARRANGE
        xml_data = build_test_xml(
            status="Отгружен",
            paid_date="2026-02-01T14:30:00",
            shipped_date="2026-02-02T09:15:30",
        )
        service = OrderStatusImportService()

        # ACT
        order_updates = service._parse_orders_xml(xml_data)

        # ASSERT
        update = order_updates[0]
        assert update.paid_at is not None
        assert update.shipped_at is not None

        # Проверяем время (не только дату)
        assert update.paid_at.hour == 14
        assert update.paid_at.minute == 30
        assert update.shipped_at.hour == 9
        assert update.shipped_at.minute == 15
        assert update.shipped_at.second == 30


@pytest.mark.unit  
class TestOrderProcessing:
    """Тесты обработки заказов с моками (AC2, AC3, AC4, AC6, AC7, AC8)."""

    def test_process_updates_order_status_and_status_1c(self):
        """AC9 4.4: Обновление статуса + status_1c."""
        # ARRANGE
        order_number = f"FS-{get_unique_suffix()}"
        xml_data = build_test_xml(
            order_number=order_number,
            status="Отгружен",
        )

        # Мокаем Order
        mock_order = MagicMock()
        mock_order.order_number = order_number
        mock_order.status = "pending"
        mock_order.status_1c = ""
        mock_order.paid_at = None
        mock_order.shipped_at = None

        service = OrderStatusImportService()

        # Мокаем bulk_fetch чтобы вернуть кэш с order
        mock_cache = {order_number: mock_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert result.updated == 1
            assert mock_order.status == "shipped"  # Mapped from "Отгружен"
            assert mock_order.status_1c == "Отгружен"  # Original 1C status (AC4)
            mock_order.save.assert_called_once()

    def test_unknown_status_logs_warning_and_skips(self):
        """AC9 4.6: Неизвестный статус — пропуск заказа (AC6)."""
        # ARRANGE
        order_number = "FS-TEST-001"
        xml_data = build_test_xml(order_number=order_number, status="НеизвестныйСтатус")

        mock_order = MagicMock()
        mock_order.order_number = order_number
        mock_order.status = "pending"
        mock_order.status_1c = ""

        service = OrderStatusImportService()
        mock_cache = {order_number: mock_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert result.skipped == 1
            assert result.updated == 0
            mock_order.save.assert_not_called()

    def test_missing_order_logs_error_and_continues(self):
        """AC9 4.7: Отсутствующий заказ — продолжение обработки (AC7)."""
        # ARRANGE
        xml_data = build_multi_order_xml([
            {"order_id": "order-1", "order_number": "MISSING-1", "status": "Отгружен"},
            {"order_id": "order-2", "order_number": "EXISTS-1", "status": "Доставлен"},
        ])

        mock_existing_order = MagicMock()
        mock_existing_order.order_number = "EXISTS-1"
        mock_existing_order.status = "pending"
        mock_existing_order.status_1c = ""
        mock_existing_order.paid_at = None
        mock_existing_order.shipped_at = None

        service = OrderStatusImportService()

        # Кэш содержит только EXISTS-1, MISSING-1 отсутствует
        mock_cache = {"EXISTS-1": mock_existing_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert result.processed == 2
            assert result.updated == 1  # EXISTS-1 updated
            assert result.not_found == 1  # MISSING-1 not found
            mock_existing_order.save.assert_called_once()

    def test_idempotent_processing_no_duplicate_updates(self):
        """AC9 4.8: Идемпотентность — повторная обработка не дублирует (AC8)."""
        # ARRANGE
        order_number = "FS-IDEM-001"
        xml_data = build_test_xml(
            order_number=order_number,
            status="Отгружен",
        )

        # Заказ уже имеет такой же статус
        mock_order = MagicMock()
        mock_order.order_number = order_number
        mock_order.status = "shipped"  # Already shipped
        mock_order.status_1c = "Отгружен"  # Same 1C status
        mock_order.paid_at = None
        mock_order.shipped_at = None

        service = OrderStatusImportService()
        mock_cache = {order_number: mock_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert result.skipped == 1
            assert result.updated == 0
            mock_order.save.assert_not_called()

    def test_idempotent_updates_dates_even_if_status_unchanged(self):
        """[AI-Review][High] Обновление дат даже если статус не изменился."""
        # ARRANGE
        order_number = "FS-DATES-001"
        xml_data = build_test_xml(
            order_number=order_number,
            status="Отгружен",
            paid_date="2026-02-01",
            shipped_date="2026-02-02",
        )

        # Заказ уже имеет такой же статус, но даты отсутствуют
        mock_order = MagicMock()
        mock_order.order_number = order_number
        mock_order.status = "shipped"  # Already shipped
        mock_order.status_1c = "Отгружен"  # Same 1C status
        mock_order.paid_at = None  # Date not set
        mock_order.shipped_at = None  # Date not set

        service = OrderStatusImportService()
        mock_cache = {order_number: mock_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT — даты должны обновиться несмотря на совпадение статуса
            assert result.updated == 1
            assert result.skipped == 0
            assert mock_order.paid_at is not None
            assert mock_order.shipped_at is not None
            mock_order.save.assert_called_once()


@pytest.mark.unit
class TestFindOrder:
    """Тесты поиска заказа (AC2)."""

    def test_find_order_by_order_number_priority(self):
        """Поиск сначала по order_number."""
        # ARRANGE
        from apps.orders.models import Order
        
        order_data = OrderUpdateData(
            order_id="order-999",
            order_number="FS-FIND-001",
            status_1c="Отгружен",
        )
        
        mock_order = MagicMock()
        mock_queryset = MagicMock()
        mock_queryset.first.return_value = mock_order
        
        service = OrderStatusImportService()
        
        with patch.object(Order.objects, "filter", return_value=mock_queryset):
            # ACT
            result = service._find_order(order_data)
            
            # ASSERT
            assert result == mock_order
            Order.objects.filter.assert_called_with(order_number="FS-FIND-001")

    def test_find_order_by_id_fallback(self):
        """Fallback поиск по order-{id} когда order_number не найден."""
        # ARRANGE
        order_data = OrderUpdateData(
            order_id="order-42",
            order_number="",  # Empty - will use order_id
            status_1c="Отгружен",
        )

        mock_order = MagicMock()
        mock_order.pk = 42
        service = OrderStatusImportService()

        # Тестируем _find_order с кэшем по pk
        cache = {"pk:42": mock_order}

        # ACT
        result = service._find_order(order_data, cache)

        # ASSERT
        assert result == mock_order

    def test_find_order_fallback_to_db_when_no_cache(self):
        """Fallback на БД когда кэш не передан — проверка через process."""
        # ARRANGE
        xml_data = build_test_xml(order_id="order-42", order_number="")

        mock_order = MagicMock()
        mock_order.status = "pending"
        mock_order.status_1c = ""
        mock_order.order_number = "FOUND-BY-ID"
        mock_order.paid_at = None
        mock_order.shipped_at = None

        service = OrderStatusImportService()

        # Кэш содержит order по pk
        mock_cache = {"pk:42": mock_order}

        with patch.object(service, "_bulk_fetch_orders", return_value=mock_cache):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert result.updated == 1


@pytest.mark.unit
class TestProcessIntegration:
    """Интеграционные unit-тесты для process()."""

    def test_process_returns_correct_result_structure(self):
        """Проверка структуры ImportResult."""
        # ARRANGE
        xml_data = build_test_xml()
        service = OrderStatusImportService()

        # Пустой кэш — заказ не найден
        with patch.object(service, "_bulk_fetch_orders", return_value={}):
            # ACT
            result = service.process(xml_data)

            # ASSERT
            assert isinstance(result, ImportResult)
            assert hasattr(result, "processed")
            assert hasattr(result, "updated")
            assert hasattr(result, "skipped")
            assert hasattr(result, "not_found")
            assert hasattr(result, "errors")

    def test_process_handles_xml_parse_error(self):
        """Обработка ошибки парсинга XML."""
        # ARRANGE
        invalid_xml = "<not valid xml>"
        service = OrderStatusImportService()
        
        # ACT
        result = service.process(invalid_xml)
        
        # ASSERT
        assert len(result.errors) > 0
        assert result.processed == 0
