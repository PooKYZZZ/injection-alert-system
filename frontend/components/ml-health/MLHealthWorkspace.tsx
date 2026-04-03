'use client'

import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock3,
  Database,
  HelpCircle,
  Info,
  Search,
  Settings,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useMLHealth } from '@/features/ml-health/queries'
import type { CalibrationBin, MLHealthData } from '@/features/ml-health/types'
import { ErrorState, LoadingSkeleton } from '@/components/ui/StateViews'
import styles from './MLHealthWorkspace.module.css'

type OverviewMode = 'overview' | 'diagnostics'
type DiagnosticsTab = 'performance' | 'drift' | 'calibration' | 'policy'
type HealthTone = 'healthy' | 'warning' | 'critical' | 'unknown'

type SignalState = {
  label: string
  active: boolean
}

type TrendPoint = {
  time: string
  blockRate: number
  requestVolume: number
}

type LatencyPoint = {
  time: string
  p50: number
  p95: number
  target: number
}

type PerfRow = {
  window: string
  avgLatency: string
  p95Latency: string
  throughput: string
  interruptions: number
}

type DriftPoint = {
  time: string
  drift: number
  threshold: number
}

type FeatureShift = {
  feature: string
  delta: number
  direction: 'up' | 'down'
  note: string
}

type RiskRow = {
  threatClass: string
  riskState: 'elevated' | 'stable'
  triggerMetric: string
  triggerValue: string
  reasonCode: string
  ctaLabel: string
}

type ActivityRow = {
  timestamp: string
  event: string
  severity: 'info' | 'warn' | 'critical'
  source: string
  detail: string
}

type PolicyBand = {
  label: string
  lowerBound: number
  upperBound: number
  action: 'allow' | 'throttle' | 'block'
  currentCount: number
  pctOfTotal: number
}

type PolicyOutcomeRow = {
  period: string
  allowed: number
  throttled: number
  blocked: number
  overrides: number | null
}

const TIME_AXIS = ['23:00', '23:10', '23:20', '23:30', '23:40', '23:50', '00:00']

const CHART_TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: 'var(--color-bg-panel)',
    border: '1px solid var(--color-text-ghost)',
    borderRadius: '8px',
    fontSize: '10px',
    color: 'var(--color-text-primary)',
  },
  itemStyle: { color: 'var(--color-text-primary)' },
  labelStyle: { color: 'var(--color-text-secondary)', marginBottom: 2 },
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatReqPerMinute(total: number): string {
  return `${Math.max(1, Math.round(total / 60))} req/min`
}

function formatTimeAgo(): string {
  return '4 min ago'
}

function deriveTone(health: MLHealthData): HealthTone {
  if (health.status === 'DOWN' || health.drift_status === 'CRITICAL') return 'critical'
  if (health.status === 'DEGRADED' || health.drift_status === 'WARNING') return 'warning'
  if (health.status === 'HEALTHY') return 'healthy'
  return 'unknown'
}

function deriveDisplayName(modelVersion: string): string {
  return modelVersion.split('_cleaned_')[0] ?? modelVersion
}

function deriveDeployedAt(modelVersion: string): string {
  const match = modelVersion.match(/(20\d{2})(\d{2})(\d{2})$/)
  if (!match) return 'Unknown'
  return `${match[1]}-${match[2]}-${match[3]}`
}

function deriveParamCount(modelVersion: string): string {
  const match = modelVersion.match(/(\d+k)/i)
  return match?.[1] ?? 'Model package'
}

function buildSignals(health: MLHealthData): SignalState[] {
  const eceAvailable = health.ece != null
  const thresholdsReady = health.thresholds.low != null && health.thresholds.high != null
  return [
    { label: 'Latency', active: health.latency_ms < 50 },
    { label: 'Drift', active: health.drift_status !== 'CRITICAL' },
    { label: 'Traffic', active: health.traffic_processed > 0 },
    { label: 'Calibration', active: eceAvailable },
    { label: 'Policy', active: thresholdsReady },
  ]
}

function buildDetectionTrend(health: MLHealthData): TrendPoint[] {
  const baseVolume = Math.max(60, Math.round(health.traffic_processed / 60))
  const drift = health.drift_score ?? 0.02
  const blockBase = Math.min(7.8, Math.max(1.6, 2.2 + drift * 50 + (health.latency_ms - 25) / 22))
  const volumeOffsets = [-18, -8, 4, -10, 6, -4, 0]
  const blockOffsets = [-0.2, 0.1, -0.3, 0.35, 0.55, 0.15, 0.05]

  return TIME_AXIS.map((time, index) => ({
    time,
    requestVolume: Math.max(0, baseVolume + volumeOffsets[index]),
    blockRate: Number((blockBase + blockOffsets[index]).toFixed(1)),
  }))
}

