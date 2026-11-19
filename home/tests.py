import time
from unittest.mock import patch

from django.core import mail, signing
from django.test import TestCase, override_settings
from django.urls import reverse

from . import antispam


def ts_valido(segundos_atras=10):
    """Marca de tiempo firmada como si el formulario se hubiera mostrado hace un rato."""
    return signing.dumps(time.time() - segundos_atras, salt=antispam._SALT)


CACHE_REAL = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    'antispam': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'antispam-tests'},
}


def respuesta_turnstile(success, codigos=()):
    class R:
        def json(self):
            return {'success': success, 'error-codes': list(codigos)}
    return R()


class ContactoAntispamTests(TestCase):
    def _post(self, **datos):
        payload = {'nombre': 'Ana Pérez', 'email': 'ana@x.cl', 'phone': '+56 9 1234 5678',
                   'asunto': 'consulta', 'mensaje': 'Hola, quiero info', 'origen': 'contacto',
                   'ts': ts_valido()}
        payload.update(datos)
        return self.client.post(reverse('contacto_formulario'), payload, follow=True)

    def test_envio_valido_manda_email_con_reply_to(self):
        r = self._post()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['info@orangetravel.cl'])
        self.assertEqual(mail.outbox[0].reply_to, ['ana@x.cl'])
        self.assertRedirects(r, reverse('contacto') + '#formulario-contacto')
        self.assertContains(r, 'Recibimos tu mensaje')

    def test_honeypot_no_envia_pero_responde_exito(self):
        r = self._post(sitio_web='http://spam.example')
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(r, 'Recibimos tu mensaje')

    def test_sin_marca_o_muy_rapido_no_envia(self):
        self._post(ts='')
        self._post(ts='no-firmado')
        self._post(ts=ts_valido(segundos_atras=0))
        self.assertEqual(len(mail.outbox), 0)

    def test_pagina_vencida_avisa(self):
        r = self._post(ts=ts_valido(segundos_atras=2 * 24 * 3600))
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(r, 'Recárgala')

    @override_settings(TURNSTILE_SECRET_KEY='secreto')
    @patch('home.antispam.requests.post', return_value=respuesta_turnstile(False, ['invalid-input-response']))
    def test_turnstile_rechazado_no_envia(self, post):
        r = self._post(**{'cf-turnstile-response': 'token-falso'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(r, 'robot')
        self.assertEqual(post.call_args.kwargs['data']['response'], 'token-falso')

    @override_settings(TURNSTILE_SECRET_KEY='secreto')
    @patch('home.antispam.requests.post')
    def test_turnstile_sin_token_no_llama_a_cloudflare(self, post):
        self._post()
        self.assertEqual(len(mail.outbox), 0)
        post.assert_not_called()

    @override_settings(TURNSTILE_SECRET_KEY='secreto')
    @patch('home.antispam.requests.post', return_value=respuesta_turnstile(True))
    def test_turnstile_ok_envia(self, post):
        self._post(**{'cf-turnstile-response': 'token-bueno'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(post.call_args.kwargs['data']['remoteip'], '127.0.0.1')

    @override_settings(TURNSTILE_SECRET_KEY='secreto')
    @patch('home.antispam.requests.post', side_effect=OSError('sin red'))
    def test_cloudflare_caido_deja_pasar(self, post):
        self._post(**{'cf-turnstile-response': 'token'})
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(CACHES=CACHE_REAL)
    def test_limite_por_ip(self):
        for _ in range(5):
            self._post()
        r = self._post()
        self.assertEqual(len(mail.outbox), 5)
        self.assertContains(r, 'varios mensajes')

    def test_html_del_mensaje_sale_escapado(self):
        self._post(nombre='Ana <b>', mensaje='<a href="http://spam.example">gana dinero</a>')
        html = mail.outbox[0].alternatives[0][0]
        self.assertNotIn('<a href="http://spam.example">', html)
        self.assertIn('&lt;a href=', html)

    def test_datos_invalidos_no_envia(self):
        self._post(email='no-es-email')
        self._post(mensaje='   ')
        self.assertEqual(len(mail.outbox), 0)

    def test_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('contacto_formulario')).status_code, 405)

    def test_origen_home_vuelve_al_home(self):
        r = self._post(origen='home')
        self.assertRedirects(r, reverse('home') + '#formulario-contacto')

    def test_formulario_trae_campos_antispam(self):
        r = self.client.get(reverse('contacto'))
        self.assertContains(r, 'name="sitio_web"')
        self.assertContains(r, 'name="ts"')
        self.assertNotContains(r, 'cf-turnstile')  # sin site key no hay widget
        with self.settings(TURNSTILE_SITE_KEY='clave-publica'):
            r = self.client.get(reverse('contacto'))
        self.assertContains(r, 'data-sitekey="clave-publica"')


class RobotsTxtTests(TestCase):
    def test_robots_txt_en_texto_plano(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/plain')
        contenido = r.content.decode()
        self.assertIn('User-agent: GPTBot\nDisallow: /\n', contenido)
        self.assertIn('Disallow: /panel/', contenido)
        self.assertNotIn('ChatGPT-User', contenido)
