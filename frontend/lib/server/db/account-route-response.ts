import 'server-only'

import { NextResponse } from 'next/server'

import { AccountManagementError } from './account-management'

export function accountManagementEnabled(): boolean {
  return process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED === 'true'
}

export function mfaEnrollmentEnabled(): boolean {
  return process.env.AUTH_MFA_ENROLLMENT_ENABLED === 'true'
}

export function featureDisabledResponse(): Response {
  return NextResponse.json(
    { error: { code: 'NOT_FOUND', message: 'Not found.' } },
    { status: 404 }
  )
}

export function requireTrustedOrigin(request: Request): Response | null {
  const configuredOrigin = process.env.AUTH_APP_ORIGIN
  const requestOrigin = request.headers.get('origin')
  try {
    if (
      !configuredOrigin ||
      !requestOrigin ||
      new URL(configuredOrigin).origin !== configuredOrigin ||
      new URL(requestOrigin).origin !== requestOrigin ||
      requestOrigin !== configuredOrigin
    ) {
      throw new Error('Untrusted origin')
    }
    return null
  } catch {
    return NextResponse.json(
      { error: { code: 'FORBIDDEN', message: 'Forbidden.' } },
      { status: 403 }
    )
  }
}

export function accountErrorResponse(error: unknown): Response {
  if (error instanceof AccountManagementError) {
    const status =
      error.code === 'INVALID_REQUEST'
        ? 400
        : error.code === 'CONFLICT'
          ? 409
          : error.code === 'NOT_FOUND'
            ? 404
            : 503
    return NextResponse.json(
      {
        error: {
          code: error.code,
          message:
            status === 409
              ? 'An account with that value already exists.'
              : status === 503
                ? 'Account management is temporarily unavailable.'
                : 'The account request is invalid.',
        },
      },
      { status }
    )
  }
  return NextResponse.json(
    { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
    { status: 500 }
  )
}

export function publicTokenErrorResponse(): Response {
  return NextResponse.json(
    {
      error: {
        code: 'INVALID_OR_EXPIRED',
        message: 'This link is invalid or expired.',
      },
    },
    { status: 400 }
  )
}

function safeErrorCode(error: unknown): string | undefined {
  if (!(error instanceof Error)) return undefined
  if ('code' in error && typeof error.code === 'string') return error.code
  return error.message
}

export function totpErrorResponse(error: unknown): Response {
  const code = safeErrorCode(error)
  const status = code === 'INVALID_REQUEST' || code === 'INVALID_CODE' || code === 'LOCKED' || code === 'EXPIRED' ? 400 : 503
  return NextResponse.json(
    {
      error: {
        code: code === 'INVALID_CODE' || code === 'LOCKED' || code === 'EXPIRED' ? 'INVALID_CODE' : 'MFA_UNAVAILABLE',
        message:
          code === 'INVALID_CODE' || code === 'LOCKED' || code === 'EXPIRED'
            ? 'That authenticator code is invalid or already used.'
            : status === 400
              ? 'The MFA request is invalid.'
              : 'MFA enrollment is temporarily unavailable.',
      },
    },
    { status }
  )
}

export function recoveryErrorResponse(error: unknown): Response {
  const code = safeErrorCode(error)
  const status = code === 'INVALID_CODE' || code === 'LOCKED' || code === 'EXPIRED' || code === 'COOLDOWN' ? 400 : 503
  return NextResponse.json(
    {
      error: {
        code: code === 'COOLDOWN' ? 'TRY_LATER' : 'RECOVERY_UNAVAILABLE',
        message:
          code === 'COOLDOWN'
            ? 'Please wait before requesting another recovery code.'
            : code === 'INVALID_CODE' || code === 'LOCKED' || code === 'EXPIRED'
              ? 'That recovery code is invalid or expired.'
              : 'Recovery is temporarily unavailable.',
      },
    },
    { status }
  )
}
