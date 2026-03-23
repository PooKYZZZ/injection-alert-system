export interface ConfidenceThresholds {
  low: number | null
  medium: number | null
  high: number | null
}

export interface CalibrationBin {
  bin_idx: number
  bin_center: number
  accuracy: number
  confidence: number
  count: number
}

export interface MLHealthData {
  model_version: string
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN'
  latency_ms: number
  latency_trend: number | null
  drift_score: number | null
  drift_status: 'NORMAL' | 'WARNING' | 'CRITICAL' | null
  traffic_processed: number
  thresholds: ConfidenceThresholds
  // Optional eval metadata from model registry artifacts
  macro_f1?: number | null
  ece?: number | null
  per_class_f1?: Record<string, number>
  calibration_bins?: CalibrationBin[]
  prediction_distribution?: { baseline: Record<string, number>; current: Record<string, number> }
}
