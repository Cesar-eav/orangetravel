# passenger_wsgi.py
import os
import sys
import pymysql
pymysql.install_as_MySQLdb()

# Si existe .env en la raíz del proyecto, sus valores sobreescriben los de cPanel
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()