# Orange Travel — Arquitectura, funcionalidades y tecnologías

Documento para entender cómo está construido orangetravel.cl. Describe el estado actual del código (octubre 2026). No contiene valores secretos, solo nombres de variables.

## 1. Qué es el sitio

Sitio web de una agencia de turismo en Arica (Chile). Permite:

- Mostrar el catálogo de tours, un blog de reseñas y páginas informativas.
- Reservar un tour **con pago online** (Flow) o **sin pago** (solicitud que el equipo confirma).
- Gestionar todo el contenido, reservas y pagos desde un panel interno.

Es una aplicación **monolítica Django** que renderiza HTML en el servidor. Solo el widget de reserva es una mini-aplicación Vue incrustada en la página del tour.

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11, Django 5.2, Django REST Framework (solo para el checkout y los webhooks de pago) |
| Base de datos | MySQL en producción (driver PyMySQL, vía `DATABASE_URL`); PostgreSQL en local |
| Frontend | Templates Django + Tailwind CSS 4 + Vue 3 (solo el widget de reserva), compilados con Vite 6 |
| Calendario / HTTP en el widget | `v-calendar` (selector de fecha) y `axios` |
| Admin | Django Admin con tema **Unfold** (`/admin/`) |
| Panel propio | App `panel` (`/panel/`), server-rendered, pensada para personas no técnicas |
| Singletons (páginas de una sola instancia) | `django-solo` |
| Editor de texto enriquecido | `django-ckeditor` (+ `ckeditor_uploader`) |
| Pagos | **Flow.cl** (cliente propio con firma HMAC-SHA256) |
| Email | **Mailgun** vía `django-anymail` |
| Imágenes (media) | **Cloudinary** (`django-cloudinary-storage`) en producción; sistema de archivos en local |
| Estáticos | **WhiteNoise** (`collectstatic` → `staticfiles/`) |
| Hosting producción | cPanel + CloudLinux + Passenger (LiteSpeed) |
| Hosting alternativo | `Procfile` y `nixpacks.toml` (Railway), conservados pero no son el deploy actual |

Dependencias exactas: `requirements.txt` (Python) y `package.json` (Node ≥ 22).

## 3. Estructura del repositorio

```
config/            Configuración Django (settings.py, urls.py). wsgi.py NO se usa en producción
passenger_wsgi.py  Punto de entrada real en producción (Passenger)
manage.py          Entrada de comandos Django (ambos archivos hacen el shim de PyMySQL)

home/              Portada, Nosotros, Contacto, Términos, Otros servicios, modo mantención
tours/             Catálogo, reservas, bloqueos de fechas, Tercera Edad, signals de email
payments/          Integración Flow, modelo Payment, emails de pago, comando de auditoría
blog/              Reseñas (posts) con imágenes intercaladas y carrusel
panel/             Panel de gestión para usuarios staff (alternativa al admin)

templates/         Layout global: base.html, includes/ (navbar, footer, contacto), maintenance.html
static/src/        Fuente del frontend: main.js, BookingApp.vue, input.css (Tailwind)
static/js/dist/    Salida de Vite (ignorada por git; se genera con npm run build)
docs/              Documentación operativa (deploy, panel, emails, propuesta de traducción)
```

Cada app Django sigue el esquema `models / views / urls / admin / templates / migrations`.

## 4. Apps y modelos de datos

### `tours`
- **TipoTour**: categoría (nombre, descripción).
- **Tour**: nombre, slug, descripción, itinerario, YouTube, imagen principal, mapa, `activo`, `destacado`, `es_prueba` (oculta tours de prueba del listado). FK a `TipoTour`.
- **GaleriaTour**: fotos adicionales de un tour.
- **ItinerarioDia**: días del itinerario (orden, título, descripción) para tours de varios días.
- **PrecioTour** (1 a 1 con Tour): precio adulto, y opcionalmente precio niño (`tiene_precio_nino`). Valores en CLP.
- **Reserva**: datos del cliente, fecha, adultos, niños, `precio_total` (se calcula en `save()` a partir de `PrecioTour`), `estado` (PENDIENTE / CONFIRMADA / CANCELADA), notas internas, código único legible (`OT-XXXXXX`, alfabeto sin caracteres ambiguos). **Borrado lógico** (`borrado_el`; `Reserva.objects` excluye borradas, `all_objects` las incluye).
- **BloqueoTour**: fecha bloqueada manualmente para un tour (única por tour+fecha).
- **TerceraEdad** (singleton): contenido de la página de tercera edad.

### `payments`
- **Payment**: pago de Flow. Estados `pending / paid / failed / canceled`. Guarda monto y moneda (CLP), token y orden del proveedor, datos del cliente, fecha de reserva, pasajeros, un **snapshot del nombre y precios del tour al pagar** (para auditoría si el tour cambia), código único, las respuestas crudas de Flow (`raw_*` JSON) y borrado lógico (`deleted_at`). FK al Tour con `PROTECT`.

