import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import {
  requireMfaPermission,
  requireRecentTotpAdmin,
} from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  accountErrorResponse,
  accountManagementEnabled,
  featureDisabledResponse,
  requireTrustedOrigin,
} from '@/lib/server/db/account-route-response'
import {
  createManagedAccount,
  listManagedAccounts,
} from '@/lib/server/db/account-management'

export async function GET(): Promise<Response> {
  if (!accountManagementEnabled()) return featureDisabledResponse()
  const session = await auth()
  const authorization = await requireMfaPermission(
    session,
    PERMISSIONS.ACCOUNTS_READ
  )
  if (!authorization.ok) return authorization.response
  try {
    return NextResponse.json({ accounts: await listManagedAccounts() })
  } catch (error) {
    return accountErrorResponse(error)
  }
}

export async function POST(request: Request): Promise<Response> {
  if (!accountManagementEnabled()) return featureDisabledResponse()
  const session = await auth()
  const authorization = await requireRecentTotpAdmin(
    session,
    PERMISSIONS.ACCOUNTS_MANAGE
  )
  if (!authorization.ok) return authorization.response
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  try {
    const input = await request.json()
    const result = await createManagedAccount(session!.user.id, input)
    return NextResponse.json(result, { status: 201 })
  } catch (error) {
    return accountErrorResponse(error)
  }
}
