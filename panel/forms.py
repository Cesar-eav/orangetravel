from django import forms
from django.contrib.auth.forms import AuthenticationForm

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
