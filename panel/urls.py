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
    path('tours/', views.TourListView.as_view(), name='tours'),
    path('tours/nuevo/', views.TourFormView.as_view(), name='tour_nuevo'),
    path('tours/<int:pk>/', views.TourFormView.as_view(), name='tour_editar'),
    path('galeria/<int:pk>/eliminar/', views.galeria_eliminar, name='galeria_eliminar'),
    path('categorias/', views.TipoListView.as_view(), name='tipos'),
    path('categorias/nueva/', views.TipoFormView.as_view(), name='tipo_nuevo'),
    path('categorias/<int:pk>/', views.TipoFormView.as_view(), name='tipo_editar'),
    path('categorias/<int:pk>/eliminar/', views.tipo_eliminar, name='tipo_eliminar'),
    path('bloqueos/', views.BloqueoListView.as_view(), name='bloqueos'),
    path('bloqueos/<int:pk>/eliminar/', views.bloqueo_eliminar, name='bloqueo_eliminar'),
    path('blog/', views.PostListView.as_view(), name='posts'),
    path('blog/nuevo/', views.PostFormView.as_view(), name='post_nuevo'),
    path('blog/<int:pk>/', views.PostFormView.as_view(), name='post_editar'),
    path('blog/<int:pk>/eliminar/', views.post_eliminar, name='post_eliminar'),
    path('carrusel/<int:pk>/eliminar/', views.carrusel_eliminar, name='carrusel_eliminar'),
    path('pagos/', views.PagoListView.as_view(), name='pagos'),
    path('pagos/<int:pk>/', views.PagoDetailView.as_view(), name='pago_detalle'),
    path('pagos/<int:pk>/reenviar/<str:destino>/', views.pago_reenviar, name='pago_reenviar'),
]
