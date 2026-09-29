import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Dev: the backend runs on :8000 (python -m resense_web --port 8000 --reload); HTTP and the live
// WebSocket under /api are proxied to it. `vite preview` proxies the same way.
// RESENSE_API_TARGET overrides the backend (e.g. http://127.0.0.1:8101 for a second instance).
const apiTarget = process.env.RESENSE_API_TARGET ?? 'http://127.0.0.1:8000';
const proxy = {
  '/api': { target: apiTarget, changeOrigin: true, ws: true },
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
        // three stays in its own chunk, loaded only by the player and the 3D previews. roslib is not
        // a manual chunk: it has dynamic imports of its own, so a manual chunk would absorb Vite's
        // preload helper and the entry would preload all of roslib; as a plain dynamic import it
        // gets its own chunk anyway (api/rosbridge.ts, Прямой эфир only).
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('/three/')) return 'three';
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
