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
    console.log("Vue montado con props:", props);

    const app = createApp(BookingApp, props);
    app.mount('#reservation-widget');   
}


