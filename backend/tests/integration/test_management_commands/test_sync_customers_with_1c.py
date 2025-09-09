"""
Интеграционные тесты для команды sync_customers_with_1c
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.users.models import User


@pytest.mark.integration
@pytest.mark.django_db
class TestSyncCustomersWith1CCommand:
    """Тесты команды синхронизации клиентов с 1С"""

    def test_command_export_new_success(self):
        """Тест экспорта новых клиентов в 1С"""
        # Создаем клиента, который нуждается в экспорте
        customer = User.objects.create(
            email="test@export.com",
            first_name="Тестовый",
            last_name="Экспорт",
            needs_1c_export=True,
            sync_status="pending",
        )

        out = StringIO()
        call_command("sync_customers_with_1c", "--export-new", stdout=out, verbosity=1)

        output = out.getvalue()
        assert "🔄 Запуск синхронизации клиентов с 1С" in output
        assert "📤 Экспорт новых клиентов в 1С..." in output
        assert "Найдено клиентов для экспорта: 1" in output
        assert "✅ Синхронизация завершена: 1 экспортировано, 0 импортировано" in output

        # Проверяем что статус клиента обновился
        customer.refresh_from_db()
        assert customer.needs_1c_export is False
        assert customer.sync_status == "synced"
        assert customer.onec_id is not None
        assert customer.last_sync_at is not None

    def test_command_import_updates_success(self):
        """Тест импорта обновлений клиентов из 1С"""
        # Создаем синхронизированного клиента
        customer = User.objects.create(
            email="test@import.com",
            first_name="Старое имя",
            last_name="Старая фамилия",
            onec_id="1C-SYNC-001",
            sync_status="synced",
            company_name="Старая компания",
        )

        out = StringIO()
        call_command(
            "sync_customers_with_1c", "--import-updates", stdout=out, verbosity=1
        )

        output = out.getvalue()
        assert "📥 Импорт обновлений клиентов из 1С..." in output

        # Проверяем что клиент может быть обновлен (зависит от mock данных)
        customer.refresh_from_db()
        assert customer.last_sync_at is not None

    def test_command_full_sync_success(self):
        """Тест полной синхронизации"""
        # Создаем клиентов для экспорта и импорта
        export_customer = User.objects.create(
            email="export@test.com",
            first_name="Экспорт",
            last_name="Клиент",
            needs_1c_export=True,
        )

        import_customer = User.objects.create(
            email="import@test.com",
            first_name="Импорт",
            last_name="Клиент",
            onec_id="1C-IMPORT-001",
            sync_status="synced",
        )

        out = StringIO()
        call_command("sync_customers_with_1c", "--full-sync", stdout=out, verbosity=1)

        output = out.getvalue()
        assert "📤 Экспорт новых клиентов в 1С..." in output
        assert "📥 Импорт обновлений клиентов из 1С..." in output

        # Проверяем обновления
        export_customer.refresh_from_db()
        assert export_customer.needs_1c_export is False
        assert export_customer.sync_status == "synced"

    def test_command_without_parameters_fails(self):
        """Тест команды без обязательных параметров"""
        with pytest.raises(CommandError, match="Укажите режим синхронизации"):
            call_command("sync_customers_with_1c", verbosity=0)

    def test_command_dry_run_no_changes(self):
        """Тест что dry-run не изменяет клиентов"""
        customer = User.objects.create(
            email="test@dryrun.com",
            first_name="Тест",
            last_name="DryRun",
            needs_1c_export=True,
            sync_status="pending",
        )

        original_status = customer.sync_status
        original_export_flag = customer.needs_1c_export

        call_command("sync_customers_with_1c", "--export-new", "--dry-run", verbosity=0)

        # Проверяем что клиент не изменился
        customer.refresh_from_db()
        assert customer.sync_status == original_status
        assert customer.needs_1c_export == original_export_flag
        assert customer.onec_id is None  # Не должен быть назначен

    def test_export_only_active_customers(self):
        """Тест что экспортируются только активные клиенты"""
        # Активный клиент
        active_customer = User.objects.create(
            email="active@test.com",
            first_name="Активный",
            last_name="Клиент",
            is_active=True,
            needs_1c_export=True,
        )

        # Неактивный клиент
        inactive_customer = User.objects.create(
            email="inactive@test.com",
            first_name="Неактивный",
            last_name="Клиент",
            is_active=False,
            needs_1c_export=True,
        )

        out = StringIO()
        call_command("sync_customers_with_1c", "--export-new", stdout=out, verbosity=1)

        output = out.getvalue()
        assert "Найдено клиентов для экспорта: 1" in output

        # Проверяем что только активный клиент экспортирован
        active_customer.refresh_from_db()
        inactive_customer.refresh_from_db()

        assert active_customer.needs_1c_export is False
        assert active_customer.sync_status == "synced"

        assert inactive_customer.needs_1c_export is True  # Не изменился
        assert inactive_customer.sync_status != "synced"

    def test_force_all_exports_all_customers(self):
        """Тест что --force-all экспортирует всех активных клиентов"""
        # Клиент без флага экспорта
        customer1 = User.objects.create(
            email="customer1@test.com",
            first_name="Клиент1",
            needs_1c_export=False,
            is_active=True,
        )

        # Клиент с флагом экспорта
        customer2 = User.objects.create(
            email="customer2@test.com",
            first_name="Клиент2",
            needs_1c_export=True,
            is_active=True,
        )

        out = StringIO()
        call_command(
            "sync_customers_with_1c",
            "--export-new",
            "--force-all",
            stdout=out,
            verbosity=1,
        )

        output = out.getvalue()
        assert "Найдено клиентов для экспорта: 2" in output

        # Оба клиента должны быть обновлены
        customer1.refresh_from_db()
        customer2.refresh_from_db()

        assert customer1.sync_status == "synced"
        assert customer2.sync_status == "synced"

    def test_chunk_size_processing(self):
        """Тест обработки батчами"""
        # Создаем несколько клиентов для экспорта
        for i in range(5):
            User.objects.create(
                email=f"batch{i}@test.com",
                first_name=f"Batch{i}",
                needs_1c_export=True,
                is_active=True,
            )

        out = StringIO()
        call_command(
            "sync_customers_with_1c",
            "--export-new",
            "--chunk-size=2",
            stdout=out,
            verbosity=1,
        )

        output = out.getvalue()
        assert "Найдено клиентов для экспорта: 5" in output
        assert "✅ Синхронизация завершена: 5 экспортировано" in output

        # Все клиенты должны быть экспортированы
        exported_count = User.objects.filter(
            email__startswith="batch", sync_status="synced"
        ).count()
        assert exported_count == 5

    def test_import_updates_existing_customers(self):
        """Тест импорта обновлений для существующих клиентов"""
        # Создаем клиентов которые могут получить обновления
        customers_data = []
        for i in range(3):
            customer = User.objects.create(
                email=f"update{i}@test.com",
                first_name=f"ИмяДо{i}",
                last_name="Фамилия",
                onec_id=f"1C-UPDATE-{i:03d}",
                sync_status="synced",
                company_name=f"КомпанияДо{i}",
            )
            customers_data.append(customer)

        call_command("sync_customers_with_1c", "--import-updates", verbosity=0)

        # Проверяем что клиенты обновлены (если они попали в mock данные)
        for customer in customers_data:
            customer.refresh_from_db()
            # last_sync_at должно быть обновлено независимо от изменения данных
            assert customer.last_sync_at is not None

    def test_export_assigns_onec_id(self):
        """Тест что экспорт назначает onec_id"""
        customer = User.objects.create(
            email="test@onecid.com",
            first_name="Тест",
            last_name="OneCID",
            needs_1c_export=True,
            onec_id=None,
        )

        call_command("sync_customers_with_1c", "--export-new", verbosity=0)

        customer.refresh_from_db()
        assert customer.onec_id is not None
        assert customer.onec_id.startswith("1C-")

    def test_sync_status_tracking(self):
        """Тест отслеживания статусов синхронизации"""
        customer = User.objects.create(
            email="status@test.com",
            first_name="Статус",
            last_name="Тест",
            needs_1c_export=True,
            sync_status="pending",
        )

        call_command("sync_customers_with_1c", "--export-new", verbosity=0)

        customer.refresh_from_db()
        assert customer.sync_status == "synced"
        assert customer.sync_error_message == ""
        assert customer.last_sync_at is not None
        assert (timezone.now() - customer.last_sync_at).seconds < 60  # Недавно обновлен
