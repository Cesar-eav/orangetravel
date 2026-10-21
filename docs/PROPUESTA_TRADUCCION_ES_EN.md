# Propuesta: Sitio web bilingüe Orange Travel (ES/EN)

**Estado:** aceptada.
**Duración:** 3 semanas desde el anticipo y el acceso necesario, con 2 entregas publicadas en el sitio real.

## Enfoque

Proponemos un solo sitio con dos idiomas, y no una copia aparte en inglés, porque así todo lo que ya funciona (reservas, pagos con Flow, emails, panel de administración) sirve en ambos idiomas sin duplicar nada.

- **Direcciones separadas por idioma** (`orangetravel.cl/` y `orangetravel.cl/en/`): Google indexa cada versión por separado y muestra a cada visitante la que corresponde.
- **Un solo sitio que mantener:** una reserva, un pago y un panel de administración. Un cambio de diseño o funcionalidad se aplica a los dos idiomas a la vez.
- **Traducción automática con DeepL, siempre revisable:** acelera el trabajo y reduce el costo. Cada traducción queda como borrador hasta que ustedes la aprueben, por lo que nada se publica sin su visto bueno.
- **Entregas parciales ya publicadas:** ven avance real en el sitio en vivo a mitad del plazo y pueden pedir ajustes antes de la entrega final.

## Qué incluye

- **Sitio en dos idiomas:** selector ES | EN en todas las páginas, direcciones separadas por idioma, etiquetas SEO por idioma (`hreflang`, títulos y descripciones) y memoria del idioma elegido por el visitante.
- **Todo el contenido actual traducido:** páginas, menús, botones, formularios, proceso de reserva y pago (incluido el formulario interactivo), tours y artículos del blog ya publicados.
- **Emails en ambos idiomas:** confirmación de reserva y de pago, al cliente y a ustedes. El cliente recibe el email en el idioma en que usó el sitio.
- **Traducción asistida para contenido futuro:** botón en el panel de administración para traducir al inglés un tour o artículo nuevo con DeepL, en estado borrador hasta que lo publiquen, más un glosario para mantener consistentes los nombres de lugares y de tours.
- **Pruebas y publicación segura:** pruebas en ambos idiomas, incluido el pago con Flow, respaldo de la base de datos antes de cada publicación y modo mantención solo el tiempo mínimo necesario.

## Plan de trabajo: 3 semanas, 2 entregas

El trabajo dura 3 semanas desde el anticipo y el acceso necesario, con dos entregas publicadas en el sitio real: la primera al terminar la semana 2 y la final al terminar la semana 3.

| Semana | Trabajo |
|---|---|
| 1 | Preparación técnica del sitio para varios idiomas y traducción de las páginas principales. |
| 2 | Traducción de tours y del proceso de reserva y pago, pruebas del pago con Flow y publicación de la entrega 1. |
| 3 | Incorporación de sus ajustes, blog, emails, traducción asistida, pruebas finales y publicación de la entrega 2. |

## Entregas

| Entrega | Cuándo | Qué recibe Orange Travel | Qué hacen ustedes |
|---|---|---|---|
| **Entrega 1:** sitio en inglés operativo | Fin de la semana 2 | Selector de idioma, direcciones `/en/`, SEO por idioma, páginas principales, tours y proceso de reserva y pago en inglés, ya publicados | Revisar los textos principales y enviar ajustes (2 a 3 días) |
| **Entrega 2:** entrega final | Fin de la semana 3 | Blog en inglés, emails en ambos idiomas, botón de traducción asistida en el panel, ajustes de la entrega 1, pruebas finales | Aprobar y publicar traducciones futuras con el botón |

---

## Anexo técnico: desarrollo en paralelo a la mantención

Uso interno. Explica cómo hacer la traducción sin frenar ni romper los cambios de mantención que se siguen publicando en `fix-orange`. El orden de ejecución y los checklists están en `docs/PLAN_TRADUCCION_ETAPAS.md`.

**Idea central:** trabajar en una rama `traduccion` que nunca se aleje mucho de `fix-orange`. Lo que no cambia el sitio en español se integra a producción temprano; el inglés se enciende en la entrega 1.

