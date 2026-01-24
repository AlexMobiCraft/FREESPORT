import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.products.tasks import process_1c_import_task, cleanup_stale_import_sessions
from apps.products.models import ImportSession

@pytest.mark.django_db
class TestImportOrchestrationTasks:
    
    @patch('apps.products.tasks.call_command')
    def test_process_1c_import_task_success(self, mock_call_command):
        """Test successful execution of import task."""
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)
        
        # Use apply to simulate task execution with a specific task_id
        result = process_1c_import_task.apply(args=[session.id], task_id='task-123').get()
        
        assert result == "success"
        
        session.refresh_from_db()
        # The task itself sets status to IN_PROGRESS. 
        # The management command would set it to COMPLETED, but we mocked it.
        # So we expect IN_PROGRESS here, or we verify the calls.
        assert session.status == ImportSession.ImportStatus.IN_PROGRESS
        assert session.celery_task_id == 'task-123'
        assert "Задача Celery запущена" in session.report
        
        mock_call_command.assert_called_once()
        args, kwargs = mock_call_command.call_args
        assert args[0] == "import_products_from_1c"
        assert kwargs['celery_task_id'] == 'task-123'

    @patch('apps.products.tasks.call_command')
    def test_process_1c_import_task_failure(self, mock_call_command):
        """Test execution when a generic error occurs."""
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)
        
        mock_call_command.side_effect = Exception("Integration error")
        
        # Use apply to execute synchronously
        result = process_1c_import_task.apply(args=[session.id], task_id='task-err').get()
        
        assert result == "failure"
        
        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED
        assert "КРИТИЧЕСКАЯ ОШИБКА: Integration error" in session.report
        assert session.error_message == "Integration error"

    @patch('apps.products.tasks.call_command')
    def test_process_1c_import_task_command_error(self, mock_call_command):
        """Test execution when a CommandError occurs."""
        from django.core.management import CommandError
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)
        
        mock_call_command.side_effect = CommandError("Invalid arguments")
        
        result = process_1c_import_task.apply(args=[session.id], task_id='task-cmd-err').get()
        
        assert result == "failure"
        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED
        assert "ОШИБКА КОМАНДЫ: Invalid arguments" in session.report
        assert "Invalid arguments" in session.error_message

    @patch('apps.products.tasks.call_command')
    def test_process_1c_import_task_timeout(self, mock_call_command):
        """Test execution when a time limit is exceeded."""
        from celery.exceptions import SoftTimeLimitExceeded
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)
        
        mock_call_command.side_effect = SoftTimeLimitExceeded()
        
        result = process_1c_import_task.apply(args=[session.id], task_id='task-timeout').get()
        
        assert result == "failure"
        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED
        assert "ПРЕВЫШЕН ЛИМИТ ВРЕМЕНИ" in session.report
        assert "Time limit exceeded" in session.error_message

    def test_cleanup_stale_import_sessions(self):
        """Test cleanup of sessions older than 2 hours."""
        now = timezone.now()
        
        # Stale session (updated 3 hours ago)
        stale_session = ImportSession.objects.create(
            status=ImportSession.ImportStatus.IN_PROGRESS
        )
        ImportSession.objects.filter(pk=stale_session.pk).update(updated_at=now - timedelta(hours=3))
        
        # Fresh session (updated 1 hour ago)
        fresh_session = ImportSession.objects.create(
            status=ImportSession.ImportStatus.IN_PROGRESS
        )
        ImportSession.objects.filter(pk=fresh_session.pk).update(updated_at=now - timedelta(hours=1))
        
        # Completed session (should be ignored)
        completed_session = ImportSession.objects.create(
            status=ImportSession.ImportStatus.COMPLETED
        )
        ImportSession.objects.filter(pk=completed_session.pk).update(updated_at=now - timedelta(hours=3))

        count = cleanup_stale_import_sessions()
        
        assert count == 1
        
        stale_session.refresh_from_db()
        assert stale_session.status == ImportSession.ImportStatus.FAILED
        assert "Зависла/Таймаут" in stale_session.error_message
        
        fresh_session.refresh_from_db()
        assert fresh_session.status == ImportSession.ImportStatus.IN_PROGRESS
        
        completed_session.refresh_from_db()
        assert completed_session.status == ImportSession.ImportStatus.COMPLETED
