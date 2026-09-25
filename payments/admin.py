from django.contrib import admin, messages
from .models import Payment
from .emails import send_payment_confirmation_to_customer, send_payment_confirmation_to_admins

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # 1. Qué columnas se ven en la lista principal
    list_display = (
        "id",
        "codigo",
        "tour",
        "amount",
        "currency",
        "status",
        "paid_at",
        "created_at",
        "is_deleted_display", # Un indicador visual para el borrado lógico
    )

    # 2. Filtros laterales para encontrar pagos rápido
    list_filter = ("status", "currency", "created_at", "paid_at", "deleted_at")

    # 3. Buscador (ajustado a campos que sí existen)
    search_fields = (
        "id",
        "codigo",
        "provider_token",
        "provider_order_id",
        "tour__nombre", # Asumiendo que tu modelo Tour tiene un campo 'nombre'
        "customer_email",
    )

    ordering = ("-created_at",)

    # Usamos raw_id_fields para el tour por si llegas a tener miles de tours
    raw_id_fields = ("tour",)

    actions = ["reenviar_notificacion_cliente", "reenviar_notificacion_admin"]

    # 4. Campos que no se pueden editar manualmente (auditoría pura)
    readonly_fields = (
        "codigo",
        "provider",
        "status",
        "tour",
        "amount",
        "currency",
        "provider_token",
        "provider_order_id",
        "paid_at",
        "raw_create_response",
        "raw_confirm_payload",
        "raw_status_response",
        "created_at",
        "updated_at",
        "deleted_at",
        "customer_name",
        "customer_email",
        "customer_phone",
        "reservation_date",
        "pax_adults",
        "pax_children",
    )

    # 5. Organización visual del formulario
    fieldsets = (
        (
            "Información de la Reserva",
            {
                "fields": (
                    "codigo",
                    "tour",
                    "status",
                    "amount",
                    "currency",
                    "paid_at",
                )
            },
        ),
        (
            "Datos del Cliente",
            {
                "fields": (
                    "customer_name",
                    "customer_email",
                    "customer_phone",
                    "reservation_date",
                    "pax_adults",
                    "pax_children",
                )
            },
        ),
        (
            "Detalles de Flow (Proveedor)",
            {
                "fields": (
                    "provider",
                    "provider_token",
                    "provider_order_id",
                )
            },
        ),
        (
            "Logs Técnicos (JSON)",
            {
                "classes": ("collapse",), # Esto hace que esta sección esté contraída por defecto
                "fields": (
                    "raw_create_response",
                    "raw_confirm_payload",
                    "raw_status_response",
                )
            },
        ),
        (
            "Tiempos y Borrado Lógico",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "deleted_at",
                )
            },
        ),
    )

    # Método para mostrar un icono de "borrado" en la lista
    @admin.display(boolean=True, description="¿Borrado?")
    def is_deleted_display(self, obj):
        return obj.deleted_at is not None

    def reenviar_notificacion_cliente(self, request, queryset):
        enviados = 0
        no_pagados = 0
        sin_email = 0
        errores = 0
        for payment in queryset:
            if payment.status != Payment.STATUS_PAID:
                no_pagados += 1
                continue
            if not payment.customer_email:
                sin_email += 1
                continue
            try:
                send_payment_confirmation_to_customer(payment)
                enviados += 1
            except Exception as e:
                errores += 1
                self.message_user(
                    request,
                    f"Error al reenviar al cliente (pago #{payment.id}): {e}",
                    level=messages.ERROR,
                )
        self.message_user(
            request,
            f"Reenvío al cliente: {enviados} enviados, {no_pagados} omitidos (no pagados), "
            f"{sin_email} omitidos (sin email), {errores} con error.",
        )
    reenviar_notificacion_cliente.short_description = "Reenviar notificación al cliente"

    def reenviar_notificacion_admin(self, request, queryset):
        enviados = 0
        no_pagados = 0
        errores = 0
        for payment in queryset:
            if payment.status != Payment.STATUS_PAID:
                no_pagados += 1
                continue
            try:
                send_payment_confirmation_to_admins(payment)
                enviados += 1
            except Exception as e:
                errores += 1
                self.message_user(
                    request,
                    f"Error al reenviar a administradores (pago #{payment.id}): {e}",
                    level=messages.ERROR,
                )
        self.message_user(
            request,
            f"Reenvío a administradores: {enviados} enviados, {no_pagados} omitidos (no pagados), "
            f"{errores} con error.",
        )
    reenviar_notificacion_admin.short_description = "Reenviar notificación a administradores"