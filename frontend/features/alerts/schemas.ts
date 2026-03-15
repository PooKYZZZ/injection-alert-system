import { z } from 'zod'
import {
  ALERT_ACTION_TAKEN_VALUES,
  ALERT_PREDICTION_VALUES,
  ALERT_SEVERITY_VALUES,
} from './contract'

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
  source_ip: z.string().nullable(),
  request_path: z.string().nullable(),
  request_method: z.string().nullable(),
  user_agent: z.string().optional(),
  payload_snippet: z.string(),
  prediction: z.enum(ALERT_PREDICTION_VALUES),
  confidence: z.number(),
  confidence_level: z.enum(ALERT_SEVERITY_VALUES),
  action_taken: z.enum(ALERT_ACTION_TAKEN_VALUES).nullable(),
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