El riesgo no está en git. Está en que la traducción toca *todos* los templates públicos (para envolver los textos en `{% trans %}`) mientras la mantención edita esos mismos templates.

**Requisitos que vienen de la propuesta comercial anterior** (`docs/PROPUESTA_TRADUCCION_EN.md`):
- La cuenta DeepL queda a nombre de Orange Travel: ellos entregan la `DEEPL_API_KEY`.
- El glosario de términos protegidos (nombres de tours, lugares, marcas) lo entregan ellos.
- Se incluyen 2 rondas de ajustes, una por entrega.

### 1. Estado de partida

- La base está limpia: las migraciones `0015` y `0016` (zonas) ya están commiteadas y desplegadas.
- `config/settings.py` ya tiene `LocaleMiddleware` y `USE_I18N = True`. Faltan `LANGUAGES`, `LOCALE_PATHS`, `i18n_patterns` y django-modeltranslation.
- Hoy no hay ningún `{% trans %}`. `templates/base.html`, `templates/maintenance.html` y `home/templates/home/renovacion.html` tienen `<html lang="es">` fijo.

### 2. Decisiones técnicas

- **Campos traducidos con django-modeltranslation**, con `MODELTRANSLATION_LANGUAGES = ('es', 'en')` y `MODELTRANSLATION_DEFAULT_LANGUAGE = 'es'` desde la semana 1, sin depender de `LANGUAGES`. Así las columnas `_en` se crean en la integración temprana y encender el inglés no genera migraciones nuevas. `modeltranslation` va antes de `django.contrib.admin` en `INSTALLED_APPS`.
- **Modelos traducidos:** `Tour` (`nombre`, `itinerario`, `incluye`), `TipoTour`, `Zona`, `ItinerarioDia`, `Post` (`titulo`, `extracto`, `contenido`), los `caption` de las imágenes del blog y los singletons `Nosotros` y `TerceraEdad`. El panel (`/panel/`) y el admin siguen en español.
- **Idioma por defecto:** `LANGUAGE_CODE = 'es'` (antes `'es-cl'`). Django no trae locale `es_CL` y ya usaba el de `'es'`, así que formatos y filtro `clp` no cambian; con `'es-cl'`, activar `'es'` (el idioma guardado de un pago) agregaba `/es/` a las URLs. `LANGUAGES = [('es', 'Español'), ('en', 'English')]`. En `hreflang` se usan `es-CL`, `en` y `x-default` → español.
- **URLs:** `home`, `tours` y `blog` van dentro de `i18n_patterns(..., prefix_default_language=False)`, de modo que las URLs en español no cambian. Quedan **fuera** `admin/`, `panel/`, `ckeditor/`, `pagos/` (Flow necesita URLs fijas) y las APIs de tours: las 4 rutas `api/` de `tours/urls.py` pasan a un include propio montado en `tours/api/`, declarado antes del include de `tours/`. `path('i18n/', include('django.conf.urls.i18n'))` (para `set_language`) va **dentro** de `i18n_patterns`: `translate_url` solo traduce desde el idioma activo, y así cambiar a español desde `/en/…` vuelve a la página equivalente.
- **Slugs compartidos:** `/en/tours/<slug-en-español>/`. No se traducen.
- **Borradores:** `Tour` y `Post` llevan el campo `traduccion_en_aprobada` (default `False`). Mientras sea `False`, `/en/` muestra el contenido en español (fallback) y esa página no emite `hreflang="en"`. Ningún tour ni artículo desaparece de `/en/`.
- **DeepL:** se llama a la API REST con `requests` (ya está en `requirements.txt`, sin el SDK `deepl`), usando `DEEPL_API_KEY` desde cPanel. Los términos del glosario se protegen antes de traducir. El botón «Traducir con DeepL» va en las vistas de edición de `/panel/` (tour, post, zona): llena los campos `_en` y deja `traduccion_en_aprobada = False`. Para el contenido existente hay un management command que hace lo mismo en lote.
- **Emails:** el cliente lo recibe en el idioma con que usó el sitio. El admin lo recibe siempre en español, con una línea «Idioma del cliente: EN/ES».
- **Memoria del idioma:** con Django 5.2 y `prefix_default_language=False`, `/` siempre sale en español aunque exista la cookie. Un middleware redirige `/…` → `/en/…` **solo** cuando existe la cookie `django_language=en` (que pone el selector), nunca por `Accept-Language`, para que Google indexe ambas versiones.
- **Textos de Vue:** `BookingApp.vue` y `CotizacionApp.vue` reciben sus textos desde el template vía `{{ textos|json_script }}`, traducidos con gettext. Así hay una sola fuente de traducción (`locale/en/LC_MESSAGES/django.po`) y no hace falta un JSON aparte en `static/`.

