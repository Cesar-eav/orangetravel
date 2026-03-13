from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Tour, Reserva
import json

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
        precios = tour.precio        # Relación inversa por defecto
        

        # 3. El Tipo de Tour es una relación directa (ForeignKey en Tour)
        tipo_de_tour = tour.tipo

        context = {
                'tour': tour,
                'fotos': galeria_fotos,
                'lista_precios': precios,
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
        
        # 1. Buscamos el tour (puedes pasarlo desde Vue)
        tour = Tour.objects.get(id=data.get('tour_id'))
        
        # 2. Creamos la instancia de Reserva
        reserva = Reserva.objects.create(
            tour=tour,
            nombre_cliente=data.get('nombre'),
            email_cliente=data.get('email'),
            telefono_cliente=data.get('telefono'),
            fecha=data.get('fecha'),
            adultos=data.get('adultos', 1),
            ninos=data.get('ninos', 0),
            notas_internas="Solicitud desde la web."
        )
        
        # Aquí podrías agregar: send_mail(...) para avisar a Orange Travel
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Solicitud recibida correctamente',
            'reserva_id': reserva.id
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)