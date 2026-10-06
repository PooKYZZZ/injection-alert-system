import { z } from 'zod'

import {
  ALERT_ACTION_TAKEN_VALUES,
  ALERT_CONFIDENCE_TIER_VALUES,
  ALERT_PREDICTION_VALUES,
} from './contract'
import { TRIAGE_STATUS_VALUES } from './schemas'

const ConfidenceTierFilterSchema = z.enum([
  'ALL',
  ...ALERT_CONFIDENCE_TIER_VALUES,
])

export const TrafficHistoryExportRequestSchema = z
  .object({
    start_date: z.iso.date(),
    end_date: z.iso.date(),
    timezone: z.string().trim().min(1).max(64),
    include_normal: z.boolean().default(false),
    severity: ConfidenceTierFilterSchema.optional(),
    confidence_tier: ConfidenceTierFilterSchema.optional(),
    search: z.string().max(200).optional(),
    action: z.enum(ALERT_ACTION_TAKEN_VALUES).optional(),
    triage_status: z.enum(TRIAGE_STATUS_VALUES).optional(),
    confidence_level: z.array(z.enum(ALERT_CONFIDENCE_TIER_VALUES)).max(5).optional(),
    prediction: z.enum(ALERT_PREDICTION_VALUES).optional(),
    source_ip: z.string().max(45).optional(),
  })
  .strict()
  .superRefine((value, context) => {
    if (value.end_date < value.start_date) {
      context.addIssue({
        code: 'custom',
        path: ['end_date'],
        message: 'End date must not precede start date.',
      })
    } else {
      const start = Date.parse(`${value.start_date}T00:00:00Z`)
      const end = Date.parse(`${value.end_date}T00:00:00Z`)
      if ((end - start) / 86_400_000 + 1 > 31) {
        context.addIssue({
          code: 'custom',
          path: ['end_date'],
          message: 'Choose a range of 31 calendar days or fewer.',
        })
      }
    }
    if (
      value.severity &&
      value.confidence_tier &&
      value.severity !== value.confidence_tier
    ) {
      context.addIssue({
        code: 'custom',
        path: ['confidence_tier'],
        message: 'Confidence filters must match.',
      })
    }
  })

export type TrafficHistoryExportRequest = z.infer<
  typeof TrafficHistoryExportRequestSchema
>
