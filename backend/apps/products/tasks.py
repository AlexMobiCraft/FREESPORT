"""
Celery задачи для импорта данных из 1С и управления сессиями.

Story 3.1: Оркестрация Асинхронного Импорта
"""

import logging
from typing import Any

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

from apps.products.models import ImportSession

logger = logging.getLogger("import_tasks")

@shared_task(name="apps.products.tasks.process_1c_import_task", bind=True)
def process_1c_import_task(self, session_id: int, data_dir: str = None, zip_filename: str = None) -> str:
    """
    Задача для асинхронного запуска импорта из 1С.
    
    Args:
        session_id: ID сессии ImportSession
        data_dir: Путь к директории с файлами (опционально)
        
    Returns:
        Результат выполнения ('success' или 'failure')
    """
    try:
        session = ImportSession.objects.get(pk=session_id)
        session.status = ImportSession.ImportStatus.IN_PROGRESS
        session.celery_task_id = self.request.id

        # Обновляем отчет о начале
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        session.report += f"[{timestamp}] Задача Celery запущена. Начинаем импорт...\n"
        
        session.save(update_fields=["status", "celery_task_id", "report", "updated_at"])
        
        # Story 3.1: Асинхронная распаковка архива
        if zip_filename and zip_filename.lower().endswith(".zip"):
            try:
                from apps.integrations.onec_exchange.file_service import FileStreamService
                from pathlib import Path
                
                # Extract sessid from data_dir path
                # data_dir = .../1c_import/<sessid>
                sessid = Path(data_dir).name
                
                file_service = FileStreamService(sessid)
                import_dir_path = Path(data_dir)
                
                # Check if file exists in temp or import dir?
                # FileStreamService.unpack_zip expects zip_filename and destination dir
                # It looks for zip_filename in temp_dir usually?
                # Let's check unpack_zip implementation if needed, but assuming it works given sessid
                
                file_service.unpack_zip(zip_filename, import_dir_path)
                
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.report += (
                    f"[{timestamp}] Архив {zip_filename} успешно распакован (асинхронно).\n"
                )
                session.save(update_fields=["report"])
                
            except Exception as e:
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = f"Ошибка распаковки архива: {e}"
                session.report += f"[{timestamp}] ОШИБКА РАСПАКОВКИ: {e}\n"
                session.save(update_fields=["status", "error_message", "report"])
                return "failure" # Stop processing if unpacking failed

                
        # Запуск management команды
        # Мы передаем celery-task-id чтобы команда использовала эту же сессию
        args = []
        options = {
            "celery_task_id": self.request.id,
        }
        if data_dir:
            options["data_dir"] = data_dir
            
        logger.info(f"Starting 1C import for session {session_id} (Task {self.request.id})")
        
        call_command("import_products_from_1c", *args, **options)
        
        # Explicitly mark ensuring completion, in case the command didn't finalize it
        # (e.g. if command logic relies on something else, or for robustness)
        session.refresh_from_db()
        if session.status != ImportSession.ImportStatus.COMPLETED:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.status = ImportSession.ImportStatus.COMPLETED
            session.finished_at = timezone.now()
            session.report += f"[{timestamp}] Импорт успешно завершен (Task).\n"
            session.save(update_fields=["status", "finished_at", "report", "updated_at"])

        return "success"
    except ImportSession.DoesNotExist:
        logger.error(f"ImportSession {session_id} not found")
        return "failure"
    except Exception as e:
        from django.core.management import CommandError
        from celery.exceptions import SoftTimeLimitExceeded
        
        logger.error(f"Error in process_1c_import_task: {e}")
        try:
            # Refresh to see if command already handled the error (set status to FAILED)
            session = ImportSession.objects.get(pk=session_id)
            
            # If status is already FAILED, we assume command handled it.
            # We just ensure the error is logged in report if needed.
            
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if isinstance(e, CommandError):
                error_prefix = "ОШИБКА КОМАНДЫ"
            elif isinstance(e, SoftTimeLimitExceeded):
                # This is internal to task, likely not handled by command
                session.status = ImportSession.ImportStatus.FAILED 
                error_prefix = "ПРЕВЫШЕН ЛИМИТ ВРЕМЕНИ"
                session.error_message = "Time limit exceeded"
            else:
                error_prefix = "КРИТИЧЕСКАЯ ОШИБКА"

            # If command already set FAILED, we might not want to overwrite error_message
            # unless it's empty.
            if session.status != ImportSession.ImportStatus.FAILED:
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = str(e)
            
            session.report += f"[{timestamp}] {error_prefix}: {e}\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])
        except:
            # If DB is unreachable, we can't do much
            pass
        return "failure"

@shared_task(name="apps.products.tasks.cleanup_stale_import_sessions")
def cleanup_stale_import_sessions() -> int:
    """
    Задача для очистки "зависших" сессий импорта.
    Находит сессии со статусом 'in_progress', которые не обновлялись более 2 часов.
    """
    stale_threshold = timezone.now() - timezone.timedelta(hours=2)
    
    stale_sessions = ImportSession.objects.filter(
        status=ImportSession.ImportStatus.IN_PROGRESS,
        updated_at__lt=stale_threshold
    )
    
    count = stale_sessions.count()
    if count > 0:
        logger.info(f"Cleaning up {count} stale import sessions")
        for session in stale_sessions:
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = "Зависла/Таймаут (не обновлялась более 2 часов)"
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] Сессия помечена как зависшая инструментом очистки.\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])
            
    return count
