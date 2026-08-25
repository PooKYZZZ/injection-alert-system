'use client'

import { useRef, useState, type KeyboardEvent } from 'react'

import type { MLHealthData } from '@/features/ml-health/types'

import type { MLHealthViewModel, PolicyBandAction } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type DiagnosticsTab = 'performance' | 'drift' | 'calibration' | 'policy'

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
}

function policyClass(action: PolicyBandAction): string {
  if (action === 'allow') return styles.policyAllow
  if (action === 'throttle') return styles.policyThrottle
  return styles.policyBlock
}

function DiagnosticsTable({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className={styles.tableScroll}>
      <table className={styles.compTable} aria-label={label}>
        {children}
      </table>
    </div>
  )
}

function PerformanceTab({ health, viewModel }: Props) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="performance-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Runtime</p>
            <h2 id="performance-heading">Serving performance</h2>
          </div>
          <span className={styles.sourceTag}>ML health endpoint</span>
        </div>
        <DiagnosticsTable label="Performance snapshot">
          <thead><tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Source field</th></tr></thead>
          <tbody>
            <tr><td>Latency</td><td className={styles.mono}>{viewModel.latencyDisplay}</td><td className={styles.mono}>latency_ms</td></tr>
            <tr><td>Latency trend</td><td className={styles.mono}>{viewModel.latencyTrendDisplay}</td><td className={styles.mono}>latency_trend</td></tr>
            <tr><td>Traffic processed</td><td className={styles.mono}>{viewModel.trafficProcessedDisplay}</td><td className={styles.mono}>traffic_processed</td></tr>
            <tr><td>Serving status</td><td><span className={styles.stateTag}>{health.status}</span></td><td className={styles.mono}>status</td></tr>
          </tbody>
        </DiagnosticsTable>
        <p className={styles.panelNote}>A zero-traffic snapshot reports latency as not measured rather than treating zero as a latency result.</p>
      </section>
    </div>
  )
}

function DriftTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="drift-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Monitoring</p>
            <h2 id="drift-heading">Drift evidence</h2>
          </div>
          <span className={styles.sourceTag}>Reported fields only</span>
        </div>
        <DiagnosticsTable label="Drift snapshot">
          <thead><tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Source field</th></tr></thead>
          <tbody>
            <tr><td>Drift score</td><td className={styles.mono}>{viewModel.driftScoreDisplay}</td><td className={styles.mono}>drift_score</td></tr>
            <tr><td>Drift status</td><td>{viewModel.driftStatusDisplay}</td><td className={styles.mono}>drift_status</td></tr>
          </tbody>
        </DiagnosticsTable>
        <p className={styles.panelNote}>{viewModel.driftStatusDisplay === 'Not reported' ? 'Drift monitoring data is not reported in this snapshot.' : 'This view does not infer a threshold that the endpoint did not provide.'}</p>
      </section>

      <section className={styles.diagnosticPanel} aria-labelledby="f1-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Evaluation</p>
            <h2 id="f1-heading">Per-class F1</h2>
          </div>
          <span className={styles.sourceTag}>Active response fields</span>
        </div>
        {viewModel.classMetrics.length > 0 ? (
          <DiagnosticsTable label="Per-class F1 reported evaluation">
            <thead><tr><th scope="col">Class</th><th scope="col">F1 score</th><th scope="col">Interpretation</th></tr></thead>
            <tbody>
              {viewModel.classMetrics.map((row) => (
                <tr key={row.label}><td>{row.label}</td><td className={styles.mono}>{row.f1Display}</td><td><span className={styles.reportedTag}>Reported</span></td></tr>
              ))}
            </tbody>
          </DiagnosticsTable>
        ) : <p className={styles.emptyEvidence}>Per-class metrics are not reported in this snapshot.</p>}
      </section>

      <section className={styles.diagnosticPanel} aria-labelledby="distribution-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Traffic mix</p>
            <h2 id="distribution-heading">Prediction distribution</h2>
          </div>
          <span className={styles.sourceTag}>Active response fields</span>
        </div>
        {viewModel.distributionRows.length > 0 ? (
          <DiagnosticsTable label="Prediction distribution snapshot">
            <thead><tr><th scope="col">Class</th><th scope="col">Baseline</th><th scope="col">Current</th><th scope="col">Delta</th></tr></thead>
            <tbody>
              {viewModel.distributionRows.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td><td className={styles.mono}>{row.baselineDisplay}</td><td className={styles.mono}>{row.currentDisplay}</td><td className={styles.mono}>{row.deltaDisplay}</td>
                </tr>
              ))}
            </tbody>
          </DiagnosticsTable>
        ) : <p className={styles.emptyEvidence}>{viewModel.distributionSummary}</p>}
        <p className={styles.panelNote}>No synthetic timeline is generated from this snapshot.</p>
      </section>
    </div>
  )
}

function CalibrationTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="calibration-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Evaluation</p>
            <h2 id="calibration-heading">Calibration evidence</h2>
          </div>
          <span className={styles.sourceTag}>Reported fields only</span>
        </div>
        <DiagnosticsTable label="Calibration snapshot">
          <thead><tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Source</th></tr></thead>
          <tbody>
            <tr><td>Expected calibration error</td><td className={styles.mono}>{viewModel.eceDisplay}</td><td className={styles.mono}>ece</td></tr>
            <tr><td>Evidence state</td><td>{viewModel.calibrationSummary}</td><td>Reported endpoint field</td></tr>
          </tbody>
        </DiagnosticsTable>
        <p className={styles.panelNote}>{viewModel.evaluationProvenanceDisplay}</p>
      </section>

      <section className={styles.diagnosticPanel} aria-labelledby="bins-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Distribution</p>
            <h2 id="bins-heading">Calibration bins</h2>
          </div>
          <span className={styles.sourceTag}>Reported evaluation</span>
        </div>
        {viewModel.calibrationBins.length > 0 ? (
          <DiagnosticsTable label="Calibration bins reported evaluation">
            <thead><tr><th scope="col">Bin</th><th scope="col">Center</th><th scope="col">Confidence</th><th scope="col">Accuracy</th><th scope="col">Count</th></tr></thead>
            <tbody>
              {viewModel.calibrationBins.map((bin) => (
                <tr key={bin.bin_idx}><td>{bin.bin_idx}</td><td className={styles.mono}>{bin.bin_center.toFixed(3)}</td><td className={styles.mono}>{bin.confidence.toFixed(3)}</td><td className={styles.mono}>{bin.accuracy.toFixed(3)}</td><td className={styles.mono}>{bin.count}</td></tr>
              ))}
            </tbody>
          </DiagnosticsTable>
        ) : <p className={styles.emptyEvidence}>Calibration bins are not reported in this snapshot.</p>}
      </section>
    </div>
  )
}

function PolicyTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="policy-heading">
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Enforcement</p>
            <h2 id="policy-heading">Confidence policy bands</h2>
          </div>
          <span className={styles.sourceTag}>Configured thresholds</span>
        </div>
        <DiagnosticsTable label="Policy decision bands">
          <thead><tr><th scope="col">Confidence band</th><th scope="col">Range</th><th scope="col">Action</th></tr></thead>
          <tbody>
            {viewModel.policyBands.map((band) => (
              <tr key={band.label}><td>{band.label}</td><td className={styles.mono}>{band.rangeLabel}</td><td><span className={policyClass(band.action)}>{band.action}</span></td></tr>
            ))}
          </tbody>
        </DiagnosticsTable>
        <div className={styles.policyNotes}>
          <p>{'Threshold-based policy bands from configured confidence thresholds.'}</p>
          <p>Low: {viewModel.thresholdLabels.low} · Medium: {viewModel.thresholdLabels.medium} · High: {viewModel.thresholdLabels.high} · Critical: {viewModel.thresholdLabels.critical}</p>
          <p>{viewModel.normalPolicyException}</p>
        </div>
      </section>
    </div>
  )
}

export function MLHealthDiagnosticsSection({ health, viewModel }: Props) {
  const [tab, setTab] = useState<DiagnosticsTab>('performance')
  const tabRefs = useRef<Record<DiagnosticsTab, HTMLButtonElement | null>>({
    performance: null,
    drift: null,
    calibration: null,
    policy: null,
  })

  const tabs: Array<{ key: DiagnosticsTab; label: string; description: string }> = [
    { key: 'performance', label: 'Performance', description: 'Serving latency and traffic' },
    { key: 'drift', label: 'Drift', description: 'Drift and class performance' },
    { key: 'calibration', label: 'Calibration', description: 'Calibration error and bins' },
    { key: 'policy', label: 'Policy', description: 'Confidence-based automatic actions' },
  ]

  const activeTab = tabs.find((item) => item.key === tab) ?? tabs[0]

  function handleDiagnosticTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabs.length - 1
    if (nextIndex == null) return

    event.preventDefault()
    const nextTab = tabs[nextIndex]
    setTab(nextTab.key)
    tabRefs.current[nextTab.key]?.focus()
  }

  return (
    <div className={styles.diagnostics}>
      <section className={styles.diagnosticsHeader} aria-labelledby="diagnostics-heading">
        <div>
          <p className={styles.eyebrow}>Evidence workspace</p>
          <h2 id="diagnostics-heading">Diagnostics</h2>
          <p className={styles.sectionDescription}>Inspect only the evidence supplied by the current health snapshot.</p>
        </div>
        <div className={styles.diagnosticIdentity}>
          <span className={styles.metaLabel}>Model</span>
          <code>{viewModel.displayName}</code>
          <span className={styles.stateTag}>{health.status}</span>
        </div>
      </section>

      <div className={styles.diagnosticTabs} role="tablist" aria-label="Diagnostic categories">
        {tabs.map((item, index) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            id={`ml-diagnostic-tab-${item.key}`}
            aria-controls={`ml-diagnostic-panel-${item.key}`}
            aria-selected={tab === item.key}
            tabIndex={tab === item.key ? 0 : -1}
            aria-label={item.label}
            className={`${styles.diagnosticTab} ${tab === item.key ? styles.diagnosticTabActive : ''}`}
            onClick={() => setTab(item.key)}
            onKeyDown={(event) => handleDiagnosticTabKeyDown(event, index)}
            ref={(element) => { tabRefs.current[item.key] = element }}
          >
            <span>{item.label}</span>
            <small>{item.description}</small>
          </button>
        ))}
      </div>

      <p className={styles.tableHint}>Scroll horizontally to view all columns on narrow screens.</p>

      <div id={`ml-diagnostic-panel-${tab}`} role="tabpanel" aria-labelledby={`ml-diagnostic-tab-${tab}`} tabIndex={0}>
        {tab === 'performance' ? <PerformanceTab health={health} viewModel={viewModel} /> : null}
        {tab === 'drift' ? <DriftTab health={health} viewModel={viewModel} /> : null}
        {tab === 'calibration' ? <CalibrationTab health={health} viewModel={viewModel} /> : null}
        {tab === 'policy' ? <PolicyTab health={health} viewModel={viewModel} /> : null}
      </div>

      <p className={styles.srOnly}>{activeTab.description}</p>
    </div>
  )
}
