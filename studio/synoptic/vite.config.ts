import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Internal-audit fix: everything used to land in one ~690kB
        // chunk (Vite's own build warned about it). React/ReactDOM and
        // Konva/react-konva rarely change between our own releases and
        // are the bulk of that weight, so splitting them into their own
        // chunk lets browsers cache them across app updates instead of
        // re-downloading them on every deploy.
        manualChunks(id: string) {
          if (id.includes('node_modules/react') || id.includes('node_modules/scheduler')) return 'vendor';
          if (id.includes('node_modules/konva') || id.includes('node_modules/react-konva')) return 'konva';
        },
      },
    },
  },
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: [
        'src/main.tsx',
        'src/types/**',
        '**/*.d.ts',
        'src/tests/**',
      ],
    },
  },
})
