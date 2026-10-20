import threading
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Count
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.admin.views.decorators import staff_member_required
from .models import IDIOMAS, Tour, Reserva, BloqueoTour, TerceraEdad, Cotizacion, Zona
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from payments.models import Payment
import json
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML
from django.template.loader import render_to_string # Si prefieres usar archivos .html
from django.utils.html import strip_tags, escape # Par
from django.utils import translation
from django.utils.translation import gettext as _
from .traduccion import texto
from datetime import date
import os

# Email del admin según el tour (keyword en el nombre en español → destinatario)
EMAIL_POR_TOUR = {
    'atacama':   'BastianDiaz10@gmail.com',
    'cotacotani': 'BastianDiaz10@gmail.com',
    'surire': 'BastianDiaz10@gmail.com',
    'desde san pedro' : 'BastianDiaz10@gmail.com',
}

EMAIL_ADMIN_DEFAULT = 'info@orangetravel.cl'
CC_RESERVAS = ['reservas@orangetravel.cl', 'cesar.eav@gmail.com']

def idioma_cliente(data):
    """Idioma que envía Vue (el de la página); cualquier otro valor cae en español."""
    idioma = str(data.get('idioma') or '')[:2]
    return idioma if idioma in dict(IDIOMAS) else 'es'


def textos_reserva():
    """Textos de BookingApp.vue / CotizacionApp.vue, traducidos al idioma activo."""
    return {
        'reservarAhora': _("RESERVAR AHORA"),
        'reservaTuCupo': _("Reserva tu Cupo"),
        'avisoMinimo': _("Todo tour está sujeto a un número mínimo de participantes. En caso de no completarse, nos comunicaremos con usted para ofrecerle el cambio de fecha o el reembolso total de su pago."),
        'nombreCompleto': _("Nombre Completo"),
        'ejemploNombre': _("Ej: César Espinoza"),
        'fechaTour': _("Fecha del Tour"),
        'seleccionaFecha': _("Selecciona una fecha"),
        'publicoGeneral': _("Público General"),
        'adultos': _("Adultos"),
        'ninos': _("Niños"),
        'totalAPagar': _("Total a pagar:"),
        'enviando': _("Enviando..."),
        'solicitarReserva': _("SOLICITAR RESERVA"),
        'errorLinkPago': _("Error al generar el link de pago."),
        'errorServidorPagos': _("No se pudo contactar con el servidor de pagos."),
        'cotizarAhora': _("COTIZAR AHORA"),
        'solicitudEnviada': _("¡Solicitud enviada!"),
        'cerrar': _("CERRAR"),
        'solicitaCotizacion': _("Solicita tu Cotización"),
        'introCotizacion': _("Cuéntanos cuándo y con cuántas personas quieres viajar y te enviaremos una propuesta a tu medida."),
        'fechaTentativa': _("Fecha tentativa (opcional)"),
        'mensajeOpcional': _("Mensaje (opcional)"),
        'placeholderMensaje': _("Preferencias, dudas, alojamiento, etc."),
        'solicitarCotizacion': _("SOLICITAR COTIZACIÓN"),
        'errorEnvio': _("No se pudo enviar la solicitud. Intenta nuevamente."),
    }


def get_email_admin(reserva):
    # nombre_es y no nombre: con el inglés activo, nombre devuelve la traducción.
    nombre = reserva.tour.nombre_es.lower()
    for keyword, email in EMAIL_POR_TOUR.items():
        if keyword in nombre:
            return email
    return EMAIL_ADMIN_DEFAULT

# Create your views here.

def tours_home(request):
    tours = (
        Tour.objects.filter(activo=True, es_prueba=False)
        .select_related('precio', 'tipo', 'zona')
        .order_by('tipo__nombre', 'nombre')
    )
    # Solo las zonas con algún tour visible se ofrecen como filtro.
    zonas = (
        Zona.objects.filter(tours__activo=True, tours__es_prueba=False)
        .annotate(num_tours=Count('tours'))
    )
    return render(request, 'tours/tours_home.html', {'tours': tours, 'zonas': zonas})

