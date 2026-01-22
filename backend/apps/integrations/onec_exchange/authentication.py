from rest_framework.authentication import BasicAuthentication
from django.contrib.auth import login
from django.conf import settings

class Basic1CAuthentication(BasicAuthentication):
    """
    Custom Basic Authentication for 1C Exchange.
    
    Inherits standard BasicAuthentication logic but serves as a distinct 
    authentication class for 1C integration points. This separation allows 
    future extensions specific to 1C auth quirks (e.g. handling specific 1C 
    User-Agent or non-standard headers) without affecting global auth.
    """
    pass
