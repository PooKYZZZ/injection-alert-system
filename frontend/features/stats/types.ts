export interface CRSComparisonMetrics {
  total_crs_flagged: number
  ml_confirmed: number
  ml_overturned: number
  false_positive_reduction_pct: number
}

export interface DashboardStats {
  actionable_alerts: number
  actionable_alerts_trend: number
  avg_confidence: number
  avg_confidence_trend: number
  threat_ip_count: number
  threat_ip_count_trend: number
  crs_comparison: CRSComparisonMetrics
}