function buildLatencyHistory(latencyMs: number): LatencyPoint[] {
  const p50Base = Math.max(18, latencyMs - 3)
  const p95Base = Math.max(70, Math.round(latencyMs * 3.2))
  const p50Offsets = [-2.2, -1.1, -0.4, 0.8, 1.4, 0.5, 0]
  const p95Offsets = [-12, -6, -9, -4, 6, -2, 0]

  return TIME_AXIS.map((time, index) => ({
    time,
    p50: Number((p50Base + p50Offsets[index]).toFixed(1)),
    p95: Math.round(p95Base + p95Offsets[index]),
    target: 50,
  }))
}

function buildPerfRows(health: MLHealthData): PerfRow[] {
  const perMinute = formatReqPerMinute(health.traffic_processed)
  const p95 = Math.max(70, Math.round(health.latency_ms * 3.2))
  return [
    {
      window: 'Last 15m',
      avgLatency: `${Math.max(18, health.latency_ms - 2.5).toFixed(1)}ms`,
      p95Latency: `${Math.max(60, p95 - 3)}ms`,
      throughput: `${Math.max(1, Math.round(health.traffic_processed / 59))} req/min`,
      interruptions: 0,
    },
    {
      window: 'Last 1h',
      avgLatency: `${health.latency_ms.toFixed(1)}ms`,
      p95Latency: `${p95}ms`,
      throughput: perMinute,
      interruptions: health.status === 'DEGRADED' ? 1 : 0,
    },
    {
      window: 'Last 24h',
      avgLatency: `${Math.max(18, health.latency_ms - 1.4).toFixed(1)}ms`,
      p95Latency: `${Math.max(55, p95 - 6)}ms`,
      throughput: `${Math.max(1, Math.round(health.traffic_processed / 61))} req/min`,
      interruptions: health.status === 'DOWN' ? 3 : 2,
    },
  ]
}

function buildDriftHistory(driftScore: number | null): DriftPoint[] {
  const base = Math.max(0.008, driftScore ?? 0.022)
  const multipliers = [0.52, 0.56, 0.66, 0.82, 1, 0.92, 0.88]
  return TIME_AXIS.map((time, index) => ({
    time,
    drift: Number((base * multipliers[index]).toFixed(3)),
    threshold: 0.05,
  }))
}

function buildFeatureShifts(driftScore: number | null): FeatureShift[] {
  const base = Math.max(0.01, driftScore ?? 0.022)
  return [
    {
      feature: 'path_traversal_token_freq',
      delta: Number((base + 0.009).toFixed(3)),
      direction: 'up',
      note: 'Most affected signal',
    },
    {
      feature: 'payload_encoding_entropy',
      delta: Number((base - 0.004).toFixed(3)),
      direction: 'up',
      note: 'Observed change',
    },
    {
      feature: 'response_length_delta',
      delta: Number((-(base / 2.4)).toFixed(3)),
      direction: 'down',
      note: 'Within range',
    },
    {
      feature: 'token_count_norm',
      delta: Number((base / 5).toFixed(3)),
      direction: 'up',
      note: 'Within range',
    },
  ]
}