def tercera_edad(request):
    pagina = TerceraEdad.get_solo()
    return render(request, 'tours/tercera_edad.html', {'pagina': pagina})

@ensure_csrf_cookie
def tour(request, slug):

    try:
        tour = Tour.objects.get(slug=slug)
        
        # 2. Traemos datos de tablas relacionadas (Reverse Relationships)
        # Aunque no los veas en el modelo Tour, existen por la ForeignKey en las otras tablas
        galeria_fotos = tour.imagenes.all() # Relación inversa por defecto
        precios = getattr(tour, 'precio', None)  # Los tours de cotización pueden no tener precio
        

        # 3. El Tipo de Tour es una relación directa (ForeignKey en Tour)
        tipo_de_tour = tour.tipo

        context = {
                'tour': tour,
                'fotos': galeria_fotos,
                'precios': precios,
                'dias': tour.dias.all(),
                'categoria': tipo_de_tour,
                'con_precio': tour.con_precio,
                'textos_reserva': textos_reserva(),
                # Enviamos una bandera para saber que estamos en modo aprendizaje
                'debug_mode': True 
            }

        return render (request, 'tours/tour.html', context) 
    
    except Tour.DoesNotExist:
        return redirect('home')

@require_POST
def crear_reserva(request):
    try:
        data = json.loads(request.body)
        idioma = idioma_cliente(data)
        translation.activate(idioma)  # mensajes de respuesta en el idioma de la página
        
        # 1. Validación del Tour
        try:
            tour = Tour.objects.get(id=data.get('tour_id'))
        except Tour.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': _('El tour no existe.')}, status=404)

        # 2. Validación de anticipación mínima: solo desde mañana (no se reserva para el mismo día)
        try:
            fecha_reserva = date.fromisoformat(data.get('fecha'))
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'mensaje': _('Fecha inválida.')}, status=400)
        if fecha_reserva <= date.today():
            return JsonResponse({'status': 'error', 'mensaje': _('Las reservas deben hacerse a partir del día siguiente.')}, status=400)

        # 3. Creación de la Reserva
        reserva = Reserva.objects.create(
            tour=tour,
            nombre_cliente=data.get('nombre'),
            email_cliente=data.get('email'),
            telefono_cliente=data.get('telefono'),
            fecha=data.get('fecha'),
            adultos=int(data.get('adultos', 1)),
            ninos=int(data.get('ninos', 0)),
            notas_internas=f"Solicitud web: {data.get('adultos')} ADL, {data.get('ninos')} CHD.",
            idioma=idioma,
        )

        # --- CAMBIO CLAVE AQUÍ ---
        # En lugar de llamar a la función directo, creamos un hilo (thread)
        # Esto dispara la función 'enviar_notificaciones_reserva' de fondo
        # y permite que el código siga a la siguiente línea (el return) al instante.
        email_thread = threading.Thread(target=enviar_notificaciones_reserva, args=(reserva,))
        email_thread.start() 
        # -------------------------
        
        return JsonResponse({
            'status': 'success',
            'mensaje': _('¡Solicitud recibida! Revisa tu correo.'),
            'reserva_id': reserva.id
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

def enviar_notificaciones_reserva(reserva):
    print(f"DEBUG: Iniciando envío de correos para la reserva {reserva.id}...") # Checkpoint 1

    # --- 1. CONFIGURACIÓN PARA EL CLIENTE (en su idioma) ---
    with translation.override(reserva.idioma):
        tour_nombre = texto(reserva.tour, 'nombre', reserva.idioma)
        asunto_cliente = _("🍊 Solicitud Recibida: %(tour)s") % {'tour': tour_nombre}
        html_cliente = render_to_string('emails/reserva_cliente.html', {'reserva': reserva, 'tour_nombre': tour_nombre})
        texto_cliente = _("Solicitud recibida.")

    # --- 2. CONFIGURACIÓN PARA EL ADMIN (TÚ), siempre en español ---
    asunto_admin = f"🚨 NUEVA RESERVA - {reserva.nombre_cliente}"
    
    # Limpiamos el teléfono para el link de WhatsApp
    tel_limpio = reserva.telefono_cliente.replace('+', '').replace(' ', '')
    
    dominio = settings.SITE_URL

    with translation.override('es'):
        html_admin = render_to_string('emails/reserva_admin.html', {
            'reserva': reserva, 'tel_limpio': tel_limpio, 'dominio': dominio,
        })

    try:
        print(f"DEBUG: Intentando conectar con SMTP: {settings.EMAIL_HOST}") # Checkpoint 2
        # Enviar al Cliente
        msg_cli = EmailMultiAlternatives(asunto_cliente, texto_cliente, settings.DEFAULT_FROM_EMAIL, [reserva.email_cliente])
        msg_cli.attach_alternative(html_cliente, "text/html")
        msg_cli.send()
        print("DEBUG: Correo cliente enviado con éxito.") # Checkpoint 3

        # Enviar al Admin (destinatario según el tour)
        email_admin = get_email_admin(reserva)
        cc_admin = [email for email in CC_RESERVAS if email != email_admin]
        print(f"DEBUG: 📧 Notificación admin → {email_admin} cc={cc_admin} (tour: {reserva.tour.nombre_es})")
        msg_adm = EmailMultiAlternatives(asunto_admin, "Nueva reserva recibida.", settings.DEFAULT_FROM_EMAIL, [email_admin], cc=cc_admin)
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()
        print("DEBUG: Correo admin enviado con éxito.") # Checkpoint 4
        
    except Exception as e:
        print(f"Error enviando correos: {e}")

@require_POST
def crear_cotizacion(request):
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'mensaje': _('Datos inválidos.')}, status=400)
    idioma = idioma_cliente(data)
    translation.activate(idioma)  # mensajes de respuesta en el idioma de la página

    try:
        tour = Tour.objects.get(id=data.get('tour_id'))
    except (Tour.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'mensaje': _('El tour no existe.')}, status=404)
    if tour.con_precio:
        return JsonResponse({'status': 'error', 'mensaje': _('Este tour se reserva con pago en línea, no por cotización.')}, status=400)

    nombre = (data.get('nombre') or '').strip()
    email = (data.get('email') or '').strip()
    telefono = (data.get('telefono') or '').strip()
    if len(nombre) < 3 or len(telefono) < 8:
        return JsonResponse({'status': 'error', 'mensaje': _('Completa tu nombre y teléfono.')}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'mensaje': _('Email inválido.')}, status=400)

    fecha_tentativa = None
    if data.get('fecha'):
        try:
            fecha_tentativa = date.fromisoformat(data.get('fecha'))
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'mensaje': _('Fecha inválida.')}, status=400)
        if fecha_tentativa <= date.today():
            return JsonResponse({'status': 'error', 'mensaje': _('La fecha tentativa debe ser futura.')}, status=400)

    try:
        adultos = max(int(data.get('adultos', 1)), 1)
        ninos = max(int(data.get('ninos', 0)), 0)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'mensaje': _('Cantidad de pasajeros inválida.')}, status=400)

    cotizacion = Cotizacion.objects.create(
        tour=tour,
        nombre=nombre[:100],
        email=email,
        telefono=telefono[:20],
        fecha_tentativa=fecha_tentativa,
        adultos=adultos,
        ninos=ninos,
        mensaje=(data.get('mensaje') or '').strip()[:2000],
        idioma=idioma,
    )

    threading.Thread(target=enviar_notificaciones_cotizacion, args=(cotizacion,)).start()

    return JsonResponse({
        'status': 'success',
        'mensaje': _('¡Solicitud recibida! Te enviaremos tu cotización a la brevedad.'),
        'cotizacion_id': cotizacion.id
    }, status=201)

