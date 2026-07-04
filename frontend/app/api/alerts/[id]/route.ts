import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { getAlertDetail } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.ALERTS_READ
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

    const result = await getAlertDetail(id)
    if (!result.ok) {
      const response = NextResponse.json({ error: result.error }, { status: result.status })
      if (result.retryAfter) {
        response.headers.set('Retry-After', result.retryAfter)
      }
      return response
    }

    return NextResponse.json(result.data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
