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
def process_1c_import_task(self, session_id: int, data_dir: str = None) -> str:
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
        session.save(update_fields=["status", "celery_task_id", "updated_at"])
        
        # Запуск management команды
        # Мы передаем celery-task-id чтобы команда использовала эту же сессию
        args = []
        options = {
            "celery_task_id": self.request.id,
        }
        if data_dir:
            options["data_dir"] = data_dir
            
        logger.info(f"Starting 1C import for session {session_id} (Task {self.request.id})")
        
        # Обновляем отчет о начале
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        session.report += f"[{timestamp}] Задача Celery запущена. Начинаем импорт...\n"
        session.save(update_fields=["report", "updated_at"])
        
        call_command("import_products_from_1c", *args, **options)
        
        return "success"
    except ImportSession.DoesNotExist:
        logger.error(f"ImportSession {session_id} not found")
        return "failure"
    except Exception as e:
        from django.core.management import CommandError
        from celery.exceptions import SoftTimeLimitExceeded
        
        logger.error(f"Error in process_1c_import_task: {e}")
        try:
            session = ImportSession.objects.get(pk=session_id)
            session.status = ImportSession.ImportStatus.FAILED
            
            if isinstance(e, CommandError):
                session.error_message = str(e)
                error_prefix = "ОШИБКА КОМАНДЫ"
            elif isinstance(e, SoftTimeLimitExceeded):
                session.error_message = "Time limit exceeded"
                error_prefix = "ПРЕВЫШЕН ЛИМИТ ВРЕМЕНИ"
            else:
                session.error_message = str(e)
                error_prefix = "КРИТИЧЕСКАЯ ОШИБКА"

            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] {error_prefix}: {e}\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])
        except:
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
