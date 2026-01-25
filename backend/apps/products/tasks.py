import logging
from pathlib import Path
from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.integrations.onec_exchange.file_service import FileStreamService
from apps.products.models import ImportSession

logger = logging.getLogger("import_tasks")


@shared_task(name="apps.products.tasks.process_1c_import_task", bind=True)
def process_1c_import_task(
    self, session_id: int, data_dir: str = None, zip_filename: str = None
) -> str:
    """
    Задача для асинхронного запуска импорта из 1С.

    Args:
        session_id: ID сессии ImportSession
        data_dir: Путь к директории с файлами (опционально)
        zip_filename: Имя ZIP-архива для асинхронной распаковки

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

        # Story 3.1: Асинхронная распаковка архива (если передан)
        if zip_filename and zip_filename.lower().endswith(".zip") and data_dir:
            try:
                # Extract sessid from data_dir path (data_dir = .../1c_import/<sessid>)
                sessid = Path(data_dir).name
                file_service = FileStreamService(sessid)
                import_dir_path = Path(data_dir)

                file_service.unpack_zip(zip_filename, import_dir_path)

                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.report += (
                    f"[{timestamp}] Архив {zip_filename} успешно распакован.\n"
                )
                session.save(update_fields=["report"])
            except Exception as e:
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = f"Ошибка распаковки архива: {e}"
                session.report += f"[{timestamp}] ОШИБКА РАСПАКОВКИ: {e}\n"
                session.save(update_fields=["status", "error_message", "report"])
                logger.error(f"Unpack failed for session {session_id}: {e}")
                return "failure"

        # Story 3.2: Defensive directory creation
        # Ensure import directory and all required subdirectories exist 
        # to satisfy management command validation.
        if data_dir:
            import_path = Path(data_dir)
            if not import_path.exists():
                logger.warning(f"Import directory {data_dir} missing. Creating it.")
                import_path.mkdir(parents=True, exist_ok=True)
            
            # Create required subdirectories if they don't exist
            # This prevents "Missing mandatory subdirectory" errors in 'all' mode
            required_subdirs = ["goods", "offers", "prices", "rests", "priceLists"]
            for subdir in required_subdirs:
                subdir_path = import_path / subdir
                if not subdir_path.exists():
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created missing subdirectory: {subdir}")
            
            # Debug: Log directory structure
            try:
                files = list(import_path.rglob("*"))
                logger.info(f"Import directory ready: {data_dir} ({len(files)} items found)")
            except Exception as e:
                logger.warning(f"Failed to list directory contents: {e}")

        # Запуск management команды
        args = []
        options = {
            "celery_task_id": self.request.id,
        }
        if data_dir:
            options["data_dir"] = data_dir

        logger.info(
            f"Starting 1C import for session {session_id} "
            f"(key={session.session_key})"
        )
        call_command("import_products_from_1c", *args, **options)

        # Финализация сессии (если команда сама не завершила её)
        session.refresh_from_db()
        if session.status != ImportSession.ImportStatus.COMPLETED:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.status = ImportSession.ImportStatus.COMPLETED
            session.finished_at = timezone.now()
            session.report += f"[{timestamp}] Импорт успешно завершен.\n"
            session.save(update_fields=["status", "finished_at", "report", "updated_at"])

        return "success"

    except ImportSession.DoesNotExist:
        logger.error(f"ImportSession {session_id} not found")
        return "failure"
    except Exception as e:
        logger.error(f"Error in process_1c_import_task: {e}")
        try:
            session = ImportSession.objects.get(pk=session_id)
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(e, CommandError):
                error_prefix = "ОШИБКА КОМАНДЫ"
                status = ImportSession.ImportStatus.FAILED
                msg = str(e)
            elif isinstance(e, SoftTimeLimitExceeded):
                error_prefix = "ПРЕВЫШЕН ЛИМИТ ВРЕМЕНИ"
                status = ImportSession.ImportStatus.FAILED
                msg = "Time limit exceeded"
            else:
                error_prefix = "КРИТИЧЕСКАЯ ОШИБКА"
                status = ImportSession.ImportStatus.FAILED
                msg = str(e)

            # Update session if not already handled by command
            if session.status != ImportSession.ImportStatus.FAILED:
                session.status = status
                session.error_message = msg
            
            session.report += f"[{timestamp}] {error_prefix}: {msg}\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])
        except Exception as db_err:
            logger.critical(f"Failed to update session status after error: {db_err}")

        return "failure"


@shared_task(name="apps.products.tasks.cleanup_stale_import_sessions")
def cleanup_stale_import_sessions() -> int:
    """
    Задача для очистки "зависших" сессий импорта.
    Находит сессии со статусом 'in_progress', которые не обновлялись более 2 часов.
    """
    stale_threshold = timezone.now() - timezone.timedelta(hours=2)

    stale_sessions = ImportSession.objects.filter(
        status=ImportSession.ImportStatus.IN_PROGRESS, updated_at__lt=stale_threshold
    )

    count = stale_sessions.count()
    if count > 0:
        logger.info(f"Cleaning up {count} stale import sessions")
        for session in stale_sessions:
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = "Зависла/Таймаут (не обновлялась более 2 часов)"
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += (
                f"[{timestamp}] Сессия помечена как зависшая инструментом очистки.\n"
            )
            session.save(update_fields=["status", "error_message", "report", "updated_at"])

    return count
