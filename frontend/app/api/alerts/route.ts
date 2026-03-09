import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { MOCK_ALERTS } from '@/mocks/alerts'
import { PaginatedAlertsSchema } from '@/features/alerts/schemas'

export async function GET(_request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // By default, use mock alerts unless explicitly disabled via USE_MOCK_ALERTS=false.
    const useMockAlerts = process.env.USE_MOCK_ALERTS !== 'false'

    if (useMockAlerts) {
      const parsed = PaginatedAlertsSchema.safeParse(MOCK_ALERTS)
      if (!parsed.success) {
        return NextResponse.json(
          { error: 'Invalid response from upstream' },
          { status: 502 }
        )
      }
      return NextResponse.json(parsed.data)
    }

    // When mocks are disabled, the real upstream implementation is not yet available.
    // PD2: replace this 501 with the real fetch implementation below.
    return NextResponse.json({ error: 'Not Implemented' }, { status: 501 })

    // PD2: replace mock with real fetch
    // const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/alerts`, {
    //   headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` },
    // })
    // const raw = await res.json()
    // const pd2parsed = PaginatedAlertsSchema.safeParse(raw)
    // if (!pd2parsed.success) {
    //   return NextResponse.json({ error: 'Invalid response from upstream' }, { status: 502 })
    // }
    // return NextResponse.json(pd2parsed.data)
  } catch {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
