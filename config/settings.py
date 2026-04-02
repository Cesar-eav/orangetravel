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
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://orangetravel-production.up.railway.app',
    'http://localhost',
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
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'home',
    'tours',
    'blog',

    'ckeditor',
    'ckeditor_uploader',
]

# Configuración de Cloudinary (Solo para Media)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

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
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

if not DATABASES['default']:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'orage_db',
        'USER': 'cesar',
        'PASSWORD': 'qwedsa',
        'HOST': '127.0.0.1',
        'PORT': 5432,
    }

if not DEBUG and DATABASES['default']:
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
        'toolbar_Custom': [
            ['Styles', 'Format', 'FontSize'],
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Blockquote'],
            ['Link', 'Unlink'],
            ['Image', 'Source'],
        ],
    },
}
CKEDITOR_STORAGE_BACKEND = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 10. INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# 11. EMAIL
# 11. EMAIL (Usando Anymail con la API de Mailgun)
ANYMAIL = {
    "MAILGUN_API_KEY": os.getenv('MAILGUN_API_KEY'),
    "MAILGUN_SENDER_DOMAIN": os.getenv('MAILGUN_SENDER_DOMAIN'),
}
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


if DEBUG:
    # Cuando estás en tu PC
    SITE_URL = 'http://127.0.0.1:8000'
else:
    # Cuando estás en Railway (Cambia esto por tu URL real de Railway)
    SITE_URL = 'https://orangetravel.up.railway.app'