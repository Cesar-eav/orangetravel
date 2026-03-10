from django.shortcuts import render
from blog.models import Post


def blog_home(request):

    posts = Post.objects.all()

    return render(request, 'blog/blog_home.html',{
        'posts': posts
    })

def post(request, slug):

    post = Post.objects.get(slug = slug)

    return render(request, 'blog/post.html',{
        'post': post
    })
