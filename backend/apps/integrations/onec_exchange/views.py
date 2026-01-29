import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_backends, login
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView

from .authentication import Basic1CAuthentication, CsrfExemptSessionAuthentication
from .file_service import FileLockError, FileStreamService
from .permissions import Is1CExchangeUser
from .renderers import PlainTextRenderer
from .routing_service import FileRoutingService

logger = logging.getLogger(__name__)


class ICExchangeView(APIView):
    def _get_exchange_identity(self, request):
        """
        Always use a stable folder for the 1C robot to allow file accumulation.
        """
        if request.user.is_authenticated:
            return "shared_1c_exchange"
        
        sessid = request.query_params.get("sessid")
        if not sessid:
            sessid = request.session.session_key
        return sessid
    """
    Main entry point for 1C exchange protocol.
    Handles authentication, file uploads, and import triggering.

    Protocol Flow:
    1. GET /?mode=checkauth -> establishment of session (Basic Auth)
    2. GET /?mode=init -> capability negotiation (Session Cookie)
    3. POST /?mode=file&filename=... -> chunked file upload (Session Cookie)
    4. GET /?mode=import&filename=... -> trigger import task (Session Cookie)

    Official Documentation:
    https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php
    """

    authentication_classes = [Basic1CAuthentication, CsrfExemptSessionAuthentication]
    permission_classes = [Is1CExchangeUser]
    renderer_classes = [PlainTextRenderer]

    def get(self, request, *args, **kwargs):
        mode = request.query_params.get("mode")

        if mode == "checkauth":
            return self.handle_checkauth(request)
        elif mode == "init":
            return self.handle_init(request)
        elif mode == "import":
            return self.handle_import(request)
        elif mode == "query":
            return self.handle_query(request)
        elif mode == "complete":
            return self.handle_complete(request)
        elif mode == "deactivate":
            return self.handle_complete(request)

        return HttpResponse(
            "failure\nUnknown mode", content_type="text/plain; charset=utf-8", status=400
        )

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests.
        Some 1C configurations send checkauth or init via POST.
        Also handles file uploads (mode=file).
        """
        mode = request.query_params.get("mode")

        if mode == "checkauth":
            return self.handle_checkauth(request)
        elif mode == "init":
            return self.handle_init(request)
        elif mode == "file":
            return self.handle_file_upload(request)
        elif mode == "import":
            return self.handle_import(request)
        elif mode == "complete":
            return self.handle_complete(request)
        elif mode == "deactivate":
            # mode=deactivate is just a notification that 1C finished exchange
            # No need to create a session or process anything
            logger.info("[DEACTIVATE] Exchange completed notification from 1C")
            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        return HttpResponse(
            "failure\nUnknown mode (POST)", content_type="text/plain; charset=utf-8", status=400
        )

    def handle_import(self, request):
        """
        Handle the import command from 1C.
        
        IMPORTANT: In incremental mode ("Выгружать только измененные объекты"),
        1C does NOT send mode=complete. It expects mode=import to trigger 
        the actual import processing.
        """
        from datetime import timedelta
        from django.db import transaction
        from apps.products.models import ImportSession

        sessid = self._get_exchange_identity(request)
        filename = request.query_params.get("filename", "unknown")
        
        if not sessid:
            logger.warning("[IMPORT] Request rejected: No identifier found.")
            return HttpResponse("failure\nMissing sessid", status=403)
            
        logger.info(f"[IMPORT] Received mode=import for sessid={sessid}, filename={filename}")

        import_dir = Path(settings.MEDIA_ROOT) / "1c_import"
        dry_run = (import_dir / ".dry_run").exists()

        with transaction.atomic():
            # Lazy Expiration: Mark sessions older than 2 hours as FAILED
            stale_threshold = timezone.now() - timedelta(hours=2)
            ImportSession.objects.filter(
                session_key=sessid,
                status__in=[
                    ImportSession.ImportStatus.PENDING,
                    ImportSession.ImportStatus.STARTED,
                    ImportSession.ImportStatus.IN_PROGRESS,
                ],
                updated_at__lt=stale_threshold
            ).update(
                status=ImportSession.ImportStatus.FAILED,
                error_message="Session expired (stale for > 2 hours)",
                finished_at=timezone.now()
            )

            # Check for active session
            active_session = ImportSession.objects.select_for_update().filter(
                session_key=sessid,
                status__in=[
                    ImportSession.ImportStatus.PENDING,
                    ImportSession.ImportStatus.STARTED,
                    ImportSession.ImportStatus.IN_PROGRESS,
                ]
            ).first()

            if active_session:
                # Only skip if session is already being processed (IN_PROGRESS)
                if active_session.status == ImportSession.ImportStatus.IN_PROGRESS:
                    logger.info(f"[IMPORT] Session {active_session.pk} is IN_PROGRESS, skipping duplicate")
                    active_session.report += f"[{timezone.now()}] mode=import для {filename} - сессия уже обрабатывается\n"
                    active_session.save(update_fields=['report', 'updated_at'])
                    return HttpResponse("success", content_type="text/plain; charset=utf-8")
                
                # For PENDING/STARTED sessions - use them and trigger import
                session = active_session
                logger.info(f"[IMPORT] Using existing PENDING session {session.pk}")
                session.report += f"[{timezone.now()}] Получен mode=import для {filename}, запускаем импорт\n"
                session.save(update_fields=['report', 'updated_at'])
            else:
                # Create new session
                session = ImportSession.objects.create(
                    session_key=sessid,
                    status=ImportSession.ImportStatus.PENDING,
                    import_type=ImportSession.ImportType.CATALOG,
                    report=f"[{timezone.now()}] Сессия создана по mode=import. Файл: {filename}\n"
                )
                logger.info(f"[IMPORT] Created NEW session id={session.pk}")

        # Transfer files from temp to import_dir
        try:
            file_service = FileStreamService(sessid)
            routing_service = FileRoutingService(sessid)
            files = file_service.list_files()
            logger.info(f"[IMPORT] Files in temp: {files}")
            
            transferred_count = 0
            for f in files:
                try:
                    routing_service.move_to_import(f)
                    transferred_count += 1
                except Exception as move_err:
                    logger.error(f"[IMPORT] Failed to move {f}: {move_err}")
            
            logger.info(f"[IMPORT] Transferred {transferred_count}/{len(files)} files")
            session.report += f"[{timezone.now()}] Перенесено файлов: {transferred_count}/{len(files)}\n"
            session.save(update_fields=['report'])
            
        except Exception as e:
            logger.error(f"[IMPORT] File transfer failed: {e}", exc_info=True)
            session.report += f"[{timezone.now()}] ОШИБКА переноса: {e}\n"
            session.save(update_fields=['report'])
            return HttpResponse("failure\nFile transfer error", content_type="text/plain; charset=utf-8", status=500)

        # Unpack ZIP files and route to subdirectories
        try:
            import zipfile
            import shutil
            from .routing_service import XML_ROUTING_RULES
            
            zip_files = list(import_dir.glob("*.zip"))
            if zip_files:
                logger.info(f"[IMPORT] Found {len(zip_files)} ZIP files to unpack")
                
                for zf in zip_files:
                    try:
                        with zipfile.ZipFile(zf, "r") as zip_ref:
                            zip_ref.extractall(import_dir)
                            unpacked_files = zip_ref.namelist()
                        
                        logger.info(f"[IMPORT] Unpacked: {zf.name} ({len(unpacked_files)} files)")
                        
                        # Route unpacked files to subdirectories
                        routed_count = 0
                        for unpacked_name in unpacked_files:
                            file_path = import_dir / unpacked_name
                            if not file_path.exists() or not file_path.is_file():
                                continue
                            
                            name_lower = unpacked_name.lower()
                            suffix = file_path.suffix.lower()
                            target_subdir = None
                            
                            if suffix == ".xml":
                                # Sort by prefix length descending for specific matching
                                sorted_rules = sorted(XML_ROUTING_RULES.items(), key=lambda x: len(x[0]), reverse=True)
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
                                dest_dir = import_dir / target_subdir
                                dest_dir.mkdir(parents=True, exist_ok=True)
                                dest_path = dest_dir / unpacked_name
                                try:
                                    shutil.move(str(file_path), str(dest_path))
                                    routed_count += 1
                                except Exception as move_err:
                                    logger.warning(f"[IMPORT] Failed to route {unpacked_name}: {move_err}")
                        
                        session.report += f"[{timezone.now()}] Архив {zf.name}: {len(unpacked_files)} файлов, распределено: {routed_count}\n"
                        
                        # Delete ZIP after unpacking
                        try:
                            zf.unlink()
                        except OSError:
                            pass
                            
                    except Exception as unzip_err:
                        logger.error(f"[IMPORT] Failed to unpack {zf.name}: {unzip_err}")
                        session.report += f"[{timezone.now()}] Ошибка распаковки {zf.name}: {unzip_err}\n"
                
                session.save(update_fields=['report'])
                
        except Exception as e:
            logger.error(f"[IMPORT] ZIP processing failed: {e}", exc_info=True)
            session.report += f"[{timezone.now()}] Ошибка обработки архивов: {e}\n"
            session.save(update_fields=['report'])

        # Run import SYNCHRONOUSLY so 1C gets real result
        try:
            if dry_run:
                logger.info("[IMPORT] DRY RUN mode - skipping import")
                session.report += f"[{timezone.now()}] DRY RUN: импорт пропущен\n"
                session.status = ImportSession.ImportStatus.COMPLETED
                session.finished_at = timezone.now()
                session.save(update_fields=['report', 'status', 'finished_at'])
            else:
                from django.core.management import call_command
                
                logger.info(f"[IMPORT] Starting SYNCHRONOUS import for session_id={session.pk}")
                session.status = ImportSession.ImportStatus.IN_PROGRESS
                session.report += f"[{timezone.now()}] Начало синхронного импорта...\n"
                session.save(update_fields=['status', 'report', 'updated_at'])
                
                # Determine file type from filename
                file_type = "all"
                fn_lower = filename.lower() if filename else ""
                if fn_lower.startswith("goods") or fn_lower.startswith("import"):
                    file_type = "goods"
                elif fn_lower.startswith("offers"):
                    file_type = "offers"
                elif fn_lower.startswith("prices") or fn_lower.startswith("pricelists"):
                    file_type = "prices"
                elif fn_lower.startswith("rests"):
                    file_type = "rests"
                
                logger.info(f"[IMPORT] Detected file_type={file_type} from filename={filename}")
                
                # Run import command synchronously
                call_command(
                    "import_products_from_1c",
                    data_dir=str(import_dir),
                    file_type=file_type,
                    import_session_id=session.pk,
                )
                
                # Refresh and finalize session
                session.refresh_from_db()
                if session.status != ImportSession.ImportStatus.COMPLETED:
                    session.status = ImportSession.ImportStatus.COMPLETED
                    session.finished_at = timezone.now()
                session.report += f"[{timezone.now()}] Импорт завершен успешно.\n"
                session.save(update_fields=['status', 'report', 'finished_at', 'updated_at'])
                
                logger.info(f"[IMPORT] Import completed successfully for session_id={session.pk}")
            
            # Mark exchange cycle complete
            file_service = FileStreamService(sessid)
            file_service.mark_complete()
            
        except Exception as e:
            logger.error(f"[IMPORT] Import failed: {e}", exc_info=True)
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = str(e)
            session.report += f"[{timezone.now()}] ОШИБКА импорта: {e}\n"
            session.save(update_fields=['status', 'error_message', 'report'])
            return HttpResponse(f"failure\n{e}", content_type="text/plain; charset=utf-8", status=500)

        return HttpResponse("success", content_type="text/plain; charset=utf-8")

    def handle_complete(self, request):
        """
        Signal from 1C that all files for the current cycle are uploaded.
        """
        from django.db import transaction
        from apps.products.models import ImportSession
        from apps.products.tasks import process_1c_import_task

        sessid = self._get_exchange_identity(request)
        logger.info(f"[COMPLETE] Received mode=complete for sessid={sessid}")
        
        if not sessid:
            logger.warning("[COMPLETE] Rejected: Missing sessid")
            return HttpResponse("failure\nMissing sessid", status=403)

        # Story 3.2: 1C Loop Fix
        # If the exchange cycle is already marked as complete (by a successful import),
        # then this 'complete' signal is redundant/late and should be ignored 
        # to prevent creating an empty session.
        try:
            file_service = FileStreamService(sessid)
            if file_service.is_complete():
                logger.info(f"[COMPLETE] Cycle already completed for {sessid}. Ignoring duplicate complete signal.")
                return HttpResponse("success", content_type="text/plain; charset=utf-8")
        except Exception as e:
            logger.warning(f"[COMPLETE] Error checking completion status: {e}")

        dry_run = request.query_params.get("dry_run") == "1"

        with transaction.atomic():
            session = ImportSession.objects.select_for_update().filter(
                session_key=sessid,
                status=ImportSession.ImportStatus.PENDING
            ).first()

            if not session:
                logger.warning(f"[COMPLETE] No PENDING session found for {sessid}. Creating NEW session.")
                session = ImportSession.objects.create(
                    session_key=sessid,
                    status=ImportSession.ImportStatus.PENDING,
                    import_type=ImportSession.ImportType.CATALOG,
                    report=f"[{timezone.now()}] Сессия создана по сигналу complete (Fix check skipped?).\n"
                )
                logger.info(f"[COMPLETE] Created NEW session id={session.pk} for sessid={sessid}")
            else:
                session.report += f"[{timezone.now()}] Получен сигнал complete.\n"
                session.save(update_fields=['report'])
                logger.info(f"[COMPLETE] Found EXISTING session id={session.pk}, status={session.status}")

            import_dir = Path(settings.MEDIA_ROOT) / "1c_import"
            
            # Transfer ALL accumulated files from temp to import_dir
            try:
                file_service = FileStreamService(sessid)
                routing_service = FileRoutingService(sessid)
                files = file_service.list_files()
                logger.info(f"[COMPLETE] Files in temp before transfer: {files}")
                
                transferred_count = 0
                for f in files:
                    try:
                        routing_service.move_to_import(f)
                        transferred_count += 1
                        logger.debug(f"[COMPLETE] Transferred: {f}")
                    except Exception as move_err:
                        logger.error(f"[COMPLETE] Failed to move file {f}: {move_err}")
                
                logger.info(f"[COMPLETE] Transferred {transferred_count}/{len(files)} files to {import_dir}")
                session.report += f"[{timezone.now()}] Перенесено файлов: {transferred_count}/{len(files)}\n"
                session.save(update_fields=['report'])
                
            except Exception as e:
                logger.error(f"[COMPLETE] Failed to transfer files: {e}", exc_info=True)
                session.report += f"[{timezone.now()}] ОШИБКА переноса файлов: {e}\n"
                session.save(update_fields=['report'])

            # Check for file-flag .dry_run
            if not dry_run and (import_dir / ".dry_run").exists():
                dry_run = True
                logger.info("[COMPLETE] Detected .dry_run flag file")

            try:
                file_service = FileStreamService(sessid)
                if dry_run:
                    zip_files = [f for f in file_service.list_files() if f.lower().endswith('.zip')]
                    logger.info(f"[COMPLETE] DRY RUN mode, unpacking {len(zip_files)} ZIPs")
                    for zf in zip_files:
                        file_service.unpack_zip(zf, import_dir)
                        session.report += f"[{timezone.now()}] DRY RUN: Архив {zf} распакован.\n"
                    session.report += f"[{timezone.now()}] DRY RUN: Импорт пропущен.\n"
                    session.save(update_fields=['report'])
                else:
                    logger.info(f"[COMPLETE] Dispatching Celery task for session_id={session.pk}, import_dir={import_dir}")
                    task_result = process_1c_import_task.delay(session.pk, str(import_dir))
                    logger.info(f"[COMPLETE] Celery task dispatched: task_id={task_result.id}")
                    session.report += f"[{timezone.now()}] Celery task запущен: {task_result.id}\n"
                    session.save(update_fields=['report'])
                
                # IMPORTANT: Set the flag so the NEXT 'init' starts a clean cycle.
                file_service.mark_complete()
                logger.info(f"[COMPLETE] Exchange cycle marked as complete for {sessid}")

            except Exception as e:
                logger.error(f"[COMPLETE] Protocol error: {e}", exc_info=True)
                session.report += f"[{timezone.now()}] ОШИБКА: {e}\n"
                session.save(update_fields=['report'])

        return HttpResponse("success", content_type="text/plain; charset=utf-8")

    def handle_checkauth(self, request):
        """
        Initializes session and returns cookie info to 1C.
        """
        # Create a session for subsequent requests
        # In DRF, request is rest_framework.request.Request, underlying is ._request

        # Ensure backend is set for login to work
        # Use configured backend from settings instead of hardcoded path
        if not hasattr(request.user, "backend"):
            backends = get_backends()
            if backends:
                backend = backends[0]
                request.user.backend = (
                    f"{backend.__module__}.{backend.__class__.__name__}"
                )
            else:
                request.user.backend = (
                    settings.AUTHENTICATION_BACKENDS[0]
                    if hasattr(settings, "AUTHENTICATION_BACKENDS") and settings.AUTHENTICATION_BACKENDS
                    else "django.contrib.auth.backends.ModelBackend"
                )

        login(request._request, request.user)

        # Use the actual Django session cookie name so 1C sends back the correct cookie
        cookie_name = settings.SESSION_COOKIE_NAME
        session_id = request.session.session_key

        # If session_id is still None, ensure it's saved.
        if not session_id:
            request.session.save()
            session_id = request.session.session_key

        response_text = f"success\r\n{cookie_name}\r\n{session_id}"
        return HttpResponse(response_text, content_type="text/plain; charset=utf-8")

    def handle_init(self, request):
        """
        Capability negotiation (mode=init).
        Implementation of the 'Complete Flag' logic.
        """
        sessid = self._get_exchange_identity(request)
        if not sessid:
            return HttpResponse("failure\nNo session", status=401)

        try:
            file_service = FileStreamService(sessid)
            
            # If the PREVIOUS exchange was marked as complete, 
            # this 'init' starts a NEW cycle -> Full Cleanup.
            if file_service.is_complete():
                logger.info(f"New exchange cycle detected for {sessid}. Performing full cleanup.")
                file_service.cleanup_session(force=True)
                file_service.clear_complete()
            else:
                logger.info(f"Continuing existing exchange cycle for {sessid}. Accumulating files.")
        except Exception as e:
            logger.warning(f"Init cleanup logic fail: {e}")

        zip_support = settings.ONEC_EXCHANGE.get("ZIP_SUPPORT", True)
        file_limit = settings.ONEC_EXCHANGE.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)
        version = settings.ONEC_EXCHANGE.get("COMMERCEML_VERSION", "3.1")

        response_text = f"zip={'yes' if zip_support else 'no'}\r\nfile_limit={file_limit}\r\n" \
                        f"sessid={sessid}\r\nversion={version}"
        return HttpResponse(response_text, content_type="text/plain; charset=utf-8")

    def handle_query(self, request):
        """
        Handle order export requests (mode=query).
        Protocol: GET /?mode=query
        Response: XML (CommerceML 2.x/3.x)
        """
        # Story 3.2: Order Export
        # For now, return empty result to satisfy 1C check
        # and prevent exchange failure (400 Unknown mode).
        
        # We must return valid XML
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Commerceml version="3.1">\n'
            '</Commerceml>'
        )
        return HttpResponse(xml_content, content_type="application/xml")

    def handle_file_upload(self, request):
        """
        Handle chunked file uploads from 1C.
        """
        sessid = self._get_exchange_identity(request)
        filename = request.query_params.get("filename")

        if not sessid or not filename:
            logger.error("Upload rejected: session or filename missing.")
            return HttpResponse("failure\nMissing session or filename", status=400)

        file_limit = settings.ONEC_EXCHANGE.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)

        try:
            file_service = FileStreamService(sessid)
            wsgi_request = request._request
            
            with file_service.open_for_write(filename) as writer:
                chunk_size = 64 * 1024
                while True:
                    chunk = wsgi_request.read(chunk_size)
                    if not chunk:
                        break
                    if writer.bytes_written + len(chunk) > file_limit:
                        return HttpResponse(f"failure\nFile too large", status=413)
                    writer.write(chunk)

            if writer.bytes_written == 0:
                return HttpResponse("failure\nEmpty body", status=400)

            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        except FileLockError:
            return HttpResponse("failure\nFile busy", status=503)
        except Exception as e:
            logger.exception(f"Upload error: {e}")
            return HttpResponse("failure\nInternal error", status=500)
