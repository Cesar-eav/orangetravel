release: python -u check_deploy.py && python manage.py makemigrations tours --noinput && python manage.py migrate --noinput
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT