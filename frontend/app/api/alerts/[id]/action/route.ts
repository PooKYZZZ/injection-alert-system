import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { updateAlertAction } from '@/lib/bff-client'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
    // Dev logging: capture incoming request for debugging
    if (process.env.NODE_ENV === 'development') {
      // eslint-disable-next-line no-console
      console.log('[API] PATCH /api/alerts/[id]/action request received')
    }
    const session = await auth()
    if (!session) {
      return NextResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' } },
        { status: 401 }
      )
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
    if (process.env.NODE_ENV === 'development') {
      // eslint-disable-next-line no-console
      console.log('[API] action_taken:', actionTaken, 'for id', id)
    }
    if (
      typeof actionTaken !== 'string' ||
      !['BLOCKED', 'THROTTLED', 'ALLOWED'].includes(actionTaken)
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

    const result = await updateAlertAction(id, actionTaken as 'BLOCKED' | 'THROTTLED' | 'ALLOWED')
    if (!result.ok) {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.error('[API] updateAlertAction failed', result)
      }
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
