from django.conf import settings
from django.urls import translate_url
from django.utils import translation

from .models import SitioIngles


def sitio_ingles(request):
    """Selector de idioma y enlaces hreflang (ver home.middleware.SitioInglesMiddleware)."""
    publico = getattr(request, 'ingles_publico', None)
    if publico is None:
        publico = SitioIngles.get_solo().publico
    ctx = {
        'ingles_publico': publico,
        'mostrar_selector_idioma': publico or request.user.is_staff,
        'vista_previa_ingles': not publico and translation.get_language() == 'en',
    }
    ruta = request.get_full_path()
    url_es, url_en = translate_url(ruta, settings.LANGUAGE_CODE), translate_url(ruta, 'en')
    if url_es != url_en:  # página con versión en los dos idiomas
        ctx['url_es'] = request.build_absolute_uri(url_es)
        ctx['url_en'] = request.build_absolute_uri(url_en)
    return ctx
