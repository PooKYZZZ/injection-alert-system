import { NextResponse } from 'next/server'
import { auth } from '@/auth'
import { getMlHealth } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export async function GET(): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.ML_HEALTH_READ
    )
    if (!authorization.ok) {
      return authorization.response
    }

    const result = await getMlHealth()
    if (!result.ok) {
      const response = NextResponse.json({ error: result.error }, { status: result.status })
      if (result.retryAfter) {
        response.headers.set('Retry-After', result.retryAfter)
      }
      return response
    }

    return NextResponse.json({
      ...result.data,
      // This is the BFF retrieval instant, not a claim about monitoring-source freshness.
      retrieved_at: new Date().toISOString(),
    })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
