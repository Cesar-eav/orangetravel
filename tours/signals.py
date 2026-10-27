import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Reserva
from payments.models import Payment

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Reserva)
def recordar_estado_previo(sender, instance, **kwargs):
    # Guardamos cómo estaba la reserva para comparar en post_save
    # (si es nueva no hay estado previo: el mail inicial ya lo envía la View)
    instance._estado_previo = (
        Reserva.all_objects.filter(pk=instance.pk).values_list('estado', flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=Reserva)
def notificar_cambio_estado(sender, instance, created, **kwargs):
    # El correo sale después de guardar: si Mailgun falla, la reserva ya quedó con su nuevo estado.
    # La vista del panel revisa instance.email_estado_fallido para avisar al staff.
    instance.email_estado_fallido = False
    previo = getattr(instance, '_estado_previo', None)
    if created or previo is None or previo == instance.estado:
        return

    # Si el estado cambió a CONFIRMADA
    if instance.estado == Reserva.Estado.CONFIRMADA:
        asunto = f"✅ ¡Reserva Confirmada! - Orange Travel"
        mensaje = (
            f"¡Hola {instance.nombre_cliente}!\n\n"
            f"Tu reserva para el tour '{instance.tour.nombre}' el día {instance.fecha} ha sido CONFIRMADA.\n"
            f"Prepárate para una gran experiencia en Arica.\n\n"
            f"Detalles:\n- Pasajeros: {instance.adultos} Adl / {instance.ninos} Chd\n- Total: ${instance.precio_total}"
        )

    # Si el estado cambió a RECHAZADA o CANCELADA
    elif instance.estado in (Reserva.Estado.RECHAZADA, Reserva.Estado.CANCELADA):
        asunto = f"⚠️ Actualización de tu reserva - Orange Travel"
        mensaje = f"Hola {instance.nombre_cliente}, lamentamos informarte que no tenemos disponibilidad para el tour '{instance.tour.nombre}' en la fecha solicitada."

        # Liberar la fecha: cancelar el Payment asociado para que salga del calendario
        Payment.objects.filter(
            tour=instance.tour,
            reservation_date=instance.fecha,
            customer_email=instance.email_cliente,
            status=Payment.STATUS_PAID,
        ).update(status=Payment.STATUS_CANCELED)
    else:
        return

    try:
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [instance.email_cliente])
    except Exception:
        logger.exception("No se pudo enviar el email de cambio de estado de la reserva %s", instance.codigo)
        instance.email_estado_fallido = True
