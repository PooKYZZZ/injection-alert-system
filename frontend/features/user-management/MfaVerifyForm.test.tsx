import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MfaVerifyForm } from './MfaVerifyForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MfaVerifyForm', () => {
  it('requires a six-digit authenticator code', () => {
    render(<MfaVerifyForm />)
    expect(screen.getByRole('heading', { name: /verify your authenticator/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })

  it('uses an accessible semantic one-time-code form', () => {
    render(<MfaVerifyForm />)

    const form = screen.getByRole('form', { name: /verify your authenticator/i })
    const input = screen.getByRole('textbox', { name: 'Authenticator code' })

    expect(form).toBeInTheDocument()
    expect(input).toHaveAttribute('autocomplete', 'one-time-code')
    expect(input).toHaveAttribute('inputmode', 'numeric')
    expect(input).toBeRequired()
    expect(input).toHaveAttribute('pattern', '\\d{6}')
    expect(input).toHaveAttribute('aria-describedby', 'mfa-code-help')
  })

  it('submits with Enter and associates verification errors with the code field', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: { message: 'Code expired.' } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaVerifyForm />)

    const input = screen.getByRole('textbox', { name: 'Authenticator code' })
    const form = screen.getByRole('form', { name: /verify your authenticator/i })
    fireEvent.change(input, { target: { value: '123456' } })
    fireEvent.submit(form)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/mfa/verify',
      expect.objectContaining({ body: JSON.stringify({ code: '123456' }) }),
    ))
    expect(await screen.findByRole('alert')).toHaveTextContent('Code expired.')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'mfa-code-help mfa-code-error')
  })
})
