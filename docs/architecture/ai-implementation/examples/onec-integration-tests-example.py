"""
Тесты интеграции с 1С - обязательные тесты по требованиям FREESPORT
Соответствует docs/architecture/10-testing-strategy.md секция 10.6 "Обязательные тестовые сценарии"
"""
import pytest
import json
from unittest.mock import patch, Mock
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import UserFactory, ProductFactory
from apps.common.services import OneCCustomerSyncService, CustomerSyncConflictResolver
from apps.common.models import ImportLog, SyncConflict, CustomerSyncLog

User = get_user_model()

# Маркировка для всего модуля
pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
    pytest.mark.onec_integration,
]


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 1: Успешный импорт покупателей из 1С =====


class TestOneCCustomerImport:
    """✅ ОБЯЗАТЕЛЬНО: Успешный импорт покупателей из 1С"""

    def test_successful_customer_import_from_1c(self):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Тестирование импорта покупателей из 1С
        Требование: docs/architecture/10-testing-strategy.md - пункт 1
        """
        # ARRANGE: Подготовка данных как от 1С
        customers_data = {
            "customers": [
                {
                    "onec_id": "CLIENT_001",
                    "onec_guid": "550e8400-e29b-41d4-a716-446655440000",
                    "email": f"client-{get_unique_suffix()}@example.com",
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "company_name": f"ООО Спорт-{get_unique_suffix()}",
                    "tax_id": f"{get_unique_suffix()}"[:10],
                    "role": "wholesale_level2",
                },
                {
                    "onec_id": "CLIENT_002",
                    "onec_guid": "550e8400-e29b-41d4-a716-446655440001",
                    "email": f"client2-{get_unique_suffix()}@example.com",
                    "first_name": "Петр",
                    "last_name": "Иванов",
                    "company_name": f"ИП Иванов-{get_unique_suffix()}",
                    "tax_id": f"{get_unique_suffix()}"[:10],
                    "role": "wholesale_level1",
                },
            ]
        }

        # ACT: Выполнение импорта
        api_client = APIClient()
        api_client.credentials(HTTP_X_API_KEY="test-1c-api-key")
        response = api_client.post(
            "/api/onec/customers/", customers_data, format="json"
        )

        # ASSERT: Проверка результата
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["imported_count"] == 2
        assert data["conflicts_count"] == 0

        # Проверяем что пользователи создались в БД
        user1 = User.objects.get(onec_id="CLIENT_001")
        assert user1.role == "wholesale_level2"
        assert user1.company_name.startswith("ООО Спорт")

        user2 = User.objects.get(onec_id="CLIENT_002")
        assert user2.role == "wholesale_level1"
        assert user2.company_name.startswith("ИП Иванов")

        # Проверяем создание логов
        import_log = ImportLog.objects.filter(import_type="customers").first()
        assert import_log is not None
        assert import_log.status == "completed"
        assert import_log.successful_records == 2


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 2: Обработка конфликтов данных =====


class TestOneCConflictHandling:
    """✅ ОБЯЗАТЕЛЬНО: Обработка конфликтов данных при импорте"""

    def test_conflict_detection_and_logging(self):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Обработка конфликтов данных при импорте
        Требование: docs/architecture/10-testing-strategy.md - пункт 2
        """
        # ARRANGE: Создаем существующего пользователя
        existing_email = f"conflict-{get_unique_suffix()}@example.com"
        existing_user = UserFactory(
            email=existing_email,
            company_name=f"ООО Старая компания-{get_unique_suffix()}",
            tax_id="1111111111",
        )

        # Импортируем того же пользователя с другими данными
        conflicting_data = {
            "customers": [
                {
                    "onec_id": "CLIENT_CONFLICT",
                    "email": existing_email,  # Тот же email
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "company_name": f"ООО Новая компания-{get_unique_suffix()}",  # ⚠️ Конфликт!
                    "tax_id": "2222222222",  # ⚠️ Конфликт!
                    "role": "wholesale_level1",
                }
            ]
        }

        # ACT: Выполнение импорта с конфликтами
        api_client = APIClient()
        api_client.credentials(HTTP_X_API_KEY="test-1c-api-key")
        response = api_client.post(
            "/api/onec/customers/", conflicting_data, format="json"
        )

        # ASSERT: Проверка обработки конфликтов
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["conflicts_count"] == 1
        assert data["imported_count"] == 0  # Конфликтные записи не импортируются

        # Проверяем что создалась запись о конфликте
        conflict = SyncConflict.objects.filter(customer=existing_user).first()
        assert conflict is not None
        assert not conflict.is_resolved
        assert "company_name" in conflict.conflicting_fields
        assert "tax_id" in conflict.conflicting_fields

        # Исходные данные не изменились
        existing_user.refresh_from_db()
        assert existing_user.company_name.startswith("ООО Старая компания")
        assert existing_user.tax_id == "1111111111"

    def test_conflict_resolution_strategies(self):
        """Тестирование стратегий разрешения конфликтов"""
        platform_data = {
            "email": f"strategy-{get_unique_suffix()}@example.com",
            "company_name": f"ООО Платформа-{get_unique_suffix()}",
            "tax_id": "1111111111",
            "phone": "+7900123456",
        }

        onec_data = {
            "email": platform_data["email"],
            "company_name": f"ООО 1С Система-{get_unique_suffix()}",  # Конфликт!
            "tax_id": "2222222222",  # Конфликт!
            "phone": "+7900123456",
        }

        resolver = CustomerSyncConflictResolver()
        conflicts = resolver._detect_conflicts(platform_data, onec_data)

        # Проверяем обнаружение конфликтов
        assert len(conflicts) == 2
        conflict_fields = [c["field"] for c in conflicts]
        assert "company_name" in conflict_fields
        assert "tax_id" in conflict_fields

        # Проверяем определение серьезности
        tax_id_conflict = next(c for c in conflicts if c["field"] == "tax_id")
        assert tax_id_conflict["severity"] == "high"


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 3: Экспорт B2B регистраций в 1С =====


