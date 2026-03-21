export interface ActivityBucket {
  bucket_index: number
  total_count: number
  blocked_count: number
  allowed_count: number
  throttled_count: number
  timestamp_start: Date
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
  activity_buckets: ActivityBucket[]
  attack_distribution: Record<string, number>
  top_source_ips: SourceIPSummary[]
  top_targeted_paths: TargetPathSummary[]
}
