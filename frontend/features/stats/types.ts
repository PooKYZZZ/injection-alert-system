export interface CRSComparisonMetrics {
  total_crs_flagged: number | null
  ml_confirmed: number
  ml_overturned: number | null
  false_positive_reduction_pct: number | null
  total_requests: number
  avg_inference_ms: number
}

export interface DashboardStats {
  actionable_alerts: number
  actionable_alerts_trend: number | null
  avg_confidence: number | null
  avg_confidence_trend: number | null
  threat_ip_count: number | null
  threat_ip_count_trend: number | null
  crs_comparison: CRSComparisonMetrics
}
