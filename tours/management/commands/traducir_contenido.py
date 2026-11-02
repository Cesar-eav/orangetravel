"""Traduce con DeepL al inglés el contenido guardado en la base de datos.

Solo llena campos <campo>_en vacíos (salvo --sobrescribir) y nunca marca
«traduccion_en_aprobada»: lo traducido queda como borrador hasta que alguien
lo revise y apruebe en /panel/.

    python manage.py traducir_contenido --simular     # cuántos textos y caracteres, sin llamar a DeepL
    python manage.py traducir_contenido               # traduce lo que falta
    python manage.py traducir_contenido --solo Tour   # un modelo
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tours.deepl import DeepLError, traducir

# (app, modelo, campos de texto plano, campos HTML de CKEditor)
MODELOS = [
    ('tours', 'Tour', ('nombre',), ('itinerario', 'incluye')),
    ('tours', 'ItinerarioDia', ('titulo', 'descripcion'), ()),
    ('tours', 'TipoTour', ('nombre', 'descripcion'), ()),
    ('tours', 'Zona', ('nombre', 'descripcion'), ()),
    ('tours', 'TerceraEdad', (), ('contenido',)),
    ('blog', 'Post', ('titulo', 'extracto'), ('contenido',)),
    ('blog', 'ImagenPost', ('caption',), ()),
    ('home', 'Nosotros', (), ('contenido',)),
]


class Command(BaseCommand):
    help = 'Traduce al inglés con DeepL los campos _en vacíos (quedan sin aprobar).'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='No llama a DeepL: solo cuenta textos y caracteres.')
        parser.add_argument('--sobrescribir', action='store_true', help='Retraduce también los campos _en que ya tienen texto.')
        parser.add_argument('--solo', help='Nombre de un modelo (Tour, Post, Zona...).')

    def handle(self, *args, simular, sobrescribir, solo, **opts):
        total_textos = total_chars = 0
        for app, modelo, planos, htmls in MODELOS:
            if solo and solo.lower() != modelo.lower():
                continue
            Model = apps.get_model(app, modelo)
            objetos = list(Model.objects.all())
            for campos, es_html in ((planos, False), (htmls, True)):
                for campo in campos:
                    pendientes = [
                        o for o in objetos
                        if (getattr(o, f'{campo}_es') or '').strip()
                        and (sobrescribir or not (getattr(o, f'{campo}_en') or '').strip())
                    ]
                    if not pendientes:
                        continue
                    textos = [getattr(o, f'{campo}_es') for o in pendientes]
                    chars = sum(len(t) for t in textos)
                    total_textos += len(textos)
                    total_chars += chars
                    self.stdout.write(f'{modelo}.{campo}: {len(textos)} textos, {chars} caracteres')
                    if simular:
                        continue
                    try:
                        traducidos = traducir(textos, es_html=es_html)
                    except DeepLError as e:
                        raise CommandError(str(e))
                    with transaction.atomic():
                        for o, t in zip(pendientes, traducidos):
                            setattr(o, f'{campo}_en', t)
                            o.save(update_fields=[f'{campo}_en'])
        accion = 'Por traducir' if simular else 'Traducidos'
        self.stdout.write(self.style.SUCCESS(f'{accion}: {total_textos} textos, {total_chars} caracteres.'))
        if not simular and total_textos:
            self.stdout.write('Quedan sin aprobar: revísalos y apruébalos en /panel/.')
