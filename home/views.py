from django.shortcuts import render
from tours.models import Tour

# Create your views here.

def home(request):

    tours = Tour.objects.all().select_related('precio')

    return render(request, 'home/index.html',{
        'tours': tours
    })
