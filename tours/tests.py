import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import TIPO_CON_PRECIO_ID, Cotizacion, PrecioTour, TipoTour, Tour


class CotizacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        con_precio = TipoTour.objects.create(pk=TIPO_CON_PRECIO_ID, nombre='Excursiones de un Día')
        a_cotizar = TipoTour.objects.create(pk=2, nombre='Trekking y Expediciones')
        cls.tour_precio = Tour.objects.create(tipo=con_precio, nombre='Valle', slug='valle', imagen_principal='tours/principales/a.jpg')
        PrecioTour.objects.create(tour=cls.tour_precio, valor_adulto=20000)
        cls.tour_cotizar = Tour.objects.create(tipo=a_cotizar, nombre='Surire', slug='surire', imagen_principal='tours/principales/b.jpg')
        cls.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)

    def _post(self, **datos):
        payload = {'tour_id': self.tour_cotizar.pk, 'nombre': 'Ana Pérez', 'email': 'ana@x.cl',
                   'telefono': '+56912345678', 'adultos': 2, 'ninos': 1, 'mensaje': 'Hola'}
        payload.update(datos)
        return self.client.post(reverse('crear_cotizacion'), json.dumps(payload), content_type='application/json')

    def test_con_precio_solo_categoria_1(self):
        self.assertTrue(self.tour_precio.con_precio)
        self.assertFalse(self.tour_cotizar.con_precio)

    @patch('tours.views.threading.Thread')
    def test_crea_cotizacion_y_envia_emails(self, thread):
        fecha = date.today() + timedelta(days=10)
        r = self._post(fecha=fecha.isoformat())
        self.assertEqual(r.status_code, 201)
        c = Cotizacion.objects.get()
        self.assertEqual((c.tour, c.adultos, c.ninos, c.fecha_tentativa), (self.tour_cotizar, 2, 1, fecha))
        thread.return_value.start.assert_called_once()

    @patch('tours.views.threading.Thread')
    def test_fecha_es_opcional(self, thread):
        self.assertEqual(self._post(fecha='').status_code, 201)
        self.assertIsNone(Cotizacion.objects.get().fecha_tentativa)

    def test_rechaza_tour_con_precio(self):
        self.assertEqual(self._post(tour_id=self.tour_precio.pk).status_code, 400)
        self.assertFalse(Cotizacion.objects.exists())

    def test_rechaza_datos_invalidos(self):
        self.assertEqual(self._post(email='no-es-email').status_code, 400)
        self.assertEqual(self._post(fecha=date.today().isoformat()).status_code, 400)
        self.assertEqual(self._post(tour_id=999).status_code, 404)
        self.assertFalse(Cotizacion.objects.exists())

    def test_checkout_rechaza_tour_de_cotizacion(self):
        r = self.client.post(reverse('tour_checkout', args=[self.tour_cotizar.pk]),
                             {'email': 'ana@x.cl'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_pagina_tour_elige_widget(self):
        r = self.client.get(reverse('tour', args=[self.tour_cotizar.slug]))
        self.assertContains(r, 'data-con-precio="0"')
        self.assertIn('csrftoken', r.cookies)
        r = self.client.get(reverse('tour', args=[self.tour_precio.slug]))
        self.assertContains(r, 'data-con-precio="1"')

    def test_listado_muestra_a_cotizar(self):
        r = self.client.get(reverse('tours_home'))
        self.assertContains(r, 'A cotizar')
        self.assertContains(r, '$20000')

    def test_panel_lista_y_marca_atendida(self):
        c = Cotizacion.objects.create(tour=self.tour_cotizar, nombre='Ana', email='ana@x.cl', telefono='12345678')
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse('panel:cotizaciones')), 'Ana')
        self.client.post(reverse('panel:cotizacion_detalle', args=[c.pk]), {'atendida': 'on'})
        c.refresh_from_db()
        self.assertTrue(c.atendida)
