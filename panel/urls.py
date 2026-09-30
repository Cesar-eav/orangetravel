from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.PanelLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page=reverse_lazy('panel:login')
    ), name='logout'),
    path('reservas/', views.ReservaListView.as_view(), name='reservas'),
    path('reservas/<int:pk>/', views.ReservaDetailView.as_view(), name='reserva_detalle'),
    path('reservas/<int:pk>/eliminar/', views.reserva_eliminar, name='reserva_eliminar'),
    path('pagos/', views.PagoListView.as_view(), name='pagos'),
    path('pagos/<int:pk>/', views.PagoDetailView.as_view(), name='pago_detalle'),
    path('pagos/<int:pk>/reenviar/<str:destino>/', views.pago_reenviar, name='pago_reenviar'),
]
