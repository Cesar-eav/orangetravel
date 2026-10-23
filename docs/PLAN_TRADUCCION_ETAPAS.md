# Plan por etapas: sitio bilingüe ES/EN

Uso interno. Ejecuta el anexo técnico de `docs/PROPUESTA_TRADUCCION_ES_EN.md`, que es donde están las decisiones y el porqué. Aquí van el orden, las tareas y cómo saber que cada etapa está lista.

**Regla general:** las etapas 1 a 4 son **inertes**: se integran a `fix-orange` y se despliegan sin que el sitio en español cambie. Cada etapa termina con su propio merge `traduccion` → `fix-orange` y su deploy, así cualquier problema queda acotado a esa etapa.

## Sitio en inglés: activo por link, sin banderas (decisión del 20 oct 2026)

La entrega 1 deja `/en/` **activa para cualquiera con el link, pero sin banderas** para el público. Así se pueden seguir publicando cambios de mantención sin que el sitio en español muestre nada nuevo, y el cliente puede revisar el inglés en el sitio real.

Panel → Sitio en inglés (modelo `home.SitioIngles`) tiene dos interruptores:

| Interruptor | Por defecto | Qué hace |
|---|---|---|
| «/en/ accesible para todos» (`publico`) | **Encendido** | Cualquiera con el link entra a `/en/`. Apagado, `/en/` da 404 salvo al staff. |
| «Mostrar banderas» (`mostrar_banderas`) | **Apagado** | Muestra el selector ES \| EN a todos y deja que Google indexe `/en/`. |

Con las banderas apagadas:
- El sitio en español queda idéntico al anterior (verificado comparando el HTML de las páginas públicas): sin selector de idioma ni `hreflang`.
- `/en/` lleva `noindex`, para que Google no la indexe mientras los tours sigan en español (falta la `DEEPL_API_KEY` del cliente para traducirlos).
- El staff con sesión sigue viendo las banderas, marcadas «staff», y un aviso de que el inglés no está anunciado.

**Para lanzar el inglés:** encender «Mostrar banderas» en el panel. No requiere deploy. Desde ese momento aparece el selector para todos, se emiten `hreflang`, `canonical` y `description`, y se recuerda el idioma elegido por el visitante (cookie).

Al desplegar no hay que configurar nada: el registro se crea solo con los valores por defecto (`/en/` activa, sin banderas).

## Estado (23 oct 2026)

- Etapas 1 a 6 implementadas y commiteadas en la rama `traduccion` (worktree `../orangetravel-i18n`), **sin desplegar**. Último commit: `ef4618f`.
- Contenido traducido en local (BD `orage_db_i18n`): 54 textos con `traducir_contenido` (tours, itinerarios, tipos, zonas, tercera edad, posts, nosotros), todo **sin aprobar**. Falta revisarlo y aprobarlo en el panel; en particular «Zona Sur» y «Zona Austral» quedaron ambas como «Southern Region».
- Migración nueva `tours 0018_nombre_en_sin_unique`: `Zona.nombre_en` y `TipoTour.nombre_en` ya no son únicos (modeltranslation copiaba `unique=True` y DeepL tradujo dos zonas igual). Se suma a las migraciones del deploy.
- La `DEEPL_API_KEY` está en el `.env` local de ambas carpetas. En producción falta cargarla en cPanel.
- Tests: pasan los 7 de traducción (`tours/tests_traduccion.py`) según el registro del 20 oct; el 23 oct no se pudieron correr (el usuario de BD local no puede crear la BD de test). Sigue fallando `test_listado_muestra_a_cotizar` (espera `$20000`), que ya fallaba antes de este trabajo.
- Pendiente para la entrega 1 (30 oct):
  1. Hacer merge de `traduccion` en `fix-orange` (los docs ya están en `fix-orange`). **Hay un conflicto en `tours/templates/tours/tour.html`**: ver «Merge con los cambios de `fix-orange` del 23 oct», más abajo.
  2. Deploy en int15 (anexo §7): modo mantención, respaldo de la BD, `git pull`, `pip install -r requirements.txt`, `export DATABASE_URL`, `migrate` (incluye `tours 0018`), `npm run build`, `collectstatic`, Restart desde cPanel. Probar que `/` quedó igual, que `/en/` abre sin sesión y hacer un pago real desde `/en/`.
  3. Cargar `DEEPL_API_KEY` en cPanel (+ Restart desde cPanel), correr `python manage.py traducir_contenido` en producción y aprobar en el panel.
