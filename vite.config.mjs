import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(), // Plugin oficial para Tailwind 4
  ],
  resolve: {
    alias: {
      // ESTO ES LO QUE FALTA:
      'vue': 'vue/dist/vue.esm-bundler.js'
    }
  },
  // Definimos la raíz de fuentes para Vite
  root: path.resolve(__dirname), 
  base: '/',
  build: {
    // Dónde se guardará el código compilado para producción
    outDir: path.resolve(__dirname, 'static/js/dist'),
    emptyOutDir: true,
    manifest: true, // Genera manifest.json para que Django sepa qué archivos cargar
    rollupOptions: {
      // El punto de entrada principal que crearemos en el siguiente paso
      input: path.resolve(__dirname, 'static/src/main.js'),
    },
  },
  server: {
    // Configuración para que el HMR (Hot Module Replacement) funcione con Django
    host: 'localhost',
    port: 5173,
    origin: 'http://localhost:5173',
    cors: true,
    watch: {
      usePolling: true,
    }
  }
});