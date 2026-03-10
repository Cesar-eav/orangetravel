from django.shortcuts import render
from tours.models import Tour
from blog.models import Post

# Create your views here.

def home(request):

    tours = Tour.objects.filter(destacado=True).select_related('precio')
    posts = Post.objects.order_by('-fecha_creacion')

    return render(request, 'home/index.html',{
        'tours': tours,
        'posts': posts
    })
