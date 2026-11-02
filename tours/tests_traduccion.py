import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from home.models import SitioIngles
from payments.emails import get_email_admin_pago
from payments.models import Payment

from .models import TIPO_CON_PRECIO_ID, Cotizacion, Reserva, TipoTour, Tour

# Los datos se crean con <campo>_es explícito: una vista que activa otro idioma deja ese
# idioma activo en el hilo, y Tour(nombre=...) escribe en el campo del idioma activo.
from .views import EMAIL_POR_TOUR, enviar_notificaciones_cotizacion, get_email_admin


class SitioInglesTests(TestCase):
    """Interruptores de «Sitio en inglés»: /en/ accesible por link y banderas (anuncio + Google)."""

    @classmethod
    def setUpTestData(cls):
        tipo = TipoTour.objects.create(pk=TIPO_CON_PRECIO_ID, nombre_es='Excursiones de un Día')
        cls.tour = Tour.objects.create(tipo=tipo, nombre_es='Valle de Azapa', nombre_en='Azapa Valley',
                                       slug='valle', imagen_principal='tours/principales/a.jpg')
        cls.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)

    def _config(self, publico=True, banderas=False):
        cfg = SitioIngles.get_solo()
        cfg.publico, cfg.mostrar_banderas = publico, banderas
        cfg.save()

    def test_por_defecto_en_accesible_por_link_sin_banderas_ni_indexar(self):
        self._config()
        r = self.client.get('/en/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '<html lang="en">')
        self.assertContains(r, 'name="robots" content="noindex"')
        self.assertNotContains(r, 'name="language"')
        r = self.client.get('/')
        self.assertNotContains(r, 'name="language"')
        self.assertNotContains(r, 'hreflang')
        self.assertNotContains(r, 'noindex')

    def test_no_accesible_es_404_para_el_publico_y_visible_para_staff(self):
        self._config(publico=False)
        self.assertEqual(self.client.get('/en/').status_code, 404)
        self.client.force_login(self.staff)
        r = self.client.get('/en/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="language"')

    def test_banderas_selector_hreflang_y_memoria(self):
        self._config(banderas=True)
        r = self.client.get('/en/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'hreflang="en"')
        r = self.client.post('/i18n/setlang/', {'language': 'en', 'next': '/tours/'})
        self.assertRedirects(r, '/en/tours/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/contacto/'), '/en/contacto/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/tours/api/bloqueos/%d/' % self.tour.pk).status_code, 200)
        r = self.client.post('/en/i18n/setlang/', {'language': 'es', 'next': '/en/tours/'})
        self.assertRedirects(r, '/tours/', fetch_redirect_response=False)

    def test_sin_aprobar_el_publico_ve_espanol_y_el_staff_el_borrador(self):
        self._config(banderas=True)
        url = f'/en/tours/tour/{self.tour.slug}/'
        r = self.client.get(url)
        self.assertContains(r, 'Valle de Azapa')
        self.assertNotContains(r, 'Azapa Valley')
        self.assertContains(r, 'rel="canonical"')
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(url), 'Azapa Valley')
        self.client.logout()
        Tour.objects.filter(pk=self.tour.pk).update(traduccion_en_aprobada=True)
        self.assertContains(self.client.get(url), 'Azapa Valley')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailsIdiomaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tipo = TipoTour.objects.create(pk=2, nombre_es='Trekking y Expediciones')
        cls.keyword, cls.destino = next(iter(EMAIL_POR_TOUR.items()))
        cls.tour = Tour.objects.create(tipo=tipo, nombre_es=f'Tour {cls.keyword.title()}', nombre_en='Salt flat tour',
                                       traduccion_en_aprobada=True, slug='t', imagen_principal='tours/principales/b.jpg')

    def test_ruteo_admin_usa_el_nombre_en_espanol(self):
        with translation.override('en'):
            tour = Tour.objects.get(pk=self.tour.pk)
            self.assertEqual(tour.nombre, 'Salt flat tour')
            self.assertEqual(get_email_admin(Reserva(tour=tour)), self.destino)
            self.assertEqual(get_email_admin_pago(Payment(tour=tour)), self.destino)

    @patch('tours.views.threading.Thread')
    def test_cotizacion_en_ingles_guarda_idioma_y_responde_en_ingles(self, thread):
        r = self.client.post(reverse('crear_cotizacion'), json.dumps({
            'tour_id': self.tour.pk, 'nombre': 'John Smith', 'email': 'john@example.com',
            'telefono': '+15550100', 'fecha': (date.today() + timedelta(days=5)).isoformat(), 'idioma': 'en',
        }), content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertIn('Request received', r.json()['mensaje'])
        self.assertEqual(Cotizacion.objects.get().idioma, 'en')

    def test_email_cliente_en_su_idioma_y_admin_en_espanol(self):
        c = Cotizacion.objects.create(tour=self.tour, nombre='John', email='john@example.com',
                                      telefono='+15550100', idioma='en')
        enviar_notificaciones_cotizacion(c)
        cliente, admin = mail.outbox
        self.assertIn('Quote request: Salt flat tour', cliente.subject)
        self.assertIn('We received your quote request', cliente.alternatives[0][0])
        self.assertEqual(admin.to, [self.destino])
        self.assertIn('NUEVA SOLICITUD DE COTIZACIÓN', admin.alternatives[0][0])
        self.assertIn('Idioma del cliente', admin.alternatives[0][0])
