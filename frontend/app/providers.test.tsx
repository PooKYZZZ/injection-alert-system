import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { Providers } from './providers'

vi.mock('@/components/SignInToast', () => ({
  __esModule: true,
  SignInToastProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  default: () => <div data-testid="sign-in-toast" />,
}))

describe('Providers', () => {
  afterEach(() => {
    vi.restoreAllMocks()
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
