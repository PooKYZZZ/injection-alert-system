import { z } from 'zod'

export const ConfidenceThresholdsSchema = z.object({
  low: z.number(),
  medium: z.number(),
  high: z.number(),
})

export const MLHealthDataSchema = z.object({
  model_version: z.string(),
  status: z.enum(['HEALTHY', 'DEGRADED', 'DOWN']),
  latency_ms: z.number(),
  latency_trend: z.number(),
  drift_score: z.number(),
  drift_status: z.enum(['NORMAL', 'WARNING', 'CRITICAL']),
  traffic_processed: z.number(),
  thresholds: ConfidenceThresholdsSchema,
})
