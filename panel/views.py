import re
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import LoginView, redirect_to_login
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from payments.emails import (
    send_payment_confirmation_to_admins,
    send_payment_confirmation_to_customer,
)
from blog.models import ImagenCarousel, Post
from home.models import MaintenanceMode, Nosotros
from payments.models import Payment
from django.db import transaction
from django.db.models import ProtectedError
from tours.models import TIPO_CON_PRECIO_ID, BloqueoTour, Cotizacion, GaleriaTour, PrecioTour, Reserva, TerceraEdad, TipoTour, Tour, Venta, Zona

from .forms import (
    CUERPO_MAX, BloqueoForm, CotizacionGestionForm, ImagenGaleriaForm, ItinerarioDiaFormSet, ImagenPostFormSet, MantencionForm, NosotrosForm,
    PanelLoginForm, PostForm, TerceraEdadForm,
    PrecioTourForm, ReservaGestionForm, TipoTourForm, TourForm, VentaForm, ZonaForm,
)
from .mixins import StaffRequiredMixin

PAGE_SIZE = 25
LOGIN_URL = reverse_lazy('panel:login')

ESTADO_PAGO = {
    Payment.STATUS_PENDING: 'Pendiente',
    Payment.STATUS_PAID: 'Pagado',
    Payment.STATUS_FAILED: 'Fallido',
    Payment.STATUS_CANCELED: 'Cancelado',
}


class PanelLoginView(LoginView):
    template_name = 'panel/login.html'
    authentication_form = PanelLoginForm

    def get_default_redirect_url(self):
        return reverse('panel:dashboard')


class PanelView(StaffRequiredMixin):
    login_url = LOGIN_URL