- El avance día a día vive en el seguimiento (artifact «Avance Orange Travel ES/EN»).

### Merge con los cambios de `fix-orange` del 23 oct

El commit `f437bb0` de `fix-orange` cambió la página del tour después de que `traduccion` le pusiera los `{% trans %}`. Simulado con `git merge-tree`: `templates/base.html` se fusiona solo y **`tours/templates/tours/tour.html` da conflicto**.

Qué cambió en `fix-orange`:
- Nuevo orden de secciones: resumen → itinerario por día → incluye → **galería → mapa → video**. Se quitó el `<hr>` que había antes de la galería.
- El nombre del tour en la portada usa `font-cinzel` (`text-3xl md:text-5xl tracking-wider`).
- Marcellus y Cinzel se cargan con `<link>` a Google Fonts en `templates/base.html`. Antes había un `@import url()` en `static/src/input.css` que Vite descartaba, así que Marcellus nunca cargaba.

Cómo resolver el conflicto de `tour.html`:
1. El bloque en conflicto (entre `<<<<<<< fix-orange` y `>>>>>>> traduccion`) trae el video y el mapa **en su posición vieja**, ya con `{% trans %}`. **Borrar el bloque entero**, marcadores incluidos. No elegir «aceptar traduccion»: los dos bloques quedarían duplicados.
2. Git deja el mapa y el video **en su posición nueva (después de la galería) sin traducir**. Volver a ponerles los `{% trans %}` de `traduccion`:
   - `{% trans "Mapa del Tour" %}`
   - `alt="{% blocktrans with nombre=tour.nombre %}Mapa del tour {{ nombre }}{% endblocktrans %}"`
   - `{% trans "Ampliar" %}`
   - `{% trans "Video del Tour" %}`
   - `{% trans "Estamos preparando un video increíble de este tour para ti." %}`
3. Revisar que la galería conserve `{% trans "Galería de Fotos" %}`, `{% trans "Anterior" %}` y `{% trans "Siguiente" %}` (git los fusiona solos), y que arriba sigan `{% load i18n %}`, `{% block meta_description %}` y `{{ textos_reserva|json_script:"textos-reserva" }}`.
4. Comprobar: `grep -c "<<<<<<<\|>>>>>>>" tours/templates/tours/tour.html` da 0; hay un solo `Mapa del Tour` y un solo `Video del Tour`, y los dos con `trans`; `makemessages` no deja textos nuevos sin traducir; `/tours/<slug>/` y `/en/tours/<slug>/` muestran galería → mapa → video.

No hay textos nuevos para traducir: el título usa `{{ tour.nombre }}`, que en `/en/` ya sale de `nombre_en` (o `nombre_es` si la traducción no está aprobada).

| Etapa | Qué | Semana | ¿Cambia el sitio? | Deploy |
|---|---|---|---|---|
| 0 | Preparación | antes / día 1 | No | — |
| 1 | Base i18n | 1 | No | Python + restart |
| 2 | Modelos traducibles e idioma | 1 | No | pip + migrate (las migraciones copian el texto a `_es`) |
| 3 | Emails a templates | 1 | No | Python + restart |
| 4 | Templates y Vue con `{% trans %}` | 1–2 | No | build + collectstatic |
| 5 | Contenido en inglés | 2 | No (aún apagado) | migrate (si aplica) + restart |
| 6 | **Inglés activo por link, sin banderas: entrega 1** | fin de la 2 | No (sin banderas; `/en/` con `noindex`) | completo |
| 7 | **Entrega 2**: blog, emails EN, DeepL en el panel | 3 | Sí | completo |

