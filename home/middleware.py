from django.conf import settings
from django.shortcuts import render

from .models import MaintenanceMode


class MaintenanceModeMiddleware:
    EXEMPT_PREFIXES = ('/admin/', '/ckeditor/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exempt = self.EXEMPT_PREFIXES + (settings.STATIC_URL, settings.MEDIA_URL)
        if request.path.startswith(exempt):
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)

        config = MaintenanceMode.get_solo()
        if config.activo:
            response = render(request, 'maintenance.html', {'mensaje': config.mensaje}, status=503)
            response['Retry-After'] = '3600'
            return response

        return self.get_response(request)
