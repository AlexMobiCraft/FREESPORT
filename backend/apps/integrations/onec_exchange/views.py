import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_backends, login
from django.http import HttpResponse
from rest_framework.views import APIView

from .authentication import Basic1CAuthentication, CsrfExemptSessionAuthentication
from .file_service import FileLockError, FileStreamService
from .permissions import Is1CExchangeUser
from .renderers import PlainTextRenderer
from .routing_service import FileRoutingService

logger = logging.getLogger(__name__)


class ICExchangeView(APIView):
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
            # Story 1.3: Handle 'complete' signal - usually just ack required
            return HttpResponse("success", content_type="text/html; charset=utf-8")

        return HttpResponse(
            "failure\nUnknown mode", content_type="text/html; charset=utf-8", status=400
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
            # Story 1.3: Handle 'complete' signal - usually just ack required
            return HttpResponse("success", content_type="text/html; charset=utf-8")

        return HttpResponse(
            "failure\nUnknown mode (POST)", content_type="text/html; charset=utf-8", status=400
        )

    def handle_import(self, request):
        """
        Trigger the import process.

        Story 3.1: Orchestration of Async Import

        Protocol: GET /?mode=import&filename=X&sessid=Y

        AC 1: Check for active sessions (pending or in-progress)
        AC 1: Create ImportSession with status pending
        AC 1: Trigger async process_1c_import_task
        AC 1: Return "success" (text/plain)
        """
        # Try to get sessid from query param first, then fallback to session key (Standard CommerceML)
        sessid = request.query_params.get("sessid") or request.session.session_key
        if not sessid:
            return HttpResponse(
                "failure\nMissing sessid", content_type="text/html; charset=utf-8", status=403
            )

        # If both are present, they MUST match
        param_sessid = request.query_params.get("sessid")
        if param_sessid and param_sessid != request.session.session_key:
            return HttpResponse(
                "failure\nInvalid session", content_type="text/html; charset=utf-8", status=403
            )

        filename = request.query_params.get("filename")
        if not filename:
            return HttpResponse(
                "failure\nMissing filename parameter",
                content_type="text/html; charset=utf-8",
                status=400,
            )

        from django.utils import timezone

        from apps.products.models import ImportSession
        from apps.products.tasks import process_1c_import_task

        # AC 1: Check for active sessions (pending or in-progress)
        active_sessions = ImportSession.objects.filter(
            status__in=[
                ImportSession.ImportStatus.PENDING,
                ImportSession.ImportStatus.IN_PROGRESS,
            ]
        )
        if active_sessions.exists():
            logger.warning(
                f"Import attempt blocked: another import is in progress "
                f"(session={sessid[:8]}...)"
            )
            # AC 1: return failure with message
            return HttpResponse(
                "failure\nImport already in progress", content_type="text/html; charset=utf-8"
            )

        # AC 1: Create ImportSession with status pending
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.PENDING,
            report=(
                f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Получена команда import от 1С (файл: {filename})\n"
            ),
        )

        
        import_dir = Path(settings.MEDIA_ROOT) / "1c_temp" / sessid

        # AC 1: Trigger async process_1c_import_task
        # Story 3.1: We pass the filename to the task so it can handle unpacking asynchronously
        # This prevents timeouts locally in the view
        process_1c_import_task.delay(session.pk, str(import_dir), filename)

        logger.info(
            f"Import triggered successfully: {filename}, "
            f"session_id={session.pk}, task dispatched"
        )

        return HttpResponse("success", content_type="text/html; charset=utf-8")

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
        return HttpResponse(response_text, content_type="text/html; charset=utf-8")

    def handle_init(self, request):
        """
        Returns server capabilities for 1C data exchange.
        Protocol: https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php

        IMPORTANT: 'sessid' is Django Session ID (request.session.session_key),
        NOT a CSRF token. This is required by the 1C protocol to maintain
        session state across checkauth -> init -> file -> import requests.

        Equivalent to PHP: session_id()

        Response format (4 lines, text/plain):
        - zip=yes|no
        - file_limit=<bytes>
        - sessid=<session_key>  ← Django Session ID (NOT CSRF token)
        - version=<CommerceML_version>
        """
        # Protocol Enforcement: Session MUST be created in checkauth
        if not request.session.session_key:
            return HttpResponse(
                "failure\nNo session - call checkauth first",
                content_type="text/html; charset=utf-8",
                status=401,
            )

        sessid = request.session.session_key

        # Clean up any previous temp files for this session
        # This addresses reuse/retry risk - prevents stale file accumulation
        # and ensures clean slate for new imports
        try:
            file_service = FileStreamService(sessid)
            file_service.cleanup_session()
            logger.info(f"Session cleanup complete for init: {sessid[:8]}...")
        except Exception as e:
            # Log but don't fail - cleanup is best-effort
            logger.warning(f"Session cleanup failed during init: {e}")

        zip_support = settings.ONEC_EXCHANGE.get("ZIP_SUPPORT", True)
        file_limit = settings.ONEC_EXCHANGE.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)
        version = settings.ONEC_EXCHANGE.get("COMMERCEML_VERSION", "3.1")

        zip_value = "yes" if zip_support else "no"
        response_text = (
            f"zip={zip_value}\r\nfile_limit={file_limit}\r\n"
            f"sessid={sessid}\r\nversion={version}"
        )
        return HttpResponse(response_text, content_type="text/html; charset=utf-8")

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

        Story 2.1: File Stream Upload

        Protocol: POST /?mode=file&filename=X&sessid=Y with binary body

        AC 1: Stream binary content to 1c_temp/<sessid>/<filename>
        AC 2: Append mode for chunked uploads (multiple requests same filename)
        AC 3: Validate sessid matches request.session.session_key
        AC 4: Return 403 if sessid is missing

        NFR2: Memory efficiency - stream body in chunks, never load entirely into RAM

        Response format (text/plain):
        - "success" on successful write
        - "failure\n<message>" on error (403 for session issues)
        """
        # Try to get sessid from query param first, then fallback to session key (Standard CommerceML)
        sessid = request.query_params.get("sessid") or request.session.session_key
        if not sessid:
            return HttpResponse(
                "failure\nMissing sessid", content_type="text/html; charset=utf-8", status=403
            )

        # If both are present, they MUST match
        param_sessid = request.query_params.get("sessid")
        if param_sessid and param_sessid != request.session.session_key:
            return HttpResponse(
                "failure\nInvalid session", content_type="text/html; charset=utf-8", status=403
            )

        # Get filename parameter
        filename = request.query_params.get("filename")
        if not filename:
            return HttpResponse(
                "failure\nMissing filename parameter",
                content_type="text/html; charset=utf-8",
                status=400,
            )

        # Get file size limit from settings
        file_limit = settings.ONEC_EXCHANGE.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)

        # AC 1 & 2: Stream content to file using append mode
        # NFR2: Stream body in chunks to avoid loading entire request into memory
        try:
            file_service = FileStreamService(sessid)

            # Chunk size for streaming reads (64KB - balance between memory and I/O)
            chunk_size = 64 * 1024

            # Access the underlying WSGI request for streaming
            # DRF wraps Django's HttpRequest; we need the raw stream
            wsgi_request = request._request

            # Use context manager to open file ONCE for all chunks
            # This avoids repeated open/close cycles for each 64KB chunk
            with file_service.open_for_write(filename) as writer:
                while True:
                    chunk = wsgi_request.read(chunk_size)
                    if not chunk:
                        break

                    # Check file size limit before writing
                    if writer.bytes_written + len(chunk) > file_limit:
                        return HttpResponse(
                            f"failure\nFile exceeds limit of {file_limit} bytes",
                            content_type="text/html; charset=utf-8",
                            status=413,
                        )

                    writer.write(chunk)

            if writer.bytes_written == 0:
                return HttpResponse(
                    "failure\nEmpty body", content_type="text/html; charset=utf-8", status=400
                )

            logger.info(
                f"File upload complete: {filename} ({writer.bytes_written} bytes) "
                f"session={sessid[:8]}..."
            )

            # Story 2.2: Route file to appropriate import directory
            # ZIP files stay in temp (for later unpacking in mode=import)
            # XML and images are routed to 1c_import/<sessid>/<subdir>/
            try:
                routing_service = FileRoutingService(sessid)
                if routing_service.should_route(filename):
                    routing_service.move_to_import(filename)
            except Exception as e:
                # Log routing error but don't fail the upload
                # File is already saved in temp, routing can be retried
                logger.warning(f"File routing failed for {filename}: {e}")

            # AC 1: Return "success" on successful write
            return HttpResponse("success", content_type="text/html; charset=utf-8")

        except FileLockError as e:
            # File is being written by another request - retry later
            logger.warning(f"File lock contention for {filename}: {e}")
            return HttpResponse(
                "failure\nFile busy - retry later",
                content_type="text/html; charset=utf-8",
                status=503,  # Service Unavailable - indicates temporary condition
            )

        except Exception as e:
            # Log full error details for debugging (server-side only)
            logger.exception(f"File upload error: {e}")

            # Return generic error message to prevent information disclosure
            # Internal details (stack traces, file paths) must not leak to client
            return HttpResponse(
                "failure\nInternal server error", content_type="text/html; charset=utf-8", status=500
            )
