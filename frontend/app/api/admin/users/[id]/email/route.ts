import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireRecentTotp } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  accountErrorResponse,
  accountManagementEnabled,
  featureDisabledResponse,
  requireTrustedOrigin,
} from '@/lib/server/db/account-route-response'
import { requestManagedEmailChange } from '@/lib/server/db/account-management'

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  if (!accountManagementEnabled()) return featureDisabledResponse()
  const session = await auth()
  const authorization = await requireRecentTotp(
    session,
    PERMISSIONS.ACCOUNTS_MANAGE
  )
  if (!authorization.ok) return authorization.response
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  try {
    const { id } = await params
    await requestManagedEmailChange(session!.user.id, id, await request.json())
    return NextResponse.json({ status: 'verification_sent' })
  } catch (error) {
    return accountErrorResponse(error)
  }
}
