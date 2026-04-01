console.log(
  "%c🚀 ORANGE TRAVEL - V1.2.5 - DEPLOY: 01-04-2026", 
  "background: #f97316; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;"
);

import { createApp } from 'vue';
import BookingApp from './components/BookingApp.vue';

import './input.css'; // Importamos tu CSS de Tailwind 4 para que Vite lo procese


// Buscamos el elemento con ID 'reservation-widget' en tu template de Django
const root = document.getElementById('reservation-widget');

if (root) {


    const precioAdulto = parseInt(root.dataset.precioAdulto) || 0;
    const precioNino = parseInt(root.dataset.precioNino) || 0;
    const tourId = parseInt(root.dataset.tourId) || 0;

    const props = {
        precioAdulto,
        precioNino,
        tourId
    };

    const app = createApp(BookingApp, props);
    app.mount('#reservation-widget');   
}


