from __future__ import annotations

from django.conf import settings
from django.db import models

from django.db import models
from django.utils import timezone

class Payment(models.Model):
    # --- Constantes de Proveedor y Estado ---
    PROVIDER_FLOW = "flow"

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELED, "Canceled"),
    )

    # --- Campos Principales ---
    provider = models.CharField(max_length=20, default=PROVIDER_FLOW)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # Cambiamos CASCADE por PROTECT para que no se borren los pagos si se borra el tour
    tour = models.ForeignKey(
        'tours.Tour', 
        on_delete=models.PROTECT, 
        related_name='pagos'
    )

    amount = models.PositiveIntegerField(help_text="Amount in minor units (e.g. CLP pesos).")
    currency = models.CharField(max_length=10, default="CLP")

    # --- Datos del Proveedor ---
    provider_token = models.CharField(max_length=120, blank=True, null=True)
    provider_order_id = models.CharField(max_length=120, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # --- Logs y Auditoría JSON ---
    raw_create_response = models.JSONField(blank=True, null=True)
    raw_confirm_payload = models.JSONField(blank=True, null=True)
    raw_status_response = models.JSONField(blank=True, null=True)

    # --- Control de Tiempos y Borrado Lógico ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Fecha de borrado lógico")

    class Meta:
        indexes = [
            models.Index(fields=["provider", "provider_token"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["status"]),
        ]

    # --- Métodos de Borrado Lógico ---
    def delete(self, *args, **kwargs):
        """Sobrescribe el borrado físico por uno lógico"""
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, *args, **kwargs):
        """Método auxiliar por si alguna vez necesitas borrar de verdad"""
        super(Payment, self).delete(*args, **kwargs)

    @property
    def is_active(self):
        """Indica si el registro no ha sido borrado"""
        return self.deleted_at is None

    def __str__(self):
        return f"Payment {self.id} - {self.status} ({self.amount} {self.currency})"