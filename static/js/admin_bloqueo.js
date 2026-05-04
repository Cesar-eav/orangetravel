// static/js/admin_bloqueo.js
// Muestra las fechas con reservas activas en el formulario de BloqueoTour y
// las resalta en el calendario popup del admin de Django.
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var tourSelect = document.querySelector('#id_tour');
        var fechaInput = document.querySelector('#id_fecha');

        if (!tourSelect || !fechaInput) return;

        // --- Panel informativo ---
        var panel = document.createElement('div');
        panel.id = 'bloqueo-reservas-panel';
        panel.style.cssText =
            'margin-top:10px;padding:12px 16px;border:1px solid #fed7aa;' +
            'background:#fff7ed;border-radius:8px;font-size:13px;display:none';

        // Insertamos el panel inmediatamente después de la fila del campo fecha
        var fechaRow =
            fechaInput.closest('.form-row') ||
            fechaInput.closest('[class*="field-fecha"]') ||
            fechaInput.parentElement;
        fechaRow.insertAdjacentElement('afterend', panel);

        // Fechas reservadas para el tour seleccionado (array de strings 'YYYY-MM-DD')
        var fechasReservadas = [];

        // --- Carga de datos desde la API ---
        function cargarReservas(tourId) {
            if (!tourId) {
                panel.style.display = 'none';
                fechasReservadas = [];
                return;
            }
            panel.innerHTML =
                '<span style="color:#9a3412">Cargando pagos\u2026</span>';
            panel.style.display = 'block';

            fetch('/tours/api/admin/pagos/' + tourId + '/')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var reservas = data.pagos || [];
                    fechasReservadas = reservas.map(function (r) { return r.fecha; });
                    renderPanel(reservas);
                    // Si el calendario ya está abierto, lo resaltamos de inmediato
                    var calBox = document.querySelector('[id^="calendarbox"]');
                    if (calBox) resaltarCeldasCalendario(calBox);
                })
                .catch(function () {
                    panel.innerHTML =
                        '<span style="color:#9a3412">Error al cargar pagos.</span>';
                });
        }

        // --- Renderizado del panel ---
        function renderPanel(reservas) {
            if (reservas.length === 0) {
                panel.innerHTML =
                    '<span style="color:#15803d">\u2713 Sin tours pagados para este tour.</span>';
            } else {
                var items = reservas
                    .map(function (r) {
                        return (
                            '<li style="margin:3px 0"><strong>' +
                            r.fecha +
                            '</strong> \u2014 ' +
                            r.cantidad +
                            ' pago' +
                            (r.cantidad !== 1 ? 's' : '') +
                            ' \u00b7 ' +
                            r.pax +
                            ' pasajero' +
                            (r.pax !== 1 ? 's' : '') +
                            '</li>'
                        );
                    })
                    .join('');
                panel.innerHTML =
                    '<p style="margin:0 0 8px;font-weight:bold;color:#c2410c">' +
                    '\u26a0 Fechas con tours pagados (' +
                    reservas.length +
                    '):</p>' +
                    '<ul style="margin:0;padding-left:18px;color:#7c2d12;line-height:1.7">' +
                    items +
                    '</ul>' +
                    '<p style="margin:8px 0 0;font-size:11px;color:#9a3412">' +
                    'Estas fechas tambi\u00e9n quedan bloqueadas en el calendario del cliente.' +
                    '</p>';
            }
            panel.style.display = 'block';
        }

        // --- Resaltado en el calendario popup del admin ---
        // Django agrega el div del calendario como hijo directo de <body>.
        // Cada celda contiene un <a> cuyo onclick incluye la fecha en formato
        // de la localización, pero podemos reconstruirla a partir del encabezado
        // del calendario (caption) + número de día.
        function resaltarCeldasCalendario(calNode) {
            if (fechasReservadas.length === 0) return;
            var reservadasSet = {};
            fechasReservadas.forEach(function (f) { reservadasSet[f] = true; });

            var caption = calNode.querySelector('caption');
            if (!caption) return;

            // El caption tiene el formato "Mes Año" en el idioma del servidor.
            var headText = caption.textContent.trim().toLowerCase();
            var yearMatch = headText.match(/\d{4}/);
            if (!yearMatch) return;
            var anio = parseInt(yearMatch[0], 10);

            var mesesES = [
                'enero','febrero','marzo','abril','mayo','junio',
                'julio','agosto','septiembre','octubre','noviembre','diciembre'
            ];
            var mesesEN = [
                'january','february','march','april','may','june',
                'july','august','september','october','november','december'
            ];
            var mes = -1;
            for (var i = 0; i < 12; i++) {
                if (headText.indexOf(mesesES[i]) !== -1 ||
                    headText.indexOf(mesesEN[i]) !== -1) {
                    mes = i + 1;
                    break;
                }
            }
            if (mes === -1) return;

            // Recorremos las celdas y marcamos las que coinciden
            var cells = calNode.querySelectorAll('td a');
            cells.forEach(function (link) {
                var day = parseInt(link.textContent.trim(), 10);
                if (!day) return;
                var fechaStr =
                    anio +
                    '-' +
                    String(mes).padStart('0', 2) +
                    '-' +
                    String(day).padStart('0', 2);
                // Nota: String.prototype.padStart recibe (maxLength, fillString)
                // Corregimos el orden de argumentos:
                fechaStr =
                    anio +
                    '-' +
                    (mes < 10 ? '0' + mes : mes) +
                    '-' +
                    (day < 10 ? '0' + day : day);

                if (reservadasSet[fechaStr]) {
                    link.style.cssText +=
                        'background-color:#fed7aa!important;' +
                        'border-radius:50%;' +
                        'outline:2px solid #f97316;' +
                        'font-weight:bold;';
                    link.title = 'Fecha con tours pagados';
                }
            });

            // Cuando se navega de mes, volvemos a resaltar
            var navLinks = calNode.querySelectorAll('a');
            navLinks.forEach(function (nav) {
                if (nav.getAttribute('data-bloqueo-bound')) return;
                nav.setAttribute('data-bloqueo-bound', '1');
                nav.addEventListener('click', function () {
                    setTimeout(function () { resaltarCeldasCalendario(calNode); }, 60);
                });
            });
        }

        // MutationObserver: detecta cuando Django agrega el popup del calendario
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (
                        node.nodeType === 1 &&
                        node.id &&
                        node.id.indexOf('calendarbox') === 0
                    ) {
                        setTimeout(function () { resaltarCeldasCalendario(node); }, 40);
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true });

        // --- Eventos ---
        tourSelect.addEventListener('change', function () {
            cargarReservas(this.value);
        });

        // Carga automática si el tour ya está seleccionado (modo edición)
        if (tourSelect.value) {
            cargarReservas(tourSelect.value);
        }
    });
})();
