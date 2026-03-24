release: python manage.py migrate --noinput
web: python -u check_deploy.py && gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 600