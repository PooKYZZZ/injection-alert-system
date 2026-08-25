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

export type MLHealthViewModel = {
  tone: HealthTone
  statusHeadline: string
  statusSubline: string
  displayName: string
  windowLabel: string
  granularityLabel: string
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

function deriveDisplayName(modelVersion: string): string {
  return modelVersion.split('_cleaned_')[0] ?? modelVersion
}

function countUnavailableMonitoringSignals(health: MLHealthData): number {
  return Number(health.drift_status == null) + Number(health.ece == null)
}

function buildStatusHeadline(health: MLHealthData): string {
  const tone = deriveHealthTone(health)

  if (tone === 'healthy' && countUnavailableMonitoringSignals(health) > 0) {
    return 'Serving is healthy; telemetry is incomplete'
  }

  if (tone === 'healthy') {
    return 'Serving is healthy'
  }

  if (tone === 'warning') {
    return 'Serving is available, but review is recommended'
  }

  if (tone === 'critical') {
    return 'Attention required in the ML subsystem'
  }

  return 'ML health is only partially reported'
}

function buildStatusSubline(health: MLHealthData): string {
  if (health.status === 'DOWN') {
    return 'Serving is down in the latest snapshot. Immediate investigation is required.'
  }

  if (health.status === 'DEGRADED') {
    return 'Serving is available but operating outside preferred limits.'
  }

  if (health.drift_status === 'CRITICAL') {
    return 'Drift monitoring reported a critical signal in the latest snapshot.'
  }

  if (health.drift_status === 'WARNING') {
    return 'Drift monitoring reported a warning signal in the latest snapshot.'
  }

  const unavailableCount = countUnavailableMonitoringSignals(health)
  if (unavailableCount > 0) {
    return `The latest snapshot includes serving health, but ${unavailableCount} monitoring signal${unavailableCount === 1 ? ' is' : 's are'} unavailable.`
  }

  return 'The latest snapshot reports healthy serving and no monitoring warnings.'
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
  const entries = Object.entries(health.per_class_f1 ?? {})
    .sort((a, b) => a[1] - b[1])

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
    ? 'Evaluation evidence is available in this snapshot.'
    : 'No evaluation evidence was reported for this snapshot.'
}

function buildDistributionSummary(health: MLHealthData): string {
  const distribution = health.prediction_distribution
  if (!distribution) {
    return 'Prediction counts are unavailable for this snapshot.'
  }

  return Object.keys(distribution.baseline).length > 0
    ? 'Current prediction counts can be compared with the supplied baseline.'
    : 'Current prediction counts are available; no reference baseline was supplied, so change is not calculated.'
}

function buildCalibrationSummary(ece: number | null | undefined): string {
  if (ece == null) {
    return 'Expected calibration error is unavailable in this snapshot.'
  }

  return 'Expected calibration error is available; no acceptance threshold is provided.'
}

export function buildMLHealthViewModel(health: MLHealthData): MLHealthViewModel {
  const driftScore = health.drift_score
  const ece = health.ece
  const hasTraffic = health.traffic_processed > 0
  const distributionHasBaseline = Object.keys(health.prediction_distribution?.baseline ?? {}).length > 0

  return {
    tone: deriveHealthTone(health),
    statusHeadline: buildStatusHeadline(health),
    statusSubline: buildStatusSubline(health),
    displayName: deriveDisplayName(health.model_version),
    windowLabel: 'Reported window',
    granularityLabel: 'Snapshot-based',
    retrievedAtDisplay: formatStableDateTime(health.retrieved_at, 'Not available'),
    sourceFreshnessDisplay: 'Source timestamp unavailable',
    hasTraffic,
    trafficProcessedDisplay: formatCount(health.traffic_processed),
    latencyDisplay: hasTraffic ? `${health.latency_ms.toFixed(1)}ms` : 'Unavailable',
    latencyTrendDisplay:
      health.latency_trend == null ? 'No baseline supplied' : `${health.latency_trend > 0 ? '+' : ''}${health.latency_trend.toFixed(1)}ms`,
    evaluationEvidenceSummary: buildEvaluationEvidenceSummary(health),
    evaluationProvenanceDisplay: hasReportedEvaluationEvidence(health)
      ? 'Evaluation run identity and timestamp are unavailable.'
      : 'Evaluation provenance is unavailable.',
    distributionSummary: buildDistributionSummary(health),
    driftScoreDisplay: driftScore == null ? 'Unavailable' : driftScore.toFixed(3),
    driftStatusDisplay: health.drift_status ?? 'Unavailable',
    eceDisplay: ece == null ? 'Unavailable' : ece.toFixed(3),
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
