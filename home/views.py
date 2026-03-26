from django.shortcuts import render, redirect
from tours.models import Tour
from blog.models import Post
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages

# Create your views here.

def home(request):

    tours = Tour.objects.filter(destacado=True).select_related('precio')
    posts = Post.objects.filter(publicado=True).order_by('-fecha_creacion')

    return render(request, 'home/index.html',{
        'tours': tours,
        'posts': posts
    })

def nosotros(request):

    return render(request, 'home/nosotros.html')

def contacto(request):
    return render(request,'home/contacto.html' )

def contacto_send_email(request):
    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        asunto_tipo = request.POST.get('asunto')
        mensaje_user = request.POST.get('mensaje')

        cuerpo_correo = f"""
        Has recibido un nuevo mensaje de contacto:

        Nombre: {nombre}
        Email: {email}
        Teléfono: {phone}
        Tipo de Consulta: {asunto_tipo}

        Mensaje:
        {mensaje_user}
        """

        try:
            send_mail(
                subject = f"WEB: {asunto_tipo.upper()} - {nombre}",
                message = cuerpo_correo,
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_CONTACTO_RECIBIDO], 
                fail_silently=False,
            )
            messages.success(request, "¡Gracias! Te responderemos a la brevedad.")
            print(f"TODO ARIBA ARIBA")
        except Exception as e:
            print(f"DEBUG ERROR EMAIL: {e}")
            messages.error(request, f"Hubo un problema al enviar el emial.")
        
        return redirect('home')
    
    return render(request, 'home/index.html') 