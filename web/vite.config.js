import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/treasury/',
  server: {
    port: 3000,
    proxy: {
      '/treasury/api': {
        target: 'http://localhost:8100',
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
