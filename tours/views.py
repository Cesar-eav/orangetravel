from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Tour

# Create your views here.

def tours_home(request):
    
    tours = Tour.objects.all().select_related('precio')

    return render (request, 'tours/tours_home.html', {
        'tours' : tours
    } )

def tour(request, slug):

    try:
        tour = Tour.objects.get(slug=slug)
        return HttpResponse(f"<pre>{tour.__dict__}</pre>")
        
        # 2. Traemos datos de tablas relacionadas (Reverse Relationships)
        # Aunque no los veas en el modelo Tour, existen por la ForeignKey en las otras tablas
        galeria_fotos = tour.imagenes # Relación inversa por defecto
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
