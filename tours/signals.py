from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from .models import Reserva
from .traduccion import texto
from payments.models import Payment

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
        with translation.override(instance.idioma):
            asunto = _("✅ ¡Reserva Confirmada! - Orange Travel")
            mensaje = _(
                "¡Hola %(nombre)s!\n\n"
                "Tu reserva para el tour '%(tour)s' el día %(fecha)s ha sido CONFIRMADA.\n"
                "Prepárate para una gran experiencia en Arica.\n\n"
                "Detalles:\n- Pasajeros: %(adultos)s Adl / %(ninos)s Chd\n- Total: $%(total)s"
            ) % {
                'nombre': instance.nombre_cliente, 'tour': texto(instance.tour, 'nombre', instance.idioma),
                'fecha': instance.fecha, 'adultos': instance.adultos, 'ninos': instance.ninos,
                'total': instance.precio_total,
            }
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [instance.email_cliente])

    # Si el estado cambió a RECHAZADA o CANCELADA
    elif reserva_previa.estado != instance.estado and instance.estado in (Reserva.Estado.RECHAZADA, Reserva.Estado.CANCELADA):
        with translation.override(instance.idioma):
            asunto = _("⚠️ Actualización de tu reserva - Orange Travel")
            mensaje = _(
                "Hola %(nombre)s, lamentamos informarte que no tenemos disponibilidad para el tour '%(tour)s' en la fecha solicitada."
            ) % {'nombre': instance.nombre_cliente, 'tour': texto(instance.tour, 'nombre', instance.idioma)}
        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [instance.email_cliente])

        # Liberar la fecha: cancelar el Payment asociado para que salga del calendario
        Payment.objects.filter(
            tour=instance.tour,
            reservation_date=instance.fecha,
            customer_email=instance.email_cliente,
            status=Payment.STATUS_PAID,
        ).update(status=Payment.STATUS_CANCELED)