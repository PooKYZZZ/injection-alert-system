import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { deployRetrainingRun } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { invalidRetrainingRunIdResponse } from '@/lib/server/retraining-route'
import { RetrainingDeployRequestSchema } from '@/features/ml-model/schemas'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_DEPLOY)
    if (!authorization.ok) return authorization.response
    const originError = requireTrustedOrigin(request)
    if (originError) return originError
    const { runId } = await params
    const runIdError = invalidRetrainingRunIdResponse(runId)
    if (runIdError) return runIdError
    if (typeof session?.user?.id !== 'string' || typeof session?.user?.role !== 'string') {
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Reviewer context is unavailable.' } },
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
    const parsed = RetrainingDeployRequestSchema.safeParse(rawBody)
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Invalid deployment request.' } },
        { status: 400 }
      )
    }
    const result = await deployRetrainingRun(runId, parsed.data, {
      id: session.user.id,
      role: session.user.role,
    })
    if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status })
    return NextResponse.json(result.data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