### `blog`
- **Post**: título, slug, autor (User), extracto (máx. 500), cuerpo CKEditor, portada, video YouTube, `publicado`.
- **ImagenPost**: imagen insertada tras el párrafo N del cuerpo (con pie de foto y orden).
- **ImagenCarousel**: carrusel de imágenes del post.

### `home`
- **Nosotros** (singleton): contenido de la página "Nosotros".
- **MaintenanceMode** (singleton): interruptor y mensaje del modo mantención.

## 5. Rutas principales

| Prefijo | Qué hace |
|---|---|
| `/` | Portada, `nosotros`, `contacto/`, `contacto_formulario/` (POST, envía email), `terminos_y_condiciones/`, `otros-servicios/` |
| `/tours/` | Listado (separa "turismo aventura" del resto), `tour/<slug>/` detalle, `tercera_edad/` |
| `/tours/api/reserva/crear/` | POST JSON: crea una reserva sin pago |
| `/tours/api/bloqueos/<tour_id>/` | GET JSON: fechas no disponibles para el calendario |
| `/tours/api/admin/pagos/<tour_id>/` | GET JSON agregado por fecha, solo staff |
| `/blog/` | Listado de reseñas y detalle por slug |
| `/pagos/checkout/<tour_id>/` | POST: crea Payment + Reserva y devuelve la URL de pago de Flow |
| `/pagos/flow-return/` | Vuelta del usuario desde Flow |
| `/pagos/flow-confirm/` | Webhook servidor-a-servidor de Flow |
| `/pagos/vista_confirmacion_pago/<id>` | Pantalla de confirmación al cliente |
| `/panel/...` | Panel de gestión (ver sección 8) |
| `/admin/` | Django Admin (Unfold) |
| `/ckeditor/` | Subida de imágenes del editor |

## 6. Flujos clave

### 6.1 Reserva con pago (Flow)

```
Página del tour ──► Widget Vue (BookingApp.vue)
   1. GET  /tours/api/bloqueos/<id>/   → pinta fechas no disponibles
   2. Cliente elige fecha y pasajeros, calcula total
   3. POST /pagos/checkout/<id>/       → valida (email, fecha ≥ hoy+3 días)
        crea Payment(pending) + Reserva(PENDIENTE)
        llama a Flow create_payment → devuelve redirect_url
   4. Navegador redirige a Flow (pago)
   5a. Flow ──POST──► /pagos/flow-confirm/   (webhook; responde siempre 200)
        consulta get_status a Flow → si pagado: Payment=paid + emails
   5b. Navegador ──► /pagos/flow-return/     (misma verificación, idempotente)
        → pantalla de confirmación o de fallo
```

- `payments/flow.py::FlowClient` firma los parámetros ordenados con HMAC-SHA256 y habla con `FLOW_API_BASE`.
- El estado de Flow se **consulta siempre a Flow** (no se confía en lo que llega por el navegador). Estados terminales fallidos marcan el pago como `failed`.
- Al pagar se llama a `enviar_confirmacion_pago(payment)` (`payments/emails.py`): email al cliente y al administrador del tour.
- Una fecha con un Payment `paid` aparece bloqueada en el calendario.

### 6.2 Reserva sin pago

`POST /tours/api/reserva/crear/` crea una `Reserva` PENDIENTE y lanza `enviar_notificaciones_reserva` en un **hilo aparte** (la respuesta no espera al email). Un administrador la confirma o cancela desde el panel/admin.

### 6.3 Cambio de estado de una reserva (signal)

`tours/signals.py` (`pre_save` de `Reserva`): al pasar a CONFIRMADA envía email de confirmación al cliente; al pasar a CANCELADA/RECHAZADA avisa al cliente y **cancela el Payment pagado** de esa fecha para liberar el calendario.

### 6.4 Enrutamiento de emails por tour

El diccionario `EMAIL_POR_TOUR` (`tours/views.py`) elige el destinatario administrador según palabras clave en `tour.nombre` (no en el slug). Sin coincidencia se usa `EMAIL_ADMIN_DEFAULT`. `CC_RESERVAS` va en copia. `payments/emails.py` reutiliza el mismo diccionario. Remitente: `noreply@mg.orangetravel.cl` (dominio verificado en Mailgun).

### 6.5 Modo mantención

`home/middleware.py::MaintenanceModeMiddleware`: si está activo, los visitantes ven `maintenance.html` con HTTP 503; los usuarios staff ven el sitio normal. `/admin/`, `/panel/`, `/ckeditor/`, estáticos y media están exentos.

### 6.6 Contexto global

`home/context_processors.py::footer_tours` inyecta los tours en el pie de página de todas las plantillas.

## 7. Frontend

