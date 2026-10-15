import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TotpEnrollmentForm } from './TotpEnrollmentForm'

describe('TotpEnrollmentForm', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('starts with an explicit enrollment action and no secret rendered', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<TotpEnrollmentForm />)
    expect(screen.getByRole('button', { name: /start authenticator setup/i })).toBeInTheDocument()
    expect(screen.queryByText('JBSWY3DPEHPK3PXP')).not.toBeInTheDocument()
  })

  it('uses an accessible OTP form after enrollment begins', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        factor_id: 'factor-1',
        manual_key: 'MANUAL-KEY',
        provisioning_uri: 'otpauth://totp/CyberTrace:test@example.test?secret=ABC',
        expires_at: '2026-08-26T00:00:00Z',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<TotpEnrollmentForm />)

    fireEvent.click(screen.getByRole('button', { name: /start authenticator setup/i }))

    const input = await screen.findByRole('textbox', { name: 'Enter the six-digit code' })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/auth/mfa/enroll', { method: 'POST' }))
    expect(input).toHaveAttribute('autocomplete', 'one-time-code')
    expect(input).toHaveAttribute('inputmode', 'numeric')
    expect(input).toHaveAttribute('pattern', '\\d{6}')
    expect(screen.getByRole('form', { name: /verify authenticator/i })).toBeInTheDocument()
  })

  it('copies and downloads the displayed backup codes without another request', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          factor_id: 'factor-1',
          manual_key: 'MANUAL-KEY',
          provisioning_uri: 'otpauth://totp/CyberTrace:test@example.test?secret=ABC',
          expires_at: '2026-08-26T00:00:00Z',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ backup_codes: ['BACKUP-ONE', 'BACKUP-TWO'] }),
      })
    const writeText = vi.fn().mockResolvedValue(undefined)
    const createObjectURL = vi.fn().mockReturnValue('blob:backup-codes')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    render(<TotpEnrollmentForm />)

    fireEvent.click(screen.getByRole('button', { name: /start authenticator setup/i }))
    const input = await screen.findByRole('textbox', { name: 'Enter the six-digit code' })
    fireEvent.change(input, { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: /verify authenticator/i }))

    await screen.findByRole('heading', { name: 'Save your backup codes' })
    fireEvent.click(screen.getByRole('button', { name: 'Copy backup codes' }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('BACKUP-ONE\nBACKUP-TWO'))
    expect(fetchMock).toHaveBeenCalledTimes(2)

    fireEvent.click(screen.getByRole('button', { name: 'Download backup codes' }))

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:backup-codes')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
