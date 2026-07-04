import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { getAlerts } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export async function GET(request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    const authorization = requirePermission(session, PERMISSIONS.ALERTS_READ)
    if (!authorization.ok) {
      return authorization.response
    }

    const result = await getAlerts(request.nextUrl.searchParams)
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
