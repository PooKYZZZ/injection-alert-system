import { z } from 'zod'

export const CRSComparisonSchema = z.object({
  total_crs_flagged: z.number(),
  ml_confirmed: z.number(),
  ml_overturned: z.number(),
  false_positive_reduction_pct: z.number(),
})

export const DashboardStatsSchema = z.object({
  actionable_alerts: z.number(),
  actionable_alerts_trend: z.number(),
  avg_confidence: z.number(),
  avg_confidence_trend: z.number(),
  threat_ip_count: z.number(),
  threat_ip_count_trend: z.number(),
  crs_comparison: CRSComparisonSchema,
})
