# Migración de FTP a git en producción

**Estado: completada el 25 sep 2026.** Producción (`/home3/cor116358/orangetravel/`) ahora corre desde un `.git` real en la rama `fix-orange`, sincronizada con `origin/fix-orange` (commit `c202bc7` al cierre de esta migración). El deploy pasa a ser `git pull` + los pasos de la sección "De ahí en adelante" al final de este documento. Esta guía queda como registro de cómo se hizo, para referencia futura.

Producción se había desplegado siempre por FTP y no tenía `.git`. Esta guía deja el paso a paso que se usó para convertirla a un deploy basado en `git pull`, hecho en sep 2026 tras verificar (por checksum) que el código desplegado coincidía casi exactamente con `fix-orange`.

**Nota importante descubierta durante la migración:** el `git init` + `checkout -f -b fix-orange origin/fix-orange` del Paso 3 (abajo) en realidad **ya se había corrido antes**, en algún momento no documentado alrededor del 16 sep 2026 (mismo día que se generó la llave SSH del Paso 1) — probablemente en una sesión anterior no registrada. Se descubrió el 25 sep cuando `git init` devolvió `Reinitialized existing Git repository` en vez de crear uno nuevo. Si en el futuro se encuentra este mismo documento y no se sabe si el Paso 3 ya corrió, verificar primero con `git status` / `git log -1` antes de asumir que hace falta ejecutarlo — correrlo de nuevo no rompe nada (`git init` sobre un repo existente es inofensivo, y `checkout -f` re-sincroniza), pero puede generar confusión si no se entiende el estado previo.

## Estado verificado antes de migrar

- Producción corre `fix-orange`, sincronizado byte a byte en ~92/99 archivos versionados.
- Python de producción: `/home3/cor116358/virtualenv/orangetravel/3.11/bin/python` (no hay `python3` en el jailshell, ni `.venv/` dentro del proyecto).
- `manage.py` **ya tiene el fix aplicado en el repo** (commit posterior a `8e955fa`): se descomentó `import pymysql; pymysql.install_as_MySQLdb()`, que es obligatorio — se confirmó en vivo que `import MySQLdb` falla (`mysqlclient` no está funcional en el venv del hosting, aunque figure en `requirements.txt`).
- `config/wsgi.py` no importa: Passenger ejecuta `passenger_wsgi.py` directamente, nunca pasa por `config/wsgi.py`.
- `payments/flow.py` tiene un default de `api_base` en modo sandbox, pero es inofensivo: `FLOW_API_BASE` siempre llega seteada desde **cPanel → Setup Python App → Environment Variables** (confirmado en vivo). Ver `docs/PRODUCCION_VARS_EMAIL.md`.
- Existe un archivo `.env_` (con guion bajo) en la raíz de producción con credenciales sandbox de Flow — es un `.env` viejo renombrado para desactivarlo. `passenger_wsgi.py` carga literalmente `.env`, así que `.env_` es inerte. No tocar / no renombrar a `.env`.
- `static/src/components/BookingApp.vue` en producción está atrasado (le falta la validación de 3 días mínimos, commit `27b7678`) — se corrige solo al desplegar `fix-orange`.
- Apareció un archivo huérfano sin versionar: `home/templates/home/index_2.html` (fechado 8 jun 2026). No lo referencia ninguna vista (`home/views.py` solo usa `home/index.html`) — es una copia de respaldo vieja hecha a mano en cPanel, no está en git y no lo toca ningún `checkout`/`reset`. Se dejó tal cual, sin acción.
- El jailshell de cPanel **no soporta process substitution** (`<(...)`, falla con `No such file or directory` en `/dev/fd/N`). Para comparar un archivo untracked contra un blob de git, usar un archivo temporal en vez de `<(git show ...)`:
  ```bash
  git show origin/fix-orange:ruta/al/archivo > /tmp/comparar.tmp
  diff /tmp/comparar.tmp ruta/al/archivo && echo "IDÉNTICO"
  ```
- `git diff <ref> -- <path>` **no sirve para verificar archivos untracked** — los muestra como "deleted file" aunque existan en disco, porque el comando compara contra el índice, no contra el árbol de trabajo real. Para eso usar el método de arriba (`git show` + `diff` a archivo temporal), o `git add -N <path>` antes de diffear.

## Paso 0 — Local

Confirmar que el fix de `manage.py` esté commiteado y pusheado a `origin/fix-orange`:
```bash
git add manage.py
git commit -m "Fix: activar shim pymysql en manage.py para producción"
git push
```

## Paso 1 — Servidor: acceso SSH a GitHub (una sola vez)

