from django.urls import path
from django.views.generic import TemplateView
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('nueva_web/', views.home, name='nueva_web'),
    path('nosotros', views.nosotros, name='nosotros'),
    path('contacto_formulario/', views.contacto_send_email, name='contacto_formulario'),
    path('contacto/', views.contacto, name='contacto'),
    path('terminos_y_condiciones/', views.devoluciones, name='politica_devoluciones'),
    path('otros-servicios/', views.otros_servicios, name='otros_servicios'),
    path('plan-de-traduccion/', TemplateView.as_view(template_name='home/plan_traduccion.html'), name='plan_traduccion'),


]
