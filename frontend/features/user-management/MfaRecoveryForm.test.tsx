import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MfaRecoveryForm } from './MfaRecoveryForm'

describe('MfaRecoveryForm', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('offers backup-code and verified-email recovery without dashboard claims', () => {
    render(<MfaRecoveryForm />)
    expect(screen.getByRole('heading', { name: /recover authenticator access/i })).toBeInTheDocument()
    expect(screen.getByRole('form', { name: /backup code/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Use backup code' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Email me a recovery code' })).toBeInTheDocument()
    expect(screen.queryByText(/dashboard/i)).toBeInTheDocument()
  })

  it('switches to email recovery after the existing request succeeds and keeps method switching available', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'sent' }) })
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaRecoveryForm />)

    fireEvent.click(screen.getByRole('button', { name: 'Email me a recovery code' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/mfa/recovery/email/request',
      expect.objectContaining({ method: 'POST' }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent(/a code has been sent/i)
    expect(screen.getByRole('textbox', { name: 'Six-digit recovery code' })).toHaveAttribute('autocomplete', 'one-time-code')
    expect(screen.getByRole('button', { name: 'Use a backup code' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Email me a new recovery code' })).toBeInTheDocument()
  })

  it('associates a backup-code failure with the recovery field', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: { message: 'That backup code is invalid.' } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaRecoveryForm />)

    const input = screen.getByRole('textbox', { name: 'Backup code' })
    fireEvent.change(input, { target: { value: 'ABCD-1234' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Backup code recovery' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/backup code is invalid/i)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'backup-code-help mfa-recovery-error')
  })
})
