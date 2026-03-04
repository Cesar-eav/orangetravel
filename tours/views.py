from django.shortcuts import render
from .models import Tour

# Create your views here.

def index(request):

    tours = Tour.objects.all().select_related('precio')

    return render(request, 'home/index.html',{
        'tours': tours
    })