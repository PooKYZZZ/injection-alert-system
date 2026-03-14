import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  esbuild: {
    jsx: 'automatic',
  },
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
      features: path.resolve(__dirname, './features'),
      lib: path.resolve(__dirname, './lib'),
    },
  },
})
