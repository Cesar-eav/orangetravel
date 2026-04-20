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
