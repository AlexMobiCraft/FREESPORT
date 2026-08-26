import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from django.conf import settings
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils import timezone

from apps.integrations.onec_exchange.file_service import FileStreamService
from apps.integrations.onec_exchange.file_type_detection import detect_file_type
from apps.products.models import ImportSession

logger = logging.getLogger("import_tasks")

IMPORT_LOCK_KEY_PREFIX = "onec:import:lock:"


def _import_lock_key(data_dir: str) -> str:
    """Ключ лока каталога обмена. Лок именно на каталог, а не на сессию."""
    return f"{IMPORT_LOCK_KEY_PREFIX}{data_dir}"


def _release_import_lock(lock_key: str, lock_token: str) -> None:
    """Снять лок каталога обмена, но только если владелец — эта задача.

    Сверка значения нужна, чтобы задача, пережившая истечение TTL, не сняла
    лок, который к тому моменту успел перезахватить сосед. Гонка «прочитали
    своё значение → TTL истёк → сосед захватил → удалили чужой лок» остаётся
    теоретически возможной, но требует импорта дольше ONEC_IMPORT_LOCK_TTL
    (по умолчанию 1800 с). При таком запасе это принимаемый риск.
    """
    try:
        if cache.get(lock_key) == lock_token:
            cache.delete(lock_key)
    except Exception as exc:  # pragma: no cover - падение Redis не должно валить импорт
        logger.warning(f"Failed to release import lock {lock_key}: {exc}")


def _mark_session_failed(session_id: int, message: str) -> None:
    """Пометить сессию как FAILED, дописав причину в отчёт."""
    try:
        session = ImportSession.objects.get(pk=session_id)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        session.status = ImportSession.ImportStatus.FAILED
        session.error_message = message
        session.report += f"[{timestamp}] {message}\n"
        session.save(update_fields=["status", "error_message", "report", "updated_at"])
    except Exception as exc:  # pragma: no cover - диагностика, не влияет на результат
        logger.critical(f"Failed to mark session {session_id} as failed: {exc}")


