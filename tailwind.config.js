/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",        // Templates globales
    "./tours/templates/**/*.html",  // Templates específicos de la app
    "./tours/models.py",            // A veces usamos clases en los modelos
    // Si usas componentes JS o librerías como Flowbite, agrégalos aquí
  ],
  theme: {
    extend: {
      colors: {
        'orage': {
          '50': '#fff8ed',
          '500': '#f97316', // Color naranja corporativo
          '600': '#ea580c',
        },
      },
    },
  },
  plugins: [],
}