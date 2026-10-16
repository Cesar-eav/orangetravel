from django import template

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un monto en pesos chilenos con punto de miles: 18000 -> 18.000."""
    try:
        return f'{int(valor):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return valor
