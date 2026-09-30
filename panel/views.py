from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import LoginView, redirect_to_login
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from payments.emails import (
    send_payment_confirmation_to_admins,
    send_payment_confirmation_to_customer,
)
from payments.models import Payment
from django.db import transaction
from django.db.models import ProtectedError
from tours.models import BloqueoTour, GaleriaTour, PrecioTour, Reserva, TipoTour, Tour

from .forms import (
    BloqueoForm, ImagenGaleriaForm, PanelLoginForm, PrecioTourForm,
    ReservaGestionForm, TipoTourForm, TourForm,
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


class DashboardView(PanelView, TemplateView):
    template_name = 'panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        pagos_ok = Payment.objects.filter(status=Payment.STATUS_PAID, deleted_at__isnull=True)
        ctx.update(
            pendientes=Reserva.objects.filter(estado=Reserva.Estado.PENDIENTE, fecha__gte=hoy).count(),
            proximas=Reserva.objects.filter(estado=Reserva.Estado.CONFIRMADA, fecha__gte=hoy).count(),
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
        messages.success(self.request, 'Reserva actualizada.')
        return response


@_staff_only
@require_POST
def reserva_eliminar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    reserva.delete()  # borrado lógico
    messages.success(request, f'Reserva {reserva.codigo} eliminada.')
    return redirect('panel:reservas')


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


# ---------------------------------------------------------------- Tours

class TourListView(PanelView, ListView):
    template_name = 'panel/tours_list.html'
    context_object_name = 'tours'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = Tour.objects.select_related('tipo', 'precio').order_by('nombre')
        if q := self.request.GET.get('q', '').strip():
            qs = qs.filter(nombre__icontains=q)
        return qs


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
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if 'form' not in ctx:
            ctx['form'], ctx['precio_form'] = self._forms()
        ctx['tour'] = self.tour
        ctx['imagenes'] = self.tour.imagenes.all() if self.tour else []
        return ctx

    def post(self, request, *args, **kwargs):
        form, precio_form = self._forms(request.POST, request.FILES)
        imagenes = request.FILES.getlist('galeria')
        galeria_forms = [ImagenGaleriaForm(files={'imagen': f}) for f in imagenes]
        if form.is_valid() and precio_form.is_valid() and all(g.is_valid() for g in galeria_forms):
            with transaction.atomic():
                tour = form.save()
                precio = precio_form.save(commit=False)
                precio.tour = tour
                precio.save()
                for g in galeria_forms:
                    GaleriaTour.objects.create(tour=tour, imagen=g.cleaned_data['imagen'])
            messages.success(request, f'Tour «{tour.nombre}» guardado.')
            return redirect('panel:tour_editar', pk=tour.pk)
        if not all(g.is_valid() for g in galeria_forms):
            messages.error(request, 'Alguna imagen de la galería no es válida.')
        return self.render_to_response(
            self.get_context_data(form=form, precio_form=precio_form)
        )


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
