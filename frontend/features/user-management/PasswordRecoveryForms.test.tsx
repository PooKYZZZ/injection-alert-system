import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ForgotPasswordForm } from './ForgotPasswordForm'
import { ResetPasswordForm } from './ResetPasswordForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('password recovery forms', () => {
  it('uses generic forgot-password copy', () => {
    render(<ForgotPasswordForm />)
    expect(screen.getByRole('heading', { name: /forgot password/i })).toBeInTheDocument()
    expect(screen.getByText('Account recovery')).toBeInTheDocument()
    expect(screen.getByText(/if the account is eligible/i)).toBeInTheDocument()
  })

  it('does not auto-login after reset', () => {
    render(<ResetPasswordForm token={'a'.repeat(43)} />)
    expect(screen.getByText(/will not be signed in automatically/i)).toBeInTheDocument()
  })

  it('submits forgot-password as a labeled form and keeps the generic response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    render(<ForgotPasswordForm />)

    const form = screen.getByRole('form', { name: /forgot password/i })
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'analyst@example.test' } })
    fireEvent.submit(form)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/forgot-password',
      expect.objectContaining({ method: 'POST' }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent(/if the account is eligible/i)
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
