from django.contrib import admin
from django.utils.html import format_html 
from .models import Post

# IMPORTANTE: Importamos ModelAdmin desde unfold.admin
from unfold.admin import ModelAdmin

@admin.register(Post)
class BlogAdmin(ModelAdmin): # Cambiado a Unfold ModelAdmin
    # Columnas en el listado principal
    list_display = ('ver_miniatura', 'titulo', 'extracto', 'fecha_creacion', 'publicado')
    list_filter = ('publicado', 'fecha_creacion')
    list_editable = ('publicado',) # Unfold hace que esto se vea genial
    search_fields = ('titulo', 'extracto', 'contenido')

    prepopulated_fields = {'slug': ('titulo',)}

    # Campos de solo lectura
    readonly_fields = ('ver_miniatura', 'fecha_creacion', 'fecha_actualizacion')

    # Organización del formulario por secciones (Fieldsets de Unfold)
    fieldsets = (
        ('Configuración Principal', {
            'fields': ('titulo', 'slug', 'autor', 'publicado'),
            # En Unfold, puedes añadir clases para iconos o estilos si quisieras
        }),
        ('Contenido de la Reseña', {
            'fields': ('extracto', 'contenido'),
            'description': 'El extracto se usa para la lista; el contenido es la reseña completa.'
        }),
        ('Multimedia y SEO', {
            'fields': ('imagen_portada', 'video_youtube'),
        }),
        ('Fechas de Registro', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',), # Unfold respeta el colapso nativo de Django
        }),
    )

    def ver_miniatura(self, obj):
        if obj.imagen_portada:
            # Ajustamos un poco el estilo para que se vea más moderno en Unfold
            return format_html(
                '<img src="{}" style="width: 150px; height: 100px; border-radius: 12px; object-fit: cover; shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);" />', 
                obj.imagen_portada.url
            )
        return "Sin imagen"
