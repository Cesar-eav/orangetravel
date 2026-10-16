# Orange Travel — instrucciones para Claude

Leer completo antes de modificar nada. Este archivo **no debe contener valores secretos** (solo nombres de variables).

## Reglas de oro (no olvidar nunca)

1. **Las variables de entorno de Django en producción vienen SOLO de cPanel → Setup Python App → orangetravel.cl → Environment Variables.**
   - El `.htaccess` con `SetEnv` **no llega a Python** (sirve solo para config del web server: redirecciones, headers, SSL). No sirve para cambiar credenciales.
   - Tras cambiar una variable en cPanel: **Restart desde el panel**. `touch tmp/restart.txt` reinicia el proceso pero no re-inyecta variables nuevas de cPanel.
2. **No existe `.env` en producción y no debe existir.** `passenger_wsgi.py` hace `load_dotenv('.env', override=True)`: si aparece un `.env` en el server, pisa las credenciales reales de cPanel (el `.env` local tiene credenciales **sandbox** de Flow). Nunca subir ni crear el `.env` local en el servidor.
   - Existe un `.env_` (con guion bajo) en la raíz de producción: es inerte, no renombrarlo.
3. **Las vars de cPanel no llegan a una shell SSH** (ni activando el virtualenv). Para correr un management command contra la BD real hay que exportar `DATABASE_URL` (y lo que haga falta) a mano en esa sesión, copiando el valor desde cPanel. Sin `DATABASE_URL`, `config/settings.py` cae a un Postgres local (`orage_db`) que no existe en el server → falla sin tocar datos.
   - `python -c "import os; print(os.getenv(...))"` por SSH **no refleja** lo que ve Passenger. Para verificar lo que ve la app: `print` temporal en una vista y revisar `~/logs/passenger.log`.
4. **El shim `import pymysql; pymysql.install_as_MySQLdb()` es obligatorio** en `manage.py` y `passenger_wsgi.py` (mysqlclient no funciona en el hosting). No quitarlo ni comentarlo.
5. **Passenger arranca desde `passenger_wsgi.py`**, no desde `config/wsgi.py` (código muerto en este deploy).
6. Nunca commitear `.env`, API keys, secrets ni contraseñas. Si se documenta una variable, solo su nombre.
7. Producción despliega la rama **`fix-orange`**. No reescribir historial de esa rama (el server hace `git pull`).

## Stack

- Django 5.2 (apps: `home`, `tours`, `payments`, `blog`), admin con Unfold, singletons con `django-solo`.
- Frontend: Tailwind + Vue (`static/src/`, p. ej. `static/src/components/BookingApp.vue`) compilado con Vite → `static/js/dist/`.
- BD: MySQL en producción (vía `DATABASE_URL` + PyMySQL); Postgres local.
- Email: Mailgun vía Anymail (`EMAIL_BACKEND` hardcodeado en `config/settings.py`).
- Media: Cloudinary. Estáticos: WhiteNoise (`collectstatic` → `staticfiles/`).
- Hosting: cPanel + CloudLinux + Passenger (LiteSpeed).

## Variables de entorno (nombres)

`DEBUG`, `DJANGO_SECRET_KEY`, `DATABASE_URL`, `FLOW_API_KEY`, `FLOW_SECRET_KEY`, `FLOW_API_BASE`, `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.

- Local: se leen del `.env` (ignorado por git).
- Producción: cPanel Python App (ver regla 1). Detalle y valores no secretos en `docs/PRODUCCION_VARS_EMAIL.md`.

## Pagos con Flow

- Cliente: `payments/flow.py` (`FlowClient`, firma HMAC-SHA256 sobre los parámetros ordenados).
- Credenciales: `FLOW_API_KEY`, `FLOW_SECRET_KEY`, `FLOW_API_BASE`.
  - Producción: `FLOW_API_BASE=https://www.flow.cl/api`, keys de producción, todo desde cPanel.
  - El default en código (`settings.py` y `flow.py`) es **sandbox** (`https://sandbox.flow.cl/api`); en producción nunca se usa porque cPanel siempre define la variable.
- Rutas (`payments/urls.py`): `checkout/<tour_id>/` → `TourCheckoutView`; `flow-return/` → `FlowReturnView` (vuelta del usuario); `flow-confirm/` → `FlowConfirmView` (webhook servidor a servidor).
- El webhook `flow-confirm` necesita URL pública: **en local nunca llega**. Para probar el email de pago en local:
  ```python
  # python manage.py shell
  from payments.models import Payment
  from payments.emails import enviar_confirmacion_pago
  enviar_confirmacion_pago(Payment.objects.get(id=<ID>))
  ```
- Pasar producción a sandbox temporalmente (solo si es imprescindible): crear `.env` en la raíz del server con las 3 vars sandbox → Restart → probar → **borrar el `.env`** → Restart. Olvidar borrarlo deja el sitio cobrando en sandbox.
- Comando de auditoría: `python manage.py detectar_incongruencias_pago`.

## Emails de notificación

