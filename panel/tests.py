from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from payments.models import Payment
from tours.calendario import url_google_calendar
from tours.models import Reserva, TipoTour, Tour, Venta

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

    @patch('tours.signals.send_mail', side_effect=Exception('Mailgun 403'))
    def test_falla_del_email_no_impide_confirmar(self, send_mail):
        with self.assertLogs('tours.signals', 'ERROR'):
            r = self.client.post(reverse('panel:reserva_detalle', args=[self.reserva.pk]),
                                 {'estado': 'CONFIRMADA', 'notas_internas': 'ok'}, follow=True)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'CONFIRMADA')
        self.assertContains(r, 'no se pudo enviar el email')
        self.assertNotContains(r, 'Reserva actualizada.')

    @patch('tours.signals.send_mail', side_effect=Exception('Mailgun 403'))
    def test_falla_del_email_igual_libera_la_fecha(self, send_mail):
        with self.assertLogs('tours.signals', 'ERROR'):
            self.client.post(reverse('panel:reserva_detalle', args=[self.reserva.pk]),
                             {'estado': 'CANCELADA', 'notas_internas': ''})
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'CANCELADA')
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.status, Payment.STATUS_CANCELED)

    @patch('tours.signals.send_mail')
    def test_guardar_sin_cambiar_estado_no_envia_email(self, send_mail):
        self.client.post(reverse('panel:reserva_detalle', args=[self.reserva.pk]),
                         {'estado': 'PENDIENTE', 'notas_internas': 'solo nota'})
        send_mail.assert_not_called()

    def test_eliminar_es_borrado_logico(self):
        self.client.post(reverse('panel:reserva_eliminar', args=[self.reserva.pk]))
        self.assertFalse(Reserva.objects.filter(pk=self.reserva.pk).exists())
        self.assertTrue(Reserva.all_objects.filter(pk=self.reserva.pk).exists())

    def test_eliminar_por_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('panel:reserva_eliminar', args=[self.reserva.pk])).status_code, 405)

    def test_eliminar_desde_lista_vuelve_con_filtros(self):
        next_url = '/panel/reservas/?estado=PENDIENTE&page=2'
        r = self.client.post(reverse('panel:reserva_eliminar', args=[self.reserva.pk]), {'next': next_url})
        self.assertRedirects(r, next_url, fetch_redirect_response=False)
        # La página 2 ya no existe: la lista muestra la última en vez de un 404
        self.assertEqual(self.client.get(next_url).status_code, 200)

    def test_eliminar_con_next_externo_vuelve_a_reservas(self):
        r = self.client.post(reverse('panel:reserva_eliminar', args=[self.reserva.pk]),
                             {'next': 'https://evil.com/'})
        self.assertRedirects(r, reverse('panel:reservas'), fetch_redirect_response=False)

    def test_lista_muestra_eliminar_seleccionadas(self):
        r = self.client.get(reverse('panel:reservas'))
        self.assertContains(r, reverse('panel:reservas_eliminar'))
        self.assertContains(r, f'name="ids" value="{self.reserva.pk}"')

    def test_eliminar_seleccionadas_solo_borra_las_marcadas(self):
        otra = Reserva.objects.create(
            tour=self.tour, nombre_cliente='Beto', email_cliente='b@x.cl',
            telefono_cliente='2', fecha=date.today() + timedelta(days=6),
        )
        tercera = Reserva.objects.create(
            tour=self.tour, nombre_cliente='Caro', email_cliente='c@x.cl',
            telefono_cliente='3', fecha=date.today() + timedelta(days=7),
        )
        next_url = '/panel/reservas/?estado=PENDIENTE'
        r = self.client.post(reverse('panel:reservas_eliminar'),
                             {'ids': [self.reserva.pk, otra.pk, 'x'], 'next': next_url})
        self.assertRedirects(r, next_url, fetch_redirect_response=False)
        self.assertFalse(Reserva.objects.filter(pk__in=[self.reserva.pk, otra.pk]).exists())
        self.assertEqual(Reserva.all_objects.filter(pk__in=[self.reserva.pk, otra.pk]).count(), 2)
        self.assertTrue(Reserva.objects.filter(pk=tercera.pk).exists())

    def test_eliminar_seleccionadas_por_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('panel:reservas_eliminar')).status_code, 405)

    def test_eliminar_seleccionadas_anonimo_no_borra(self):
        self.client.logout()
        self.client.post(reverse('panel:reservas_eliminar'), {'ids': [self.reserva.pk]})
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())


class CatalogoTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_anonimo_redirige(self):
        self.client.logout()
        for name in ('tours', 'tour_nuevo', 'tipos', 'bloqueos'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 302)

    def test_paginas_cargan(self):
        for name in ('tours', 'tour_nuevo', 'tipos', 'tipo_nuevo', 'bloqueos'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 200, name)
        self.assertEqual(self.client.get(reverse('panel:tour_editar', args=[self.tour.pk])).status_code, 200)

    def test_cambiar_categoria_desde_listado(self):
        otra = TipoTour.objects.create(nombre='Otra')
        url = reverse('panel:tour_cambiar_tipo', args=[self.tour.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        r = self.client.post(url, {'tipo': otra.pk, 'next': '/panel/tours/?q=Tour'})
        self.assertRedirects(r, '/panel/tours/?q=Tour', fetch_redirect_response=False)
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.tipo_id, otra.pk)
        self.client.force_login(self.normal)
        self.assertEqual(self.client.post(url, {'tipo': self.tour.tipo_id}).status_code, 403)

    def test_editar_tour_crea_precio(self):
        from tours.models import PrecioTour
        Tour.objects.filter(pk=self.tour.pk).update(imagen_principal='tours/principales/x.jpg')
        r = self.client.post(reverse('panel:tour_editar', args=[self.tour.pk]), {
            't-nombre': 'Tour A2', 't-slug': 'tour-a', 't-tipo': self.tour.tipo_id,
            't-itinerario': 'x', 't-incluye': 'y', 't-activo': 'on',
            'd-TOTAL_FORMS': '0', 'd-INITIAL_FORMS': '0',
            'p-valor_adulto': '20000', 'p-valor_nino': '0',
        })
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.nombre, 'Tour A2')
        self.assertEqual(PrecioTour.objects.get(tour=self.tour).valor_adulto, 20000)

    def test_guardar_dias_del_itinerario(self):
        Tour.objects.filter(pk=self.tour.pk).update(imagen_principal='tours/principales/x.jpg')
        r = self.client.post(reverse('panel:tour_editar', args=[self.tour.pk]), {
            't-nombre': 'Tour A', 't-slug': 'tour-a', 't-tipo': self.tour.tipo_id,
            't-itinerario': 'resumen', 't-incluye': 'y', 't-activo': 'on',
            'p-valor_adulto': '20000', 'p-valor_nino': '0',
            'd-TOTAL_FORMS': '2', 'd-INITIAL_FORMS': '0',
            'd-0-orden': '1', 'd-0-titulo': 'Llegada', 'd-0-descripcion': 'a',
            'd-1-orden': '2', 'd-1-titulo': 'Valles', 'd-1-descripcion': 'b',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.tour.dias.values_list('orden', 'titulo')), [(1, 'Llegada'), (2, 'Valles')])

    def test_precio_nino_obligatorio_si_activado(self):
        r = self.client.post(reverse('panel:tour_editar', args=[self.tour.pk]), {
            't-nombre': 'Tour A', 't-slug': 'tour-a', 't-tipo': self.tour.tipo_id,
            't-itinerario': 'x', 't-incluye': 'y',
            'd-TOTAL_FORMS': '0', 'd-INITIAL_FORMS': '0',
            'p-valor_adulto': '20000', 'p-tiene_precio_nino': 'on', 'p-valor_nino': '0',
        })
        self.assertEqual(r.status_code, 200)

    def _post_tour(self, pk=None, **extra):
        data = {
            't-nombre': 'Tour Nuevo', 't-slug': '', 't-tipo': self.tour.tipo_id,
            't-itinerario': '<p>resumen</p>', 't-incluye': '', 't-activo': 'on',
            'd-TOTAL_FORMS': '0', 'd-INITIAL_FORMS': '0',
            'p-valor_adulto': '20000', 'p-valor_nino': '0',
        }
        data.update(extra)
        url = reverse('panel:tour_editar', args=[pk]) if pk else reverse('panel:tour_nuevo')
        return self.client.post(url, data)

    def test_incluye_vacio_guarda_y_precio_nino_se_fuerza_a_cero(self):
        Tour.objects.filter(pk=self.tour.pk).update(imagen_principal='tours/principales/x.jpg')
        r = self._post_tour(self.tour.pk, **{'t-slug': 'tour-a', 'p-valor_nino': '5000'})
        self.assertEqual(r.status_code, 302)
        from tours.models import PrecioTour
        self.assertEqual(PrecioTour.objects.get(tour=self.tour).valor_nino, 0)

    def test_fallo_muestra_resumen_de_errores(self):
        Tour.objects.filter(pk=self.tour.pk).update(imagen_principal='tours/principales/x.jpg')
        r = self._post_tour(self.tour.pk, **{'t-slug': 'tour-a', 't-itinerario': '<p>&nbsp;</p>',
                                             't-video_youtube': 'https://example.com/x'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No se guardó el tour')
        self.assertContains(r, 'Escribe el resumen del tour')
        self.assertContains(r, 'No parece un enlace de YouTube')

    def test_slug_se_autogenera_y_no_colisiona(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image
        for _ in range(2):
            b = io.BytesIO(); Image.new('RGB', (4, 4)).save(b, 'PNG')
            r = self._post_tour(**{'t-imagen_principal': SimpleUploadedFile('i.png', b.getvalue(), 'image/png')})
            self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        self.assertEqual(sorted(Tour.objects.filter(nombre='Tour Nuevo').values_list('slug', flat=True)),
                         ['tour-nuevo', 'tour-nuevo-2'])

    def test_fila_de_dia_en_blanco_se_ignora(self):
        Tour.objects.filter(pk=self.tour.pk).update(imagen_principal='tours/principales/x.jpg')
        r = self._post_tour(self.tour.pk, **{
            't-slug': 'tour-a', 'd-TOTAL_FORMS': '1', 'd-0-orden': '1', 'd-0-titulo': '', 'd-0-descripcion': '',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.tour.dias.count(), 0)

    def test_categoria_con_tours_no_se_elimina(self):
        from tours.models import TipoTour
        self.client.post(reverse('panel:tipo_eliminar', args=[self.tour.tipo_id]))
        self.assertTrue(TipoTour.objects.filter(pk=self.tour.tipo_id).exists())
        vacia = TipoTour.objects.create(nombre='Vacía')
        self.client.post(reverse('panel:tipo_eliminar', args=[vacia.pk]))
        self.assertFalse(TipoTour.objects.filter(pk=vacia.pk).exists())

    def test_bloqueos_crear_duplicado_y_eliminar(self):
        from tours.models import BloqueoTour
        datos = {'tour': self.tour.pk, 'fecha': '2030-01-10', 'motivo': 'Clima'}
        self.client.post(reverse('panel:bloqueos'), datos)
        self.client.post(reverse('panel:bloqueos'), datos)
        self.assertEqual(BloqueoTour.objects.count(), 1)
        self.client.post(reverse('panel:bloqueo_eliminar', args=[BloqueoTour.objects.get().pk]))
        self.assertEqual(BloqueoTour.objects.count(), 0)


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

    def _pago_con_reserva(self, email):
        """Pago y la reserva que crea el checkout justo después (mismo tour, fecha y email)."""
        fecha = date.today() + timedelta(days=9)
        pago = Payment.objects.create(
            tour=self.tour, amount=1000, customer_name='Prueba', customer_email=email,
            reservation_date=fecha,
        )
        reserva = Reserva.objects.create(
            tour=self.tour, nombre_cliente='Prueba', email_cliente=email,
            telefono_cliente='9', fecha=fecha,
        )
        return pago, reserva

    def test_lista_muestra_eliminar_seleccionados(self):
        r = self.client.get(reverse('panel:pagos'))
        self.assertContains(r, reverse('panel:pagos_eliminar'))
        self.assertContains(r, f'name="ids" value="{self.pago.pk}"')

    def test_eliminar_seleccionados_borra_pagos_y_sus_reservas(self):
        pago1, reserva1 = self._pago_con_reserva('p1@x.cl')
        pago2, reserva2 = self._pago_con_reserva('p2@x.cl')
        next_url = '/panel/pagos/?status=pending'
        r = self.client.post(reverse('panel:pagos_eliminar'),
                             {'ids': [pago1.pk, pago2.pk, 'x'], 'next': next_url})
        self.assertRedirects(r, next_url, fetch_redirect_response=False)
        # Borrado lógico: siguen en la BD, fuera de la lista.
        self.assertEqual(Payment.objects.filter(pk__in=[pago1.pk, pago2.pk], deleted_at__isnull=False).count(), 2)
        self.assertNotContains(self.client.get(reverse('panel:pagos')), reverse('panel:pago_detalle', args=[pago1.pk]))
        self.assertFalse(Reserva.objects.filter(pk__in=[reserva1.pk, reserva2.pk]).exists())
        self.assertEqual(Reserva.all_objects.filter(pk__in=[reserva1.pk, reserva2.pk]).count(), 2)
        # Lo no marcado queda intacto (la reserva de Ana no es de ningún pago borrado).
        self.assertTrue(Payment.objects.filter(pk=self.pago.pk, deleted_at__isnull=True).exists())
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())

    def test_no_borra_reserva_de_otro_cliente(self):
        pago, _ = self._pago_con_reserva('p1@x.cl')
        _, ajena = self._pago_con_reserva('otro@x.cl')
        self.client.post(reverse('panel:pagos_eliminar'), {'ids': [pago.pk]})
        self.assertTrue(Reserva.objects.filter(pk=ajena.pk).exists())

    def test_eliminar_desde_detalle(self):
        pago, reserva = self._pago_con_reserva('p1@x.cl')
        self.assertContains(self.client.get(reverse('panel:pago_detalle', args=[pago.pk])),
                            reverse('panel:pago_eliminar', args=[pago.pk]))
        r = self.client.post(reverse('panel:pago_eliminar', args=[pago.pk]))
        self.assertRedirects(r, reverse('panel:pagos'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('panel:pago_detalle', args=[pago.pk])).status_code, 404)
        self.assertFalse(Reserva.objects.filter(pk=reserva.pk).exists())

    def test_eliminar_por_get_no_permitido(self):
        self.assertEqual(self.client.get(reverse('panel:pagos_eliminar')).status_code, 405)
        self.assertEqual(self.client.get(reverse('panel:pago_eliminar', args=[self.pago.pk])).status_code, 405)

    def test_eliminar_anonimo_no_borra(self):
        self.client.logout()
        self.client.post(reverse('panel:pagos_eliminar'), {'ids': [self.pago.pk]})
        self.client.post(reverse('panel:pago_eliminar', args=[self.pago.pk]))
        self.assertTrue(Payment.objects.filter(pk=self.pago.pk, deleted_at__isnull=True).exists())


class BlogTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def _post(self, **kw):
        from blog.models import Post
        return Post.objects.create(
            titulo='Reseña', slug='resena', extracto='e', contenido='<p>a</p><p>b</p>',
            imagen_portada='blog/portadas/x.jpg', **kw,
        )

    def _datos(self, **extra):
        datos = {
            'b-titulo': 'Mi viaje', 'b-extracto': 'resumen',
            'b-contenido': '<p>uno</p><p>dos</p>', 'b-publicado': 'on',
            'ip-TOTAL_FORMS': '0', 'ip-INITIAL_FORMS': '0',
            'ip-MIN_NUM_FORMS': '0', 'ip-MAX_NUM_FORMS': '1000',
        }
        datos.update(extra)
        return datos

    def test_anonimo_redirige(self):
        self.client.logout()
        for name in ('posts', 'post_nuevo'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 302)

    def test_paginas_cargan_y_cuenta_bloques(self):
        post = self._post()
        self.assertEqual(self.client.get(reverse('panel:posts')).status_code, 200)
        self.assertEqual(self.client.get(reverse('panel:post_nuevo')).status_code, 200)
        r = self.client.get(reverse('panel:post_editar', args=[post.pk]))
        self.assertContains(r, '2 bloque(s)')

    def test_crear_genera_slug_y_autor(self):
        from blog.models import Post
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.new('RGB', (2, 2)).save(buf, 'PNG')
        img = SimpleUploadedFile('p.png', buf.getvalue(), 'image/png')
        with self.settings(MEDIA_ROOT='/tmp/panel_test_media'):
            r = self.client.post(reverse('panel:post_nuevo'), self._datos(**{'b-imagen_portada': img}))
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        post = Post.objects.get()
        self.assertEqual(post.slug, 'mi-viaje')
        self.assertEqual(post.autor, self.staff)

    def test_slug_automatico_unico_y_estable_al_editar(self):
        from panel.forms import PostForm
        existente = self._post()
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.new('RGB', (2, 2)).save(buf, 'PNG')
        img = SimpleUploadedFile('p.png', buf.getvalue(), 'image/png')
        form = PostForm({'titulo': 'Reseña', 'extracto': 'e', 'contenido': 'x'},
                        {'imagen_portada': img})
        self.assertNotIn('slug', form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        nuevo = form.save(commit=False)
        self.assertEqual(nuevo.slug, 'resena-2')
        # al editar el título, el slug existente no cambia
        form = PostForm({'titulo': 'Otro título', 'extracto': 'e', 'contenido': 'x'},
                        instance=existente)
        form.is_valid()
        self.assertEqual(form.save(commit=False).slug, 'resena')

    def test_extracto_y_cuerpo_respetan_maximo(self):
        from panel.forms import CUERPO_MAX, PostForm
        largo = PostForm({'titulo': 't', 'extracto': 'x' * 501,
                          'contenido': '<p>' + 'a' * (CUERPO_MAX + 1) + '</p>'})
        largo.is_valid()
        self.assertIn('extracto', largo.errors)
        self.assertIn('contenido', largo.errors)
        # las etiquetas HTML no cuentan
        html_ok = PostForm({'titulo': 't', 'extracto': 'x',
                            'contenido': '<p><strong>' + 'a' * CUERPO_MAX + '</strong></p>'})
        html_ok.is_valid()
        self.assertNotIn('contenido', html_ok.errors)

    def test_carrusel_eliminar_y_post_eliminar(self):
        from blog.models import ImagenCarousel, Post
        post = self._post()
        img = ImagenCarousel.objects.create(post=post, imagen='blog/carousel/x.jpg')
        self.client.post(reverse('panel:carrusel_eliminar', args=[img.pk]))
        self.assertFalse(ImagenCarousel.objects.exists())
        self.assertEqual(self.client.get(reverse('panel:post_eliminar', args=[post.pk])).status_code, 405)
        self.client.post(reverse('panel:post_eliminar', args=[post.pk]))
        self.assertFalse(Post.objects.exists())


class SingletonTests(PanelBase):
    def test_anonimo_redirige(self):
        for name in ('nosotros', 'tercera_edad', 'mantencion'):
            r = self.client.get(reverse(f'panel:{name}'))
            self.assertEqual(r.status_code, 302)

    def test_no_staff_403(self):
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get(reverse('panel:mantencion')).status_code, 403)

    def test_guardar_nosotros_y_tercera_edad(self):
        from home.models import Nosotros
        from tours.models import TerceraEdad
        self.client.force_login(self.staff)
        for name, model in (('nosotros', Nosotros), ('tercera_edad', TerceraEdad)):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 200)
            r = self.client.post(reverse(f'panel:{name}'), {'contenido': '<p>Hola</p>'})
            self.assertRedirects(r, reverse(f'panel:{name}'))
            self.assertEqual(model.get_solo().contenido, '<p>Hola</p>')

    def test_activar_mantencion_no_bloquea_al_staff(self):
        from home.models import MaintenanceMode
        self.client.force_login(self.staff)
        r = self.client.post(reverse('panel:mantencion'), {'activo': 'on', 'mensaje': '<p>Volvemos</p>'})
        self.assertRedirects(r, reverse('panel:mantencion'))
        self.assertTrue(MaintenanceMode.get_solo().activo)
        self.assertEqual(self.client.get(reverse('panel:dashboard')).status_code, 200)


class AyudaYNavegacionTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_listas_muestran_ayuda(self):
        for name in ('dashboard', 'reservas', 'pagos', 'tours', 'tipos', 'bloqueos', 'posts'):
            r = self.client.get(reverse(f'panel:{name}'))
            self.assertContains(r, 'class="ayuda"', msg_prefix=name)

    def test_todas_las_pantallas_exigen_staff(self):
        self.client.logout()
        self.client.force_login(self.normal)
        for name in ('dashboard', 'reservas', 'pagos', 'tours', 'tipos', 'bloqueos',
                     'posts', 'nosotros', 'tercera_edad', 'mantencion'):
            r = self.client.get(reverse(f'panel:{name}'))
            self.assertEqual(r.status_code, 403, name)

    def test_logout_solo_por_post(self):
        self.assertEqual(self.client.get(reverse('panel:logout')).status_code, 405)
        r = self.client.post(reverse('panel:logout'))
        self.assertRedirects(r, reverse('panel:login'))

    def test_detalle_inexistente_da_404(self):
        for name in ('reserva_detalle', 'pago_detalle', 'tour_editar', 'tipo_editar', 'post_editar'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}', args=[999999])).status_code, 404, name)

    def test_acciones_destructivas_rechazan_get(self):
        for name in ('reserva_eliminar', 'tipo_eliminar', 'bloqueo_eliminar', 'post_eliminar',
                     'galeria_eliminar', 'carrusel_eliminar'):
            r = self.client.get(reverse(f'panel:{name}', args=[self.reserva.pk]))
            self.assertIn(r.status_code, (404, 405), name)


def datos_venta(**extra):
    datos = {
        'nombre_cliente': 'Luis', 'telefono': '+56911111111', 'email': '',
        'fecha_venta': date.today().isoformat(),
        'fecha_servicio': (date.today() + timedelta(days=3)).isoformat(),
        'canal': 'whatsapp', 'tipo_servicio': 'traslado', 'tour': '',
        'servicio': 'Traslado aeropuerto', 'destino': 'Aeropuerto - Centro', 'pasajeros': 2,
        'precio_total': 30000, 'monto_pagado': 10000, 'medio_pago': 'Transferencia',
        'estado_reserva': 'confirmada', 'observaciones': '',
    }
    datos.update(extra)
    return datos


class VentaTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def _datos(self, **extra):
        return datos_venta(**extra)

    def test_anonimo_redirige(self):
        self.client.logout()
        for name in ('ventas', 'venta_nueva'):
            self.assertEqual(self.client.get(reverse(f'panel:{name}')).status_code, 302)

    def test_crear_servicio_escrito(self):
        r = self.client.post(reverse('panel:venta_nueva'), self._datos(estado_reserva='pendiente'))
        self.assertRedirects(r, reverse('panel:ventas'))
        v = Venta.objects.get()
        self.assertEqual(v.servicio, 'Traslado aeropuerto')
        self.assertEqual(v.estado_pago, Venta.EstadoPago.ABONO)
        self.assertEqual(v.saldo_pendiente, 20000)
        self.assertEqual(v.creada_por, self.staff)

    def test_tour_sin_servicio_usa_nombre_del_tour(self):
        self.client.post(reverse('panel:venta_nueva'), self._datos(tour=self.tour.pk, servicio='', tipo_servicio='tour'))
        self.assertEqual(Venta.objects.get().servicio, self.tour.nombre_es)

    def test_sin_tour_ni_servicio_da_error(self):
        r = self.client.post(reverse('panel:venta_nueva'), self._datos(servicio=''))
        self.assertContains(r, 'Elige un tour o escribe el servicio.')
        self.assertFalse(Venta.objects.exists())

    def test_pagado_mayor_que_total_da_error(self):
        r = self.client.post(reverse('panel:venta_nueva'), self._datos(monto_pagado=40000))
        self.assertContains(r, 'no puede ser mayor que el precio total')
        self.assertFalse(Venta.objects.exists())

    def test_estado_pago_se_calcula(self):
        for pagado, estado in ((30000, 'pagado'), (1, 'abono'), (0, 'pendiente')):
            v = Venta.objects.create(
                nombre_cliente='X', fecha_servicio=date.today(), canal='oficina',
                tipo_servicio='otro', servicio='S', precio_total=30000, monto_pagado=pagado,
            )
            self.assertEqual(v.estado_pago, estado, pagado)

    def test_editar_recalcula_estado_pago(self):
        self.client.post(reverse('panel:venta_nueva'), self._datos())
        v = Venta.objects.get()
        self.client.post(reverse('panel:venta_editar', args=[v.pk]), self._datos(monto_pagado=30000))
        v.refresh_from_db()
        self.assertEqual(v.estado_pago, Venta.EstadoPago.PAGADO)
        self.assertEqual(v.creada_por, self.staff)

    def test_filtros_y_totales(self):
        self.client.post(reverse('panel:venta_nueva'), self._datos(nombre_cliente='Luis'))
        self.client.post(reverse('panel:venta_nueva'), self._datos(nombre_cliente='Marta', canal='oficina', monto_pagado=0))
        r = self.client.get(reverse('panel:ventas'))
        self.assertEqual(r.context['totales'], {'total': 60000, 'pagado': 10000, 'saldo': 50000})
        r = self.client.get(reverse('panel:ventas'), {'canal': 'oficina'})
        self.assertContains(r, 'Marta')
        self.assertNotContains(r, 'Luis')
        r = self.client.get(reverse('panel:ventas'), {'estado_pago': 'abono', 'desde': 'no-es-fecha'})
        self.assertContains(r, 'Luis')
        self.assertNotContains(r, 'Marta')

    def test_eliminar_es_borrado_logico(self):
        self.client.post(reverse('panel:venta_nueva'), self._datos())
        v = Venta.objects.get()
        self.assertEqual(self.client.get(reverse('panel:venta_eliminar', args=[v.pk])).status_code, 405)
        self.client.post(reverse('panel:venta_eliminar', args=[v.pk]))
        self.assertFalse(Venta.objects.filter(pk=v.pk).exists())
        self.assertTrue(Venta.all_objects.filter(pk=v.pk).exists())

    def test_confirmadas_proximas_incluye_ventas(self):
        hoy = date.today()
        for nombre, dias, estado in (
            ('Ana Futura', 3, 'confirmada'), ('Beto Pasado', -3, 'confirmada'),
            ('Ciro Sinconfirmar', 3, 'pendiente'), ('Dora Anulada', 3, 'cancelada'),
        ):
            Venta.objects.create(
                nombre_cliente=nombre, fecha_servicio=hoy + timedelta(days=dias), canal='oficina',
                tipo_servicio='otro', servicio='S', precio_total=1000, estado_reserva=estado,
            )
        r = self.client.get(reverse('panel:dashboard'))
        self.assertEqual(r.context['proximas'], 1)
        self.assertEqual(r.context['proximas_ventas'], 1)
        r = self.client.get(reverse('panel:reservas'), {'estado': 'CONFIRMADA', 'proximas': '1'})
        self.assertContains(r, 'Ana Futura')
        for nombre in ('Beto Pasado', 'Ciro Sinconfirmar', 'Dora Anulada'):
            self.assertNotContains(r, nombre)
        r = self.client.get(reverse('panel:reservas'))
        self.assertNotContains(r, 'Ana Futura')


@override_settings(GOOGLE_CALENDAR_EMAIL='reservas@gmail.com', SITE_URL='https://orangetravel.cl')
class GoogleCalendarTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def _venta(self, **extra):
        datos = dict(
            nombre_cliente='Luis', fecha_servicio=date(2026, 12, 31), canal='whatsapp', tipo_servicio='traslado',
            servicio='Traslado aeropuerto', pasajeros=2, precio_total=30000, monto_pagado=10000,
            estado_reserva='confirmada',
        )
        datos.update(extra)
        return Venta.objects.create(**datos)

    def test_url_reserva_dia_completo_con_cuenta(self):
        self.reserva.fecha = date(2026, 12, 31)
        url = url_google_calendar(self.reserva)
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params['action'], ['TEMPLATE'])
        self.assertEqual(params['dates'], ['20261231/20270101'])
        self.assertEqual(params['text'], ['Tour A – Ana'])
        self.assertEqual(params['authuser'], ['reservas@gmail.com'])
        self.assertIn(self.reserva.codigo, params['details'][0])
        self.assertIn('Pasajeros: 1 adulto\n', params['details'][0])
        self.assertIn(f'https://orangetravel.cl/panel/reservas/{self.reserva.pk}/', params['details'][0])

    @override_settings(GOOGLE_CALENDAR_EMAIL='')
    def test_url_sin_cuenta_configurada(self):
        params = parse_qs(urlparse(url_google_calendar(self._venta())).query)
        self.assertNotIn('authuser', params)
        self.assertEqual(params['text'], ['Traslado aeropuerto – Luis'])
        self.assertIn('Total: $30.000 (Abono, saldo $20.000)', params['details'][0])
        self.assertIn('Pasajeros: 2 personas', params['details'][0])

    @patch('tours.signals.send_mail')
    def test_confirmar_reserva_abre_popup(self, send_mail):
        url = reverse('panel:reserva_detalle', args=[self.reserva.pk])
        r = self.client.get(url)
        self.assertNotContains(r, 'Agregar a Google Calendar')
        r = self.client.post(url, {'estado': 'CONFIRMADA', 'notas_internas': ''})
        self.assertRedirects(r, url + '?agregar_calendario=1')
        r = self.client.get(url + '?agregar_calendario=1')
        self.assertContains(r, '¿Quieres agregar esta reserva confirmada a Google Calendar?')
        self.assertContains(r, 'reservas@gmail.com')
        # Ya confirmada: guardar otra vez no repite el pop up, pero el botón sigue
        r = self.client.post(url, {'estado': 'CONFIRMADA', 'notas_internas': 'van 2'})
        self.assertRedirects(r, url)
        r = self.client.get(url)
        self.assertContains(r, 'Agregar a Google Calendar')
        self.assertNotContains(r, 'popup-calendario')

    def test_venta_nueva_confirmada_abre_popup(self):
        datos = datos_venta()
        r = self.client.post(reverse('panel:venta_nueva'), datos)
        v = Venta.objects.get()
        self.assertRedirects(r, reverse('panel:venta_editar', args=[v.pk]) + '?agregar_calendario=1')
        r = self.client.get(reverse('panel:venta_editar', args=[v.pk]) + '?agregar_calendario=1')
        self.assertContains(r, '¿Quieres agregar esta venta confirmada a Google Calendar?')

    def test_venta_pasa_a_confirmada_abre_popup(self):
        v = self._venta(estado_reserva='pendiente')
        url = reverse('panel:venta_editar', args=[v.pk])
        self.assertNotContains(self.client.get(url), 'Agregar a Google Calendar')
        datos = datos_venta(fecha_servicio=v.fecha_servicio.isoformat())
        r = self.client.post(url, datos)
        self.assertRedirects(r, url + '?agregar_calendario=1')
        # Sin cambiar el estado vuelve a la lista
        r = self.client.post(url, datos)
        self.assertRedirects(r, reverse('panel:ventas'))


class ReservaEstadoDesdeListaTests(PanelBase):
    def setUp(self):
        self.client.force_login(self.staff)
        self.url = reverse('panel:reserva_cambiar_estado', args=[self.reserva.pk])
        self.lista = reverse('panel:reservas') + '?estado=PENDIENTE&page=1'

    def test_solo_post_y_staff(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(self.normal)
        self.client.post(self.url, {'estado': 'CONFIRMADA'})
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'PENDIENTE')

    @patch('tours.signals.send_mail')
    def test_confirmar_envia_email_y_vuelve_con_popup(self, send_mail):
        r = self.client.post(self.url, {'estado': 'CONFIRMADA', 'next': self.lista + '&agregar_calendario=999'})
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'CONFIRMADA')
        self.assertEqual(send_mail.call_count, 1)
        self.assertRedirects(
            r, reverse('panel:reservas') + f'?estado=PENDIENTE&page=1&agregar_calendario={self.reserva.pk}',
            fetch_redirect_response=False,
        )
        r = self.client.get(reverse('panel:reservas') + f'?agregar_calendario={self.reserva.pk}')
        self.assertContains(r, '¿Quieres agregar esta reserva confirmada a Google Calendar?')
        self.assertContains(r, f'Reserva {self.reserva.codigo}: Confirmada.')

    @patch('tours.signals.send_mail')
    def test_cancelar_vuelve_sin_popup(self, send_mail):
        r = self.client.post(self.url, {'estado': 'CANCELADA', 'next': self.lista + '&agregar_calendario=999'})
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'CANCELADA')
        self.assertRedirects(r, self.lista, fetch_redirect_response=False)
        self.assertNotContains(self.client.get(self.lista), 'popup-calendario')

    @patch('tours.signals.send_mail')
    def test_estado_invalido_o_igual_no_hace_nada(self, send_mail):
        for estado in ('NO-EXISTE', 'PENDIENTE'):
            r = self.client.post(self.url, {'estado': estado, 'next': self.lista})
            self.assertRedirects(r, self.lista, fetch_redirect_response=False)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, 'PENDIENTE')
        send_mail.assert_not_called()

    @patch('tours.signals.send_mail', side_effect=Exception('Mailgun 403'))
    def test_falla_del_email_avisa(self, send_mail):
        with self.assertLogs('tours.signals', 'ERROR'):
            r = self.client.post(self.url, {'estado': 'CONFIRMADA', 'next': self.lista}, follow=True)
        self.assertContains(r, 'no se pudo enviar el email')

    def test_next_externo_vuelve_a_la_lista(self):
        r = self.client.post(self.url, {'estado': 'PENDIENTE', 'next': 'https://malo.com/'})
        self.assertRedirects(r, reverse('panel:reservas'), fetch_redirect_response=False)

    def test_tabla_muestra_select_de_estado(self):
        r = self.client.get(reverse('panel:reservas'))
        self.assertContains(r, f'action="{self.url}"')
        self.assertContains(r, 'class="estado-reserva b-PENDIENTE"')
