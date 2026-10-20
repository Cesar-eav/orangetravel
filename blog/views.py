import re
from collections import defaultdict
from django.shortcuts import render
from .models import Post
from tours.traduccion import mostrar_aprobado


def blog_home(request):
    posts = mostrar_aprobado(list(Post.objects.all()), request)
    return render(request, 'blog/blog_home.html', {'posts': posts})


def post(request, slug):
    post_obj = Post.objects.get(slug=slug)
    mostrar_aprobado([post_obj], request)
    imagenes = mostrar_aprobado(list(post_obj.imagenes_post.all()), request, aprobado=post_obj.traduccion_en_aprobada)

    # Dividir el contenido HTML en bloques por etiquetas de bloque
    content = post_obj.contenido or ''
    SEP = '\x00'
    marcado = re.sub(
        r'</(?:p|h1|h2|h3|h4|h5|h6|ul|ol|blockquote|figure)>',
        lambda m: m.group(0) + SEP,
        content,
    )
    bloques_html = [b.strip() for b in marcado.split(SEP) if b.strip()]

    # Agrupar imágenes por posición
    imagen_map = defaultdict(list)
    for img in imagenes:
        imagen_map[img.despues_del_parrafo].append(img)

    bloques = []

    # Imágenes en posición 0 → antes de todo el contenido
    for img in imagen_map.get(0, []):
        bloques.append({'tipo': 'imagen', 'imagen': img})

    for i, html in enumerate(bloques_html, 1):
        bloques.append({'tipo': 'texto', 'contenido': html})
        for img in imagen_map.get(i, []):
            bloques.append({'tipo': 'imagen', 'imagen': img})

    return render(request, 'blog/post.html', {'post': post_obj, 'bloques': bloques})