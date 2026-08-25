export interface ConfidenceThresholds {
  low: number | null
  medium: number | null
  high: number | null
  critical: number | null
}

export interface CalibrationBin {
  bin_idx: number
  bin_center: number
  accuracy: number
  confidence: number
  count: number
}

export interface QueueHealth {
  enabled: boolean
  max_size: number
  depth: number
  available_capacity: number
  worker_count: number
  worker_running: boolean
  total_enqueued: number
  total_processed: number
  total_failed: number
  overflow_count: number
  last_error: string | null
  last_error_at: string | null
  last_processed_at: string | null
}

export interface MLHealthData {
  model_version: string
  /** Timestamp added by the Next.js BFF when it retrieves this snapshot. */
  retrieved_at?: string
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
  queue?: QueueHealth | null
}
