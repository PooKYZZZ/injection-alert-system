import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireRecentTotp } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { resendPasswordSetupRequestSchema } from '@/features/user-management/contract'
import {
  accountErrorResponse,
  accountManagementEnabled,
  featureDisabledResponse,
  requireTrustedOrigin,
} from '@/lib/server/db/account-route-response'
import { resendPasswordSetup } from '@/lib/server/db/account-management'

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
    const requestText = await request.text()
    let requestBody: unknown = {}
    if (requestText.trim()) {
      try {
        requestBody = JSON.parse(requestText)
      } catch {
        return NextResponse.json(
          { error: { code: 'INVALID_REQUEST', message: 'The account request is invalid.' } },
          { status: 400 }
        )
      }
    }
    const input = resendPasswordSetupRequestSchema.safeParse(requestBody)
    if (!input.success) {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'The account request is invalid.' } },
        { status: 400 }
      )
    }
    await resendPasswordSetup(session!.user.id, id, input.data.lifetime)
    return NextResponse.json({ status: 'setup_sent' })
  } catch (error) {
    return accountErrorResponse(error)
  }
}
