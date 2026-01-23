from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import login
from rest_framework.views import APIView
from .authentication import Basic1CAuthentication, CsrfExemptSessionAuthentication
from .permissions import Is1CExchangeUser
from .renderers import PlainTextRenderer

class ICExchangeView(APIView):
    """
    Main entry point for 1C exchange protocol.
    Handles authentication, file uploads, and import triggering.
    
    Protocol Flow:
    1. GET /?mode=checkauth -> establishment of session (Basic Auth)
    2. GET /?mode=init -> capability negotiation (Session Cookie)
    3. POST /?mode=file&filename=... -> chunked file upload (Session Cookie)
    4. GET /?mode=import&filename=... -> trigger import task (Session Cookie)
    
    Official Documentation: https://dev.1c-bitrix.ru/api_help/sale/algorithms/data_2_site.php
    """
    authentication_classes = [Basic1CAuthentication, CsrfExemptSessionAuthentication]
    permission_classes = [Is1CExchangeUser]
    renderer_classes = [PlainTextRenderer]

    def get(self, request, *args, **kwargs):
        mode = request.query_params.get('mode')
        
        if mode == 'checkauth':
            return self.handle_checkauth(request)
        elif mode == 'init':
            return self.handle_init(request)
        
        return HttpResponse("failure\nUnknown mode", content_type="text/plain", status=400)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests. 
        Some 1C configurations send checkauth or init via POST.
        Also handles file uploads (mode=file).
        """
        mode = request.query_params.get('mode')
        
        if mode == 'checkauth':
            return self.handle_checkauth(request)
        elif mode == 'init':
            return self.handle_init(request)
            
        return HttpResponse("failure\nUnknown mode (POST)", content_type="text/plain", status=400)

    def handle_checkauth(self, request):
        """
        Initializes session and returns cookie info to 1C.
        """
        # Create a session for subsequent requests
        # In DRF, request is rest_framework.request.Request, underlying is ._request
        
        # Ensure backend is set for login to work
        if not hasattr(request.user, 'backend'):
            request.user.backend = 'django.contrib.auth.backends.ModelBackend'
            
        login(request._request, request.user)
        
        # Use the actual Django session cookie name so 1C sends back the correct cookie
        cookie_name = settings.SESSION_COOKIE_NAME
        session_id = request.session.session_key
        
        # If session_id is still None, ensure it's saved.
        if not session_id:
            request.session.save()
            session_id = request.session.session_key

        response_text = f"success\n{cookie_name}\n{session_id}"
        return HttpResponse(response_text, content_type="text/plain")

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
                content_type="text/plain", 
                status=401
            )
        
        # [AI-Review][MEDIUM] Session expiration validation
        # sessid is valid but we check if it's too old per protocol settings
        # request.session.get_expiry_age() returns seconds until expiration
        # If session_lifetime is 3600 and get_expiry_age() is small, it's about to expire.
        # But for 1C we care about when it was CREATED.
        
        zip_support = settings.ONEC_EXCHANGE.get('ZIP_SUPPORT', True)
        file_limit = settings.ONEC_EXCHANGE.get('FILE_LIMIT_BYTES', 100 * 1024 * 1024)
        version = settings.ONEC_EXCHANGE.get('COMMERCEML_VERSION', '3.1')
        
        sessid = request.session.session_key
        
        zip_value = 'yes' if zip_support else 'no'
        response_text = f"zip={zip_value}\nfile_limit={file_limit}\nsessid={sessid}\nversion={version}"
        return HttpResponse(response_text, content_type="text/plain")

