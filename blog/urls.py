from django.urls import path
from . import views

urlpatterns = [
     path('', views.blog_home, name="blog_home" ),
    # path('tour/<slug:slug>/', views.tour, name="tour")
]