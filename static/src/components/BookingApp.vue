<template>
  <div>

    <div v-if="!isModalOpen" class="text-center mt-5">
      <button type="button" @click="isModalOpen = true"
        class="bg-orange-500 cursor-pointer hover:bg-orange-600 px-6 py-3 text-white font-bold transition rounded shadow-lg uppercase relative z-50">
        RESERVAR AHORA
      </button>
    </div>

<div v-if="isModalOpen" 
     class="fixed inset-0 z-[100] flex justify-center items-start overflow-y-auto bg-slate-900/60 backdrop-blur-sm p-4 py-10 md:py-20">
    
    <div class="relative w-full max-w-md p-8 bg-white rounded-3xl shadow-2xl border border-orange-100 my-auto top-10">
        
        <button 
            @click="isModalOpen = false" 
            class="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-orange-600 hover:bg-orange-50 transition-all"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>

        <h2 class="text-2xl font-black text-slate-800 mb-1 uppercase tracking-tighter">
            Reserva tu Cupo
        </h2>
        <p class="text-slate-500 text-sm mb-6">Completa tus datos para coordinar tu viaje en Arica.</p>

        <div class="space-y-4 text-slate-700">
          <div>
            <label class="block text-xs font-bold text-slate-700 uppercase mb-1 ml-1">Nombre Completo</label>
            <input type="text" v-model="form.nombre" placeholder="Ej: César Espinoza"
              class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:bg-white outline-none transition-all" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-slate-700 uppercase mb-1 ml-1">Email</label>
              <input type="email" v-model="form.email" placeholder="tu@correo.com"
                class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all" />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-700 uppercase mb-1 ml-1">WhatsApp</label>
              <input type="tel" v-model="form.telefono" placeholder="+56 9..."
                class="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all" />
            </div>
          </div>

          <div>
           <label class="block text-xs font-bold text-slate-700 uppercase mb-1 ml-1">Fecha del Tour</label>
  
  <DatePicker 
    v-model="form.fecha" 
    :disabled-dates="diasBloqueados"
    :min-date="new Date()"
    is-required
    color="orange"
  >
    <template #default="{ inputValue, inputEvents }">
      <input
        class="w-full p-3 bg-orange-50 border border-orange-100 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all font-semibold text-orange-800"
        :value="inputValue"
        v-on="inputEvents"
        readonly
        placeholder="Selecciona una  s sfecha"
      />
    </template>
  </DatePicker>
          </div>

          <div class="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-sm font-bold text-slate-700">Adultos ({{ this.precioAdulto }})</span>
              <div class="flex items-center gap-3">
                <button @click="decrement('adultos')"
                  class="w-8 h-8 rounded-full bg-white border border-slate-300 shadow-sm">-</button>
                <span class="font-bold text-slate-800">{{ form.adultos }}</span>
                <button @click="increment('adultos')"
                  class="w-8 h-8 rounded-full bg-white border border-slate-300 shadow-sm">+</button>
              </div>
            </div>
            <div v-if="this.precioNino" class="flex justify-between items-center">
              <span class="text-sm font-bold text-slate-700">Niños ({{ this.precioNino }})</span>
              <div class="flex items-center gap-3">
                <button @click="decrement('ninos')"
                  class="w-8 h-8 rounded-full bg-white border border-slate-300 shadow-sm">-</button>
                <span class="font-bold text-slate-800">{{ form.ninos }}</span>
                <button @click="increment('ninos')"
                  class="w-8 h-8 rounded-full bg-white border border-slate-300 shadow-sm">+</button>
              </div>
            </div>
          </div>

          <div class="pt-4">
            <div class="flex justify-between items-end mb-4">
              <span class="text-slate-500 text-sm font-medium">Total a pagar:</span>
              <span class="text-3xl font-black text-orange-600">${{ formatoCLP(totalReserva) }}</span>
            </div>

            <button @click="enviarReserva" :disabled="!formularioValido"
              class="w-full py-4 rounded-2xl font-black text-lg transition-all active:scale-95 shadow-xl disabled:opacity-50 disabled:grayscale"
              :class="formularioValido ? 'bg-orange-500 text-white hover:bg-orange-600' : 'bg-slate-200 text-slate-400 cursor-not-allowed'">
              {{ cargando ? 'Enviando...' : 'SOLICITAR RESERVA' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

</template>

<script>

import { DatePicker } from 'v-calendar';
import 'v-calendar/style.css';
import axios from 'axios';

export default {
  props: ['precioAdulto', 'precioNino', 'tourId'],
  
  components: {
    DatePicker,
  },

  data() {
    return {
      diasBloqueados: [],
      isModalOpen: false,
      cargando: false,
      form: {
        nombre: '',
        email: '',
        telefono: '',
        fecha: '',
        adultos: 1,
        ninos: 0,
    
      }
    }
  },

  mounted() {
    console.log("🚀 BookingApp montado. ID del Tour:", this.tourId);
    if (this.tourId) {
      this.cargarBloqueos();
    }
  },

  computed: {
    totalReserva() {
      const total = (this.form.adultos * this.precioAdulto) + (this.form.ninos * (this.precioNino || 0));
      return total;
    },
    formularioValido() {
      return (
        this.form.nombre.length > 3 &&
        this.form.email.includes('@') &&
        this.form.telefono.length > 7 &&
        this.form.fecha !== ''
      );
    }
  },

  methods: {
    // 1. Cargar bloqueos usando AXIOS
    cargarBloqueos() {
      console.log("📡 Pidiendo fechas bloqueadas...");
      
      axios.get(`/tours/api/bloqueos/${this.tourId}/`)
        .then(response => {
          // Con Axios, los datos ya vienen procesados en 'response.data'
          const fechas = response.data.bloqueadas;
          console.log("✅ Fechas recibidas:", fechas);
          
          this.diasBloqueados = fechas.map(f => new Date(f + 'T12:00:00'));
        })
        .catch(error => {
          console.error("❌ Error al cargar bloqueos:", error);
        });
    },

    // 2. Enviar reserva usando AXIOS
enviarReserva() {
      this.cargando = true;
      
      // Formateo de fecha para Django (YYYY-MM-DD)
      let fechaLimpia = "";
      if (this.form.fecha instanceof Date) {
        const d = this.form.fecha;
        fechaLimpia = d.getFullYear() + '-' + 
                      String(d.getMonth() + 1).padStart(2, '0') + '-' + 
                      String(d.getDate()).padStart(2, '0');
      }

      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];

      // Incluimos el total y los pax para que el backend los registre
      const payload = {
        nombre: this.form.nombre,
        email: this.form.email,
        telefono: this.form.telefono,
        fecha: fechaLimpia,
        adultos: this.form.adultos,
        ninos: this.form.ninos,
        total: this.totalReserva // Enviamos el total calculado
      };

      console.log("🚀 Iniciando Checkout...");

      // Llamamos a la nueva vista de Checkout que creamos antes
      axios.post(`/pagos/checkout/${this.tourId}/`, payload, {
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
          }
        })
        .then(response => {
          // Si el backend nos devuelve la URL de Flow, redirigimos inmediatamente
          if (response.data.redirect_url) {
            window.location.href = response.data.redirect_url;
          } else {
            alert("Error al generar el link de pago.");
          }
        })
        .catch(error => {
          console.error("❌ Error en el proceso de pago:", error);
          const msg = error.response?.data?.detail || "No se pudo contactar con el servidor de pagos.";
          alert(msg);
        })
        .finally(() => {
          this.cargando = false;
        });
    },

    // Helpers
    increment(tipo) { this.form[tipo]++; },
    decrement(tipo) {
      if (tipo === 'adultos' && this.form.adultos > 1) this.form.adultos--;
      if (tipo === 'ninos' && this.form.ninos > 0) this.form.ninos--;
    },
    formatoCLP(valor) {
      return new Intl.NumberFormat('es-CL').format(valor);
    },
    resetFormulario() {
      this.form = { nombre: '', email: '', telefono: '', fecha: '', adultos: 1, ninos: 0 };
    }
  }
}
</script>