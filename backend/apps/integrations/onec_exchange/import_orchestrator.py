"""
Import Orchestrator Service for 1C Exchange.

Extracts complex import logic from ICExchangeView.handle_import
into a dedicated service following the "Fat Services, Thin Views" pattern.

Story 4.3 Review Follow-up: [AI-Review][MEDIUM] Fat View refactoring.
"""

import logging
import shutil
import zipfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from .file_service import FileStreamService
from .routing_service import FileRoutingService, XML_ROUTING_RULES

logger = logging.getLogger(__name__)


class ImportOrchestratorService:
    """
    Orchestrates the full import cycle triggered by mode=import.

    Responsibilities:
    - Expire stale import sessions
    - Find or create an ImportSession
    - Transfer files from temp to import directory
    - Unpack ZIP archives with Zip Slip protection and route contents
    - Execute synchronous import via management command
    - Mark exchange cycle as complete
    """

    def __init__(self, sessid: str, filename: str = "unknown"):
        self.sessid = sessid
        self.filename = filename
        self.import_dir = Path(settings.MEDIA_ROOT) / "1c_import"

    def execute(self) -> tuple[bool, str]:
        """
        Run the full import orchestration.

        Returns:
            Tuple of (success: bool, message: str).
        """
        from apps.products.models import ImportSession

        session = self._resolve_session(ImportSession)
        if session is None:
            return False, "Missing sessid"

        # If session is IN_PROGRESS, do NOT touch import_dir — another import is running
        if session.status == ImportSession.ImportStatus.IN_PROGRESS:
            logger.info(
                f"[IMPORT] Session {session.pk} is IN_PROGRESS, "
                "returning success without modifying import_dir"
            )
            return True, "already_in_progress"

        # Transfer files
        ok, msg = self._transfer_files(session)
        if not ok:
            return False, msg

        # Unpack ZIPs
        self._unpack_zips(session)

        # Run import
        ok, msg = self._run_import(session, ImportSession)
        if not ok:
            return False, msg

        return True, "success"

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _resolve_session(self, ImportSession):
        """Expire stale sessions and find or create an active one."""
        if not self.sessid:
            logger.warning("[IMPORT] Request rejected: No identifier found.")
            return None

        logger.info(
            f"[IMPORT] Received mode=import for sessid={self.sessid}, "
            f"filename={self.filename}"
        )

        with transaction.atomic():
            # Lazy Expiration: Mark sessions older than 2 hours as FAILED
            stale_threshold = timezone.now() - timedelta(hours=2)
            ImportSession.objects.filter(
                session_key=self.sessid,
                status__in=[
                    ImportSession.ImportStatus.PENDING,
                    ImportSession.ImportStatus.STARTED,
                    ImportSession.ImportStatus.IN_PROGRESS,
                ],
                updated_at__lt=stale_threshold,
            ).update(
                status=ImportSession.ImportStatus.FAILED,
                error_message="Session expired (stale for > 2 hours)",
                finished_at=timezone.now(),
            )

            active_session = (
                ImportSession.objects.select_for_update()
                .filter(
                    session_key=self.sessid,
                    status__in=[
                        ImportSession.ImportStatus.PENDING,
                        ImportSession.ImportStatus.STARTED,
                        ImportSession.ImportStatus.IN_PROGRESS,
                    ],
                )
                .first()
            )

            if active_session:
                if active_session.status == ImportSession.ImportStatus.IN_PROGRESS:
                    logger.info(
                        f"[IMPORT] Session {active_session.pk} is IN_PROGRESS, "
                        "skipping duplicate"
                    )
                    active_session.report += (
                        f"[{timezone.now()}] mode=import для {self.filename} "
                        "- сессия уже обрабатывается\n"
                    )
                    active_session.save(update_fields=["report", "updated_at"])
                    # Return a sentinel to indicate "already running" — caller treats as success
                    return active_session

                session = active_session
                logger.info(f"[IMPORT] Using existing PENDING session {session.pk}")
                session.report += (
                    f"[{timezone.now()}] Получен mode=import для {self.filename}, "
                    "запускаем импорт\n"
                )
                session.save(update_fields=["report", "updated_at"])
            else:
                session = ImportSession.objects.create(
                    session_key=self.sessid,
                    status=ImportSession.ImportStatus.PENDING,
                    import_type=ImportSession.ImportType.CATALOG,
                    report=(
                        f"[{timezone.now()}] Сессия создана по mode=import. "
                        f"Файл: {self.filename}\n"
                    ),
                )
                logger.info(f"[IMPORT] Created NEW session id={session.pk}")

        return session

    def _transfer_files(self, session) -> tuple[bool, str]:
        """Transfer files from temp to import directory."""
        try:
            file_service = FileStreamService(self.sessid)
            routing_service = FileRoutingService(self.sessid)
            files = file_service.list_files()
            logger.info(f"[IMPORT] Files in temp: {files}")

            transferred_count = 0
            for f in files:
                try:
                    routing_service.move_to_import(f)
                    transferred_count += 1
                except Exception as move_err:
                    logger.error(f"[IMPORT] Failed to move {f}: {move_err}")

            logger.info(
                f"[IMPORT] Transferred {transferred_count}/{len(files)} files"
            )
            session.report += (
                f"[{timezone.now()}] Перенесено файлов: "
                f"{transferred_count}/{len(files)}\n"
            )
            session.save(update_fields=["report"])
            return True, ""

        except Exception as e:
            logger.error(f"[IMPORT] File transfer failed: {e}", exc_info=True)
            session.report += f"[{timezone.now()}] ОШИБКА переноса: {e}\n"
            session.save(update_fields=["report"])
            return False, "File transfer error"

    def _unpack_zips(self, session) -> None:
        """Unpack ZIP files with Zip Slip protection and route contents."""
        try:
            zip_files = list(self.import_dir.glob("*.zip"))
            if not zip_files:
                return

            logger.info(f"[IMPORT] Found {len(zip_files)} ZIP files to unpack")

            for zf in zip_files:
                try:
                    with zipfile.ZipFile(zf, "r") as zip_ref:
                        unpacked_files = zip_ref.namelist()
                        # Zip Slip protection
                        for member in unpacked_files:
                            member_path = (self.import_dir / member).resolve()
                            if not str(member_path).startswith(
                                str(self.import_dir.resolve())
                            ):
                                raise ValueError(
                                    f"Zip Slip detected: {member} resolves "
                                    "outside import dir"
                                )
                        zip_ref.extractall(self.import_dir)

                    logger.info(
                        f"[IMPORT] Unpacked: {zf.name} "
                        f"({len(unpacked_files)} files)"
                    )

                    routed_count = self._route_unpacked_files(unpacked_files)

                    session.report += (
                        f"[{timezone.now()}] Архив {zf.name}: "
                        f"{len(unpacked_files)} файлов, распределено: "
                        f"{routed_count}\n"
                    )

                    try:
                        zf.unlink()
                    except OSError:
                        pass

                except Exception as unzip_err:
                    logger.error(
                        f"[IMPORT] Failed to unpack {zf.name}: {unzip_err}"
                    )
                    session.report += (
                        f"[{timezone.now()}] Ошибка распаковки {zf.name}: "
                        f"{unzip_err}\n"
                    )

            session.save(update_fields=["report"])

        except Exception as e:
            logger.error(
                f"[IMPORT] ZIP processing failed: {e}", exc_info=True
            )
            session.report += (
                f"[{timezone.now()}] Ошибка обработки архивов: {e}\n"
            )
            session.save(update_fields=["report"])

    def _route_unpacked_files(self, unpacked_files: list[str]) -> int:
        """Route unpacked files to subdirectories based on naming rules."""
        routed_count = 0
        for unpacked_name in unpacked_files:
            file_path = self.import_dir / unpacked_name
            if not file_path.exists() or not file_path.is_file():
                continue

            name_lower = unpacked_name.lower()
            suffix = file_path.suffix.lower()
            target_subdir = None

            if suffix == ".xml":
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
                if name_lower.startswith("import_files/"):
                    target_subdir = "goods"
                else:
                    target_subdir = "goods/import_files"

            if target_subdir:
                dest_dir = self.import_dir / target_subdir
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / unpacked_name
                try:
                    shutil.move(str(file_path), str(dest_path))
                    routed_count += 1
                except Exception as move_err:
                    logger.warning(
                        f"[IMPORT] Failed to route {unpacked_name}: {move_err}"
                    )

        return routed_count

    def _run_import(self, session, ImportSession) -> tuple[bool, str]:
        """Execute synchronous import and finalize session."""
        # Check if session is already IN_PROGRESS (duplicate request)
        if session.status == ImportSession.ImportStatus.IN_PROGRESS:
            return True, "success"

        dry_run = (self.import_dir / ".dry_run").exists()

        try:
            if dry_run:
                logger.info("[IMPORT] DRY RUN mode - skipping import")
                session.report += (
                    f"[{timezone.now()}] DRY RUN: импорт пропущен\n"
                )
                session.status = ImportSession.ImportStatus.COMPLETED
                session.finished_at = timezone.now()
                session.save(
                    update_fields=["report", "status", "finished_at"]
                )
            else:
                logger.info(
                    f"[IMPORT] Starting SYNCHRONOUS import for "
                    f"session_id={session.pk}"
                )
                session.status = ImportSession.ImportStatus.IN_PROGRESS
                session.report += (
                    f"[{timezone.now()}] Начало синхронного импорта...\n"
                )
                session.save(
                    update_fields=["status", "report", "updated_at"]
                )

                file_type = self._detect_file_type()

                logger.info(
                    f"[IMPORT] Detected file_type={file_type} "
                    f"from filename={self.filename}"
                )

                call_command(
                    "import_products_from_1c",
                    data_dir=str(self.import_dir),
                    file_type=file_type,
                    import_session_id=session.pk,
                )

                session.refresh_from_db()
                if session.status != ImportSession.ImportStatus.COMPLETED:
                    session.status = ImportSession.ImportStatus.COMPLETED
                    session.finished_at = timezone.now()
                session.report += (
                    f"[{timezone.now()}] Импорт завершен успешно.\n"
                )
                session.save(
                    update_fields=[
                        "status", "report", "finished_at", "updated_at"
                    ]
                )

                logger.info(
                    f"[IMPORT] Import completed successfully for "
                    f"session_id={session.pk}"
                )

            # Mark exchange cycle complete
            file_service = FileStreamService(self.sessid)
            file_service.mark_complete()

        except Exception as e:
            logger.error(f"[IMPORT] Import failed: {e}", exc_info=True)
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = str(e)
            session.report += f"[{timezone.now()}] ОШИБКА импорта: {e}\n"
            session.save(
                update_fields=["status", "error_message", "report"]
            )
            return False, str(e)

        return True, "success"

    def _detect_file_type(self) -> str:
        """Determine import file type from filename."""
        fn_lower = self.filename.lower() if self.filename else ""
        if fn_lower.startswith("goods") or fn_lower.startswith("import"):
            return "goods"
        elif fn_lower.startswith("offers"):
            return "offers"
        elif fn_lower.startswith("prices") or fn_lower.startswith("pricelists"):
            return "prices"
        elif fn_lower.startswith("rests"):
            return "rests"
        return "all"

    def finalize_batch(self, dry_run: bool = False) -> tuple[bool, str]:
        """
        Finalize a complete exchange batch (mode=complete).
        
        Orchestrates the full completion cycle triggered when 1C signals
        that all files have been uploaded:
        - Check if cycle already completed (duplicate signal)
        - Create/find ImportSession (in transaction)
        - Transfer files from temp to import directory (outside transaction)
        - In async mode: dispatch Celery task
        - In dry_run mode: just unpack ZIPs
        - Mark exchange cycle as complete
        
        Returns:
            Tuple of (success: bool, message: str).
            message is "already_complete" when cycle was already done.
            
        Note:
            IO operations (file transfer, unpack) are performed OUTSIDE the
            transaction to avoid blocking the ImportSession table during
            potentially long disk operations.
        """
        from apps.products.models import ImportSession

        # Check if already complete (duplicate signal from 1C)
        try:
            file_service = FileStreamService(self.sessid)
            if file_service.is_complete():
                logger.info(
                    f"[COMPLETE] Cycle already completed for {self.sessid}. "
                    "Ignoring duplicate complete signal."
                )
                return True, "already_complete"
        except Exception as e:
            logger.warning(f"[COMPLETE] Error checking completion status: {e}")

        # Step 1: Resolve session in a SHORT transaction (DB lock released quickly)
        with transaction.atomic():
            session = self._resolve_complete_session(ImportSession)

        # Step 2: IO operations OUTSIDE transaction (no DB lock held)
        # Transfer files from temp to import directory
        self._transfer_files_complete(session)

        # Check for file-flag .dry_run
        if not dry_run and (self.import_dir / ".dry_run").exists():
            dry_run = True
            logger.info("[COMPLETE] Detected .dry_run flag file")

        # Step 3: Dispatch import or dry-run unpack (also outside transaction)
        self._dispatch_or_dryrun(session, dry_run)

        return True, "success"

    def _resolve_complete_session(self, ImportSession):
        """Find or create ImportSession for mode=complete."""
        session = ImportSession.objects.select_for_update().filter(
            session_key=self.sessid,
            status=ImportSession.ImportStatus.PENDING
        ).first()

        if not session:
            logger.warning(
                f"[COMPLETE] No PENDING session found for {self.sessid}. "
                "Creating NEW session."
            )
            session = ImportSession.objects.create(
                session_key=self.sessid,
                status=ImportSession.ImportStatus.PENDING,
                import_type=ImportSession.ImportType.CATALOG,
                report=(
                    f"[{timezone.now()}] Сессия создана по сигналу complete "
                    "(Fix check skipped?).\n"
                ),
            )
            logger.info(
                f"[COMPLETE] Created NEW session id={session.pk} "
                f"for sessid={self.sessid}"
            )
        else:
            session.report += f"[{timezone.now()}] Получен сигнал complete.\n"
            session.save(update_fields=["report"])
            logger.info(
                f"[COMPLETE] Found EXISTING session id={session.pk}, "
                f"status={session.status}"
            )

        return session

    def _transfer_files_complete(self, session) -> None:
        """Transfer accumulated files from temp to import_dir for mode=complete."""
        try:
            file_service = FileStreamService(self.sessid)
            routing_service = FileRoutingService(self.sessid)
            files = file_service.list_files()
            logger.info(f"[COMPLETE] Files in temp before transfer: {files}")

            transferred_count = 0
            for f in files:
                try:
                    routing_service.move_to_import(f)
                    transferred_count += 1
                    logger.debug(f"[COMPLETE] Transferred: {f}")
                except Exception as move_err:
                    logger.error(
                        f"[COMPLETE] Failed to move file {f}: {move_err}"
                    )

            logger.info(
                f"[COMPLETE] Transferred {transferred_count}/{len(files)} "
                f"files to {self.import_dir}"
            )
            session.report += (
                f"[{timezone.now()}] Перенесено файлов: "
                f"{transferred_count}/{len(files)}\n"
            )
            session.save(update_fields=["report"])

        except Exception as e:
            logger.error(
                f"[COMPLETE] Failed to transfer files: {e}", exc_info=True
            )
            session.report += (
                f"[{timezone.now()}] ОШИБКА переноса файлов: {e}\n"
            )
            session.save(update_fields=["report"])

    def _dispatch_or_dryrun(self, session, dry_run: bool) -> None:
        """Dispatch Celery task or run dry-run unpack for mode=complete."""
        from apps.products.tasks import process_1c_import_task

        try:
            file_service = FileStreamService(self.sessid)

            if dry_run:
                zip_files = [
                    f for f in file_service.list_files()
                    if f.lower().endswith(".zip")
                ]
                logger.info(
                    f"[COMPLETE] DRY RUN mode, unpacking {len(zip_files)} ZIPs"
                )
                for zf in zip_files:
                    file_service.unpack_zip(zf, self.import_dir)
                    session.report += (
                        f"[{timezone.now()}] DRY RUN: Архив {zf} распакован.\n"
                    )
                session.report += (
                    f"[{timezone.now()}] DRY RUN: Импорт пропущен.\n"
                )
                session.save(update_fields=["report"])
            else:
                logger.info(
                    f"[COMPLETE] Dispatching Celery task for "
                    f"session_id={session.pk}, import_dir={self.import_dir}"
                )
                task_result = process_1c_import_task.delay(
                    session.pk, str(self.import_dir)
                )
                logger.info(
                    f"[COMPLETE] Celery task dispatched: task_id={task_result.id}"
                )
                session.report += (
                    f"[{timezone.now()}] Celery task запущен: {task_result.id}\n"
                )
                session.save(update_fields=["report"])

            # Mark exchange cycle complete for next init
            file_service.mark_complete()
            logger.info(
                f"[COMPLETE] Exchange cycle marked as complete for {self.sessid}"
            )

        except Exception as e:
            logger.error(f"[COMPLETE] Protocol error: {e}", exc_info=True)
            session.report += f"[{timezone.now()}] ОШИБКА: {e}\n"
            session.save(update_fields=["report"])
