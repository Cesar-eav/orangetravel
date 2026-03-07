from django.contrib import admin
from .models import TipoTour, Tour, GaleriaTour, PrecioTour
from django.utils.html import format_html 

class PrecioInline(admin.StackedInline):
    model = PrecioTour
    can_delete = False
    verbose_name = "Configuración de Precios"

class GaleriaInline(admin.TabularInline):
    model = GaleriaTour
    extra = 3

@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    # Lo que se ve en la tabla principal
    list_display = ('previsualizacion', 'nombre', 'tipo', 'get_precio_adulto', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)
    
    # Genera el slug automáticamente mientras escribes el nombre
    prepopulated_fields = {'slug': ('nombre',)}
    
    # Unimos Precio y Galería en el formulario del Tour
    inlines = [PrecioInline, GaleriaInline]

    def previsualizacion(self, obj):
            if obj.imagen_principal:
                return format_html(
                    '<img src="{}" style="width: 80px; height: auto; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);" />',
                    obj.imagen_principal.url
                )
            return "Sin imagen"
        
    previsualizacion.short_description = 'Imágen Pirncipal'

    readonly_fields = ('ver_imagen_grande',)

    def ver_imagen_grande(self, obj):
        if obj.imagen_principal:
            return format_html('<img src="{}" style="max-width: 400px; height: auto;" />', obj.imagen_principal.url)
        return "No hay imagen cargada"

    # Función auxiliar para mostrar el precio en la lista
    def get_precio_adulto(self, obj):
 # Intentamos obtener el precio, si no existe o falla, devolvemos un aviso
        try:
            if hasattr(obj, 'precio') and obj.precio:
                return f"${obj.precio.valor_adulto:,.0f}"
        except Exception:
            pass
        return "No asignado"
    get_precio_adulto.short_description = 'Precio General'

 # 3. Registro de las Categorías
@admin.register(TipoTour)
class TipoTourAdmin(admin.ModelAdmin):
    list_display = ('nombre',)   