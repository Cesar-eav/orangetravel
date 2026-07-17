# Deploy y archivos estaticos

Guia rapida para saber cuando ejecutar `npm run build`, `collectstatic` y reiniciar la app en produccion.

## Regla corta

- Cambios en HTML/templates solamente: subir archivos y reiniciar la app si Passenger no refleja el cambio.
- Cambios en Python: subir archivos y reiniciar la app.
- Cambios en clases Tailwind, CSS, JS o Vue: ejecutar `npm run build`, subir el build y ejecutar `collectstatic`.
- Nuevos archivos en `static/`, como imagenes o videos: subirlos y ejecutar `collectstatic`.
- Archivos en `media/`: no pasan por `collectstatic`; deben estar disponibles en `/media/` o en el storage configurado.

## Cuando usar `npm run build`

Ejecutar `npm run build` cuando cambie algo que afecte los assets compilados:

- Agregas o cambias clases Tailwind en templates, por ejemplo `mt-20`, `h-120`, `bg-orange-500`.
- Editas `static/src/input.css`.
- Editas `static/src/main.js`.
- Editas componentes Vue en `static/src/components/`.
- Cambias configuracion de Vite o Tailwind.

El build genera archivos en:

```bash
static/js/dist/
```

Si el servidor no puede ejecutar Node/npm, corre el build en desarrollo y sube por FTP la carpeta:

```bash
static/js/dist/
```

## Cuando usar `collectstatic`

Ejecutar `collectstatic` en produccion cuando cambie cualquier archivo servido desde `static/`:

- Despues de `npm run build`.
- Despues de subir imagenes, videos, CSS o JS a `static/`.
- Despues de cambiar archivos en `static/js/dist/`.

Comando:

```bash
cd ~/orangetravel
.venv/bin/python manage.py collectstatic --noinput
```

Si el virtualenv esta fuera del proyecto, usar el Python correcto del hosting. Ejemplo:

```bash
cd ~/orangetravel
~/virtualenv/orangetravel/*/bin/python manage.py collectstatic --noinput
```

## Cuando reiniciar la app

Reiniciar Passenger cuando cambie codigo del servidor o cuando el sitio siga mostrando una version anterior:

- Cambios en `.py`.
- Cambios en settings, urls, modelos, vistas o admin.
- Cambios en templates que Passenger no refresca.
- Despues de `collectstatic` si WhiteNoise o el navegador siguen sirviendo archivos antiguos.

Opciones usuales:

```bash
cd ~/orangetravel
mkdir -p tmp
touch tmp/restart.txt
```

Tambien se puede reiniciar desde cPanel si esta disponible.

## Flujo recomendado por tipo de cambio

### Solo templates HTML

```bash
git pull
touch tmp/restart.txt
```

### Python, vistas, modelos o admin

```bash
git pull
.venv/bin/python manage.py migrate
touch tmp/restart.txt
```

Usar `migrate` solo si hay migraciones nuevas.

### Tailwind, CSS, JS o Vue

```bash
git pull
npm run build
.venv/bin/python manage.py collectstatic --noinput
touch tmp/restart.txt
```

### Archivo nuevo en `static/`

Ejemplo: `static/video/banner-home.mp4`.

```bash
git pull
.venv/bin/python manage.py collectstatic --noinput
touch tmp/restart.txt
```

Si se agregaron clases Tailwind nuevas en templates junto con el archivo, tambien correr:

```bash
npm run build
```

antes de `collectstatic`.

## Verificaciones utiles

Ver si el archivo existe en el static publico:

```bash
ls -l ~/orangetravel/staticfiles/video/banner-home.mp4
```

Probar la URL directa:

```text
https://orangetravel.cl/static/video/banner-home.mp4
```

Verificar Django:

```bash
.venv/bin/python manage.py check
```

## Nota sobre cache

Si el HTML cambio pero el estilo no aparece, puede ser por una de estas razones:

- No se ejecuto `npm run build` despues de agregar clases Tailwind.
- No se ejecuto `collectstatic` despues del build.
- El navegador esta usando CSS antiguo en cache.
- Passenger/WhiteNoise sigue sirviendo una version anterior hasta reiniciar la app.
