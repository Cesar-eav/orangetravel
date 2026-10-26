from modeltranslation.translator import TranslationOptions, register

from .models import Nosotros


@register(Nosotros)
class NosotrosTranslationOptions(TranslationOptions):
    fields = ('contenido',)
