'use server'

import { signIn } from '@/auth'
import { AuthError } from 'next-auth'

export type LoginResult =
  | { ok: true }
  | { ok: false; code: 'INVALID_CREDENTIALS' | 'SERVER_ERROR' }

const LOGIN_REDIRECT_TO = '/dashboard'

export async function loginAction(password: string): Promise<LoginResult> {
  try {
    await signIn('credentials', {
      password,
      // This action intentionally redirects only to the dashboard.
      redirectTo: LOGIN_REDIRECT_TO
    })

    return { ok: true }
  } catch (error) {
    if (error instanceof Error && error.message === 'NEXT_REDIRECT') {
      throw error
    }

    if (error instanceof AuthError && error.type === 'CredentialsSignin') {
      return { ok: false, code: 'INVALID_CREDENTIALS' }
    }

    console.error('Login failed unexpectedly', error)
    return { ok: false, code: 'SERVER_ERROR' }
  }
}
