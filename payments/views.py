from __future__ import annotations

import logging
from datetime import date
from typing import Any
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlsplit, urlunsplit

from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import render, redirect

from .models import Payment
from tours.models import Reserva
from tours.views import idioma_cliente
from tours.traduccion import mostrar_aprobado, texto
from django.utils import translation
from django.utils.translation import gettext as _

from tours.models import Tour  # Asegúrate de que esta ruta sea correcta
from .flow import FlowClient

from .confirmacion import aplicar_estado_flow

logger = logging.getLogger(__name__)

def _coerce_https_if_forwarded(request, url: str) -> str:
    """URLs de retorno y webhook siempre en HTTPS en producción.

    Si Flow recibiera http://, SECURE_SSL_REDIRECT respondería 301 y Flow no
    repite el POST del webhook tras una redirección: el aviso se perdería.
    """
    proto = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip().lower()
    if (proto == "https" or not settings.DEBUG) and url.startswith("http://"):
        parts = urlsplit(url)
        return urlunsplit(("https", parts.netloc, parts.path, parts.query, parts.fragment))
    return url

class TourCheckoutView(APIView):
    """
    Inicia el proceso de pago para un Tour. 
    Permite acceso a usuarios no registrados (AllowAny).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, tour_id: int):
        tour = get_object_or_404(Tour, id=tour_id)
        data = request.data
        idioma = idioma_cliente(data)
        translation.activate(idioma)  # mensajes de respuesta en el idioma de la página
        if not tour.con_precio:
            return Response({"detail": _("Este tour se reserva por cotización.")}, status=status.HTTP_400_BAD_REQUEST)

        # El email debe venir en el POST ya que el usuario no está registrado
        email = request.data.get("email")
        if not email:
            return Response({"detail": _("Se requiere un email para la reserva.")}, status=status.HTTP_400_BAD_REQUEST)

        # Validación de anticipación mínima: solo desde mañana (no se reserva para el mismo día)
        try:
            fecha_reserva = date.fromisoformat(str(data.get('fecha', '')))
        except (TypeError, ValueError):
            return Response({"detail": _("Fecha inválida.")}, status=status.HTTP_400_BAD_REQUEST)
        if fecha_reserva <= date.today():
            return Response({"detail": _("Las reservas deben hacerse a partir del día siguiente.")}, status=status.HTTP_400_BAD_REQUEST)

        # Crear el registro de pago en nuestra DB (Estado PENDING)
        payment = Payment.objects.create(
            tour=tour,
            amount=data.get('total'), # Asumiendo que Tour tiene un campo precio
            currency="CLP",
            customer_name=data.get('nombre'),
            customer_email=data.get('email'),
            customer_phone=data.get('telefono'),
            reservation_date=data.get('fecha'),
            pax_adults=data.get('adultos'),
            pax_children=data.get('ninos'),
            status=Payment.STATUS_PENDING,
            idioma=idioma,
        )

        # 2. Creación de la Reserva
        reserva = Reserva.objects.create(
            tour=tour,
            nombre_cliente=data.get('nombre'),
            email_cliente=data.get('email'),
            telefono_cliente=data.get('telefono'),
            fecha=data.get('fecha'),
            adultos=int(data.get('adultos', 1)),
            ninos=int(data.get('ninos', 0)),
            notas_internas=f"Solicitud web: {data.get('adultos')} ADL, {data.get('ninos')} CHD.",
            idioma=idioma,
        )


        flow = FlowClient()
        if not flow.is_configured():
            return Response({"detail": _("Error de configuración en el servidor.")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Configurar URLs de retorno
        url_return = request.build_absolute_uri(reverse("flow_return"))
        url_confirmation = request.build_absolute_uri(reverse("flow_confirm"))
        
        url_return = _coerce_https_if_forwarded(request, url_return)
        url_confirmation = _coerce_https_if_forwarded(request, url_confirmation)
        logger.info("Checkout pago %s: urlConfirmation=%s", payment.id, url_confirmation)

        try:
            result = flow.create_payment(
                commerce_order=str(payment.id),
                subject=f"Reserva Tour: {tour.nombre_es}",
                amount=payment.amount,
                email=email,
                url_return=url_return,
                url_confirmation=url_confirmation,
            )
            
            payment.provider_token = result.token
            payment.raw_create_response = result.raw
            payment.save(update_fields=["provider_token", "raw_create_response", "updated_at"])

            return Response({"redirect_url": result.redirect_url})
            
        except Exception as exc:
            payment.status = Payment.STATUS_FAILED
            payment.raw_create_response = {"error": str(exc)}
            payment.save(update_fields=["status", "raw_create_response", "updated_at"])
            return Response({"detail": _("Error al contactar con el proveedor de pagos.")}, status=status.HTTP_502_BAD_GATEWAY)

class FlowReturnView(APIView):
    """
    Esta vista recibe al usuario de vuelta desde el portal de Flow.
    No requiere autenticación ya que el usuario puede ser un invitado.
    """
    permission_classes = [permissions.AllowAny]

    def _get_params(self, request):
        """Extrae el token de Flow sin importar si viene por GET o POST."""
        return request.data.get("token") or request.GET.get("token")

    def handle_request(self, request):
        token = self._get_params(request)
        
        if not token:
            logger.warning("FlowReturnView: Se accedió sin token.")
            return HttpResponseRedirect("/") # Redirigir al inicio si no hay token

        # Buscamos el pago por el token que nos dio Flow
        payment = Payment.objects.filter(provider_token=str(token)).first()
        
        if not payment:
            messages.error(request, _("No pudimos encontrar el registro de tu pago."))
            return HttpResponseRedirect("/")

        # /pagos/ no lleva prefijo de idioma: los mensajes siguen el idioma en que se pagó.
        translation.activate(payment.idioma)

        # --- SINCRONIZACIÓN DE ESTADO (Best-effort) ---
        # Si el pago aún no figura como pagado, le preguntamos a Flow ahora mismo
        if payment.status != Payment.STATUS_PAID:
            try:
                resultado = aplicar_estado_flow(payment, FlowClient().get_status(token=token))
            except Exception:
                logger.exception("Error consultando a Flow en el retorno (pago %s)", payment.id)
                resultado = None

            if resultado in ("pagado", "ya_pagado"):
                messages.success(request, _("¡Gracias! Tu reserva para el tour '%(tour)s' ha sido confirmada.") % {'tour': texto(payment.tour, 'nombre', payment.idioma)})
            elif resultado == "fallido":
                messages.error(request, _("El pago fue rechazado o cancelado. Por favor, intenta nuevamente."))
            elif resultado == "pendiente":
                messages.warning(request, _("Tu pago está siendo procesado por la institución financiera."))
            else:
                messages.warning(request, _("Estamos confirmando tu pago. Te avisaremos por email en unos minutos."))

        # --- REDIRECCIÓN FINAL ---

        return HttpResponseRedirect(reverse('vista_confirmacion_pago', args=[payment.id]))

    def get(self, request): return self.handle_request(request)
    def post(self, request): return self.handle_request(request)

class FlowConfirmView(APIView):
    """
    Webhook: Flow llama a esta vista servidor-a-servidor.
    Aquí es donde se confirma el pago REAL en la base de datos.
    """
    permission_classes = [permissions.AllowAny]

    @csrf_exempt
    def post(self, request):
        def _first(value: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return str(value[0]) if value else None
            return str(value)

        def _normalized_payload() -> dict[str, Any]:
            # DRF FormParser may yield QueryDict where dict(...) becomes lists.
            out: dict[str, Any] = {}
            try:
                if hasattr(request, "data") and hasattr(request.data, "keys"):
                    for k in request.data.keys():
                        out[str(k)] = _first(request.data.get(k))
            except Exception:  # noqa: BLE001
                pass
            try:
                for k in request.POST.keys():
                    if str(k) not in out:
                        out[str(k)] = _first(request.POST.get(k))
            except Exception:  # noqa: BLE001
                pass
            return out

        payload = _normalized_payload()
        token = payload.get("token")
        # Queda en stderr.log: sirve para saber si Flow está llegando al webhook.
        logger.info("Webhook Flow recibido (token %s)", f"...{token[-6:]}" if token else "ausente")
        if not token:
            return HttpResponse("OK", status=200)  # Flow exige 200 siempre

        payment = Payment.objects.filter(provider_token=str(token)).first()
        if not payment:
            logger.warning("Webhook Flow con token desconocido (...%s)", token[-6:])
            return HttpResponse("OK", status=200)

        payment.raw_confirm_payload = payload
        payment.save(update_fields=["raw_confirm_payload", "updated_at"])

        try:
            resultado = aplicar_estado_flow(payment, FlowClient().get_status(token=token))
            logger.info("Webhook Flow: pago %s → %s", payment.id, resultado)
        except Exception:
            logger.exception("Error procesando el webhook de Flow (pago %s)", payment.id)

        return HttpResponse("OK", status=200)
    

def VistaConfirmacionPago(request, payment_id):

    payment = Payment.objects.get(id=payment_id)
    # /pagos/ no lleva prefijo de idioma: la página sigue el idioma en que se pagó.
    translation.activate(payment.idioma)
    tour = mostrar_aprobado([payment.tour], request)[0]
   
    context = {
        'payment': payment,
        'tour': tour,
        'pax_total': payment.pax_adults + payment.pax_children
    }

    if payment.status == Payment.STATUS_PAID:
        return render(request, 'payments/confirmacion_reserva.html', context)

    else:
        messages.error(request, _("Lo sentimos, no encontramos una confirmación válida para este pago."))
        return render(request, 'payments/fail.html', context)
    

