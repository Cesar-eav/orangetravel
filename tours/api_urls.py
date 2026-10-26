from django.urls import path
from . import views


# Montadas en /tours/api/ fuera de i18n_patterns: Vue y el admin las llaman
# con rutas absolutas, sin prefijo de idioma.
urlpatterns = [
    path('reserva/crear/', views.crear_reserva, name='crear_reserva'),
    path('cotizacion/crear/', views.crear_cotizacion, name='crear_cotizacion'),
    path('bloqueos/<int:tour_id>/', views.get_fechas_bloqueadas, name='api_bloqueos'),
    path('admin/pagos/<int:tour_id>/', views.get_pagos_activos_admin, name='api_admin_pagos'),
]
