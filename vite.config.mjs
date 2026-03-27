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
        // FORZAMOS LOS DOS ARCHIVOS COMO ENTRADA
        input: {
          main: path.resolve(__dirname, 'static/src/main.js'),
          styles: path.resolve(__dirname, 'static/src/input.css') 
        },
        output: {
          entryFileNames: `assets/[name].js`,
          chunkFileNames: `assets/[name].js`,
          assetFileNames: `assets/[name].[ext]` // Esto asegurará que sea main.css
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