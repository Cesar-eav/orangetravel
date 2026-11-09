# passenger_wsgi.py
import os
import sys
import pymysql
pymysql.install_as_MySQLdb()

# En int15 Passenger arranca Python con stdout en ASCII: un print() con emoji o tildes
# lanzaba UnicodeEncodeError y cortaba el envío de emails (desde el 15 oct 2026).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:  # noqa: BLE001 — Passenger podría dar un stream sin reconfigure
        pass

# Si existe .env en la raíz del proyecto, sus valores sobreescriben los de cPanel
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
_django_app = get_wsgi_application()


def application(environ, start_response):
    # El wsgi.file_wrapper de LiteSpeed no soporta el SlicedFile que WhiteNoise
    # usa para las respuestas 206: los GET con "Range" (videos) daban 500.
    # Sin file_wrapper, Django envía el archivo leyéndolo por bloques.
    if 'HTTP_RANGE' in environ:
        environ.pop('wsgi.file_wrapper', None)
    return _django_app(environ, start_response)