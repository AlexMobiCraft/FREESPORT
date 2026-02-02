import io
import logging
import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_backends, login
from django.core.cache import cache
from django.db import transaction
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.services.order_export import OrderExportService
from apps.orders.signals import orders_bulk_updated

from .authentication import Basic1CAuthentication, CsrfExemptSessionAuthentication
from .file_service import FileLockError, FileStreamService
from .permissions import Is1CExchangeUser
from .renderers import PlainTextRenderer
from .import_orchestrator import ImportOrchestratorService
from .routing_service import FileRoutingService

logger = logging.getLogger(__name__)

EXCHANGE_LOG_SUBDIR = "1c_exchange/logs"
ORDERS_XML_FILENAME = "orders.xml"
ORDERS_ZIP_FILENAME = "orders.zip"


def _get_exchange_log_dir() -> Path:
    """Return the private directory for exchange audit logs.

    Uses ``settings.EXCHANGE_LOG_DIR`` when configured, otherwise falls back
    to ``BASE_DIR / "var" / EXCHANGE_LOG_SUBDIR`` which is NOT inside
    MEDIA_ROOT (and therefore not publicly accessible).
    """
    custom = getattr(settings, "EXCHANGE_LOG_DIR", None)
    if custom:
        return Path(custom)
    return Path(settings.BASE_DIR) / "var" / EXCHANGE_LOG_SUBDIR


def _save_exchange_log(filename: str, content, is_binary: bool = False) -> None:
    """Save a copy of exchange output to a private log directory for audit."""
    try:
        log_dir = _get_exchange_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filepath = log_dir / f"{timestamp}_{filename}"
        if is_binary:
            filepath.write_bytes(content)
        else:
            filepath.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error(f"[EXCHANGE LOG] Failed to save audit log {filename}: {e}")


def _copy_file_to_log(source_path: Path, filename: str) -> None:
    """Copy a file to the exchange log directory without loading it into RAM.
    
    This avoids OOM issues when logging large XML/ZIP files by using
    filesystem-level copy instead of reading content into memory.
    """
    try:
        log_dir = _get_exchange_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        dest_path = log_dir / f"{timestamp}_{filename}"
        shutil.copy2(source_path, dest_path)
    except Exception as e:
        logger.error(f"[EXCHANGE LOG] Failed to copy audit log {filename}: {e}")