def _staff_only(view):
    """Decorador para vistas de función (POST): staff o redirige al login."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), str(LOGIN_URL))
        if not request.user.is_staff:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def ventas_confirmadas_proximas():
    """Ventas manuales confirmadas con servicio desde hoy; cuentan como «Confirmadas próximas»."""
    return Venta.objects.filter(
        estado_reserva=Venta.EstadoReserva.CONFIRMADA, fecha_servicio__gte=timezone.localdate()
    )


class DashboardView(PanelView, TemplateView):
    template_name = 'panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        pagos_ok = Payment.objects.filter(status=Payment.STATUS_PAID, deleted_at__isnull=True)
        proximas_ventas = ventas_confirmadas_proximas().count()
        ctx.update(
            pendientes=Reserva.objects.filter(estado=Reserva.Estado.PENDIENTE, fecha__gte=hoy).count(),
            proximas=Reserva.objects.filter(estado=Reserva.Estado.CONFIRMADA, fecha__gte=hoy).count() + proximas_ventas,
            proximas_ventas=proximas_ventas,
            cotizaciones=Cotizacion.objects.filter(atendida=False).count(),
            pagos_semana=pagos_ok.filter(paid_at__gte=timezone.now() - timedelta(days=7)).count(),
            ultimas_reservas=Reserva.objects.select_related('tour').order_by('-creada_el')[:5],
            ultimos_pagos=pagos_ok.select_related('tour').order_by('-paid_at')[:5],
        )
        return ctx


class ReservaListView(PanelView, ListView):
    template_name = 'panel/reservas_list.html'
    context_object_name = 'reservas'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Reserva.objects.select_related('tour')
        g = self.request.GET
        if q := g.get('q', '').strip():
            qs = qs.filter(
                Q(codigo__icontains=q) | Q(nombre_cliente__icontains=q) | Q(email_cliente__icontains=q)
            )
        if g.get('estado') in Reserva.Estado.values:
            qs = qs.filter(estado=g['estado'])
        if g.get('tour', '').isdigit():
            qs = qs.filter(tour_id=g['tour'])
        if g.get('proximas'):
            qs = qs.filter(fecha__gte=timezone.localdate())
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx.update(
            estados=Reserva.Estado.choices,
            tours=Tour.objects.order_by('nombre'),
            querystring=params.urlencode(),
        )
        g = self.request.GET
        if g.get('estado') == Reserva.Estado.CONFIRMADA and g.get('proximas'):
            ventas = ventas_confirmadas_proximas().select_related('tour').order_by('fecha_servicio')
            if q := g.get('q', '').strip():
                ventas = ventas.filter(
                    Q(nombre_cliente__icontains=q) | Q(email__icontains=q) | Q(telefono__icontains=q)
                )
            if g.get('tour', '').isdigit():
                ventas = ventas.filter(tour_id=g['tour'])
            ctx['ventas_proximas'] = ventas
        return ctx


class ReservaDetailView(PanelView, UpdateView):
    model = Reserva
    form_class = ReservaGestionForm
    template_name = 'panel/reserva_detail.html'
    context_object_name = 'reserva'

    def get_success_url(self):
        return reverse('panel:reserva_detalle', args=[self.object.pk])

    def form_valid(self, form):
        # save() normal: el signal de tours/signals.py envía el correo si cambia el estado
        response = super().form_valid(form)
        if getattr(self.object, 'email_estado_fallido', False):
            messages.error(
                self.request,
                f'Reserva guardada como {self.object.get_estado_display()}, pero no se pudo enviar el email '
                f'al cliente ({self.object.email_cliente}). Avísale por otro medio.',
            )
        else:
            messages.success(self.request, 'Reserva actualizada.')
        return response


@_staff_only
@require_POST
def reserva_eliminar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    reserva.delete()  # borrado lógico
    messages.success(request, f'Reserva {reserva.codigo} eliminada.')
    return redirect('panel:reservas')


class CotizacionListView(PanelView, ListView):
    template_name = 'panel/cotizaciones_list.html'
    context_object_name = 'cotizaciones'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Cotizacion.objects.select_related('tour')
        g = self.request.GET
        if q := g.get('q', '').strip():
            qs = qs.filter(Q(nombre__icontains=q) | Q(email__icontains=q) | Q(telefono__icontains=q))
        if g.get('tour', '').isdigit():
            qs = qs.filter(tour_id=g['tour'])
        if g.get('pendientes'):
            qs = qs.filter(atendida=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx.update(
            tours=Tour.objects.exclude(tipo_id=TIPO_CON_PRECIO_ID).order_by('nombre'),
            querystring=params.urlencode(),
        )
        return ctx


class CotizacionDetailView(PanelView, UpdateView):
    model = Cotizacion
    form_class = CotizacionGestionForm
    template_name = 'panel/cotizacion_detail.html'
    context_object_name = 'cotizacion'

    def get_success_url(self):
        return reverse('panel:cotizacion_detalle', args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Cotización actualizada.')
        return response


class PagoListView(PanelView, ListView):
    template_name = 'panel/pagos_list.html'
    context_object_name = 'pagos'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Payment.objects.filter(deleted_at__isnull=True).select_related('tour').order_by('-created_at')
        g = self.request.GET
        if q := g.get('q', '').strip():
            qs = qs.filter(
                Q(codigo__icontains=q) | Q(customer_name__icontains=q) | Q(customer_email__icontains=q)
            )
        if g.get('status') in ESTADO_PAGO:
            qs = qs.filter(status=g['status'])
        if g.get('tour', '').isdigit():
            qs = qs.filter(tour_id=g['tour'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx.update(
            estados=ESTADO_PAGO.items(),
            tours=Tour.objects.order_by('nombre'),
            querystring=params.urlencode(),
        )
        return ctx


class PagoDetailView(PanelView, DetailView):
    template_name = 'panel/pago_detail.html'
    context_object_name = 'pago'
    queryset = Payment.objects.filter(deleted_at__isnull=True).select_related('tour')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estado_texto'] = ESTADO_PAGO.get(self.object.status, self.object.status)
        return ctx


# ---------------------------------------------------------------- Ventas

class VentaListView(PanelView, ListView):
    template_name = 'panel/ventas_list.html'
    context_object_name = 'ventas'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Venta.objects.select_related('tour')
        g = self.request.GET
        if q := g.get('q', '').strip():
            qs = qs.filter(
                Q(nombre_cliente__icontains=q) | Q(email__icontains=q) | Q(telefono__icontains=q)
                | Q(servicio__icontains=q)
            )
        filtros = (
            ('canal', Venta.Canal), ('tipo_servicio', Venta.TipoServicio),
            ('estado_pago', Venta.EstadoPago), ('estado_reserva', Venta.EstadoReserva),
        )
        for campo, choices in filtros:
            if g.get(campo) in choices.values:
                qs = qs.filter(**{campo: g[campo]})
        for param, lookup in (('desde', 'fecha_servicio__gte'), ('hasta', 'fecha_servicio__lte')):
            try:
                fecha = parse_date(g.get(param, ''))
            except ValueError:
                fecha = None
            if fecha:
                qs = qs.filter(**{lookup: fecha})
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        totales = self.object_list.aggregate(
            total=Sum('precio_total'), pagado=Sum('monto_pagado'),
            saldo=Sum(F('precio_total') - F('monto_pagado')),
        )
        ctx.update(
            canales=Venta.Canal.choices,
            tipos_servicio=Venta.TipoServicio.choices,
            estados_pago=Venta.EstadoPago.choices,
            estados_reserva=Venta.EstadoReserva.choices,
            totales=totales,
            querystring=params.urlencode(),
        )
        return ctx


class VentaFormView(PanelView, TemplateView):
    """Crear (sin pk) y editar (con pk) una venta ingresada a mano."""
    template_name = 'panel/venta_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = kwargs.get('pk')
        self.venta = get_object_or_404(Venta, pk=pk) if pk else None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('form', VentaForm(instance=self.venta))
        ctx['venta'] = self.venta
        return ctx

    def post(self, request, *args, **kwargs):
        form = VentaForm(request.POST, instance=self.venta)
        if form.is_valid():
            venta = form.save(commit=False)
            if venta.creada_por_id is None and not venta.pk:
                venta.creada_por = request.user
            venta.save()
            messages.success(request, f'Venta de {venta.nombre_cliente} guardada.')
            return redirect('panel:ventas')
        return self.render_to_response(self.get_context_data(form=form))


@_staff_only
@require_POST
def venta_eliminar(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    venta.delete()  # borrado lógico
    messages.success(request, f'Venta de {venta.nombre_cliente} eliminada.')
    return redirect('panel:ventas')


# ---------------------------------------------------------------- Tours

class TourListView(PanelView, ListView):
    template_name = 'panel/tours_list.html'
    context_object_name = 'tours'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Tour.objects.select_related('tipo', 'zona', 'precio').order_by('nombre')
        if q := self.request.GET.get('q', '').strip():
            qs = qs.filter(nombre__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipos'] = TipoTour.objects.order_by('nombre')
        ctx['zonas'] = Zona.objects.all()
        return ctx


@_staff_only
@require_POST
def tour_cambiar_tipo(request, pk):
    tour = get_object_or_404(Tour, pk=pk)
    tipo = get_object_or_404(TipoTour, pk=request.POST.get('tipo'))
    tour.tipo = tipo
    tour.save(update_fields=['tipo'])
    messages.success(request, f'«{tour.nombre}» ahora está en «{tipo.nombre}».')
    return _volver_a_tours(request)


@_staff_only
@require_POST
def tour_cambiar_zona(request, pk):
    tour = get_object_or_404(Tour, pk=pk)
    zona_id = request.POST.get('zona')
    tour.zona = get_object_or_404(Zona, pk=zona_id) if zona_id else None
    tour.save(update_fields=['zona'])
    if tour.zona:
        messages.success(request, f'«{tour.nombre}» ahora está en la zona «{tour.zona.nombre}».')
    else:
        messages.success(request, f'«{tour.nombre}» quedó sin zona.')
    return _volver_a_tours(request)


def _volver_a_tours(request):
    destino = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = reverse('panel:tours')
    return redirect(destino)


class TourFormView(PanelView, TemplateView):
    """Crear (sin pk) y editar (con pk) un tour junto a su precio y galería."""
    template_name = 'panel/tour_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = kwargs.get('pk')
        self.tour = get_object_or_404(Tour, pk=pk) if pk else None

    def _forms(self, data=None, files=None):
        precio = getattr(self.tour, 'precio', None) if self.tour else None
        return (
            TourForm(data, files, instance=self.tour, prefix='t'),
            PrecioTourForm(data, instance=precio, prefix='p'),
            ItinerarioDiaFormSet(data, instance=self.tour, prefix='d'),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if 'form' not in ctx:
            ctx['form'], ctx['precio_form'], ctx['dias_form'] = self._forms()
        ctx['tour'] = self.tour
        ctx['imagenes'] = self.tour.imagenes.all() if self.tour else []
        return ctx

    def post(self, request, *args, **kwargs):
        form, precio_form, dias_form = self._forms(request.POST, request.FILES)
        imagenes = request.FILES.getlist('galeria')
        galeria_forms = [ImagenGaleriaForm(files={'imagen': f}) for f in imagenes]
        # Se validan todos (sin cortocircuito) para poder mostrar todos los errores juntos.
        validos = [form.is_valid(), precio_form.is_valid(), dias_form.is_valid()]
        validos += [g.is_valid() for g in galeria_forms]
        if all(validos):
            with transaction.atomic():
                tour = form.save()
                precio = precio_form.save(commit=False)
                precio.tour = tour
                precio.save()
                dias_form.instance = tour
                for d in dias_form.save(commit=False):
                    d.tour = tour
                    d.save()
                for d in dias_form.deleted_objects:
                    d.delete()
                for n, d in enumerate(tour.dias.all(), 1):
                    if d.orden != n:
                        d.orden = n
                        d.save(update_fields=['orden'])
                for g in galeria_forms:
                    GaleriaTour.objects.create(tour=tour, imagen=g.cleaned_data['imagen'])
            messages.success(request, f'Tour «{tour.nombre}» guardado.')
            return redirect('panel:tour_editar', pk=tour.pk)
        if not all(g.is_valid() for g in galeria_forms):
            messages.error(request, 'Alguna imagen de la galería no es válida.')
        return self.render_to_response(
            self.get_context_data(
                form=form, precio_form=precio_form, dias_form=dias_form,
                errores=self._errores(form, precio_form, dias_form),
            )
        )

    @staticmethod
    def _errores(form, precio_form, dias_form):
        """Lista (etiqueta, mensaje, ancla) de todo lo que impidió guardar, para el aviso superior."""
        out = []
        for f, prefix in ((form, 't'), (precio_form, 'p')):
            for nombre, errs in f.errors.items():
                etiqueta = 'General' if nombre == '__all__' else f.fields[nombre].label or nombre
                ancla = f'id_{prefix}-{nombre}' if nombre != '__all__' else ''
                out.extend((etiqueta, e, ancla) for e in errs)
        n = 0
        for d in dias_form:
            if getattr(d, 'cleaned_data', {}).get('DELETE'):
                continue
            n += 1
            for nombre, errs in d.errors.items():
                etiqueta = f'Día {n}: {d.fields[nombre].label or nombre}'
                out.extend((etiqueta, e, 'dias') for e in errs)
        out.extend(('Itinerario por día', e, 'dias') for e in dias_form.non_form_errors())
        return out


@_staff_only
@require_POST
def galeria_eliminar(request, pk):
    img = get_object_or_404(GaleriaTour, pk=pk)
    tour_pk = img.tour_id
    img.delete()
    messages.success(request, 'Imagen eliminada.')
    return redirect('panel:tour_editar', pk=tour_pk)


# ------------------------------------------------------------ Categorías

class TipoListView(PanelView, ListView):
    template_name = 'panel/tipos_list.html'
    context_object_name = 'tipos'

    def get_queryset(self):
        return TipoTour.objects.order_by('nombre')


class TipoFormView(PanelView, TemplateView):
    template_name = 'panel/tipo_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = kwargs.get('pk')
        self.tipo = get_object_or_404(TipoTour, pk=pk) if pk else None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('form', TipoTourForm(instance=self.tipo))
        ctx['tipo'] = self.tipo
        return ctx

    def post(self, request, *args, **kwargs):
        form = TipoTourForm(request.POST, instance=self.tipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría guardada.')
            return redirect('panel:tipos')
        return self.render_to_response(self.get_context_data(form=form))


@_staff_only
@require_POST
def tipo_eliminar(request, pk):
    tipo = get_object_or_404(TipoTour, pk=pk)
    try:
        tipo.delete()
        messages.success(request, f'Categoría «{tipo.nombre}» eliminada.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar: hay tours en esta categoría.')
    return redirect('panel:tipos')


# ----------------------------------------------------------------- Zonas

class ZonaListView(PanelView, ListView):
    template_name = 'panel/zonas_list.html'
    context_object_name = 'zonas'

    def get_queryset(self):
        return Zona.objects.annotate(num_tours=Count('tours'))


class ZonaFormView(PanelView, TemplateView):
    template_name = 'panel/zona_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = kwargs.get('pk')
        self.zona = get_object_or_404(Zona, pk=pk) if pk else None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('form', ZonaForm(instance=self.zona))
        ctx['zona'] = self.zona
        return ctx

    def post(self, request, *args, **kwargs):
        form = ZonaForm(request.POST, request.FILES, instance=self.zona)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zona guardada.')
            return redirect('panel:zonas')
        return self.render_to_response(self.get_context_data(form=form))


@_staff_only
@require_POST
def zona_eliminar(request, pk):
    zona = get_object_or_404(Zona, pk=pk)
    try:
        zona.delete()
        messages.success(request, f'Zona «{zona.nombre}» eliminada.')
    except ProtectedError:
        messages.error(request, 'No se puede eliminar: hay tours en esta zona.')
    return redirect('panel:zonas')


# -------------------------------------------------------------- Bloqueos

class BloqueoListView(PanelView, TemplateView):
    template_name = 'panel/bloqueos.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = BloqueoTour.objects.select_related('tour').order_by('fecha')
        if self.request.GET.get('pasados') != '1':
            qs = qs.filter(fecha__gte=timezone.localdate())
        if self.request.GET.get('tour', '').isdigit():
            qs = qs.filter(tour_id=self.request.GET['tour'])
        ctx.update(
            bloqueos=qs,
            form=kwargs.get('form') or BloqueoForm(),
            tours=Tour.objects.order_by('nombre'),
        )
        return ctx

    def post(self, request, *args, **kwargs):
        form = BloqueoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fecha bloqueada.')
            return redirect('panel:bloqueos')
        return self.render_to_response(self.get_context_data(form=form))


@_staff_only
@require_POST
def bloqueo_eliminar(request, pk):
    get_object_or_404(BloqueoTour, pk=pk).delete()
    messages.success(request, 'Bloqueo eliminado.')
    return redirect('panel:bloqueos')


# ------------------------------------------------------------------ Blog

MAX_CARRUSEL = 20


def contar_bloques(contenido):
    """Mismo criterio que el admin: bloques que cierran (p, h1-6, ul, ol, blockquote, figure)."""
    return len(re.findall(r'</(?:p|h[1-6]|ul|ol|blockquote|figure)>', contenido or ''))


class PostListView(PanelView, ListView):
    template_name = 'panel/posts_list.html'
    context_object_name = 'posts'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Post.objects.select_related('autor')
        g = self.request.GET
        if q := g.get('q', '').strip():
            qs = qs.filter(Q(titulo__icontains=q) | Q(extracto__icontains=q))
        if g.get('publicado') in ('1', '0'):
            qs = qs.filter(publicado=g['publicado'] == '1')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['querystring'] = params.urlencode()
        return ctx


class PostFormView(PanelView, TemplateView):
    """Crear (sin pk) y editar (con pk) una reseña con sus imágenes."""
    template_name = 'panel/post_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = kwargs.get('pk')
        self.post_obj = get_object_or_404(Post, pk=pk) if pk else None

    def _forms(self, data=None, files=None):
        return (
            PostForm(data, files, instance=self.post_obj, prefix='b'),
            ImagenPostFormSet(data, files, instance=self.post_obj, prefix='ip'),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if 'form' not in ctx:
            ctx['form'], ctx['imagenes_form'] = self._forms()
        post = self.post_obj
        ctx.update(
            post=post,
            bloques=contar_bloques(post.contenido) if post else 0,
            carrusel=post.imagenes_carousel.all() if post else [],
            max_carrusel=MAX_CARRUSEL,
            extracto_max=Post._meta.get_field('extracto').max_length,
            cuerpo_max=CUERPO_MAX,
        )
        return ctx

    def post(self, request, *args, **kwargs):
        form, imagenes_form = self._forms(request.POST, request.FILES)
        carrusel_forms = [ImagenGaleriaForm(files={'imagen': f}) for f in request.FILES.getlist('carrusel')]
        carrusel_ok = all(c.is_valid() for c in carrusel_forms)
        actuales = self.post_obj.imagenes_carousel.count() if self.post_obj else 0
        if actuales + len(carrusel_forms) > MAX_CARRUSEL:
            carrusel_ok = False
            messages.error(request, f'El carrusel admite máximo {MAX_CARRUSEL} imágenes.')
        elif not carrusel_ok:
            messages.error(request, 'Alguna imagen del carrusel no es válida.')
        if form.is_valid() and imagenes_form.is_valid() and carrusel_ok:
            with transaction.atomic():
                post = form.save(commit=False)
                if post.autor_id is None:
                    post.autor = request.user
                post.save()
                imagenes_form.instance = post
                imagenes_form.save()
                for i, c in enumerate(carrusel_forms):
                    ImagenCarousel.objects.create(
                        post=post, imagen=c.cleaned_data['imagen'], orden=actuales + i,
                    )
            messages.success(request, f'Reseña «{post.titulo}» guardada.')
            return redirect('panel:post_editar', pk=post.pk)
        return self.render_to_response(
            self.get_context_data(form=form, imagenes_form=imagenes_form)
        )


@_staff_only
@require_POST
def carrusel_eliminar(request, pk):
    img = get_object_or_404(ImagenCarousel, pk=pk)
    post_pk = img.post_id
    img.delete()
    messages.success(request, 'Imagen eliminada del carrusel.')
    return redirect('panel:post_editar', pk=post_pk)


@_staff_only
@require_POST
def post_eliminar(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.delete()
    messages.success(request, f'Reseña «{post.titulo}» eliminada.')
    return redirect('panel:posts')


# ------------------------------------------------- Páginas y ajustes (singletons)

class SingletonFormView(PanelView, TemplateView):
    """Edita un modelo singleton (django-solo). Subclases definen model, form_class y textos."""
    template_name = 'panel/singleton_form.html'
    model = None
    form_class = None
    titulo = ''
    ayuda = ''
    url_name = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('form', self.form_class(instance=self.model.get_solo()))
        ctx.update(titulo=self.titulo, ayuda=self.ayuda)
        return ctx

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, instance=self.model.get_solo())
        if form.is_valid():
            form.save()
            messages.success(request, f'«{self.titulo}» guardado.')
            return redirect(self.url_name)
        return self.render_to_response(self.get_context_data(form=form))


class NosotrosView(SingletonFormView):
    model, form_class, url_name = Nosotros, NosotrosForm, 'panel:nosotros'
    titulo = 'Página Nosotros'


class TerceraEdadView(SingletonFormView):
    model, form_class, url_name = TerceraEdad, TerceraEdadForm, 'panel:tercera_edad'
    titulo = 'Página Tercera Edad'


class MantencionView(SingletonFormView):
    model, form_class, url_name = MaintenanceMode, MantencionForm, 'panel:mantencion'
    titulo = 'Modo mantención'
    ayuda = ('Si lo activas, los visitantes verán el mensaje con error 503. '
             'Los usuarios staff siguen viendo el sitio normal y el panel.')


@_staff_only
@require_POST
def pago_reenviar(request, pk, destino):
    pago = get_object_or_404(Payment, pk=pk, deleted_at__isnull=True)
    if pago.status != Payment.STATUS_PAID:
        messages.error(request, 'Solo se pueden reenviar correos de pagos pagados.')
    elif destino == 'cliente':
        if not pago.customer_email:
            messages.error(request, 'El pago no tiene email de cliente.')
        else:
            try:
                send_payment_confirmation_to_customer(pago)
                messages.success(request, 'Correo reenviado al cliente.')
            except Exception as e:
                messages.error(request, f'Error al reenviar al cliente: {e}')
    elif destino == 'admin':
        try:
            send_payment_confirmation_to_admins(pago)
            messages.success(request, 'Correo reenviado a administradores.')
        except Exception as e:
            messages.error(request, f'Error al reenviar a administradores: {e}')
    else:
        messages.error(request, 'Destino no válido.')
    return redirect('panel:pago_detalle', pk=pago.pk)
