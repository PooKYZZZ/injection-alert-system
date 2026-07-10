import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireRecentTotpAdmin } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  accountErrorResponse,
  accountManagementEnabled,
  featureDisabledResponse,
  requireTrustedOrigin,
} from '@/lib/server/db/account-route-response'
import { setManagedAccountEnabled } from '@/lib/server/db/account-management'

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
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
    const { id } = await params
    await setManagedAccountEnabled(session!.user.id, id, await request.json())
    return NextResponse.json({ status: 'account_status_changed' })
  } catch (error) {
    return accountErrorResponse(error)
  }
}
