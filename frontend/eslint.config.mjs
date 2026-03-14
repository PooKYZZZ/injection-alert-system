import js from '@eslint/js'
import { FlatCompat } from '@eslint/eslintrc'

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
  recommendedConfig: js.configs.recommended,
})

const eslintConfig = [
  {
    ignores: ['.next/**', 'coverage/**', 'node_modules/**'],
  },
  ...compat.config({
    extends: ['next/core-web-vitals'],
  }),
]

export default eslintConfig
