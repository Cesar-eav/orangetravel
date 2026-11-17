import logging

from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.translation import gettext as _, get_language
from tours.models import Tour
from blog.models import Post
from .models import Nosotros
from tours.traduccion import mostrar_aprobado
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives

from . import antispam

logger = logging.getLogger(__name__)

# Create your views here.

def renovacion(request):
    return render(request, 'home/renovacion.html')

def home(request):

    tours = Tour.objects.filter(destacado=True, activo=True, es_prueba=False).select_related('precio')
    posts = Post.objects.filter(publicado=True).order_by('-fecha_creacion')

    return render(request, 'home/index.html',{
        'tours': mostrar_aprobado(list(tours), request),
        'posts': mostrar_aprobado(list(posts), request),
    })

def nosotros(request):
    nosotros = Nosotros.get_solo()
    return render(request, 'home/nosotros.html', {'nosotros': nosotros})

def contacto(request):
    return render(request,'home/contacto.html' )

def devoluciones(request):
    return render(request,'home/politica_devoluciones.html' )

def otros_servicios(request):
    return render(request, 'home/otros_servicios.html')

# FORMULARIO DE CONTACTO (home y /contacto/): email a info@, protegido con home/antispam.py
ASUNTOS_CONTACTO = {
    'consulta': 'Consulta General',
    'reserva': 'Problemas con una Reserva',
    'tour_especial': 'Tour Personalizado / Grupal',
    'otro': 'Otro',
}
ORIGENES_CONTACTO = {'home': 'home', 'contacto': 'contacto'}  # lista blanca para el redirect


@require_POST
def contacto_send_email(request):
    destino = reverse(ORIGENES_CONTACTO.get(request.POST.get('origen'), 'contacto')) + '#formulario-contacto'
    exito = _("¡Gracias! Recibimos tu mensaje y te responderemos a la brevedad.")

    motivo = antispam.revisar(request, request.POST, clave='contacto', maximo=5, ventana=3600)
    if motivo in antispam.MOTIVOS_SILENCIOSOS:
        messages.success(request, exito)  # al bot se le responde igual que a una persona
        return redirect(destino)
    if motivo == 'expirado':
        messages.error(request, _("La página estuvo abierta mucho tiempo. Recárgala y vuelve a enviar tu mensaje."))
        return redirect(destino)
    if motivo == 'limite':
        messages.error(request, _("Recibimos varios mensajes desde tu conexión. Intenta más tarde o escríbenos por WhatsApp."))
        return redirect(destino)
    if motivo == 'turnstile':
        messages.error(request, _("No pudimos verificar que no eres un robot. Inténtalo de nuevo."))
        return redirect(destino)

    nombre = (request.POST.get('nombre') or '').strip()[:100]
    email = (request.POST.get('email') or '').strip()[:254]
    telefono = (request.POST.get('phone') or '').strip()[:20]
    asunto = ASUNTOS_CONTACTO.get(request.POST.get('asunto'), ASUNTOS_CONTACTO['otro'])
    mensaje = (request.POST.get('mensaje') or '').strip()[:3000]
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, _("Email inválido."))
        return redirect(destino)
    if len(nombre) < 2 or not mensaje:
        messages.error(request, _("Completa tu nombre y tu mensaje."))
        return redirect(destino)

    # Template con autoescape: el HTML o los links que mande alguien salen como texto.
    html_admin = render_to_string('emails/contacto_admin.html', {
        'nombre': nombre, 'email': email, 'telefono': telefono, 'asunto': asunto,
        'mensaje': mensaje, 'idioma': (get_language() or 'es')[:2],
    })
    try:
        msg_adm = EmailMultiAlternatives(
            subject=f"🥳 CONTACTO WEB - {nombre}",
            body=f"Nuevo contacto de {nombre} <{email}>:\n\n{mensaje}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["info@orangetravel.cl"],
            reply_to=[email],
        )
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()
    except Exception:
        logger.exception("No se pudo enviar el email del formulario de contacto")
        messages.error(request, _("Hubo un problema al enviar tu mensaje. Inténtalo de nuevo o escríbenos por WhatsApp."))
        return redirect(destino)

    messages.success(request, exito)
    return redirect(destino)
