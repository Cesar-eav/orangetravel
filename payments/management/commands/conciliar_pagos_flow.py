"""Pregunta a Flow por los pagos pendientes recientes y los confirma.

Respaldo del webhook (flow-confirm): si Flow no logra avisar, o el cliente no vuelve
al sitio después de pagar, el pago quedaría en pending para siempre (sin emails ni
bloqueo de la fecha en el calendario). Pensado para un cron de cPanel cada 10 minutos:

    cd ~/orangetravel && ~/virtualenv/orangetravel/3.11/bin/python manage.py conciliar_pagos_flow

Usa la misma lógica que el webhook (payments/confirmacion.py): un pago nunca envía
emails dos veces aunque el webhook, el retorno y este comando coincidan.
"""
import sys
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.confirmacion import aplicar_estado_flow, estado_flow
from payments.flow import FlowClient
from payments.models import Payment


class Command(BaseCommand):
    help = "Confirma con Flow los pagos pendientes recientes (respaldo del webhook)."

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=3,
                            help='Revisar pagos pendientes creados en los últimos N días (por defecto 3).')
        parser.add_argument('--simular', action='store_true',
                            help='Solo muestra lo que diría Flow; no cambia nada ni envía emails.')
        parser.add_argument('--sin-emails', action='store_true',
                            help='Actualiza los estados pero no envía emails (para pagos antiguos).')

    def handle(self, *args, dias, simular, sin_emails, **options):
        # Como en passenger_wsgi.py: en cron stdout puede ser ASCII y Flow responde con tildes.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='backslashreplace')
            except Exception:  # noqa: BLE001
                pass

        flow = FlowClient()
        if not flow.is_configured():
            self.stderr.write("Flow no está configurado (FLOW_API_KEY / FLOW_SECRET_KEY).")
            return

        desde = timezone.now() - timedelta(days=dias)
        pendientes = (Payment.objects
                      .filter(status=Payment.STATUS_PENDING, deleted_at__isnull=True,
                              created_at__gte=desde)
                      .exclude(provider_token__isnull=True).exclude(provider_token='')
                      .order_by('id'))

        resumen: dict[str, int] = {}
        for pago in pendientes:
            try:
                status_data = flow.get_status(token=pago.provider_token)
            except Exception as exc:  # noqa: BLE001 — un pago con error no frena al resto
                resultado = 'error'
                detalle = str(exc)
            else:
                estado = estado_flow(status_data)
                if estado is None:
                    # Flow responde {code, message} si no reconoce el token (p. ej. uno de sandbox).
                    resultado, detalle = 'error', status_data.get('message') or str(status_data)
                elif simular:
                    resultado, detalle = f'flow_status={estado}', 'simulado'
                else:
                    resultado = aplicar_estado_flow(pago, status_data, enviar_emails=not sin_emails)
                    detalle = f'flow_status={estado}'
            resumen[resultado] = resumen.get(resultado, 0) + 1
            if resultado != 'pendiente':
                self.stdout.write(f"Pago {pago.id} {pago.codigo} ({pago.customer_email}): {resultado} [{detalle}]")

        total = sum(resumen.values())
        partes = ', '.join(f'{k}: {v}' for k, v in sorted(resumen.items())) or 'nada que revisar'
        # Con hora: en conciliar.log cada corrida queda fechada (historial del cron).
        ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M')
        self.stdout.write(f"[{ahora}] {total} pagos pendientes revisados ({partes}).")
