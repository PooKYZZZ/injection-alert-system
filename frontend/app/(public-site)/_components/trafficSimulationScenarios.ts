export type TrafficSimulationScenarioId = 'normal' | 'sql-injection' | 'code-injection'

export type TrafficSimulationWafRule = {
  id: string
  message: string
}

export type TrafficSimulationFirewallEvidence = {
  status: 'match' | 'no-match'
  source: 'modsec_audit_bridge' | null
  crsScore: number | null
  rules: TrafficSimulationWafRule[]
}

export type TrafficSimulationScenario = {
  id: TrafficSimulationScenarioId
  title: string
  summary: string
  method: 'GET' | 'POST'
  path: string
  body?: string
  prediction: 'Normal' | 'SQL Injection' | 'Code Injection'
  confidenceTier: 'INFORMATIONAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  firewallEvidence: TrafficSimulationFirewallEvidence
  recordedAction: 'ALLOWED' | 'THROTTLED' | 'BLOCKED'
  sampleHttpResponse: string
  sampleResponseSource: 'Application' | 'ModSecurity'
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
    firewallEvidence: {
      status: 'no-match',
      source: null,
      crsScore: null,
      rules: [],
    },
    recordedAction: 'ALLOWED',
    sampleHttpResponse: '200 OK',
    sampleResponseSource: 'Application',
    sampleHandling: 'The request reached the application; no CRS rule matched.',
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
    firewallEvidence: {
      status: 'match',
      source: 'modsec_audit_bridge',
      crsScore: 5,
      rules: [
        { id: '942100', message: 'SQL Injection Attack Detected via libinjection' },
        { id: '949110', message: 'Inbound Anomaly Score Exceeded (Total Score: 5)' },
      ],
    },
    recordedAction: 'BLOCKED',
    sampleHttpResponse: '403 Forbidden',
    sampleResponseSource: 'ModSecurity',
    sampleHandling: 'ModSecurity returned 403 before the request reached the application.',
    isSecurityDetection: true,
  },
  'code-injection': {
    id: 'code-injection',
    title: 'Code injection pattern',
    summary: 'A prepared input that resembles a server-side command.',
    method: 'POST',
    path: '/feedback',
    body: '{"comment":"require(\'child_process\').exec(\'id\')"}',
    prediction: 'Code Injection',
    confidenceTier: 'MEDIUM',
    firewallEvidence: {
      status: 'match',
      source: 'modsec_audit_bridge',
      crsScore: 10,
      rules: [
        { id: '932100', message: 'Remote Command Execution: Unix Command Injection' },
        { id: '934100', message: 'Node.js Injection Attack' },
        { id: '949110', message: 'Inbound Anomaly Score Exceeded (Total Score: 10)' },
      ],
    },
    recordedAction: 'THROTTLED',
    sampleHttpResponse: '403 Forbidden',
    sampleResponseSource: 'ModSecurity',
    sampleHandling: 'ModSecurity returned 403; the system separately recorded THROTTLED.',
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
