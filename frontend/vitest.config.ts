import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./setupTests.ts'],
    // Required: login page tests deliberately rethrow NEXT_REDIRECT as an
    // unhandled rejection to verify the error propagates correctly.
    dangerouslyIgnoreUnhandledErrors: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      components: path.resolve(__dirname, './components'),
      features: path.resolve(__dirname, './features'),
      lib: path.resolve(__dirname, './lib'),
      store: path.resolve(__dirname, './store'),
    },
  },
})
