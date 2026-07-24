import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/predict': 'https://two026-07-03-tvdi-ai.onrender.com',
      '/train': 'https://two026-07-03-tvdi-ai.onrender.com',
    },
  },
})
