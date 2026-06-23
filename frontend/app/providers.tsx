'use client'

import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import SignInToast, { SignInToastProvider } from '@/components/SignInToast'

type Theme = 'light' | 'dark'
type ThemePreference = Theme | 'system'

const THEME_STORAGE_KEY = 'ias-theme'
const THEME_MEDIA_QUERY = '(prefers-color-scheme: dark)'
const REDUCED_MOTION_MEDIA_QUERY = '(prefers-reduced-motion: reduce)'
const THEME_TRANSITION_CLASS = 'theme-transitioning'
const THEME_TRANSITION_DURATION_MS = 145

interface ThemeContextValue {
  theme: Theme
  themePreference: ThemePreference
  setThemePreference: (next: ThemePreference) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function getSystemTheme(): Theme {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return 'dark'
  }

  return window.matchMedia(THEME_MEDIA_QUERY).matches ? 'dark' : 'light'
}

function getStoredThemePreference(): ThemePreference {
  if (typeof window === 'undefined') {
    return 'system'
  }

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
  return storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : 'system'
}

function applyThemeToRoot(theme: Theme) {
  if (typeof document === 'undefined') {
    return
  }

  const root = document.documentElement

  if (root.getAttribute('data-theme') !== theme) {
    root.setAttribute('data-theme', theme)
  }

  if (root.style.colorScheme !== theme) {
    root.style.colorScheme = theme
  }
}

export function useTheme() {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error('useTheme must be used within Providers')
  }

  return context
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 2 * 60 * 1000,
          },
        },
      }),
  )

  const [themePreference, setThemePreference] = useState<ThemePreference>(() => getStoredThemePreference())
  const [systemTheme, setSystemTheme] = useState<Theme>(() => getSystemTheme())
  const transitionTimeoutRef = useRef<number | null>(null)

  const theme = themePreference === 'system' ? systemTheme : themePreference
  applyThemeToRoot(theme)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (themePreference === 'system') {
      window.localStorage.removeItem(THEME_STORAGE_KEY)
      return
    }

    window.localStorage.setItem(THEME_STORAGE_KEY, themePreference)
  }, [themePreference])

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }

    const mediaQueryList = window.matchMedia(THEME_MEDIA_QUERY)

    const handleChange = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? 'dark' : 'light')
    }

    if (typeof mediaQueryList.addEventListener === 'function') {
      mediaQueryList.addEventListener('change', handleChange)
      return () => mediaQueryList.removeEventListener('change', handleChange)
    }

    mediaQueryList.addListener(handleChange)
    return () => mediaQueryList.removeListener(handleChange)
  }, [])

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && transitionTimeoutRef.current !== null) {
        window.clearTimeout(transitionTimeoutRef.current)
      }

      if (typeof document !== 'undefined') {
        document.documentElement.classList.remove(THEME_TRANSITION_CLASS)
      }
    }
  }, [])

  const themeContextValue = useMemo<ThemeContextValue>(
    () => ({
      theme,
      themePreference,
      setThemePreference,
      toggleTheme: () => {
        if (typeof document !== 'undefined' && typeof window !== 'undefined') {
          const prefersReducedMotion =
            typeof window.matchMedia === 'function' && window.matchMedia(REDUCED_MOTION_MEDIA_QUERY).matches

          const root = document.documentElement

          if (!prefersReducedMotion) {
            root.classList.add(THEME_TRANSITION_CLASS)

            if (transitionTimeoutRef.current !== null) {
              window.clearTimeout(transitionTimeoutRef.current)
            }

            transitionTimeoutRef.current = window.setTimeout(() => {
              root.classList.remove(THEME_TRANSITION_CLASS)
              transitionTimeoutRef.current = null
            }, THEME_TRANSITION_DURATION_MS)
          }
        }

        setThemePreference((previousPreference) => {
          const resolvedTheme = previousPreference === 'system' ? systemTheme : previousPreference
          return resolvedTheme === 'dark' ? 'light' : 'dark'
        })
      },
    }),
    [theme, themePreference, systemTheme],
  )

  return (
    <ThemeContext.Provider value={themeContextValue}>
      <QueryClientProvider client={queryClient}>
        <SignInToastProvider>
          {children}
          <SignInToast />
        </SignInToastProvider>
        {process.env.NODE_ENV === 'development' && <ReactQueryDevtools />}
      </QueryClientProvider>
    </ThemeContext.Provider>
  )
}
