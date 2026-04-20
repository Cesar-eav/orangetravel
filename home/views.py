from django.shortcuts import render, redirect
from tours.models import Tour
from blog.models import Post
from .models import Nosotros
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML

# Create your views here.

def home(request):

    tours = Tour.objects.filter(destacado=True, activo=True).select_related('precio')
    posts = Post.objects.filter(publicado=True).order_by('-fecha_creacion')

    return render(request, 'home/index.html',{
        'tours': tours,
        'posts': posts
    })

def nosotros(request):
    nosotros = Nosotros.get_solo()
    return render(request, 'home/nosotros.html', {'nosotros': nosotros})

def contacto(request):
    return render(request,'home/contacto.html' )

def devoluciones(request):
    return render(request,'home/politica_devoluciones.html' )   

#FORMULARIO DE CONTACTO
def contacto_send_email(request):
    if request.method == 'POST':

        tel_limpio = request.POST.get('phone').replace('+', '').replace(' ', '')
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        asunto_tipo = request.POST.get('asunto')
        mensaje_user = request.POST.get('mensaje')


        html_admin = f"""
        <div style="border: 2px solid #FF8C00; padding: 20px; font-family: sans-serif;">
            <h2 style="color: #FF8C00;">Gracias por contactarnos</h2>
            <p><strong>Cliente:</strong> {nombre}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Telefono:</strong> {phone}</p>

            <p><strong>Asunto:</strong> {asunto_tipo}</p>
            <p><strong>Mensaje:</strong> {mensaje_user}</p>
    
            
        </div>
        """
        #<p><a href="https://wa.me/{tel_limpio}" style="color: #25D366; font-weight: bold;">📱 Contactar por WhatsApp</a></p>
        try:
            msg_adm = EmailMultiAlternatives(
            subject=f"🥳 CONTACTO WEB - {nombre}",
            body="Nuevo contacto",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["cesar.eav@gmail.com"] # Tu correo autorizado en Sandbox
            )
            msg_adm.attach_alternative(html_admin, "text/html")
            msg_adm.send()
            
        except Exception as e:

            print(f"DEBUG ERROR EMAIL: {e}")
            messages.error(request, f"Hubo un problema al enviar el emial.")
        
        return redirect('home')
    
    return render(request, 'home/index.html') 