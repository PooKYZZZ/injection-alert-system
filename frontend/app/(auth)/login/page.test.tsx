import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('next-auth', () => ({
  AuthError: class AuthError extends Error {},
}))

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock }),
}))

import LoginPage from './page'
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
  cleanup()
})

describe('LoginPage', () => {
  it('renders identifier and password fields without a role selector', () => {
    renderLogin()

    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText('CyberTrace')).toBeInTheDocument()
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

  it('shows fallback message on unexpected sign-in failure', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockResolvedValue({ ok: false, code: 'SERVER_ERROR' })

    renderLogin()

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Unable to sign in right now')).toBeInTheDocument()
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
