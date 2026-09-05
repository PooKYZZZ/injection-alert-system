import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { getRetrainingSummary } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export async function GET(): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_READ)
    if (!authorization.ok) return authorization.response
    const result = await getRetrainingSummary({
      id: session!.user.id,
      role: session!.user.role,
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
