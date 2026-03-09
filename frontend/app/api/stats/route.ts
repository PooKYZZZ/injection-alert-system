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

    const useMock = process.env.USE_MOCK_STATS === 'true'

    if (useMock) {
      const parsed = DashboardStatsSchema.safeParse(MOCK_STATS)
      if (!parsed.success) {
        return NextResponse.json(
          { error: 'Invalid response from upstream' },
          { status: 502 }
        )
      }

      return NextResponse.json(parsed.data)
    }

    const fastApiBaseUrl = process.env.FASTAPI_BASE_URL
    const internalApiKey = process.env.INTERNAL_API_KEY

    if (!fastApiBaseUrl || !internalApiKey) {
      return NextResponse.json(
        { error: 'Upstream service not configured' },
        { status: 501 }
      )
    }

    const res = await fetch(`${fastApiBaseUrl}/api/stats`, {
      headers: { Authorization: `Bearer ${internalApiKey}` },
    })

    if (!res.ok) {
      return NextResponse.json(
        { error: 'Error response from upstream', status: res.status },
        { status: 502 }
      )
    }

    const raw = await res.json()
    const pd2parsed = DashboardStatsSchema.safeParse(raw)
    if (!pd2parsed.success) {
      return NextResponse.json(
        { error: 'Invalid response from upstream' },
        { status: 502 }
      )
    }

    return NextResponse.json(pd2parsed.data)
  } catch {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
