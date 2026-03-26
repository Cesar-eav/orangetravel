from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Tour, Reserva, BloqueoTour
import json
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML
from django.template.loader import render_to_string # Si prefieres usar archivos .html
from django.utils.html import strip_tags # Par

# Create your views here.

def tours_home(request):
    
    tours = Tour.objects.all().select_related('precio')

    return render (request, 'tours/tours_home.html', {
        'tours' : tours
    } )

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
        
        # 1. Validación de existencia del Tour
        try:
            # Importante: Asegúrate que desde Vue envías 'tour_id'
            tour = Tour.objects.get(id=data.get('tour_id'))
        except Tour.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'El tour seleccionado no existe.'}, status=404)

        # 2. Creación de la Reserva
        # El método save() de tu modelo calculará automáticamente el precio_total
        reserva = Reserva.objects.create(
            tour=tour,
            nombre_cliente=data.get('nombre'),
            email_cliente=data.get('email'),
            telefono_cliente=data.get('telefono'),
            fecha=data.get('fecha'),
            adultos=int(data.get('adultos', 1)),
            ninos=int(data.get('ninos', 0)),
            notas_internas=f"Solicitud web. Pasajeros: {data.get('adultos')} ADL, {data.get('ninos')} CHD."
        )

        # 3. Lógica de Notificaciones por Email
        # Llamamos a la función auxiliar definida abajo
        enviar_notificaciones_reserva(reserva)
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Tu solicitud ha sido recibida. Revisa tu correo.',
            'reserva_id': reserva.id,
            'total': reserva.precio_total 
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': f"Error en el servidor: {str(e)}"}, status=500)


def enviar_notificaciones_reserva(reserva):
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
            <a href="http://127.0.0.1:8000/admin/tours/reserva/{reserva.id}/change/" 
               style="background-color: #333; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
               Ver en Panel Admin
            </a>
        </div>
    </div>
    """

    try:
        # Enviar al Cliente
        msg_cli = EmailMultiAlternatives(asunto_cliente, "Solicitud recibida.", settings.DEFAULT_FROM_EMAIL, [reserva.email_cliente])
        msg_cli.attach_alternative(html_cliente, "text/html")
        msg_cli.send()

        # Enviar al Admin
        msg_adm = EmailMultiAlternatives(asunto_admin, "Nueva reserva recibida.", settings.DEFAULT_FROM_EMAIL, ['cesar.eav@gmail.com'])
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()

    except Exception as e:
        print(f"Error enviando correos: {e}")

def dias_bloqueados_api(request, tour_id):
# 1. Traer fechas de reservas confirmadas (o pagadas)
    reservas = Reserva.objects.filter(
        tour_id=tour_id, 
        estado__in=['Confirmada', 'Realizada'] # Ajusta según tus estados
    ).values_list('fecha', flat=True)

    # 2. Traer fechas de bloqueos manuales
    bloqueos_manuales = BloqueoTour.objects.filter(
        tour_id=tour_id
    ).values_list('fecha', flat=True)

    # Combinamos y formateamos a string 'YYYY-MM-DD'
    fechas_finales = [f.strftime('%Y-%m-%d') for f in list(reservas) + list(bloqueos_manuales)]
    
    return JsonResponse({'bloqueados': fechas_finales})