def enviar_notificaciones_cotizacion(cotizacion):
    with translation.override(cotizacion.idioma):
        tour_nombre = texto(cotizacion.tour, 'nombre', cotizacion.idioma)
        asunto_cliente = _("🍊 Solicitud de cotización: %(tour)s") % {'tour': tour_nombre}
        html_cliente = render_to_string('emails/cotizacion_cliente.html', {'cotizacion': cotizacion, 'tour_nombre': tour_nombre})
        texto_cliente = _("Solicitud de cotización recibida.")

    asunto_admin = f"🧾 COTIZACIÓN: {cotizacion.tour.nombre_es} - {cotizacion.nombre}"
    tel_limpio = cotizacion.telefono.replace('+', '').replace(' ', '')
    dominio = settings.SITE_URL

    with translation.override('es'):
        html_admin = render_to_string('emails/cotizacion_admin.html', {
            'cotizacion': cotizacion, 'tel_limpio': tel_limpio, 'dominio': dominio,
        })

    try:
        msg_cli = EmailMultiAlternatives(asunto_cliente, texto_cliente, settings.DEFAULT_FROM_EMAIL, [cotizacion.email])
        msg_cli.attach_alternative(html_cliente, "text/html")
        msg_cli.send()

        email_admin = get_email_admin(cotizacion)
        cc_admin = [email for email in CC_RESERVAS if email != email_admin]
        print(f"DEBUG: 📧 Cotización {cotizacion.id} → {email_admin} cc={cc_admin} (tour: {cotizacion.tour.nombre_es})")
        msg_adm = EmailMultiAlternatives(asunto_admin, "Nueva solicitud de cotización.", settings.DEFAULT_FROM_EMAIL, [email_admin], cc=cc_admin, reply_to=[cotizacion.email])
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()
    except Exception as e:
        print(f"Error enviando correos de cotización: {e}")