class ICExchangeView(APIView):
    def _get_exchange_identity(self, request):
        """
        Return a unique exchange identity per session to avoid race conditions.
        
        Uses session_key which is unique per browser/1C client connection.
        This ensures multiple concurrent 1C exchanges don't interfere with
        each other's temp files and import directories.
        """
        # Prefer explicit sessid from query params (for 1C compatibility)
        sessid = request.query_params.get("sessid")
        if sessid:
            return sessid
        
        # Fall back to Django session key (unique per connection)
        return request.session.session_key
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
        elif mode == "success":
            return self.handle_success(request)
        elif mode == "complete":
            return self.handle_complete(request)
        elif mode == "deactivate":
            return self.handle_complete(request)

        return HttpResponse(
            "failure\nUnknown mode", content_type="text/plain; charset=utf-8"
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
            "failure\nUnknown mode (POST)", content_type="text/plain; charset=utf-8"
        )

    def handle_import(self, request):
        """
        Handle the import command from 1C.

        IMPORTANT: In incremental mode ("Выгружать только измененные объекты"),
        1C does NOT send mode=complete. It expects mode=import to trigger
        the actual import processing.

        Delegates to ImportOrchestratorService (Fat Services, Thin Views).
        """
        sessid = self._get_exchange_identity(request)
        filename = request.query_params.get("filename", "unknown")

        if not sessid:
            logger.warning("[IMPORT] Request rejected: No identifier found.")
            return HttpResponse(
                "failure\nMissing sessid", content_type="text/plain; charset=utf-8"
            )

        orchestrator = ImportOrchestratorService(sessid, filename)
        success, message = orchestrator.execute()

        if success:
            return HttpResponse("success", content_type="text/plain; charset=utf-8")
        return HttpResponse(
            f"failure\n{message}",
            content_type="text/plain; charset=utf-8",
        )

    def handle_complete(self, request):
        """
        Signal from 1C that all files for the current cycle are uploaded.
        
        Delegates to ImportOrchestratorService.finalize_batch() following
        the Fat Services / Thin Views pattern.
        """
        sessid = self._get_exchange_identity(request)
        logger.info(f"[COMPLETE] Received mode=complete for sessid={sessid}")

        if not sessid:
            logger.warning("[COMPLETE] Rejected: Missing sessid")
            return HttpResponse(
                "failure\nMissing sessid", content_type="text/plain; charset=utf-8"
            )

        dry_run = request.query_params.get("dry_run") == "1"
        orchestrator = ImportOrchestratorService(sessid, "complete")
        success, message = orchestrator.finalize_batch(dry_run=dry_run)

        if success:
            return HttpResponse("success", content_type="text/plain; charset=utf-8")
        return HttpResponse(
            f"failure\n{message}",
            content_type="text/plain; charset=utf-8",
        )

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
            return HttpResponse(
                "failure\nNo session", content_type="text/plain; charset=utf-8"
            )

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

        exchange_cfg = getattr(settings, "ONEC_EXCHANGE", {})
        zip_support = exchange_cfg.get("ZIP_SUPPORT", True)
        file_limit = exchange_cfg.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)
        version = exchange_cfg.get("COMMERCEML_VERSION", "3.1")

        response_text = f"zip={'yes' if zip_support else 'no'}\r\nfile_limit={file_limit}\r\n" \
                        f"sessid={sessid}\r\nversion={version}"
        return HttpResponse(response_text, content_type="text/plain; charset=utf-8")

    def handle_query(self, request):
        """
        Handle order export requests (mode=query).
        Protocol: GET /?mode=query[&zip=yes]
        Returns XML (or ZIP) with pending orders for 1C.
        
        Memory optimization: Uses streaming for XML responses to avoid
        materializing large exports in RAM. For ZIP, uses tempfile to
        avoid doubling memory pressure.
        """
        query_time = timezone.now()

        orders = (
            Order.objects.filter(
                sent_to_1c=False,
                export_skipped=False,
                created_at__lte=query_time,
            )
            .select_related("user")
            .prefetch_related("items__variant")
        )

        service = OrderExportService()
        use_zip = request.query_params.get("zip", "").lower() == "yes"

        import tempfile
        exported_ids: list[int] = []
        skipped_ids: list[int] = []

        if use_zip:
            # ZIP mode: Stream XML to temp file, then compress and stream response
            # Using NamedTemporaryFile to allow FileResponse streaming
            xml_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
            try:
                for chunk in service.generate_xml_streaming(orders, exported_ids, skipped_ids):
                    xml_tmp.write(chunk.encode("utf-8"))
                xml_tmp.close()

                # Mark skipped orders to prevent poison queue
                if skipped_ids:
                    Order.objects.filter(pk__in=skipped_ids).update(export_skipped=True)
                    logger.info(f"Marked {len(skipped_ids)} orders as export_skipped")

                # Store session/cache state after successful generation
                request.session["last_1c_query_time"] = query_time.isoformat()
                cache_key = f"1c_exported_ids_{request.session.session_key}"
                cache.set(cache_key, exported_ids, timeout=3600)

                # Create ZIP in a named temp file for streaming
                zip_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                try:
                    with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(xml_tmp.name, ORDERS_XML_FILENAME)
                    zip_tmp.close()

                    # Save audit log via file copy (avoids loading into RAM)
                    _copy_file_to_log(Path(zip_tmp.name), ORDERS_ZIP_FILENAME)

                    # Stream ZIP file as response
                    response = FileResponse(
                        open(zip_tmp.name, "rb"),
                        content_type="application/zip",
                        as_attachment=True,
                        filename=ORDERS_ZIP_FILENAME,
                    )
                    # Mark temp file for cleanup after response is sent
                    zip_path = Path(zip_tmp.name)
                    response._resource_closers.append(lambda p=zip_path: p.unlink(missing_ok=True))
                    return response
                finally:
                    # Cleanup XML temp file
                    Path(xml_tmp.name).unlink(missing_ok=True)
            except Exception:
                # Cleanup on error
                Path(xml_tmp.name).unlink(missing_ok=True)
                raise

        # Non-ZIP: Stream XML directly via FileResponse
        xml_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode="w", encoding="utf-8")
        try:
            for chunk in service.generate_xml_streaming(orders, exported_ids, skipped_ids):
                xml_tmp.write(chunk)
            xml_tmp.close()

            # Mark skipped orders to prevent poison queue
            if skipped_ids:
                Order.objects.filter(pk__in=skipped_ids).update(export_skipped=True)
                logger.info(f"Marked {len(skipped_ids)} orders as export_skipped")

            # Store session/cache state after successful generation
            request.session["last_1c_query_time"] = query_time.isoformat()
            cache_key = f"1c_exported_ids_{request.session.session_key}"
            cache.set(cache_key, exported_ids, timeout=3600)

            # Save audit log via file copy (avoids loading into RAM)
            _copy_file_to_log(Path(xml_tmp.name), ORDERS_XML_FILENAME)

            # Stream XML file as response
            response = FileResponse(
                open(xml_tmp.name, "rb"),
                content_type="application/xml",
            )
            # Mark temp file for cleanup after response is sent
            xml_path = Path(xml_tmp.name)
            response._resource_closers.append(lambda p=xml_path: p.unlink(missing_ok=True))
            return response
        except Exception:
            # Cleanup on error
            Path(xml_tmp.name).unlink(missing_ok=True)
            raise

    def handle_success(self, request):
        """
        Handle order export confirmation (mode=success).
        Marks ONLY orders that were actually exported in the last query as sent_to_1c=True.
        Uses exported_order_ids from session to ensure data integrity.
        """
        last_query_iso = request.session.get("last_1c_query_time")
        cache_key = f"1c_exported_ids_{request.session.session_key}"
        exported_ids = cache.get(cache_key)

        if not last_query_iso:
            logger.warning(
                "[EXPORT SUCCESS] No last_1c_query_time in session — "
                "cannot determine which orders to mark. Returning failure."
            )
            return HttpResponse(
                "failure\nNo prior query timestamp in session",
                content_type="text/plain; charset=utf-8",
            )

        if exported_ids is None:
            # Fallback: use time-window based update when cache is lost
            # This is less precise but prevents complete failure after long imports
            logger.warning(
                "[EXPORT SUCCESS] Cache entry for exported_ids is missing "
                "(eviction or restart) — using time-window fallback."
            )
            try:
                from datetime import datetime
                last_query_time = datetime.fromisoformat(last_query_iso)
                if timezone.is_naive(last_query_time):
                    last_query_time = timezone.make_aware(last_query_time)
                
                # Fallback: mark orders that match the time window and are not skipped
                now = timezone.now()
                with transaction.atomic():
                    updated = Order.objects.filter(
                        sent_to_1c=False,
                        export_skipped=False,
                        created_at__lte=last_query_time,
                    ).update(
                        sent_to_1c=True,
                        sent_to_1c_at=now,
                        updated_at=now,
                    )
                
                logger.info(
                    f"[EXPORT SUCCESS] Fallback: marked {updated} orders as sent_to_1c "
                    f"(time-window: created_at <= {last_query_time})"
                )
                
                # Clean up session state
                del request.session["last_1c_query_time"]
                return HttpResponse("success", content_type="text/plain; charset=utf-8")
            except Exception as e:
                logger.error(f"[EXPORT SUCCESS] Fallback failed: {e}")
                return HttpResponse(
                    "failure\nExported order IDs lost from cache — retry query first",
                    content_type="text/plain; charset=utf-8",
                )

        if not exported_ids:
            logger.info("[EXPORT SUCCESS] No orders were exported in last query — nothing to mark.")
            # Clean up session state
            del request.session["last_1c_query_time"]
            cache.delete(cache_key)
            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        now = timezone.now()
        with transaction.atomic():
            updated = Order.objects.filter(
                pk__in=exported_ids,
                sent_to_1c=False,
            ).update(
                sent_to_1c=True,
                sent_to_1c_at=now,
                updated_at=now,
            )

        logger.info(f"[EXPORT SUCCESS] Marked {updated} orders as sent_to_1c (of {len(exported_ids)} exported)")

        # Send custom signal for audit (QuerySet.update bypasses post_save)
        if updated > 0:
            orders_bulk_updated.send(
                sender=Order,
                order_ids=exported_ids,
                field="sent_to_1c",
                timestamp=now,
            )

        # Clear the session/cache state to prevent double-processing
        del request.session["last_1c_query_time"]
        cache.delete(cache_key)

        return HttpResponse("success", content_type="text/plain; charset=utf-8")

    def handle_file_upload(self, request):
        """
        Handle chunked file uploads from 1C.
        """
        sessid = self._get_exchange_identity(request)
        filename = request.query_params.get("filename")

        if not sessid or not filename:
            logger.error("Upload rejected: session or filename missing.")
            return HttpResponse(
                "failure\nMissing session or filename",
                content_type="text/plain; charset=utf-8",
            )

        exchange_cfg = getattr(settings, "ONEC_EXCHANGE", {})
        file_limit = exchange_cfg.get("FILE_LIMIT_BYTES", 100 * 1024 * 1024)

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
                        return HttpResponse(
                            "failure\nFile too large",
                            content_type="text/plain; charset=utf-8",
                        )
                    writer.write(chunk)

            if writer.bytes_written == 0:
                return HttpResponse(
                    "failure\nEmpty body", content_type="text/plain; charset=utf-8"
                )

            return HttpResponse("success", content_type="text/plain; charset=utf-8")

        except FileLockError:
            return HttpResponse(
                "failure\nFile busy", content_type="text/plain; charset=utf-8"
            )
        except Exception as e:
            logger.exception(f"Upload error: {e}")
            return HttpResponse(
                "failure\nInternal error", content_type="text/plain; charset=utf-8"
            )