class TestOneCCustomerExport:
    """✅ ОБЯЗАТЕЛЬНО: Экспорт новых B2B регистраций в 1С"""

    @patch("apps.common.services.OneCCircuitBreaker.call_1c_api")
    def test_export_b2b_registration_to_1c(self, mock_1c_call):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Экспорт B2B регистрации в 1С
        Требование: docs/architecture/10-testing-strategy.md - пункт 3
        """
        # ARRANGE: Настраиваем mock ответ от 1С
        mock_1c_call.return_value = {
            "status": "success",
            "onec_id": "CLIENT_NEW_001",
            "message": "Customer created successfully",
        }

        # Создаем B2B пользователя для экспорта
        user = UserFactory(
            role="wholesale_level2",
            email=f"b2b-export-{get_unique_suffix()}@example.com",
            company_name=f"ООО Экспорт Тест-{get_unique_suffix()}",
            tax_id=f"{get_unique_suffix()}"[:10],
            is_verified=True,
        )

        # ACT: Экспортируем в 1С
        sync_service = OneCCustomerSyncService()
        result = sync_service.export_customer_to_1c(user)

        # ASSERT: Проверяем результат экспорта
        assert result["status"] == "success"
        assert result["onec_id"] == "CLIENT_NEW_001"

        # Проверяем что пользователь обновился
        user.refresh_from_db()
        assert user.onec_id == "CLIENT_NEW_001"
        assert user.last_sync_to_1c is not None

        # Проверяем что создался лог синхронизации
        sync_log = CustomerSyncLog.objects.filter(
            customer=user, operation_type="export_to_1c"
        ).first()
        assert sync_log is not None
        assert sync_log.status == "success"

        # Проверяем содержимое вызова 1С API
        mock_1c_call.assert_called_once()
        call_args = mock_1c_call.call_args[0][0]  # Первый аргумент вызова
        assert call_args["email"] == user.email
        assert call_args["company_name"] == user.company_name
        assert call_args["role"] == "wholesale_level2"


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 4: Fallback к файловому обмену =====


class TestOneCFallbackBehavior:
    """✅ ОБЯЗАТЕЛЬНО: Fallback к файловому обмену при недоступности 1С"""

    @patch("apps.common.services.OneCCircuitBreaker.call_1c_api")
    def test_fallback_to_file_exchange_when_1c_unavailable(self, mock_1c_call):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Fallback к файловому обмену
        Требование: docs/architecture/10-testing-strategy.md - пункт 4
        """
        # ARRANGE: Настраиваем mock для имитации fallback
        mock_1c_call.return_value = {
            "status": "fallback_success",
            "method": "file",
            "file_path": "/tmp/export_customers_20231201.xml",
            "message": "Exported to XML file for manual processing",
        }

        user = UserFactory(
            role="wholesale_level1", email=f"fallback-{get_unique_suffix()}@example.com"
        )

        # ACT: Пытаемся экспортировать при недоступности 1С
        sync_service = OneCCustomerSyncService()
        result = sync_service.export_customer_to_1c(user)

        # ASSERT: Проверяем что сработал fallback
        assert result["status"] == "fallback_success"
        assert result["method"] == "file"
        assert "file_path" in result

        # Проверяем что создался лог с отметкой о fallback
        sync_log = CustomerSyncLog.objects.filter(customer=user).first()
        assert sync_log is not None
        assert "fallback" in sync_log.details.get("method", "")
        assert sync_log.status == "fallback_success"


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 5: Circuit Breaker поведение =====


