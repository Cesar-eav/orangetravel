import html
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import strip_tags
from django.utils.text import slugify

from blog.models import ImagenPost, Post
from home.models import MaintenanceMode, Nosotros
from tours.models import YOUTUBE_REGEX, BloqueoTour, ItinerarioDia, PrecioTour, Reserva, TerceraEdad, TipoTour, Tour


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


def _texto_visible(html_str):
    """Texto de un campo CKEditor sin etiquetas ni &nbsp; (para detectar «vacío»)."""
    return html.unescape(strip_tags(html_str or '')).replace('\xa0', ' ').strip()


class TourForm(forms.ModelForm):
    # La validación la hace el servidor (el <form> lleva novalidate): un campo oculto por
    # CKEditor con «required» bloquearía el envío sin mostrar ningún mensaje.
    use_required_attribute = False

    class Meta:
        model = Tour
        fields = (
            'nombre', 'slug', 'tipo', 'imagen_principal', 'mapa', 'itinerario', 'incluye',
            'video_youtube', 'activo', 'destacado', 'es_prueba',
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


class ItinerarioDiaForm(forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = ItinerarioDia
        fields = ('orden', 'titulo', 'descripcion')
        widgets = {
            'orden': forms.HiddenInput(),
            'titulo': forms.TextInput(attrs={'placeholder': 'Título'}),
            'descripcion': forms.Textarea(attrs={'rows': 5}),
        }

    def has_changed(self):
        # «orden» lo rellena el JS en cada fila: una fila nueva sin texto debe ignorarse.
        return bool({'titulo', 'descripcion'} & set(self.changed_data))


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


class TipoTourForm(forms.ModelForm):
    class Meta:
        model = TipoTour
        fields = ('nombre', 'descripcion')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


CUERPO_MAX = 10000  # caracteres de texto visible (sin etiquetas HTML)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = (
            'titulo', 'extracto', 'contenido', 'imagen_portada',
            'video_youtube', 'publicado',
        )
        widgets = {'extracto': forms.Textarea(attrs={'rows': 3})}

    def clean_contenido(self):
        contenido = self.cleaned_data['contenido']
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


class ImagenPostForm(forms.ModelForm):
    class Meta:
        model = ImagenPost
        fields = ('imagen', 'despues_del_parrafo', 'caption', 'orden')


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


class NosotrosForm(forms.ModelForm):
    class Meta:
        model = Nosotros
        fields = ('contenido',)


class TerceraEdadForm(forms.ModelForm):
    class Meta:
        model = TerceraEdad
        fields = ('contenido',)


class MantencionForm(forms.ModelForm):
    class Meta:
        model = MaintenanceMode
        fields = ('activo', 'mensaje')
