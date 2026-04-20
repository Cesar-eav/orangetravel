from django.urls import path
from . import views


urlpatterns = [
    path('', views.tours_home, name="tours_home" ),
    path('tour/<slug:slug>/', views.tour, name="tour"),
    path('tercera_edad/', views.tercera_edad, name="tercera_edad"),
    path('api/reserva/crear/', views.crear_reserva, name='crear_reserva'),
    path('api/bloqueos/<int:tour_id>/', views.get_fechas_bloqueadas, name='api_bloqueos'),
    path('api/admin/reservas/<int:tour_id>/', views.get_reservas_activas_admin, name='api_admin_reservas'),
]