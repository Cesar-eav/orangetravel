from modeltranslation.translator import TranslationOptions, register

from .models import ItinerarioDia, TerceraEdad, TipoTour, Tour, Zona


@register(Tour)
class TourTranslationOptions(TranslationOptions):
    fields = ('nombre', 'itinerario', 'incluye')


@register(ItinerarioDia)
class ItinerarioDiaTranslationOptions(TranslationOptions):
    fields = ('titulo', 'descripcion')


@register(TipoTour)
class TipoTourTranslationOptions(TranslationOptions):
    fields = ('nombre', 'descripcion')


@register(Zona)
class ZonaTranslationOptions(TranslationOptions):
    fields = ('nombre', 'descripcion')


@register(TerceraEdad)
class TerceraEdadTranslationOptions(TranslationOptions):
    fields = ('contenido',)
