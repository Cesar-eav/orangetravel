# Panel de gestión (`/panel/`)

Panel alternativo al admin de Django/Unfold, pensado para usuarios no técnicos. **Convive con `/admin/`**, que no se modifica: ambos usan la misma base de datos y los mismos usuarios.

## Decisiones de diseño
- App Django nueva `panel`, montada en `config/urls.py` como `panel/`.
- Vistas server-rendered (templates Django + `ModelForm`), sin Vue ni API nueva.
- Estilos en línea dentro de `panel/templates/panel/base.html`: **no requiere `npm run build`**. (El `.gitignore` excluye `static/`, por eso no se usa un CSS propio.)
- Acceso: usuarios con `is_staff=True`. Login en `/panel/login/`, logout por POST en `/panel/logout/`. No se toca `LOGIN_URL` global.
- No se modifica la lógica de pagos ni de emails: el panel solo llama a las funciones existentes.

## Estado por etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 0 | Base, login, `StaffRequiredMixin`, layout, exención en modo mantención | Hecha |
| 1 | Reservas, Pagos y dashboard con contadores | Hecha |
| 2 | Tours (con precio y galería), categorías, bloqueos de fechas | Hecha |
| 3 | Blog (reseñas) con imágenes en párrafos y carrusel | Hecha |
| 4 | Páginas y ajustes: `Nosotros`, `TerceraEdad`, `MaintenanceMode` | Hecha |
| 5 | Pulido: ayudas, permisos por grupo, más tests, decidir retiro del admin | Pendiente |

## Modificaciones realizadas

Commits en la rama `fix-orange`:

1. **`8d5f14a` — Seguridad.** `tours/views.py`: `get_pagos_activos_admin` (`/tours/api/admin/pagos/<id>/`) ahora tiene `@staff_member_required`. Antes cualquiera podía ver, por tour, cuántos pagos y pasajeros había por fecha (datos agregados, sin datos personales).
2. **`a3af2a9` — Panel, etapas 0 y 1.**
   - Archivos nuevos en `panel/`: `apps.py`, `mixins.py`, `forms.py`, `urls.py`, `views.py`, `tests.py` y `templates/panel/` (`base`, `login`, `dashboard`, `reservas_list`, `reserva_detail`, `pagos_list`, `pago_detail`, `_pager`).
   - `config/settings.py`: `'panel'` en `INSTALLED_APPS`.
   - `config/urls.py`: `path('panel/', include('panel.urls'))`.
   - `home/middleware.py`: `/panel/` agregado a `EXEMPT_PREFIXES`, para que el login funcione en modo mantención (el staff igual pasa).
3. **`854cd7b` — Corrección.** El login sin `next` redirigía a `/accounts/profile/` (404). Se creó `PanelLoginView` que redirige a `/panel/`.

## Funcionalidad actual

**Acceso**
- Anónimo: redirige a `/panel/login/`.
- Usuario sin `is_staff`: no puede iniciar sesión; si ya está logueado, recibe 403.

**Inicio (`/panel/`)**: reservas por confirmar, confirmadas próximas, pagos de los últimos 7 días, últimas reservas y últimos pagos.

**Reservas (`/panel/reservas/`)**
- Búsqueda por código, nombre o email; filtros por estado, tour y "solo próximas"; paginación de 25.
- Detalle: cambiar estado y editar notas internas.
- Eliminar = borrado lógico (`Reserva.delete()`), solo por POST.

**Pagos (`/panel/pagos/`)**
- Lista y detalle de solo lectura, con filtros por estado y tour.
- Botones "Reenviar al cliente" / "Reenviar a administradores": solo con pago `paid` (y con email de cliente en el primer caso).

**Tours (`/panel/tours/`)**: lista con búsqueda; crear/editar en una sola pantalla (datos, itinerario con CKEditor, precio adulto/niño y galería con subida múltiple y borrado de imágenes). No se eliminan tours desde el panel (borrarlos arrastraría sus reservas): se desmarca "activo".

**Categorías (`/panel/categorias/`)**: crear, editar y eliminar; si tiene tours asociados se muestra un aviso y no se elimina.

**Bloqueos de fechas (`/panel/bloqueos/`)**: bloquear una fecha por tour (sin duplicados), filtrar (por defecto solo futuros) y quitar bloqueos.

**Blog (`/panel/blog/`)**: lista con búsqueda y filtro publicadas/ocultas; crear/editar en una pantalla (título, slug automático (se genera desde el título al crear, se hace único y no cambia al editar), resumen (máx. 500 caracteres) y cuerpo con CKEditor (máx. 10.000 caracteres de texto), ambos con contador en vivo, portada, YouTube, publicada). Incluye tabla de imágenes entre párrafos (con contador de bloques, editar/quitar) y carrusel con subida múltiple (máx. 20) y borrado individual. El autor se asigna al usuario que crea la reseña. Eliminar reseña es borrado real (con confirmación); para ocultarla basta desmarcar «publicada».

**Páginas y ajustes**: `/panel/nosotros/` y `/panel/tercera-edad/` (contenido con CKEditor) y `/panel/mantencion/` (activar/desactivar el modo mantención y editar su mensaje; el staff sigue viendo el sitio). Los tres son singletons: una sola pantalla de edición, sin crear ni eliminar.

## Lógica existente que el panel reutiliza (sin modificarla)
- `payments/emails.py`: `send_payment_confirmation_to_customer` y `send_payment_confirmation_to_admins`.
- `tours/signals.py`: al guardar una `Reserva` con estado CONFIRMADA, RECHAZADA o CANCELADA se envía email al cliente; RECHAZADA/CANCELADA además cancela el `Payment` pagado de esa fecha. El panel usa `save()` normal, así que esto ocurre igual que en el admin, y el detalle muestra un aviso previo.
- Borrado lógico de `Reserva` (`SoftDeleteManager`, `borrado_el`).

## Pruebas
```bash
# Tests (el Postgres local no permite crear la BD de pruebas, se usa SQLite)
DATABASE_URL=sqlite:////tmp/panel_test.sqlite3 python manage.py test panel

# Probar a mano en local
python manage.py runserver   # → http://127.0.0.1:8000/panel/login/
```
30 tests cubren (incluye catálogo, blog y páginas/ajustes): acceso anónimo/no staff/staff, redirección post-login, filtros, cambio de estado (dispara el signal de correo), borrado lógico, reenvío de correos y protección del endpoint de pagos.

## Despliegue a producción
Tras `git pull` en `~/orangetravel`: `touch tmp/restart.txt`. No hay migraciones ni `collectstatic` ni `npm run build` para las etapas 0–4. Entrar a `/panel/login/` con un usuario que tenga "Es staff".
