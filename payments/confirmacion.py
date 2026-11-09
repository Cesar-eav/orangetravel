"""Aplicar a un Payment el estado que informa Flow (payment/getStatus).

Lo usan las tres vías que pueden enterarse de un pago: el webhook (flow-confirm),
la vuelta del cliente (flow-return) y el comando `conciliar_pagos_flow` (cron). Pueden
llegar casi a la vez, así que el paso a pagado es un UPDATE condicional: solo la vía
que lo gana envía los emails, y nunca salen dos veces.
"""
from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from .models import Payment

logger = logging.getLogger(__name__)

FLOW_PAGADO = 2
FLOW_RECHAZADO = 3
FLOW_ANULADO = 4


def estado_flow(status_data: dict[str, Any] | None) -> int | None:
    """Código numérico de Flow (1 pendiente, 2 pagado, 3 rechazado, 4 anulado) o None."""
    valor = (status_data or {}).get("status")
    if str(valor).strip().lower() == "paid":
        return FLOW_PAGADO
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def aplicar_estado_flow(payment: Payment, status_data: dict[str, Any], *, enviar_emails: bool = True) -> str:
    """Actualiza el pago según Flow. Devuelve 'pagado', 'ya_pagado', 'fallido' o 'pendiente'."""
    estado = estado_flow(status_data)

    if estado == FLOW_PAGADO:
        ganado = Payment.objects.filter(pk=payment.pk, paid_at__isnull=True).update(
            status=Payment.STATUS_PAID, paid_at=timezone.now(),
            raw_status_response=status_data, updated_at=timezone.now(),
        )
        payment.refresh_from_db()
        if not ganado:
            return "ya_pagado"
        logger.info("Pago %s (%s) confirmado por Flow", payment.id, payment.codigo)
        if enviar_emails:
            from .emails import enviar_confirmacion_pago
            enviar_confirmacion_pago(payment)
        return "pagado"

    if estado in (FLOW_RECHAZADO, FLOW_ANULADO):
        nuevo = Payment.STATUS_FAILED if estado == FLOW_RECHAZADO else Payment.STATUS_CANCELED
        Payment.objects.filter(pk=payment.pk, status=Payment.STATUS_PENDING).update(
            status=nuevo, raw_status_response=status_data, updated_at=timezone.now(),
        )
        payment.refresh_from_db()
        return "fallido"

    return "pendiente"
