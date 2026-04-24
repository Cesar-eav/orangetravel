from django.urls import path
from . import views


urlpatterns = [
    path('', views.renovacion, name='home'),
    path('nueva_web/', views.home, name='nueva_web'),
    path('nosotros', views.nosotros, name='nosotros'),
    path('contacto_formulario/', views.contacto_send_email, name='contacto_formulario'),
    path('contacto/', views.contacto, name='contacto'),
    path('terminos_y_condiciones/', views.devoluciones, name='politica_devoluciones')


]
