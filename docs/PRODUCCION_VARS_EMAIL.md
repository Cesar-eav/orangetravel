# Variables de entorno y email en producción

## Dos mecanismos que coexisten

En producción (cPanel + CloudLinux + Passenger) hay **dos sistemas de variables de entorno separados** que sirven propósitos distintos:

| Mecanismo | Qué afecta |
|---|---|
| **cPanel → Python App → Environment Variables** | El proceso Django (Passenger) — lo que lee `os.getenv()` en Python |
| **`.htaccess` SetEnv** | LiteSpeed/Apache a nivel web server — redirecciones, headers, SSL, archivos estáticos |

El `.htaccess` fue necesario en algún momento para configuración a nivel servidor y debe mantenerse. Lo que **no funciona** es pasar variables Python via `.htaccess` — Passenger no las hereda del web server.

**Regla:** para cambiar variables que usa Django → cPanel Python App. Para config del web server → `.htaccess`.

---

## Variables de Django: cPanel Python App

**cPanel → Setup Python App → orangetravel.cl → Environment Variables**

Este es el único mecanismo que Passenger lee de forma confiable para la app Python.

Para reiniciar la app después de un cambio:
- Desde cPanel: Setup Python App → Restart
- Desde terminal: `touch /home3/cor116358/orangetravel/tmp/restart.txt`

### Variables configuradas (jul 2026)

| Variable | Valor |
|---|---|
| `DEFAULT_FROM_EMAIL` | `noreply@mg.orangetravel.cl` |
| `MAILGUN_API_KEY` | key real de Mailgun |
| `MAILGUN_SENDER_DOMAIN` | `mg.orangetravel.cl` |
| `FLOW_API_KEY` | key producción Flow (`53158FEB-...`) |
| `FLOW_SECRET_KEY` | secret producción Flow |
| `FLOW_API_BASE` | `https://www.flow.cl/api` |
| `DATABASE_URL` | `mysql://cor116358_admin:...@localhost/cor116358_orangetravel` |
| `DEBUG` | `False` |

`EMAIL_BACKEND = anymail.backends.mailgun.EmailBackend` está hardcodeado en `config/settings.py`.

---

## Por qué NO hay `.env` en producción

`passenger_wsgi.py` tiene:

```python
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
```

El `override=True` significa que **si existiera un `.env` en el servidor, sobreescribiría las variables de cPanel**. Confirmado: no existe `.env` en `/home3/cor116358/orangetravel/`.

El `.env` local usa credenciales sandbox — si se sube accidentalmente al servidor via FTP, las variables de cPanel quedan anuladas y todo deja de funcionar.

**Regla:** nunca subir el `.env` local al servidor de producción.

---

## Configuración DNS y anti-spoofing (jul 2026)

| Registro | Valor |
|---|---|
| SPF `orangetravel.cl` | `v=spf1 include:_spf.cpanelhost.cl -all` |
| DMARC `_dmarc.orangetravel.cl` | `v=DMARC1; p=quarantine; rua=mailto:info@orangetravel.cl;` |
| SPF `mg.orangetravel.cl` | `v=spf1 include:mailgun.org ~all` |
| DKIM `mg.orangetravel.cl` | configurado por Mailgun (Active) |

El FROM de los emails del sistema es `noreply@mg.orangetravel.cl` (dominio verificado en Mailgun). Esto separa los correos legítimos del sistema de posibles spoofs de `info@orangetravel.cl`.

---

## Enrutamiento de emails admin por tour

Definido en `tours/views.py`. El matching se hace sobre el **nombre del tour** (no el slug):

```python
EMAIL_POR_TOUR = {
    'atacama':         'BastianDiaz10@gmail.com',
    'cotacotani':      'BastianDiaz10@gmail.com',
    'surire':          'BastianDiaz10@gmail.com',
    'desde san pedro': 'BastianDiaz10@gmail.com',
}
EMAIL_ADMIN_DEFAULT = 'info@orangetravel.cl'
CC_RESERVAS = 'reservas@orangetravel.cl'
```

- Tours con keyword en el nombre → Bastian + CC a `reservas@orangetravel.cl`
- Sin match → `info@orangetravel.cl` sin CC

El mismo diccionario se importa en `payments/emails.py`.

---

## Flujo completo de emails

### Reserva sin pago (formulario web)
`tours/views.py` → `crear_reserva` → thread → `enviar_notificaciones_reserva`
- Cliente: "Solicitud Recibida" → `reserva.email_cliente`
- Admin: "NUEVA RESERVA" → según tour + CC si corresponde

### Pago confirmado (webhook Flow)
`payments/views.py` → `FlowConfirmView` → `enviar_confirmacion_pago`
- Cliente: "Reserva Confirmada" → `payment.customer_email`
- Admin: "PAGO RECIBIDO" → según tour + CC si corresponde
