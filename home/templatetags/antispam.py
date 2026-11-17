"""{% antispam_campos %}: honeypot, marca de tiempo firmada y widget de Turnstile (home/antispam.py)."""
from django import template
from django.conf import settings
from django.utils.translation import get_language

from home import antispam

register = template.Library()


@register.inclusion_tag('home/_antispam.html')
def antispam_campos():
    return {
        'campo_honeypot': antispam.CAMPO_HONEYPOT,
        'campo_tiempo': antispam.CAMPO_TIEMPO,
        'marca_tiempo': antispam.marca_tiempo(),
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'idioma': (get_language() or 'es')[:2],
    }


@register.simple_tag
def antispam_marca_tiempo():
    """Solo la marca firmada, para formularios en Vue (data-antispam-ts)."""
    return antispam.marca_tiempo()