### 3. Problemas conocidos y su solución

1. **El ruteo de emails falla en inglés.** `EMAIL_POR_TOUR` busca la palabra clave en `tour.nombre` (`tours/views.py`, `payments/emails.py`). Con modeltranslation, `tour.nombre` devuelve `nombre_en` cuando el idioma activo es inglés: el match falla y todo cae en `EMAIL_ADMIN_DEFAULT`. **Solución:** usar `nombre_es` en el ruteo, en `Payment.tour_nombre_al_pagar` (`payments/models.py`) y en el `subject` que se envía a Flow (`payments/views.py`). Este cambio va en el mismo commit que instala modeltranslation (antes no existe `nombre_es`).
2. **El webhook no sabe el idioma del cliente.** `FlowConfirmView` es servidor a servidor: no tiene sesión ni prefijo `/en/`. **Solución:** agregar el campo `idioma` (default `'es'`) a `Reserva`, `Payment` y `Cotizacion`, guardarlo al crearse y generar los emails dentro de `translation.override(obj.idioma)` (y `override('es')` para el admin). `FlowReturnView` y `VistaConfirmacionPago` activan `payment.idioma`, porque `pagos/` no tiene prefijo.
3. **Las llamadas de Vue no llevan el idioma.** Los componentes llaman a `/tours/api/...` y `/pagos/checkout/...` sin prefijo, así que el servidor las procesa en español. **Solución:** el payload envía `idioma` (leído de `document.documentElement.lang`, que `base.html` debe generar con `{% get_current_language %}`), y `crear_reserva`, `crear_cotizacion` y `TourCheckoutView` lo validan contra `LANGUAGES` y lo guardan.
4. **Los emails están como HTML en f-strings** dentro de `tours/views.py` y `payments/emails.py`. **Solución:** pasarlos primero a templates (`templates/emails/`) sin cambiar el texto (es inerte) y después envolverlos en `{% trans %}`.
5. **El worktree queda sin imágenes ni videos.** `static/img` (~23 MB) y `static/video` (~127 MB) no están en git. **Solución:** crear symlinks en el worktree (ver sección 4).
6. **`.mo` en el servidor.** No hay garantía de que exista `msgfmt` en el jailshell. **Solución:** correr `makemessages`/`compilemessages` en local y **commitear** `locale/en/LC_MESSAGES/django.po` y `django.mo` (`.gitignore` no los excluye).

### 4. Trabajo en paralelo con worktree

```bash
git worktree add ../orangetravel-i18n -b traduccion fix-orange
ln -s /var/www/html/orangetravel/static/img   ../orangetravel-i18n/static/img
ln -s /var/www/html/orangetravel/static/video ../orangetravel-i18n/static/video
```

- Mantención: `/var/www/html/orangetravel` (rama `fix-orange`), sin cambios en el flujo. Traducción: `../orangetravel-i18n`. Sin `stash` ni `checkout`.
- **BD local separada para el worktree:** copiar el `.env` y cambiar `DATABASE_URL` a otra base (p. ej. `orage_db_i18n`, clonada de la de mantención). Si no, las migraciones de traducción (campos `nombre_en`, `idioma`, etc.) se aplican en la BD de mantención y pueden romper ese checkout.
- Python: reutilizar el `.venv` de mantención (`/var/www/html/orangetravel/.venv/bin/python`). Instalar ahí django-modeltranslation no afecta a `fix-orange` mientras no esté en `INSTALLED_APPS`.
- Correr `npm ci` en el worktree (`node_modules/` no se comparte).

