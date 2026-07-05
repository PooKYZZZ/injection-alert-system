import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { Providers, useTheme } from './providers'

vi.mock('@/components/SignInToast', () => ({
  __esModule: true,
  SignInToastProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  default: () => <div data-testid="sign-in-toast" />,
}))

describe('Providers', () => {
  const mockMatchMedia = ({
    matchesDark,
    prefersReducedMotion = false,
  }: {
    matchesDark: boolean
    prefersReducedMotion?: boolean
  }) => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches:
          query === '(prefers-color-scheme: dark)'
            ? matchesDark
            : query === '(prefers-reduced-motion: reduce)'
              ? prefersReducedMotion
              : false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  }

  function ThemeToggleHarness() {
    const { theme, toggleTheme } = useTheme()

    return (
      <div>
        <span data-testid="active-theme">{theme}</span>
        <button type="button" onClick={toggleTheme}>
          Toggle theme
        </button>
      </div>
    )
  }

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.restoreAllMocks()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.colorScheme = ''
    document.documentElement.classList.remove('theme-transitioning')
  })

  it('applies saved explicit theme to the root after render', () => {
    window.localStorage.setItem('ias-theme', 'light')
    mockMatchMedia({ matchesDark: true })

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('falls back safely when browser theme APIs throw', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn(() => {
        throw new Error('media query unavailable')
      }),
    })

    expect(() =>
      render(
        <Providers>
          <div>child</div>
        </Providers>
      )
    ).not.toThrow()
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })

  it('falls back to system preference when no explicit theme is saved', () => {
    mockMatchMedia({ matchesDark: true })

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('does not apply transition class during initial render', () => {
    mockMatchMedia({ matchesDark: true })

    render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    expect(document.documentElement).not.toHaveClass('theme-transitioning')
  })

  it('applies transition class only when the user explicitly toggles theme', () => {
    vi.useFakeTimers()
    mockMatchMedia({ matchesDark: true })

    render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    expect(document.documentElement).not.toHaveClass('theme-transitioning')

    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))

    expect(document.documentElement).toHaveClass('theme-transitioning')
    expect(screen.getByTestId('active-theme')).toHaveTextContent('light')

    vi.advanceTimersByTime(160)
    expect(document.documentElement).not.toHaveClass('theme-transitioning')
  })

  it('skips transition class when reduced-motion is enabled', () => {
    mockMatchMedia({ matchesDark: true, prefersReducedMotion: true })

    render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))

    expect(screen.getByTestId('active-theme')).toHaveTextContent('light')
    expect(document.documentElement).not.toHaveClass('theme-transitioning')
  })

  it('renders SignInToast and does not register action-retry-success listeners', () => {
    const addEventListenerSpy = vi.spyOn(window, 'addEventListener')

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    expect(screen.getByTestId('sign-in-toast')).toBeInTheDocument()

    const registeredEvents = addEventListenerSpy.mock.calls.map(([eventName]) => eventName)
    expect(registeredEvents).not.toContain('action-retry-success')
  })
})
