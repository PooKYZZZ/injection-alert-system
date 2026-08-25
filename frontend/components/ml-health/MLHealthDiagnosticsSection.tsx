'use client'

import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

import type { MLHealthData } from '@/features/ml-health/types'

import type { MLHealthViewModel, PolicyBandAction } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type DiagnosticsTab = 'performance' | 'monitoring' | 'evaluation' | 'policy'

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
}

type ViewProps = Pick<Props, 'viewModel'>

function policyClass(action: PolicyBandAction): string {
  if (action === 'allow') return styles.policyAllow
  if (action === 'throttle') return styles.policyThrottle
  return styles.policyBlock
}

function DiagnosticsTable({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.tableScroll}>
      <table className={styles.compTable} aria-label={label}>
        {children}
      </table>
    </div>
  )
}

function EmptyEvidence({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <div className={styles.emptyEvidenceState}>
      <strong>{heading}</strong>
      <p>{children}</p>
    </div>
  )
}

function PerformanceTab({ viewModel }: ViewProps) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="performance-heading">
        <div className={styles.panelHeader}>
          <div>
            <h2 id="performance-heading">Serving metrics</h2>
            <p className={styles.panelDescription}>Traffic and latency reported by this health snapshot.</p>
          </div>
        </div>
        <DiagnosticsTable label="Serving metrics">
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Value</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Requests in snapshot</td><td className={styles.mono}>{viewModel.trafficProcessedDisplay}</td></tr>
            <tr><td>Inference latency</td><td className={styles.mono}>{viewModel.latencyDisplay}</td></tr>
            <tr><td>Latency comparison</td><td className={styles.mono}>{viewModel.latencyTrendDisplay}</td></tr>
          </tbody>
        </DiagnosticsTable>
        <p className={styles.panelNote}>
          {viewModel.hasTraffic
            ? 'Latency is measured only when the snapshot includes traffic.'
            : 'No serving traffic in this snapshot.'}
        </p>
      </section>
    </div>
  )
}

function MonitoringTab({ viewModel }: ViewProps) {
  const hasMonitoringEvidence =
    viewModel.driftScoreDisplay !== 'Unavailable' || viewModel.driftStatusDisplay !== 'Unavailable'

  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="monitoring-heading">
        <div className={styles.panelHeader}>
          <div>
            <h2 id="monitoring-heading">Drift monitoring</h2>
            <p className={styles.panelDescription}>Only results included in the current snapshot are shown.</p>
          </div>
        </div>
        {hasMonitoringEvidence ? (
          <DiagnosticsTable label="Drift monitoring">
            <thead>
              <tr>
                <th scope="col">Signal</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Drift score</td><td className={styles.mono}>{viewModel.driftScoreDisplay}</td></tr>
              <tr><td>Drift status</td><td>{viewModel.driftStatusDisplay}</td></tr>
            </tbody>
          </DiagnosticsTable>
        ) : (
          <EmptyEvidence heading="Drift result unavailable">
            This snapshot does not include a drift result. No threshold or trend is inferred here.
          </EmptyEvidence>
        )}
      </section>
    </div>
  )
}

