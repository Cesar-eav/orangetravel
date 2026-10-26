from django.contrib import admin
from django.utils.html import format_html 
from solo.admin import SingletonModelAdmin
from modeltranslation.admin import TranslationAdmin
from .models import Nosotros, MaintenanceMode, SitioIngles

# Register your models here.

@admin.register(Nosotros)
class NosotrosAdmin(SingletonModelAdmin, TranslationAdmin):
    pass


@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(SingletonModelAdmin):
    pass


@admin.register(SitioIngles)
class SitioInglesAdmin(SingletonModelAdmin):
    pass