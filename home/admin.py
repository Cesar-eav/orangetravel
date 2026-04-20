from django.contrib import admin
from django.utils.html import format_html 
from solo.admin import SingletonModelAdmin
from .models import Nosotros

# Register your models here.

@admin.register(Nosotros)
class NosotrosAdmin(SingletonModelAdmin):
    pass