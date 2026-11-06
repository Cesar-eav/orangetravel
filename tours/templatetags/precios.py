from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un monto en pesos chilenos con punto de miles: 18000 -> 18.000."""
    try:
        return f'{int(valor):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return valor


@register.filter
def precio(valor):
    """Precio para el público según el idioma activo: «$18.000» en español, «$18,000 CLP» en inglés.

    En inglés se agrega CLP para que no se lea como dólares, con coma de miles.
    """
    try:
        monto = int(valor)
    except (TypeError, ValueError):
        return valor
    if (get_language() or '').startswith('en'):
        return f'${monto:,} CLP'
    return f'${monto:,}'.replace(',', '.')
