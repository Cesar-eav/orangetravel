"""
Django settings for config project.
Configurado para despliegue en Railway.com
"""

import os
from pathlib import Path
from dotenv import load_dotenv 
import dj_database_url  # Importante para la base de datos en Railway

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))


# --- CONFIGURACIÓN DE PRODUCCIÓN (Variables de Entorno) ---

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tu_53-at5s0jw-&9hkvp+c-%n+rzar(+59pxh!jckw7f!*x!dt')

DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

# En Railway, puedes poner ".railway.app,localhost" en la variable de entorno
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if os.getenv('DJANGO_ALLOWED_HOSTS') else []


# --- APLICACIONES ---

INSTALLED_APPS = [
    'jet_reboot',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ckeditor',
    'ckeditor_uploader',

    # APP ORANGE TRAVEL
    'home',
    'tours',
    'blog'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Servidor de estáticos para producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# --- BASE DE DATOS (Configuración Dinámica) ---

DATABASES = {
    'default': dj_database_url.config(
        # Si no hay DATABASE_URL (local), usa tu Postgres de desarrollo
        default='postgresql://cesar:qwedsa@127.0.0.1:5432/orage_db',
        conn_max_age=600
    )
}


# --- VALIDACIÓN DE CONTRASEÑAS ---

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- INTERNACIONALIZACIÓN ---

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# --- ARCHIVOS ESTÁTICOS Y MEDIA ---

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuración para que WhiteNoise comprima y use caché (optimización)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# --- CONFIGURACIÓN CKEDITOR ---

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'toolbar': 'Custom',
        'height': 600,
        'width': '100%',
        'language': 'es',
        'extraAllowedContent': 'img(*); div(*); figure(*); figcaption(*);',
        'extraPlugins': ','.join(['image2', 'uploadimage', 'widget', 'lineutils', 'clipboard', 'dialog', 'dialogui']),
        'removePlugins': 'image',
        'disallowedContent': 'img{width,height}[width,height]',
        'extraConfig': {
            'image2_disableResizer': True,
        },
        'contentsCss': [
            'https://cdn.tailwindcss.com',
            '/static/css/output.css',
        ],
        'bodyClass': 'resena-content',
        'toolbar_Custom': [
            ['Styles', 'Format', 'FontSize'],
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['Image', 'Table', 'HorizontalRule', 'SpecialChar'],
            ['TextColor', 'BGColor'],
            ['Maximize', 'Source'],
        ],
        'image2_alignClasses': ['image-left', 'image-center', 'image-right'],
        'image2_captionedClass': 'image-captioned',
        'stylesSet': [
            {'name': 'Texto Alerta Naranja', 'element': 'span', 'attributes': { 'class': 'text-orange-500 font-bold' }},
            {'name': 'Imagen Pequeña (25%)', 'element': 'img', 'attributes': { 'class': 'img-blog-small' }, 'type': 'widget', 'widget': 'image'},
            {'name': 'Imagen Mediana (50%)', 'element': 'img', 'attributes': { 'class': 'img-blog-medium' }, 'type': 'widget', 'widget': 'image'},
            {'name': 'Imagen Full (100%)', 'element': 'img', 'attributes': { 'class': 'img-blog-full' }, 'type': 'widget', 'widget': 'image'},
        ],
    },
}

CKEDITOR_UPLOAD_PATH = "publicaciones/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_RESTRICT_BY_USER = True


# --- SEGURIDAD Y HTTPS ---

# DJANGO JET (Mantenemos comentado por tu solicitud)
# JET_INDEX_DASHBOARD = 'dashboard.CustomIndexDashboard'
# JET_APP_INDEX_DASHBOARD = 'dashboard.CustomAppIndexDashboard'

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Confianza para el dominio de Railway (evita errores 403 en formularios)
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if 'localhost' not in host and host]

if not DEBUG:
    # Configuraciones de seguridad obligatorias para Railway (HTTPS)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --- OTROS ---

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')     
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')
EMAIL_CONTACTO_RECIBIDO = 'cesar.eav@gmail.com'