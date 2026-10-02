export type TrafficSimulationScenarioId = 'normal' | 'sql-injection' | 'code-injection'

export type TrafficSimulationScenario = {
  id: TrafficSimulationScenarioId
  title: string
  summary: string
  method: 'GET' | 'POST'
  path: string
  body?: string
  prediction: 'Normal' | 'SQL Injection' | 'Code Injection'
  confidenceTier: 'INFORMATIONAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  wafFindingIncluded: boolean
  firewallEvidenceSummary: string
  recordedAction: 'ALLOWED' | 'THROTTLED' | 'BLOCKED'
  sampleHttpResponse: string
  sampleHandling: string
  isSecurityDetection: boolean
}

/**
 * Fixed, browser-only teaching examples. These values are illustrative and
 * must never be submitted to the live target or written to Traffic History.
 */
export const TRAFFIC_SIMULATION_SCENARIOS: Record<
  TrafficSimulationScenarioId,
  TrafficSimulationScenario
> = {
  normal: {
    id: 'normal',
    title: 'Ordinary search',
    summary: 'A routine catalog lookup for comparison.',
    method: 'GET',
    path: '/catalog/search?q=blue+shoes',
    prediction: 'Normal',
    confidenceTier: 'INFORMATIONAL',
    wafFindingIncluded: false,
    firewallEvidenceSummary: 'No firewall rule match is recorded for this routine catalog search.',
    recordedAction: 'ALLOWED',
    sampleHttpResponse: '200 OK',
    sampleHandling: 'The request continues to the application.',
    isSecurityDetection: false,
  },
  'sql-injection': {
    id: 'sql-injection',
    title: 'SQL injection pattern',
    summary: 'A harmless text example that resembles an injection attempt.',
    method: 'GET',
    path: "/catalog/search?q=%27%20OR%20%271%27%3D%271",
    prediction: 'SQL Injection',
    confidenceTier: 'HIGH',
    wafFindingIncluded: true,
    firewallEvidenceSummary: 'A firewall rule match is included for the SQL injection pattern in this sample.',
    recordedAction: 'BLOCKED',
    sampleHttpResponse: '403 Forbidden',
    sampleHandling: 'Access is blocked in this example.',
    isSecurityDetection: true,
  },
  'code-injection': {
    id: 'code-injection',
    title: 'Code injection pattern',
    summary: 'A prepared request with a template-like expression in its input.',
    method: 'POST',
    path: '/feedback',
    body: '{"comment":"${7*7}"}',
    prediction: 'Code Injection',
    confidenceTier: 'MEDIUM',
    wafFindingIncluded: false,
    firewallEvidenceSummary: 'No firewall rule match is included; the ML model still identifies a code-injection pattern.',
    recordedAction: 'THROTTLED',
    sampleHttpResponse: '429 Too Many Requests',
    sampleHandling: 'The request is rate limited in this example.',
    isSecurityDetection: true,
  },
}

export const TRAFFIC_SIMULATION_STAGES = [
  { label: 'Request', title: 'Request context' },
  { label: 'WAF', title: 'Firewall evidence' },
  { label: 'ML', title: 'Model suggestion' },
  { label: 'History', title: 'Traffic History' },
  { label: 'Details', title: 'Traffic Details' },
  { label: 'Review', title: 'Analyst review' },
] as const
