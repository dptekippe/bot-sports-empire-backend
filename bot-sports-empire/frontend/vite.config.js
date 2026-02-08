import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://bot-sports-empire-backend.onrender.com',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: 'wss://bot-sports-empire-backend.onrender.com',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  }
})