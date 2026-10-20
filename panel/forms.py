import html
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import strip_tags
from django.utils.text import slugify

from blog.models import ImagenPost, Post
from home.models import MaintenanceMode, Nosotros, SitioIngles
from tours.models import YOUTUBE_REGEX, BloqueoTour, Cotizacion, ItinerarioDia, PrecioTour, Reserva, TerceraEdad, TipoTour, Tour, Zona


class PanelLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                "Esta cuenta no tiene acceso al panel.", code='no_staff'
            )


class ReservaGestionForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ('estado', 'notas_internas')
        widgets = {'notas_internas': forms.Textarea(attrs={'rows': 4})}


class CotizacionGestionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ('atendida',)


class InglesMixin:
    """Etiqueta los campos <campo>_en como «<etiqueta> (inglés)». Son opcionales:
    vacíos, el sitio en inglés muestra el texto en español."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            if nombre.endswith('_en'):
                base = self.fields.get(nombre[:-3])
                campo.label = f"{base.label if base else campo.label} (inglés)"
                campo.required = False


def _texto_visible(html_str):
    """Texto de un campo CKEditor sin etiquetas ni &nbsp; (para detectar «vacío»)."""
    return html.unescape(strip_tags(html_str or '')).replace('\xa0', ' ').strip()


class TourForm(InglesMixin, forms.ModelForm):
    # La validación la hace el servidor (el <form> lleva novalidate): un campo oculto por
    # CKEditor con «required» bloquearía el envío sin mostrar ningún mensaje.
    use_required_attribute = False

    class Meta:
        model = Tour
        fields = (
            'nombre', 'slug', 'tipo', 'zona', 'imagen_principal', 'mapa', 'itinerario', 'incluye',
            'video_youtube', 'activo', 'destacado', 'es_prueba',
            'nombre_en', 'itinerario_en', 'incluye_en', 'traduccion_en_aprobada',
        )
        help_texts = {
            'slug': 'Es la dirección web del tour. Se genera sola desde el nombre.',
            'video_youtube': 'Enlace de YouTube (youtube.com/watch?v=… o youtu.be/…). Opcional.',
            'incluye': 'Opcional.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Cambiar el slug de un tour publicado rompe sus enlaces: se desbloquea a propósito.
            self.fields['slug'].widget.attrs['readonly'] = True
            self.fields['slug'].help_text = 'Cambiarla rompe los enlaces ya compartidos de este tour.'
        else:
            self.fields['slug'].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            return slug
        base = slugify(self.cleaned_data.get('nombre', ''))[:240] or 'tour'
        candidato, n = base, 2
        while Tour.objects.filter(slug=candidato).exists():
            candidato, n = f'{base}-{n}', n + 1
        return candidato

    def clean_itinerario(self):
        valor = self.cleaned_data.get('itinerario')
        if not _texto_visible(valor):
            raise forms.ValidationError('Escribe el resumen del tour.')
        return valor

    def clean_video_youtube(self):
        url = self.cleaned_data.get('video_youtube')
        if url and not re.search(YOUTUBE_REGEX, url):
            raise forms.ValidationError(
                'No parece un enlace de YouTube. Usa youtube.com/watch?v=… o youtu.be/…'
            )
        return url


class ItinerarioDiaForm(InglesMixin, forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = ItinerarioDia
        fields = ('orden', 'titulo', 'descripcion', 'titulo_en', 'descripcion_en')
        widgets = {
            'orden': forms.HiddenInput(),
            'titulo': forms.TextInput(attrs={'placeholder': 'Título'}),
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'titulo_en': forms.TextInput(attrs={'placeholder': 'Título en inglés (opcional)'}),
            'descripcion_en': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Descripción en inglés (opcional)'}),
        }

    def has_changed(self):
        # «orden» lo rellena el JS en cada fila: una fila nueva sin texto debe ignorarse.
        return bool({'titulo', 'descripcion', 'titulo_en', 'descripcion_en'} & set(self.changed_data))


ItinerarioDiaFormSet = forms.inlineformset_factory(
    Tour, ItinerarioDia, form=ItinerarioDiaForm, extra=0, can_delete=True,
)


class PrecioTourForm(forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = PrecioTour
        fields = ('valor_adulto', 'tiene_precio_nino', 'valor_nino')

    def clean(self):
        data = super().clean()
        adulto, nino = data.get('valor_adulto'), data.get('valor_nino')
        if adulto is not None and adulto <= 0:
            self.add_error('valor_adulto', 'El precio debe ser mayor que 0.')
        if data.get('tiene_precio_nino'):
            if not nino or nino < 0:
                self.add_error('valor_nino', 'Indica el precio del niño o desmarca la opción.')
        else:
            data['valor_nino'] = 0
        return data


class ImagenGaleriaForm(forms.Form):
    imagen = forms.ImageField()


class TipoTourForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = TipoTour
        fields = ('nombre', 'descripcion', 'nombre_en', 'descripcion_en')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3}), 'descripcion_en': forms.Textarea(attrs={'rows': 3})}


class ZonaForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = Zona
        fields = ('nombre', 'slug', 'descripcion', 'imagen', 'orden', 'nombre_en', 'descripcion_en')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3}), 'descripcion_en': forms.Textarea(attrs={'rows': 3})}
        help_texts = {
            'slug': 'Aparece en la dirección del filtro (/tours/?zona=…). Se genera sola desde el nombre.',
            'descripcion': 'Se muestra en /tours/ al elegir esta zona. Separa los párrafos con una línea en blanco.',
            'imagen': 'Se muestra junto al nombre en el filtro de /tours/ (p. ej. el geoglifo del Norte Grande). Mejor un PNG con fondo transparente.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('nombre', ''))[:110] or 'zona'
        if Zona.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe una zona con esta dirección.')
        return slug


CUERPO_MAX = 10000  # caracteres de texto visible (sin etiquetas HTML)


class PostForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = Post
        fields = (
            'titulo', 'extracto', 'contenido', 'imagen_portada',
            'video_youtube', 'publicado',
            'titulo_en', 'extracto_en', 'contenido_en', 'traduccion_en_aprobada',
        )
        widgets = {'extracto': forms.Textarea(attrs={'rows': 3}), 'extracto_en': forms.Textarea(attrs={'rows': 3})}

    def clean_contenido(self):
        return self._validar_cuerpo('contenido')

    def clean_contenido_en(self):
        return self._validar_cuerpo('contenido_en')

    def _validar_cuerpo(self, campo):
        contenido = self.cleaned_data[campo] or ''
        largo = len(html.unescape(strip_tags(contenido)).strip())
        if largo > CUERPO_MAX:
            raise forms.ValidationError(
                f'El cuerpo tiene {largo} caracteres; el máximo es {CUERPO_MAX}.'
            )
        return contenido

    def _slug_unico(self):
        base = slugify(self.cleaned_data['titulo'])[:240] or 'resena'
        candidato, n = base, 2
        others = Post.objects.exclude(pk=self.instance.pk)
        while others.filter(slug=candidato).exists():
            candidato, n = f'{base}-{n}', n + 1
        return candidato

    def save(self, commit=True):
        # El slug se genera solo al crear; al editar se conserva para no romper enlaces.
        if not self.instance.slug:
            self.instance.slug = self._slug_unico()
        return super().save(commit)


class ImagenPostForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = ImagenPost
        fields = ('imagen', 'despues_del_parrafo', 'caption', 'caption_en', 'orden')


ImagenPostFormSet = forms.inlineformset_factory(
    Post, ImagenPost, form=ImagenPostForm, extra=1, can_delete=True,
)


class BloqueoForm(forms.ModelForm):
    class Meta:
        model = BloqueoTour
        fields = ('tour', 'fecha', 'motivo')
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean(self):
        data = super().clean()
        if data.get('tour') and data.get('fecha') and BloqueoTour.objects.filter(
            tour=data['tour'], fecha=data['fecha']
        ).exists():
            raise forms.ValidationError('Esa fecha ya está bloqueada para este tour.')
        return data


class NosotrosForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = Nosotros
        fields = ('contenido', 'contenido_en')


class TerceraEdadForm(InglesMixin, forms.ModelForm):
    class Meta:
        model = TerceraEdad
        fields = ('contenido', 'contenido_en')


class MantencionForm(forms.ModelForm):
    class Meta:
        model = MaintenanceMode
        fields = ('activo', 'mensaje')


class SitioInglesForm(forms.ModelForm):
    class Meta:
        model = SitioIngles
        fields = ('publico',)
