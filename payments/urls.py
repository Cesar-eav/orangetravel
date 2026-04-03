from django.urls import path
from . import views


from .views import TourCheckoutView, FlowReturnView, FlowConfirmView, VistaConfirmacionPago


urlpatterns = [
    # Ruta para el botón de reserva (POST desde Vue)
    # Coincide con: /pagos/checkout/5/
    path('checkout/<int:tour_id>/', TourCheckoutView.as_view(), name='tour_checkout'),

    # Ruta donde llega el usuario tras pagar en Flow
    # Coincide con: /pagos/flow-return/
    path('flow-return/', FlowReturnView.as_view(), name='flow_return'),

    # Ruta invisible donde Flow avisa que el pago fue exitoso
    # Coincide con: /pagos/flow-confirm/
    path('flow-confirm/', FlowConfirmView.as_view(), name='flow_confirm'),

    #Vista de Confirmacion 
    path('vista_confirmacion_pago/<int:payment_id>', views.VistaConfirmacionPago, name='vista_confirmacion_pago'  )
]
