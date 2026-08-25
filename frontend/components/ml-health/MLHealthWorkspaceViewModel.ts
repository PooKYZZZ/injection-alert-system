import type { CalibrationBin, MLHealthData } from '@/features/ml-health/types'

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
  isElevated: boolean
}

export type DistributionRowView = {
  label: string
  baselineDisplay: string
  currentDisplay: string
  deltaDisplay: string
}

export type MLHealthViewModel = {
  tone: HealthTone
  statusHeadline: string
  statusSubline: string
  displayName: string
  windowLabel: string
  granularityLabel: string
  trafficProcessedDisplay: string
  latencyDisplay: string
  latencyTrendDisplay: string
  evaluationEvidenceSummary: string
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

function buildStatusHeadline(tone: HealthTone): string {
  if (tone === 'healthy') {
    return 'All core health signals are within expected range'
  }

  if (tone === 'warning') {
    return 'One or more health signals require review'
  }

  if (tone === 'critical') {
    return 'Critical health signal detected'
  }

  return 'Health signals are partially reported'
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

  return 'Latest snapshot indicates healthy serving and no critical drift alerts.'
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
      { label: 'Low confidence non-Normal', action: 'allow', rangeLabel: 'Not configured' },
      { label: 'Medium confidence non-Normal', action: 'throttle', rangeLabel: 'Not configured' },
      { label: 'High confidence non-Normal', action: 'block', rangeLabel: 'Not configured' },
      { label: 'Critical confidence non-Normal', action: 'block', rangeLabel: 'Not configured' },
    ]
  }

  const lowPct = Math.round(low * 100)
  const highPct = Math.round(high * 100)
  const criticalPct = Math.round(critical * 100)

  return [
    { label: 'Low confidence non-Normal', action: 'allow', rangeLabel: `<${lowPct}%` },
    { label: 'Medium confidence non-Normal', action: 'throttle', rangeLabel: `${lowPct}%-${highPct}%` },
    { label: 'High confidence non-Normal', action: 'block', rangeLabel: `>${highPct}%-<${criticalPct}%` },
    { label: 'Critical confidence non-Normal', action: 'block', rangeLabel: `>=${criticalPct}%` },
  ]
}

function buildClassMetrics(health: MLHealthData): ClassMetricView[] {
  const entries = Object.entries(health.per_class_f1 ?? {})
    .sort((a, b) => a[1] - b[1])

  return entries.map(([label, value]) => ({
    label,
    f1Display: value.toFixed(3),
    isElevated: value < 0.89,
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

  return [...labels]
    .sort((a, b) => a.localeCompare(b))
    .map((label) => {
      const baseline = distribution.baseline[label] ?? null
      const current = distribution.current[label] ?? null
      const delta = baseline != null && current != null ? current - baseline : null

      return {
        label,
        baselineDisplay: formatNullableCount(baseline),
        currentDisplay: formatNullableCount(current),
        deltaDisplay: delta == null ? 'Not reported' : `${delta > 0 ? '+' : ''}${delta}`,
      }
    })
}

function buildEvaluationEvidenceSummary(health: MLHealthData): string {
  const hasEvidence =
    health.macro_f1 != null ||
    health.ece != null ||
    Object.keys(health.per_class_f1 ?? {}).length > 0 ||
    (health.calibration_bins?.length ?? 0) > 0

  return hasEvidence
    ? 'Reported evaluation evidence is separate from current traffic quality.'
    : 'Evaluation evidence is not reported in this snapshot.'
}

function buildDistributionSummary(health: MLHealthData): string {
  const distribution = health.prediction_distribution
  if (!distribution) {
    return 'Prediction counts are not reported in this snapshot.'
  }

  return Object.keys(distribution.baseline).length > 0
    ? 'Current prediction counts are reported against a supplied reference baseline.'
    : 'Current prediction counts are reported; no reference baseline was supplied.'
}

function buildCalibrationSummary(ece: number | null | undefined): string {
  if (ece == null) {
    return 'Expected calibration error not reported in this snapshot.'
  }

  if (ece <= 0.05) {
    return 'Calibration is within the preferred range (<= 0.050).'
  }

  return 'Calibration is above the preferred range (> 0.050).'
}

export function buildMLHealthViewModel(health: MLHealthData): MLHealthViewModel {
  const driftScore = health.drift_score
  const ece = health.ece

  return {
    tone: deriveHealthTone(health),
    statusHeadline: buildStatusHeadline(deriveHealthTone(health)),
    statusSubline: buildStatusSubline(health),
    displayName: deriveDisplayName(health.model_version),
    windowLabel: 'Reported window',
    granularityLabel: 'Snapshot-based',
    trafficProcessedDisplay: formatCount(health.traffic_processed),
    latencyDisplay:
      health.traffic_processed > 0 ? `${health.latency_ms.toFixed(1)}ms` : 'Not measured',
    latencyTrendDisplay:
      health.latency_trend == null ? 'No trend reported' : `${health.latency_trend > 0 ? '+' : ''}${health.latency_trend.toFixed(1)}ms`,
    evaluationEvidenceSummary: buildEvaluationEvidenceSummary(health),
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
    distributionRows: buildDistributionRows(health),
    calibrationBins: health.calibration_bins ?? [],
  }
}
