"""Qué versión (español o inglés) del contenido traducible se muestra.

Tour y Post tienen «traduccion_en_aprobada»: mientras no esté marcada, el público
que navega en inglés ve el texto en español. Los modelos sin ese campo (zonas,
categorías, páginas) muestran el inglés en cuanto existe.
"""
from django.utils.translation import get_language

CAMPOS = {
    'Tour': ('nombre', 'itinerario', 'incluye'),
    'ItinerarioDia': ('titulo', 'descripcion'),
    'Post': ('titulo', 'extracto', 'contenido'),
    'ImagenPost': ('caption',),
}


def es_ingles(idioma=None):
    return (idioma or get_language() or '').split('-')[0] == 'en'


def texto(obj, campo, idioma):
    """Valor de `campo` para un cliente en `idioma` (emails: no hay request)."""
    if es_ingles(idioma) and getattr(obj, 'traduccion_en_aprobada', True):
        valor = getattr(obj, f'{campo}_en', None)
        if valor:
            return valor
    return getattr(obj, f'{campo}_es')


def mostrar_aprobado(objs, request, aprobado=None):
    """Para el público en inglés, deja en español los objetos sin traducción aprobada.

    Cambia los valores solo en memoria (las vistas públicas no guardan). El staff
    ve los borradores en inglés para revisarlos en el sitio. `aprobado` permite
    heredar la aprobación del padre (los días del itinerario siguen a su tour).
    """
    if not es_ingles() or (request.user.is_authenticated and request.user.is_staff):
        return objs
    for obj in objs:
        ok = aprobado if aprobado is not None else getattr(obj, 'traduccion_en_aprobada', True)
        if not ok:
            for campo in CAMPOS.get(type(obj).__name__, ()):
                setattr(obj, campo, getattr(obj, f'{campo}_es'))
    return objs
