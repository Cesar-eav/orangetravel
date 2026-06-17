from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField # Para las fotos tipo blog

class Post(models.Model):
    # Información básica
    titulo = models.CharField(max_length=200, verbose_name="Título de la Reseña")
    slug = models.SlugField(unique=True, max_length=255)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='blog_posts')
    
    # Contenido (Usando el uploader que permite fotos entre párrafos)
    extracto = models.TextField(max_length=500, help_text="Pequeño resumen para la lista de blogs.")
    contenido = RichTextUploadingField(verbose_name="Cuerpo de la reseña")
    
    # Media
    imagen_portada = models.ImageField(upload_to='blog/portadas/', verbose_name="Imagen Principal")
    
    # El campo de YouTube opcional
    video_youtube = models.URLField(
        max_length=500, 
        blank=True, 
        null=True, 
        verbose_name="Enlace de YouTube",
        help_text="Opcional: Pega la URL completa del video (ej: https://www.youtube.com/watch?v=...)"
    )

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    publicado = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"

    def __str__(self):
        return self.titulo

    # Tip de Pro: Método para convertir la URL de YouTube en formato "embed"
    @property
    def youtube_embed_url(self):
        if self.video_youtube:
            if 'watch?v=' in self.video_youtube:
                return self.video_youtube.replace('watch?v=', 'embed/')
            elif 'youtu.be/' in self.video_youtube:
                video_id = self.video_youtube.split('/')[-1]
                return f"https://www.youtube.com/embed/{video_id}"
        return None


class ImagenPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='imagenes_post')
    imagen = models.ImageField(upload_to='blog/post_images/', verbose_name="Imagen")
    despues_del_parrafo = models.PositiveIntegerField(
        default=1,
        verbose_name="Después del párrafo",
        help_text="Número del párrafo tras el cual aparece esta imagen (1 = después del 1°). Usa 0 para insertarla antes de todo el contenido."
    )
    caption = models.CharField(max_length=300, blank=True, verbose_name="Pie de foto")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden", help_text="Si hay varias imágenes en la misma posición, cuál va primero.")

    class Meta:
        ordering = ['despues_del_parrafo', 'orden']
        verbose_name = "Imagen entre párrafos"
        verbose_name_plural = "Imágenes entre párrafos"

    def __str__(self):
        return f"Img después párr.{self.despues_del_parrafo} – {self.post.titulo}"


class ImagenCarousel(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='imagenes_carousel')
    imagen = models.ImageField(upload_to='blog/carousel/')
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Imagen del Carrusel"
        verbose_name_plural = "Imágenes del Carrusel"

    def __str__(self):
        return f"Imagen {self.orden} – {self.post.titulo}"