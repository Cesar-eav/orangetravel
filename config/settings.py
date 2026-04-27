import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from django.templatetags.static import static

# 1. RUTAS BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent
if os.path.exists(os.path.join(BASE_DIR, '.env')):
    load_dotenv(os.path.join(BASE_DIR, '.env'))

# 2. SEGURIDAD
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tu_53-at5s0jw-&9hkvp+c-%n+rzar(+59pxh!jckw7f!*x!dt')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'orangetravel-production.up.railway.app',
    'localhost',
    'orangetravel.cl',
    'www.orangetravel.cl'
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://orangetravel-production.up.railway.app',
    'http://localhost',
    'https://orangetravel.cl',
    'https://www.orangetravel.cl'
]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True

# 3. APLICACIONES INSTALADAS (Orden corregido para WhiteNoise vs Cloudinary)
INSTALLED_APPS = [
    "whitenoise.runserver_nostatic", 
    "unfold",  
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    
    # Archivos estáticos (Primero WhiteNoise/Django)
    'django.contrib.staticfiles',
    
    # Multimedia (Cloudinary DESPUÉS de staticfiles para que no toque el CSS)
    'cloudinary_storage', 
    'cloudinary',

    'django.contrib.admin',
    # 'django.contrib.humanize',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'solo',

    'home',
    'tours',
    'blog',
    'payments',
    'rest_framework',
    'ckeditor',
    'ckeditor_uploader',
]

# Configuración de Cloudinary (Solo para Media)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB


if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    INTERNAL_IPS = ["127.0.0.1"]

# 4. MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
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
                'home.context_processors.footer_tours',
            ],
        },
    },
]

# 6. CONFIGURACIÓN DE UNFOLD
UNFOLD = {
    "SITE_TITLE": "Orange Travel Admin",
    "SITE_SYMBOL": "travel_explore",
    "COLORS": {
        "primary": {
            "50": "255 248 237",
            "500": "249 115 22", 
            "600": "234 88 12",
        },
    },
    "STYLES": [
        lambda request: static("js/dist/assets/styles.css"),
    ],
}

WSGI_APPLICATION = 'config.wsgi.application'

# 7. BASE DE DATOS
database_url = os.getenv('DATABASE_URL', '')

if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'orage_db',
            'USER': 'cesar',
            'PASSWORD': 'qwedsa',
            'HOST': '127.0.0.1',
            'PORT': 5432,
        }
    }

if not DEBUG and 'mysql' in DATABASES['default'].get('ENGINE', ''):
    DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4'}
elif not DEBUG and 'postgresql' in DATABASES['default'].get('ENGINE', ''):
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

# 8. ARCHIVOS ESTÁTICOS Y MEDIA (Configuración Django 5.2 Clean)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_IGNORE_MISSING_FILES = True 

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": { "BACKEND": "django.core.files.storage.FileSystemStorage" },
        "staticfiles": { "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" },
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 9. CKEDITOR

# X_FRAME_OPTIONS = 'SAMEORIGIN'

CKEDITOR_UPLOAD_PATH = "publicaciones/"
CKEDITOR_IMAGE_BACKEND = "ckeditor_uploader.backends.dummy_backend.DummyBackend"
# settings.py

# settings.py

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'toolbar': 'Custom',
        'height': 500,
        'width': '100%',
        'language': 'es',
        'extraPlugins': ','.join([
            'image2', 'uploadimage', 'widget', 'lineutils', 
            'clipboard', 'dialog', 'justify', 'table', 'maximize'
        ]),
        'removePlugins': 'image',
        'image2_alignClasses': ['image-left', 'image-center', 'image-right'],
        'extraAllowedContent': 'img(image-left,image-right,image-center,img-blog-small,img-blog-medium,img-blog-full);''img(*); div(*); figure(*); figcaption(*); section(*); iframe[*](*)',
        
        
        # VITAL: Aplica tu clase maestra al cuerpo del editor para que se vea igual que en la web
        'bodyClass': 'resena-content',
        
        # VITAL: Carga tu CSS compilado en el editor (ajusta la ruta si es necesario)
        'contentsCss': [
            'https://cdn.tailwindcss.com', # Para que las clases @apply funcionen visualmente
            '/static/js/dist/assets/styles.css', # Tu archivo compilado por Vite
        ],

        'toolbar_Custom': [
            ['Maximize', 'Source'],
            ['Styles', 'Format', 'FontSize'],
            ['Bold', 'Italic', 'Underline', 'Strike', '-', 'TextColor', 'BGColor'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['Image', 'Table', 'HorizontalRule'],
            ['RemoveFormat'],
        ],
        # 'disallowedContent': 'img{float};',

        # MAPEADO DE TU CSS AL MENÚ DE ESTILOS
        'stylesSet': [
            # Posicionamiento (Floats con el padding que ya creaste)
            {"name": "Imagen Izquierda", "element": "img", "attributes": {"class": "image-left"}},
            {"name": "Imagen Derecha", "element": "img", "attributes": {"class": "image-right"}},
            {"name": "Imagen Centrada", "element": "img", "attributes": {"class": "image-center"}},
            
            # Tamaños (Las clases que tienes en el punto 5 de tu CSS)
            {"name": "Tamaño: Pequeña (25%)", "element": "img", "attributes": {"class": "img-blog-small"}},
            {"name": "Tamaño: Mediana (45%)", "element": "img", "attributes": {"class": "img-blog-medium"}},
            {"name": "Tamaño: Completa (100%)", "element": "img", "attributes": {"class": "img-blog-full"}},
            
            # Texto
            {"name": "Texto Naranja Orange", "element": "span", "attributes": {"class": "text-orange-500 font-bold"}},
        ],
    },
}


CKEDITOR_STORAGE_BACKEND = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 10. INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
# USE_L10N = True
# USE_THOUSAND_SEPARATOR = True

# 11. EMAIL (Usando Anymail con la API de Mailgun)
ANYMAIL = {
    "MAILGUN_API_KEY": os.getenv('MAILGUN_API_KEY'),
    "MAILGUN_SENDER_DOMAIN": os.getenv('MAILGUN_SENDER_DOMAIN'),
}
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


if DEBUG:
    SITE_URL = 'http://127.0.0.1:8000'
else:
    SITE_URL = 'https://orangetravel.cl'



# 12 Configuraciones de Flow
FLOW_API_KEY = os.getenv("FLOW_API_KEY")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY")
# En producción cambiar esto a la URL de producción de Flow
FLOW_API_BASE = os.getenv("FLOW_API_BASE", "https://sandbox.flow.cl/api")