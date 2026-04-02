from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # 1. Qué columnas se ven en la lista principal
    list_display = (
        "id",
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
        "provider_token",
        "provider_order_id",
        "tour__nombre", # Asumiendo que tu modelo Tour tiene un campo 'nombre'
    )

    ordering = ("-created_at",)
    
    # Usamos raw_id_fields para el tour por si llegas a tener miles de tours
    raw_id_fields = ("tour",)

    # 4. Campos que no se pueden editar manualmente (auditoría pura)
    readonly_fields = (
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
    )

    # 5. Organización visual del formulario
    fieldsets = (
        (
            "Información de la Reserva",
            {
                "fields": (
                    "tour",
                    "status",
                    "amount",
                    "currency",
                    "paid_at",
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