from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
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
from tours.models import Reserva, Tour

from .forms import ReservaGestionForm
from .mixins import StaffRequiredMixin

PAGE_SIZE = 25
LOGIN_URL = reverse_lazy('panel:login')

ESTADO_PAGO = {
    Payment.STATUS_PENDING: 'Pendiente',
    Payment.STATUS_PAID: 'Pagado',
    Payment.STATUS_FAILED: 'Fallido',
    Payment.STATUS_CANCELED: 'Cancelado',
}


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
