'use client'

import { useState } from 'react'
import type { MLHealthData } from '@/features/ml-health/types'
import type { MLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type DiagnosticsTab = 'performance' | 'drift' | 'calibration' | 'policy'

type Props = {
  health: MLHealthData
  viewModel: MLHealthViewModel
}

function PerformanceTab({ health, viewModel }: Props) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Performance Snapshot</span>
        </div>
        <div className={styles.tableScroll}>
          <table className={styles.compTable}>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Latency</td>
                <td>{viewModel.latencyDisplay}</td>
                <td>health.latency_ms</td>
              </tr>
              <tr>
                <td>Latency trend</td>
                <td>{viewModel.latencyTrendDisplay}</td>
                <td>health.latency_trend</td>
              </tr>
              <tr>
                <td>Traffic processed</td>
                <td>{viewModel.trafficProcessedDisplay}</td>
                <td>health.traffic_processed</td>
              </tr>
              <tr>
                <td>Serving status</td>
                <td>{health.status}</td>
                <td>health.status</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function DriftTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Drift Snapshot</span>
        </div>
        <div className={styles.tableScroll}>
          <table className={styles.compTable}>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Drift score</td>
                <td>{viewModel.driftScoreDisplay}</td>
                <td>health.drift_score</td>
              </tr>
              <tr>
                <td>Drift status</td>
                <td>{viewModel.driftStatusDisplay}</td>
                <td>health.drift_status</td>
              </tr>
            </tbody>
          </table>
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
    </div>
  )
}

function CalibrationTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Calibration Snapshot</span>
        </div>
        <div className={styles.tableScroll}>
          <table className={styles.compTable}>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Expected calibration error</td>
                <td>{viewModel.eceDisplay}</td>
                <td>health.ece</td>
              </tr>
              <tr>
                <td>Assessment</td>
                <td>{viewModel.calibrationSummary}</td>
                <td>derived</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Calibration bins (reported)</span>
        </div>
        <div className={styles.tableScroll}>
          {viewModel.calibrationBins.length > 0 ? (
            <table className={styles.compTable}>
              <thead>
                <tr>
                  <th>Bin</th>
                  <th>Center</th>
                  <th>Confidence</th>
                  <th>Accuracy</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.calibrationBins.map((bin) => (
                  <tr key={bin.bin_idx}>
                    <td>{bin.bin_idx}</td>
                    <td>{bin.bin_center.toFixed(3)}</td>
                    <td>{bin.confidence.toFixed(3)}</td>
                    <td>{bin.accuracy.toFixed(3)}</td>
                    <td>{bin.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className={styles.panelBody}>
              <span className={styles.muted}>Calibration bins are not reported in this snapshot.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function PolicyTab({ viewModel }: Props) {
  return (
    <div className={styles.diagnosticsStack}>
      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.panelTitle}>Policy decision bands</span>
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
          <p className={styles.policyFootnote}>Low: {viewModel.thresholdLabels.low} · Medium: {viewModel.thresholdLabels.medium} · High: {viewModel.thresholdLabels.high}</p>
        </div>
      </div>
    </div>
  )
}

export function MLHealthDiagnosticsSection({ health, viewModel }: Props) {
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
          <span className={styles.diagSummaryLabel}>Serving status</span>
          <span className={styles.diagSummaryValue}>{health.status}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>Drift score</span>
          <span className={styles.diagSummaryValue}>{viewModel.driftScoreDisplay}</span>
        </div>
        <div className={styles.diagDivider} />
        <div className={styles.diagSummaryItem}>
          <span className={styles.diagSummaryLabel}>ECE</span>
          <span className={styles.diagSummaryValue}>{viewModel.eceDisplay}</span>
        </div>
      </div>

      <div className={styles.tabs}>
        {tabs.map((item) => (
          <button
            key={item.key}
            className={`${styles.tab} ${tab === item.key ? styles.tabActive : ''}`}
            onClick={() => setTab(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'performance' ? <PerformanceTab health={health} viewModel={viewModel} /> : null}
      {tab === 'drift' ? <DriftTab health={health} viewModel={viewModel} /> : null}
      {tab === 'calibration' ? <CalibrationTab health={health} viewModel={viewModel} /> : null}
      {tab === 'policy' ? <PolicyTab health={health} viewModel={viewModel} /> : null}
    </div>
  )
}
