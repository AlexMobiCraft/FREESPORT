"""
Unit тесты для admin actions в products app

Проверяет отдельные методы ImportSessionAdmin в изоляции:
- duration calculation
- progress_display rendering
- colored_status rendering
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone

from apps.integrations.admin import ImportSessionAdmin
from apps.integrations.models import Session as ImportSession

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.django_db
class TestImportSessionAdminDuration:
    """Unit тесты для метода duration"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.admin = ImportSessionAdmin(ImportSession, AdminSite())

    def test_duration_completed_import_minutes(self) -> None:
        """
        Тест расчета длительности для завершенного импорта (минуты).

        Проверяет что длительность корректно вычисляется
        для импорта длительностью 5 минут.
        """
        # Arrange
        started = timezone.now()
        finished = started + timedelta(minutes=5)

        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
            started_at=started,
            finished_at=finished,
        )

        # Act
        result = self.admin.duration(import_session)

        # Assert
        assert "5.0 мин" in result

    def test_duration_completed_import_seconds(self) -> None:
        """
        Тест расчета длительности для быстрого импорта (секунды).

        Проверяет что для импорта длительностью < 1 минуты
        показывается время в секундах.
        """
        # Arrange
        started = timezone.now()
        finished = started + timedelta(seconds=30)

        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
            started_at=started,
            finished_at=finished,
        )

        # Act
        result = self.admin.duration(import_session)

        # Assert
        assert "30 сек" in result or "30.0 сек" in result

    def test_duration_in_progress(self) -> None:
        """
        Тест отображения длительности для импорта в процессе.

        Проверяет что для незавершенного импорта
        показывается "В процессе...".
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            started_at=timezone.now(),
            finished_at=None,
        )

        # Act
        result = self.admin.duration(import_session)

        # Assert
        assert result == "В процессе..."

    def test_duration_not_started(self) -> None:
        """
        Тест отображения длительности для импорта со статусом STARTED.

        Проверяет что для импорта со статусом STARTED
        (который технически уже начат, т.к. started_at установлен auto_now_add)
        показывается "В процессе...".

        Note: started_at устанавливается автоматически Django при создании,
        поэтому технически невозможно создать ImportSession без started_at.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
            finished_at=None,
        )

        # Act
        result = self.admin.duration(import_session)

        # Assert
        assert result == "В процессе..."


@pytest.mark.unit
@pytest.mark.django_db
class TestImportSessionAdminProgressDisplay:
    """Unit тесты для метода progress_display"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.admin = ImportSessionAdmin(ImportSession, AdminSite())

    def test_progress_display_50_percent(self) -> None:
        """
        Тест отображения прогресса 50%.

        Проверяет корректное отображение progress bar
        для импорта с 50% прогрессом.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            report_details={"total_items": 100, "processed_items": 50},
        )

        # Act
        result = self.admin.progress_display(import_session)

        # Assert
        assert "<progress" in result
        assert 'value="50.0"' in result or 'value="50"' in result
        assert "50%" in result
        assert "50/100" in result

    def test_progress_display_100_percent(self) -> None:
        """
        Тест отображения прогресса 100%.

        Проверяет отображение для полностью завершенного импорта.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            report_details={"total_items": 200, "processed_items": 200},
        )

        # Act
        result = self.admin.progress_display(import_session)

        # Assert
        assert "<progress" in result
        assert "100%" in result
        assert "200/200" in result

    def test_progress_display_zero_total(self) -> None:
        """
        Тест отображения прогресса с нулевым total_items.

        Проверяет что не происходит division by zero
        и показывается "-".
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            report_details={"total_items": 0, "processed_items": 0},
        )

        # Act
        result = self.admin.progress_display(import_session)

        # Assert
        assert result == "-"

    def test_progress_display_no_report_details(self) -> None:
        """
        Тест отображения прогресса без report_details.

        Проверяет что показывается "-" если нет данных о прогрессе.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
            report_details={},
        )

        # Act
        result = self.admin.progress_display(import_session)

        # Assert
        assert result == "-"

    def test_progress_display_completed_status(self) -> None:
        """
        Тест отображения прогресса для завершенного импорта.

        Проверяет что для статуса 'completed' не показывается
        progress bar (только для 'in_progress').
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
            report_details={"total_items": 100, "processed_items": 100},
        )

        # Act
        result = self.admin.progress_display(import_session)

        # Assert
        assert result == "-"


@pytest.mark.unit
@pytest.mark.django_db
class TestImportSessionAdminColoredStatus:
    """Unit тесты для метода colored_status"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.admin = ImportSessionAdmin(ImportSession, AdminSite())

    def test_colored_status_completed(self) -> None:
        """
        Тест отображения статуса 'completed'.

        Проверяет зеленый цвет и иконку ✅.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
        )

        # Act
        result = self.admin.colored_status(import_session)

        # Assert
        assert "green" in result
        assert "✅" in result
        assert "Завершено" in result or "completed" in result.lower()

    def test_colored_status_in_progress(self) -> None:
        """
        Тест отображения статуса 'in_progress'.

        Проверяет оранжевый цвет и иконку ⏳.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.IN_PROGRESS,
        )

        # Act
        result = self.admin.colored_status(import_session)

        # Assert
        assert "orange" in result
        assert "⏳" in result

    def test_colored_status_failed(self) -> None:
        """
        Тест отображения статуса 'failed'.

        Проверяет красный цвет и иконку ❌.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.FAILED,
        )

        # Act
        result = self.admin.colored_status(import_session)

        # Assert
        assert "red" in result
        assert "❌" in result

    def test_colored_status_started(self) -> None:
        """
        Тест отображения статуса 'started'.

        Проверяет серый цвет и иконку ⏸️.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )

        # Act
        result = self.admin.colored_status(import_session)

        # Assert
        assert "gray" in result
        assert "⏸️" in result

    def test_colored_status_html_format(self) -> None:
        """
        Тест что результат является валидным HTML.

        Проверяет наличие тега span со стилями.
        """
        # Arrange
        import_session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.COMPLETED,
        )

        # Act
        result = self.admin.colored_status(import_session)

        # Assert
        assert "<span" in result
        assert "style=" in result
        assert "color:" in result
        assert "</span>" in result
