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
