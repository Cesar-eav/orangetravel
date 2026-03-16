from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Reserva

@receiver(pre_save, sender=Reserva)
def notificar_cambio_estado(sender, instance, **kwargs):
    # Si la reserva es nueva, no hacemos nada (el mail inicial ya lo envía la View)
    if not instance.pk:
        return

    try:
        # Obtenemos cómo estaba la reserva antes de guardar los cambios
        reserva_previa = Reserva.objects.get(pk=instance.pk)
    except Reserva.DoesNotExist:
        return

    # Si el estado cambió a CONFIRMADA
    if reserva_previa.estado != instance.estado and instance.estado == Reserva.Estado.CONFIRMADA:
        asunto = f"✅ ¡Reserva Confirmada! - Orange Travel"
        mensaje = (
            f"¡Hola {instance.nombre_cliente}!\n\n"
            f"Tu reserva para el tour '{instance.tour.nombre}' el día {instance.fecha} ha sido CONFIRMADA.\n"
            f"Prepárate para una gran experiencia en Arica.\n\n"
            f"Detalles:\n- Pasajeros: {instance.adultos} Adl / {instance.ninos} Chd\n- Total: ${instance.precio_total}"
        )
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [instance.email_cliente])

    # Si el estado cambió a RECHAZADA o CANCELADA
    elif reserva_previa.estado != instance.estado and instance.estado == Reserva.Estado.RECHAZADA:
        asunto = f"⚠️ Actualización de tu reserva - Orange Travel"
        mensaje = f"Hola {instance.nombre_cliente}, lamentamos informarte que no tenemos disponibilidad para el tour '{instance.tour.nombre}' en la fecha solicitada."
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [instance.email_cliente])