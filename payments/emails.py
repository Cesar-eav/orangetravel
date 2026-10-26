from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from .models import Payment
from tours.traduccion import texto
from tours.views import EMAIL_POR_TOUR, EMAIL_ADMIN_DEFAULT, CC_RESERVAS


def get_email_admin_pago(payment):
    # nombre_es y no nombre: con el inglés activo, nombre devuelve la traducción.
    nombre = payment.tour.nombre_es.lower()
    for keyword, email in EMAIL_POR_TOUR.items():
        if keyword in nombre:
            return email
    return EMAIL_ADMIN_DEFAULT


def send_download_purchase_confirmation_email(*, payment: Payment) -> bool:
    user = getattr(payment, "user", None)
    media = getattr(payment, "media", None)

    to_email = getattr(user, "email", "") or ""
    if not to_email:
        return False

    portal_name = getattr(settings, "PORTAL_NAME", "RodeoVMS")

    media_url = ""
    try:
        ssl_frontend_host = getattr(settings, "SSL_FRONTEND_HOST", "") or ""
        if media and ssl_frontend_host:
            media_url = ssl_frontend_host.rstrip("/") + media.get_absolute_url()
    except Exception:  # noqa: BLE001
        media_url = ""

    title = f"[{portal_name}] - Compra confirmada"

    amount = getattr(payment, "amount", None)
    currency = getattr(payment, "currency", "") or ""

    msg_lines: list[str] = [
        "Tu compra fue confirmada exitosamente.",
        "",
    ]

    if media:
        msg_lines.append(f"Contenido: {media.title}")
    if amount is not None:
        msg_lines.append(f"Monto: {amount} {currency}".strip())
    if media_url:
        msg_lines.extend(
            [
                "",
                "Tu compra ya está confirmada y la descarga quedó habilitada. Ingresa al enlace del video y haz clic en el botón DESCARGAR para elegir una de las calidades disponibles.",
                "",
                f"Puedes volver al video aquí: {media_url}",
            ]
        )
    else:
        msg_lines.extend(
            [
                "",
                "Tu compra ya está confirmada y la descarga quedó habilitada. Entra al video y haz clic en el botón DESCARGAR para elegir una de las calidades disponibles.",
            ]
        )

    msg_lines.append("Gracias por tu compra.")

    email = EmailMessage(title, "\n".join(msg_lines), settings.DEFAULT_FROM_EMAIL, [to_email])
    email.send(fail_silently=True)
    return True


def send_download_purchase_problem_email(*, payment: Payment, problem: str) -> bool:
    user = getattr(payment, "user", None)
    media = getattr(payment, "media", None)

    to_email = getattr(user, "email", "") or ""
    if not to_email:
        return False

    portal_name = getattr(settings, "PORTAL_NAME", "MediaVMS")
    title = f"[{portal_name}] - Problema con tu compra"

    media_url = ""
    try:
        ssl_frontend_host = getattr(settings, "SSL_FRONTEND_HOST", "") or ""
        if media and ssl_frontend_host:
            media_url = ssl_frontend_host.rstrip("/") + media.get_absolute_url()
    except Exception:  # noqa: BLE001
        media_url = ""

    msg_lines: list[str] = [
        "Detectamos un problema al procesar tu compra.",
        "",
        f"Detalle: {problem}",
    ]

    if media:
        msg_lines.extend(["", f"Contenido: {media.title}"])
    if media_url:
        msg_lines.extend(["", f"Link: {media_url}"])

    msg_lines.extend(
        [
            "",
            "Si el cobro se realizó pero no se habilitó la descarga, responde este correo o contáctanos para validarlo.",
        ]
    )

    email = EmailMessage(title, "\n".join(msg_lines), settings.DEFAULT_FROM_EMAIL, [to_email])
    email.send(fail_silently=True)
    return True


