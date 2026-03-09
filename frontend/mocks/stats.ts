import { DashboardStats } from '@/features/stats/types'

export const MOCK_STATS: DashboardStats = {
  actionable_alerts: 145,
  actionable_alerts_trend: 12.5,
  avg_confidence: 0.88,
  avg_confidence_trend: 2.1,
  threat_ip_count: 32,
  threat_ip_count_trend: -4.0,
  crs_comparison: {
    total_crs_flagged: 1000,
    ml_confirmed: 145,
    ml_overturned: 855,
    false_positive_reduction_pct: 85.5,
    total_requests: 8400000,
    avg_inference_ms: 3.4
  }
}
