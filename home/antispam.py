"""Protección antispam de los formularios públicos (contacto, cotización, checkout).

Capas, de la más barata a la más cara:
1. Honeypot: campo `sitio_web` oculto; una persona no lo ve, un bot lo llena.
2. Tiempo: marca firmada del momento en que se mostró el formulario; un bot que
   envía en menos de `TIEMPO_MINIMO` segundos (o sin la marca) no es una persona.
3. Límite por IP: máximo de envíos por ventana de tiempo (cache `antispam`).
4. Cloudflare Turnstile: captcha casi siempre invisible, verificado en el servidor.

Turnstile falla abierto: sin `TURNSTILE_SECRET_KEY` o si Cloudflare no responde, el
envío pasa (las otras capas siguen activas). Cada rechazo queda en el log `home.antispam`
(en int15, `~/orangetravel/stderr.log`) con el motivo y la IP, sin datos del formulario.
"""
import ipaddress
import logging
import time

import requests
from django.conf import settings
from django.core import signing
from django.core.cache import caches

logger = logging.getLogger(__name__)

CAMPO_HONEYPOT = 'sitio_web'
CAMPO_TIEMPO = 'ts'
CAMPO_TURNSTILE = 'cf-turnstile-response'  # nombre que usa el widget en un <form> normal

TIEMPO_MINIMO = 3            # segundos desde que se mostró el formulario
TIEMPO_MAXIMO = 24 * 3600    # después de esto la página se considera vencida
TURNSTILE_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
_SALT = 'home.antispam.formulario'

# Motivos ante los que se responde como si el envío hubiera salido bien, para no
# darle pistas al bot. El resto (límite, Turnstile, página vencida) se le muestra
# a la persona, que puede reintentar.
MOTIVOS_SILENCIOSOS = {'honeypot', 'tiempo'}


def ip_cliente(request):
    """IP del visitante. Si REMOTE_ADDR es local/privada (proxy delante), usa X-Forwarded-For."""
    remota = request.META.get('REMOTE_ADDR', '') or ''
    try:
        privada = ipaddress.ip_address(remota).is_private
    except ValueError:
        privada = True
    if privada:
        reenviada = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
        if reenviada:
            return reenviada[:45]
    return remota[:45]


def marca_tiempo():
    """Valor firmado para el campo oculto `ts` del formulario."""
    return signing.dumps(time.time(), salt=_SALT)


def revisar_tiempo(valor):
    """None si está bien; 'tiempo' si falta, es inválida o muy rápida; 'expirado' si es vieja."""
    if not valor:
        return 'tiempo'
    try:
        emitida = float(signing.loads(str(valor), salt=_SALT))
    except (signing.BadSignature, TypeError, ValueError):
        return 'tiempo'
    transcurrido = time.time() - emitida
    if transcurrido < TIEMPO_MINIMO:
        return 'tiempo'
    if transcurrido > TIEMPO_MAXIMO:
        return 'expirado'
    return None


def excede_limite(ip, clave, maximo, ventana):
    """Suma un envío de `ip` en `clave` y dice si ya pasó `maximo` en la ventana actual."""
    cache = caches['antispam']
    llave = f'antispam:{clave}:{ip}:{int(time.time() // ventana)}'
    try:
        cuenta = (cache.get(llave) or 0) + 1
        cache.set(llave, cuenta, ventana)
    except Exception:
        logger.exception('Antispam: no se pudo usar el cache del límite por IP')
        return False
    return cuenta > maximo


def verificar_turnstile(token, ip):
    """True si Cloudflare valida el token (o si no hay clave / Cloudflare no responde)."""
    secreto = settings.TURNSTILE_SECRET_KEY
    if not secreto:
        return True
    if not token:
        return False
    try:
        respuesta = requests.post(
            TURNSTILE_URL,
            data={'secret': secreto, 'response': str(token)[:2048], 'remoteip': ip},
            timeout=5,
        )
        resultado = respuesta.json()
    except Exception:
        logger.exception('Antispam: Cloudflare Turnstile no respondió; se deja pasar el envío')
        return True
    if not resultado.get('success'):
        logger.info('Antispam: Turnstile rechazó el token (%s)', ','.join(resultado.get('error-codes') or []))
        return False
    return True


def revisar(request, datos, *, clave, maximo, ventana=3600, turnstile=True, tiempo=True):
    """Corre las capas sobre `datos` (request.POST o el JSON) y devuelve el motivo del
    rechazo ('honeypot', 'tiempo', 'expirado', 'limite', 'turnstile') o None si pasa."""
    ip = ip_cliente(request)
    motivo = None
    if str(datos.get(CAMPO_HONEYPOT) or '').strip():
        motivo = 'honeypot'
    elif tiempo:
        motivo = revisar_tiempo(datos.get(CAMPO_TIEMPO))
    if not motivo and excede_limite(ip, clave, maximo, ventana):
        motivo = 'limite'
    if not motivo and turnstile:
        token = datos.get(CAMPO_TURNSTILE) or datos.get('turnstile_token')
        if not verificar_turnstile(token, ip):
            motivo = 'turnstile'
    if motivo:
        logger.info('Antispam: envío rechazado en %s (motivo=%s, ip=%s)', clave, motivo, ip)
    return motivo
