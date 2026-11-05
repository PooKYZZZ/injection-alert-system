import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('next-auth', () => ({
  AuthError: class AuthError extends Error {},
}))

vi.mock('@/components/auth/TurnstileWidget', () => ({
  TurnstileWidget: ({ resetKey, onToken }: {
    resetKey: number
    onToken: (token: string) => void
  }) => (
    <div role="group" aria-label="Security verification">
      <button
        type="button"
        onClick={() => onToken(`single-use-token-${resetKey}`)}
      >
        Complete security verification
      </button>
    </div>
  ),
}))

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock }),
}))

import LoginPage, { dynamic } from './page'
import { loginAction } from './actions'
import { AuthShell } from '@/components/auth/AuthShell'

vi.mock('./actions', () => ({
  loginAction: vi.fn(),
}))

const mockedLoginAction = vi.mocked(loginAction)

function renderLogin() {
  return render(
    <AuthShell>
      <LoginPage />
    </AuthShell>
  )
}

afterEach(() => {
  vi.clearAllMocks()
  vi.unstubAllEnvs()
  cleanup()
})

describe('LoginPage', () => {
  it('renders dynamically so cached login documents cannot retain an old action ID', () => {
    expect(dynamic).toBe('force-dynamic')
  })

  it('renders identifier and password fields without a role selector', () => {
    renderLogin()

    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText('CyberTrace')).toBeInTheDocument()
    expect(screen.getByText('Secure workspace')).toBeInTheDocument()
    expect(screen.getByText('Use your CyberTrace credentials to continue.')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'background' })).not.toBeInTheDocument()
    expect(screen.queryByText(/advanced WAF|real-time attack monitoring/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Password required')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Forgot password?' })).toHaveAttribute('href', '/forgot-password')

    const identifierInput = screen.getByLabelText('Email or username')
    const passwordInput = screen.getByLabelText('Password')
    expect(identifierInput).toHaveAttribute('id', 'identifier')
    expect(passwordInput).toBeInTheDocument()
    expect(passwordInput).toHaveAttribute('id', 'password')
    expect(screen.queryByLabelText('Role')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toHaveClass('w-full')
  })

  it('shows the generic invalid-login message without account-existence leakage', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: false, code: 'INVALID_CREDENTIALS' })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'unknown@example.test')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByText('Invalid username or password.')
    ).toBeInTheDocument()
    expect(screen.queryByText(/account.*not found/i)).not.toBeInTheDocument()
  })

  it('shows the conditional challenge only after the server requires it', async () => {
    const user = userEvent.setup()
    vi.stubEnv('NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY', 'public-test-site-key')
    mockedLoginAction.mockResolvedValue({
      ok: false,
      code: 'VERIFICATION_REQUIRED',
    })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    expect(screen.queryByRole('group', { name: 'Security verification' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByRole('group', { name: 'Security verification' })
    ).toBeInTheDocument()
    expect(
      screen.getByText('Please complete the security verification, then try again.')
    ).toHaveAttribute('role', 'alert')
  })

  it('submits a fresh widget token and discards it after the attempt', async () => {
    const user = userEvent.setup()
    vi.stubEnv('NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY', 'public-test-site-key')
    mockedLoginAction
      .mockResolvedValueOnce({ ok: false, code: 'VERIFICATION_REQUIRED' })
      .mockResolvedValueOnce({ ok: false, code: 'VERIFICATION_REQUIRED' })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByRole('group', { name: 'Security verification' })
    await user.click(
      screen.getByRole('button', { name: 'Complete security verification' })
    )
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(mockedLoginAction).toHaveBeenNthCalledWith(
      2,
      'analyst@example.test',
      'wrong-password',
      'single-use-token-0'
    )
    expect(
      await screen.findByRole('group', { name: 'Security verification' })
    ).toBeInTheDocument()
  })

  it('shows fallback message on unexpected sign-in failure', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: false, code: 'SERVER_ERROR' })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByText(
        'Sign-in service is temporarily unavailable. Please try again shortly.'
      )
    ).toBeInTheDocument()
  })

  it('button is re-enabled after thrown non-redirect error', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockRejectedValue(new Error('Unexpected failure'))

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    const button = screen.getByRole('button', { name: 'Sign in' })
    await user.click(button)

    expect(await screen.findByText('Unable to sign in right now')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sign in' })).not.toBeDisabled()
    })
  })

  it('navigates explicitly after Auth.js completes without a framework redirect', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: true })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/dashboard')
    })
  })
})
