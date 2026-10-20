"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static


# Sin prefijo de idioma: admin/panel en español, URLs fijas para Flow
# (pagos/) y APIs que Vue llama con rutas absolutas (tours/api/).
urlpatterns = [
    # path('jet/', include('jet.urls', 'jet')),  # URLs de JET
    # path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')), #
    path('admin/', admin.site.urls),
    path('panel/', include('panel.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('i18n/', include('django.conf.urls.i18n')),

    path('tours/api/', include('tours.api_urls')),
    path('pagos/', include('payments.urls')),
]

# Páginas públicas: español sin prefijo (/tours/), inglés con /en/.
urlpatterns += i18n_patterns(
    path('', include('home.urls')),
    path('tours/', include('tours.urls')),
    path('blog/', include('blog.urls')),
    prefix_default_language=False,
)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns