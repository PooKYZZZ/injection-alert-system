import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { getRetrainingRun } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

const RUN_ID_PATTERN = /^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$/

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_READ)
    if (!authorization.ok) return authorization.response
    if (typeof session?.user?.id !== 'string' || typeof session?.user?.role !== 'string') {
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Requester context is unavailable.' } },
        { status: 403 }
      )
    }
    const { runId } = await params
    if (!RUN_ID_PATTERN.test(runId)) {
      return NextResponse.json(
        { error: { code: 'INVALID_RUN_ID', message: 'Retraining run ID is invalid.' } },
        { status: 400 }
      )
    }
    const result = await getRetrainingRun(runId, {
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