---

## Etapa 0: Preparación

**Objetivo:** poder trabajar sin tocar la mantención y tener los insumos del cliente.

- [ ] Pedir a Orange Travel: `DEEPL_API_KEY` (cuenta a su nombre), el glosario de términos protegidos y una persona de contacto para aprobar las traducciones.
- [x] `git worktree add ../orangetravel-i18n -b traduccion fix-orange`.
- [x] Crear los symlinks de `static/img` y `static/video` en el worktree (anexo §4).
- [x] Crear la BD `orage_db_i18n` clonada de la local y apuntar a ella con `DATABASE_URL` en el `.env` del worktree.
- [x] `npm ci` en el worktree.
- [x] Instalar django-modeltranslation en el `.venv` compartido y agregarlo a `requirements.txt` (en la rama `traduccion`).

**Lista cuando:** `runserver` en el worktree muestra el sitio con imágenes y videos, sobre su propia BD.

## Etapa 1: Base i18n (inerte)

**Objetivo:** el proyecto queda preparado para varios idiomas, con solo español activo.

- [x] `config/settings.py`: `LANGUAGES = [('es', 'Español')]`, `LOCALE_PATHS = [BASE_DIR / 'locale']` (manteniendo `LANGUAGE_CODE = 'es-cl'`).
- [x] Mover las 4 rutas `api/` de `tours/urls.py` a un include propio (`tours/api_urls.py`) montado en `tours/api/`, antes del include de `tours/`.
- [x] `config/urls.py`: `home`, `tours` y `blog` dentro de `i18n_patterns(..., prefix_default_language=False)`. `admin/`, `panel/`, `ckeditor/`, `pagos/` y `tours/api/` quedan fuera. Agregar `path('i18n/', include('django.conf.urls.i18n'))`.
- [x] `<html lang="{{ LANGUAGE_CODE }}">` con `{% get_current_language %}` en `templates/base.html`, `templates/maintenance.html` y `home/templates/home/renovacion.html`.

**Lista cuando:** `manage.py check` sin errores; todas las URLs públicas, `/pagos/flow-return/`, `/pagos/flow-confirm/` y las APIs responden igual que antes; `/en/` da 404.

## Etapa 2: Modelos traducibles e idioma (inerte)

**Objetivo:** las columnas `_es`/`_en` existen y los emails ya no dependen del idioma activo.

- [x] `settings.py`: `modeltranslation` antes de `django.contrib.admin`; `MODELTRANSLATION_LANGUAGES = ('es', 'en')`, `MODELTRANSLATION_DEFAULT_LANGUAGE = 'es'`.
- [x] `translation.py` en `tours` (Tour, TipoTour, Zona, ItinerarioDia, TerceraEdad), `blog` (Post, captions) y `home` (Nosotros).
- [x] Campo `traduccion_en_aprobada` (default `False`) en `Tour` y `Post`.
- [x] Campo `idioma` (default `'es'`) en `Reserva`, `Cotizacion` y `Payment`.
- [x] **En el mismo commit:** el ruteo de `EMAIL_POR_TOUR` por `nombre_es` (`tours/views.py`, `payments/emails.py`), `tour_nombre_al_pagar` (`payments/models.py`) y el `subject` de Flow (`payments/views.py`).
- [x] `makemigrations` + `migrate` + `update_translation_fields` en local.
- [x] Verificar que el admin (Unfold) y `/panel/` siguen guardando bien los tours (el campo base sigue siendo el español).

**Lista cuando:** el sitio se ve igual, una reserva de prueba envía el email al buzón correcto de `EMAIL_POR_TOUR` y los campos `_es` están llenos.

