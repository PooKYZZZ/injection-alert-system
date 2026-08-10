'use client'

import type { RetrainingRunDetail } from '@/features/ml-model/types'
import styles from './MLModelWorkspace.module.css'

interface Props {
  run: RetrainingRunDetail
}

interface MetricRow {
  name: string
  definition: string
  source: string
}

const METRICS: MetricRow[] = [
  {
    name: 'True Normal false-positive rate',
    definition: 'Actual Normal rows predicted as a non-Normal class divided by all verified Normal rows.',
    source: 'Ground truth: verified_label; evaluation split.',
  },
  {
    name: 'Attack recall',
    definition: 'Actual attack rows predicted as a non-Normal class divided by all rows with a non-Normal verified label.',
    source: 'Ground truth: verified_label; evaluation split.',
  },
  {
    name: 'Attack escape rate',
    definition: 'Actual attack rows predicted as Normal divided by all rows with a non-Normal verified label.',
    source: 'Ground truth: verified_label; evaluation split.',
  },
  {
    name: 'Macro F1',
    definition: 'Mean of the four canonical per-class F1 values.',
    source: 'Ground truth: verified_label; evaluation split.',
  },
  {
    name: 'Per-class F1',
    definition: 'F1 for Code Injection, Normal, Other Attacks, and SQL Injection.',
    source: 'Ground truth: verified_label; class support is required.',
  },
]

function unavailableStatus(run: RetrainingRunDetail): string {
  return run.state === 'NOT_ENOUGH_EVIDENCE' || run.evidence_status === 'NOT_ENOUGH_EVIDENCE'
    ? 'NOT_ENOUGH_EVIDENCE'
    : 'NOT_RUN'
}

export function MLModelComparisonPanel({ run }: Props) {
  const status = unavailableStatus(run)

  return (
    <section className={styles.comparisonSection} aria-labelledby="ml-model-comparison-heading">
      <div className={styles.sectionHeaderCompact}>
        <div>
          <p className={styles.eyebrow}>Evidence gate</p>
          <h2 id="ml-model-comparison-heading" className={styles.sectionTitle}>
            Active versus candidate evidence
          </h2>
        </div>
        <span className={styles.statusBadge}>{status}</span>
      </div>

      <div className={styles.modelPair}>
        <div>
          <span className={styles.metricLabel}>Active model</span>
          <strong className={styles.modelVersion}>{run.active_model_version}</strong>
          <span className={styles.monoSubline}>{run.active_model_digest}</span>
        </div>
        <div>
          <span className={styles.metricLabel}>Candidate model</span>
          <strong className={styles.modelVersion}>{run.candidate_model_version ?? 'Not created'}</strong>
          <span className={styles.monoSubline}>{run.candidate_model_digest ?? '—'}</span>
        </div>
      </div>

      <div className={styles.tableScroll}>
        <table className={styles.comparisonTable}>
          <caption className={styles.visuallyHidden}>
            Ground-truth comparison metrics. No values are shown until a native evaluation artifact is available.
          </caption>
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Active</th>
              <th scope="col">Candidate</th>
              <th scope="col">Delta</th>
              <th scope="col">Support</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric) => (
              <tr key={metric.name}>
                <th scope="row">
                  <span className={styles.metricName}>{metric.name}</span>
                  <span className={styles.metricDefinition}>{metric.definition}</span>
                </th>
                <td>—</td>
                <td>—</td>
                <td>—</td>
                <td>—</td>
                <td><span className={styles.statusBadge}>{status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className={styles.metricHelp}>
        <summary>Metric definitions and source</summary>
        <div className={styles.metricHelpBody}>
          {METRICS.map((metric) => (
            <div key={metric.name}>
              <strong>{metric.name}</strong>
              <span>{metric.definition}</span>
              <small>{metric.source}</small>
            </div>
          ))}
          <p>
            Ground-truth evidence uses verified_label. The dashboard operational proxy is not a ground-truth false-positive rate. A PASS requires sufficient verified-label evidence and a native evaluation artifact.
          </p>
        </div>
      </details>

      <div className={styles.evidenceNotice}>
        {status === 'NOT_ENOUGH_EVIDENCE'
          ? 'This run does not have enough eligible evaluation evidence for a comparison or approval gate.'
          : 'Comparison values and gates are not available from the current run contract. The active model remains unchanged.'}
      </div>
    </section>
  )
}
