# Entregabilidad de correo — Orange Travel

## Resultado mail-tester.com

**Puntaje: 10/10** (verificado 2026-08-26)

Correo enviado desde `noreply@mg.orangetravel.cl` vía Mailgun.

## Configuración actual

| Variable | Valor (producción) |
|----------|-------------------|
| `EMAIL_BACKEND` | `anymail.backends.mailgun.EmailBackend` |
| `MAILGUN_SENDER_DOMAIN` | `mg.orangetravel.cl` |
| `DEFAULT_FROM_EMAIL` | `Orange Travel <noreply@mg.orangetravel.cl>` |

## Registros DNS verificados

- **SPF** — `mg.orangetravel.cl` incluye los servidores de Mailgun
- **DKIM** — clave de Mailgun configurada en DNS
- **Dominio** — `mg.orangetravel.cl` verificado en Mailgun

## Cómo repetir la prueba

1. Ir a [mail-tester.com](https://www.mail-tester.com) y copiar la dirección temporal
2. Conectarse al servidor y ejecutar:

```bash
cd /var/www/html/orangetravel && source .venv/bin/activate && python manage.py shell
```

3. Dentro del shell de Django:

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    subject='Test entregabilidad Orange Travel',
    message='Prueba de configuración de correo.',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['DIRECCION_DE_MAIL_TESTER'],
)
```

4. Volver a mail-tester.com y hacer clic en **"Check your score"**

## Notas

- El subdominio `mg.orangetravel.cl` tiene MX apuntando a Mailgun — no crear casillas en cPanel bajo ese subdominio.
- Si el puntaje baja en el futuro, revisar el contenido del correo (links, imágenes, palabras spam) antes que la configuración técnica.
- El `.env` local usa el sandbox de Mailgun (`sandbox3239...mailgun.org`) — no refleja la configuración de producción.
