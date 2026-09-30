from django import forms
from django.contrib.auth.forms import AuthenticationForm

from tours.models import Reserva


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
