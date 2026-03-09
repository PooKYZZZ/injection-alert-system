import { z } from 'zod'

export const ShapFeatureSchema = z.object({
  feature_name: z.string(),
  contribution: z.number(),
})

export const SourceIntelSchema = z.object({
  ip: z.string(),
  asn: z.string().optional(),
  country: z.string().optional(),
  reputation_score: z.number().optional(),
})

export const AlertSchema = z.object({
  alert_id: z.string(),
  timestamp: z.string(),
  source_ip: z.string(),
  request_path: z.string(),
  request_method: z.string(),
  user_agent: z.string().optional(),
  payload_snippet: z.string(),
  prediction: z.string(),
  confidence: z.number(),
  confidence_level: z.enum(['LOW', 'MEDIUM', 'HIGH']),
  action_taken: z.enum(['BLOCKED', 'THROTTLED', 'LOGGED', 'RATE_LIMITED']),
  crs_score: z.number().optional(),
  shap_values: z.array(ShapFeatureSchema).optional(),
  source_intel: SourceIntelSchema.optional(),
})

export const PaginatedAlertsSchema = z.object({
  items: z.array(AlertSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
})
