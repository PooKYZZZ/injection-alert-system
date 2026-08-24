import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { getRetrainingRun } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { invalidRetrainingRunIdResponse } from '@/lib/server/retraining-route'

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
    const runIdError = invalidRetrainingRunIdResponse(runId)
    if (runIdError) return runIdError
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
