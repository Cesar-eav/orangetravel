from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField 
from solo.models import SingletonModel

# Create your models here.

class Nosotros(SingletonModel):

    contenido = RichTextUploadingField(verbose_name="Contenido")
    def __str__(self):
        return f"Pagina Nosotros"

    class Meta:
        verbose_name = "Nosotros"
        verbose_name_plural ="Nosotros"


class MaintenanceMode(SingletonModel):
    activo = models.BooleanField(default=False, verbose_name="Activo")
    mensaje = RichTextUploadingField(
        verbose_name="Mensaje",
        default="Estamos realizando tareas de mantención. Vuelve pronto.",
    )

    def __str__(self):
        return "Modo Mantención"

    class Meta:
        verbose_name = "Modo Mantención"
        verbose_name_plural = "Modo Mantención"


class SitioIngles(SingletonModel):
    """Interruptores de la versión en inglés (/en/): acceso por link y anuncio (banderas + Google)."""
    publico = models.BooleanField(
        default=True,
        verbose_name="/en/ accesible para todos",
        help_text="Cualquiera con el link puede ver /en/. Apagado, solo los usuarios staff pueden verla.",
    )
    mostrar_banderas = models.BooleanField(
        default=False,
        verbose_name="Mostrar banderas ES | EN y dejar que Google indexe /en/",
        help_text="Mientras esté apagado no hay selector de idioma para el público y /en/ "
                  "lleva «noindex», sin hreflang. Encenderlo también hace /en/ accesible.",
    )

    def __str__(self):
        return "Sitio en inglés"

    class Meta:
        verbose_name = "Sitio en inglés"
        verbose_name_plural = "Sitio en inglés"
