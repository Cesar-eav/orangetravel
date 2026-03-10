from django.contrib import admin
from .models import Post
from django.utils.html import format_html 


# Register your models here.
@admin.register(Post)
class BlogAdmin(admin.ModelAdmin):
    list_display =('ver_miniatura','titulo', 'extracto', 'fecha_creacion')
    list_filter=('publicado',)
    search_fields=('titulo','extracto','contenido')

    prepopulated_fields={'slug':('titulo',)}

# 3. Campos de solo lectura para previsualizar media
    readonly_fields = ('ver_miniatura','fecha_creacion', 'fecha_actualizacion')
# 4. Organización del formulario por secciones (Fieldsets)
    fieldsets = (
        ('Configuración Principal', {
            'fields': ('titulo', 'slug', 'autor', 'publicado')
        }),
        ('Contenido de la Reseña', {
            'fields': ('extracto', 'contenido'),
            'description': 'El extracto se usa para la lista; el contenido es la reseña completa.'
        }),
        ('Multimedia y SEO', {
            'fields': ('imagen_portada','ver_miniatura',  'video_youtube'),
        }),
        ('Fechas de Registro', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',), # Esto lo oculta por defecto para limpiar la vista
        }),
    )
    def ver_miniatura(self, obj):
        if obj.imagen_portada: # Ojo: verifica si el nombre en tu modelo es imagen_portada
            return format_html(
                '<img src="{}" style="width: 200px; height: 200px; border-radius: 5px; object-fit: cover;" />', 
                obj.imagen_portada.url)
        return "Sin imagen"

    ver_miniatura.short_description = 'Miniatura'

