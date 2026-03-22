import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { updateAlertTriage } from '@/lib/bff-client'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
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
            message:
              'Request body must be valid JSON and include a triage_status field.',
          },
        },
        { status: 400 }
      )
    }
    const triageStatus = body.triage_status

    if (
      typeof triageStatus !== 'string' ||
      !['new', 'in_review', 'escalated', 'resolved', 'false_positive'].includes(
        triageStatus
      )
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'INVALID_REQUEST',
            message:
              'Invalid or missing triage_status. Must be one of: new, in_review, escalated, resolved, false_positive.',
          },
        },
        { status: 400 }
      )
    }

    const result = await updateAlertTriage(
      id,
      triageStatus as
        | 'new'
        | 'in_review'
        | 'escalated'
        | 'resolved'
        | 'false_positive'
    )
    if (!result.ok) {
      return NextResponse.json(
        { error: result.error },
        { status: result.status }
      )
    }

    return NextResponse.json(result.data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
