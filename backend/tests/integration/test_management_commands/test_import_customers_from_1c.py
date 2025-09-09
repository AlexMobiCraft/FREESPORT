"""
Интеграционные тесты для команды import_customers_from_1c
"""

import json
import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.users.models import User


@pytest.mark.integration
@pytest.mark.django_db
class TestImportCustomersFrom1CCommand:
    """Тесты команды импорта клиентов из 1С"""

    def test_command_with_mock_data_success(self):
        """Тест команды с тестовыми данными"""
        out = StringIO()

        call_command(
            "import_customers_from_1c",
            "--mock-data",
            "--dry-run",
            stdout=out,
            verbosity=1,
        )

        output = out.getvalue()
        assert "🚀 Запуск импорта клиентов из 1С" in output
        assert "📦 Загружены тестовые данные: 15 клиентов" in output
        assert "✅ DRY-RUN завершен: 15 клиентов обработано" in output

    def test_command_creates_customers_with_mock_data(self):
        """Тест создания клиентов с тестовыми данными"""
        initial_count = User.objects.count()

        call_command("import_customers_from_1c", "--mock-data", verbosity=0)

        final_count = User.objects.count()
        assert final_count > initial_count

        # Проверяем созданных клиентов
        test_customers = User.objects.filter(onec_id__startswith="1C-CUSTOMER-")
        assert test_customers.count() == 15

        # Проверяем первого клиента
        first_customer = test_customers.first()
        assert first_customer.first_name == "Имя1"
        assert first_customer.last_name == "Фамилия1"
        assert first_customer.email == "customer1@test-1c.ru"
        assert first_customer.sync_status == "synced"
        assert first_customer.created_in_1c is True

    def test_command_with_json_file_success(self):
        """Тест команды с JSON файлом"""
        # Создаем временный JSON файл
        test_data = {
            "customers": [
                {
                    "onec_id": "JSON-CUSTOMER-001",
                    "email": "test@example.com",
                    "first_name": "Тестовый",
                    "last_name": "Клиент",
                    "role": "wholesale_level1",
                    "phone_number": "+79991234567",
                    "company_name": "ООО Тест",
                    "is_active": True,
                    "created_in_1c": True,
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f, ensure_ascii=False)
            json_file_path = f.name

        try:
            call_command(
                "import_customers_from_1c", f"--file={json_file_path}", verbosity=0
            )

            # Проверяем что клиент создан
            customer = User.objects.get(onec_id="JSON-CUSTOMER-001")
            assert customer.email == "test@example.com"
            assert customer.first_name == "Тестовый"
            assert customer.last_name == "Клиент"
            assert customer.role == "wholesale_level1"
            assert customer.phone == "+79991234567"
            assert customer.company_name == "ООО Тест"
            assert customer.is_active is True

        finally:
            Path(json_file_path).unlink()

    def test_command_with_invalid_json_file_fails(self):
        """Тест команды с некорректным JSON файлом"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            json_file_path = f.name

        try:
            with pytest.raises(CommandError, match="Ошибка парсинга JSON"):
                call_command(
                    "import_customers_from_1c", f"--file={json_file_path}", verbosity=0
                )
        finally:
            Path(json_file_path).unlink()

    def test_command_with_nonexistent_file_fails(self):
        """Тест команды с несуществующим файлом"""
        with pytest.raises(CommandError, match="Файл не найден"):
            call_command(
                "import_customers_from_1c", "--file=/nonexistent/file.json", verbosity=0
            )

    def test_command_xml_not_implemented(self):
        """Тест что XML парсер не реализован"""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"<xml>test</xml>")
            xml_file_path = f.name

        try:
            with pytest.raises(CommandError, match="XML парсер будет реализован"):
                call_command(
                    "import_customers_from_1c", f"--file={xml_file_path}", verbosity=0
                )
        finally:
            Path(xml_file_path).unlink()

    def test_command_without_parameters_fails(self):
        """Тест команды без обязательных параметров"""
        with pytest.raises(CommandError, match="Укажите либо --file"):
            call_command("import_customers_from_1c", verbosity=0)

    def test_command_dry_run_no_changes(self):
        """Тест что dry-run не создает клиентов"""
        initial_count = User.objects.count()

        call_command(
            "import_customers_from_1c", "--mock-data", "--dry-run", verbosity=0
        )

        final_count = User.objects.count()
        assert final_count == initial_count  # Нет изменений

    def test_command_force_overwrites_existing(self):
        """Тест что --force перезаписывает существующих клиентов"""
        # Создаем тестового клиента
        customer = User.objects.create(
            onec_id="1C-CUSTOMER-00001",
            email="old@test.com",
            first_name="Старое",
            last_name="Имя",
            role="retail",
        )

        call_command("import_customers_from_1c", "--mock-data", "--force", verbosity=0)

        # Проверяем что клиент обновился
        customer.refresh_from_db()
        assert customer.first_name == "Имя1"
        assert customer.last_name == "Фамилия1"
        assert customer.email == "customer1@test-1c.ru"

    def test_command_without_force_skips_existing(self):
        """Тест что без --force существующие клиенты пропускаются"""
        # Создаем тестового клиента
        original_email = "original@test.com"
        customer = User.objects.create(
            onec_id="1C-CUSTOMER-00001",
            email=original_email,
            first_name="Оригинальное",
            last_name="Имя",
            role="retail",
        )

        call_command("import_customers_from_1c", "--mock-data", verbosity=0)

        # Проверяем что клиент НЕ изменился
        customer.refresh_from_db()
        assert customer.email == original_email
        assert customer.first_name == "Оригинальное"
        assert customer.last_name == "Имя"

    def test_command_with_chunk_size(self):
        """Тест команды с настройкой размера батча"""
        out = StringIO()

        call_command(
            "import_customers_from_1c",
            "--mock-data",
            "--chunk-size=5",
            "--dry-run",
            stdout=out,
            verbosity=1,
        )

        output = out.getvalue()
        assert "✅ DRY-RUN завершен: 15 клиентов обработано" in output

    def test_customer_role_assignment(self):
        """Тест назначения ролей клиентам"""
        call_command("import_customers_from_1c", "--mock-data", verbosity=0)

        test_customers = User.objects.filter(onec_id__startswith="1C-CUSTOMER-")

        # Проверяем что созданы клиенты разных ролей
        roles_created = set(test_customers.values_list("role", flat=True))
        expected_roles = {
            "retail",
            "wholesale_level1",
            "wholesale_level2",
            "wholesale_level3",
            "trainer",
        }

        # Должна быть хотя бы одна роль из ожидаемых
        assert roles_created.intersection(expected_roles)

    def test_company_data_assignment(self):
        """Тест назначения корпоративных данных"""
        call_command("import_customers_from_1c", "--mock-data", verbosity=0)

        test_customers = User.objects.filter(onec_id__startswith="1C-CUSTOMER-")

        # Некоторые клиенты должны иметь корпоративные данные
        customers_with_company = test_customers.exclude(company_name="")
        customers_with_tax_id = test_customers.exclude(tax_id="")

        assert customers_with_company.exists()
        assert customers_with_tax_id.exists()
