from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Tour, Reserva
import json
from django.core.mail import send_mail
from django.conf import settings

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
    """ Función auxiliar para enviar correos a cliente y admin """
    
    # Email para el Cliente
    asunto_cliente = f"🍊 Solicitud de Reserva: {reserva.tour.nombre}"
    mensaje_cliente = (
        f"Hola {reserva.nombre_cliente},\n\n"
        f"Hemos recibido tu solicitud para el tour {reserva.tour.nombre} el día {reserva.fecha}.\n"
        f"Detalles:\n- Adultos: {reserva.adultos}\n- Niños: {reserva.ninos}\n- Total estimado: ${reserva.precio_total}\n\n"
        f"Estado actual: PENDIENTE DE CONFIRMACIÓN. Nos contactaremos contigo vía WhatsApp o Email pronto."
    )
    
    # Email para el Administrador (Orange Travel)
    asunto_admin = f"🚨 NUEVA RESERVA - {reserva.nombre_cliente}"
    mensaje_admin = (
        f"Nueva solicitud recibida:\n\n"
        f"Cliente: {reserva.nombre_cliente}\n"
        f"Tour: {reserva.tour.nombre}\n"
        f"Fecha: {reserva.fecha}\n"
        f"WhatsApp: {reserva.telefono_cliente}\n"
        f"Email: {reserva.email_cliente}"
    )

    try:
        # Envío al cliente
        send_mail(
            asunto_cliente, 
            mensaje_cliente, 
            settings.DEFAULT_FROM_EMAIL, 
            [reserva.email_cliente],
            fail_silently=False
        )
        # Envío al admin (ajusta a tu correo real)
        send_mail(
            asunto_admin, 
            mensaje_admin, 
            settings.DEFAULT_FROM_EMAIL, 
            ['cesar.eav@gmail.com'],
            fail_silently=False
        )
    except Exception as e:
        # Esto imprimirá el error en la consola de Django si Mailgun falla
        print(f"Error enviando correos: {e}")