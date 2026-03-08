import { PaginatedAlerts, Alert } from '@/features/alerts/types'

const items: Alert[] = [
  {
    alert_id: "ALT-1001",
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    source_ip: "192.168.1.100",
    request_path: "/api/login",
    request_method: "POST",
    payload_snippet: "' OR '1'='1",
    prediction: "SQLi",
    confidence: 0.98,
    confidence_level: "HIGH",
    action_taken: "BLOCKED",
    crs_score: 20,
    shap_values: [
      { feature_name: "keyword_or", contribution: 0.4 },
      { feature_name: "quote_balance", contribution: 0.4 },
    ],
    source_intel: { ip: "192.168.1.100", country: "US", reputation_score: 10 }
  },
  {
    alert_id: "ALT-1002",
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    source_ip: "10.0.0.5",
    request_path: "/search",
    request_method: "GET",
    payload_snippet: "q=admin'; WAITFOR DELAY '0:0:10'--",
    prediction: "SQLi",
    confidence: 0.75,
    confidence_level: "MEDIUM",
    action_taken: "THROTTLED",
    crs_score: 12,
  },
  {
    alert_id: "ALT-1003",
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    source_ip: "172.16.0.42",
    request_path: "/products",
    request_method: "GET",
    payload_snippet: "id=1 AND (SELECT * FROM users)",
    prediction: "SQLi",
    confidence: 0.45,
    confidence_level: "LOW",
    action_taken: "LOGGED",
    crs_score: 8,
  }
]

export const MOCK_ALERTS: PaginatedAlerts = {
  items,
  total: items.length,
  page: 1,
  pageSize: 20
}
