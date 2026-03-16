import type {
  AlertAction,
  AlertPrediction,
  AlertSeverity,
} from './contract'

export type { AlertAction, AlertPrediction, AlertSeverity }

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
  confidence_level: AlertSeverity
  action_taken: AlertAction | null
  crs_score?: number
  crs_rule_ids?: string[] | null
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
