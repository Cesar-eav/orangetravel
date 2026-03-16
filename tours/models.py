from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
import re
from django.utils import timezone
from datetime import date

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

# Manager para filtrar los borrados lógicos por defecto
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        # Solo devuelve registros que NO tengan fecha de borrado
        return super().get_queryset().filter(borrado_el__isnull=True)

class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Confirmación'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    # --- Relaciones ---
    tour = models.ForeignKey('Tour', on_delete=models.CASCADE, related_name='reservas')
    
    # --- Datos del Cliente ---
    nombre_cliente = models.CharField("Nombre del cliente", max_length=100)
    email_cliente = models.EmailField("Correo electrónico")
    telefono_cliente = models.CharField("Teléfono/WhatsApp", max_length=20)
    
    # --- Detalle de la Reserva ---
    fecha = models.DateField("Fecha del tour")
    adultos = models.PositiveIntegerField("Número de adultos", default=1)
    ninos = models.PositiveIntegerField("Número de niños (hasta 11 años)", default=0)
    precio_total = models.IntegerField("Precio Total ($)", editable=False)
    
    # --- Gestión Administrativa ---
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    notas_internas = models.TextField(
        "Notas Internas (Vehículo, Clima, etc.)", 
        blank=True, 
        null=True
    )
    
    # --- Auditoría y Borrado Lógico ---
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    borrado_el = models.DateTimeField("Fecha de borrado", null=True, blank=True, editable=False)

    # --- Managers ---
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-fecha', '-creada_el']

    def __str__(self):
        return f"{self.nombre_cliente} - {self.tour.nombre} ({self.fecha})"

    # --- LÓGICA DE NEGOCIO ---

    def save(self, *args, **kwargs):
        """Cálculo automático del total antes de persistir en DB."""
        # Fallback a precios estándar de Arica si el Tour no los define explícitamente
        p_adulto = getattr(self.tour, 'valor_adulto', 18000)
        p_nino = getattr(self.tour, 'valor_nino', 15000)
        self.precio_total = (self.adultos * p_adulto) + (self.ninos * p_nino)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Borrado lógico: marca la fecha pero no elimina la fila."""
        self.borrado_el = timezone.now()
        self.save()

    def restaurar(self):
        """Revierte el borrado lógico."""
        self.borrado_el = None
        self.save()

    # --- PROPIEDADES DINÁMICAS (Consumidas por Vue/Templates) ---

    @property
    def situacion(self):
        """Estado semántico histórico de la reserva."""
        hoy = date.today()
        if self.borrado_el:
            return "Eliminada (Lógico)"
        
        if self.fecha < hoy:
            if self.estado == self.Estado.CONFIRMADA:
                return "Realizada"
            elif self.estado == self.Estado.PENDIENTE:
                return "No concretada / Expirada"
        
        return self.get_estado_display()

    @property
    def es_activa(self):
        """Determina si la reserva es válida y para una fecha futura."""
        return self.borrado_el is None and self.fecha >= date.today()


