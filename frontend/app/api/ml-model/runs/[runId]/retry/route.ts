import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { retryRetrainingRun } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { RetrainingRetryRequestSchema } from '@/features/ml-model/schemas'

const RUN_ID_PATTERN = /^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$/

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_RUN)
    if (!authorization.ok) return authorization.response
    const originError = requireTrustedOrigin(request)
    if (originError) return originError
    const { runId } = await params
    if (!RUN_ID_PATTERN.test(runId)) {
      return NextResponse.json(
        { error: { code: 'INVALID_RUN_ID', message: 'Retraining run ID is invalid.' } },
        { status: 400 }
      )
    }
    if (typeof session?.user?.id !== 'string' || typeof session?.user?.role !== 'string') {
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Requester context is unavailable.' } },
        { status: 403 }
      )
    }
    let rawBody: unknown
    try {
      rawBody = await request.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Request body must be valid JSON.' } },
        { status: 400 }
      )
    }
    const parsed = RetrainingRetryRequestSchema.safeParse(rawBody)
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Invalid retraining retry request.' } },
        { status: 400 }
      )
    }
    const result = await retryRetrainingRun(
      runId,
      parsed.data,
      {
        id: session.user.id,
        role: session.user.role,
      }
    )
    if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status })
    return NextResponse.json(result.data, { status: 202 })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
