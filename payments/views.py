from __future__ import annotations

import logging
from typing import Any
from .emails import enviar_confirmacion_pago  # Asumiendo que están en la misma carpeta
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlsplit, urlunsplit

from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import render, redirect

from .models import Payment
from tours.models import Reserva

from tours.models import Tour  # Asegúrate de que esta ruta sea correcta
from .flow import FlowClient

from .emails import (
    send_download_purchase_confirmation_email
    # send_download_purchase_problem_email,
    # send_payment_integration_error_to_admins,
)
from .models import Payment

logger = logging.getLogger(__name__)

def _flow_terminal_failure(status_value: Any) -> str | None:
    """Mapeo de estados de Flow a estados de fallo terminal."""
    if status_value is None:
        return None

    try:
        numeric = int(status_value)
    except Exception:
        numeric = None

    if numeric == 3: return Payment.STATUS_FAILED
    if numeric == 4: return Payment.STATUS_CANCELED

    s = str(status_value).strip().lower()
    if s in ("rejected", "reject", "failed", "failure", "error"):
        return Payment.STATUS_FAILED
    if s in ("canceled", "cancelled", "canceled_by_user", "cancel"):
        return Payment.STATUS_CANCELED
    return None

def _coerce_https_if_forwarded(request, url: str) -> str:
    """Asegura que las URLs de retorno usen HTTPS si el sitio está tras un proxy."""
    proto = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip().lower()
    if proto == "https" and url.startswith("http://"):
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

        print("Resreva: ", data)
        # El email debe venir en el POST ya que el usuario no está registrado
        email = request.data.get("email")
        if not email:
            return Response({"detail": "Se requiere un email para la reserva."}, status=status.HTTP_400_BAD_REQUEST)

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
            notas_internas=f"Solicitud web: {data.get('adultos')} ADL, {data.get('ninos')} CHD."
        )


        flow = FlowClient()
        if not flow.is_configured():
            return Response({"detail": "Error de configuración en el servidor."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Configurar URLs de retorno
        url_return = request.build_absolute_uri(reverse("flow_return"))
        url_confirmation = request.build_absolute_uri(reverse("flow_confirm"))
        
        url_return = _coerce_https_if_forwarded(request, url_return)
        url_confirmation = _coerce_https_if_forwarded(request, url_confirmation)

        try:
            result = flow.create_payment(
                commerce_order=str(payment.id),
                subject=f"Reserva Tour: {tour.nombre}",
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
            return Response({"detail": "Error al contactar con el proveedor de pagos."}, status=status.HTTP_502_BAD_GATEWAY)

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
            messages.error(request, "No pudimos encontrar el registro de tu pago.")
            return HttpResponseRedirect("/")

        # --- SINCRONIZACIÓN DE ESTADO (Best-effort) ---
        # Si el pago aún no figura como pagado, le preguntamos a Flow ahora mismo
        if payment.status != Payment.STATUS_PAID:
            flow = FlowClient()
            try:
                status_data = flow.get_status(token=token)
                flow_status = status_data.get("status")

                # Actualizamos el registro local si Flow confirma el éxito (status 2)
                if flow_status in (2, "2", "paid"):
                    payment.status = Payment.STATUS_PAID
                    payment.paid_at = timezone.now()
                    payment.raw_status_response = status_data
                    payment.save()
                    messages.success(request, f"¡Gracias! Tu reserva para el tour '{payment.tour.nombre}' ha sido confirmada.")
                
                elif flow_status in (3, "3", 4, "4"):
                    payment.status = Payment.STATUS_FAILED
                    payment.save()
                    messages.error(request, "El pago fue rechazado o cancelado. Por favor, intenta nuevamente.")
                
                else:
                    messages.warning(request, "Tu pago está siendo procesado por la institución financiera.")

            except Exception as e:
                logger.error(f"Error consultando estado en retorno: {e}")
                messages.warning(request, "Estamos confirmando tu pago. Te avisaremos por email en unos minutos.")

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
    
        token = request.data.get("token")
        if not token:
            return HttpResponse("OK", status=200) # Flow exige 200 siempre

        payment = Payment.objects.filter(provider_token=str(token)).first()
        if not payment:
            return HttpResponse("OK", status=200)
        
        payment.raw_confirm_payload = payload
        if token:
            payment.provider_token = str(token)
        payment.save(update_fields=["raw_confirm_payload", "provider_token", "updated_at"])

        flow = FlowClient()
        try:
            status_data = flow.get_status(token=payment.provider_token)
            payment.raw_status_response = status_data
            
            flow_status = status_data.get("status")
            
            # 1. Caso éxito (Status 2 en Flow)
            if flow_status in (2, "2", "paid"):
                if payment.status != Payment.STATUS_PAID:
                    payment.status = Payment.STATUS_PAID
                    payment.paid_at = timezone.now()
                    payment.save()
                    send_download_purchase_confirmation_email(payment=payment)

                    try:
                        enviar_confirmacion_pago(payment)
                    except Exception as e:
                        # Logueamos el error pero no dejamos que la vista falle
                        print(f"Error al enviar emails: {e}")

            # 2. Caso fallo
            else:
                terminal = _flow_terminal_failure(flow_status)
                if terminal:
                    payment.status = terminal
                    payment.save()
                    
        except Exception as exc:
            logger.error(f"Error confirmación Flow: {exc}")
            
        return HttpResponse("OK", status=200)
    

def VistaConfirmacionPago(request, payment_id):

    payment = Payment.objects.get(id=payment_id)

    print("HOLAAAAA-------->", payment)
    
    context = {
        'payment': payment,
        'tour': payment.tour,
        'pax_total': payment.pax_adults + payment.pax_children
    }

    if payment.status == Payment.STATUS_PAID:
        return render(request, 'payments/confirmacion_reserva.html', context)

    else:
        messages.error(request, "Lo sentimos, no encontramos una confirmación válida para este pago.")
        return render(request, 'payments/fail.html', context)
    

