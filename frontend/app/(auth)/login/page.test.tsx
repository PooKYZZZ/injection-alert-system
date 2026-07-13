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

vi.mock('./actions', () => ({
  loginAction: vi.fn(),
}))

const mockedLoginAction = vi.mocked(loginAction)

afterEach(() => {
  vi.clearAllMocks()
  cleanup()
})

describe('LoginPage', () => {
  it('renders identifier and password fields without a role selector', () => {
    render(<LoginPage />)

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

    render(<LoginPage />)

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

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Unable to sign in right now')).toBeInTheDocument()
  })

  it('button is re-enabled after thrown non-redirect error', async () => {
    const user = userEvent.setup()
    mockedLoginAction.mockRejectedValue(new Error('Unexpected failure'))

    render(<LoginPage />)

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

    render(<LoginPage />)

    await user.type(screen.getByLabelText('Email or username'), 'analyst@example.test')
    await user.type(screen.getByLabelText('Password'), 'pw')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/dashboard')
    })
  })
})