- Flujo 1, reserva sin pago: `tours/views.py` → `enviar_notificaciones_reserva(reserva)` (cliente + admin).
- Flujo 2, pago Flow: `FlowConfirmView` → `payments/emails.py::enviar_confirmacion_pago(payment)` (cliente + admin).
- Flujo 3, cotización: solo los tours de la categoría `TIPO_CON_PRECIO_ID = 1` (Excursiones de un Día, `tours/models.py`, propiedad `Tour.con_precio`) muestran precio y pagan con Flow. El resto muestra «A cotizar» y monta `CotizacionApp.vue` en vez de `BookingApp.vue` → `tours/views.py::crear_cotizacion` guarda una `Cotizacion` y llama a `enviar_notificaciones_cotizacion` (cliente + admin). Se gestionan en `/panel/cotizaciones/`. `TourCheckoutView` rechaza los tours sin precio.
- Enrutamiento del admin: `EMAIL_POR_TOUR` en `tours/views.py`, matching por palabra clave en **`tour.nombre`** (no slug). Sin match → `EMAIL_ADMIN_DEFAULT` (`info@orangetravel.cl`). CC en `CC_RESERVAS`. `payments/emails.py` importa ese mismo diccionario.
- FROM: `noreply@mg.orangetravel.cl` (dominio verificado en Mailgun). Ver `docs/email-deliverability.md`.

## Zonas de tours

- Modelo `Zona` (`tours/models.py`): `Tour.zona` es FK opcional (`PROTECT`). Zonas iniciales creadas por la migración `0016_zonas_iniciales` (Norte Grande, Zona Central, Zona Sur, Zona Austral, Expediciones y Montaña; esta última no es geográfica pero es una zona más).
- Se gestionan en `/panel/zonas/` (nombre, slug, imagen opcional, orden); la zona de cada tour se cambia desde el select en `/panel/tours/` o en la edición del tour.
- `/tours/` (`tours_home.html`) muestra una tarjeta por zona con tours visibles; al elegir una se muestra su `descripcion` (párrafos separados por línea en blanco) y se filtran los tours. El filtro es JS inline (show/hide de tarjetas por `data-zona`, sin Vue) y deja `?zona=<slug>` en la URL. Tours sin zona solo salen en «Todas».
- Precios en CLP con punto de miles: filtro `{% load precios %}{{ valor|clp }}` (`tours/templatetags/precios.py`). `floatformat:"0g"` no sirve: con `es-cl` usa espacio como separador.

## Producción y deploy

- **Servidor: `int15.cpanelhost.cl` (138.117.148.165, LiteSpeed)** desde el 15 oct 2026 15:57 (el hosting trasladó la cuenta desde `srv28`, 190.107.177.38, que quedó como copia vieja sin tráfico). Antes de desplegar, confirmar con `hostname` que la sesión SSH está en int15, y en cPanel que la "Dirección IP compartida" sea 138.117.148.165. cPanel: `https://int15.cpanelhost.cl:2083`.
- Ruta: `/home/cor116358/orangetravel/` (= `~/orangetravel`; `/home3/cor116358` es un enlace a `/home/cor116358`). Rama `fix-orange`, deploy con `git pull` desde el 25 sep 2026 (ya no FTP).
- Python: `~/virtualenv/orangetravel/3.11/bin/python`. **No existe `.venv/` ni `python3`** en el server (`docs/DEPLOY.md` menciona `.venv/bin/python`, pero en producción es el virtualenv).
- Node no está en el PATH: antes de `npm` correr `export PATH=/opt/alt/alt-nodejs22/root/usr/bin:$PATH` (el proyecto pide Node ≥ 22). `node_modules/` ya está instalado (`npm ci`); no correr `npm audit fix` en el server (modifica `package-lock.json`).
- Reiniciar desde cPanel → Setup Python App → Restart. `touch tmp/restart.txt` no está verificado en int15.
- Log: `~/logs/passenger.log` (no verificado en int15).

| Qué cambió | Qué correr en el server tras `git pull` |
|---|---|
| Solo templates | `touch tmp/restart.txt` |
| Python (views, models, urls, admin, settings) | `migrate` si hay migraciones nuevas + `touch tmp/restart.txt` |
| Tailwind/CSS/JS/Vue o `vite.config.mjs` | `npm run build` + `collectstatic --noinput` + restart |
| Archivos nuevos en `static/` | `collectstatic --noinput` + restart |
| Variables de entorno | Editar en cPanel + **Restart desde cPanel** |

- Error "Incomplete response received from application" = Django no arrancó. Revisar `passenger.log`; causa típica: una vista referenciada en `urls.py` que no existe en `views.py`.
- **Modo mantención**: toggle en `/admin/` (modelo `MaintenanceMode` en `home/models.py`, `home/middleware.py`). Los no-staff reciben 503; los staff ven el sitio. Usarlo antes de deploys riesgosos.
- Jailshell de cPanel: no soporta process substitution (`<(...)`); usar archivos temporales.
- Archivos ocultos en el File Manager de cPanel: Settings → Show Hidden Files.

## Documentación de referencia

- `docs/DEPLOY.md`: cuándo hacer build / collectstatic / restart.
- `docs/MIGRACION_GIT.md`: cómo se migró producción de FTP a git y el flujo actual.
- `docs/PRODUCCION_VARS_EMAIL.md`: variables en cPanel, por qué no hay `.env`, DNS y enrutamiento de emails.
- `docs/COTIZACIONES.md`: tours con precio (categoría 1) vs. tours con cotización; flujo, modelo, panel y deploy.
- `docs/email-deliverability.md`: SPF/DKIM/DMARC y Mailgun.