El repo es privado, el servidor necesita su propia llave:
```bash
ls -la ~/.ssh/id_ed25519* 2>&1   # ver si ya existe una llave
```
Si no existe:
```bash
ssh-keygen -t ed25519 -C "orangetravel-prod" -N ""
cat ~/.ssh/id_ed25519.pub
```
Copiar esa llave pública y agregarla en GitHub → repo `Cesar-eav/orangetravel` → **Settings → Deploy keys → Add deploy key** (dejarla **read-only**). Luego probar:
```bash
ssh -T git@github.com
```

## Paso 2 — Backup de seguridad

Antes de tocar nada en producción:
```bash
cd ~
tar -czf orangetravel-backup-$(date +%Y%m%d).tar.gz --exclude='orangetravel/media' --exclude='orangetravel/staticfiles' orangetravel/
```
(se excluyen `media/` y `staticfiles/` por tamaño; lo importante es poder recuperar el código si algo sale mal).

## Paso 3 — Inicializar git en el directorio existente

```bash
cd ~/orangetravel
git init
git remote add origin git@github.com:Cesar-eav/orangetravel.git
git fetch origin
git checkout -f -b fix-orange origin/fix-orange
```

`-f` sobreescribe en disco los archivos que difieren de `fix-orange` (`.gitignore`, `requirements.txt`, `payments/flow.py`, `BookingApp.vue`, `templates/base.html` — todos cambios ya revisados y deseados). **No toca** `media/`, `static/img/`, `staticfiles/`, `.env_`, `tmp/`, `__pycache__/`, `.vscode/` porque están en `.gitignore` o no son parte del árbol de git.

## Paso 4 — Verificar

```bash
git status            # debería decir "nada para commitear, working tree clean"
git log -1 --oneline  # debería mostrar el último commit de fix-orange
```

## Paso 5 — Reiniciar y probar

```bash
touch tmp/restart.txt
```
Visitar el sitio y probar el flujo completo de reserva/pago. Si algo falla, revisar:
```bash
tail -50 ~/logs/passenger.log
```

## Modo mantención (agregado 25 sep 2026, antes de cerrar la migración)

Como red de seguridad para el resto de la migración, se agregó un toggle de "modo mantención" activable desde `/admin/` (commit `c202bc7`):

- Modelo singleton `MaintenanceMode` (django-solo, mismo patrón que `Nosotros`/`TerceraEdad`) en `home/models.py`, con campos `activo` y `mensaje` (rich text).
- Middleware `home/middleware.py` (`MaintenanceModeMiddleware`), insertado en `config/settings.py` después de `AuthenticationMiddleware`. Si `activo=True`, cualquier visitante no-staff recibe `503` + página `templates/maintenance.html` en cualquier URL. `/admin/`, `/ckeditor/`, estáticos y media quedan exentos. Usuarios `is_staff` navegan el sitio normal para poder verificar y desactivarlo.
- `templates/maintenance.html`: página standalone (no extiende `base.html`) con logo, mensaje editable, contacto (email + 2 teléfonos), links a Facebook/Instagram y botones de WhatsApp a los dos números — todo tomado de `templates/includes/footer.html`.

Se probó primero en local, se subió por FTP a producción (6 archivos: `config/settings.py`, `home/admin.py`, `home/models.py`, `home/middleware.py`, `home/migrations/0002_maintenancemode.py`, `templates/maintenance.html`) **antes** de tocar el repo en el servidor, y recién después se commiteó/pusheó a `fix-orange` — para minimizar la ventana sin defensa durante el resto de la migración. Requirió `python manage.py migrate home` en producción para crear la tabla.

## Sincronización final del repo en producción (25 sep 2026)

Como el Paso 3 ya estaba hecho de antes (ver nota al principio del documento), sincronizar producción con el commit nuevo (`c202bc7`) no requirió un `checkout -f` desde cero, sino:

```bash
cd ~/orangetravel
git fetch origin
# Verificar que los archivos subidos por FTP coinciden exacto con lo commiteado (ver método en "Estado verificado" arriba)
git reset --hard origin/fix-orange
git status   # debe quedar limpio salvo .env_, tmp/, home/templates/home/index_2.html
git log -1 --oneline   # c202bc7
touch tmp/restart.txt
```

`reset --hard` es seguro acá porque se verificó primero que el contenido en disco (subido por FTP) era byte-a-byte idéntico al del commit — no se perdió ni sobreescribió nada real, solo se actualizó el puntero de la rama y se pasaron a "tracked" los 3 archivos nuevos.

## De ahí en adelante — flujo normal de deploy

```bash
cd ~/orangetravel
git pull
# si cambió algo de Tailwind/CSS/JS/Vue:
npm run build
~/virtualenv/orangetravel/3.11/bin/python manage.py collectstatic --noinput
# si hay migraciones nuevas:
~/virtualenv/orangetravel/3.11/bin/python manage.py migrate
touch tmp/restart.txt
```

Ver también `docs/DEPLOY.md` para la regla completa de cuándo hacer cada paso.
