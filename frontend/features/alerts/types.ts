import type {
  AlertAction,
  AlertConfidenceTier,
  AlertPrediction,
  AlertSeverity,
} from './contract'
import type { TriageStatus, AlertFilters } from './schemas'

export type {
  AlertAction,
  AlertConfidenceTier,
  AlertPrediction,
  AlertSeverity,
  TriageStatus,
  AlertFilters,
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
  timestamp: string
  source_ip: string | null
  request_path: string | null
  request_method: string | null
  user_agent?: string
  payload_snippet: string
  prediction: AlertPrediction
  confidence: number
  confidence_level: AlertConfidenceTier
  action_taken: AlertAction | null
  triage_status?: TriageStatus | null
  crs_score?: number
  crs_rule_ids?: string[] | null
  ingest_source?: string | null
  matched_rule_messages?: string[] | null
  matched_rule_tags?: string[] | null
  analyst_label?: string | null
  labeled_at?: string | null
  labeled_by?: string | null
  shap_values?: ShapFeature[]
  source_intel?: SourceIntel
}

export interface PaginatedAlerts {
  items: Alert[]
  total: number
  page: number
  pageSize: number
}
