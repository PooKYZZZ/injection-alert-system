import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth } from '@/auth'
import { requireRecentTotpAdmin } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { accountErrorResponse, accountManagementEnabled, featureDisabledResponse, requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { resetManagedAccountMfa } from '@/lib/server/db/password-recovery'

const requestSchema = z.object({ reason: z.string().trim().min(1).max(128) }).strict()

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }): Promise<Response> {
  if (!accountManagementEnabled()) return featureDisabledResponse()
  const session = await auth()
  const authorization = await requireRecentTotpAdmin(session, PERMISSIONS.ACCOUNTS_MANAGE)
  if (!authorization.ok) return authorization.response
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  try {
    const input = requestSchema.parse(await request.json())
    const { id } = await params
    await resetManagedAccountMfa(session!.user.id, id, input.reason)
    return NextResponse.json({ status: 'mfa_reset' })
  } catch (error) {
    return accountErrorResponse(error)
  }
}
