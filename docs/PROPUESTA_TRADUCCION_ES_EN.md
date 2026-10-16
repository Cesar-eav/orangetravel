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

Uso interno. Cómo hacer la traducción sin frenar ni romper los cambios de mantención que se siguen publicando en `fix-orange`.

**Idea central:** una rama `traduccion` que nunca se aleje mucho de `fix-orange`. Lo que no cambia el sitio en español se integra a producción temprano; lo nuevo se enciende en la entrega 1.

El riesgo no es git: es que la traducción toca *todos* los templates (para envolver textos en `{% trans %}`) mientras la mantención edita esos mismos templates.

### 1. Antes de empezar

- Commitear y desplegar en `fix-orange` todo lo pendiente (p. ej. zonas, migraciones `0015` y `0016`). La rama de traducción debe partir de una base limpia.

### 2. Trabajo en paralelo con worktree

```bash
git worktree add ../orangetravel-i18n -b traduccion fix-orange
```

- Mantención: `/var/www/html/orangetravel` (rama `fix-orange`), sin cambios en el flujo. Traducción: `../orangetravel-i18n`. Sin `stash` ni `checkout`.
- **BD local separada para el worktree:** copiar el `.env` y cambiar `DATABASE_URL` a otra base (p. ej. `orage_db_i18n`). Si no, las migraciones de traducción (campos `nombre_en`, etc.) se aplican en la BD de mantención y pueden romper ese checkout.
- Correr `npm ci` en el worktree (`node_modules/` no se comparte).

### 3. Mantener la rama cerca de producción

- **Todos los días:** `git merge fix-orange` dentro de `traduccion` (merge, no rebase).
- **Integrar temprano a `fix-orange` lo inerte** (semana 1), sin que el sitio en español cambie:
  - `LocaleMiddleware` e `i18n_patterns(..., prefix_default_language=False)`: las URLs en español quedan idénticas.
  - `LANGUAGES` solo con `'es'`.
  - Templates con `{% trans %}` / `{% blocktrans %}`: renderizan el mismo español.

  Así la rama larga solo guarda lo realmente nuevo. Encender el inglés en la entrega 1 = agregar `'en'` a `LANGUAGES` y mostrar el selector.
- Desde ese momento, **los textos nuevos que se escriban en mantención van con `{% trans %}`**.

### 4. Puntos de choque propios de este repo

- **Migraciones:** si la mantención crea una migración en `tours` o `blog`, hacer merge a `traduccion` de inmediato y regenerar ahí las migraciones de traducción (`makemigrations` después del merge). Evita dos `0017` en paralelo.
- **`static/css/output.css` está versionado** (Tailwind compilado). Ante un conflicto no resolverlo a mano: `npm run build` y commitear el resultado.
- **`static/` está en `.gitignore`** (algunos archivos están forzados). Todo archivo **nuevo** en `static/` (componentes Vue, JSON de textos en inglés) necesita `git add -f`; si no, no llega al server y no hay aviso.

### 5. Publicación de cada entrega

Merge `traduccion` → `fix-orange` y en el server:

1. Activar modo mantención (`/admin/`).
2. Respaldo de la BD.
3. `git pull`, `migrate`, `npm run build`, `collectstatic --noinput`, restart.
4. Probar `/` y `/en/`, incluido un pago con Flow.
5. Desactivar modo mantención.

Como lo grande ya se integró antes, el merge final es chico y la ventana de mantención es corta.
