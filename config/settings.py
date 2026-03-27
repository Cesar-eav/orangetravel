import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from django.templatetags.static import static

# 1. RUTAS BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent
if os.path.exists(os.path.join(BASE_DIR, '.env')):
    load_dotenv(os.path.join(BASE_DIR, '.env'))

# 2. SEGURIDAD (Configuración dinámica para Railway/Local)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tu_53-at5s0jw-&9hkvp+c-%n+rzar(+59pxh!jckw7f!*x!dt')

# IMPORTANTE: En Railway, crea una variable DEBUG = False
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    # '*',
    '127.0.0.1',
    'orangetravel-production.up.railway.app',
    'localhost',
    # '.railway.app',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://orangetravel-production.up.railway.app',
    'http://localhost',
]


if not DEBUG:
    # Esto es vital para que Railway no te de 502 por SSL
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True



# 3. APLICACIONES INSTALADAS
INSTALLED_APPS = [
    "unfold",  # SIEMPRE PRIMERO
    "unfold.contrib.filters",
    "unfold.contrib.forms",

    'cloudinary_storage', # Debe ir antes de staticfiles
    'cloudinary',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'ckeditor',
    'ckeditor_uploader',

    # APPS PROPIAS
    'home',
    'tours',
    'blog',
]

# Configuración de Cloudinary
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET')
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    INTERNAL_IPS = ["127.0.0.1"]

# 4. MIDDLEWARE (Orden crítico para WhiteNoise y DebugToolbar)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Segundo lugar para estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    # Se inserta en la posición 3 para no interferir con WhiteNoise
    MIDDLEWARE.insert(2, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'config.urls'

# 5. TEMPLATES
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

# 6. CONFIGURACIÓN DE UNFOLD (Tailwind 4 Integration)
UNFOLD = {
    "SITE_TITLE": "Orange Travel Admin",
    "SITE_SYMBOL": "travel_explore",
    "COLORS": {
        "primary": {
            "50": "255 248 237",
            "500": "249 115 22", # Naranja Orange Travel
            "600": "234 88 12",
        },
    },
    "STYLES": [
        lambda request: static("css/output.css"), # Tu CSS de Tailwind 4
    ],
}

WSGI_APPLICATION = 'config.wsgi.application'

# 7. BASE DE DATOS (Conexión Inteligente)
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Si no hay DATABASE_URL (Estamos en local), usamos tu Postgres manual
if not DATABASES['default']:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'orage_db',
        'USER': 'cesar',
        'PASSWORD': 'qwedsa',
        'HOST': '127.0.0.1',
        'PORT': 5432,
    }

# Obligar SSL en producción (Railway)
if not DEBUG and DATABASES['default']:
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

# 8. ARCHIVOS ESTÁTICOS Y MEDIA
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Soporte para compresión de WhiteNoise en producción

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 9. CKEDITOR (Configuración avanzada para Tailwind)
CKEDITOR_UPLOAD_PATH = "publicaciones/"
CKEDITOR_IMAGE_BACKEND = "pillow"

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'toolbar': 'Custom',
        'height': 500,
        'width': '100%',
        'language': 'es',
        'extraPlugins': ','.join(['image2', 'uploadimage', 'widget', 'lineutils', 'clipboard', 'dialog']),
        'removePlugins': 'image',
        'extraAllowedContent': 'img(*); div(*); figure(*); figcaption(*);',
        'contentsCss': [
            'https://cdn.tailwindcss.com',
            '/static/css/output.css',
        ],
        'bodyClass': 'resena-content', # Clase padre de tus estilos
        'toolbar_Custom': [
            ['Styles', 'Format', 'FontSize'],
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Blockquote'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['Image', 'Table', 'HorizontalRule'],
            ['TextColor', 'BGColor'],
            ['Maximize', 'Source'],
        ],
        'stylesSet': [
            {'name': 'Texto Naranja', 'element': 'span', 'attributes': {'class': 'text-orange-500 font-bold'}},
            {'name': 'Imagen 25%', 'element': 'img', 'attributes': {'class': 'img-blog-small'}, 'type': 'widget', 'widget': 'image'},
            {'name': 'Imagen 50%', 'element': 'img', 'attributes': {'class': 'img-blog-medium'}, 'type': 'widget', 'widget': 'image'},
            {'name': 'Imagen 100%', 'element': 'img', 'attributes': {'class': 'img-blog-full'}, 'type': 'widget', 'widget': 'image'},
        ],
    },
}
CKEDITOR_STORAGE_BACKEND = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 10. INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# 11. EMAIL (Mailgun)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_CONTACTO_RECIBIDO = 'cesar.eav@gmail.com'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Orange Travel <noreply@orangetravel.cl>')

# 12. OTROS
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'