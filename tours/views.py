from django.shortcuts import render

# Create your views here.

def prueba_tailwind(request):
    return render(request, 'tours/prueba.html')
