import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { MOCK_ML_HEALTH } from '@/mocks/ml-health'
import { MLHealthDataSchema } from '@/features/ml-health/schemas'

export async function GET(_request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const parsed = MLHealthDataSchema.safeParse(MOCK_ML_HEALTH)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid response from upstream' },
        { status: 502 }
      )
    }

    return NextResponse.json(parsed.data)

    // PD2: replace mock with real fetch
    // const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/ml-health`, {
    //   headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` },
    // })
    // const raw = await res.json()
    // const pd2parsed = MLHealthDataSchema.safeParse(raw)
    // if (!pd2parsed.success) {
    //   return NextResponse.json({ error: 'Invalid response from upstream' }, { status: 502 })
    // }
    // return NextResponse.json(pd2parsed.data)
  } catch {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
