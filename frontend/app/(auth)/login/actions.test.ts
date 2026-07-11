import { beforeEach, describe, expect, it, vi } from 'vitest'

const { signInMock } = vi.hoisted(() => ({
  signInMock: vi.fn(),
}))

vi.mock('@/auth', () => ({
  signIn: signInMock,
}))

vi.mock('next-auth', () => ({
  AuthError: class AuthError extends Error {
    type: string

    constructor(type: string) {
      super(type)
      this.type = type
    }
  },
}))

import { AuthError } from 'next-auth'
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

  it('returns one generic result for invalid credentials', async () => {
    signInMock.mockRejectedValue(new AuthError('CredentialsSignin'))

    await expect(loginAction('missing@example.test', 'wrong')).resolves.toEqual({
      ok: false,
      code: 'INVALID_CREDENTIALS',
    })
  })

  it('returns a safe server error for unexpected Auth.js failures', async () => {
    signInMock.mockRejectedValue(new Error('database detail must not escape'))

    await expect(
      loginAction('analyst@example.test', 'password')
    ).resolves.toEqual({ ok: false, code: 'SERVER_ERROR' })
  })
})
