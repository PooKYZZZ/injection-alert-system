export interface ActivityBucket {
  bucket_index: number
  total_count: number
  blocked_count: number
  timestamp_start: Date
}

export interface DashboardStats {
  actionable_alerts: number
  total_requests: number
  avg_inference_latency_ms: number
  blocked_count: number
  allowed_count: number
  avg_confidence: number | null
  activity_buckets: ActivityBucket[]
}
