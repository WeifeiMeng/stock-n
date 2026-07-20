import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/stock-n': 'http://localhost:8000',
      '/stock-position': 'http://localhost:8000',
      '/calculate-price': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
});
