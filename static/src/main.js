import { createApp } from 'vue';
import BookingApp from './components/BookingApp.vue';
import CotizacionApp from './components/CotizacionApp.vue';

import './input.css'; // Importamos tu CSS de Tailwind 4 para que Vite lo procese


// Buscamos el elemento con ID 'reservation-widget' en tu template de Django
const root = document.getElementById('reservation-widget');

if (root) {


    const tourId = parseInt(root.dataset.tourId) || 0;
    // Textos traducidos por Django (json_script en tours/tour.html) e idioma de la página.
    const t = JSON.parse(document.getElementById('textos-reserva').textContent);
    const idioma = (document.documentElement.lang || 'es').slice(0, 2);

    // Solo los tours de la categoría con precio se pagan en línea; el resto se cotiza.
    let app;
    if (root.dataset.conPrecio === '1') {
        const precioAdulto = parseInt(root.dataset.precioAdulto) || 0;
        const precioNino = parseInt(root.dataset.precioNino) || 0;
        app = createApp(BookingApp, { precioAdulto, precioNino, tourId, t, idioma });
    } else {
        app = createApp(CotizacionApp, { tourId, t, idioma });
    }
    app.mount('#reservation-widget');
}
