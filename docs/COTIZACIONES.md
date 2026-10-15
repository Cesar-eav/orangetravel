# Tours con precio vs. tours con cotización

Desde octubre de 2026, según la categoría del tour, el sitio permite **pagar en línea** o **pedir una cotización**.

| Categoría (`TipoTour`) | id | Qué ve el cliente |
|---|---|---|
| Excursiones de un Día | 1 | Precio, botón «RESERVAR AHORA» y pago con Flow (igual que antes) |
| Trekking y Expediciones | 2 | «A cotizar», botón «COTIZAR AHORA» y formulario de cotización |
| Viajes Multidía | 3 | «A cotizar», botón «COTIZAR AHORA» y formulario de cotización |

## Regla

- `tours/models.py`: constante `TIPO_CON_PRECIO_ID = 1` y propiedad `Tour.con_precio` (`tipo_id == TIPO_CON_PRECIO_ID`).
- La regla está **fija por id**. Si la categoría 1 se borra y se recrea con otro id, ningún tour volverá a mostrar precio. Para cambiar qué categoría se vende con precio, hay que editar la constante.
- Los ids de las categorías son los mismos en producción y en local.

## Flujo de cotización

1. `tours/views.py::tour` pasa `con_precio` al template. `tour.html` lo expone como `data-con-precio="1|0"` en `#reservation-widget`.
2. `static/src/main.js` monta `BookingApp.vue` si `con_precio` es `1` y, si no, `CotizacionApp.vue`.
3. `CotizacionApp.vue` hace un POST JSON a `/tours/api/cotizacion/crear/` (`crear_cotizacion`) con: `tour_id`, `nombre`, `email`, `telefono`, `fecha` (opcional, `YYYY-MM-DD`), `adultos`, `ninos` y `mensaje`.
4. `crear_cotizacion` valida los datos y rechaza con 400 si el tour tiene precio, el email no es válido o la fecha no es futura. Luego crea la `Cotizacion` y llama a `enviar_notificaciones_cotizacion` en un hilo.
5. Se envían dos emails:
   - **Cliente**: «🍊 Solicitud de cotización: <tour>».
   - **Admin**: «🧾 COTIZACIÓN: <tour> - <cliente>». Usa el mismo enrutamiento que las reservas (`get_email_admin` / `EMAIL_POR_TOUR`, `CC_RESERVAS`), con `reply_to` al cliente y un enlace a `/panel/cotizaciones/<id>/`.

## Modelo `Cotizacion` (migración `tours/0014_cotizacion`)

`tour` (FK `PROTECT`), `nombre`, `email`, `telefono`, `fecha_tentativa` (opcional), `adultos`, `ninos`, `mensaje`, `atendida`, `creada_el`.

## Gestión

- **Panel** (`/panel/cotizaciones/`): lista con búsqueda (nombre, email o teléfono), filtro por tour y «Solo sin atender». En el detalle se marca como **atendida**. El inicio del panel muestra el contador «Cotizaciones sin atender».
- **Admin** (`/admin/tours/cotizacion/`): `atendida` se puede editar desde la lista.

## Otros cambios

- `payments/views.py::TourCheckoutView` responde 400 si el tour no tiene precio, así no se puede iniciar un pago Flow de un tour de cotización por la API.
- En las tarjetas de `tours/templates/tours/tours_home.html` y `home/templates/home/index.html`, los tours de cotización muestran «A cotizar» en lugar del monto.
- La vista `tour` lleva `@ensure_csrf_cookie`. Antes, si el cliente entraba directo a un tour sin pasar por la portada, no tenía cookie CSRF y el POST fallaba.
- La vista `tour` usa `getattr(tour, 'precio', None)`, así que un tour de cotización sin `PrecioTour` ya no da error 500.
- Pendiente: el formulario de tours del panel sigue pidiendo precio para todos los tours. En los de cotización ese precio simplemente no se muestra.

## Archivos

- Modelo y lógica: `tours/models.py`, `tours/views.py`, `tours/urls.py`, `tours/admin.py`, `tours/migrations/0014_cotizacion.py`.
- Pagos: `payments/views.py`.
- Frontend: `static/src/components/CotizacionApp.vue` (nuevo), `static/src/main.js`, `tours/templates/tours/tour.html`, `tours/templates/tours/tours_home.html`, `home/templates/home/index.html`.
- Panel: `panel/forms.py` (`CotizacionGestionForm`), `panel/views.py` (`CotizacionListView`, `CotizacionDetailView`), `panel/urls.py`, `panel/templates/panel/cotizaciones_list.html`, `panel/templates/panel/cotizacion_detail.html`, `base.html` (menú) y `dashboard.html` (contador).
- Tests: `tours/tests.py` (`CotizacionTests`).

> `static/` está en `.gitignore`: el componente nuevo se agrega con `git add -f static/src/components/CotizacionApp.vue`.

## Deploy en producción

Tras `git pull` en `~/orangetravel` (activar antes el modo mantención):

```bash
~/virtualenv/orangetravel/3.11/bin/python manage.py migrate   # con DATABASE_URL exportada (ver CLAUDE.md, regla 3)
npm run build
~/virtualenv/orangetravel/3.11/bin/python manage.py collectstatic --noinput
touch tmp/restart.txt
```

## Verificación

- `/tours/`: los tours de la categoría 1 muestran precio y el resto muestra «A cotizar».
- Tour de la categoría 1: «RESERVAR AHORA» con precio y total.
- Tour de la categoría 2 o 3: «COTIZAR AHORA» → enviar → mensaje de éxito; la cotización aparece en `/panel/cotizaciones/` y llegan los dos emails.
- Tests en local. La base de prueba va en SQLite porque el usuario de Postgres local no puede crear bases:
  ```bash
  DATABASE_URL=sqlite:////tmp/test.sqlite3 .venv/bin/python manage.py test
  ```
