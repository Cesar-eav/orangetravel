from django.shortcuts import render
from blog.models import Post


def blog_home(request):

    posts = Post.objects.all()

    return render(request, 'blog/blog_home.html',{
        'posts': posts
    })
