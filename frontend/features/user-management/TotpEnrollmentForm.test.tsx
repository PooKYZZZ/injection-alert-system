import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TotpEnrollmentForm } from './TotpEnrollmentForm'

describe('TotpEnrollmentForm', () => {
  afterEach(() => {
    cleanup()
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
})
