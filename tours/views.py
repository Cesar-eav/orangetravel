import threading
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Tour, Reserva, BloqueoTour, TerceraEdad
from payments.models import Payment
import json
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML
from django.template.loader import render_to_string # Si prefieres usar archivos .html
from django.utils.html import strip_tags # Par
from datetime import date, timedelta
import os
import unicodedata
print("FLOW_API_BASE en Passenger:", os.getenv('FLOW_API_BASE'))
print("FLOW_API_KEY en Passenger:", os.getenv('FLOW_API_KEY'))

# Email del admin según el tour (keyword en el slug → destinatario)
EMAIL_POR_TOUR = {
    'atacama':   'BastianDiaz10@gmail.com',
    'cotacotani': 'BastianDiaz10@gmail.com',
    'surire': 'BastianDiaz10@gmail.com',
    'desde san pedro' : 'BastianDiaz10@gmail.com',
}

EMAIL_ADMIN_DEFAULT = 'info@orangetravel.cl'
CC_RESERVAS = 'reservas@orangetravel.cl'

TURISMO_AVENTURA_KEYWORDS = (
    'san pedro de atacama',
    'cotacotani',
    'surire',
    'suriplaza',
)

def es_turismo_aventura(nombre):
    nombre_normalizado = unicodedata.normalize('NFKD', nombre.lower())
    nombre_normalizado = ''.join(
        caracter for caracter in nombre_normalizado
        if not unicodedata.combining(caracter)
    )
    nombre_compacto = ''.join(
        caracter for caracter in nombre_normalizado
        if caracter.isalnum()
    )

    return any(
        palabra in nombre_normalizado or palabra.replace(' ', '') in nombre_compacto
        for palabra in TURISMO_AVENTURA_KEYWORDS
    )

def get_email_admin(reserva):
    nombre = reserva.tour.nombre.lower()
    for keyword, email in EMAIL_POR_TOUR.items():
        if keyword in nombre:
            return email
    return EMAIL_ADMIN_DEFAULT

# Create your views here.

def tours_home(request):
    
    tours = list(Tour.objects.filter(activo=True, es_prueba=False).select_related('precio'))
    aventura_tours = [tour for tour in tours if es_turismo_aventura(tour.nombre)]
    otros_tours = [tour for tour in tours if not es_turismo_aventura(tour.nombre)]

    return render (request, 'tours/tours_home.html', {
        'tours': tours,
        'otros_tours': otros_tours,
        'aventura_tours': aventura_tours,
    } )

def tercera_edad(request):
    pagina = TerceraEdad.get_solo()
    return render(request, 'tours/tercera_edad.html', {'pagina': pagina})

def tour(request, slug):

    try:
        tour = Tour.objects.get(slug=slug)
        
        # 2. Traemos datos de tablas relacionadas (Reverse Relationships)
        # Aunque no los veas en el modelo Tour, existen por la ForeignKey en las otras tablas
        galeria_fotos = tour.imagenes.all() # Relación inversa por defecto
        precios = tour.precio               # Relación inversa por defecto
        

        # 3. El Tipo de Tour es una relación directa (ForeignKey en Tour)
        tipo_de_tour = tour.tipo

        context = {
                'tour': tour,
                'fotos': galeria_fotos,
                'precios': precios,
                'categoria': tipo_de_tour,
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
        
        # 1. Validación del Tour
        try:
            tour = Tour.objects.get(id=data.get('tour_id'))
        except Tour.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'El tour no existe.'}, status=404)

        # 2. Validación de anticipación mínima (3 días desde hoy en zona horaria del servidor)
        try:
            fecha_reserva = date.fromisoformat(data.get('fecha'))
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'mensaje': 'Fecha inválida.'}, status=400)
        if fecha_reserva < date.today() + timedelta(days=3):
            return JsonResponse({'status': 'error', 'mensaje': 'Las reservas deben hacerse con al menos 2 días de anticipación.'}, status=400)

        # 3. Creación de la Reserva
        reserva = Reserva.objects.create(
            tour=tour,
            nombre_cliente=data.get('nombre'),
            email_cliente=data.get('email'),
            telefono_cliente=data.get('telefono'),
            fecha=data.get('fecha'),
            adultos=int(data.get('adultos', 1)),
            ninos=int(data.get('ninos', 0)),
            notas_internas=f"Solicitud web: {data.get('adultos')} ADL, {data.get('ninos')} CHD."
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
            'mensaje': '¡Solicitud recibida! Revisa tu correo.',
            'reserva_id': reserva.id
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)

