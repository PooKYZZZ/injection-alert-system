import { z } from 'zod'
import type {
  AlertAction,
  AlertConfidenceTier,
  AlertNotificationChannel,
  AlertNotificationStatus,
  AlertPolicyDecision,
  AlertPrediction,
  AlertSeverity,
  LabelReviewApprovalState,
  VerifiedLabel,
} from './contract'
import type {
  TriageStatus,
  AlertFilters,
  LabelReviewSchema,
  AlertActionHistorySchema,
  CorrelatedEvidenceRecordSchema,
  EvidenceRelationshipSchema,
} from './schemas'

export type {
  AlertAction,
  AlertConfidenceTier,
  AlertNotificationChannel,
  AlertNotificationStatus,
  AlertPolicyDecision,
  AlertPrediction,
  AlertSeverity,
  TriageStatus,
  AlertFilters,
  LabelReviewApprovalState,
  VerifiedLabel,
}

export interface ShapFeature {
  feature_name: string
  contribution: number
}

export interface SourceIntel {
  ip: string
  asn?: string
  country?: string
  reputation_score?: number
}

export interface Alert {
  alert_id: string
  transaction_id?: string | null
  request_correlation_id?: string | null
  timestamp: string
  source_ip: string | null
  request_path: string | null
  request_method: string | null
  user_agent?: string
  payload_snippet: string
  query_string?: string | null
  prediction: AlertPrediction
  confidence: number
  confidence_level: AlertConfidenceTier
  model_version?: string | null
  preprocessing_version?: string | null
  action_taken: AlertAction | null
  observed_http_status?: number | null
  evidence_relationship?: EvidenceRelationship
  correlated_records?: CorrelatedEvidenceRecord[]
  action_history?: AlertActionHistory[]
  policy_decision?: AlertPolicyDecision | null
  policy_decision_reason?: string | null
  policy_version?: string | null
  policy_evidence_context?: Record<string, unknown> | null
  notification_status?: Partial<Record<AlertNotificationChannel, AlertNotificationStatus>> | null
  triage_status?: TriageStatus | null
  crs_score?: number | null
  crs_rule_ids?: string[] | null
  ingest_source?: string | null
  source_provenance?: string | null
  source_verification_status?: string | null
  matched_rule_messages?: string[] | null
  matched_rule_tags?: string[] | null
  analyst_label?: string | null
  labeled_at?: string | null
  labeled_by?: string | null
  label_review?: LabelReview | null
  shap_values?: ShapFeature[]
  source_intel?: SourceIntel
}

export type LabelReview = z.infer<typeof LabelReviewSchema>
export type EvidenceRelationship = z.infer<typeof EvidenceRelationshipSchema>
export type CorrelatedEvidenceRecord = z.infer<typeof CorrelatedEvidenceRecordSchema>
export type AlertActionHistory = z.infer<typeof AlertActionHistorySchema>

export interface PaginatedAlerts {
  items: Alert[]
  total: number
  page: number
  pageSize: number
}
