import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { Providers, useTheme } from './providers'

vi.mock('@/components/SignInToast', () => ({
  __esModule: true,
  SignInToastProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  default: () => <div data-testid="sign-in-toast" />,
}))

function mockMatchMedia(matchesDark: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-color-scheme: dark)' ? matchesDark : false,
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

function mockAnimationFrames() {
  let nextFrameId = 0
  const callbacks = new Map<number, FrameRequestCallback>()

  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
    const frameId = ++nextFrameId
    callbacks.set(frameId, callback)
    return frameId
  })
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((frameId) => {
    callbacks.delete(frameId)
  })

  return {
    flushFrame() {
      const currentCallbacks = [...callbacks.values()]
      callbacks.clear()
      currentCallbacks.forEach((callback) => callback(0))
    },
    pendingCount: () => callbacks.size,
  }
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

describe('Providers', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.colorScheme = ''
    document.documentElement.classList.remove('theme-switching')
  })

  it('applies saved explicit theme to the root after render', () => {
    window.localStorage.setItem('ias-theme', 'light')
    mockMatchMedia(true)

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(document.documentElement.style.colorScheme).toBe('light')
    expect(document.documentElement).not.toHaveClass('theme-switching')
  })

  it('falls back safely when browser theme APIs throw', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
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

  it('uses the system preference when no explicit theme is saved', () => {
    mockMatchMedia(true)

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')
    expect(document.documentElement).not.toHaveClass('theme-switching')
  })

  it('applies a theme switch immediately and suppresses transitions for one painted frame', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    const frames = mockAnimationFrames()

    render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Toggle theme' }))

    expect(screen.getByTestId('active-theme')).toHaveTextContent('light')
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(document.documentElement.style.colorScheme).toBe('light')
    expect(document.documentElement).toHaveClass('theme-switching')

    frames.flushFrame()
    expect(document.documentElement).toHaveClass('theme-switching')
    frames.flushFrame()
    expect(document.documentElement).not.toHaveClass('theme-switching')
  })

  it('keeps rapid back-to-back switches synchronized and replaces stale cleanup frames', () => {
    mockMatchMedia(true)
    const frames = mockAnimationFrames()

    render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    const toggle = screen.getByRole('button', { name: 'Toggle theme' })
    fireEvent.click(toggle)
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    fireEvent.click(toggle)

    expect(screen.getByTestId('active-theme')).toHaveTextContent('dark')
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(document.documentElement).toHaveClass('theme-switching')
    expect(frames.pendingCount()).toBe(1)

    frames.flushFrame()
    frames.flushFrame()
    expect(document.documentElement).not.toHaveClass('theme-switching')
  })

  it('cleans up the pending transition-suppression frame when providers unmount', () => {
    mockMatchMedia(true)
    const frames = mockAnimationFrames()
    const { unmount } = render(
      <Providers>
        <ThemeToggleHarness />
      </Providers>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Toggle theme' }))
    expect(document.documentElement).toHaveClass('theme-switching')
    unmount()

    expect(document.documentElement).not.toHaveClass('theme-switching')
    expect(frames.pendingCount()).toBe(0)
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
