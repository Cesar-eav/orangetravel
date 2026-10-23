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


# modeltranslation copia unique=True de «nombre» a cada idioma. En inglés dos nombres
# distintos pueden traducirse igual («Zona Sur» y «Zona Austral» → «Southern Region»),
# así que la unicidad queda solo en nombre_es.
for _modelo in (TipoTour, Zona):
    _campo = _modelo._meta.get_field('nombre_en')
    _campo._unique = False
    _campo._field_options_kwargs = {'unique': False}  # para que las migraciones lo vean
