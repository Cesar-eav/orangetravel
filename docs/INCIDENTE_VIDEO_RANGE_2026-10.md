# Incidente: video del banner no carga (Range → 500) — 15-16 oct 2026

**Estado: resuelto el 16 oct 2026.** El video se volvió a mostrar con `38bd5ba`.

## Resumen

- El 15 oct 2026 a las 15:57 cPanelHost trasladó la cuenta de `srv28.cpanelhost.cl` (190.107.177.38) a `int15.cpanelhost.cl` (138.117.148.165, LiteSpeed). El DNS pasó a int15, pero el SSH y el cPanel que se usaban seguían entrando a srv28.
- En int15, LiteSpeed devolvía 500 en las respuestas 206 (peticiones con `Range`) de archivos estáticos servidos por Django/WhiteNoise. Los navegadores piden el video con `Range`, así que no cargaba.
- El arreglo `5c1fc45` (en `passenger_wsgi.py`, quitar `wsgi.file_wrapper` del environ en peticiones con `Range`) **sí resuelve el problema**, pero ese día se desplegó en srv28, que ya no recibía tráfico. Por eso pareció que no servía y se ocultó el video (`71f5177`).
- El 16 oct se desplegó en int15 (`git pull` hasta `0729b1d` + `npm run build` + `collectstatic` + Restart desde cPanel): `Range` → 206 con HTTP/2 y HTTP/1.1, desde el server y desde fuera. Se revirtió `71f5177` con `38bd5ba`.
- **No revertir `5c1fc45`**: es lo que hace funcionar el video en int15.

## Síntoma

- En la home, el video `https://orangetravel.cl/static/video/banner-home.mp4` no cargaba.
- Firefox mostraba `NS_BINDING_ABORTED` en la pestaña Red.
- Empezó cerca de las 16:53 del 15 oct, sin cambios relacionados en el código.

## Diagnóstico (contra el sitio público, int15)

| Petición | Resultado |
|---|---|
| `GET` del video sin `Range` | 200 ✅ |
| `GET` del video con `Range: bytes=0-1023` (HTTP/2 y HTTP/1.1) | **500** ❌ |
| `GET` de `/static/js/dist/assets/styles.css` con `Range` | **500** ❌ |
| `HEAD` del video con `Range` | 206 ✅ (ETag de WhiteNoise: la petición llega a Django) |
| `GET /` con `Range` | 200 (Django ignora `Range` en HTML) |

El cuerpo del 500 era la página genérica de LiteSpeed (`DTD HTML 2.0`, `charset=iso-8859-1`), no la de Django. En este hosting `/static/...` no lo entrega LiteSpeed desde el disco, sino la app Python:

```
navegador → LiteSpeed → app Python (Django + WhiteNoise lee staticfiles/) → LiteSpeed → navegador
```

Django generaba bien el 206, y LiteSpeed fallaba al entregarlo usando su `wsgi.file_wrapper` con el `SlicedFile` de WhiteNoise.

### Lo que confundió el diagnóstico

- Las pruebas por SSH (ejecutar `passenger_wsgi.application` con un environ simulado) se hicieron en **srv28**, no en int15.
- `~/logs/passenger.log` dejó de escribirse a las 16:53 porque era el log de srv28, que dejó de recibir visitas cuando el DNS pasó a int15.
- El 16 oct en la mañana se interpretó al revés: que srv28 era el servidor nuevo y el DNS había quedado mal. El hosting lo aclaró con su registro (`srv28 > int15 - 2026-10-15 15:57:18`). La base de srv28 es una copia anterior (nada posterior al 14/10 22:01) y no tiene datos que falten en int15.

## Qué se hizo

1. `5c1fc45 Fix video banner`: quita `wsgi.file_wrapper` en peticiones con `Range`. Es el arreglo efectivo.
2. `71f5177 Oculta temporalmente video banner`: se comentó el `<video>`. Revertido por `38bd5ba`.
3. Deploy en int15 el 16 oct; detalle en `CLAUDE.md` → "Producción y deploy" (`hostname`, Node en `/opt/alt/alt-nodejs22`, Restart desde cPanel).

## Alternativas que no hicieron falta

- Enlace simbólico `~/public_html/static → ../orangetravel/staticfiles` para que LiteSpeed sirva `/static/` directamente.
- Servir el video desde Cloudinary.
- Quitar el `Range` en Python: descartado porque Safari/iOS exige 206 para reproducir video.

## Pendiente

- `banner-home.mp4` pesa 18 MB y se carga con `preload="auto"` en cada visita a la home. Conviene comprimirlo o servirlo desde Cloudinary.
- Verificar en int15: que `~/logs/passenger.log` registre (visitar una URL inexistente y buscar el `Not Found`) y si `touch tmp/restart.txt` reinicia la app.
- Una reserva o pago de prueba en int15 (Flow + emails).
