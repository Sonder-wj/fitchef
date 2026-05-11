import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/auth': 'http://backend:8000',
      '/chat': 'http://backend:8000',
      '/health': 'http://backend:8000',
    }
  }
})
