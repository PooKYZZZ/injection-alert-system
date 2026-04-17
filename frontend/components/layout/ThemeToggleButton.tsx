'use client'

import { useEffect, useState } from 'react'
import { useTheme } from '@/components/theme/ThemeProvider'

export function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme()
  const isDarkTheme = theme === 'dark'
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setIsMounted(true)
    })

    return () => window.cancelAnimationFrame(frame)
  }, [])

  const nextTheme = isDarkTheme ? 'light' : 'dark'
  const buttonLabel = isMounted ? `${nextTheme === 'light' ? 'Light' : 'Dark'} Theme` : 'Theme'
  const ariaLabel = isMounted ? `Switch to ${nextTheme} theme` : 'Toggle theme'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={ariaLabel}
      title={ariaLabel}
      className="inline-flex h-[38px] items-center gap-2 rounded-md border border-border-light bg-bg-elevated px-3 text-sm font-medium text-text-primary transition-colors hover:bg-bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel"
    >
      <span aria-hidden="true" className="text-base leading-none">
        {isMounted ? (isDarkTheme ? '☀' : '☾') : '◌'}
      </span>
      <span>{buttonLabel}</span>
    </button>
  )
}
