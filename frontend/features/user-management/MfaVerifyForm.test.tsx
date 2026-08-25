import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MfaVerifyForm } from './MfaVerifyForm'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MfaVerifyForm', () => {
  it('uses a restrained CyberTrace second-factor shell', () => {
    render(<MfaVerifyForm />)

    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByText('CyberTrace')).toBeInTheDocument()
    expect(screen.getByText('Second factor')).toBeInTheDocument()
    expect(screen.getByText('2 of 2')).toBeInTheDocument()
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(screen.queryByText(/quiet checkpoint|protected workspace|challenge is bound/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/backup code|recovery/i)).not.toBeInTheDocument()
  })

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

  it('keeps a recoverable code available and selects it for immediate replacement', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: { code: 'INVALID_CODE', message: 'That authenticator code is invalid. Try again.' } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaVerifyForm />)

    const input = screen.getByRole('textbox', { name: 'Authenticator code' }) as HTMLInputElement
    fireEvent.change(input, { target: { value: '123456' } })
    fireEvent.submit(screen.getByRole('form', { name: /verify your authenticator/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Try again.')
    expect(input).toHaveValue('123456')
    expect(document.activeElement).toBe(input)
    expect(input.selectionStart).toBe(0)
    expect(input.selectionEnd).toBe(6)
  })

  it('replaces the OTP form with a terminal restart state', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        error: {
          code: 'MFA_CHALLENGE_EXPIRED',
          message: 'This sign-in challenge has expired. Start sign-in again.',
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaVerifyForm />)

    const input = screen.getByRole('textbox', { name: 'Authenticator code' })
    fireEvent.change(input, { target: { value: '123456' } })
    fireEvent.submit(screen.getByRole('form', { name: /verify your authenticator/i }))

    expect(await screen.findByRole('heading', { name: 'Start sign-in again' })).toBeInTheDocument()
    expect(screen.getByText('This sign-in challenge has expired. Start sign-in again.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Return to sign in' })).toHaveAttribute('href', '/login')
    expect(screen.queryByRole('textbox', { name: 'Authenticator code' })).not.toBeInTheDocument()
  })

  it('keeps verification single-flight when the form is submitted twice', async () => {
    let resolveResponse: ((response: Response) => void) | undefined
    const fetchMock = vi.fn().mockImplementation(() => new Promise<Response>((resolve) => {
      resolveResponse = resolve
    }))
    vi.stubGlobal('fetch', fetchMock)
    render(<MfaVerifyForm />)

    const input = screen.getByRole('textbox', { name: 'Authenticator code' })
    const form = screen.getByRole('form', { name: /verify your authenticator/i })
    fireEvent.change(input, { target: { value: '123456' } })
    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Verifying…' })).toBeDisabled()

    resolveResponse?.({
      ok: false,
      json: async () => ({ error: { code: 'INVALID_CODE', message: 'Try again.' } }),
    } as Response)
    expect(await screen.findByRole('alert')).toHaveTextContent('Try again.')
  })
})
