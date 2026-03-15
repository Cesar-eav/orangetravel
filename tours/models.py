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
        return super().get_queryset().filter(borrado_el__isnull=True)

class Reserva(models.Model):
    # Opciones de Estado
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Confirmación'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    # Relaciones y Datos del Tour
    tour = models.ForeignKey('Tour', on_delete=models.CASCADE, related_name='reservas')
    fecha = models.DateField("Fecha del tour")
    
    # Datos del Cliente
    nombre_cliente = models.CharField("Nombre del cliente", max_length=100)
    email_cliente = models.EmailField("Correo electrónico")
    telefono_cliente = models.CharField("Teléfono/WhatsApp", max_length=20)
    
    # Detalle de Pasajeros y Precios
    adultos = models.PositiveIntegerField("Número de adultos", default=1)
    ninos = models.PositiveIntegerField("Número de niños (hasta 11 años)", default=0)
    precio_total = models.IntegerField("Precio Total ($)", editable=False)
    
    # Gestión Administrativa
    estado = models.CharField(
        "Estado de la reserva",
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    notas_internas = models.TextField(
        "Notas (Clima, Vehículo, Guía)", 
        blank=True, 
        null=True
    )
    
    # Auditoría y Borrado Lógico
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    borrado_el = models.DateTimeField("Fecha de borrado", null=True, blank=True, editable=False)

    # Managers
    objects = SoftDeleteManager()           # Filtra borrados automáticamente
    all_objects = models.Manager()          # Permite ver TODO incluyendo borrados

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-fecha', '-creada_el']

    def __str__(self):
        return f"{self.nombre_cliente} - {self.tour.nombre} ({self.fecha})"

    # --- LÓGICA DE NEGOCIO ---

    def save(self, *args, **kwargs):
        """Calcula el total basado en precios fijos de Arica antes de guardar."""
# Asumiendo que en tu modelo Tour tienes campos llamados 'precio_adulto' y 'precio_nino'
        total = (self.adultos * self.tour.valor_adulto) + (self.ninos * self.tour.valor_nino)
        self.precio_total = total
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Implementación de borrado lógico."""
        self.borrado_el = timezone.now()
        self.save()

    def restaurar(self):
        """Recupera una reserva borrada por error."""
        self.borrado_el = None
        self.save()

    # --- PROPIEDADES DINÁMICAS ---

    @property
    def situacion(self):
        """Determina si el tour ya se realizó o si la reserva expiró."""
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
        """Define si la reserva está vigente para el futuro."""
        return self.borrado_el is None and self.fecha >= date.today()

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Confirmación'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    tour = models.ForeignKey('Tour', on_delete=models.CASCADE, related_name='reservas')
    
    # Datos del Cliente
    nombre_cliente = models.CharField("Nombre del cliente", max_length=100)
    email_cliente = models.EmailField("Correo electrónico")
    telefono_cliente = models.CharField("Teléfono/WhatsApp", max_length=20)
    
    # Detalle de la Reserva
    fecha = models.DateField("Fecha del tour")
    adultos = models.PositiveIntegerField("Número de adultos", default=1)
    ninos = models.PositiveIntegerField("Número de niños (hasta 11 años)", default=0)
    precio_total = models.IntegerField("Precio Total", editable=False)
    
    # Gestión de Orange Travel
    estado = models.CharField(
        "Estado de la reserva",
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    notas_internas = models.TextField(
        "Notas internas (Clima, Vehículo, Disponibilidad)", 
        blank=True, 
        null=True
    )
    
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.nombre_cliente} - {self.tour.nombre} ({self.fecha})"

    def save(self, *args, **kwargs):
        # Lógica de precios: $18.000 adultos, $15.000 niños
        self.precio_total = (self.adultos * 18000) + (self.ninos * 15000)
        super().save(*args, **kwargs)