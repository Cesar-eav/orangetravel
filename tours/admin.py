from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import TipoTour, Tour, GaleriaTour, PrecioTour, Reserva, BloqueoTour
from django import forms

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

class TourAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].empty_label = "Selecciona un tipo"


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
    list_display = ('nombre','id', 'tipo', 'get_precio_adulto', 'activo', 'destacado')
    list_editable = ('activo','destacado')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)
    readonly_fields = ('previsualizacion', 'get_precio_adulto')

    form = TourAdminForm

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

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

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
    list_display = ('tour', 'fecha', 'motivo', 'tiene_reservas_activas')
    list_filter = ('tour', 'fecha')
    date_hierarchy = 'fecha'
    readonly_fields = ('resumen_reservas',)
    fieldsets = (
        (None, {
            'fields': ('tour', 'fecha', 'motivo'),
        }),
        ('Reservas activas del tour', {
            'fields': ('resumen_reservas',),
        }),
    )

    def tiene_reservas_activas(self, obj):
        estados = ['PENDIENTE', 'CONFIRMADA', 'Confirmada', 'Realizada']
        count = Reserva.objects.filter(
            tour=obj.tour,
            fecha=obj.fecha,
            estado__in=estados,
        ).count()
        if count:
            label = f'{count} reserva{"s" if count > 1 else ""}'
            return format_html(
                '<span style="color:#c2410c;font-weight:bold">⚠ {}</span>',
                label,
            )
        return format_html('<span style="color:#6b7280">—</span>')
    tiene_reservas_activas.short_description = 'Reservas activas'

    def resumen_reservas(self, obj):
        if not obj.pk or not obj.tour_id:
            return 'Selecciona un tour para ver sus reservas activas.'
        estados = ['PENDIENTE', 'CONFIRMADA', 'Confirmada', 'Realizada']
        reservas = Reserva.objects.filter(
            tour=obj.tour,
            estado__in=estados,
        ).order_by('fecha')
        if not reservas.exists():
            return '✓ Sin reservas activas para este tour.'
        items = ''.join(
            f'<li style="margin:3px 0"><strong>{r.fecha}</strong> — '
            f'{r.nombre_cliente} &nbsp;·&nbsp; {r.adultos} adulto{"s" if r.adultos != 1 else ""}'
            f'{", " + str(r.ninos) + " niño" + ("s" if r.ninos != 1 else "") if r.ninos else ""}'
            f'</li>'
            for r in reservas
        )
        return format_html(
            '<ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.7">{}</ul>',
            mark_safe(items),
        )
    resumen_reservas.short_description = 'Reservas activas del tour'

    class Media:
        js = ('js/admin_bloqueo.js',)

