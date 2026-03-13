<template>
  <div class="p-6 bg-white rounded-2xl shadow-xl border border-orange-100 max-w-md mx-auto">
    <h2 class="text-2xl font-bold text-blue-dark mb-2 uppercase tracking-tight">
      Reserva tu Cupo
    </h2>
    <p class="text-gray-500 text-sm mb-6">
      Selecciona una fecha y gestionaremos tu disponibilidad en Arica.
    </p>

    <div class="bg-gray-50 h-32 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg mb-6">
      <span class="text-gray-400 font-medium italic text-center px-4">
        Calendario de Reservas (Vue 3)
      </span>
    </div>

    <button @click="test" class="w-full bg-orange-500 text-white py-4 rounded-xl font-bold text-lg hover:bg-orange-600 shadow-md transition-all active:scale-95">
      Verificar Disponibilidad
    </button>
  </div>
</template>

<script setup>
const test = () => {
    alert("¡Vue 3 funcionando en Orange Travel! 🚀");
};
</script>