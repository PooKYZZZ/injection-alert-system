import type { CalibrationBin, MLHealthData } from '@/features/ml-health/types'
import { formatStableDateTime } from '@/lib/date-time'

export type HealthTone = 'healthy' | 'warning' | 'critical' | 'unknown'
export type PolicyBandAction = 'allow' | 'throttle' | 'block'

export type PolicyBandView = {
  label: string
  action: PolicyBandAction
  rangeLabel: string
}

export type ClassMetricView = {
  label: string
  f1Display: string
}

export type DistributionRowView = {
  label: string
  baselineDisplay: string | null
  currentDisplay: string
  deltaDisplay: string | null
}

export type DiagnosticTab = 'performance' | 'monitoring' | 'evaluation' | 'policy'

export type MLHealthViewModel = {
  tone: HealthTone
  servingTone: HealthTone
  servingStatusLabel: string
  servingStatusDetail: string
  monitoringTone: HealthTone
  monitoringStatusLabel: string
  monitoringStatusDetail: string
  monitoringUnavailableCount: number
  retrievedAtDisplay: string
  sourceFreshnessDisplay: string
  hasTraffic: boolean
  trafficProcessedDisplay: string
  latencyDisplay: string
  latencyTrendDisplay: string
  evaluationEvidenceSummary: string
  evaluationProvenanceDisplay: string
  distributionSummary: string
  driftScoreDisplay: string
  driftStatusDisplay: string
  eceDisplay: string
  calibrationSummary: string
  normalPolicyException: string
  thresholdLabels: {
    low: string
    medium: string
    high: string
    critical: string
  }
  policyBands: PolicyBandView[]
  classMetrics: ClassMetricView[]
  distributionHasBaseline: boolean
  distributionRows: DistributionRowView[]
  calibrationBins: CalibrationBin[]
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatThreshold(value: number | null): string {
  if (value == null) {
    return 'Not configured'
  }

  return `${Math.round(value * 100)}%`
}

function countUnavailableMonitoringSignals(health: MLHealthData): number {
  return Number(health.drift_status == null) + Number(health.ece == null)
}

function deriveServingTone(status: MLHealthData['status']): HealthTone {
  if (status === 'HEALTHY') return 'healthy'
  if (status === 'DEGRADED') return 'warning'
  if (status === 'DOWN') return 'critical'
  return 'unknown'
}

function buildServingStatusLabel(status: MLHealthData['status']): string {
  if (status === 'HEALTHY') return 'Healthy'
  if (status === 'DEGRADED') return 'Degraded'
  if (status === 'DOWN') return 'Down'
  return 'Not reported'
}

function buildServingStatusDetail(health: MLHealthData): string {
  if (health.status === 'DOWN') {
    return 'Serving is down in this snapshot. Immediate investigation is required.'
  }

  if (health.status === 'DEGRADED') {
    return 'Serving is available but operating outside preferred limits in this snapshot.'
  }

  if (health.status === 'HEALTHY' && health.traffic_processed === 0) {
    return 'Serving is healthy, but no serving traffic was reported in this snapshot.'
  }

  if (health.status === 'HEALTHY') return 'Serving is healthy in this snapshot.'

  return 'Serving status was not reported in this snapshot.'
}

function deriveMonitoringTone(health: MLHealthData): HealthTone {
  if (health.drift_status === 'CRITICAL') return 'critical'
  if (health.drift_status === 'WARNING' || countUnavailableMonitoringSignals(health) > 0) return 'warning'
  if (health.drift_status === 'NORMAL' && health.ece != null) return 'healthy'
  return 'unknown'
}

function buildMonitoringStatusLabel(health: MLHealthData): string {
  if (health.drift_status === 'CRITICAL') return 'Critical'
  if (health.drift_status === 'WARNING') return 'Warning'
  if (countUnavailableMonitoringSignals(health) > 0) return 'Incomplete'
  if (health.drift_status === 'NORMAL' && health.ece != null) return 'Complete'
  return 'Not reported'
}

function buildMonitoringStatusDetail(health: MLHealthData): string {
  if (health.drift_status === 'CRITICAL') return 'Drift monitoring reported a critical signal in this snapshot.'
  if (health.drift_status === 'WARNING') return 'Drift monitoring reported a warning signal in this snapshot.'

  const unavailableCount = countUnavailableMonitoringSignals(health)
  if (unavailableCount > 0) {
    return `${unavailableCount} monitoring signal${unavailableCount === 1 ? ' is' : 's are'} not reported in this snapshot.`
  }

  if (health.drift_status === 'NORMAL' && health.ece != null) {
    return 'Drift monitoring reports no warning and calibration evidence is included.'
  }

  return 'Monitoring status was not reported in this snapshot.'
}

export function deriveHealthTone(health: MLHealthData): HealthTone {
  if (health.status === 'DOWN' || health.drift_status === 'CRITICAL') {
    return 'critical'
  }

  if (health.status === 'DEGRADED' || health.drift_status === 'WARNING') {
    return 'warning'
  }

  if (health.status === 'HEALTHY') {
    return 'healthy'
  }

  return 'unknown'
}

export function buildPolicyBands(health: MLHealthData): PolicyBandView[] {
  const low = health.thresholds.low
  const high = health.thresholds.high
  const critical = health.thresholds.critical

  if (low == null || high == null || critical == null || low >= high || high >= critical) {
    return [
      { label: 'Low', action: 'allow', rangeLabel: 'Not configured' },
      { label: 'Medium', action: 'throttle', rangeLabel: 'Not configured' },
      { label: 'High', action: 'block', rangeLabel: 'Not configured' },
      { label: 'Critical', action: 'block', rangeLabel: 'Not configured' },
    ]
  }

  const lowPct = Math.round(low * 100)
  const highPct = Math.round(high * 100)
  const criticalPct = Math.round(critical * 100)

  return [
    { label: 'Low', action: 'allow', rangeLabel: `< ${lowPct}%` },
    { label: 'Medium', action: 'throttle', rangeLabel: `${lowPct}% – ≤ ${highPct}%` },
    { label: 'High', action: 'block', rangeLabel: `> ${highPct}% – < ${criticalPct}%` },
    { label: 'Critical', action: 'block', rangeLabel: `≥ ${criticalPct}%` },
  ]
}

function buildClassMetrics(health: MLHealthData): ClassMetricView[] {
  const preferredOrder = ['Normal', 'SQL Injection', 'Code Injection', 'Other Attacks']
  const entries = Object.entries(health.per_class_f1 ?? {})
    .sort(([a], [b]) => {
      const aIndex = preferredOrder.indexOf(a)
      const bIndex = preferredOrder.indexOf(b)
      if (aIndex !== -1 || bIndex !== -1) {
        if (aIndex === -1) return 1
        if (bIndex === -1) return -1
        return aIndex - bIndex
      }
      return a.localeCompare(b)
    })

  return entries.map(([label, value]) => ({
    label,
    f1Display: value.toFixed(3),
  }))
}

function formatNullableCount(value: number | null): string {
  if (value == null) {
    return 'Not reported'
  }

  return formatCount(value)
}

function buildDistributionRows(health: MLHealthData): DistributionRowView[] {
  const distribution = health.prediction_distribution
  if (!distribution) {
    return []
  }

  const labels = new Set<string>()
  for (const label of Object.keys(distribution.baseline)) {
    labels.add(label)
  }
  for (const label of Object.keys(distribution.current)) {
    labels.add(label)
  }

  const preferredOrder = ['Normal', 'SQL Injection', 'Code Injection', 'Other Attacks']

  return [...labels]
    .sort((a, b) => {
      const aIndex = preferredOrder.indexOf(a)
      const bIndex = preferredOrder.indexOf(b)
      if (aIndex !== -1 || bIndex !== -1) {
        if (aIndex === -1) return 1
        if (bIndex === -1) return -1
        return aIndex - bIndex
      }
      return a.localeCompare(b)
    })
    .map((label) => {
      const baseline = distribution.baseline[label] ?? null
      const current = distribution.current[label] ?? null
      const delta = baseline != null && current != null ? current - baseline : null

      return {
        label,
        baselineDisplay: baseline == null ? null : formatNullableCount(baseline),
        currentDisplay: formatNullableCount(current),
        deltaDisplay: delta == null ? null : `${delta > 0 ? '+' : ''}${delta}`,
      }
    })
}

function hasReportedEvaluationEvidence(health: MLHealthData): boolean {
  return (
    health.macro_f1 != null ||
    health.ece != null ||
    Object.keys(health.per_class_f1 ?? {}).length > 0 ||
    (health.calibration_bins?.length ?? 0) > 0
  )
}

function buildEvaluationEvidenceSummary(health: MLHealthData): string {
  const hasEvidence = hasReportedEvaluationEvidence(health)

  return hasEvidence
    ? 'Reported evaluation metrics are included in this snapshot.'
    : 'No evaluation metrics were reported in this snapshot.'
}

function buildDistributionSummary(health: MLHealthData): string {
  const distribution = health.prediction_distribution
  if (!distribution) {
    return 'Prediction counts were not reported in this snapshot.'
  }

  return Object.keys(distribution.baseline).length > 0
    ? 'Current prediction counts can be compared with the supplied baseline.'
    : 'Current prediction counts are available; no reference baseline was supplied, so comparison is unavailable.'
}

function buildCalibrationSummary(ece: number | null | undefined): string {
  if (ece == null) {
    return 'Expected calibration error was not reported in this snapshot.'
  }

  return 'Expected calibration error was reported; no acceptance threshold was provided.'
}

export function buildMLHealthViewModel(health: MLHealthData): MLHealthViewModel {
  const driftScore = health.drift_score
  const ece = health.ece
  const hasTraffic = health.traffic_processed > 0
  const distributionHasBaseline = Object.keys(health.prediction_distribution?.baseline ?? {}).length > 0

  return {
    tone: deriveHealthTone(health),
    servingTone: deriveServingTone(health.status),
    servingStatusLabel: buildServingStatusLabel(health.status),
    servingStatusDetail: buildServingStatusDetail(health),
    monitoringTone: deriveMonitoringTone(health),
    monitoringStatusLabel: buildMonitoringStatusLabel(health),
    monitoringStatusDetail: buildMonitoringStatusDetail(health),
    monitoringUnavailableCount: countUnavailableMonitoringSignals(health),
    retrievedAtDisplay: formatStableDateTime(health.retrieved_at, 'Not available'),
    sourceFreshnessDisplay: 'Source timestamp unavailable',
    hasTraffic,
    trafficProcessedDisplay: formatCount(health.traffic_processed),
    latencyDisplay: hasTraffic ? `${health.latency_ms.toFixed(1)}ms` : 'Not available',
    latencyTrendDisplay:
      health.latency_trend == null ? 'No previous latency available' : `${health.latency_trend > 0 ? '+' : ''}${health.latency_trend.toFixed(1)}ms`,
    evaluationEvidenceSummary: buildEvaluationEvidenceSummary(health),
    evaluationProvenanceDisplay: hasReportedEvaluationEvidence(health)
      ? 'Evaluation run identity and timestamp were not provided.'
      : 'No evaluation provenance was provided.',
    distributionSummary: buildDistributionSummary(health),
    driftScoreDisplay: driftScore == null ? 'Not reported' : driftScore.toFixed(3),
    driftStatusDisplay: health.drift_status ?? 'Not reported',
    eceDisplay: ece == null ? 'Not reported' : ece.toFixed(3),
    calibrationSummary: buildCalibrationSummary(ece),
    normalPolicyException: 'Normal predictions remain allowed for all valid confidence tiers.',
    thresholdLabels: {
      low: formatThreshold(health.thresholds.low),
      medium: formatThreshold(health.thresholds.medium),
      high: formatThreshold(health.thresholds.high),
      critical: formatThreshold(health.thresholds.critical),
    },
    policyBands: buildPolicyBands(health),
    classMetrics: buildClassMetrics(health),
    distributionHasBaseline,
    distributionRows: buildDistributionRows(health),
    calibrationBins: health.calibration_bins ?? [],
  }
}
