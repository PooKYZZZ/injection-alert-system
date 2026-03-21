import { DashboardStats, ActivityBucket } from '@/features/stats/types'

// Deterministic mock activity buckets for tests and demos
// Fixed 24-hour pattern with realistic-looking data
const MOCK_ACTIVITY_BUCKETS: ActivityBucket[] = (() => {
  const buckets: ActivityBucket[] = []
  // Use a fixed base date for deterministic timestamps
  const baseDate = new Date('2024-01-15T00:00:00Z')
  // Deterministic pattern: higher activity during "business hours", lower at night
  const pattern = [
    12, 8, 5, 3, 2, 4,  // 0-5: night/early morning (low)
    15, 35, 55, 72, 85, 90, // 6-11: morning ramp up
    88, 82, 78, 85, 92, 88, // 12-17: afternoon peak
    75, 65, 52, 38, 25, 18, // 18-23: evening wind down
  ]
  const blockedPattern = [
    2, 1, 1, 0, 0, 1, // 0-5
    3, 8, 12, 15, 18, 20, // 6-11
    19, 17, 16, 18, 21, 19, // 12-17
    16, 14, 11, 8, 5, 3, // 18-23
  ]
  const throttledPattern = [
    1, 0, 0, 0, 0, 0, // 0-5
    1, 2, 3, 4, 5, 5, // 6-11
    5, 4, 4, 5, 5, 5, // 12-17
    4, 3, 2, 1, 1, 0, // 18-23
  ]

  for (let i = 0; i < 24; i++) {
    const hour = new Date(baseDate.getTime() + i * 60 * 60 * 1000)
    buckets.push({
      bucket_index: i,
      total_count: pattern[i],
      blocked_count: blockedPattern[i],
      allowed_count: pattern[i] - blockedPattern[i] - throttledPattern[i],
      throttled_count: throttledPattern[i],
      timestamp_start: hour,
    })
  }
  return buckets
})()

export const MOCK_STATS: DashboardStats = {
  actionable_alerts: 145,
  total_requests: 8400000,
  avg_inference_latency_ms: 3.4,
  blocked_count: 89,
  allowed_count: 23,
  throttled_count: 12,
  avg_confidence: 0.78,
  activity_buckets: MOCK_ACTIVITY_BUCKETS,
  attack_distribution: {
    'SQL Injection': 45,
    'Code Injection': 8,
    'Other Attacks': 12,
    'Normal': 3,
  },
  top_source_ips: [
    { ip: '192.168.1.14', count: 7, action: 'BLOCKED' },
    { ip: '10.0.0.45', count: 4, action: 'BLOCKED' },
    { ip: '172.16.0.7', count: 3, action: 'THROTTLED' },
  ],
  top_targeted_paths: [
    { path: '/api/login', hits: 6 },
    { path: '/admin/query', hits: 4 },
    { path: '/api/users', hits: 3 },
  ],
}
