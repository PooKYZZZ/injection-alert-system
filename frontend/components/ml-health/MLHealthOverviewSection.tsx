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

function servingLabel(status: MLHealthData['status']): string {
  if (status === 'HEALTHY') return 'Healthy'
  if (status === 'DEGRADED') return 'Degraded'
  return 'Down'
}

function servingTone(status: MLHealthData['status']): Tone {
  if (status === 'HEALTHY') return 'healthy'
  if (status === 'DEGRADED') return 'warning'
  return 'critical'
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
  return 'Not reported'
}

function monitoringDetail(status: MLHealthData['drift_status']): string {
  if (status === 'NORMAL') return 'The latest snapshot reports no drift warning.'
  if (status === 'WARNING') return 'The latest snapshot contains a drift signal to review.'
  if (status === 'CRITICAL') return 'The latest snapshot contains a critical drift signal.'
  return 'Drift monitoring data is not reported in this snapshot.'
}

function calibrationLabel(ece: number | null | undefined): string {
  return ece == null ? 'Not reported' : 'Reported'
}

function calibrationDetail(ece: number | null | undefined): string {
  return ece == null
    ? 'Calibration data is not reported in this snapshot.'
    : 'An ECE value is present; no acceptance threshold is supplied by the endpoint.'
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
      <span className={styles.signalRowValue}>{value}</span>
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
          <p className={styles.eyebrow}>Serving answer</p>
          <h2 id="ml-health-status-heading">{viewModel.statusHeadline}</h2>
          <p className={styles.statusSubline}>{viewModel.statusSubline}</p>
        </div>
        <dl className={styles.statusHeroAside}>
          <div>
            <dt>Serving status</dt>
            <dd>{health.status}</dd>
          </div>
          <div>
            <dt>Snapshot</dt>
            <dd>Latest reported state</dd>
          </div>
        </dl>
      </section>

      <section className={styles.section} aria-labelledby="operational-signals-heading">
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Monitoring</p>
            <h2 id="operational-signals-heading">Operational signals</h2>
          </div>
          <p className={styles.sectionDescription}>A signal is marked not reported when the current endpoint supplied no result.</p>
        </div>
        <div className={styles.signalList}>
          <SignalRow
            label="Inference endpoint"
            value={servingLabel(health.status)}
            detail={health.status === 'HEALTHY' ? 'The latest snapshot reports the model as ready.' : viewModel.statusSubline}
            tone={servingTone(health.status)}
          />
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
            <p className={styles.eyebrow}>Runtime</p>
            <h2 id="serving-snapshot-heading">Serving snapshot</h2>
          </div>
          <p className={styles.sectionDescription}>Values reported by the ML health endpoint; no synthetic time series is shown.</p>
        </div>
        <dl className={styles.metricList}>
          <div className={styles.metricRow}>
            <dt>Requests analyzed</dt>
            <dd>{viewModel.trafficProcessedDisplay}</dd>
            <p>Traffic processed in the reported snapshot</p>
          </div>
          <div className={styles.metricRow}>
            <dt>Inference latency</dt>
            <dd>{viewModel.latencyDisplay}</dd>
            <p>Measured only when traffic is reported</p>
          </div>
          <div className={styles.metricRow}>
            <dt>Latency trend</dt>
            <dd>{viewModel.latencyTrendDisplay}</dd>
            <p>Comparison supplied by the health endpoint</p>
          </div>
        </dl>
      </section>

      <section className={styles.section} aria-labelledby="evidence-policy-heading">
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Evidence</p>
            <h2 id="evidence-policy-heading">Evidence and policy</h2>
          </div>
          <p className={styles.sectionDescription}>Open a section when the serving answer needs investigation.</p>
        </div>

        <div className={styles.disclosureGrid}>
          <details className={styles.disclosure}>
            <summary>
              <span className={styles.summaryTitle}>
                <span className={styles.summaryKicker}>Reported evaluation</span>
                <strong>Model quality evidence</strong>
              </span>
              <span className={styles.summaryValue}>{viewModel.classMetrics.length > 0 ? `${viewModel.classMetrics.length} classes` : 'Not reported'}</span>
              <ChevronDown size={16} aria-hidden="true" className={styles.disclosureChevron} />
            </summary>
            <div className={styles.disclosureBody}>
              <p className={styles.evidenceNote}>{viewModel.evaluationEvidenceSummary}</p>
              {viewModel.classMetrics.length > 0 ? (
                <p className={styles.evidenceNote}>{viewModel.classMetrics.length} per-class metric{viewModel.classMetrics.length === 1 ? '' : 's'} reported. Open Diagnostics → Drift for the detailed table.</p>
              ) : <p className={styles.emptyEvidence}>Per-class metrics are not reported in this snapshot.</p>}
              <p className={styles.evidenceNote}>Detailed prediction distribution and calibration evidence are available in Diagnostics. {viewModel.evaluationProvenanceDisplay}</p>
            </div>
          </details>

          <details className={styles.disclosure}>
            <summary>
              <span className={styles.summaryTitle}>
                <span className={styles.summaryKicker}>Automatic response</span>
                <strong>Confidence policy</strong>
              </span>
              <span className={styles.summaryValue}>4 bands</span>
              <ChevronDown size={16} aria-hidden="true" className={styles.disclosureChevron} />
            </summary>
            <div className={styles.disclosureBody}>
              <p className={styles.evidenceNote}>Threshold-based policy bands from configured confidence thresholds. These rules apply to non-Normal predictions only.</p>
              <h3 className={styles.subsectionTitle}>Non-Normal policy bands</h3>
              <PolicyTable viewModel={viewModel} />
              <p className={styles.evidenceNote}>{viewModel.normalPolicyException}</p>
            </div>
          </details>
        </div>
      </section>

      <footer className={styles.provenance}>
        <span>Source: ML health endpoint</span>
        <span className={styles.provenanceDivider}>·</span>
        <code>{health.model_version}</code>
      </footer>
    </div>
  )
}
