# Incidente: video del banner no carga (Range → 500) — 15 oct 2026

## Síntoma

- En la home, el video `https://orangetravel.cl/static/video/banner-home.mp4` no cargaba.
- Firefox mostraba `NS_BINDING_ABORTED` en la pestaña Red.
- Funcionaba hasta ~2 horas antes y no hubo cambios relacionados en el código (el commit previo, `3a189d1 Reserva día siguiente`, solo tocó vistas de reservas y `BookingApp.vue`).

## Diagnóstico

Los navegadores piden los videos por trozos (cabecera `Range`, p. ej. Firefox envía `Range: bytes=0-`). Pruebas contra producción:

| Petición | Resultado |
|---|---|
| `GET` del video sin `Range` | 200 ✅ |
| `GET` del video con `Range: bytes=0-1023` | **500** ❌ |
| `GET` de `styles.css` con `Range` | **500** ❌ |
| `HEAD` del video con `Range` | 206 ✅ (cabeceras correctas) |
| `GET /` con `Range` | 200 (Django ignora `Range` en HTML) |

Conclusión: falla **toda respuesta 206 con cuerpo** de archivos estáticos, sin importar HTTP/1.1 o HTTP/2 ni el tamaño pedido. El 500 es la página genérica de LiteSpeed, no de Django.

Verificación por SSH (ejecutando `passenger_wsgi.application` con un environ simulado y `Range: bytes=0-1023`): Django/WhiteNoise responde `206 Partial Content`, `Content-Range: bytes 0-1023/18388884`, 1024 bytes. **Python funciona bien; el 500 lo genera LiteSpeed al entregar el 206.**

Pista adicional: `~/logs/passenger.log` dejó de escribirse a las **16:53** (hora del server, `-03`), coincidiendo con el inicio del problema. No aparece ningún traceback del video.

## Causa

Cambio del lado del hosting. cPanelHost había avisado ese día (10:11) que trasladaría la cuenta a un servidor nuevo "con otro tipo de cortafuegos", con la migración durante la noche del 15 al 16 oct. Lo más probable es que ya hubieran empezado a cambiar la forma en que LiteSpeed atiende la app Python.

## Qué se hizo

1. `5c1fc45 Fix video banner`: en `passenger_wsgi.py`, se quita `wsgi.file_wrapper` del environ en peticiones con `Range` (hipótesis: el file_wrapper de LiteSpeed no soportaba el `SlicedFile` de WhiteNoise). **No resolvió el problema**: candidato a revertir.
2. `71f5177 Oculta temporalmente video banner`: se comentó la sección `<video>` en `home/templates/home/index.html`.
   - Al ser un cambio de template, requiere `touch tmp/restart.txt` (o Restart desde cPanel) tras el `git pull`; con `DEBUG=False` Django cachea los templates.

## Estado tras el cambio de cortafuegos (16 oct 2026)

El hosting ya aplicó el cambio y **el problema sigue igual**:

| Petición | Resultado |
|---|---|
| `GET` del video sin `Range` | 200 ✅ |
| `GET` del video con `Range: bytes=0-1023` (HTTP/2 y HTTP/1.1) | **500** ❌ |
| `HEAD` del video con `Range` | 206 ✅ (ETag de WhiteNoise: la petición sí llega a Django) |
| `GET` de `/static/js/dist/assets/styles.css` con `Range` | **500** ❌ |

El cuerpo del 500 es la página genérica de LiteSpeed (`DTD HTML 2.0`, `charset=iso-8859-1`), no la de Django.

### Por qué falla aunque el video esté en el servidor

En este hosting `/static/...` no lo entrega LiteSpeed desde el disco; pasa por la app Python:

```
navegador → LiteSpeed → app Python (Django + WhiteNoise lee staticfiles/) → LiteSpeed → navegador
```

Django genera bien el 206, pero LiteSpeed lo convierte en 500 al reenviarlo. Mientras el video pase por Python va a fallar, esté donde esté dentro del proyecto. No se arregla desde el código de Django (`5c1fc45` no sirvió).

- En la práctica solo afecta a video/audio: los navegadores no piden CSS ni imágenes con `Range`.
- **Safari/iOS exige 206 para reproducir video**, así que quitar el `Range` en Python (para que WhiteNoise responda 200 completo) no es solución: el video no se vería en iPhone.

## Estrategia elegida: que LiteSpeed sirva `/static/` directamente

LiteSpeed sí responde 206 correctamente con archivos propios. Se crea un enlace simbólico **relativo** en la raíz pública del dominio hacia `staticfiles/`, para que LiteSpeed entregue `/static/` sin pasar por Python. Ventajas: el enlace se actualiza solo con cada `collectstatic`, y CSS/JS también se sirven más rápido.

1. Revisar antes de crear nada (por SSH):
   ```bash
   ls -la ~/public_html/          # que no exista ya "static"
   cat ~/public_html/.htaccess    # revisar reglas
   ```
2. Si `static` no existe, crear el enlace y probar:
   ```bash
   cd ~/public_html
   ln -s ../orangetravel/staticfiles static
   curl -s -o /dev/null -w "%{http_code}\n" -H "Range: bytes=0-1023" https://orangetravel.cl/static/video/banner-home.mp4
   ```
3. Si responde **206**: descomentar el video en `home/templates/home/index.html`, revertir `5c1fc45` y, tras el `git pull`, `touch tmp/restart.txt`.
4. Si sigue en **500**: LiteSpeed manda todo a Python aunque el archivo exista en el docroot. Opciones:
   - Reclamar al hosting con la evidencia de arriba (es un fallo de su lado).
   - Servir el video desde Cloudinary (ya configurado para media). Lo saca del camino Python → LiteSpeed y de paso lo comprime.
5. Para deshacer: `rm ~/public_html/static` (borra solo el enlace, no los archivos).

En cualquier caso conviene avisar al hosting del 500 en respuestas 206, porque es una regresión suya.

## Pendiente tras la migración del hosting

1. Aplicar la estrategia de arriba y verificar que el video responde 206.
2. Revisar lo que la migración puede haber movido:
   - Variables de entorno en cPanel → Setup Python App (`DATABASE_URL`, `FLOW_*`, `MAILGUN_*`, etc.).
   - Ruta del home (hoy `/home3/cor116358/`) y virtualenv; actualizar `CLAUDE.md` si cambian.
   - Que `~/logs/passenger.log` vuelva a registrar (visitar una URL inexistente y buscar el `Not Found`).
   - Que `touch tmp/restart.txt` siga reiniciando la app.
   - Que `git pull` funcione desde el server.
   - Que no se haya copiado un `.env` en la raíz del proyecto.
   - Una reserva o pago de prueba (Flow + emails).

## Mejora independiente

`banner-home.mp4` pesa 18 MB y se carga con `preload="auto"` en cada visita a la home. Conviene comprimirlo o servirlo desde Cloudinary.
