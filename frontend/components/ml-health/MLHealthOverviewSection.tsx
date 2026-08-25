import { ChevronDown } from 'lucide-react'

import type { MLHealthData } from '@/features/ml-health/types'

import type { MLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type Tone = MLHealthViewModel['tone']

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
}

function toneClass(tone: Tone): string {
  if (tone === 'healthy') return styles.toneHealthy
  if (tone === 'warning') return styles.toneWarning
  if (tone === 'critical') return styles.toneCritical
  return styles.toneUnknown
}

function monitoringTone(status: MLHealthData['drift_status']): Tone {
  if (status === 'NORMAL') return 'healthy'
  if (status === 'WARNING') return 'warning'
  if (status === 'CRITICAL') return 'critical'
  return 'unknown'
}

function monitoringLabel(status: MLHealthData['drift_status']): string {
  if (status === 'NORMAL') return 'Normal'
  if (status === 'WARNING') return 'Warning'
  if (status === 'CRITICAL') return 'Critical'
  return 'Unavailable'
}

function monitoringDetail(status: MLHealthData['drift_status']): string {
  if (status === 'NORMAL') return 'The latest snapshot reports no drift warning.'
  if (status === 'WARNING') return 'The latest snapshot contains a drift signal to review.'
  if (status === 'CRITICAL') return 'The latest snapshot contains a critical drift signal.'
  return 'No drift result was included in this snapshot.'
}

function calibrationLabel(ece: number | null | undefined): string {
  return ece == null ? 'Unavailable' : 'Available'
}

function calibrationDetail(ece: number | null | undefined): string {
  return ece == null
    ? 'No calibration result was included in this snapshot.'
    : 'An expected calibration error value is available; no acceptance threshold is provided.'
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
  tone: Tone
}) {
  return (
    <div className={`${styles.signalRow} ${toneClass(tone)}`}>
      <div className={styles.signalRowLabel}>
        <span className={styles.signalMarker} aria-hidden="true" />
        <strong>{label}</strong>
      </div>
      <span className={`${styles.signalRowValue} ${value === 'Unavailable' ? styles.unavailableValue : ''}`}>{value}</span>
      <span className={styles.signalRowDetail}>{detail}</span>
    </div>
  )
}

function PolicyTable({ viewModel }: { viewModel: MLHealthViewModel }) {
  return (
    <div className={styles.tableScroll}>
      <table className={styles.compTable} aria-label="Non-Normal policy bands">
        <thead>
          <tr>
            <th scope="col">Confidence band</th>
            <th scope="col">Range</th>
            <th scope="col">Automatic action</th>
          </tr>
        </thead>
        <tbody>
          {viewModel.policyBands.map((band) => (
            <tr key={band.label}>
              <td>{band.label}</td>
              <td className={styles.mono}>{band.rangeLabel}</td>
              <td>
                <span className={styles[`policy${band.action[0].toUpperCase()}${band.action.slice(1)}` as 'policyAllow' | 'policyThrottle' | 'policyBlock']}>
                  {band.action}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MLHealthOverviewSection({ health, viewModel }: Props) {
  return (
    <div className={styles.overview}>
      <section className={`${styles.statusHero} ${toneClass(viewModel.tone)}`} aria-labelledby="ml-health-status-heading">
        <div className={styles.statusHeroMain}>
          <h2 id="ml-health-status-heading">{viewModel.statusHeadline}</h2>
          <p className={styles.statusSubline}>{viewModel.statusSubline}</p>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="monitoring-coverage-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="monitoring-coverage-heading">Monitoring coverage</h2>
          </div>
          <p className={styles.sectionDescription}>Results included in the current snapshot.</p>
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

      <section className={styles.section} aria-labelledby="serving-snapshot-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="serving-snapshot-heading">Runtime snapshot</h2>
          </div>
          <p className={styles.sectionDescription}>Traffic and latency from this snapshot.</p>
        </div>
        <dl className={styles.metricList}>
          <div className={styles.metricRow}>
            <dt>Requests in snapshot</dt>
            <dd>{viewModel.trafficProcessedDisplay}</dd>
            <p>Requests included in this health response</p>
          </div>
          <div className={styles.metricRow}>
            <dt>Inference latency</dt>
            <dd className={viewModel.latencyDisplay === 'Unavailable' ? styles.unavailableValue : ''}>{viewModel.latencyDisplay}</dd>
            <p>Measured only when traffic is reported</p>
          </div>
          <div className={styles.metricRow}>
            <dt>Latency comparison</dt>
            <dd className={viewModel.latencyTrendDisplay === 'No baseline supplied' ? styles.unavailableValue : ''}>{viewModel.latencyTrendDisplay}</dd>
            <p>Change from the previous result, when supplied</p>
          </div>
        </dl>
      </section>

      <section className={`${styles.section} ${styles.evidenceSection}`} aria-labelledby="evidence-policy-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="evidence-policy-heading">Evidence</h2>
          </div>
          <p className={styles.sectionDescription}>Open a section when the snapshot needs investigation.</p>
        </div>

        <div className={styles.disclosureGrid}>
          <details className={styles.disclosure}>
            <summary>
              <span className={styles.summaryTitle}>
                <strong>Model quality evidence</strong>
              </span>
              <span className={styles.summaryValue}>{viewModel.classMetrics.length > 0 ? `${viewModel.classMetrics.length} classes` : 'No per-class metrics'}</span>
              <ChevronDown size={16} aria-hidden="true" className={styles.disclosureChevron} />
            </summary>
            <div className={styles.disclosureBody}>
              <p className={styles.evidenceNote}>{viewModel.evaluationEvidenceSummary}</p>
              {viewModel.classMetrics.length > 0 ? (
                <p className={styles.evidenceNote}>{viewModel.classMetrics.length} per-class metric{viewModel.classMetrics.length === 1 ? '' : 's'} reported. Open Diagnostics for the detailed tables.</p>
              ) : <p className={styles.emptyEvidence}>Per-class metrics are not included in this snapshot.</p>}
              <p className={styles.evidenceNote}>{viewModel.evaluationProvenanceDisplay}</p>
            </div>
          </details>

          <details className={styles.disclosure}>
            <summary>
              <span className={styles.summaryTitle}>
                <strong>Confidence policy</strong>
              </span>
              <span className={styles.summaryValue}>4 bands</span>
              <ChevronDown size={16} aria-hidden="true" className={styles.disclosureChevron} />
            </summary>
            <div className={styles.disclosureBody}>
              <p className={styles.evidenceNote}>Configured bands for non-Normal predictions.</p>
              <PolicyTable viewModel={viewModel} />
              <p className={styles.evidenceNote}>{viewModel.normalPolicyException}</p>
            </div>
          </details>
        </div>
      </section>

    </div>
  )
}
