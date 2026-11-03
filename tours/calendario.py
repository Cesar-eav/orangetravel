"""Link «Agregar a Google Calendar» para reservas y ventas confirmadas.

No usa la API de Google: arma la URL de plantilla que abre Google Calendar con el
evento prellenado y la persona lo guarda. `authuser` sugiere la cuenta de
GOOGLE_CALENDAR_EMAIL, pero Google usa la cuenta activa si esa no tiene sesión.
"""
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse

from .models import Reserva, Venta
from .templatetags.precios import clp

URL_PLANTILLA = 'https://calendar.google.com/calendar/render'
LARGO_MAX_NOTAS = 800


def _corto(texto):
    texto = (texto or '').strip()
    return texto if len(texto) <= LARGO_MAX_NOTAS else texto[:LARGO_MAX_NOTAS] + '…'


def _pasajeros(n, singular, plural):
    return f'{n} {singular if n == 1 else plural}'


def _datos_reserva(r):
    titulo = f'{r.tour.nombre_es} – {r.nombre_cliente}'
    lineas = [
        f'Reserva {r.codigo}',
        f'Cliente: {r.nombre_cliente}',
        f'Email: {r.email_cliente}',
        f'Teléfono: {r.telefono_cliente}',
        f'Pasajeros: {_pasajeros(r.adultos, "adulto", "adultos")}'
        + (f', {_pasajeros(r.ninos, "niño", "niños")}' if r.ninos else ''),
        f'Total: ${clp(r.precio_total)}',
    ]
    if notas := _corto(r.notas_internas):
        lineas.append(f'Notas: {notas}')
    panel = reverse('panel:reserva_detalle', args=[r.pk])
    return r.fecha, titulo, lineas, panel


def _datos_venta(v):
    titulo = f'{v.servicio} – {v.nombre_cliente}'
    lineas = [f'Venta manual ({v.get_canal_display()})', f'Cliente: {v.nombre_cliente}']
    if v.telefono:
        lineas.append(f'Teléfono: {v.telefono}')
    if v.email:
        lineas.append(f'Email: {v.email}')
    if v.destino:
        lineas.append(f'Destino: {v.destino}')
    lineas += [
        f'Pasajeros: {_pasajeros(v.pasajeros, "persona", "personas")}',
        f'Total: ${clp(v.precio_total)} ({v.get_estado_pago_display()}, saldo ${clp(v.saldo_pendiente)})',
    ]
    if obs := _corto(v.observaciones):
        lineas.append(f'Observaciones: {obs}')
    panel = reverse('panel:venta_editar', args=[v.pk])
    return v.fecha_servicio, titulo, lineas, panel


def esta_confirmada(obj):
    if isinstance(obj, Reserva):
        return obj.estado == Reserva.Estado.CONFIRMADA
    return obj.estado_reserva == Venta.EstadoReserva.CONFIRMADA


def url_google_calendar(obj):
    """URL que abre Google Calendar con un evento de día completo para la reserva o venta."""
    fecha, titulo, lineas, panel = (_datos_reserva if isinstance(obj, Reserva) else _datos_venta)(obj)
    lineas.append(f'Panel: {settings.SITE_URL}{panel}')
    params = {
        'action': 'TEMPLATE',
        'text': titulo,
        # Día completo: el fin es exclusivo, por eso va el día siguiente.
        'dates': f'{fecha:%Y%m%d}/{fecha + timedelta(days=1):%Y%m%d}',
        'details': '\n'.join(lineas),
    }
    if settings.GOOGLE_CALENDAR_EMAIL:
        params['authuser'] = settings.GOOGLE_CALENDAR_EMAIL
    return f'{URL_PLANTILLA}?{urlencode(params)}'


def contexto_calendario(obj, request):
    """Variables para panel/_google_calendar.html (vacío si no está confirmada)."""
    if obj is None or not obj.pk or not esta_confirmada(obj):
        return {}
    return {
        'url_calendario': url_google_calendar(obj),
        'email_calendario': settings.GOOGLE_CALENDAR_EMAIL,
        'mostrar_popup_calendario': bool(request.GET.get('agregar_calendario')),
    }
