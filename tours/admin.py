from django.contrib import admin, messages
from django.utils.html import format_html 
from .models import TipoTour, Tour, GaleriaTour, PrecioTour, Reserva, BloqueoTour

# IMPORTANTE: Importamos desde unfold.admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline

# --- INLINES (Componentes dentro de otros) ---

class PrecioInline(StackedInline): # Cambiado a Unfold StackedInline
    model = PrecioTour
    can_delete = False
    verbose_name = "Configuración de Precios"
    # Esto ayuda a Unfold a organizar los inlines en pestañas laterales o inferiores
    tab = True 

class GaleriaInline(TabularInline): # Cambiado a Unfold TabularInline
    model = GaleriaTour
    extra = 3
    tab = True

# --- ADMIN MODELS ---

@admin.register(Reserva)
class ReservaAdmin(ModelAdmin): # Cambiado a Unfold ModelAdmin
    # Columnas que se verán en el listado
    list_display = (
        'id', 'nombre_cliente', 'tour', 'fecha', 
        'creada_el', 'columna_estado', 'estado', 'columna_activa'
    )
    list_filter = ('estado', 'fecha', 'tour')
    list_editable = ('estado',)
    search_fields = ('nombre_cliente', 'email_cliente')
    readonly_fields = ('precio_total', 'creada_el', 'borrado_el')
    
    # Lógica de colores para Unfold
    def columna_estado(self, obj):
        situacion = obj.situacion
        color = "black"
        
        if situacion == "Realizada":
            color = "#28a745" # Verde
        elif situacion == "Pendiente de Confirmación":
            color = "#fd7e14" # Naranja
        elif situacion == "Eliminada" or situacion == "Cancelada":
            color = "#dc3545" # Rojo
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            situacion
        )
    columna_estado.short_description = 'Estado Actual'

    def columna_activa(self, obj):
        return obj.es_activa
    columna_activa.boolean = True
    columna_activa.short_description = '¿Está Vigente?'

    def get_queryset(self, request):
        # Mantenemos tu lógica de ver borrados lógicos
        return Reserva.all_objects.all()
    
    actions = ['marcar_como_borrado']
    
    def marcar_como_borrado(self, request, queryset):
        for obj in queryset:
            obj.delete() 
        self.message_user(request, "Las reservas han sido movidas a la papelera (borrado lógico).")
    marcar_como_borrado.short_description = "Eliminar reservas seleccionadas"


@admin.register(Tour)
class TourAdmin(ModelAdmin): # Cambiado a Unfold ModelAdmin
    list_display = ('nombre', 'tipo', 'get_precio_adulto', 'activo', 'destacado', 'video_youtube')
    list_editable = ('activo',)
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)
    readonly_fields = ('previsualizacion', 'get_precio_adulto')


    # Para que Unfold active las PESTAÑAS, usamos 'fieldsets' en lugar de 'fields'
    fieldsets = (
        ("Información del Tour", {
            "fields": (
                'imagen_principal', 
                'nombre', 
                'activo',
                'destacado', 
                'slug', 
                'tipo', 
                'itinerario', 
                'get_precio_adulto'
                
            ),
        }),
        ("Multimedia", {
            "fields": (
                'video_youtube',
            ),
        }),
    )
    
    prepopulated_fields = {'slug': ('nombre',)}
    
    # Inlines de Unfold (Precios y Galería aparecerán como secciones/pestañas)
    inlines = [PrecioInline, GaleriaInline]

    # Sobreescribimos la acción de borrado individual
    def delete_model(self, request, obj):
        obj.activo = False
        obj.save()
        messages.success(request, f"El tour '{obj.nombre}' ha sido desactivado (borrado lógico).")

    class Media:
        js = ('js/admin_tour_warning.js',)

    def get_prepopulated_fields(self, request, obj=None):
        if obj: 
            return {}
        return self.prepopulated_fields

    def previsualizacion(self, obj):
        if obj.imagen_principal:
            return format_html(
                '<img src="{}" style="width: 80px; height: auto; border-radius: 8px;" />',
                obj.imagen_principal.url
            )
        return "Sin imagen"
    previsualizacion.short_description = 'Imagen Principal'

    def ver_imagen_grande(self, obj):
        if obj.imagen_principal:
            return format_html('<img src="{}" style="max-width: 400px; height: auto; border-radius: 12px;" />', obj.imagen_principal.url)
        return "No hay imagen cargada"

    def get_precio_adulto(self, obj):
        try:
            if hasattr(obj, 'precio') and obj.precio:
                return f"${obj.precio.valor_adulto:,.0f}"
        except Exception:
            pass
        return "No asignado"
    get_precio_adulto.short_description = 'Precio General'


@admin.register(TipoTour)
class TipoTourAdmin(ModelAdmin): # Cambiado a Unfold ModelAdmin
    list_display = ('nombre',)


@admin.register(BloqueoTour)
class BloqueoTourAdmin(ModelAdmin):
    list_display = ('tour', 'fecha', 'motivo')
    list_filter = ('tour', 'fecha')
    date_hierarchy = 'fecha' # Crea una barrita de navegación por fechas arriba    