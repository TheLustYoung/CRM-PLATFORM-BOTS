import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {proxy: {'/api': 'http://127.0.0.1:8000'}},
  build: {
    rollupOptions: {
      output: {
        // Translations (11 languages) and React change rarely: separate files stay cached across dashboard updates.
        manualChunks(id) {
          if (id.includes('/services/locales/') || id.includes('i18n')) return 'i18n';
          if (id.includes('node_modules')) return 'vendor';
        },
      },
    },
  },
});
