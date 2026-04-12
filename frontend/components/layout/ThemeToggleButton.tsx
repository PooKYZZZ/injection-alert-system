'use client'

import { useTheme } from '@/components/theme/ThemeProvider'

export function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme()
  const isDarkTheme = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
      className="inline-flex h-[38px] items-center gap-2 rounded-md border border-border-light bg-bg-elevated px-3 text-sm font-medium text-text-primary transition-colors hover:bg-bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel"
    >
      <span aria-hidden="true" className="text-base leading-none">
        {isDarkTheme ? '☀' : '☾'}
      </span>
      <span>{isDarkTheme ? 'Light' : 'Dark'} Theme</span>
    </button>
  )
}