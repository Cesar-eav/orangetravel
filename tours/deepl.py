"""Cliente mínimo de la API de DeepL (español → inglés) con glosario de términos protegidos.

La cuenta es de Orange Travel; la clave llega por DEEPL_API_KEY (cPanel en producción).
Las claves del plan gratuito terminan en «:fx» y usan otro host.
"""
import html
import re

import requests
from django.conf import settings

from .glosario import GLOSARIO

LOTE = 50  # textos por request (límite de DeepL)


class DeepLError(Exception):
    pass


def _url(clave):
    host = 'api-free.deepl.com' if clave.endswith(':fx') else 'api.deepl.com'
    return f'https://{host}/v2/translate'


def _proteger(texto):
    """Encierra cada término del glosario en <x> (DeepL no traduce lo que va en ignore_tags).

    Si el glosario fija una traducción, se envía ya traducida dentro de <x>.
    Los términos más largos van primero para que «Salar de Surire» gane sobre «Surire».
    Solo se toca el texto entre etiquetas, nunca atributos (alt, src, href).
    """
    partes = re.split(r'(<[^>]+>)', texto)
    for i in range(0, len(partes), 2):
        for termino in sorted(GLOSARIO, key=len, reverse=True):
            destino = GLOSARIO[termino] or termino
            patron = r'(?<!\w)' + re.escape(termino) + r'(?!\w)'
            partes[i] = re.sub(patron, lambda m, d=destino: f'\x00{d}\x01', partes[i])
        partes[i] = partes[i].replace('\x00', '<x>').replace('\x01', '</x>')
    return ''.join(partes)


def traducir(textos, es_html=False):
    """Traduce una lista de textos del español al inglés. Devuelve la lista en el mismo orden."""
    clave = getattr(settings, 'DEEPL_API_KEY', None)
    if not clave:
        raise DeepLError('Falta DEEPL_API_KEY: cárgala en cPanel (producción) o en el .env (local).')
    resultado = []
    for i in range(0, len(textos), LOTE):
        lote = [_proteger(t if es_html else html.escape(t, quote=False)) for t in textos[i:i + LOTE]]
        r = requests.post(
            _url(clave),
            headers={'Authorization': f'DeepL-Auth-Key {clave}'},
            json={
                'text': lote,
                'source_lang': 'ES',
                'target_lang': 'EN-US',
                'tag_handling': 'html',
                'ignore_tags': ['x'],
            },
            timeout=60,
        )
        if r.status_code == 456:
            raise DeepLError('Se agotó la cuota mensual de caracteres de DeepL.')
        if r.status_code in (401, 403):
            raise DeepLError('DeepL rechazó la clave (DEEPL_API_KEY).')
        if r.status_code != 200:
            raise DeepLError(f'DeepL respondió {r.status_code}: {r.text[:200]}')
        for t in r.json()['translations']:
            texto = re.sub(r'</?x>', '', t['text'])
            resultado.append(texto if es_html else html.unescape(texto))
    return resultado