def get_fechas_bloqueadas(request, tour_id):
    """
    Une los bloqueos manuales del Admin con las reservas existentes 
    para enviarlas al calendario de Vue.
    """
    # 1. Traer fechas de reservas confirmadas, realizadas o pendientes
    # Usamos .distinct() por si acaso para no enviar fechas duplicadas
    reservas = Payment.objects.filter(
        tour_id=tour_id, 
        status__in=['paid']
    ).values_list('reservation_date', flat=True).distinct()

    # 2. Traer fechas de bloqueos manuales (lo que haces desde el Admin)
    bloqueos_manuales = BloqueoTour.objects.filter(
        tour_id=tour_id
    ).values_list('fecha', flat=True).distinct()


    # 3. Combinamos ambas listas en un solo Set (para evitar duplicados)
    # y formateamos a string 'YYYY-MM-DD'
    todas_las_fechas = set(list(reservas) + list(bloqueos_manuales))
    
    # ISOformat o strftime('%Y-%m-%d') dan el mismo resultado: "2026-03-27"
    fechas_finales = [f.isoformat() for f in todas_las_fechas]
    
    # IMPORTANTE: La clave debe ser 'bloqueadas' para que coincida con tu Vue
    return JsonResponse({'bloqueadas': fechas_finales})


@staff_member_required
def get_pagos_activos_admin(request, tour_id):
    from django.db.models import Count, Sum

    agrupado = (
        Payment.objects.filter(
            tour_id=tour_id,
            status=Payment.STATUS_PAID,
            deleted_at__isnull=True,
        )
        .values('reservation_date')
        .annotate(
            cantidad=Count('id'),
            total_adultos=Sum('pax_adults'),
            total_ninos=Sum('pax_children'),
        )
        .order_by('reservation_date')
    )

    pagos = [
        {
            'fecha': p['reservation_date'].isoformat(),
            'cantidad': p['cantidad'],
            'pax': (p['total_adultos'] or 0) + (p['total_ninos'] or 0),
        }
        for p in agrupado
        if p['reservation_date']
    ]

    return JsonResponse({'tour_id': tour_id, 'pagos': pagos})
