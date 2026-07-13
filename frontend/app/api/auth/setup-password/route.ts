import { NextResponse } from 'next/server'
import { z } from 'zod'

import {
  accountManagementEnabled,
  featureDisabledResponse,
  publicTokenErrorResponse,
  requireTrustedOrigin,
} from '@/lib/server/db/account-route-response'
import { completeInitialPasswordSetup } from '@/lib/server/db/account-management'

const requestSchema = z.object({
  token: z.string().min(20).max(512),
  password: z.string().min(1).max(256),
}).strict()

export async function POST(request: Request): Promise<Response> {
  if (!accountManagementEnabled()) return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  try {
    const input = requestSchema.parse(await request.json())
    await completeInitialPasswordSetup(input.token, input.password)
    return NextResponse.json({ status: 'password_set' })
  } catch {
    return publicTokenErrorResponse()
  }
}