class TestOneCCircuitBreaker:
    """✅ ОБЯЗАТЕЛЬНО: Circuit breaker behavior при ошибках 1С"""

    @patch("apps.common.services.requests.post")
    def test_circuit_breaker_opens_after_failures(self, mock_post):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Circuit breaker при ошибках 1С
        Требование: docs/architecture/10-testing-strategy.md - пункт 5
        """
        from apps.common.services import OneCCircuitBreaker

        # ARRANGE: Настраиваем mock для имитации ошибок
        mock_post.side_effect = ConnectionError("1C service unavailable")

        circuit_breaker = OneCCircuitBreaker()
        users = UserFactory.create_batch(3, role="wholesale_level1")

        # ACT: Выполняем несколько запросов которые должны упасть
        results = []
        for user in users:
            try:
                result = circuit_breaker.call_1c_api(
                    {"email": user.email, "company_name": user.company_name}
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        # ASSERT: Проверяем что circuit breaker сработал
        # Первые запросы должны пытаться достучаться до 1С
        # После определенного количества ошибок должен включиться fallback
        errors = [r for r in results if "error" in r]
        assert len(errors) > 0  # Должны быть ошибки

        # Circuit breaker должен открыться и перестать вызывать 1С
        assert circuit_breaker.state in ["open", "half_open"]

    @patch("apps.common.services.OneCCircuitBreaker.is_circuit_open")
    def test_circuit_breaker_prevents_calls_when_open(self, mock_is_open):
        """Тест что открытый circuit breaker предотвращает вызовы"""
        # ARRANGE
        mock_is_open.return_value = True

        sync_service = OneCCustomerSyncService()
        user = UserFactory(role="wholesale_level2")

        # ACT
        result = sync_service.export_customer_to_1c(user)

        # ASSERT
        assert result["status"] in ["fallback_success", "circuit_open"]
        assert "circuit breaker" in result.get("message", "").lower()


# ===== ОБЯЗАТЕЛЬНЫЙ ТЕСТ 6: Разрешение конфликтов =====


class TestOneCConflictResolution:
    """✅ ОБЯЗАТЕЛЬНО: Разрешение конфликтов различными стратегиями"""

    def test_manual_conflict_resolution(self):
        """
        ОБЯЗАТЕЛЬНЫЙ ТЕСТ: Ручное разрешение конфликтов
        Требование: docs/architecture/10-testing-strategy.md - пункт 6
        """
        # ARRANGE: Создаем конфликт
        user = UserFactory(
            email=f"manual-resolve-{get_unique_suffix()}@example.com",
            company_name=f"Исходная компания-{get_unique_suffix()}",
        )

        conflict = SyncConflict.objects.create(
            conflict_type="customer_data",
            customer=user,
            platform_data={"company_name": user.company_name},
            onec_data={"company_name": f"1С компания-{get_unique_suffix()}"},
            conflicting_fields=["company_name"],
            severity="medium",
        )

        # ACT: Разрешаем конфликт вручную (выбираем данные 1С)
        api_client = APIClient()
        admin_user = UserFactory(role="admin", is_staff=True)
        api_client.force_authenticate(user=admin_user)

        response = api_client.post(
            f"/api/onec/conflicts/{conflict.id}/resolve/",
            {
                "resolution_strategy": "prefer_onec",
                "resolved_data": {"company_name": f"1С компания-{get_unique_suffix()}"},
            },
        )

        # ASSERT: Проверяем результат разрешения
        assert response.status_code == status.HTTP_200_OK

        # Конфликт должен быть отмечен как разрешенный
        conflict.refresh_from_db()
        assert conflict.is_resolved is True
        assert conflict.resolved_by == admin_user
        assert conflict.resolution_strategy == "prefer_onec"

        # Данные пользователя должны обновиться
        user.refresh_from_db()
        assert user.company_name.startswith("1С компания")

    def test_automatic_conflict_resolution_by_priority(self):
        """Автоматическое разрешение конфликтов по приоритету полей"""
        resolver = CustomerSyncConflictResolver()

        # ARRANGE: Конфликт с полем высокого приоритета (tax_id)
        platform_data = {"tax_id": "1111111111"}
        onec_data = {"tax_id": "2222222222"}

        # ACT: Автоматическое разрешение
        resolution = resolver.auto_resolve_by_field_priority(platform_data, onec_data)

        # ASSERT: Высокоприоритетные поля (tax_id) должны предпочесть данные 1С
        assert resolution["strategy"] == "prefer_onec_for_critical_fields"
        assert resolution["resolved_data"]["tax_id"] == "2222222222"


# ===== ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ 1С ИНТЕГРАЦИИ =====


@pytest.mark.performance
class TestOneCPerformance:
    """Тесты производительности интеграции с 1С"""

    def test_bulk_customer_import_performance(self, django_assert_num_queries):
        """Тест производительности массового импорта"""
        # ARRANGE: Создаем данные для 100 клиентов
        customers_data = {
            "customers": [
                {
                    "onec_id": f"BULK_{i:03d}",
                    "email": f"bulk{i}-{get_unique_suffix()}@example.com",
                    "first_name": f"Клиент{i}",
                    "company_name": f"ООО Компания{i}-{get_unique_suffix()}",
                    "role": "wholesale_level1",
                }
                for i in range(100)
            ]
        }

        # ACT & ASSERT: Проверяем количество запросов к БД
        with django_assert_num_queries(15):  # Должно быть не более 15 запросов
            api_client = APIClient()
            api_client.credentials(HTTP_X_API_KEY="test-1c-api-key")
            response = api_client.post(
                "/api/onec/customers/", customers_data, format="json"
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            assert response.json()["imported_count"] == 100


# ===== УТИЛИТЫ ДЛЯ ТЕСТОВ =====

from apps.common.services import (
    get_unique_suffix,
)  # Импортируем нашу функцию уникальности
