import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { getRetrainingRuns, startRetrainingRun } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { RetrainingRunRequestSchema } from '@/features/ml-model/schemas'

export async function GET(): Promise<Response> {
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
    const result = await getRetrainingRuns({
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

export async function POST(request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_RUN)
    if (!authorization.ok) return authorization.response
    const originError = requireTrustedOrigin(request)
    if (originError) return originError
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
    const parsed = RetrainingRunRequestSchema.safeParse(rawBody)
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Invalid retraining request.' } },
        { status: 400 }
      )
    }
    const result = await startRetrainingRun(parsed.data, {
      id: session.user.id,
      role: session.user.role,
    })
    if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status })
    return NextResponse.json(result.data, { status: 202 })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
