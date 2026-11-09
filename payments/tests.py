import io
from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from home.models import MaintenanceMode
from tours.models import TIPO_CON_PRECIO_ID, PrecioTour, TipoTour, Tour

from .models import Payment


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class MantencionFlowTests(TestCase):
    """Con el sitio en mantención, la vuelta de Flow debe seguir funcionando."""

    @classmethod
    def setUpTestData(cls):
        tipo = TipoTour.objects.create(pk=TIPO_CON_PRECIO_ID, nombre='Excursiones de un Día')
        cls.tour = Tour.objects.create(tipo=tipo, nombre='Tour A', slug='tour-a')
        PrecioTour.objects.create(tour=cls.tour, valor_adulto=20000)

    def setUp(self):
        mantencion = MaintenanceMode.get_solo()
        mantencion.activo = True
        mantencion.save()
        self.pago = Payment.objects.create(
            tour=self.tour, amount=20000, status=Payment.STATUS_PENDING,
            customer_name='Ann', customer_email='ann@example.com', customer_phone='+56 9 1111 2222',
            reservation_date=date.today() + timedelta(days=5), pax_adults=1, pax_children=0,
            idioma='en', provider_token='tok-123',
        )

    @patch('payments.views.FlowClient.get_status', return_value={'status': 2})
    def test_webhook_confirma_y_envia_emails(self, _):
        r = self.client.post(reverse('flow_confirm'), {'token': 'tok-123'})
        self.assertEqual(r.status_code, 200)
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.status, Payment.STATUS_PAID)
        asuntos = [m.subject for m in mail.outbox]
        self.assertEqual(len(asuntos), 2)
        self.assertTrue(any(a.startswith('✅ Booking Confirmed') for a in asuntos))
        self.assertTrue(any(a.startswith('🚨 PAGO RECIBIDO') for a in asuntos))

    @patch('payments.views.FlowClient.get_status', return_value={'status': 2})
    def test_return_anonimo_llega_a_la_confirmacion(self, _):
        r = self.client.post(reverse('flow_return'), {'token': 'tok-123'}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'payments/confirmacion_reserva.html')

    def test_checkout_sigue_bloqueado(self):
        r = self.client.post(reverse('tour_checkout', args=[self.tour.id]), {})
        self.assertEqual(r.status_code, 503)


def stdout_ascii():
    """stdout como el de Passenger en int15: ASCII estricto (un emoji o tilde lanza error)."""
    return patch('sys.stdout', io.TextIOWrapper(io.BytesIO(), encoding='ascii'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class StdoutAsciiPagoTests(TestCase):
    """En int15 un print() con emoji cortaba los emails de pago (15 oct - 9 nov 2026)."""

    @classmethod
    def setUpTestData(cls):
        tipo = TipoTour.objects.create(pk=TIPO_CON_PRECIO_ID, nombre='Excursiones de un Día')
        cls.tour = Tour.objects.create(tipo=tipo, nombre='Excursión Valle', slug='valle')
        PrecioTour.objects.create(tour=cls.tour, valor_adulto=20000)

    def _pago(self, **extra):
        datos = dict(
            tour=self.tour, amount=20000, status=Payment.STATUS_PENDING,
            customer_name='José Peña', customer_email='jose@example.com', customer_phone='+56 9 1111 2222',
            reservation_date=date.today() + timedelta(days=5), pax_adults=1, pax_children=0,
            idioma='en', provider_token='tok-ascii',
        )
        datos.update(extra)
        return Payment.objects.create(**datos)

    @patch('payments.views.FlowClient.get_status', return_value={'status': 2})
    def test_return_envia_emails_con_stdout_ascii(self, _):
        pago = self._pago()
        with stdout_ascii():
            self.client.post(reverse('flow_return'), {'token': 'tok-ascii'})
        pago.refresh_from_db()
        self.assertEqual(pago.status, Payment.STATUS_PAID)
        self.assertEqual(len(mail.outbox), 2)

    def test_fallo_del_cliente_no_frena_al_admin(self):
        from . import emails
        pago = self._pago()
        with patch.object(emails, 'send_payment_confirmation_to_customer', side_effect=RuntimeError('Mailgun')), \
                self.assertLogs('payments.emails', level='ERROR'):
            emails.enviar_confirmacion_pago(pago)
        self.assertEqual([m.subject for m in mail.outbox], ['🚨 PAGO RECIBIDO - José Peña'])

    @patch('payments.views.FlowClient.is_configured', return_value=True)
    @patch('payments.views.FlowClient.create_payment')
    def test_checkout_con_tildes_y_stdout_ascii(self, create_payment, _):
        create_payment.return_value.token = 'tok-nuevo'
        create_payment.return_value.raw = {}
        create_payment.return_value.redirect_url = 'https://sandbox.flow.cl/pay?token=tok-nuevo'
        payload = {'nombre': 'José Peña', 'email': 'jose@example.com', 'telefono': '+56911112222',
                   'fecha': str(date.today() + timedelta(days=5)), 'adultos': 1, 'ninos': 0,
                   'total': 20000, 'idioma': 'es'}
        with stdout_ascii():
            r = self.client.post(reverse('tour_checkout', args=[self.tour.id]), payload, content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
