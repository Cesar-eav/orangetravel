import html

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import strip_tags
from django.utils.text import slugify

from blog.models import ImagenPost, Post
from tours.models import BloqueoTour, PrecioTour, Reserva, TipoTour, Tour


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


class TourForm(forms.ModelForm):
    class Meta:
        model = Tour
        fields = (
            'nombre', 'slug', 'tipo', 'imagen_principal', 'itinerario', 'incluye',
            'video_youtube', 'activo', 'destacado', 'es_prueba',
        )
        widgets = {'incluye': forms.Textarea(attrs={'rows': 5})}


class PrecioTourForm(forms.ModelForm):
    class Meta:
        model = PrecioTour
        fields = ('valor_adulto', 'tiene_precio_nino', 'valor_nino')

    def clean(self):
        data = super().clean()
        if data.get('tiene_precio_nino') and not data.get('valor_nino'):
            self.add_error('valor_nino', 'Indica el precio del niño o desmarca la opción.')
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
