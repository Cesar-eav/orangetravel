from django.urls import path
from . import views


urlpatterns = [
    path('', views.tours_home, name="tours_home" ),
    path('tour/<slug:slug>/', views.tour, name="tour"),
    path('tercera_edad/', views.tercera_edad, name="tercera_edad"),
    # Las APIs están en tours/api_urls.py (fuera de i18n_patterns).
]