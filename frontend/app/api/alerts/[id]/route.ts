import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { getAlertDetail } from '@/lib/bff-client'

export async function GET(
  _request: NextRequest,
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

    const result = await getAlertDetail(id)
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
