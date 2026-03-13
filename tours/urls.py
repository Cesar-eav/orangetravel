from django.urls import path
from . import views

urlpatterns = [
    path('', views.tours_home, name="tours_home" ),
    path('tour/<slug:slug>/', views.tour, name="tour"),
    path('api/reserva/crear/', views.crear_reserva, name='crear_reserva'),
]