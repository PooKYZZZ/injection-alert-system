import { z } from 'zod'
import {
  ALERT_ACTION_TAKEN_VALUES,
  ALERT_PREDICTION_VALUES,
  ALERT_SEVERITY_VALUES,
} from './contract'

export const TRIAGE_STATUS_VALUES = [
  'new',
  'in_review',
  'escalated',
  'resolved',
  'false_positive',
] as const

export const TriageStatusSchema = z.enum(TRIAGE_STATUS_VALUES)
export type TriageStatus = z.infer<typeof TriageStatusSchema>

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

export const AlertFiltersSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().positive().default(20),
  severity: z.enum(['ALL', ...ALERT_SEVERITY_VALUES]).optional(),
  confidence_level: z.array(z.enum(ALERT_SEVERITY_VALUES)).optional(),
  action: z.enum(ALERT_ACTION_TAKEN_VALUES).optional(),
  triage_status: TriageStatusSchema.optional(),
  prediction: z.enum(ALERT_PREDICTION_VALUES).optional(),
  source_ip: z.string().optional(),
  search: z.string().max(200).optional(),
  window: z.enum(['1h', '6h', '24h', '7d']).optional(),
  sort_by: z.enum(['timestamp', 'confidence', 'severity', 'action']).default('timestamp'),
  sort_dir: z.enum(['asc', 'desc']).default('desc'),
})

export type AlertFilters = z.infer<typeof AlertFiltersSchema>

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
  triage_status: TriageStatusSchema.nullable().optional(),
  crs_score: z.number().optional(),
  crs_rule_ids: z.array(z.string()).nullable().optional(),
  ingest_source: z.string().nullable().optional(),
  matched_rule_messages: z.array(z.string()).nullable().optional(),
  matched_rule_tags: z.array(z.string()).nullable().optional(),
  analyst_label: z.string().nullable().optional(),
  labeled_at: z.string().nullable().optional(),
  labeled_by: z.string().nullable().optional(),
  shap_values: z.array(ShapFeatureSchema).optional(),
  source_intel: SourceIntelSchema.optional(),
})

export const PaginatedAlertsSchema = z.object({
  items: z.array(AlertSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
})
