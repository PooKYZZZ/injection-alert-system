import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SetupPasswordForm } from './SetupPasswordForm'
import { VerifyEmailForm } from './VerifyEmailForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('scanner-safe account action forms', () => {
  it('requires deliberate matching password submission and does not auto-login', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    render(<SetupPasswordForm token="opaque-token-that-is-long-enough" />)

    fireEvent.change(screen.getByLabelText('New password'), {
      target: { value: 'correct horse battery staple' },
    })
    fireEvent.change(screen.getByLabelText('Confirm password'), {
      target: { value: 'different password phrase' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Set password' }))
    expect(fetchMock).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Confirm password'), {
      target: { value: 'correct horse battery staple' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Set password' }))
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/setup-password',
      expect.objectContaining({ method: 'POST' })
    )
    expect(screen.queryByText(/dashboard/i)).not.toBeInTheDocument()
  })

  it('activates a managed email only after explicit confirmation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    render(<VerifyEmailForm token="opaque-token-that-is-long-enough" />)

    expect(fetchMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Verify email' }))
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/verify-email',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
