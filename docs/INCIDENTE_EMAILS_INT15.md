# Incidente: emails sin enviar en int15 (15 oct – 9 nov 2026)

## Resumen

Desde que el hosting trasladó la cuenta de `srv28` a `int15` (15 oct 2026, 15:57), **ningún pago con Flow envió emails**, ni al cliente ni al admin. En reservas y cotizaciones sí llegaba el email al cliente, pero no el del admin. Además, el checkout fallaba con error 500 cuando el nombre del cliente tenía tilde o ñ.

Causa: en int15 Passenger arranca Python con la **salida estándar (stdout) en ASCII**. Cualquier `print()` con un emoji o una tilde lanza `UnicodeEncodeError`, y el código tenía `print()` de depuración justo antes o entre los envíos de email.

Detectado el 9 nov 2026 con un pago de prueba en sandbox desde `/en/`. Corregido en el commit `e2b6dbc`.

## Síntoma

Pago de prueba en sandbox: llegaba el correo de Flow, pero ninguno de Orange Travel. Al principio pareció un problema del sitio en inglés o del modo mantención, pero no era ninguno de los dos.

## Diagnóstico

En el server, el `Payment` de la prueba estaba en `paid` (`flow_status=2`): Flow sí había confirmado el pago. En `~/orangetravel/stderr.log` aparecía:

```
Error enviando correo en retorno: 'ascii' codec can't encode character '\U0001f34a' in position 7: ordinal not in range(128)
```

`\U0001f34a` es 🍊. La primera línea de `payments/emails.py::enviar_confirmacion_pago` era:

```python
print(f"DEBUG: 🍊 Iniciando envío vía Anymail (Mailgun API) para Pago #{payment.id}...")
```

Ese `print` lanzaba la excepción antes de enviar nada. `FlowReturnView` la capturaba y la registraba en el log, así que el sitio funcionaba con normalidad y nadie se enteraba.

En srv28 el mismo código funcionaba: `~/logs/passenger.log` (el log de srv28, que termina el 15 oct) muestra los envíos correctos hasta esa fecha.

¿Por qué stdout y no stderr? Python 3 abre stderr con `errors='backslashreplace'`, así que nunca falla al escribir (por eso en el log se ve `\xf3` en vez de «ó»). En cambio, stdout usa `errors='strict'` y lanza la excepción.

## Impacto

| Flujo | Qué fallaba |
|---|---|
| Pago con Flow (`payments/emails.py`) | No salía ningún email (cliente ni admin). El pago sí quedaba registrado como pagado. |
| Reserva sin pago (`tours/views.py::enviar_notificaciones_reserva`) | Salía el email al cliente; el `print` siguiente cortaba el del admin. |
| Cotización (`tours/views.py::enviar_notificaciones_cotizacion`) | Salía el email al cliente; el `print("📧 …")` previo cortaba el del admin. |
| Checkout (`payments/views.py::TourCheckoutView`) | `print("Resreva: ", data)` daba error 500 si el nombre traía tilde o ñ: el cliente no podía pagar. |

## Arreglo (commit `e2b6dbc`)

1. **`passenger_wsgi.py`** fuerza UTF-8 en stdout y stderr al arrancar (`reconfigure(encoding='utf-8', errors='backslashreplace')`). Esto cubre cualquier `print` que quede en el proyecto.
2. **Los envíos de email ya no usan `print`.** En pagos, reservas y cotizaciones, cada email (cliente y admin) va en su propio `try`, y los errores se registran con `logger.exception`. Si falla uno, el otro igual sale.
3. **Se quitaron los `print` de depuración** del checkout y de `payments/flow.py` (uno de ellos escribía la API key de Flow en el log).
4. **Tests** (`payments/tests.py`, `tours/tests.py`) que reemplazan stdout por uno ASCII estricto, como el de int15. Con el código anterior fallan los 5.

## Cambio relacionado: modo mantención (commit `289d4a8`)

Durante el diagnóstico apareció otro problema. Con el modo mantención activo, las rutas de vuelta de Flow (`/pagos/flow-confirm/` y `/pagos/flow-return/`) respondían 503 y el pago quedaba en `pending`. El webhook llega sin cookies, y el return es un POST desde flow.cl en el que la cookie de sesión (`SameSite=Lax`) no viaja, así que ni el staff se ve logueado. Ahora esas rutas y la página de confirmación quedan exentas de la mantención; el checkout sigue bloqueado.

No era la causa del incidente: la segunda prueba se hizo con la mantención apagada y tampoco llegaron los emails.

## Pendientes

