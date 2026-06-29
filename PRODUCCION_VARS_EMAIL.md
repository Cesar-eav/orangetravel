# Variables de entorno y email en producción

## Cómo llegan las variables de entorno a Django

En producción (cPanel + CloudLinux + Passenger), **no se usa archivo `.env`**.

Las variables se configuran en el `.htaccess` con `SetEnv`:

```apache
<IfModule Litespeed>
    SetEnv MAILGUN_API_KEY ...
    SetEnv MAILGUN_SENDER_DOMAIN mg.orangetravel.cl
    ...
</IfModule>

<IfModule mod_env.c>
    SetEnv MAILGUN_API_KEY ...
    SetEnv MAILGUN_SENDER_DOMAIN mg.orangetravel.cl
    ...
</IfModule>
```

Ambos bloques son necesarios porque cPanel puede correr con LiteSpeed o Apache según la operación.

## Por qué NO hay `.env` en producción

`passenger_wsgi.py` tiene:

```python
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
```

El `override=True` significa que **si existiera un `.env` en el servidor, sobreescribiría las variables del `.htaccess`**. El `.env` local (desarrollo) usa credenciales de sandbox de Mailgun — si se sube accidentalmente a producción via FTP, los emails dejarían de funcionar.

**Regla:** nunca subir el `.env` local al servidor de producción.

## Configuración de Mailgun

| Variable | Valor en producción |
|---|---|
| `MAILGUN_API_KEY` | key real (ver `.htaccess`) |
| `MAILGUN_SENDER_DOMAIN` | `mg.orangetravel.cl` |
| `DEFAULT_FROM_EMAIL` | `info@orangetravel.cl` |
| `EMAIL_BACKEND` | `anymail.backends.mailgun.EmailBackend` |

El dominio `mg.orangetravel.cl` debe estar verificado en el dashboard de Mailgun (DNS: registros MX, TXT SPF y DKIM en el panel de cPanel del dominio).

## Enrutamiento de emails admin por tour

Definido en `tours/views.py`. El matching se hace sobre el **nombre del tour** (no el slug):

```python
EMAIL_POR_TOUR = {
    'atacama':        'BastianDiaz10@gmail.com',
    'cotacotani':     'BastianDiaz10@gmail.com',
    'surire':         'BastianDiaz10@gmail.com',
    'desde san pedro':'BastianDiaz10@gmail.com',
}
EMAIL_ADMIN_DEFAULT = 'info@orangetravel.cl'
CC_RESERVAS = 'reservas@orangetravel.cl'
```

- Si el nombre del tour contiene alguna keyword → va a Bastian + CC a `reservas@orangetravel.cl`
- Si no hay match → va a `info@orangetravel.cl` sin CC

Este mismo diccionario se importa en `payments/emails.py` para los emails de confirmación de pago.

## Flujo completo de emails

### Reserva sin pago (formulario web)
`tours/views.py` → `crear_reserva` → thread → `enviar_notificaciones_reserva`
- Email cliente: "Solicitud Recibida" → `reserva.email_cliente`
- Email admin: "NUEVA RESERVA" → según tour + CC si corresponde

### Pago confirmado (webhook Flow)
`payments/views.py` → `FlowConfirmView` → `enviar_confirmacion_pago`
- Email cliente: "Reserva Confirmada" → `payment.customer_email`
- Email admin: "PAGO RECIBIDO" → según tour + CC si corresponde
