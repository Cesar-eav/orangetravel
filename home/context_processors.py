from django.conf import settings
from django.urls import translate_url
from django.utils import translation

from .models import SitioIngles


def sitio_ingles(request):
    """Selector de idioma y enlaces hreflang (ver home.middleware.SitioInglesMiddleware).

    Mientras el inglés no esté anunciado (banderas apagadas), /en/ lleva noindex y solo
    el staff ve el selector; el resto puede entrar a /en/ por link si es accesible.
    """
    anunciado = getattr(request, 'ingles_anunciado', None)
    if anunciado is None:
        anunciado = SitioIngles.get_solo().mostrar_banderas
    en_ingles = translation.get_language() == 'en'
    ctx = {
        'ingles_anunciado': anunciado,
        'mostrar_selector_idioma': anunciado or request.user.is_staff,
        'noindex_ingles': not anunciado and en_ingles,
        'vista_previa_ingles': not anunciado and en_ingles and request.user.is_staff,
    }
    ruta = request.get_full_path()
    url_es, url_en = translate_url(ruta, settings.LANGUAGE_CODE), translate_url(ruta, 'en')
    if url_es != url_en:  # página con versión en los dos idiomas
        ctx['url_es'] = request.build_absolute_uri(url_es)
        ctx['url_en'] = request.build_absolute_uri(url_en)
    return ctx
