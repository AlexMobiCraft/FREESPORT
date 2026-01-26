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
            return self.handle_complete(request)

        return HttpResponse(
            "failure\nUnknown mode (POST)", content_type="text/plain; charset=utf-8", status=400
        )

    def handle_import(self, request):
        """
        Acknowledge the import command from 1C.
        """
        from datetime import timedelta
        from django.db import transaction
        from apps.products.models import ImportSession

        sessid = self._get_exchange_identity(request)
        if not sessid:
            logger.warning("Import request rejected: No identifier found.")
            return HttpResponse("failure\nMissing sessid", status=403)
            
        logger.info(f"Import command received for identity {sessid}")

        # 2. Lazy Expiration & Concurrency Protection
        with transaction.atomic():
            # Mark sessions older than 2 hours as FAILED
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
                # Add info about command to report
                filename = request.query_params.get("filename", "unknown")
                active_session.report += f"[{timezone.now()}] Получена команда import для файла: {filename}\n"
                active_session.save(update_fields=['report'])
                
                # Check for routing
                router = FileRoutingService(sessid)
                if router.should_route(filename):
                    try:
                        router.move_to_import(filename)
                    except Exception as e:
                        logger.error(f"Routing error: {e}")
                
                return HttpResponse("success", content_type="text/plain; charset=utf-8")

            # 3. Create new session record if none exists
            new_session = ImportSession.objects.create(
                session_key=sessid,
                status=ImportSession.ImportStatus.PENDING,
                import_type=ImportSession.ImportType.CATALOG,
                report=f"[{timezone.now()}] Сессия создана по запросу mode=import. Ожидание mode=complete или новых файлов.\n"
            )
            
            # Initial routing attempt
            filename = request.query_params.get("filename")
            if filename:
                router = FileRoutingService(sessid)
                if router.should_route(filename):
                    try:
                        router.move_to_import(filename)
                    except Exception as e:
                        logger.warning(f"Initial routing fail: {e}")

        return HttpResponse("success", content_type="text/plain; charset=utf-8")

    def handle_complete(self, request):
        """
        Signal from 1C that all files for the current cycle are uploaded.
        """
        from django.db import transaction
        from apps.products.models import ImportSession
        from apps.products.tasks import process_1c_import_task

        sessid = self._get_exchange_identity(request)
        if not sessid:
            return HttpResponse("failure\nMissing sessid", status=403)

        dry_run = request.query_params.get("dry_run") == "1"

        with transaction.atomic():
            session = ImportSession.objects.select_for_update().filter(
                session_key=sessid,
                status=ImportSession.ImportStatus.PENDING
            ).first()

            if not session:
                session = ImportSession.objects.create(
                    session_key=sessid,
                    status=ImportSession.ImportStatus.PENDING,
                    import_type=ImportSession.ImportType.CATALOG,
                    report=f"[{timezone.now()}] Сессия создана по сигналу complete.\n"
                )
            else:
                session.report += f"[{timezone.now()}] Получен сигнал complete.\n"
                session.save(update_fields=['report'])

            import_dir = Path(settings.MEDIA_ROOT) / "1c_import"
            
            # Check for file-flag .dry_run
            if not dry_run and (import_dir / ".dry_run").exists():
                dry_run = True

            try:
                file_service = FileStreamService(sessid)
                if dry_run:
                    zip_files = [f for f in file_service.list_files() if f.lower().endswith('.zip')]
                    for zf in zip_files:
                        file_service.unpack_zip(zf, import_dir)
                        session.report += f"[{timezone.now()}] DRY RUN: Архив {zf} распакован.\n"
                    session.report += f"[{timezone.now()}] DRY RUN: Импорт пропущен.\n"
                    session.save(update_fields=['report'])
                else:
                    process_1c_import_task.delay(session.pk, str(import_dir))
                
                # IMPORTANT: Set the flag so the NEXT 'init' starts a clean cycle.
                file_service.mark_complete()
                logger.info(f"Exchange cycle marked as complete for {sessid}")

            except Exception as e:
                logger.error(f"Complete protocol error: {e}")

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

            # Accumulate files immediately in import dir to support per-file session mode
            try:
                routing_service = FileRoutingService(sessid)
                if routing_service.should_route(filename):
                    routing_service.move_to_import(filename)
            except Exception as e:
                logger.warning(f"Immediate routing failed for {filename}: {e}")

            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        except FileLockError:
            return HttpResponse("failure\nFile busy", status=503)
        except Exception as e:
            logger.exception(f"Upload error: {e}")
            return HttpResponse("failure\nInternal error", status=500)
