import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { Providers } from './providers'

vi.mock('@/components/SignInToast', () => ({
  __esModule: true,
  SignInToastProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  default: () => <div data-testid="sign-in-toast" />,
}))

describe('Providers', () => {
  const originalMatchMedia = window.matchMedia

  afterEach(() => {
    vi.restoreAllMocks()

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: originalMatchMedia,
    })

    window.localStorage.removeItem('cybertrace-theme')
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.removeProperty('color-scheme')
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

  it('applies light theme when system preference is light and no stored override exists', async () => {
    window.localStorage.removeItem('cybertrace-theme')

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === '(prefers-color-scheme: light)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    render(
      <Providers>
        <div>child</div>
      </Providers>
    )

    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe('light')
      expect(document.documentElement.style.colorScheme).toBe('light')
    })
  })
})
