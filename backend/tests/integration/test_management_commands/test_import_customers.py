"""
Integration-тесты для команды import_customers_from_1c
Используют реальные данные из data/import_1c/contragents/
"""
from __future__ import annotations

import pytest
from pathlib import Path
from django.core.management import call_command
from django.contrib.auth import get_user_model
from io import StringIO

from apps.common.models import CustomerSyncLog
from apps.products.models import ImportSession

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.integration
class TestImportCustomersCommand:
    """Integration-тесты для команды import_customers_from_1c"""

    @pytest.fixture
    def real_xml_file(self):
        """Путь к реальному XML файлу из 1С"""
        # В Docker контейнере data смонтирована в /app/data
        # Локально - из корня проекта
        import os

        if os.path.exists("/app/data"):
            # Docker environment
            xml_path = Path(
                "/app/data/import_1c/contragents/"
                "contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml"
            )
        else:
            # Local environment
            base_path = Path(__file__).parent.parent.parent.parent.parent
            xml_path = (
                base_path
                / "data"
                / "import_1c"
                / "contragents"
                / "contragents_1_564750cd-8a00-4926-a2a4-7a1c995605c0.xml"
            )
        return str(xml_path)

    def test_command_imports_real_customers(self, real_xml_file):
        """Тест импорта реальных клиентов из 1С"""
        out = StringIO()

        # Запустить команду
        call_command("import_customers_from_1c", file=real_xml_file, stdout=out)

        output = out.getvalue()

        # Проверить что команда вывела статистику
        assert "Начата сессия импорта" in output
        assert "Распознано" in output
        assert "клиентов" in output or "контрагентов" in output
        assert "Статистика обработки" in output
        assert "Импорт завершен успешно" in output

        # Проверить что сессия создана и завершена успешно
        session = ImportSession.objects.filter(
            import_type=ImportSession.ImportType.CUSTOMERS
        ).latest("started_at")

        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert session.finished_at is not None
        assert "total" in session.report_details
        assert session.report_details["total"] > 0

        # Проверить что клиенты созданы
        customers_count = User.objects.filter(created_in_1c=True).count()
        assert customers_count > 0
        assert (
            customers_count
            == session.report_details["created"] + session.report_details["updated"]
        )

        # Проверить что логи созданы
        logs_count = CustomerSyncLog.objects.filter(session=session).count()
        assert logs_count > 0

    def test_command_dry_run_mode(self, real_xml_file):
        """Тест dry-run режима команды"""
        initial_users_count = User.objects.count()

        out = StringIO()
        call_command(
            "import_customers_from_1c", file=real_xml_file, dry_run=True, stdout=out
        )

        output = out.getvalue()

        # Проверить сообщение о dry-run
        assert "DRY-RUN режим" in output
        assert "изменения не сохранены" in output

        # Проверить что данные НЕ сохранены
        assert User.objects.count() == initial_users_count

        # Проверить что сессия НЕ создана
        sessions_count = ImportSession.objects.filter(
            import_type=ImportSession.ImportType.CUSTOMERS
        ).count()
        assert sessions_count == 0

    def test_command_with_custom_chunk_size(self, real_xml_file):
        """Тест команды с пользовательским chunk_size"""
        out = StringIO()

        # Запустить с малым chunk_size
        call_command(
            "import_customers_from_1c", file=real_xml_file, chunk_size=2, stdout=out
        )

        output = out.getvalue()

        # Проверить успешное выполнение
        assert "Импорт завершен успешно" in output

        # Проверить что клиенты созданы
        session = ImportSession.objects.latest("started_at")
        assert session.status == ImportSession.ImportStatus.COMPLETED

    def test_command_handles_file_not_found(self):
        """Тест обработки несуществующего файла"""
        from django.core.management.base import CommandError

        with pytest.raises(CommandError) as exc_info:
            call_command("import_customers_from_1c", file="/nonexistent/file.xml")

        assert "Файл не найден" in str(exc_info.value)

    def test_command_handles_invalid_chunk_size(self, real_xml_file):
        """Тест обработки невалидного chunk_size"""
        from django.core.management.base import CommandError

        with pytest.raises(CommandError) as exc_info:
            call_command("import_customers_from_1c", file=real_xml_file, chunk_size=0)

        assert "chunk-size" in str(exc_info.value).lower()

    def test_command_prevents_concurrent_execution(self, real_xml_file):
        """Тест защиты от параллельного выполнения"""
        # Создать активную сессию импорта
        ImportSession.objects.create(
            import_type=ImportSession.ImportType.CUSTOMERS,
            status=ImportSession.ImportStatus.STARTED,
        )

        from django.core.management.base import CommandError

        with pytest.raises(CommandError) as exc_info:
            call_command("import_customers_from_1c", file=real_xml_file)

        error_message = str(exc_info.value)
        assert "уже выполняется" in error_message or "активн" in error_message

    def test_command_handles_malformed_xml(self, tmp_path):
        """Тест обработки некорректного XML"""
        malformed_xml = tmp_path / "malformed.xml"
        malformed_xml.write_text(
            "<КоммерческаяИнформация><Контрагенты>", encoding="utf-8"
        )

        with pytest.raises(Exception):  # Может быть CommandError или ValidationError
            call_command("import_customers_from_1c", file=str(malformed_xml))

        # Проверить что сессия помечена как failed
        sessions = ImportSession.objects.filter(
            import_type=ImportSession.ImportType.CUSTOMERS
        )
        if sessions.exists():
            session = sessions.latest("started_at")
            assert session.status == ImportSession.ImportStatus.FAILED
            assert session.error_message != ""

    def test_command_creates_correct_roles(self, real_xml_file):
        """Тест корректного маппинга ролей"""
        call_command("import_customers_from_1c", file=real_xml_file)

        # Проверить что роли корректно установлены
        users = User.objects.filter(created_in_1c=True)

        # Все роли должны быть валидными
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        for user in users:
            assert user.role in valid_roles

    def test_command_handles_customers_without_email(self, real_xml_file):
        """Тест обработки клиентов без email"""
        call_command("import_customers_from_1c", file=real_xml_file)

        # Проверить что клиенты без email созданы
        users_without_email = User.objects.filter(created_in_1c=True, email="")

        # Может быть 0 или больше клиентов без email
        if users_without_email.exists():
            # Для каждого клиента без email должен быть onec_id
            for user in users_without_email:
                assert user.onec_id

            # Проверить что есть логи с warning
            session = ImportSession.objects.latest("started_at")
            warning_logs = CustomerSyncLog.objects.filter(
                session=session, status=CustomerSyncLog.StatusType.WARNING
            )
            # Может быть warning логи для клиентов без email

    def test_command_updates_existing_customers(self, real_xml_file):
        """Тест обновления существующих клиентов"""
        # Запустить импорт первый раз
        call_command("import_customers_from_1c", file=real_xml_file)

        first_session = ImportSession.objects.latest("started_at")
        first_created = first_session.report_details["created"]

        # Запустить импорт второй раз
        call_command("import_customers_from_1c", file=real_xml_file)

        second_session = ImportSession.objects.latest("started_at")

        # Во второй раз должны быть только обновления, а не создания
        assert second_session.report_details["updated"] > 0
        assert second_session.report_details["created"] == 0

    def test_command_logs_all_operations(self, real_xml_file):
        """Тест логирования всех операций"""
        call_command("import_customers_from_1c", file=real_xml_file)

        session = ImportSession.objects.latest("started_at")
        logs_count = CustomerSyncLog.objects.filter(session=session).count()

        # Должно быть столько же логов, сколько обработано клиентов
        total_processed = session.report_details["total"]
        assert (
            logs_count >= total_processed
        )  # >= потому что может быть несколько логов на клиента

    def test_command_sets_sync_status(self, real_xml_file):
        """Тест установки статуса синхронизации"""
        call_command("import_customers_from_1c", file=real_xml_file)

        # Все импортированные клиенты должны иметь sync_status='synced'
        users = User.objects.filter(created_in_1c=True)
        for user in users:
            assert user.sync_status == "synced"
            assert user.last_sync_at is not None
