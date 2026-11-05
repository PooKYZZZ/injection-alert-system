'use server'

import { signIn } from '@/auth'
import { CredentialsSignin } from 'next-auth'

export type LoginResult =
  | { ok: true }
  | {
      ok: false
      code: 'INVALID_CREDENTIALS' | 'VERIFICATION_REQUIRED' | 'SERVER_ERROR'
    }

const LOGIN_REDIRECT_TO = '/dashboard'

export async function loginAction(
  identifier: string,
  password: string,
  turnstileToken?: string
): Promise<LoginResult> {
  try {
    await signIn('credentials', {
      identifier,
      password,
      ...(turnstileToken ? { turnstile_token: turnstileToken } : {}),
      redirect: false,
      redirectTo: LOGIN_REDIRECT_TO,
    })

    return { ok: true }
  } catch (error) {
    if (error instanceof CredentialsSignin) {
      if (error.code === 'verification_required') {
        return { ok: false, code: 'VERIFICATION_REQUIRED' }
      }
      return { ok: false, code: 'INVALID_CREDENTIALS' }
    }

    console.error('Login failed unexpectedly', {
      code: 'AUTH_UNEXPECTED',
      errorName: error instanceof Error ? error.name : 'UnknownError',
    })
    return { ok: false, code: 'SERVER_ERROR' }
  }
}