### 5. Mantener la rama cerca de producción

- **Todos los días:** `git merge fix-orange` dentro de `traduccion` (merge, no rebase).
- **Integrar temprano a `fix-orange` lo inerte** (semana 1), sin que el sitio en español cambie:
  - `LANGUAGES` solo con `'es'`, `LOCALE_PATHS` e `i18n_patterns(..., prefix_default_language=False)` (las URLs en español quedan idénticas), y la separación de `tours/api/`.
  - modeltranslation con los campos `_es`/`_en`, y en el mismo commit el ruteo de emails por `nombre_es` (problema 1).
  - El campo `idioma` en `Reserva`, `Payment` y `Cotizacion` (problema 2).
  - Emails pasados a templates (problema 4).
  - Templates públicos (~18: `templates/`, `templates/includes/`, `home/`, `tours/`, `blog/`, `payments/`) con `{% trans %}` / `{% blocktrans trimmed %}`: renderizan el mismo español. `<html lang>` dinámico.

  Así la rama larga solo guarda lo realmente nuevo.
- **Interruptor «Sitio en inglés» (decisión del 20 oct 2026):** el inglés se publica en la entrega 1 pero oculto. `home.SitioIngles.publico` (panel → Sitio en inglés) apagado: `/en/` es 404 para el público y solo el staff la ve (selector marcado «staff», aviso y `noindex`). Encendido: selector de banderas para todos, `hreflang` y memoria del idioma. Encenderlo no requiere deploy.
- Desde ese momento, **los textos nuevos que se escriban en mantención van con `{% trans %}`**, y en los emails se usa `nombre_es`.

### 6. Puntos de choque propios de este repo

- **Migraciones:** si la mantención crea una migración en `tours`, `blog`, `home` o `payments`, hacer merge a `traduccion` de inmediato y regenerar ahí las migraciones de traducción (`makemigrations` después del merge). Evita dos `0017` en paralelo.
- **`static/css/output.css` está versionado** (Tailwind compilado). Ante un conflicto no resolverlo a mano: `npm run build` y commitear el resultado.
- **`static/` está en `.gitignore`** (algunos archivos están forzados). Todo archivo **nuevo** en `static/` (p. ej. componentes Vue) necesita `git add -f`; si no, no llega al server y no hay aviso.
- **`locale/en/LC_MESSAGES/django.po`:** ante un conflicto, resolver, correr `makemessages -l en`, completar las traducciones y `compilemessages`. El `.mo` siempre se regenera; no se resuelve a mano.

### 7. Publicación de cada entrega

Merge `traduccion` → `fix-orange`. Antes de encender el inglés, cargar `DEEPL_API_KEY` en cPanel → Setup Python App → Environment Variables y hacer **Restart desde cPanel** (regla 1 de `CLAUDE.md`).

En el server (`hostname` = int15, `cd ~/orangetravel`):

1. Activar modo mantención (`/admin/`).
2. Respaldo de la BD.
3. `git pull`.
4. `~/virtualenv/orangetravel/3.11/bin/pip install -r requirements.txt` (dependencia nueva: django-modeltranslation).
5. `export DATABASE_URL=...` copiado desde cPanel (las vars de cPanel no llegan a SSH, regla 3).
6. `~/virtualenv/orangetravel/3.11/bin/python manage.py migrate`.
7. Ya no hace falta `update_translation_fields`: las migraciones `tours 0017`, `blog 0004` y `home 0003` copian el texto actual a los campos `_es` (correrlo igual es inofensivo).
8. `export PATH=/opt/alt/alt-nodejs22/root/usr/bin:$PATH && npm run build`, y después `collectstatic --noinput`.
9. Restart desde cPanel.
10. Probar `/` y `/en/`: reserva, cotización y un pago con Flow; revisar que el email del admin llegue al buzón de `EMAIL_POR_TOUR`.
11. Desactivar modo mantención.

Como lo grande ya se integró antes, el merge final es chico y la ventana de mantención es corta.
