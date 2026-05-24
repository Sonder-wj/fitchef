import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/workout': 'http://localhost:8000',
      '/body-metric': 'http://localhost:8000',
      '/diet-meal': 'http://localhost:8000',
      '/food': 'http://localhost:8000',
    }
  }
})
