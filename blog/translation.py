from modeltranslation.translator import TranslationOptions, register

from .models import ImagenPost, Post


@register(Post)
class PostTranslationOptions(TranslationOptions):
    fields = ('titulo', 'extracto', 'contenido')


@register(ImagenPost)
class ImagenPostTranslationOptions(TranslationOptions):
    fields = ('caption',)
