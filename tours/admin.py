from django.contrib import admin
from .models import TipoTour, Tour, GaleriaTour, PrecioTour


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
    list_display = ('nombre', 'tipo', 'get_precio_adulto', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)
    
    # Genera el slug automáticamente mientras escribes el nombre
    prepopulated_fields = {'slug': ('nombre',)}
    
    # Unimos Precio y Galería en el formulario del Tour
    inlines = [PrecioInline, GaleriaInline]

    # Función auxiliar para mostrar el precio en la lista
    def get_precio_adulto(self, obj):
        return f"${obj.precio.valor_adulto:,.0f}"
    get_precio_adulto.short_description = 'Precio General'

 # 3. Registro de las Categorías
@admin.register(TipoTour)
class TipoTourAdmin(admin.ModelAdmin):
    list_display = ('nombre',)   