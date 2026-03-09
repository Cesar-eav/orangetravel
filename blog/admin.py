from django.contrib import admin
from .models import Post
from django.utils.html import format_html 


# Register your models here.
@admin.register(Post)
class BlogAdmin(admin.ModelAdmin):
    list_display =('ver_miniatura','titulo', 'extracto', 'fecha_creacion')
    list_filter=('publicado',)
    search_fields=('titulo','contenido')

    prepopulated_fields={'slug':('titulo',)}

# 3. Campos de solo lectura para previsualizar media
    readonly_fields = ('ver_miniatura',)

    def ver_miniatura(self, obj):
        if obj.imagen_portada: # Ojo: verifica si el nombre en tu modelo es imagen_portada
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />', 
                obj.imagen_portada.url)
        return "Sin imagen"

    ver_miniatura.short_description = 'Miniatura'

