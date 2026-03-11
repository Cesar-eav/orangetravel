from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
import re
class TipoTour(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Tipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción del tipo (opcional)")

    class Meta:
        verbose_name = "Categoría de Tour"
        verbose_name_plural = "Categorías de Tours"

    def __str__(self):
        return self.nombre

class Tour(models.Model):
    # Relación dinámica: El usuario gestiona esto desde el Admin
    tipo = models.ForeignKey(TipoTour, on_delete=models.PROTECT, related_name='tours', verbose_name="Tipo de Tour")
    
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=255)
    
     # Contenido CKEditor
    itinerario = RichTextUploadingField(verbose_name="Itinerario Detallado")
    incluye = models.TextField()
    video_youtube = models.URLField(blank=True, null=True)
    @property
    def youtube_embed_url(self):
        if not self.video_youtube:
            return None
        # Esta lógica extrae el ID de casi cualquier formato de link de YouTube
        regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.video_youtube)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
        return None
    
    imagen_principal = models.ImageField(upload_to='tours/principales/')
    activo = models.BooleanField(default=True)

    destacado = models.BooleanField(
        default=False,
        verbose_name="Destacado",
        help_text="Si se marca, aparecerá en la sección principal de la página de inicio."
        )

    def __str__(self):
        return self.nombre


class GaleriaTour(models.Model):
    tour = models.ForeignKey(Tour, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='tours/galeria/')
    

class PrecioTour(models.Model):
    tour = models.OneToOneField(Tour, on_delete=models.CASCADE, related_name='precio')
    valor_adulto = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Precio Adulto/General (CLP)")
    
    # Lógica para niños
    tiene_precio_nino = models.BooleanField(default=False, verbose_name="¿Activar precio para niños?")
    valor_nino = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Precio Niño (CLP)", default=0, blank=True)

    class Meta:
        verbose_name = "Precio de Tour"
        verbose_name_plural = "Precios de Tours"