def send_payment_integration_error_to_admins(*, payment: Payment, error: str) -> bool:
    admin_list = list(getattr(settings, "ADMIN_EMAIL_LIST", []) or [])
    if not admin_list:
        return False

    portal_name = getattr(settings, "PORTAL_NAME", "MediaVMS")
    title = f"[{portal_name}] - Error integración Flow (payment_id={payment.id})"

    msg = "\n".join(
        [
            "Hubo un error consultando el estado del pago en Flow.",
            "",
            f"payment_id: {payment.id}",
            f"status local: {payment.status}",
            f"provider_token: {payment.provider_token}",
            "",
            f"error: {error}",
        ]
    )

    email = EmailMessage(title, msg, settings.DEFAULT_FROM_EMAIL, admin_list)
    email.send(fail_silently=True)
    return True

def _pax_detalle(payment) -> str:
    pax_detalle = _("%(n)s Adultos") % {'n': payment.pax_adults}
    if payment.pax_children > 0:
        pax_detalle += _(" / %(n)s Niños") % {'n': payment.pax_children}
    return pax_detalle


def _fecha_cl(payment) -> str:
    fecha = payment.reservation_date
    return fecha.strftime("%d-%m-%Y") if fecha else "-"


def _contexto_pago(payment) -> dict:
    return {
        'payment': payment,
        'pax_detalle': _pax_detalle(payment),
        'fecha': _fecha_cl(payment),
        'monto': f"{payment.amount:,}",
    }


def _html_cliente_pago(payment) -> str:
    ctx = _contexto_pago(payment)
    ctx['tour_nombre'] = texto(payment.tour, 'nombre', payment.idioma)
    return render_to_string('emails/pago_cliente.html', ctx)


def _html_admin_pago(payment) -> str:
    ctx = _contexto_pago(payment)
    ctx['tel_limpio'] = payment.customer_phone.replace('+', '').replace(' ', '')
    return render_to_string('emails/pago_admin.html', ctx)


def send_payment_confirmation_to_customer(payment: Payment) -> None:
    """Envía solo el correo de confirmación de pago al cliente, en su idioma. Propaga excepciones."""
    with translation.override(payment.idioma):
        html_cliente = _html_cliente_pago(payment)
        asunto = _("✅ Reserva Confirmada: %(tour)s") % {'tour': texto(payment.tour, 'nombre', payment.idioma)}
        cuerpo = _("Tu pago ha sido confirmado.")
    msg_cli = EmailMultiAlternatives(
        subject=asunto,
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[payment.customer_email],
    )
    msg_cli.attach_alternative(html_cliente, "text/html")
    msg_cli.send()


def send_payment_confirmation_to_admins(payment: Payment) -> None:
    """Envía solo el correo de notificación de pago a los administradores. Propaga excepciones."""
    with translation.override('es'):
        html_admin = _html_admin_pago(payment)
    email_admin = get_email_admin_pago(payment)
    cc_admin = [email for email in CC_RESERVAS if email != email_admin]
    msg_adm = EmailMultiAlternatives(
        subject=f"🚨 PAGO RECIBIDO - {payment.customer_name}",
        body="Nueva venta realizada.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email_admin],
        cc=cc_admin,
    )
    msg_adm.attach_alternative(html_admin, "text/html")
    msg_adm.send()


def enviar_confirmacion_pago(payment):
    print(f"DEBUG: 🍊 Iniciando envío vía Anymail (Mailgun API) para Pago #{payment.id}...")
    try:
        send_payment_confirmation_to_customer(payment)
        print("DEBUG: ✅ Anymail: Correo cliente enviado.")

        email_admin = get_email_admin_pago(payment)
        print(f"DEBUG: 📧 Notificación pago → {email_admin} (tour: {payment.tour.nombre_es})")
        send_payment_confirmation_to_admins(payment)
        print("DEBUG: ✅ Anymail: Correo admin enviado.")

    except Exception as e:
        print(f"❌ ERROR CON ANYMAIL/MAILGUN: {e}")
