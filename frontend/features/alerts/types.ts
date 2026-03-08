export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH'
export type AlertAction = 'BLOCKED' | 'THROTTLED' | 'LOGGED' | 'RATE_LIMITED'

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
  source_ip: string
  request_path: string
  request_method: string
  user_agent?: string
  payload_snippet: string
  prediction: string
  confidence: number
  confidence_level: AlertSeverity
  action_taken: AlertAction
  crs_score?: number
  shap_values?: ShapFeature[]
  source_intel?: SourceIntel
}

export interface PaginatedAlerts {
  items: Alert[]
  total: number
  page: number
  pageSize: number
}
