export interface ActivityBucket {
  bucket_index: number
  total_count: number
  blocked_count: number
  allowed_count: number
  throttled_count: number
  timestamp_start: Date
  timestamp_end?: Date | null
  bucket_width_seconds?: number | null
}

import type { AlertAction } from '@/features/alerts/contract'

export interface SourceIPSummary {
  ip: string
  count: number
  action: AlertAction | null
}

export interface TargetPathSummary {
  path: string
  hits: number
}

export interface DashboardStats {
  actionable_alerts: number
  total_requests: number
  avg_inference_latency_ms: number
  blocked_count: number
  allowed_count: number
  throttled_count: number
  avg_confidence: number | null
  false_positive_rate: number
  false_positive_count: number
  high_alert_count: number
  prev_high_alert_count: number | null
  prev_total_requests: number | null
  prev_blocked_count: number | null
  prev_allowed_count: number | null
  prev_throttled_count: number | null
  activity_buckets: ActivityBucket[]
  attack_distribution: Record<string, number>
  top_source_ips: SourceIPSummary[]
  top_targeted_paths: TargetPathSummary[]
}
