import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ForgotPasswordForm } from './ForgotPasswordForm'
import { ResetPasswordForm } from './ResetPasswordForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('password recovery forms', () => {
  it('explains the forgot-password request without promising delivery', () => {
    render(<ForgotPasswordForm />)
    expect(screen.getByRole('heading', { name: /forgot password/i })).toBeInTheDocument()
    expect(screen.getByText('Account recovery')).toBeInTheDocument()
    expect(screen.getByText(/request password reset instructions/i)).toBeInTheDocument()
  })

  it('does not auto-login after reset', () => {
    render(<ResetPasswordForm token={'a'.repeat(43)} />)
    expect(screen.getByText(/will not be signed in automatically/i)).toBeInTheDocument()
  })

  it('shows a success state when the server queues a reset for an eligible account', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'sent',
        message: 'Reset instructions were queued for this account. Check your inbox.',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<ForgotPasswordForm />)

    const form = screen.getByRole('form', { name: /forgot password/i })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'analyst@example.test' } })
    fireEvent.submit(form)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/forgot-password',
      expect.objectContaining({ method: 'POST' }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent(/reset instructions were queued for this account/i)
  })

  it('shows an error for an unknown account without showing success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        status: 'not_found',
        message: 'No eligible account was found for this email address.',
      }),
    }))
    render(<ForgotPasswordForm />)

    const input = screen.getByLabelText('Email address')
    fireEvent.change(input, { target: { value: 'unknown@example.test' } })
    fireEvent.submit(screen.getByRole('form', { name: /forgot password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no eligible account was found/i)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })

  it('shows a recoverable service error without clearing the entered email', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('network'))
    vi.stubGlobal('fetch', fetchMock)
    render(<ForgotPasswordForm />)

    const input = screen.getByLabelText('Email address')
    fireEvent.change(input, { target: { value: 'analyst@example.test' } })
    fireEvent.submit(screen.getByRole('form', { name: /forgot password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/unable to send/i)
    expect(input).toHaveValue('analyst@example.test')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'forgot-password-error')
  })

  it('treats a non-OK recovery response as a recoverable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    render(<ForgotPasswordForm />)

    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'analyst@example.test' } })
    fireEvent.submit(screen.getByRole('form', { name: /forgot password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/unable to send/i)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('associates reset-link errors with the password control', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 410 }))
    render(<ResetPasswordForm token={'a'.repeat(43)} />)

    const input = screen.getByLabelText('New password')
    fireEvent.change(input, { target: { value: 'a'.repeat(6) } })
    fireEvent.submit(screen.getByRole('form', { name: /set a new password/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid or expired/i)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'reset-password-error')
  })
})
