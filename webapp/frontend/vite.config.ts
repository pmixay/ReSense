import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Dev: the backend runs on :8000 (python -m resense_web --port 8000 --reload); HTTP and the live
// WebSocket under /api are proxied to it. `vite preview` proxies the same way.
const proxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2022',
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // three / roslib stay in their own chunks, loaded only by the pages that import them
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('/three/')) return 'three';
          if (id.includes('/roslib/')) return 'roslib';
          if (id.includes('/@tanstack/')) return 'query';
          if (/\/(react|react-dom|react-router|react-router-dom|scheduler|@remix-run)\//.test(id)) return 'react';
          return undefined;
        },
      },
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'node', // component tests opt into jsdom per file
    setupFiles: ['src/test/setup.ts'],
  },
});
