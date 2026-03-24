import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('next-auth', () => ({
  AuthError: class AuthError extends Error {},
}))

import LoginPage from './page'
import { loginAction } from './actions'

vi.mock('./actions', () => ({
  loginAction: vi.fn(),
}))

const mockedLoginAction = vi.mocked(loginAction)

afterEach(() => {
  vi.clearAllMocks()
  cleanup()
})

function captureNodeUnhandledRejections() {
  const reasons: unknown[] = []
  const handler = (reason: unknown) => {
    reasons.push(reason)
  }

  process.on('unhandledRejection', handler)

  return {
    reasons,
    stop: () => process.off('unhandledRejection', handler),
  }
}

describe('LoginPage', () => {
  it('renders password label linked to input via htmlFor/id', () => {
    render(<LoginPage />)

    const passwordInput = screen.getByLabelText('Password')
    expect(passwordInput).toBeInTheDocument()
    expect(passwordInput).toHaveAttribute('id', 'password')
  })

  it('shows incorrect password message on invalid credentials', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: false, code: 'INVALID_CREDENTIALS' })

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Incorrect password')).toBeInTheDocument()
  })

  it('shows fallback message on unexpected sign-in failure', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: false, code: 'SERVER_ERROR' })

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Unable to sign in right now')).toBeInTheDocument()
  })

  it('button is re-enabled after thrown non-redirect error', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockRejectedValue(new Error('Unexpected failure'))

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Password'), 'pw')
    const button = screen.getByRole('button', { name: 'Sign in' })
    await user.click(button)

    expect(await screen.findByText('Unable to sign in right now')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sign in' })).not.toBeDisabled()
    })
  })

  it('does not swallow NEXT_REDIRECT error', async () => {
    const user = userEvent.setup()
    const tracker = captureNodeUnhandledRejections()
    mockedLoginAction.mockRejectedValue(new Error('NEXT_REDIRECT'))

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => {
      expect(
        tracker.reasons.some(
          (reason) => reason instanceof Error && reason.message === 'NEXT_REDIRECT'
        )
      ).toBe(true)
    })

    expect(screen.queryByText('Incorrect password')).not.toBeInTheDocument()

    tracker.stop()
  })
})
