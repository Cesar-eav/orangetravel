from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import translate_url
from django.utils import translation

from .models import MaintenanceMode, SitioIngles


class MaintenanceModeMiddleware:
    EXEMPT_PREFIXES = ('/admin/', '/panel/', '/ckeditor/')

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


class SitioInglesMiddleware:
    """Controla /en/ con el interruptor «Sitio en inglés» (home.SitioIngles).

    Apagado: /en/ responde 404 salvo al staff, que la usa para revisar traducciones.
    Encendido: /en/ es pública y quien eligió inglés en el selector (cookie de
    idioma) vuelve a /en/ al entrar por una URL en español. Nunca se decide por
    Accept-Language, para que Google indexe las dos versiones.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        publico = SitioIngles.get_solo().publico
        request.ingles_publico = publico
        idioma_ruta = translation.get_language_from_path(request.path_info)

        if idioma_ruta == 'en' and not publico and not request.user.is_staff:
            raise Http404

        if (publico and idioma_ruta is None and request.method == 'GET'
                and request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) == 'en'):
            actual = request.get_full_path()
            destino = translate_url(actual, 'en')
            if destino != actual:  # solo páginas públicas traducibles (no admin, panel ni pagos)
                return redirect(destino)

        return self.get_response(request)
