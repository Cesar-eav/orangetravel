from django.shortcuts import render
from tours.models import Tour

# Create your views here.

def home(request):

    tours = Tour.objects.filter(destacado=True).select_related('precio')

    return render(request, 'home/index.html',{
        'tours': tours
    })
