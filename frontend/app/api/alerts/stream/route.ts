import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { openAlertStream } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.ALERTS_READ
    )
    if (!authorization.ok) return authorization.response

    const result = await openAlertStream(request.signal)
    if (!result.ok) {
      return NextResponse.json(
        { error: result.error },
        { status: result.status }
      )
    }

    return new Response(result.data.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'private, no-cache, no-store, no-transform',
        'X-Content-Type-Options': 'nosniff',
        'X-Accel-Buffering': 'no',
      },
    })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
