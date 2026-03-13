<template>
  <div class="p-6 bg-white rounded-2xl shadow-xl border border-orange-100 max-w-md mx-auto">
    <h2 class="text-xl font-bold text-blue-dark mb-4 uppercase tracking-tighter">
      Reserva tu Experiencia
    </h2>

    <div class="mb-6">
      <label class="block text-sm font-medium text-gray-700 mb-2">Fecha del Tour</label>
      <input 
        type="date" 
        v-model="selectedDate"
        :min="minDate"
        class="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
      />
    </div>

    <div class="space-y-4 mb-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="font-semibold text-gray-800">Adultos</p>
          <p class="text-xs text-gray-500">$18.000 p/p</p>
        </div>
        <div class="flex items-center gap-3">
          <button @click="decrement('adults')" class="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center hover:bg-gray-100">-</button>
          <span class="font-bold w-4 text-center">{{ adults }}</span>
          <button @click="increment('adults')" class="w-8 h-8 rounded-full border border-orange-500 text-orange-600 flex items-center justify-center hover:bg-orange-50">+</button>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div>
          <p class="font-semibold text-gray-800">Niños</p>
          <p class="text-xs text-gray-500">Hasta 11 años - $15.000</p>
        </div>
        <div class="flex items-center gap-3">
          <button @click="decrement('children')" class="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center hover:bg-gray-100">-</button>
          <span class="font-bold w-4 text-center">{{ children }}</span>
          <button @click="increment('children')" class="w-8 h-8 rounded-full border border-orange-500 text-orange-600 flex items-center justify-center hover:bg-orange-50">+</button>
        </div>
      </div>
    </div>

    <div class="pt-4 border-t border-dashed border-gray-200">
      <div class="flex justify-between items-center mb-6">
        <span class="text-gray-600 font-medium">Total Estimado:</span>
        <span class="text-2xl font-black text-orange-600">${{ formatPrice(totalPrice) }}</span>
      </div>
      
      <button 
        @click="submitBooking"
        :disabled="!selectedDate"
        class="w-full py-4 rounded-xl font-bold text-lg shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        :class="selectedDate ? 'bg-orange-500 text-white hover:bg-orange-600' : 'bg-gray-200 text-gray-400'"
      >
        Solicitar Reserva
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BookingApp',
  
  data() {
    return {
      selectedDate: '',
      adults: 1,
      children: 0,
      prices: {
        adult: 18000,
        child: 15000
      }
    }
  },

  computed: {
    // Evita fechas pasadas
    minDate() {
      const today = new Date();
      return today.toISOString().split('T')[0];
    },

    // Cálculo del total en tiempo real
    totalPrice() {
      return (this.adults * this.prices.adult) + (this.children * this.prices.child);
    }
  },

  methods: {
    increment(type) {
      this[type]++;
    },

    decrement(type) {
      if (type === 'adults' && this.adults > 1) this.adults--;
      if (type === 'children' && this.children > 0) this.children--;
    },

    formatPrice(value) {
      return new Intl.NumberFormat('es-CL').format(value);
    },

    submitBooking() {
      const payload = {
        fecha: this.selectedDate,
        adultos: this.adults,
        ninos: this.children,
        total: this.totalPrice
      };
      console.log("Enviando reserva a Orange Travel:", payload);
      alert(`Solicitud enviada para el ${this.selectedDate}. ¡Revisa tu correo pronto!`);
    }
  }
}
</script>