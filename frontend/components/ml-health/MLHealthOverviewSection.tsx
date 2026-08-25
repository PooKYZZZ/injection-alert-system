import { ChevronRight } from 'lucide-react'

import type { MLHealthData } from '@/features/ml-health/types'

import type { DiagnosticTab, HealthTone, MLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
  onNavigateToDiagnostics: (tab: DiagnosticTab) => void
}

function toneClass(tone: HealthTone): string {
  if (tone === 'healthy') return styles.toneHealthy
  if (tone === 'warning') return styles.toneWarning
  if (tone === 'critical') return styles.toneCritical
  return styles.toneUnknown
}

function monitoringTone(status: MLHealthData['drift_status']): HealthTone {
  if (status === 'NORMAL') return 'healthy'
  if (status === 'WARNING') return 'warning'
  if (status === 'CRITICAL') return 'critical'
  return 'unknown'
}

function monitoringLabel(status: MLHealthData['drift_status']): string {
  if (status === 'NORMAL') return 'Normal'
  if (status === 'WARNING') return 'Warning'
  if (status === 'CRITICAL') return 'Critical'
  return 'Not reported'
}

function monitoringDetail(status: MLHealthData['drift_status']): string {
  if (status === 'NORMAL') return 'No drift warning was reported in this snapshot.'
  if (status === 'WARNING') return 'A drift signal was reported for review.'
  if (status === 'CRITICAL') return 'A critical drift signal was reported.'
  return 'No drift result was included in this snapshot.'
}

function calibrationLabel(ece: number | null | undefined): string {
  return ece == null ? 'Not reported' : 'Reported'
}

function calibrationDetail(ece: number | null | undefined): string {
  return ece == null
    ? 'No calibration result was included in this snapshot.'
    : 'Calibration evidence is included; no acceptance threshold is provided.'
}

function SignalRow({
  label,
  value,
  detail,
  tone,
}: {
  label: string
  value: string
  detail: string
  tone: HealthTone
}) {
  return (
    <div className={`${styles.signalRow} ${toneClass(tone)}`}>
      <strong className={styles.signalRowLabel}>{label}</strong>
      <div className={styles.signalRowStatus}>
        <span className={`${styles.signalRowValue} ${value === 'Not reported' ? styles.unavailableValue : ''}`}>{value}</span>
        <span className={styles.signalRowDetail}>{detail}</span>
      </div>
    </div>
  )
}

function EvidenceLink({
  label,
  value,
  onClick,
  ariaLabel,
}: {
  label: string
  value: string
  onClick: () => void
  ariaLabel: string
}) {
  return (
    <button type="button" className={styles.evidenceLink} onClick={onClick} aria-label={ariaLabel}>
      <span className={styles.evidenceLinkCopy}>
        <strong>{label}</strong>
        <span>{value}</span>
      </span>
      <ChevronRight size={16} aria-hidden="true" />
    </button>
  )
}

export function MLHealthOverviewSection({ health, viewModel, onNavigateToDiagnostics }: Props) {
  return (
    <div className={styles.overview}>
      <section className={styles.statusGrid} aria-label="ML health status">
        <div className={`${styles.statusCard} ${toneClass(viewModel.servingTone)}`}>
          <h2 id="ml-health-serving-heading">Serving</h2>
          <strong className={styles.statusValue}>{viewModel.servingStatusLabel}</strong>
          <p className={styles.statusCardDetail}>{viewModel.servingStatusDetail}</p>
        </div>
        <div className={`${styles.statusCard} ${toneClass(viewModel.monitoringTone)}`}>
          <h2 id="ml-health-monitoring-heading">Monitoring</h2>
          <strong className={styles.statusValue}>{viewModel.monitoringStatusLabel}</strong>
          <p className={styles.statusCardDetail}>{viewModel.monitoringStatusDetail}</p>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="monitoring-coverage-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="monitoring-coverage-heading">Monitoring coverage</h2>
          </div>
          <p className={styles.sectionDescription}>Reported signals from this snapshot.</p>
        </div>
        <div className={styles.signalList}>
          <SignalRow
            label="Feature drift"
            value={monitoringLabel(health.drift_status)}
            detail={monitoringDetail(health.drift_status)}
            tone={monitoringTone(health.drift_status)}
          />
          <SignalRow
            label="Calibration evidence"
            value={calibrationLabel(health.ece)}
            detail={calibrationDetail(health.ece)}
            tone={health.ece == null ? 'unknown' : 'healthy'}
          />
        </div>
      </section>

      <section className={styles.section} aria-labelledby="runtime-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="runtime-heading">Runtime</h2>
          </div>
          <p className={styles.sectionDescription}>Requests and latency from this snapshot.</p>
        </div>
        <p className={styles.runtimeSummary}>
          {viewModel.hasTraffic
            ? 'Serving traffic is present; latency is measured from the reported requests.'
            : 'No serving traffic in this snapshot. Latency is not available without traffic.'}
        </p>
        <dl className={styles.metricList}>
          <div className={styles.metricRow}>
            <dt>Requests in snapshot</dt>
            <dd>{viewModel.trafficProcessedDisplay}</dd>
          </div>
          <div className={styles.metricRow}>
            <dt>Inference latency</dt>
            <dd className={viewModel.latencyDisplay === 'Not available' ? styles.unavailableValue : ''}>{viewModel.latencyDisplay}</dd>
          </div>
          <div className={styles.metricRow}>
            <dt>Latency comparison</dt>
            <dd className={viewModel.latencyTrendDisplay === 'No previous latency available' ? styles.unavailableValue : ''}>{viewModel.latencyTrendDisplay}</dd>
          </div>
        </dl>
      </section>

      <section className={`${styles.section} ${styles.evidenceSection}`} aria-labelledby="evidence-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="evidence-heading">Evidence</h2>
          </div>
          <p className={styles.sectionDescription}>Open detailed evidence in Diagnostics.</p>
        </div>

        <div className={styles.evidenceLinks}>
          <EvidenceLink
            label="Model evaluation"
            value={viewModel.classMetrics.length > 0
              ? `${viewModel.classMetrics.length} classes reported · provenance incomplete`
              : 'No per-class metrics reported'}
            ariaLabel="Open Model evaluation diagnostics"
            onClick={() => onNavigateToDiagnostics('evaluation')}
          />
          <EvidenceLink
            label="Confidence policy"
            value="4 bands · configured action mapping"
            ariaLabel="Open Confidence policy diagnostics"
            onClick={() => onNavigateToDiagnostics('policy')}
          />
        </div>
      </section>
    </div>
  )
}
