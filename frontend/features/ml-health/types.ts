export interface ConfidenceThresholds {
  low: number | null
  medium: number | null
  high: number | null
}

export interface MLHealthData {
  model_version: string
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN'
  latency_ms: number
  latency_trend: number | null
  drift_score: number | null
  drift_status: 'NORMAL' | 'WARNING' | 'CRITICAL'
  traffic_processed: number
  thresholds: ConfidenceThresholds
}
