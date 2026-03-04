from django.shortcuts import render
from .models import Tour

# Create your views here.

def tours_home(request):
    
    tours = Tour.objects.all().select_related('precio')

    return render (request, 'tours/tours_home.html', {
        'tours' : tours
    } )
