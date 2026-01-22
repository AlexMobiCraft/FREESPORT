from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import login
from rest_framework.views import APIView
from .authentication import Basic1CAuthentication
from .permissions import Is1CExchangeUser

class ICExchangeView(APIView):
    """
    Main entry point for 1C exchange protocol.
    Handles authentication, file uploads, and import triggering.
    """
    authentication_classes = [Basic1CAuthentication]
    permission_classes = [Is1CExchangeUser]

    def get(self, request, *args, **kwargs):
        mode = request.query_params.get('mode')
        
        if mode == 'checkauth':
            return self.handle_checkauth(request)
        
        return HttpResponse("failure\nUnknown mode", content_type="text/plain", status=400)

    def handle_checkauth(self, request):
        """
        Initializes session and returns cookie info to 1C.
        """
        # Create a session for subsequent requests
        # In DRF, request is rest_framework.request.Request, underlying is ._request
        login(request._request, request.user)
        
        cookie_name = settings.ONEC_EXCHANGE.get('SESSION_COOKIE_NAME', 'FREESPORT_1C_SESSION')
        session_id = request.session.session_key
        
        # If session_id is still None, ensure it's saved.
        if not session_id:
            request.session.save()
            session_id = request.session.session_key

        response_text = f"success\n{cookie_name}\n{session_id}"
        return HttpResponse(response_text, content_type="text/plain")
