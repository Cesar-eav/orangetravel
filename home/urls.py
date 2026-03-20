from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('nosotros', views.nosotros, name='nosotros'),
    path('contacto_formulario/', views.contacto_send_email, name='contacto_formulario'),
    path('contacto/', views.contacto, name='contacto')


]