**Deploy (crítico):** `pip install -r requirements.txt` → `export DATABASE_URL` → `migrate` → restart. Las migraciones `tours 0017`, `blog 0004` y `home 0003` copian el texto actual a los campos `_es`, así que no hace falta correr `update_translation_fields` (correrlo igual es inofensivo). Hacer respaldo de la BD antes y usar modo mantención.

**Implementado distinto al plan:**
- `LANGUAGE_CODE` pasó de `'es-cl'` a `'es'`. Django no trae locale `es_CL` (usaba igual el de `'es'`), y con `'es-cl'` activar `'es'` agregaba `/es/` a las URLs.
- Los emails de `tours/signals.py` (reserva confirmada o rechazada) también salen en el idioma del cliente.

## Etapa 3: Emails a templates (inerte)

**Objetivo:** los emails salen de templates, con el mismo texto que hoy.

- [x] Pasar los HTML en f-string de `tours/views.py` (reserva y cotización) y de `payments/emails.py` (pago) a `templates/emails/` (cliente y admin por flujo).
- [x] Generar los emails dentro de `translation.override(obj.idioma)` para el cliente y `override('es')` para el admin; en los del admin, agregar la línea «Idioma del cliente».

**Lista cuando:** los 3 flujos (reserva, cotización, pago con `enviar_confirmacion_pago` desde el shell) envían el mismo contenido que antes, comparado con un email real anterior.

## Etapa 4: Templates y Vue con `{% trans %}` (inerte)

**Objetivo:** todo el texto de la interfaz pública queda marcado para traducir.

- [x] Envolver los textos de los ~18 templates públicos (`templates/`, `templates/includes/`, `home/`, `tours/`, `blog/`, `payments/`) con `{% trans %}` / `{% blocktrans trimmed %}`, incluidos `messages.success` y los textos de las vistas (`gettext`).
- [x] Vue: textos desde el template con `{{ textos|json_script:"textos-reserva" }}` → prop en `BookingApp`/`CotizacionApp` (`static/src/main.js`).
- [x] Vue: enviar `idioma` en el payload; `crear_reserva`, `crear_cotizacion` y `TourCheckoutView` lo validan contra `LANGUAGES` y lo guardan.
- [x] `FlowReturnView` y `VistaConfirmacionPago` activan `payment.idioma`.
- [x] `makemessages -l en` → primer `locale/en/LC_MESSAGES/django.po` (vacío), commiteado.

**Lista cuando:** el sitio en español es idéntico (revisión visual página por página y reserva/cotización completas), y las reservas nuevas guardan `idioma='es'`.

**Choques:** es la etapa que más pisa la mantención. Conviene hacerla por bloques (home → tours → blog → pagos) con merge a `fix-orange` después de cada bloque.

## Etapa 5: Contenido en inglés (sigue apagado)

**Objetivo:** el inglés existe completo, pero nadie lo ve todavía.

- [x] Traducir `django.po` (interfaz + Vue) con DeepL y revisar a mano; `compilemessages` y commitear el `.mo`.
- [x] Cliente DeepL (`requests`, `DEEPL_API_KEY`) con protección de los términos del glosario.
- [x] Management command que traduce en lote los campos `_en` del contenido existente (tours, itinerarios, zonas, tipos, singletons). Deja `traduccion_en_aprobada = False`.
- [x] `/panel/`: campos `_en` y el checkbox «Traducción aprobada» en `TourForm`, `ItinerarioDiaForm`, `ZonaForm` y `TipoTourForm`; `TabbedTranslationAdmin` para `Nosotros` y `TerceraEdad`.
- [x] Lógica de fallback: en `/en/`, si `traduccion_en_aprobada` es falso, el contenido del tour/post se muestra en español (helper o template tag; un solo lugar, no repetido en cada template).

**Lista cuando:** con `LANGUAGES` con `'en'` en local, `/en/` se ve completo y los tours no aprobados salen en español.