- **Ventas del 15 oct al 9 nov sin aviso.** Revisar en el panel los `Payment` pagados en ese período, porque el equipo no recibió el email de ninguno:
  ```bash
  ~/virtualenv/orangetravel/3.11/bin/python manage.py shell -c "
  from payments.models import Payment
  for p in Payment.objects.filter(status='paid', paid_at__date__gte='2026-10-15').order_by('paid_at'):
      print(p.id, p.codigo, p.paid_at, p.customer_name, p.customer_email, p.tour_nombre_al_pagar)
  "
  ```
  Lo mismo para las reservas y cotizaciones de ese período (el admin no recibió aviso, aunque aparecen en `/panel/`).

## Webhook de Flow que no llega

Los pagos de prueba 226 y 227 no tienen `raw_confirm_payload`: el webhook `/pagos/flow-confirm/` no llegó (o no se procesó) y se marcaron pagados solo porque el usuario volvió al sitio desde Flow. Si el cliente no vuelve (cierra la pestaña, paga desde la app del banco, se corta la conexión) o el medio de pago confirma más tarde, el pago queda en `pending` para siempre. Eso significa que no salen emails, que el panel no lo muestra como venta y que **la fecha no se bloquea en el calendario** (`get_fechas_bloqueadas` solo cuenta pagos `paid`), con riesgo de sobreventa.

La causa exacta no está confirmada (puede ser int15 —firewall o ModSecurity— o algo del sandbox). Arreglo:

1. **Conciliación por cron (no depende del webhook).** `python manage.py conciliar_pagos_flow` le pregunta a Flow (`payment/getStatus`) por cada pago `pending` de los últimos 3 días y aplica el resultado: pagado (con emails), rechazado/anulado o sigue pendiente. Opciones: `--dias N`, `--simular`, `--sin-emails`.
2. **Una sola lógica de confirmación** (`payments/confirmacion.py::aplicar_estado_flow`) para el webhook, el retorno y el cron, con un UPDATE condicional sobre `paid_at`: los emails salen una sola vez aunque las tres vías coincidan.
3. **URLs para Flow siempre en `https://` en producción.** Si llegara `http://`, `SECURE_SSL_REDIRECT` respondería 301 y Flow no repite el POST del webhook tras una redirección.
4. **Logging (`LOGGING` en `config/settings.py`) a `stderr.log`:** «Webhook Flow recibido (token …)» en cada llamada, el resultado de cada webhook y la `urlConfirmation` que se envía a Flow en cada checkout.

### Puesta en marcha en el server

1. `git pull` + Restart desde cPanel.
2. Revisar primero sin cambiar nada (ojo con la regla 3 del CLAUDE.md: toca la BD real):
   ```bash
   ~/virtualenv/orangetravel/3.11/bin/python manage.py conciliar_pagos_flow --simular --dias 30
   ```
   Los pagos sandbox (p. ej. 225) saldrán como `error` (las keys de producción no reconocen tokens de sandbox): es lo esperado.
3. Si aparecen pagos reales que Flow da como pagados (`flow_status=2`), decidir con el equipo antes de confirmarlos: con emails (`--dias 30`) o sin ellos (`--dias 30 --sin-emails`) y avisar al cliente a mano.
4. Crear el cron en cPanel → Cron Jobs, cada 10 minutos:
   ```
   */10 * * * * cd ~/orangetravel && ~/virtualenv/orangetravel/3.11/bin/python manage.py conciliar_pagos_flow >> ~/orangetravel/conciliar.log 2>&1
   ```
   Comprobar en `conciliar.log`, tras la primera ejecución, que dice «N pagos pendientes revisados» y no «Flow no está configurado» (eso indicaría que el cron no recibe las variables de cPanel).
5. Tras el próximo pago, buscar `Webhook Flow recibido` en `~/orangetravel/stderr.log`. Si no aparece, el webhook no está llegando a Django: revisar el log de acceso de LiteSpeed (`POST /pagos/flow-confirm/`) o consultar al hosting por bloqueos de ModSecurity. Mientras tanto, el cron cubre la confirmación con un retraso máximo de 10 minutos.

## Lecciones

- **No usar `print` en código de producción**; usar `logging`. Y nunca poner nada que pueda fallar antes de un envío importante.
- **Un `try` por envío**: si falla el email al cliente, no debe perderse el aviso al equipo.
- **Tras una migración de servidor, probar los flujos de punta a punta** (pago, reserva, cotización) y confirmar que llegan los emails, no solo que el sitio cargue.
- **El log de la app en int15 es `~/orangetravel/stderr.log`**, no `~/logs/passenger.log`.