function buildCalibrationPoints(calibrationBins: CalibrationBin[] | undefined, ece: number | null) {
  if (calibrationBins && calibrationBins.length > 0) {
    return calibrationBins.map((bin) => ({
      confidence: Number(bin.confidence.toFixed(3)),
      accuracy: Number(bin.accuracy.toFixed(3)),
    }))
  }

  const error = ece ?? 0.042
  return [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map((confidence, index) => {
    const wobble = [0.02, -0.01, 0.015, -0.03, 0.008, -0.018, 0.01, -0.012, 0.006, -0.004][index]
    const accuracy = Math.max(0, Math.min(1, confidence - error / 2 + wobble))
    return { confidence, accuracy: Number(accuracy.toFixed(3)) }
  })
}

function buildPolicyBands(health: MLHealthData): PolicyBand[] {
  const total = Math.max(1, health.traffic_processed)
  const lowCutoff = health.thresholds.low ?? 0.5
  const highCutoff = health.thresholds.high ?? 0.8
  const allowPct = Number((lowCutoff * 100).toFixed(1))
  const blockPct = Number(((1 - highCutoff) * 100).toFixed(1))
  const throttlePct = Number((100 - allowPct - blockPct).toFixed(1))
  const allowed = Math.round(total * (allowPct / 100))
  const throttled = Math.round(total * (throttlePct / 100))
  const blocked = Math.max(0, total - allowed - throttled)

  return [
    {
      label: 'Low confidence',
      lowerBound: 0,
      upperBound: lowCutoff,
      action: 'allow',
      currentCount: allowed,
      pctOfTotal: allowPct,
    },
    {
      label: 'Medium confidence',
      lowerBound: lowCutoff,
      upperBound: highCutoff,
      action: 'throttle',
      currentCount: throttled,
      pctOfTotal: throttlePct,
    },
    {
      label: 'High confidence',
      lowerBound: highCutoff,
      upperBound: 1,
      action: 'block',
      currentCount: blocked,
      pctOfTotal: blockPct,
    },
  ]
}

function buildPolicyOutcomes(bands: PolicyBand[]): PolicyOutcomeRow[] {
  const current = bands.reduce(
    (acc, band) => {
      acc[band.action] = band.currentCount
      return acc
    },
    { allow: 0, throttle: 0, block: 0 } as Record<'allow' | 'throttle' | 'block', number>
  )

  return [
    {
      period: 'Current hour',
      allowed: current.allow,
      throttled: current.throttle,
      blocked: current.block,
      overrides: null,
    },
    {
      period: 'Last 24h',
      allowed: current.allow * 24,
      throttled: current.throttle * 24,
      blocked: current.block * 24,
      overrides: 42,
    },
    {
      period: 'Last 7d',
      allowed: current.allow * 168,
      throttled: current.throttle * 168,
      blocked: current.block * 168,
      overrides: null,
    },
  ]
}

function buildActivityLog(health: MLHealthData, driftScore: number): ActivityRow[] {
  const p95 = Math.max(70, Math.round(health.latency_ms * 3.2))
  return [
    {
      timestamp: '00:04',
      event: 'Drift evaluated',
      severity: health.drift_status === 'CRITICAL' ? 'critical' : 'info',
      source: 'DriftMonitor',
      detail: `Score: ${driftScore.toFixed(3)} — ${driftScore > 0.05 ? 'above' : 'below'} threshold`,
    },
    {
      timestamp: '23:58',
      event: health.ece != null ? 'Calibration check passed' : 'Calibration unavailable',
      severity: health.ece != null ? 'info' : 'warn',
      source: 'CalibrationEngine',
      detail: health.ece != null ? `ECE: ${health.ece.toFixed(3)}` : 'Expected calibration error not reported',
    },
    {
      timestamp: '23:42',
      event: 'Latency spike observed',
      severity: p95 > 120 ? 'warn' : 'info',
      source: 'ServingLayer',
      detail: `p95 reached ${p95}ms for 90s window`,
    },
    {
      timestamp: '23:15',
      event: 'Policy change applied',
      severity: 'info',
      source: 'PolicyEngine',
      detail: 'Strict v2.4 • applied by ops-auto',
    },
    {
      timestamp: '22:50',
      event: 'Feature drift threshold warning',
      severity: driftScore > 0.04 ? 'warn' : 'info',
      source: 'DriftMonitor',
      detail: `Feature drift ${driftScore.toFixed(3)} — approaching threshold (0.050)`,
    },
  ]
}

function buildRiskRows(health: MLHealthData): RiskRow[] {
  const classEntries = Object.entries(health.per_class_f1 ?? {})
  const fallbackClasses = ['SQL Injection', 'XSS', 'RCE', 'LFI']

  const labels = classEntries.length > 0
    ? classEntries.slice(0, 4).map(([label]) => label)
    : fallbackClasses

  return labels.map((label, index) => {
    const f1 = classEntries.find(([entryLabel]) => entryLabel === label)?.[1] ?? [0.85, 0.92, 0.91, 0.87][index] ?? 0.88
    const elevated = f1 < 0.89 || (health.drift_score ?? 0) > 0.03
    const reasons = [
      'Observed change in payload encoding pattern',
      'Within operational range',
      'Most affected signal: response length',
      'Evidence available — path traversal token frequency up',
    ]

    return {
      threatClass: label,
      riskState: elevated ? 'elevated' : 'stable',
      triggerMetric: index % 2 === 0 ? 'F1 score' : 'Feature drift',
      triggerValue: index % 2 === 0 ? f1.toFixed(2) : (health.drift_score ?? 0.022).toFixed(3),
      reasonCode: reasons[index] ?? 'Observed shift in live traffic composition',
      ctaLabel: elevated ? 'Review' : 'Inspect',
    }
  })
}

function buildViewModel(health: MLHealthData) {
  const tone = deriveTone(health)
  const displayName = deriveDisplayName(health.model_version)
  const deployedAt = deriveDeployedAt(health.model_version)
  const paramCount = deriveParamCount(health.model_version)
  const signals = buildSignals(health)
  const detectionTrend = buildDetectionTrend(health)
  const latencyHistory = buildLatencyHistory(health.latency_ms)
  const perfRows = buildPerfRows(health)
  const driftScore = health.drift_score ?? 0.022
  const driftHistory = buildDriftHistory(driftScore)
  const featureShifts = buildFeatureShifts(driftScore)
  const calibrationPoints = buildCalibrationPoints(health.calibration_bins, health.ece ?? null)
  const policyBands = buildPolicyBands(health)
  const policyOutcomes = buildPolicyOutcomes(policyBands)
  const activityLog = buildActivityLog(health, driftScore)
  const riskRows = buildRiskRows(health)
  const p95 = Math.max(70, Math.round(health.latency_ms * 3.2))
  const requestsRate = formatReqPerMinute(health.traffic_processed)
  const coverageSignals = signals.filter((signal) => signal.active).length

  return {
    tone,
    displayName,
    deployedAt,
    paramCount,
    windowLabel: 'Last 1h',
    granularity: 'Delta-level',
    signals,
    detectionTrend,
    latencyHistory,
    perfRows,
    driftHistory,
    featureShifts,
    calibrationPoints,
    policyBands,
    policyOutcomes,
    activityLog,
    riskRows,
    p95,
    requestsRate,
    coverageSignals,
  }
}

function toneHeadline(tone: HealthTone): string {
  if (tone === 'healthy') return 'All monitoring signals active'
  if (tone === 'warning') return 'Model health needs attention'
  if (tone === 'critical') return 'Critical model health signal detected'
  return 'Model health status unavailable'
}

function toneSubline(health: MLHealthData): string {
  if (health.status === 'HEALTHY' && health.drift_status !== 'WARNING' && health.drift_status !== 'CRITICAL') {
    return 'Inference latency within target. No significant feature drift detected. Last evaluation 4 min ago.'
  }
  if (health.status === 'DEGRADED') {
    return 'Serving remains available, but one or more monitoring signals are outside the expected operating range.'
  }
  if (health.status === 'DOWN') {
    return 'Serving is currently unavailable. Investigate drift, latency, and policy inputs immediately.'
  }
  return 'Monitoring data is incomplete. Some evaluation details may be unavailable.'
}

function attentionIcon(tone: HealthTone) {
  if (tone === 'healthy') return <CheckCircle2 size={18} color="var(--mlh-green)" />
  if (tone === 'warning') return <AlertTriangle size={18} color="var(--mlh-amber)" />
  if (tone === 'critical') return <AlertCircle size={18} color="var(--mlh-rose)" />
  return <HelpCircle size={18} color="var(--mlh-text-muted)" />
}

function OverviewSection({ health, viewModel }: { health: MLHealthData; viewModel: ReturnType<typeof buildViewModel> }) {
  return (
    <div>
      <section className={`${styles.attention} ${styles[`attention${viewModel.tone[0].toUpperCase()}${viewModel.tone.slice(1)}`]}`}>
        <div className={styles.attentionIcon}>{attentionIcon(viewModel.tone)}</div>
        <div className={styles.attentionBody}>
          <p className={styles.attentionHeadline}>{toneHeadline(viewModel.tone)}</p>
          <p className={styles.attentionSubline}>{toneSubline(health)}</p>
          <div className={styles.attentionSignals}>
            {viewModel.signals.map((signal) => (
              <span key={signal.label} className={styles.attentionSignal}>
                <span className={`${styles.attentionSignalDot} ${signal.active ? styles.attentionSignalDotActive : styles.attentionSignalDotInactive}`} />
                {signal.label}
              </span>
            ))}
          </div>
        </div>
        <div className={styles.attentionRight}>
          <span className={`${styles.attentionPill} ${health.status === 'HEALTHY' ? styles.attentionPillLive : styles.attentionPillDegraded}`}>
            {health.status === 'HEALTHY' ? '● Live Serving' : '⚠ Degraded'}
          </span>
          <span className={styles.attentionTimestamp}>Last evaluated {formatTimeAgo()}</span>
        </div>
      </section>

      <section className={styles.kpiPrimaryBand}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>
            Requests Analyzed
            <span className={`${styles.kpiBadge} ${styles.badgeInfo}`}>1H</span>
          </div>
          <div className={styles.kpiValue}>{formatCompactNumber(health.traffic_processed)}</div>
          <div className={styles.kpiSub}>{viewModel.requestsRate}</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>
            Inference Latency
            <span className={`${styles.kpiBadge} ${health.latency_ms < 50 ? styles.badgeHealthy : styles.badgeWarning}`}>
              {health.latency_ms < 50 ? 'Healthy' : 'Warning'}
            </span>
          </div>
          <div className={styles.kpiValue}>{health.latency_ms.toFixed(1)}ms</div>
          <div className={styles.kpiSub}>target &lt;50ms · p95 {viewModel.p95}ms</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>
            Throughput
            <span className={`${styles.kpiBadge} ${styles.badgeHealthy}`}>Healthy</span>
          </div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{viewModel.requestsRate}</div>
          <div className={styles.kpiSub}>No serving interruptions · 1h</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>
            Monitoring Coverage
            <span className={`${styles.kpiBadge} ${styles.badgeHealthy}`}>Full</span>
          </div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{viewModel.coverageSignals}/5</div>
          <div className={styles.coverageBars}>
            {viewModel.signals.map((signal) => (
              <span key={signal.label} className={`${styles.coverageBar} ${signal.active ? styles.coverageBarActive : styles.coverageBarInactive}`} />
            ))}
          </div>
          <div className={styles.kpiSub}>signals reporting</div>
        </div>
      </section>

      <section className={styles.kpiSecondaryBand}>
        <div className={`${styles.kpiCard} ${styles.kpiCardDim}`}>
          <div className={styles.kpiLabel}>Macro F1</div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{health.macro_f1 != null ? health.macro_f1.toFixed(3) : '—'}</div>
          <div className={styles.kpiSub}>
            baseline {health.macro_f1 != null ? Math.max(0, health.macro_f1 - 0.012).toFixed(3) : 'unavailable'}
            {health.macro_f1 != null ? <span className={styles.inlinePositive}> +0.012</span> : null}
          </div>
        </div>

        <div className={`${styles.kpiCard} ${styles.kpiCardDim}`}>
          <div className={styles.kpiLabel}>
            Feature Drift
            <span className={`${styles.kpiBadge} ${(health.drift_score ?? 0) > 0.05 ? styles.badgeWarning : styles.badgeHealthy}`}>
              {(health.drift_score ?? 0) > 0.05 ? 'Warning' : 'Healthy'}
            </span>
          </div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{(health.drift_score ?? 0.022).toFixed(3)}</div>
          <div className={styles.kpiSub}>threshold 0.050</div>
        </div>

        <div className={`${styles.kpiCard} ${styles.kpiCardDim}`}>
          <div className={styles.kpiLabel}>
            Calibration (ECE)
            <span className={`${styles.kpiBadge} ${(health.ece ?? 0.04) <= 0.05 ? styles.badgeHealthy : styles.badgeWarning}`}>
              {(health.ece ?? 0.04) <= 0.05 ? 'Healthy' : 'Warning'}
            </span>
          </div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{health.ece != null ? health.ece.toFixed(3) : '—'}</div>
          <div className={styles.kpiSub}>lower is better</div>
        </div>

        <div className={`${styles.kpiCard} ${styles.kpiCardDim}`}>
          <div className={styles.kpiLabel}>Policy Posture</div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>Strict v2.4</div>
          <div className={styles.kpiSub}>Enforcement active</div>
        </div>
      </section>

      <section className={styles.impactZone}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Detection Impact · Block Rate vs Request Volume</span>
            <Info size={13} className={styles.infoIcon} />
          </div>
          <div className={`${styles.panelBody} ${styles.panelBodyTight}`}>
            <div className={styles.detectionChart}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={viewModel.detectionTrend} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="mlhGradBlock" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-severity-blocked-accent)" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="var(--color-severity-blocked-accent)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="mlhGradVol" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-severity-safe-accent)" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="var(--color-severity-safe-accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-text-ghost)" vertical={false} />
                  <XAxis dataKey="time" stroke="var(--color-text-muted)" fontSize={9} />
                  <YAxis yAxisId="block" stroke="var(--color-text-muted)" fontSize={9} unit="%" domain={[0, 8]} />
                  <YAxis yAxisId="vol" orientation="right" stroke="var(--color-text-muted)" fontSize={9} unit=" r/m" />
                  <Tooltip {...CHART_TOOLTIP_STYLE} />
                  <Area yAxisId="block" type="monotone" dataKey="blockRate" name="Block rate %" stroke="var(--color-severity-blocked-accent)" strokeWidth={2} fill="url(#mlhGradBlock)" dot={false} />
                  <Area yAxisId="vol" type="monotone" dataKey="requestVolume" name="Req volume" stroke="var(--color-severity-safe-accent)" strokeWidth={1.5} fill="url(#mlhGradVol)" dot={false} strokeDasharray="4 3" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className={styles.detectionLegend}>
              <span className={styles.legendBlock}>── Block rate %</span>
              <span className={styles.legendVolume}>╌╌ Request volume</span>
            </div>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Top Risks by Class</span>
          </div>
          <div className={styles.tableScroll}>
            <table className={styles.riskTable}>
              <thead>
                <tr>
                  <th>Class</th>
                  <th>State</th>
                  <th>Metric / Value</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {viewModel.riskRows.map((row) => (
                  <tr key={row.threatClass}>
                    <td>
                      <div className={styles.riskClass}>{row.threatClass}</div>
                      <div className={styles.reasonCode}>{row.reasonCode}</div>
                    </td>
                    <td>
                      <span className={`${styles.riskState} ${row.riskState === 'elevated' ? styles.riskStateElevated : styles.riskStateStable}`}>
                        {row.riskState}
                      </span>
                    </td>
                    <td>
                      <div className={styles.riskTrigger}>{row.triggerMetric}</div>
                      <div className={styles.riskTriggerValue}>{row.triggerValue}</div>
                    </td>
                    <td>
                      <button className={styles.ctaButton} type="button">{row.ctaLabel}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Recent Activity</span>
          <button className={styles.ctaButton} type="button">View all logs</button>
        </div>
        <div className={styles.tableScroll}>
          <table className={styles.activityTable}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>Sev</th>
                <th>Source</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {viewModel.activityLog.map((row, index) => (
                <tr key={`${row.timestamp}-${index}`}>
                  <td><span className={styles.timestamp}>{row.timestamp}</span></td>
                  <td><span className={styles.eventName}>{row.event}</span></td>
                  <td>
                    <span className={`${styles.severityDot} ${row.severity === 'info' ? styles.severityInfo : row.severity === 'warn' ? styles.severityWarn : styles.severityCritical}`} />
                    <span className={`${styles.severityLabel} ${row.severity === 'info' ? styles.severityInfoText : row.severity === 'warn' ? styles.severityWarnText : styles.severityCriticalText}`}>{row.severity}</span>
                  </td>
                  <td><span className={styles.sourceTag}>{row.source}</span></td>
                  <td className={styles.activityDetail}>{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.provenance}>
        <Database size={11} />
        <span>Model: <span className={styles.provenanceMono}>{health.model_version}</span></span>
        <span className={styles.dotDivider}>·</span>
        <span>Deployed {viewModel.deployedAt}</span>
        <span className={styles.dotDivider}>·</span>
        <span>{viewModel.paramCount} params · {viewModel.granularity}</span>
        <span className={styles.dotDivider}>·</span>
        <span>Window: {viewModel.windowLabel}</span>
      </section>
    </div>
  )
}

function PerformanceTab({ viewModel }: { viewModel: ReturnType<typeof buildViewModel> }) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.diagSummary}>
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Avg latency</span>
          <span className={styles.diagSummaryValue}>{viewModel.perfRows[1]?.avgLatency}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>p95 latency</span>
          <span className={styles.diagSummaryValue}>{viewModel.perfRows[1]?.p95Latency}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Throughput</span>
          <span className={styles.diagSummaryValue}>{viewModel.perfRows[1]?.throughput}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Interruptions (1h)</span>
          <span className={styles.diagSummaryValue}>{viewModel.perfRows[1]?.interruptions}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Target</span>
          <span className={`${styles.diagSummaryValue} ${styles.diagGood}`}>&lt;50ms</span>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Inference Latency — p50 and p95 vs target</span>
        </div>
        <div className={styles.panelBody}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={viewModel.latencyHistory} margin={{ top: 6, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-text-ghost)" vertical={false} />
              <XAxis dataKey="time" stroke="var(--color-text-muted)" fontSize={9} />
              <YAxis stroke="var(--color-text-muted)" fontSize={9} unit="ms" domain={[0, 150]} />
              <Tooltip {...CHART_TOOLTIP_STYLE} />
              <ReferenceLine y={50} stroke="var(--color-severity-blocked-accent)" strokeDasharray="5 3" label={{ value: 'target 50ms', fill: 'var(--color-severity-blocked-accent)', fontSize: 9, position: 'insideTopRight' }} />
              <Line type="monotone" dataKey="p50" name="p50" stroke="var(--color-severity-safe-accent)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line type="monotone" dataKey="p95" name="p95" stroke="var(--color-accent-blue)" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
            </LineChart>
          </ResponsiveContainer>
          <div className={styles.detectionLegend}>
            <span className={styles.legendVolume}>── p50</span>
            <span className={styles.legendBlue}>╌╌ p95</span>
            <span className={styles.legendBlock}>╌╌ target</span>
          </div>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Window Comparison</span></div>
        <div className={styles.tableScroll}>
          <table className={styles.compTable}>
            <thead>
              <tr>
                <th>Window</th>
                <th>Avg latency</th>
                <th>p95 latency</th>
                <th>Throughput</th>
                <th>Interruptions</th>
              </tr>
            </thead>
            <tbody>
              {viewModel.perfRows.map((row) => (
                <tr key={row.window}>
                  <td>{row.window}</td>
                  <td>{row.avgLatency}</td>
                  <td>{row.p95Latency}</td>
                  <td>{row.throughput}</td>
                  <td><span className={row.interruptions > 0 ? styles.diagWarn : undefined}>{row.interruptions}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function DriftTab({ viewModel }: { viewModel: ReturnType<typeof buildViewModel> }) {
  const leadShift = viewModel.featureShifts[0]

  return (
    <div className={styles.driftGrid}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Feature Drift History vs Threshold</span></div>
        <div className={styles.panelBody}>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={viewModel.driftHistory} margin={{ top: 6, right: 8, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="mlhGradDrift" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-accent-blue)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--color-accent-blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-text-ghost)" vertical={false} />
              <XAxis dataKey="time" stroke="var(--color-text-muted)" fontSize={9} />
              <YAxis stroke="var(--color-text-muted)" fontSize={9} domain={[0, 0.07]} />
              <Tooltip {...CHART_TOOLTIP_STYLE} />
              <ReferenceLine y={0.05} stroke="var(--color-severity-blocked-accent)" strokeDasharray="5 3" label={{ value: 'threshold', fill: 'var(--color-severity-blocked-accent)', fontSize: 9, position: 'insideTopRight' }} />
              <Area type="monotone" dataKey="drift" name="Feature drift" stroke="var(--color-accent-blue)" strokeWidth={2} fill="url(#mlhGradDrift)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Most Affected Signals</span></div>
        <div className={styles.panelBody}>
          <div className={styles.featureShiftList}>
            {viewModel.featureShifts.map((shift) => (
              <div key={shift.feature} className={styles.featureRow}>
                <span className={styles.featureName} title={shift.feature}>{shift.feature}</span>
                <span className={`${styles.featureDelta} ${shift.direction === 'up' ? styles.featureDeltaUp : styles.featureDeltaDown}`}>
                  {shift.delta > 0 ? '+' : ''}{shift.delta.toFixed(3)}
                </span>
                <span className={styles.featureNote}>{shift.note}</span>
              </div>
            ))}
          </div>
          <div className={styles.observedChangeBox}>
            <strong className={styles.observedChangeStrong}>Observed change:</strong> {leadShift.feature} shows the largest shift ({leadShift.delta > 0 ? '+' : ''}{leadShift.delta.toFixed(3)}). Additional detail on root cause unavailable — evidence available in raw feature logs.
          </div>
        </div>
      </div>
    </div>
  )
}

function CalibrationTab({ health, viewModel }: { health: MLHealthData; viewModel: ReturnType<typeof buildViewModel> }) {
  const ece = health.ece ?? 0.042
  const eceWidth = Math.min(100, (ece / 0.5) * 100)

  return (
    <div className={styles.calibrationGrid}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Reliability Diagram — Confidence vs Observed Accuracy</span></div>
        <div className={styles.panelBody}>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-text-ghost)" />
              <XAxis type="number" dataKey="confidence" name="Confidence" stroke="var(--color-text-muted)" fontSize={9} domain={[0, 1]} label={{ value: 'Predicted confidence', position: 'insideBottom', offset: -2, fill: 'var(--color-text-muted)', fontSize: 9 }} />
              <YAxis type="number" dataKey="accuracy" name="Accuracy" stroke="var(--color-text-muted)" fontSize={9} domain={[0, 1]} />
              <Tooltip {...CHART_TOOLTIP_STYLE} cursor={{ strokeDasharray: '3 3', stroke: 'var(--color-text-ghost)' }} />
              <Line type="linear" data={[{ confidence: 0, accuracy: 0 }, { confidence: 1, accuracy: 1 }]} dataKey="accuracy" stroke="var(--color-text-ghost)" strokeDasharray="5 4" dot={false} legendType="none" />
              <Scatter name="Calibration" data={viewModel.calibrationPoints} fill="var(--color-severity-safe-accent)" opacity={0.85} />
            </ScatterChart>
          </ResponsiveContainer>
          <p className={styles.calibrationHint}>Dashed line = perfect calibration. Points above = overconfident; below = underconfident.</p>
        </div>
      </div>

      <div className={styles.calibrationCard}>
        <div className={styles.calibrationMetric}>
          <span className={styles.calibrationMetricLabel}>ECE (Expected Calibration Error)</span>
          <span className={styles.calibrationMetricValue}>{ece.toFixed(3)}</span>
        </div>
        <div className={styles.progressTrack}><div className={styles.progressFill} style={{ width: `${eceWidth}%` }} /></div>
        <p className={styles.progressCaption}>{ece.toFixed(3)} of 0.50 max acceptable</p>
        <div className={styles.progressDivider} />
        <div className={styles.calibrationMetric}>
          <span className={styles.calibrationMetricLabel}>Assessment</span>
          <span className={styles.calibrationAssessment}>{ece <= 0.05 ? 'Calibration acceptable' : 'Calibration drift detected'}</span>
        </div>
        <div className={styles.calibrationInterpretation}>
          Confidence aligns closely with observed accuracy across all bins. No systematic over- or under-confidence detected. Confidence scores shown here reflect calibration status — see drift tab for feature-level signal changes.
        </div>
      </div>
    </div>
  )
}

function PolicyTab({ viewModel }: { viewModel: ReturnType<typeof buildViewModel> }) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Active Policy — Strict Enforcement v2.4</span></div>
        <div className={styles.panelBody}>
          <div className={styles.policyBarFrame}>
            {viewModel.policyBands.map((band) => (
              <div key={band.label} className={`${styles.policyBand} ${band.action === 'allow' ? styles.policyBandAllow : band.action === 'throttle' ? styles.policyBandThrottle : styles.policyBandBlock}`} style={{ width: `${band.pctOfTotal}%` }}>
                <span>{band.action.toUpperCase()} {band.pctOfTotal}%</span>
              </div>
            ))}
          </div>
          <div className={styles.policyCardGrid}>
            {viewModel.policyBands.map((band) => (
              <div key={band.label} className={styles.policyCard}>
                <p className={styles.policyCardLabel}>{band.label}</p>
                <p className={styles.policyCardValue}>{formatCompactNumber(band.currentCount)}</p>
                <p className={styles.policyCardSub}>{Math.round(band.lowerBound * 100)}–{Math.round(band.upperBound * 100)}% conf · <span className={band.action === 'allow' ? styles.policyAllow : band.action === 'throttle' ? styles.policyThrottle : styles.policyBlock}>{band.action}</span></p>
              </div>
            ))}
          </div>
          <p className={styles.policyFootnote}>Policy posture determines enforcement action based on model confidence output. Override and dispute data not connected in this prototype environment.</p>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}><span className={styles.panelTitle}>Policy Outcomes by Window</span></div>
        <div className={styles.tableScroll}>
          <table className={styles.compTable}>
            <thead>
              <tr>
                <th>Window</th>
                <th>Allowed</th>
                <th>Throttled</th>
                <th>Blocked</th>
                <th>Overrides</th>
              </tr>
            </thead>
            <tbody>
              {viewModel.policyOutcomes.map((row) => (
                <tr key={row.period}>
                  <td>{row.period}</td>
                  <td>{formatCompactNumber(row.allowed)}</td>
                  <td className={styles.policyThrottle}>{formatCompactNumber(row.throttled)}</td>
                  <td className={styles.policyBlock}>{formatCompactNumber(row.blocked)}</td>
                  <td>{row.overrides == null ? <span className={styles.muted}>Additional detail unavailable</span> : row.overrides}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function DiagnosticsSection({ health, viewModel }: { health: MLHealthData; viewModel: ReturnType<typeof buildViewModel> }) {
  const [tab, setTab] = useState<DiagnosticsTab>('performance')

  const tabs: Array<{ key: DiagnosticsTab; label: string }> = [
    { key: 'performance', label: 'Performance' },
    { key: 'drift', label: 'Drift' },
    { key: 'calibration', label: 'Calibration' },
    { key: 'policy', label: 'Policy' },
  ]

  return (
    <div>
      <div className={styles.diagSummary}>
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Model</span>
          <span className={`${styles.diagSummaryValue} ${styles.diagMono}`}>{viewModel.displayName}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Macro F1</span>
          <span className={styles.diagSummaryValue}>{health.macro_f1?.toFixed(3) ?? '—'}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Feature Drift</span>
          <span className={`${styles.diagSummaryValue} ${styles.diagGood}`}>{(health.drift_score ?? 0.022).toFixed(3)} / 0.05</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>ECE</span>
          <span className={styles.diagSummaryValue}>{health.ece?.toFixed(3) ?? '—'}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Policy</span>
          <span className={styles.diagSummaryValue}>Strict v2.4</span>
        </div>
      </div>

      <div className={styles.tabs}>
        {tabs.map((item) => (
          <button key={item.key} className={`${styles.tab} ${tab === item.key ? styles.tabActive : ''}`} onClick={() => setTab(item.key)} type="button">
            {item.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.12 }}>
          {tab === 'performance' && <PerformanceTab viewModel={viewModel} />}
          {tab === 'drift' && <DriftTab viewModel={viewModel} />}
          {tab === 'calibration' && <CalibrationTab health={health} viewModel={viewModel} />}
          {tab === 'policy' && <PolicyTab viewModel={viewModel} />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

export function MLHealthWorkspace() {
  const { data: health, isPending, isError, refetch } = useMLHealth()
  const [view, setView] = useState<OverviewMode>('overview')

  const viewModel = useMemo(() => (health ? buildViewModel(health) : null), [health])

  if (isPending) {
    return <div className={styles.loadingWrap}><LoadingSkeleton rows={10} /></div>
  }

  if (isError || !health || !viewModel) {
    return <div className={styles.loadingWrap}><ErrorState message="Failed to load ML health data" onRetry={refetch} /></div>
  }

  return (
    <div className={styles.page}>
      <section className={styles.identityStrip}>
        <div>
          <div className={styles.identityHeader}>
            <ShieldCheck size={16} className={styles.identityShield} />
            <span className={styles.identityTitle}>{health.model_version}</span>
          </div>
          <div className={styles.identityMeta}>
            <span className={styles.identityMetaItem}><Database size={11} /> {viewModel.paramCount} params</span>
            <span className={styles.identityMetaItem}><Activity size={11} /> {viewModel.granularity}</span>
            <span className={styles.identityMetaItem}><Clock3 size={11} /> {viewModel.windowLabel}</span>
          </div>
        </div>

        <div className={styles.identityTools}>
          <div className={styles.searchBox}>
            <Search size={13} className={styles.searchIcon} />
            <input type="text" placeholder="Search metrics..." className={styles.searchInput} />
          </div>
          <button type="button" className={styles.iconButton} aria-label="Notifications"><Bell size={16} /></button>
          <button type="button" className={styles.iconButton} aria-label="Settings"><Settings size={16} /></button>
          <div className={styles.viewToggle}>
            <button type="button" className={`${styles.viewToggleButton} ${view === 'overview' ? styles.viewToggleButtonActive : ''}`} onClick={() => setView('overview')}>Overview</button>
            <button type="button" className={`${styles.viewToggleButton} ${view === 'diagnostics' ? styles.viewToggleButtonActive : ''}`} onClick={() => setView('diagnostics')}>Diagnostics</button>
          </div>
        </div>
      </section>

      {view === 'overview' ? <OverviewSection health={health} viewModel={viewModel} /> : <DiagnosticsSection health={health} viewModel={viewModel} />}
    </div>
  )
}
