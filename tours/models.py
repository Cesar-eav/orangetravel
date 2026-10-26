from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField
import re
import secrets
from django.utils import timezone
from datetime import date
from solo.models import SingletonModel

# Extrae el ID de casi cualquier formato de link de YouTube
YOUTUBE_REGEX = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})'

# Alfabeto sin 0/O ni 1/I para evitar confusiones al leer el código en voz alta
CODIGO_RESERVA_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_codigo_reserva(queryset, campo='codigo', longitud=6, prefijo='OT'):
    """Genera un código único de reserva (ej: OT-4K7QXZ), reintentando ante colisiones."""
    while True:
        sufijo = ''.join(secrets.choice(CODIGO_RESERVA_ALFABETO) for _ in range(longitud))
        codigo = f"{prefijo}-{sufijo}"
        if not queryset.filter(**{campo: codigo}).exists():
            return codigo

# Única categoría que se vende con precio y pago Flow; el resto se cotiza.
TIPO_CON_PRECIO_ID = 1

class TipoTour(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Tipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción del tipo (opcional)")

    class Meta:
        verbose_name = "Categoría de Tour"
        verbose_name_plural = "Categorías de Tours"

    def __str__(self):
        return self.nombre

class Zona(models.Model):
    # «Expediciones y Montaña» es una zona más aunque no sea geográfica.
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=120)
    descripcion = models.TextField(blank=True, verbose_name="Descripción (opcional)")
    imagen = models.ImageField(upload_to='tours/zonas/', blank=True, null=True, verbose_name="Imagen o ícono (opcional)")
    orden = models.PositiveSmallIntegerField(default=0, help_text="Posición en el listado público (menor primero).")

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"

    def __str__(self):
        return self.nombre

class Tour(models.Model):
    # Relación dinámica: El usuario gestiona esto desde el Admin
    tipo = models.ForeignKey(TipoTour, on_delete=models.PROTECT, related_name='tours', verbose_name="Tipo de Tour")
    zona = models.ForeignKey(Zona, on_delete=models.PROTECT, related_name='tours', null=True, blank=True)

    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=255)
    
     # Contenido CKEditor
    itinerario = RichTextUploadingField(verbose_name="Resumen del tour")
    incluye = RichTextUploadingField(blank=True, verbose_name="Incluye")
    video_youtube = models.URLField(blank=True, null=True)
    @property
    def youtube_embed_url(self):
        if not self.video_youtube:
            return None
        match = re.search(YOUTUBE_REGEX, self.video_youtube)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
        return None
    
    imagen_principal = models.ImageField(upload_to='tours/principales/')
    mapa = models.ImageField(upload_to='tours/mapas/', blank=True, null=True, verbose_name="Mapa del tour")
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")

    destacado = models.BooleanField(
        default=False,
        verbose_name="Destacado",
        help_text="Si se marca, aparecerá en la sección principal de la página de inicio."
        )

    es_prueba = models.BooleanField(
        default=False,
        verbose_name="Tour de prueba",
        help_text="Si se marca, el tour NO aparecerá en el listado público aunque esté activo. Solo accesible por URL directa."
    )

    def __str__(self):
        return self.nombre

    @property
    def con_precio(self):
        return self.tipo_id == TIPO_CON_PRECIO_ID


class GaleriaTour(models.Model):
    tour = models.ForeignKey(Tour, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='tours/galeria/')
    

class ItinerarioDia(models.Model):
    tour = models.ForeignKey(Tour, related_name='dias', on_delete=models.CASCADE)
    orden = models.PositiveSmallIntegerField(default=1, verbose_name="Día")
    titulo = models.CharField(max_length=200, verbose_name="Título del día")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        ordering = ['orden', 'pk']
        verbose_name = "Día del itinerario"
        verbose_name_plural = "Itinerario por día"

    def __str__(self):
        return f"Día {self.orden}: {self.titulo}"


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

    # --- Identificación ---
    codigo = models.CharField(
        "Código de reserva", max_length=20, unique=True, editable=False,
        null=True, blank=True,
    )

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
        if not self.codigo:
            self.codigo = generar_codigo_reserva(Reserva.all_objects)

        if hasattr(self.tour, 'precio'):
            p = self.tour.precio
            p_adulto = p.valor_adulto
            p_nino = p.valor_nino if p.tiene_precio_nino else p.valor_adulto
        else:
            # Fallback a precios estándar de Arica si el Tour no tiene PrecioTour configurado
            p_adulto = 18000
            p_nino = 15000

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


