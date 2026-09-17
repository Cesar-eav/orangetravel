"""Comando de SOLO LECTURA: no modifica ningun dato.

Detecta incongruencias entre Payment.amount y Reserva.precio_total,
emparejando ambos modelos de forma heuristica (no existe FK entre ellos)
por tour + fecha + email, siguiendo el mismo criterio ya usado en
tours/signals.py para vincular pagos con reservas.
"""
import csv
from collections import defaultdict

from django.core.management.base import BaseCommand

from payments.models import Payment
from tours.models import Reserva

FALLBACK_ADULTO = 18000
FALLBACK_NINO = 15000


def _clave(tour_id, fecha, email):
    return (tour_id, fecha, (email or "").strip().lower())


def clasificar_causas(payment, reserva):
    causas = []

    if hasattr(reserva.tour, "precio"):
        precio = reserva.tour.precio
        p_adulto_correcto = precio.valor_adulto
        p_nino_correcto = precio.valor_nino if precio.tiene_precio_nino else precio.valor_adulto
        total_correcto = (reserva.adultos * p_adulto_correcto) + (reserva.ninos * p_nino_correcto)
        total_fallback = (reserva.adultos * FALLBACK_ADULTO) + (reserva.ninos * FALLBACK_NINO)

        if reserva.precio_total != total_correcto:
            if reserva.precio_total == total_fallback:
                causas.append("BUG_FALLBACK_1800015000")
            else:
                causas.append("RESERVA_PRECIO_INCONSISTENTE")

        if payment.amount == total_correcto:
            causas.append("PAYMENT_CORRECTO_RESERVA_BUGUEADA")
    else:
        causas.append("TOUR_SIN_PRECIOTOUR")

    if reserva.adultos != payment.pax_adults or reserva.ninos != payment.pax_children:
        causas.append("PAX_DIVERGENTE")

    if payment.tour_precio_al_pagar is None:
        causas.append("PAYMENT_AMOUNT_SIN_VALIDAR")

    if not causas:
        causas.append("CAUSA_DESCONOCIDA")

    return causas


