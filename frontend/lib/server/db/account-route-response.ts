import 'server-only'

import { NextResponse } from 'next/server'

import { AccountManagementError } from './account-management'

export function accountManagementEnabled(): boolean {
  return process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED === 'true'
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