@shared_task(name="apps.products.tasks.process_1c_import_task", bind=True)
def process_1c_import_task(
    self: Any,
    session_id: int,
    data_dir: str | None = None,
    zip_filename: str | None = None,
    source_filename: str | None = None,
) -> str:
    """
    Задача для асинхронного запуска импорта из 1С.

    Args:
        session_id: ID сессии ImportSession
        data_dir: Путь к директории с файлами (опционально)
        zip_filename: Имя ZIP-архива для асинхронной распаковки
        source_filename: Имя файла, присланного 1С (`rests_1_16_….xml`).
            Определяет шаг импорта. Отдельный параметр, а не `zip_filename`:
            последний включает ветку распаковки архива.

    Returns:
        Результат выполнения ('success' или 'failure')
    """
    # Story 3.2: Defered Unpacking
    # Files (including ZIPs) are already moved to import_dir by the view (handle_complete).
    # We need to find them there and unpack.
    target_import_dir = Path(data_dir) if data_dir else Path(str(settings.ONEC_EXCHANGE["IMPORT_DIR"]))
    # Story 36.1: единый резолвленный путь для management-команд. Без него
    # вызов задачи без data_dir уводил импорт товаров на ONEC_DATA_DIR
    # (ручные выгрузки data/import_1c/), хотя ZIP и контрагенты в этой же
    # задаче уже читаются из приватного ONEC_EXCHANGE["IMPORT_DIR"].
    effective_data_dir = data_dir or str(target_import_dir)

    # Лок каталога обмена: 1С отдаёт сегмент каждые ~6,5 с при обработке 7-8 с,
    # а воркер prefork держит nproc процессов — без сериализации соседние задачи
    # чистят файлы друг друга. cache.add на Redis — атомарный SETNX.
    #
    # Захват и retry живут ВНЕ внешнего try/except: celery.exceptions.Retry
    # наследует Exception, и обработчик ниже пометил бы сессию FAILED.
    lock_key = _import_lock_key(effective_data_dir)
    lock_token = self.request.id or f"session-{session_id}"

    if not cache.add(lock_key, lock_token, settings.ONEC_IMPORT_LOCK_TTL):
        holder = cache.get(lock_key)
        logger.info(
            f"Import directory {effective_data_dir} is locked by {holder}; "
            f"retrying session {session_id} (attempt {self.request.retries + 1})"
        )
        # Отчёт засоряется только один раз за задачу, а не на каждой попытке.
        if self.request.retries == 0:
            try:
                ImportSession.objects.filter(pk=session_id).update(
                    report=Concat(
                        F("report"),
                        Value(
                            f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                            f"Каталог обмена занят другим импортом, задача отложена.\n"
                        ),
                    ),
                    updated_at=timezone.now(),
                )
            except Exception as exc:  # pragma: no cover - диагностика
                logger.warning(f"Failed to log lock wait for session {session_id}: {exc}")

        try:
            raise self.retry(
                countdown=settings.ONEC_IMPORT_LOCK_RETRY_COUNTDOWN,
                max_retries=settings.ONEC_IMPORT_LOCK_MAX_RETRIES,
            )
        except MaxRetriesExceededError:
            _mark_session_failed(
                session_id,
                f"Каталог обмена {effective_data_dir} оставался занят дольше допустимого "
                f"({settings.ONEC_IMPORT_LOCK_MAX_RETRIES} попыток × "
                f"{settings.ONEC_IMPORT_LOCK_RETRY_COUNTDOWN} с) — импорт не запущен.",
            )
            return "failure"

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
                session.report += f"[{timestamp}] Архив {zip_filename} успешно распакован.\n"
                session.save(update_fields=["report"])
            except Exception as e:
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = f"Ошибка распаковки архива: {e}"
                session.report += f"[{timestamp}] ОШИБКА РАСПАКОВКИ: {e}\n"
                session.save(update_fields=["status", "error_message", "report"])
                logger.error(f"Unpack failed for session {session_id}: {e}")
                return "failure"

        if target_import_dir.exists():
            zip_files = list(target_import_dir.glob("*.zip"))
            if zip_files:
                logger.info(f"Found {len(zip_files)} ZIP files in import dir. Unpacking...")
                import zipfile

                from apps.integrations.onec_exchange.routing_service import XML_ROUTING_RULES

                for zf in zip_files:
                    try:
                        # Direct unpacking to target directory
                        with zipfile.ZipFile(zf, "r") as zip_ref:
                            zip_ref.extractall(target_import_dir)
                            unpacked_files = zip_ref.namelist()

                        logger.info(f"Unpacked: {zf.name} to {target_import_dir}")

                        # Route unpacked files to subdirectories
                        routed_count = 0
                        for filename in unpacked_files:
                            file_path = target_import_dir / filename
                            if not file_path.exists() or not file_path.is_file():
                                continue

                            # Logic similar to FileRoutingService.route_file
                            name_lower = filename.lower()
                            suffix = file_path.suffix.lower()
                            target_subdir = None

                            if suffix == ".xml":
                                # Sort rules by length of prefix descending to match most specific first
                                # e.g. 'propertiesOffers' (len 16) before 'properties' (len 10)
                                sorted_rules = sorted(
                                    XML_ROUTING_RULES.items(),
                                    key=lambda x: len(x[0]),
                                    reverse=True,
                                )
                                for prefix, subdir in sorted_rules:
                                    if name_lower.startswith(prefix):
                                        target_subdir = subdir.rstrip("/")
                                        break
                            elif suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                                # Story 13.2: Handle images inside import_files folder or at root
                                if name_lower.startswith("import_files/"):
                                    # If file is already in import_files/ folder in ZIP,
                                    # target should be just 'goods' so it lands in goods/import_files/file.jpg
                                    target_subdir = "goods"
                                else:
                                    # If file is at root, put it into import_files
                                    target_subdir = "goods/import_files"

                            if target_subdir:
                                dest_dir = target_import_dir / target_subdir
                                dest_dir.mkdir(parents=True, exist_ok=True)
                                dest_path = dest_dir / filename

                                try:
                                    # Move file
                                    import shutil

                                    shutil.move(str(file_path), str(dest_path))
                                    routed_count += 1
                                except Exception as move_err:
                                    logger.warning(f"Failed to route {filename}: {move_err}")

                        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                        session.report += (
                            f"[{timestamp}] Архив {zf.name} распакован ({len(unpacked_files)} файлов). "
                            f"Распределено по папкам: {routed_count}.\n"
                        )

                        # Delete the ZIP file after unpacking
                        try:
                            zf.unlink()
                            logger.info(f"Deleted archive: {zf.name}")
                        except OSError as e:
                            logger.warning(f"Failed to delete archive {zf.name}: {e}")

                    except Exception as e:
                        logger.error(f"Failed to unpack {zf.name}: {e}")
                        session.report += f"[{timezone.now()}] Ошибка распаковки {zf.name}: {e}\n"
                        # Remove the corrupted zip file so it doesn't get retried endlessly
                        try:
                            zf.unlink()
                            logger.info(f"Deleted corrupted archive: {zf.name}")
                        except OSError as del_err:
                            logger.warning(f"Failed to delete corrupted archive {zf.name}: {del_err}")

                session.save(update_fields=["report"])

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

        # Determine file type based on the name 1C sent.
        # This prevents running unnecessary steps and allows 1C to trigger
        # granular imports (e.g. only stocks or only prices).
        detected_file_type = detect_file_type(source_filename or zip_filename)

        # Определяем тип импорта: контрагенты или товарный каталог
        contragents_dir = target_import_dir / "contragents" if target_import_dir.exists() else None
        has_contragents = bool(
            contragents_dir and contragents_dir.exists() and list(contragents_dir.glob("contragents*.xml"))
        )

        if has_contragents:
            logger.info(
                f"Starting 1C customers import for session {session_id} "
                f"(key={session.session_key}, data_dir={effective_data_dir})"
            )
            call_command("import_customers_from_1c", data_dir=effective_data_dir)
        else:
            # Запуск management команды импорта товарного каталога
            args: list[Any] = []
            options = {
                "celery_task_id": self.request.id,
                "file_type": detected_file_type,
                "import_session_id": session_id,
                "data_dir": effective_data_dir,
            }

            logger.info(
                f"Starting 1C import for session {session_id} "
                f"(key={session.session_key}, file_type={detected_file_type}, "
                f"file={source_filename or zip_filename})"
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

        # Clean up shared import directory only if no other sessions are active.
        # Multiple sessions share the same import_dir; cleaning up while another
        # session's Celery task is still running would delete its files mid-import.
        try:
            other_active = (
                ImportSession.objects.filter(
                    status=ImportSession.ImportStatus.IN_PROGRESS,
                )
                .exclude(pk=session.pk)
                .exists()
            )

            if other_active:
                logger.info("Skipping import directory cleanup — other sessions are still IN_PROGRESS.")
            elif session.session_key:
                from apps.integrations.onec_exchange.routing_service import FileRoutingService

                routing_service = FileRoutingService(str(session.session_key))
                cleaned = routing_service.cleanup_import_dir()
                logger.info(f"Post-import cleanup removed {cleaned} items from import directory.")
            else:
                logger.warning("Session key is missing, skipping cleanup.")
        except Exception as cleanup_err:
            logger.warning(f"Failed post-import cleanup: {cleanup_err}")

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

    finally:
        _release_import_lock(lock_key, lock_token)


@shared_task(name="apps.products.tasks.cleanup_stale_import_sessions")
def cleanup_stale_import_sessions() -> int:
    """
    Задача для очистки "зависших" сессий импорта.
    Находит сессии со статусом 'in_progress', которые не обновлялись более 2 часов.
    """
    stale_threshold = timezone.now() - timedelta(hours=2)

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
            session.report += f"[{timestamp}] Сессия помечена как зависшая инструментом очистки.\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])

    return count