function EvaluationTab({ viewModel }: ViewProps) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="evaluation-heading">
        <div className={styles.panelHeader}>
          <div>
            <h2 id="evaluation-heading">Model evaluation</h2>
            <p className={styles.panelDescription}>{viewModel.evaluationEvidenceSummary}</p>
          </div>
        </div>

        {viewModel.classMetrics.length > 0 ? (
          <DiagnosticsTable label="Per-class F1 reported evaluation">
            <thead>
              <tr><th scope="col">Class</th><th scope="col">F1 score</th></tr>
            </thead>
            <tbody>
              {viewModel.classMetrics.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td className={styles.mono}>{row.f1Display}</td>
                </tr>
              ))}
            </tbody>
          </DiagnosticsTable>
        ) : (
          <EmptyEvidence heading="Per-class evaluation unavailable">
            The current snapshot does not include class-level evaluation results.
          </EmptyEvidence>
        )}

        <div className={styles.evidenceBlock}>
          <h3>Prediction distribution</h3>
          {viewModel.distributionRows.length > 0 ? (
            <DiagnosticsTable label="Prediction distribution snapshot">
              <thead>
                <tr>
                  <th scope="col">Class</th>
                  {viewModel.distributionHasBaseline ? <th scope="col">Baseline</th> : null}
                  <th scope="col">Current</th>
                  {viewModel.distributionHasBaseline ? <th scope="col">Change</th> : null}
                </tr>
              </thead>
              <tbody>
                {viewModel.distributionRows.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    {viewModel.distributionHasBaseline ? <td className={styles.mono}>{row.baselineDisplay ?? 'Unavailable'}</td> : null}
                    <td className={styles.mono}>{row.currentDisplay}</td>
                    {viewModel.distributionHasBaseline ? <td className={styles.mono}>{row.deltaDisplay ?? 'Unavailable'}</td> : null}
                  </tr>
                ))}
              </tbody>
            </DiagnosticsTable>
          ) : (
            <EmptyEvidence heading="Prediction distribution unavailable">
              {viewModel.distributionSummary}
            </EmptyEvidence>
          )}
          {viewModel.distributionRows.length > 0 ? <p className={styles.panelNote}>{viewModel.distributionSummary}</p> : null}
        </div>

        <div className={styles.evidenceBlock}>
          <h3>Calibration</h3>
          <div className={styles.inlineMetric}>
            <span>Expected calibration error</span>
            <strong className={styles.mono}>{viewModel.eceDisplay}</strong>
          </div>
          {viewModel.calibrationBins.length > 0 ? (
            <DiagnosticsTable label="Calibration bins reported evaluation">
              <thead>
                <tr>
                  <th scope="col">Bin</th>
                  <th scope="col">Center</th>
                  <th scope="col">Confidence</th>
                  <th scope="col">Accuracy</th>
                  <th scope="col">Count</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.calibrationBins.map((bin) => (
                  <tr key={bin.bin_idx}>
                    <td>{bin.bin_idx}</td>
                    <td className={styles.mono}>{bin.bin_center.toFixed(3)}</td>
                    <td className={styles.mono}>{bin.confidence.toFixed(3)}</td>
                    <td className={styles.mono}>{bin.accuracy.toFixed(3)}</td>
                    <td className={styles.mono}>{bin.count}</td>
                  </tr>
                ))}
              </tbody>
            </DiagnosticsTable>
          ) : (
            <p className={styles.panelNote}>{viewModel.calibrationSummary}</p>
          )}
        </div>

        <p className={styles.panelNote}>{viewModel.evaluationProvenanceDisplay}</p>
      </section>
    </div>
  )
}

function PolicyTab({ viewModel }: ViewProps) {
  return (
    <div className={styles.diagnosticStack}>
      <section className={styles.diagnosticPanel} aria-labelledby="policy-heading">
        <div className={styles.panelHeader}>
          <div>
            <h2 id="policy-heading">Confidence policy</h2>
            <p className={styles.panelDescription}>Automatic response bands for non-Normal predictions.</p>
          </div>
        </div>
        <DiagnosticsTable label="Confidence policy">
          <thead>
            <tr><th scope="col">Confidence band</th><th scope="col">Range</th><th scope="col">Action</th></tr>
          </thead>
          <tbody>
            {viewModel.policyBands.map((band) => (
              <tr key={band.label}>
                <td>{band.label}</td>
                <td className={styles.mono}>{band.rangeLabel}</td>
                <td><span className={policyClass(band.action)}>{band.action}</span></td>
              </tr>
            ))}
          </tbody>
        </DiagnosticsTable>
        <p className={styles.panelNote}>{viewModel.normalPolicyException}</p>
      </section>
    </div>
  )
}

export function MLHealthDiagnosticsSection({ viewModel }: Props) {
  const [tab, setTab] = useState<DiagnosticsTab>('performance')
  const tabRefs = useRef<Record<DiagnosticsTab, HTMLButtonElement | null>>({
    performance: null,
    monitoring: null,
    evaluation: null,
    policy: null,
  })

  const tabs: Array<{ key: DiagnosticsTab; label: string }> = [
    { key: 'performance', label: 'Performance' },
    { key: 'monitoring', label: 'Monitoring' },
    { key: 'evaluation', label: 'Evaluation' },
    { key: 'policy', label: 'Policy' },
  ]

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
          <h2 id="diagnostics-heading">Diagnostics</h2>
          <p className={styles.sectionDescription}>Review evidence supplied by the current health snapshot.</p>
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
            {item.label}
          </button>
        ))}
      </div>

      <div id={`ml-diagnostic-panel-${tab}`} role="tabpanel" aria-labelledby={`ml-diagnostic-tab-${tab}`} tabIndex={0}>
        {tab === 'performance' ? <PerformanceTab viewModel={viewModel} /> : null}
        {tab === 'monitoring' ? <MonitoringTab viewModel={viewModel} /> : null}
        {tab === 'evaluation' ? <EvaluationTab viewModel={viewModel} /> : null}
        {tab === 'policy' ? <PolicyTab viewModel={viewModel} /> : null}
      </div>

    </div>
  )
}
