import { beforeEach, describe, expect, it, vi } from 'vitest'

const { signInMock } = vi.hoisted(() => ({
  signInMock: vi.fn(),
}))

vi.mock('@/auth', () => ({
  signIn: signInMock,
}))

vi.mock('next-auth', () => ({
  CredentialsSignin: class CredentialsSignin extends Error {
    type = 'CredentialsSignin'
    code = 'credentials'
  },
}))

import { CredentialsSignin } from 'next-auth'
import { loginAction } from './actions'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('loginAction', () => {
  it('submits identifier and password to Auth.js', async () => {
    signInMock.mockResolvedValue(undefined)

    await expect(
      loginAction('analyst@example.test', 'password')
    ).resolves.toEqual({ ok: true })
    expect(signInMock).toHaveBeenCalledWith('credentials', {
      identifier: 'analyst@example.test',
      password: 'password',
      redirect: false,
      redirectTo: '/dashboard',
    })
  })

  it('forwards only the submitted token as a password credential', async () => {
    signInMock.mockResolvedValue(undefined)

    await expect(
      loginAction('analyst@example.test', 'password', 'single-use-token')
    ).resolves.toEqual({ ok: true })
    expect(signInMock).toHaveBeenCalledWith('credentials', {
      identifier: 'analyst@example.test',
      password: 'password',
      turnstile_token: 'single-use-token',
      redirect: false,
      redirectTo: '/dashboard',
    })
  })

  it('returns one generic result for invalid credentials', async () => {
    signInMock.mockRejectedValue(new CredentialsSignin())

    await expect(loginAction('missing@example.test', 'wrong')).resolves.toEqual({
      ok: false,
      code: 'INVALID_CREDENTIALS',
    })
  })

  it('returns a generic challenge-required state from Auth.js', async () => {
    const error = new CredentialsSignin()
    error.code = 'verification_required'
    signInMock.mockRejectedValue(error)

    await expect(
      loginAction('analyst@example.test', 'password')
    ).resolves.toEqual({ ok: false, code: 'VERIFICATION_REQUIRED' })
  })

  it('returns a safe server error for unexpected Auth.js failures', async () => {
    signInMock.mockRejectedValue(new Error('database detail must not escape'))

    await expect(
      loginAction('analyst@example.test', 'password')
    ).resolves.toEqual({ ok: false, code: 'SERVER_ERROR' })
  })
})
