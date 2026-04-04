import { AlertCircle, AlertTriangle, CheckCircle2, Database, HelpCircle } from 'lucide-react'
import type { MLHealthData } from '@/features/ml-health/types'
import type { MLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
}

function attentionIcon(tone: MLHealthViewModel['tone']) {
  if (tone === 'healthy') return <CheckCircle2 size={18} color="var(--mlh-green)" />
  if (tone === 'warning') return <AlertTriangle size={18} color="var(--mlh-amber)" />
  if (tone === 'critical') return <AlertCircle size={18} color="var(--mlh-rose)" />
  return <HelpCircle size={18} color="var(--mlh-text-muted)" />
}

export function MLHealthOverviewSection({ health, viewModel }: Props) {
  const attentionToneClass =
    viewModel.tone === 'healthy'
      ? styles.attentionHealthy
      : viewModel.tone === 'warning'
        ? styles.attentionWarning
        : viewModel.tone === 'critical'
          ? styles.attentionCritical
          : styles.attentionUnknown

  return (
    <div>
      <section className={`${styles.attention} ${attentionToneClass}`}>
        <div className={styles.attentionIcon}>{attentionIcon(viewModel.tone)}</div>
        <div className={styles.attentionBody}>
          <p className={styles.attentionHeadline}>{viewModel.statusHeadline}</p>
          <p className={styles.attentionSubline}>{viewModel.statusSubline}</p>
          <div className={styles.attentionSignals}>
            <span className={styles.attentionSignal}>
              <span className={`${styles.attentionSignalDot} ${health.status === 'HEALTHY' ? styles.attentionSignalDotActive : styles.attentionSignalDotInactive}`} />
              Serving {health.status}
            </span>
            <span className={styles.attentionSignal}>
              <span className={`${styles.attentionSignalDot} ${health.drift_status === 'CRITICAL' ? styles.attentionSignalDotInactive : styles.attentionSignalDotActive}`} />
              Drift {viewModel.driftStatusDisplay}
            </span>
            <span className={styles.attentionSignal}>
              <span className={`${styles.attentionSignalDot} ${health.ece != null && health.ece <= 0.05 ? styles.attentionSignalDotActive : styles.attentionSignalDotInactive}`} />
              ECE {viewModel.eceDisplay}
            </span>
          </div>
        </div>
        <div className={styles.attentionRight}>
          <span className={`${styles.attentionPill} ${health.status === 'HEALTHY' ? styles.attentionPillLive : styles.attentionPillDegraded}`}>
            {health.status === 'HEALTHY' ? 'Serving healthy' : 'Review required'}
          </span>
          <span className={styles.attentionTimestamp}>Reported in latest snapshot</span>
        </div>
      </section>

      <section className={styles.kpiPrimaryBand}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Requests analyzed</div>
          <div className={styles.kpiValue}>{viewModel.trafficProcessedDisplay}</div>
          <div className={styles.kpiSub}>reported by ML health endpoint</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Inference latency</div>
          <div className={styles.kpiValue}>{viewModel.latencyDisplay}</div>
          <div className={styles.kpiSub}>trend: {viewModel.latencyTrendDisplay}</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Feature drift</div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{viewModel.driftScoreDisplay}</div>
          <div className={styles.kpiSub}>status: {viewModel.driftStatusDisplay} · threshold 0.050</div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Calibration (ECE)</div>
          <div className={`${styles.kpiValue} ${styles.kpiValueSmall}`}>{viewModel.eceDisplay}</div>
          <div className={styles.kpiSub}>{viewModel.calibrationSummary}</div>
        </div>
      </section>

      <section className={styles.impactZone}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Policy Bands (configured thresholds)</span>
          </div>
          <div className={styles.tableScroll}>
            <table className={styles.compTable}>
              <thead>
                <tr>
                  <th>Band</th>
                  <th>Confidence range</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.policyBands.map((band) => (
                  <tr key={band.label}>
                    <td>{band.label}</td>
                    <td>{band.rangeLabel}</td>
                    <td>
                      <span
                        className={
                          band.action === 'allow'
                            ? styles.policyAllow
                            : band.action === 'throttle'
                              ? styles.policyThrottle
                              : styles.policyBlock
                        }
                      >
                        {band.action}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={styles.panelBody}>
            <p className={styles.policyFootnote}>Threshold-based policy bands from configured confidence thresholds.</p>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Per-class F1 (reported)</span>
          </div>
          <div className={styles.tableScroll}>
            {viewModel.classMetrics.length > 0 ? (
              <table className={styles.compTable}>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>F1 score</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {viewModel.classMetrics.map((row) => (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td>{row.f1Display}</td>
                      <td>
                        <span className={row.isElevated ? styles.policyThrottle : styles.policyAllow}>
                          {row.isElevated ? 'review' : 'stable'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className={styles.panelBody}>
                <span className={styles.muted}>Per-class metrics are not reported in this snapshot.</span>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Prediction Distribution Snapshot</span>
        </div>
        <div className={styles.tableScroll}>
          {viewModel.distributionRows.length > 0 ? (
            <table className={styles.compTable}>
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Baseline</th>
                  <th>Current</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.distributionRows.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    <td>{row.baselineDisplay}</td>
                    <td>{row.currentDisplay}</td>
                    <td>{row.deltaDisplay}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className={styles.panelBody}>
              <span className={styles.muted}>Prediction distribution is not reported in this snapshot.</span>
            </div>
          )}
        </div>
        <div className={styles.panelBody}>
          <p className={styles.policyFootnote}>
            Counts reflect the latest API payload. No synthetic timeline is generated in this view.
          </p>
        </div>
      </section>

      <section className={styles.provenance}>
        <Database size={11} />
        <span>
          Model: <span className={styles.provenanceMono}>{health.model_version}</span>
        </span>
        <span className={styles.dotDivider}>·</span>
        <span>Window: {viewModel.windowLabel}</span>
      </section>
    </div>
  )
}