def enviar_notificaciones_reserva(reserva):
    print(f"DEBUG: Iniciando envío de correos para la reserva {reserva.id}...") # Checkpoint 1

    # --- 1. CONFIGURACIÓN PARA EL CLIENTE ---
    asunto_cliente = f"🍊 Solicitud Recibida: {reserva.tour.nombre}"
    
    html_cliente = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
        <div style="background-color: #FF8C00; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Orange Travel</h1>
        </div>
        <div style="padding: 20px; color: #333;">
            <h2>¡Hola {reserva.nombre_cliente}!</h2>
            <p>Hemos recibido tu solicitud de reserva. Nuestro equipo la revisará y te contactará a la brevedad para confirmar la disponibilidad.</p>
            
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Tour:</strong> {reserva.tour.nombre}</p>
                <p><strong>Fecha:</strong> {reserva.fecha}</p>
                <p><strong>Pasajeros:</strong> {reserva.adultos} Adultos / {reserva.ninos} Niños</p>
                <p style="font-size: 18px; color: #FF8C00;"><strong>Total estimado: ${reserva.precio_total}</strong></p>
            </div>
            
            <p style="font-style: italic; color: #666;">* Estado actual: <strong>Pendiente de Confirmación</strong>.</p>
        </div>
        <div style="background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px;">
            Arica, Chile - ¡La ciudad de la eterna primavera!
        </div>
    </div>
    """

    # --- 2. CONFIGURACIÓN PARA EL ADMIN (TÚ) ---
    asunto_admin = f"🚨 NUEVA RESERVA - {reserva.nombre_cliente}"
    
    # Limpiamos el teléfono para el link de WhatsApp
    tel_limpio = reserva.telefono_cliente.replace('+', '').replace(' ', '')
    
    dominio = settings.SITE_URL

    html_admin = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 2px solid #FF8C00; border-radius: 10px; padding: 20px;">
        <h2 style="color: #FF8C00;">NUEVA SOLICITUD WEB</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><strong>Cliente:</strong></td><td>{reserva.nombre_cliente}</td></tr>
            <tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><strong>Tour:</strong></td><td>{reserva.tour.nombre}</td></tr>
            <tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><strong>Fecha:</strong></td><td>{reserva.fecha}</td></tr>
            <tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><strong>WhatsApp:</strong></td>
                <td><a href="https://wa.me/{tel_limpio}" style="color: #25D366; font-weight: bold; text-decoration: none;">📱 {reserva.telefono_cliente}</a></td>
            </tr>
            <tr style="border-bottom: 1px solid #eee;"><td style="padding: 8px;"><strong>Email:</strong></td><td>{reserva.email_cliente}</td></tr>
        </table>
        
        <div style="margin-top: 25px; text-align: center;">
            <p style="color: #666; font-size: 12px;">Link generado desde: {dominio}</p>
            <a href="{dominio}/admin/tours/reserva/{reserva.id}/change/" 
            style="background-color: #333; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
            Ver en Panel Admin
            </a>
        </div>
    </div>
    """

    try:
        print(f"DEBUG: Intentando conectar con SMTP: {settings.EMAIL_HOST}") # Checkpoint 2
        # Enviar al Cliente
        msg_cli = EmailMultiAlternatives(asunto_cliente, "Solicitud recibida.", settings.DEFAULT_FROM_EMAIL, [reserva.email_cliente])
        msg_cli.attach_alternative(html_cliente, "text/html")
        msg_cli.send()
        print("DEBUG: Correo cliente enviado con éxito.") # Checkpoint 3

        # Enviar al Admin (destinatario según el tour)
        email_admin = get_email_admin(reserva)
        cc_admin = [CC_RESERVAS] if email_admin != EMAIL_ADMIN_DEFAULT else []
        print(f"DEBUG: 📧 Notificación admin → {email_admin} cc={cc_admin} (tour: {reserva.tour.nombre})")
        msg_adm = EmailMultiAlternatives(asunto_admin, "Nueva reserva recibida.", settings.DEFAULT_FROM_EMAIL, [email_admin], cc=cc_admin)
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()
        print("DEBUG: Correo admin enviado con éxito.") # Checkpoint 4
        
    except Exception as e:
        print(f"Error enviando correos: {e}")

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
