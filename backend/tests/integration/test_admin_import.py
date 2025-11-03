"""
Integration тесты для admin action импорта каталога из 1С

Проверяет:
- Запуск импорта через admin action
- Concurrent import prevention через Redis lock
- Освобождение lock после завершения/ошибки
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django_redis import get_redis_connection

from apps.products.admin import ImportSessionAdmin
from apps.products.models import ImportSession

if TYPE_CHECKING:
    from django.db.models import QuerySet

User = get_user_model()


@pytest.mark.integration
@pytest.mark.django_db
class TestImportAdminAction:
    """Тесты для admin action импорта каталога"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = ImportSessionAdmin(ImportSession, self.site)
        self.user = User.objects.create_superuser(
            email="admin@test.com", password="testpass123"
        )

        # Очистить Redis lock перед каждым тестом
        redis_conn = get_redis_connection("default")
        redis_conn.delete("import_catalog_lock")

    def teardown_method(self) -> None:
        """Очистка после каждого теста"""
        # Убедиться что lock освобожден
        redis_conn = get_redis_connection("default")
        redis_conn.delete("import_catalog_lock")

    def _create_request_with_messages(self, path: str = "/admin/") -> MagicMock:
        """Создает mock request с поддержкой messages framework"""
        request = self.factory.post(path)
        request.user = self.user

        # Mock для messages framework
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        return request

    @patch("apps.products.admin.call_command")
    @patch("apps.products.admin.settings")
    def test_trigger_import_success(
        self, mock_settings: MagicMock, mock_call_command: MagicMock
    ) -> None:
        """
        Тест успешного запуска импорта через admin action.

        Проверяет что:
        - call_command вызывается с правильными параметрами
        - Lock захватывается и освобождается
        - Показывается success сообщение
        """
        # Arrange
        mock_settings.ONEC_DATA_DIR = "/fake/data/dir"
        request = self._create_request_with_messages()
        queryset = ImportSession.objects.none()

        # Act
        self.admin.trigger_catalog_import(request, queryset)

        # Assert
        mock_call_command.assert_called_once_with(
            "import_catalog_from_1c", "--data-dir", "/fake/data/dir"
        )

        # Проверить что lock освобожден
        redis_conn = get_redis_connection("default")
        lock = redis_conn.lock("import_catalog_lock", timeout=1)
        assert lock.acquire(blocking=False), "Lock должен быть освобожден после импорта"
        lock.release()

    @patch("apps.products.admin.call_command")
    @patch("apps.products.admin.settings")
    def test_concurrent_import_prevention(
        self, mock_settings: MagicMock, mock_call_command: MagicMock
    ) -> None:
        """
        Тест предотвращения concurrent импортов через Redis lock.

        Проверяет что:
        - Второй импорт не запускается если lock уже захвачен
        - Показывается warning сообщение
        - call_command НЕ вызывается
        """
        # Arrange
        mock_settings.ONEC_DATA_DIR = "/fake/data/dir"
        redis_conn = get_redis_connection("default")

        # Захватить lock вручную (симуляция running импорта)
        lock = redis_conn.lock("import_catalog_lock", timeout=10)
        acquired = lock.acquire(blocking=False)
        assert acquired, "Не удалось захватить lock для теста"

        try:
            request = self._create_request_with_messages()
            queryset = ImportSession.objects.none()

            # Act
            self.admin.trigger_catalog_import(request, queryset)

            # Assert
            mock_call_command.assert_not_called()

            # Проверить что было warning сообщение
            messages = list(request._messages)
            assert len(messages) > 0, "Должно быть warning сообщение"
            assert "⚠️" in str(messages[0]) or "уже запущен" in str(messages[0])

        finally:
            lock.release()

    @patch("apps.products.admin.call_command")
    @patch("apps.products.admin.settings")
    def test_lock_released_on_exception(
        self, mock_settings: MagicMock, mock_call_command: MagicMock
    ) -> None:
        """
        Тест освобождения lock при ошибке импорта.

        Проверяет что:
        - Lock освобождается даже если call_command выбрасывает exception
        - Показывается error сообщение
        """
        # Arrange
        mock_settings.ONEC_DATA_DIR = "/fake/data/dir"
        mock_call_command.side_effect = RuntimeError("Import failed")

        request = self._create_request_with_messages()
        queryset = ImportSession.objects.none()

        # Act
        self.admin.trigger_catalog_import(request, queryset)

        # Assert
        mock_call_command.assert_called_once()

        # Проверить что lock освобожден даже после ошибки
        redis_conn = get_redis_connection("default")
        lock = redis_conn.lock("import_catalog_lock", timeout=1)
        assert lock.acquire(
            blocking=False
        ), "Lock должен быть освобожден после ошибки"
        lock.release()

        # Проверить что было error сообщение
        messages = list(request._messages)
        assert len(messages) > 0, "Должно быть error сообщение"
        assert "❌" in str(messages[0]) or "Ошибка" in str(messages[0])

    @patch("apps.products.admin.call_command")
    def test_trigger_import_missing_settings(
        self, mock_call_command: MagicMock
    ) -> None:
        """
        Тест обработки отсутствующей настройки ONEC_DATA_DIR.

        Проверяет что:
        - Показывается error сообщение
        - call_command НЕ вызывается
        - Lock освобождается
        """
        # Arrange
        request = self._create_request_with_messages()
        queryset = ImportSession.objects.none()

        # Удаляем ONEC_DATA_DIR из settings временно
        with patch("apps.products.admin.settings") as mock_settings:
            with patch("apps.products.admin.getattr", return_value=None):
                # Act
                self.admin.trigger_catalog_import(request, queryset)

        # Assert
        mock_call_command.assert_not_called()

        # Проверить что lock освобожден
        redis_conn = get_redis_connection("default")
        lock = redis_conn.lock("import_catalog_lock", timeout=1)
        assert lock.acquire(blocking=False), "Lock должен быть освобожден"
        lock.release()

        # Проверить что было error сообщение
        messages = list(request._messages)
        assert len(messages) > 0, "Должно быть error сообщение"


@pytest.mark.integration
@pytest.mark.django_db
class TestImportSessionDisplayMethods:
    """Тесты для display methods в ImportSessionAdmin"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.admin = ImportSessionAdmin(ImportSession, AdminSite())

    def test_colored_status_display_completed(self) -> None:
        """Тест отображения статуса 'completed' с зеленым цветом"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
        )

        result = self.admin.colored_status(import_session)

        assert "green" in result
        assert "✅" in result
        assert "Завершено" in result

    def test_colored_status_display_in_progress(self) -> None:
        """Тест отображения статуса 'in_progress' с оранжевым цветом"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )

        result = self.admin.colored_status(import_session)

        assert "orange" in result
        assert "⏳" in result

    def test_colored_status_display_failed(self) -> None:
        """Тест отображения статуса 'failed' с красным цветом"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.FAILED,
        )

        result = self.admin.colored_status(import_session)

        assert "red" in result
        assert "❌" in result

    def test_duration_display_not_finished(self) -> None:
        """Тест отображения длительности для незавершенного импорта"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )

        result = self.admin.duration(import_session)

        assert result == "В процессе..."

    def test_progress_display_with_data(self) -> None:
        """Тест отображения прогресса с реальными данными"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            report_details={"total_items": 100, "processed_items": 50},
        )

        result = self.admin.progress_display(import_session)

        assert "<progress" in result
        assert "50%" in result or "50.0%" in result
        assert "50/100" in result

    def test_progress_display_no_data(self) -> None:
        """Тест отображения прогресса без данных"""
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
        )

        result = self.admin.progress_display(import_session)

        assert result == "-"
