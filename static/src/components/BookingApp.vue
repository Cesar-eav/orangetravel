<template>
  <div>

    <div v-if="!isModalOpen" class="text-center mt-5">
      <button type="button" @click="isModalOpen = true"
        class="bg-orange-500 cursor-pointer hover:bg-orange-600 px-6 py-3 text-white font-bold transition rounded shadow-lg uppercase relative z-50">
        RESERVAR AHORA
      </button>
    </div>

<div v-if="isModalOpen" 
class="fixed inset-0 z-50 flex items-center justify-center 
            bg-black/40 
            backdrop-blur-md 
            p-4">
    
    <div class="p-8 bg-white rounded-3xl shadow-2xl border border-orange-100 max-w-md w-full relative">
        
        <button 
            @click="isModalOpen = false" 
            class="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-orange-600 hover:bg-orange-50 transition-all group"
            title="Cerrar"
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
          <input type="date" v-model="form.fecha" :min="minDate"
            class="w-full p-3 bg-orange-50 border border-orange-100 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all font-semibold text-orange-800" />
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
export default {
props: ['precioAdulto', 'precioNino', 'tourId'],

watch: {
  isModalOpen(abierto) {
    if (abierto) {
      // Aplicamos la clase de Tailwind al body
      document.body.classList.add('overflow-hidden');
    } else {
      // La quitamos al cerrar
      document.body.classList.remove('overflow-hidden');
    }
  }
},
  data() {
    return {
      isModalOpen: false,
      cargando: false,
      form: {
        nombre: '',
        email: '',
        telefono: '',
        fecha: '',
        adultos: 1,
        ninos: 0,
        tour_id: this.tourId // Este ID debe venir dinámicamente de Django después
      }
    }
  },
  computed: {
    minDate() {
      return new Date().toISOString().split('T')[0];
    },
    totalReserva() {
      let total = this.form.adultos * this.precioAdulto;

      if (this.form.ninos > 0) {
        total += this.form.ninos * this.precioNino;
      }
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
    increment(tipo) { this.form[tipo]++; },
    decrement(tipo) {
      if (tipo === 'adultos' && this.form.adultos > 1) this.form.adultos--;
      if (tipo === 'ninos' && this.form.ninos > 0) this.form.ninos--;
    },
    formatoCLP(valor) {
      return new Intl.NumberFormat('es-CL').format(valor);
    },
    async enviarReserva() {
      this.cargando = true;

      // Capturamos el CSRF Token de las cookies de Django
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];

      try {
        const response = await fetch('/tours/api/reserva/crear/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(this.form)
        });

        const data = await response.json();

        if (data.status === 'success') {
          alert("¡Solicitud enviada! Nos contactaremos contigo a la brevedad.");
          // Opcional: limpiar formulario
          this.form.fecha = '';
        } else {
          alert("Error: " + data.mensaje);
        }
      } catch (error) {
        console.error("Error en la petición:", error);
      } finally {
        this.cargando = false;
      }
    }
  }
}
</script>s