class Cotizacion(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.PROTECT, related_name='cotizaciones')
    nombre = models.CharField("Nombre", max_length=100)
    email = models.EmailField("Correo electrónico")
    telefono = models.CharField("Teléfono/WhatsApp", max_length=20)
    fecha_tentativa = models.DateField("Fecha tentativa", null=True, blank=True)
    adultos = models.PositiveIntegerField("Adultos", default=1)
    ninos = models.PositiveIntegerField("Niños", default=0)
    mensaje = models.TextField("Mensaje", blank=True)
    atendida = models.BooleanField("Atendida", default=False)
    creada_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"
        ordering = ['-creada_el']

    def __str__(self):
        return f"{self.nombre} - {self.tour.nombre}"


class Venta(models.Model):
    """Venta ingresada a mano desde el panel (oficina, WhatsApp, agencia...).
    Registro aparte: no crea Reserva ni Payment, no envía emails ni bloquea fechas."""

    class Canal(models.TextChoices):
        WEB = 'web', 'Web'
        OFICINA = 'oficina', 'Oficina'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        EMAIL = 'email', 'Email'
        AGENCIA = 'agencia', 'Agencia'
        OTRO = 'otro', 'Otro'

    class TipoServicio(models.TextChoices):
        TOUR = 'tour', 'Tour'
        TRASLADO = 'traslado', 'Traslado'
        COMBINADO = 'combinado', 'Combinado'
        OTRO = 'otro', 'Otro'

    class EstadoPago(models.TextChoices):
        PAGADO = 'pagado', 'Pagado'
        ABONO = 'abono', 'Abono'
        PENDIENTE = 'pendiente', 'Pendiente'

    class EstadoReserva(models.TextChoices):
        CONFIRMADA = 'confirmada', 'Confirmada'
        PENDIENTE = 'pendiente', 'Pendiente'
        CANCELADA = 'cancelada', 'Cancelada'

    # --- Cliente ---
    nombre_cliente = models.CharField("Nombre del cliente", max_length=100)
    telefono = models.CharField("Teléfono / WhatsApp", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)

    # --- Servicio ---
    fecha_venta = models.DateField("Fecha de venta", default=timezone.localdate)
    fecha_servicio = models.DateField("Fecha del servicio")
    canal = models.CharField("Canal de venta", max_length=20, choices=Canal.choices)
    tipo_servicio = models.CharField("Tipo de servicio", max_length=20, choices=TipoServicio.choices)
    tour = models.ForeignKey(
        Tour, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas',
        verbose_name="Tour del catálogo",
    )
    servicio = models.CharField("Tour o servicio", max_length=200)
    destino = models.CharField("Destino o ruta", max_length=200, blank=True)
    pasajeros = models.PositiveIntegerField("Cantidad de pasajeros", default=1)

    # --- Pago (CLP) ---
    precio_total = models.PositiveIntegerField("Precio total ($)")
    monto_pagado = models.PositiveIntegerField("Monto pagado ($)", default=0)
    medio_pago = models.CharField("Medio de pago", max_length=100, blank=True)
    estado_pago = models.CharField(
        "Estado del pago", max_length=20, choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE, editable=False,
    )
    estado_reserva = models.CharField(
        "Estado de la reserva", max_length=20, choices=EstadoReserva.choices,
        default=EstadoReserva.PENDIENTE,
    )
    observaciones = models.TextField("Observaciones / detalle de servicios", blank=True)

    # --- Auditoría y borrado lógico ---
    creada_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, editable=False,
        related_name='+',
    )
    creada_el = models.DateTimeField(auto_now_add=True)
    actualizada_el = models.DateTimeField(auto_now=True)
    borrado_el = models.DateTimeField("Fecha de borrado", null=True, blank=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_venta', '-creada_el']

    def __str__(self):
        return f"{self.nombre_cliente} - {self.servicio} ({self.fecha_servicio})"

    @property
    def saldo_pendiente(self):
        return (self.precio_total or 0) - (self.monto_pagado or 0)

    def save(self, *args, **kwargs):
        # Se guarda calculado para poder filtrar por estado del pago.
        if self.saldo_pendiente <= 0:
            self.estado_pago = self.EstadoPago.PAGADO
        elif self.monto_pagado:
            self.estado_pago = self.EstadoPago.ABONO
        else:
            self.estado_pago = self.EstadoPago.PENDIENTE
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Borrado lógico: marca la fecha pero no elimina la fila."""
        self.borrado_el = timezone.now()
        self.save()


class BloqueoTour(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='bloqueos')
    fecha = models.DateField()
    motivo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('tour', 'fecha') # Evita duplicar el mismo bloqueo
        verbose_name = "Bloqueo de Fecha"
        verbose_name_plural = "Bloqueos de Fechas"

    def __str__(self):
        return f"Bloqueo {self.tour.nombre} - {self.fecha}"




class TerceraEdad(SingletonModel):
    contenido = RichTextUploadingField(verbose_name="Contenido")

    def __str__(self):
        return "Página Tercera Edad"

    class Meta:
        verbose_name = "Tercera Edad"
        verbose_name_plural = "Tercera Edad"
