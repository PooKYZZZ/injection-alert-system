import { PaginatedAlerts, Alert } from '@/features/alerts/types'

const items: Alert[] = [
  {
    alert_id: "1",
    timestamp: "2026-03-09T09:55:00.000Z",
    source_ip: "192.168.1.100",
    request_path: "/api/login",
    request_method: "POST",
    payload_snippet: "' OR '1'='1",
    prediction: "SQL Injection",
    confidence: 0.98,
    confidence_level: "HIGH",
    action_taken: "BLOCKED",
    crs_score: 20,
    triage_status: null,
    shap_values: [
      { feature_name: "keyword_or", contribution: 0.4 },
      { feature_name: "quote_balance", contribution: 0.4 },
    ],
    source_intel: { ip: "192.168.1.100", country: "US", reputation_score: 10 }
  },
  {
    alert_id: "2",
    timestamp: "2026-03-09T09:45:00.000Z",
    source_ip: "10.0.0.5",
    request_path: "/search",
    request_method: "GET",
    payload_snippet: "q=admin'; WAITFOR DELAY '0:0:10'--",
    prediction: "SQL Injection",
    confidence: 0.75,
    confidence_level: "MEDIUM",
    action_taken: "THROTTLED",
    crs_score: 12,
    triage_status: null,
  },
  {
    alert_id: "3",
    timestamp: "2026-03-09T09:00:00.000Z",
    source_ip: "172.16.0.42",
    request_path: "/products",
    request_method: "GET",
    payload_snippet: "id=1 AND (SELECT * FROM users)",
    prediction: "SQL Injection",
    confidence: 0.45,
    confidence_level: "LOW",
    action_taken: "ALLOWED",
    crs_score: 8,
    triage_status: null,
  }
]

export const MOCK_ALERTS: PaginatedAlerts = {
  items,
  total: items.length,
  page: 1,
  pageSize: 20
}
