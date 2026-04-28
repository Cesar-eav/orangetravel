from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives # Importante para enviar HTML


from .models import Payment


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

def enviar_confirmacion_pago(payment):
    print(f"DEBUG: 🍊 Iniciando envío vía Anymail (Mailgun API) para Pago #{payment.id}...")

    # --- 1. DISEÑO DEL CORREO (Estilo Orange) ---
    pax_detalle = f"{payment.pax_adults} Adultos"
    if payment.pax_children > 0:
        pax_detalle += f" / {payment.pax_children} Niños"

    # HTML para el Cliente
    html_cliente = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
        <div style="background-color: #FF8C00; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Orange Travel</h1>
        </div>
        <div style="padding: 20px; color: #333;">
            <h2>¡Hola {payment.customer_name}!</h2>
            <p>¡Tu aventura en Arica está confirmada! Hemos recibido tu pago exitosamente.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Tour:</strong> {payment.tour.nombre}</p>
                <p><strong>Fecha:</strong> {payment.reservation_date}</p>
                <p><strong>Pasajeros:</strong> {pax_detalle}</p>
                <p style="font-size: 18px; color: #FF8C00;"><strong>Total Pagado: ${payment.amount:,} CLP</strong></p>
            </div>
            <p>Te contactaremos pronto al WhatsApp {payment.customer_phone}.</p>
        </div>
    </div>
    """

    # HTML para el Admin
    tel_limpio = payment.customer_phone.replace('+', '').replace(' ', '')
    html_admin = f"""
    <div style="border: 2px solid #FF8C00; padding: 20px; font-family: sans-serif;">
        <h2 style="color: #FF8C00;">🚨 NUEVA VENTA CONFIRMADA</h2>
        <p><strong>Cliente:</strong> {payment.customer_name}</p>
        <p><strong>Tour:</strong> {payment.tour.nombre}</p>
        <p><strong>Monto:</strong> ${payment.amount:,}</p>
        <p><a href="https://wa.me/{tel_limpio}" style="color: #25D366; font-weight: bold;">📱 Contactar por WhatsApp</a></p>
    </div>
    """

    try:
        # --- 2. ENVÍO AL CLIENTE ---
        msg_cli = EmailMultiAlternatives(
            subject=f"✅ Reserva Confirmada: {payment.tour.nombre}",
            body="Tu pago ha sido confirmado.", # Versión texto plano
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[payment.customer_email]
        )
        msg_cli.attach_alternative(html_cliente, "text/html")
        msg_cli.send()
        print("DEBUG: ✅ Anymail: Correo cliente enviado.")

        # --- 3. ENVÍO AL ADMIN ---
        msg_adm = EmailMultiAlternatives(
            subject=f"🚨 PAGO RECIBIDO - {payment.customer_name}",
            body="Nueva venta realizada.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=["reservas@orangetravel.cl"] # Tu correo autorizado en Sandbox
        )
        msg_adm.attach_alternative(html_admin, "text/html")
        msg_adm.send()
        print("DEBUG: ✅ Anymail: Correo admin enviado.")

    except Exception as e:
        print(f"❌ ERROR CON ANYMAIL/MAILGUN: {e}")
