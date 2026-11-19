import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// In dev the SPA talks to the API through this proxy, so the same relative
// "/api" and "/ws" paths work in `npm run dev` and behind nginx in production.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/ws': { target: apiTarget, ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
