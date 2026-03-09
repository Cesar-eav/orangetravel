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