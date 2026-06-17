from django.contrib import admin
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django.utils.html import format_html

from unfold.admin import ModelAdmin, TabularInline

from .models import Post, ImagenCarousel, ImagenPost


class ImagenPostInline(TabularInline):
    model = ImagenPost
    extra = 1
    fields = ('imagen', 'despues_del_parrafo', 'caption', 'orden')
    verbose_name = "Imagen entre párrafos"
    verbose_name_plural = "Imágenes entre párrafos"


class ImagenCarouselInline(TabularInline):
    model = ImagenCarousel
    extra = 0
    max_num = 20
    fields = ('imagen', 'orden')
    verbose_name_plural = "Imágenes del carrusel"


@admin.register(Post)
class BlogAdmin(ModelAdmin):
    list_display = ('ver_miniatura', 'titulo', 'extracto', 'fecha_creacion', 'publicado')
    list_filter = ('publicado', 'fecha_creacion')
    list_editable = ('publicado',)
    search_fields = ('titulo', 'extracto', 'contenido')
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = ('ver_miniatura', 'fecha_creacion', 'fecha_actualizacion', 'boton_subir_imagenes', 'contador_parrafos')
    inlines = [ImagenPostInline, ImagenCarouselInline]

    fieldsets = (
        ('Configuración Principal', {
            'fields': ('titulo', 'slug', 'autor', 'publicado'),
        }),
        ('Contenido de la Reseña', {
            'fields': ('extracto', 'contenido', 'contador_parrafos'),
            'description': 'El extracto se usa para la lista; el contenido es la reseña completa. El contador te indica cuántos párrafos tiene el post para que sepas qué números usar al insertar imágenes.'
        }),
        ('Multimedia y SEO', {
            'fields': ('imagen_portada', 'video_youtube'),
        }),
        ('Subida masiva al carrusel', {
            'fields': ('boton_subir_imagenes',),
            'description': 'Guarda la reseña primero y luego usa el botón para subir varias imágenes a la vez.',
        }),
        ('Fechas de Registro', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:post_id>/upload-carousel/',
                self.admin_site.admin_view(self.upload_carousel_view),
                name='blog_post_upload_carousel',
            ),
        ]
        return custom_urls + urls

    def upload_carousel_view(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)

        if request.method == 'POST':
            archivos = request.FILES.getlist('imagenes')
            if not archivos:
                messages.warning(request, 'No seleccionaste ninguna imagen.')
            else:
                archivos = archivos[:20]
                orden_base = post.imagenes_carousel.count()
                for i, f in enumerate(archivos):
                    ImagenCarousel.objects.create(post=post, imagen=f, orden=orden_base + i)
                messages.success(request, f'{len(archivos)} imagen(es) añadida(s) al carrusel.')
            return redirect(f'../../{post_id}/change/')

        context = {
            **self.admin_site.each_context(request),
            'post': post,
            'opts': self.model._meta,
            'title': f'Subir imágenes – {post.titulo}',
        }
        return TemplateResponse(request, 'admin/blog/upload_carousel.html', context)

    def contador_parrafos(self, obj):
        if not obj.pk or not obj.contenido:
            return "Guarda la reseña primero."
        import re
        parrafos = re.findall(r'</(?:p|h[1-6]|ul|ol|blockquote|figure)>', obj.contenido)
        n = len(parrafos)
        return format_html(
            '<span style="font-weight:600;">Este post tiene {} bloque(s) de contenido.</span> '
            'Usa números del 1 al {} en el campo "Después del párrafo" de las imágenes de abajo.',
            n, n
        )
    contador_parrafos.short_description = "Párrafos detectados"

    def boton_subir_imagenes(self, obj):
        if not obj.pk:
            return "Guarda la reseña primero para poder subir imágenes."
        url = f'/admin/blog/post/{obj.pk}/upload-carousel/'
        return format_html(
            '<a href="{}" style="display:inline-block;padding:8px 20px;background:#f97316;'
            'color:#fff;border-radius:6px;font-weight:600;text-decoration:none;">'
            '📁 Subir varias imágenes a la vez</a>',
            url,
        )
    boton_subir_imagenes.short_description = "Carga masiva"

    def ver_miniatura(self, obj):
        if obj.imagen_portada:
            return format_html(
                '<img src="{}" style="width:150px;height:100px;border-radius:12px;object-fit:cover;" />',
                obj.imagen_portada.url,
            )
        return "Sin imagen"
