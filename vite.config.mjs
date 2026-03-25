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
      outDir: path.resolve(__dirname, 'static/js/dist'),
      emptyOutDir: true,
      manifest: true,
      rollupOptions: {
        input: path.resolve(__dirname, 'static/src/main.js'),
        // AGREGA ESTO:
        output: {
          entryFileNames: `assets/[name].js`,
          chunkFileNames: `assets/[name].js`,
          assetFileNames: `assets/[name].[ext]`
        }
      },
    },
  server: {
    // Configuración para que el HMR (Hot Module Replacement) funcione con Django
    host: 'localhost',
    port: 5173,
    origin: 'http://localhost:5173',
    cors: true,
    watch: {
ignored: ['!**/templates/**'],
    }
  }
});