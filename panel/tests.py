from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from payments.models import Payment
from tours.models import Reserva, TipoTour, Tour

User = get_user_model()


class PanelBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('staff', password='x', is_staff=True)
        cls.normal = User.objects.create_user('normal', password='x')
        tipo = TipoTour.objects.create(nombre='Cat')
        cls.tour = Tour.objects.create(tipo=tipo, nombre='Tour A', slug='tour-a')
        cls.reserva = Reserva.objects.create(
            tour=cls.tour, nombre_cliente='Ana', email_cliente='a@x.cl',
            telefono_cliente='1', fecha=date.today() + timedelta(days=5),
        )
        cls.pago = Payment.objects.create(
            tour=cls.tour, amount=1000, status=Payment.STATUS_PAID,
            customer_name='Ana', customer_email='a@x.cl',
            reservation_date=date.today() + timedelta(days=5),
        )


class AccesoTests(PanelBase):
    def test_anonimo_redirige_a_login(self):
        for name in ('dashboard', 'reservas', 'pagos'):
            r = self.client.get(reverse(f'panel:{name}'))
            self.assertRedirects(r, f"{reverse('panel:login')}?next={reverse(f'panel:{name}')}")

    def test_post_anonimo_redirige(self):
        r = self.client.post(reverse('panel:reserva_eliminar', args=[self.reserva.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())

    def test_login_sin_next_va_al_dashboard(self):
        r = self.client.post(reverse('panel:login'), {'username': 'staff', 'password': 'x'})
        self.assertRedirects(r, reverse('panel:dashboard'))

    def test_no_staff_no_puede_loguear(self):
        r = self.client.post(reverse('panel:login'), {'username': 'normal', 'password': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_no_staff_logueado_recibe_403(self):
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get(reverse('panel:dashboard')).status_code, 403)

    def test_staff_login_y_acceso(self):
        r = self.client.post(reverse('panel:login'), {'username': 'staff', 'password': 'x', 'next': reverse('panel:reservas')})
        self.assertRedirects(r, reverse('panel:reservas'))
        for name in ('dashboard', 'reservas', 'pagos'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 200)

    def test_endpoint_pagos_admin_exige_staff(self):
        url = reverse('api_admin_pagos', args=[self.tour.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)


class ReservaTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_filtros_y_detalle(self):
        r = self.client.get(reverse('panel:reservas'), {'q': self.reserva.codigo, 'estado': 'PENDIENTE'})
        self.assertContains(r, self.reserva.codigo)
        r = self.client.get(reverse('panel:reservas'), {'estado': 'CONFIRMADA'})
        self.assertNotContains(r, self.reserva.codigo)
        self.assertEqual(self.client.get(reverse('panel:reserva_detalle', args=[self.reserva.pk])).status_code, 200)

    @patch('tours.signals.send_mail')
    def test_cambio_estado_dispara_signal_de_correo(self, send_mail):
        self.client.post(reverse('panel:reserva_detalle', args=[self.reserva.pk]),
                         {'estado': 'CONFIRMADA', 'notas_internas': 'ok'})
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'CONFIRMADA')
        self.assertEqual(send_mail.call_count, 1)

    def test_eliminar_es_borrado_logico(self):
        self.client.post(reverse('panel:reserva_eliminar', args=[self.reserva.pk]))
        self.assertFalse(Reserva.objects.filter(pk=self.reserva.pk).exists())
        self.assertTrue(Reserva.all_objects.filter(pk=self.reserva.pk).exists())

    def test_eliminar_por_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('panel:reserva_eliminar', args=[self.reserva.pk])).status_code, 405)


class PagoTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_lista_y_detalle(self):
        self.assertContains(self.client.get(reverse('panel:pagos')), self.pago.codigo)
        self.assertContains(self.client.get(reverse('panel:pago_detalle', args=[self.pago.pk])), 'Reenviar al cliente')

    @patch('panel.views.send_payment_confirmation_to_admins')
    @patch('panel.views.send_payment_confirmation_to_customer')
    def test_reenviar(self, cliente, admin):
        self.client.post(reverse('panel:pago_reenviar', args=[self.pago.pk, 'cliente']))
        self.client.post(reverse('panel:pago_reenviar', args=[self.pago.pk, 'admin']))
        cliente.assert_called_once_with(self.pago)
        admin.assert_called_once_with(self.pago)

    @patch('panel.views.send_payment_confirmation_to_customer')
    def test_no_reenvia_si_no_pagado(self, cliente):
        Payment.objects.filter(pk=self.pago.pk).update(status=Payment.STATUS_PENDING)
        self.client.post(reverse('panel:pago_reenviar', args=[self.pago.pk, 'cliente']))
        cliente.assert_not_called()