- **Páginas**: HTML renderizado por Django (`templates/base.html` + templates de cada app) con clases Tailwind.
- **Widget de reserva**: `static/src/main.js` busca el elemento `#reservation-widget` en la página del tour, lee sus `data-*` (precios, id del tour) y monta `BookingApp.vue`. Esto es lo único que usa Vue.
- **Build**: `npm run build` (Vite) genera `static/js/dist/assets/main.js` y `main.css`, que los templates referencian. Vite incluye el plugin de Tailwind 4 y un alias de Vue al bundler con compilador de templates.
- `static/` está en `.gitignore`: lo compilado **no** viaja por git; se construye en cada entorno.

## 8. Panel de gestión (`/panel/`)

Alternativa al admin para usuarios no técnicos. Vistas basadas en clases con `StaffRequiredMixin` (solo `is_staff`), estilos en línea en `panel/templates/panel/base.html` (no requiere build).

| Sección | Capacidad |
|---|---|
| Inicio | Contadores: reservas por confirmar, próximas confirmadas, pagos de 7 días |
| Reservas | Buscar/filtrar, cambiar estado, notas internas, borrado lógico |
| Pagos | Solo lectura, filtros, reenvío de emails al cliente o administradores |
| Tours | Crear/editar con itinerario, mapa, precios, galería múltiple. No se borran: se desactivan |
| Categorías | CRUD con protección si tienen tours |
| Bloqueos | Bloquear/desbloquear fechas por tour |
| Blog | CRUD con imágenes entre párrafos y carrusel |
| Nosotros / Tercera edad / Mantención | Edición de los singletons |

Más detalle en `docs/PANEL.md`. El panel y el admin conviven y comparten base de datos y usuarios.

## 9. Configuración y entornos

Variables de entorno (solo nombres): `DEBUG`, `DJANGO_SECRET_KEY`, `DATABASE_URL`, `FLOW_API_KEY`, `FLOW_SECRET_KEY`, `FLOW_API_BASE`, `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.

| | Local | Producción |
|---|---|---|
| Variables | archivo `.env` (ignorado por git; credenciales **sandbox** de Flow) | Solo cPanel → Setup Python App |
| BD | PostgreSQL | MySQL (`utf8mb4`) |
| Media | Disco (`media/`) | Cloudinary |
| Flow | `sandbox.flow.cl` | `www.flow.cl` |
| Extras | Django Debug Toolbar | — |

Particularidades que conviene conocer:

- `passenger_wsgi.py` hace `load_dotenv('.env', override=True)`: **no debe existir `.env` en producción**, porque pisaría las credenciales reales.
- El shim `pymysql.install_as_MySQLdb()` es obligatorio en `manage.py` y `passenger_wsgi.py` (mysqlclient no funciona en el hosting).
- `LANGUAGE_CODE = es-cl`, zona horaria `America/Santiago`. El sitio es solo en español (hay una propuesta de versión en inglés en `docs/PROPUESTA_TRADUCCION_EN.md`).
- Reglas de negocio con valores fijos en código: anticipación mínima de reserva de 3 días (`tours/views.py` y `payments/views.py`).

## 10. Deploy

Producción corre la rama `fix-orange` en `~/orangetravel` (cPanel) y se actualiza con `git pull`.

| Qué cambió | Qué hacer en el servidor |
|---|---|
| Solo templates | `touch tmp/restart.txt` |
| Python (views, models, urls, admin, settings) | `migrate` si hay migraciones + restart |
| Tailwind/CSS/JS/Vue | `npm run build` + `collectstatic --noinput` + restart |
| Archivos nuevos en `static/` | `collectstatic --noinput` + restart |
| Variables de entorno | Editar en cPanel y hacer Restart desde el panel |

Comando de auditoría de pagos: `python manage.py detectar_incongruencias_pago`.
Más detalle: `docs/DEPLOY.md`, `docs/MIGRACION_GIT.md`, `docs/PRODUCCION_VARS_EMAIL.md`, `docs/email-deliverability.md`.

## 11. Pruebas

Existen tests en `panel/tests.py` (acceso, filtros, estados, borrado lógico, reenvío de emails, 403/404) y archivos `tests.py` en las demás apps. Para ejecutarlos en local con SQLite:

```bash
DATABASE_URL=sqlite:////tmp/panel_test.sqlite3 python manage.py test panel
```

## 12. Deuda técnica conocida

- `config/wsgi.py` es código muerto en el deploy actual (Passenger usa `passenger_wsgi.py`).
- `Procfile` y `nixpacks.toml` (Railway) siguen en el repo pero no son el deploy vigente.
- Los emails del formulario de contacto y de reservas tienen HTML escrito dentro de las vistas (no en templates).
- La vista `tour` redirige al inicio si el slug no existe (en vez de devolver 404) y arrastra una bandera `debug_mode` de aprendizaje.
- `TourCheckoutView` crea la `Reserva` junto al `Payment` antes de confirmar el pago, por lo que un pago abandonado deja una reserva PENDIENTE.
- Permisos del panel: hoy todo `is_staff` ve todo (los grupos por rol están diferidos).