class Command(BaseCommand):
    help = (
        "SOLO LECTURA. Detecta incongruencias entre Payment.amount y "
        "Reserva.precio_total emparejando ambos modelos por tour+fecha+email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv", dest="csv_path", default=None,
            help="Ruta de archivo CSV donde exportar el reporte completo.",
        )
        parser.add_argument(
            "--incluir-borrados", action="store_true",
            help="Incluye Reservas con borrado logico y Payments con deleted_at != None.",
        )
        parser.add_argument(
            "--todos-los-status", action="store_true",
            help="Al reportar Payments sin Reserva, incluye todos los status "
                 "(por defecto solo se reportan los de status='paid').",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        incluir_borrados = options["incluir_borrados"]
        todos_los_status = options["todos_los_status"]

        reservas_qs = Reserva.all_objects if incluir_borrados else Reserva.objects
        reservas = list(reservas_qs.select_related("tour", "tour__precio"))

        payments_qs = Payment.objects.select_related("tour", "tour__precio")
        if not incluir_borrados:
            payments_qs = payments_qs.filter(deleted_at__isnull=True)
        payments = list(payments_qs)

        reservas_por_clave = defaultdict(list)
        for r in reservas:
            reservas_por_clave[_clave(r.tour_id, r.fecha, r.email_cliente)].append(r)

        reservas_emparejadas_ids = set()
        incongruencias = []
        payments_sin_reserva = []
        matches_ambiguos = []

        for p in payments:
            candidatos = reservas_por_clave.get(_clave(p.tour_id, p.reservation_date, p.customer_email), [])

            if not candidatos:
                payments_sin_reserva.append(p)
                continue

            match = None
            if len(candidatos) == 1:
                match = candidatos[0]
            else:
                exactos = [
                    r for r in candidatos
                    if r.adultos == p.pax_adults and r.ninos == p.pax_children
                ]
                if len(exactos) == 1:
                    match = exactos[0]
                else:
                    matches_ambiguos.append((p, candidatos))
                    continue

            reservas_emparejadas_ids.add(match.id)

            if p.amount != match.precio_total:
                incongruencias.append((p, match, clasificar_causas(p, match)))

        reservas_sin_payment = [r for r in reservas if r.id not in reservas_emparejadas_ids]

        self._imprimir_reporte(
            incongruencias, reservas_sin_payment, payments_sin_reserva,
            matches_ambiguos, todos_los_status, len(payments), len(reservas),
        )

        if csv_path:
            self._exportar_csv(
                csv_path, incongruencias, reservas_sin_payment,
                payments_sin_reserva, matches_ambiguos, todos_los_status,
            )
            self.stdout.write(self.style.SUCCESS(f"\nCSV exportado a: {csv_path}"))

    def _payments_sin_reserva_filtrados(self, payments_sin_reserva, todos_los_status):
        if todos_los_status:
            return payments_sin_reserva
        return [p for p in payments_sin_reserva if p.status == Payment.STATUS_PAID]

    def _imprimir_reporte(self, incongruencias, reservas_sin_payment, payments_sin_reserva,
                           matches_ambiguos, todos_los_status, total_payments, total_reservas):
        w = self.stdout.write

        w(self.style.MIGRATE_HEADING(
            f"\n=== INCONGRUENCIAS DE MONTO ({len(incongruencias)}) ==="
        ))
        for p, r, causas in incongruencias:
            diff = p.amount - r.precio_total
            w(
                f"Payment #{p.id} ({p.codigo}) vs Reserva #{r.id} ({r.codigo}) | "
                f"Tour: {r.tour.nombre} | Fecha: {r.fecha} | Email: {r.email_cliente} | "
                f"amount={p.amount} precio_total={r.precio_total} diff={diff} | "
                f"Causas: {', '.join(causas)}"
            )

        w(self.style.MIGRATE_HEADING(
            f"\n=== RESERVAS SIN PAYMENT EMPAREJADO ({len(reservas_sin_payment)}) ==="
        ))
        for r in reservas_sin_payment:
            w(
                f"Reserva #{r.id} ({r.codigo}) | Tour: {r.tour.nombre} | Fecha: {r.fecha} | "
                f"Email: {r.email_cliente} | Adultos={r.adultos} Ninos={r.ninos} | "
                f"precio_total={r.precio_total} | Estado={r.estado}"
            )

        filtrados = self._payments_sin_reserva_filtrados(payments_sin_reserva, todos_los_status)
        etiqueta = "" if todos_los_status else " (solo status='paid')"
        w(self.style.MIGRATE_HEADING(
            f"\n=== PAYMENTS SIN RESERVA EMPAREJADA{etiqueta} ({len(filtrados)}) ==="
        ))
        for p in filtrados:
            w(
                f"Payment #{p.id} ({p.codigo}) | Tour: {p.tour.nombre} | Fecha: {p.reservation_date} | "
                f"Email: {p.customer_email} | pax_adults={p.pax_adults} pax_children={p.pax_children} | "
                f"amount={p.amount} | status={p.status}"
            )

        if matches_ambiguos:
            w(self.style.MIGRATE_HEADING(
                f"\n=== MATCHES AMBIGUOS SIN RESOLVER ({len(matches_ambiguos)}) ==="
            ))
            for p, candidatos in matches_ambiguos:
                ids = ", ".join(str(r.id) for r in candidatos)
                w(f"Payment #{p.id} ({p.codigo}) tiene {len(candidatos)} Reservas candidatas: #{ids}")

        conteo_causas = defaultdict(int)
        for _p, _r, causas in incongruencias:
            for c in causas:
                conteo_causas[c] += 1

        w(self.style.MIGRATE_HEADING("\n=== RESUMEN ==="))
        w(f"Payments analizados: {total_payments}")
        w(f"Reservas analizadas: {total_reservas}")
        w(f"Incongruencias de monto: {len(incongruencias)}")
        for causa, n in sorted(conteo_causas.items(), key=lambda kv: -kv[1]):
            w(f"  - {causa}: {n}")
        w(f"Reservas sin Payment: {len(reservas_sin_payment)}")
        w(f"Payments sin Reserva{etiqueta}: {len(filtrados)}")
        w(f"Matches ambiguos (no resueltos): {len(matches_ambiguos)}")

    def _exportar_csv(self, csv_path, incongruencias, reservas_sin_payment,
                       payments_sin_reserva, matches_ambiguos, todos_los_status):
        filtrados = self._payments_sin_reserva_filtrados(payments_sin_reserva, todos_los_status)

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tipo_de_fila", "payment_id", "payment_codigo", "reserva_id", "reserva_codigo",
                "tour", "fecha", "email", "adultos_o_pax_adults", "ninos_o_pax_children",
                "amount", "precio_total", "diferencia", "estado_o_status", "causas_o_detalle",
            ])

            for p, r, causas in incongruencias:
                writer.writerow([
                    "incongruencia_monto", p.id, p.codigo, r.id, r.codigo, r.tour.nombre,
                    r.fecha, r.email_cliente, r.adultos, r.ninos, p.amount, r.precio_total,
                    p.amount - r.precio_total, r.estado, "; ".join(causas),
                ])

            for r in reservas_sin_payment:
                writer.writerow([
                    "reserva_sin_payment", "", "", r.id, r.codigo, r.tour.nombre, r.fecha,
                    r.email_cliente, r.adultos, r.ninos, "", r.precio_total, "", r.estado, "",
                ])

            for p in filtrados:
                writer.writerow([
                    "payment_sin_reserva", p.id, p.codigo, "", "", p.tour.nombre,
                    p.reservation_date, p.customer_email, p.pax_adults, p.pax_children,
                    p.amount, "", "", p.status, "",
                ])

            for p, candidatos in matches_ambiguos:
                ids = ", ".join(str(r.id) for r in candidatos)
                writer.writerow([
                    "match_ambiguo", p.id, p.codigo, "", "", p.tour.nombre,
                    p.reservation_date, p.customer_email, p.pax_adults, p.pax_children,
                    p.amount, "", "", p.status, f"Reservas candidatas: {ids}",
                ])
