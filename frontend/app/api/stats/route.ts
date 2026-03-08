import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { auth } from '@/auth'
import { MOCK_STATS } from '@/mocks/stats'

const CRSComparisonSchema = z.object({
  total_crs_flagged: z.number(),
  ml_confirmed: z.number(),
  ml_overturned: z.number(),
  false_positive_reduction_pct: z.number(),
})

const DashboardStatsSchema = z.object({
  actionable_alerts: z.number(),
  actionable_alerts_trend: z.number(),
  avg_confidence: z.number(),
  avg_confidence_trend: z.number(),
  threat_ip_count: z.number(),
  threat_ip_count_trend: z.number(),
  crs_comparison: CRSComparisonSchema,
})

export async function GET(_request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const parsed = DashboardStatsSchema.safeParse(MOCK_STATS)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid response from upstream' },
        { status: 502 }
      )
    }

    return NextResponse.json(parsed.data)

    // PD2: replace mock with real fetch
    // const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/stats`, {
    //   headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` },
    // })
    // const raw = await res.json()
    // const pd2parsed = DashboardStatsSchema.safeParse(raw)
    // if (!pd2parsed.success) {
    //   return NextResponse.json({ error: 'Invalid response from upstream' }, { status: 502 })
    // }
    // return NextResponse.json(pd2parsed.data)
  } catch {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
