release: python manage.py makemigrations --noinput && python manage.py migrate --noinput && python check_deploy.py
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT