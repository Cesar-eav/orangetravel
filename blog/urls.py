from django.urls import path
from . import views

urlpatterns = [
     path('', views.blog_home, name="blog_home" ),
     path('blog/<slug:slug>/', views.post, name="post")
]