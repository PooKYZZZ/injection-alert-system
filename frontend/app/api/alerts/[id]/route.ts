import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { MOCK_ALERTS } from '@/mocks/alerts'
import { AlertSchema } from '@/features/alerts/schemas'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params

    // By default, use mock alerts unless explicitly disabled via USE_MOCK_ALERTS=false.
    const useMockAlerts = process.env.USE_MOCK_ALERTS !== 'false'

    if (useMockAlerts) {
      const alert = MOCK_ALERTS.items.find((a) => a.alert_id === id)
      if (!alert) {
        return NextResponse.json({ error: 'Not Found' }, { status: 404 })
      }

      const parsed = AlertSchema.safeParse(alert)
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
    // const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/alerts/${id}`, {
    //   headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` },
    // })
    // if (res.status === 404) {
    //   return NextResponse.json({ error: 'Not Found' }, { status: 404 })
    // }
    // const raw = await res.json()
    // const pd2parsed = AlertSchema.safeParse(raw)
    // if (!pd2parsed.success) {
    //   return NextResponse.json({ error: 'Invalid response from upstream' }, { status: 502 })
    // }
    // return NextResponse.json(pd2parsed.data)
  } catch {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
