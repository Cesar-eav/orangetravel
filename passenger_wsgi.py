# passenger_wsgi.py
import os
import sys
import pymysql
pymysql.install_as_MySQLdb()

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()