**Deploy:** se puede desplegar apagado; así el cliente revisa y aprueba en el panel de producción antes de encender.

## Etapa 6: Inglés activo por link, sin banderas: entrega 1

**Objetivo:** el sitio en inglés publicado en producción, con reserva y pago, accesible por link pero sin banderas ni indexación hasta encender «Mostrar banderas».

- [x] `LANGUAGES = [('es', 'Español'), ('en', 'English')]`.
- [x] `home.SitioIngles` («Sitio en inglés», panel y admin) + `home.middleware.SitioInglesMiddleware`: `publico` (/en/ accesible, por defecto sí) y `mostrar_banderas` (por defecto no).
- [x] Selector de banderas ES | EN (`templates/includes/_selector_idioma.html`): todos lo ven con «Mostrar banderas»; si no, solo el staff, marcado «staff».
- [x] Memoria del idioma (con «Mostrar banderas»): redirige `/…` → `/en/…` solo con la cookie `django_language=en`.
- [x] SEO (con «Mostrar banderas»): `hreflang` (`es-CL`, `en`, `x-default`), `description` por idioma y, en contenido sin aprobar, `canonical` a la versión en español. Sin banderas, `/en/` lleva `noindex`.
- [x] `/i18n/` dentro de `i18n_patterns`: así, cambiar a español desde `/en/…` vuelve a la página equivalente.
- [ ] Cargar `DEEPL_API_KEY` en cPanel + Restart desde cPanel (cuando el cliente la entregue).
- [ ] Publicación completa (anexo §7) con un pago Flow real desde `/en/`.

**Lista cuando:** se cumple el checklist de verificación (abajo) en producción. Arranca la ronda 1 de ajustes del cliente (2 a 3 días). Encender «Mostrar banderas» es decisión del cliente y no requiere deploy.

## Etapa 7: Entrega 2

**Objetivo:** cerrar el alcance de la propuesta.

- [x] Traducir los textos de los emails en `django.po` (el cliente en inglés si `idioma='en'`). Adelantado en la etapa 5.
- [x] Blog: campos `_en` y aprobación en `PostForm` (adelantado en la etapa 5).
- [ ] Traducción en lote de los posts publicados (`traducir_contenido --solo Post`, requiere `DEEPL_API_KEY`).
- [ ] Botón «Traducir con DeepL» en las vistas de edición de `/panel/` (tour, post, zona): llena los `_en` y deja la aprobación en falso.
- [ ] Glosario editable (archivo o modelo simple) usado por el botón y por el comando.
- [ ] Incorporar los ajustes de la ronda 1.
- [ ] Publicación completa + checklist de verificación.

**Lista cuando:** el cliente puede crear un tour nuevo, traducirlo con el botón, revisarlo y aprobarlo sin ayuda. Arranca la ronda 2 de ajustes y los 30 días de garantía.

---

## Checklist de verificación (etapas 6 y 7)

- [ ] `/` sin cookie → español; elegir EN → `/en/…`; volver a `/` → redirige a `/en/`.
- [ ] `/en/`, `/en/tours/`, `/en/tours/?zona=<slug>`, un tour con precio, un tour «a cotizar», `/en/blog/`.
- [ ] Tour no aprobado en `/en/` → contenido en español, sin `hreflang="en"`.
- [ ] Reserva y cotización desde `/en/` → cliente recibe el email en inglés, admin en español, al buzón de `EMAIL_POR_TOUR`.
- [ ] Pago Flow desde `/en/` → `flow-return` en inglés, email de pago en inglés, `Payment.idioma='en'`.
- [ ] Lo mismo desde `/` → todo en español, sin cambios respecto de antes.
- [ ] Source de `/` y `/en/`: `<html lang>`, `hreflang`, `title` y `description` correctos.
- [ ] `python manage.py detectar_incongruencias_pago` sin novedades.
