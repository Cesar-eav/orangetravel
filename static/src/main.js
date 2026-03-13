import { createApp } from 'vue';
import BookingApp from './components/BookingApp.vue';
import './input.css'; // Importamos tu CSS de Tailwind 4 para que Vite lo procese

const app = createApp(BookingApp);

// Buscamos el elemento con ID 'reservation-widget' en tu template de Django
const root = document.getElementById('reservation-widget');

if (root) {
    app.mount('#reservation-widget');
}