import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { ALERT_ACTION_TAKEN_VALUES, type AlertAction } from '@/features/alerts/contract'
import { updateAlertAction } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.ALERTS_ACTION_UPDATE
    )
    if (!authorization.ok) {
      return authorization.response
    }

    const { id } = await params
    const numericId = Number(id)
    if (!id || !Number.isFinite(numericId) || !Number.isInteger(numericId)) {
      return NextResponse.json(
        { error: { code: 'INVALID_ID', message: 'Alert ID must be a valid number.' } },
        { status: 400 }
      )
    }

    let body: Record<string, unknown>
    try {
      body = (await request.json()) as Record<string, unknown>
    } catch {
      return NextResponse.json(
        {
          error: {
            code: 'INVALID_REQUEST',
            message: 'Request body must be valid JSON and include an action_taken field.',
          },
        },
        { status: 400 }
      )
    }

    const actionTaken = body.action_taken
    if (
      typeof actionTaken !== 'string' ||
      !ALERT_ACTION_TAKEN_VALUES.includes(actionTaken as AlertAction)
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'INVALID_REQUEST',
            message: 'Invalid or missing action_taken. Must be one of: BLOCKED, THROTTLED, ALLOWED.',
          },
        },
        { status: 400 }
      )
    }

    const result = await updateAlertAction(id, actionTaken as AlertAction)
    if (!result.ok) {
      return NextResponse.json({ error: result.error }, { status: result.status })
    }

    return NextResponse.json(result.data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
