'use client'

import type { RetrainingRunDetail } from '@/features/ml-model/types'
import styles from './MLModelWorkspace.module.css'

interface Props {
  run: RetrainingRunDetail
}

interface MetricRow {
  key: string
  name: string
  definition: string
  source: string
}

const METRICS: MetricRow[] = [
  {
    key: 'normal_false_positive_rate',
    name: 'True Normal false-positive rate',
    definition: 'Actual Normal rows predicted as a non-Normal class divided by all verified Normal rows.',
    source: 'Ground truth: verified_label; frozen test split.',
  },
  {
    key: 'normal_recall',
    name: 'Normal recall',
    definition: 'Actual Normal rows predicted as Normal divided by all verified Normal rows.',
    source: 'Ground truth: verified_label; frozen test split.',
  },
  {
    key: 'attack_recall',
    name: 'Attack recall',
    definition: 'Actual attack rows predicted as a non-Normal class divided by all rows with a non-Normal verified label.',
    source: 'Ground truth: verified_label; frozen test split.',
  },
  {
    key: 'attack_escape_rate',
    name: 'Attack escape rate',
    definition: 'Actual attack rows predicted as Normal divided by all rows with a non-Normal verified label.',
    source: 'Ground truth: verified_label; frozen test split.',
  },
  {
    key: 'macro_f1',
    name: 'Macro F1',
    definition: 'Mean of the four canonical per-class F1 values.',
    source: 'Ground truth: verified_label; frozen test split.',
  },
  ...(['Code Injection', 'Normal', 'Other Attacks', 'SQL Injection'] as const).map((label) => ({
    key: `per_class.${label}.f1`,
    name: `${label} F1`,
    definition: `F1 for the verified ${label} class.`,
    source: 'Ground truth: verified_label; class support is required.',
  })),
]

function formatMetric(value: number | null): string {
  return value === null ? '—' : `${(value * 100).toFixed(2)}%`
}

function formatDelta(value: number | null): string {
  if (value === null) return '—'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${(value * 100).toFixed(2)} pp`
}

function formatHeartbeat(age: number | null): string {
  if (age === null) return 'Not recorded'
  if (age < 60) return `${age}s ago`
  return `${Math.floor(age / 60)}m ago`
}

export function MLModelComparisonPanel({ run }: Props) {
  const evidence = run.evidence_summary
  const metricByName = new Map(evidence.metrics.map((metric) => [metric.name, metric]))
  const gateStatus = evidence.comparison_status
  const status = gateStatus === 'NOT_RUN' ? run.evidence_status : gateStatus

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

      <div className={styles.evidenceNotice} role="status">
        <strong>Run stage:</strong> {run.stage.replaceAll('_', ' ')} · <strong>Evidence:</strong> {run.evidence_status} ·{' '}
        <strong>Heartbeat:</strong> {formatHeartbeat(run.heartbeat_age_seconds)}
        <br />
        <strong>Dataset:</strong> {run.dataset_version ?? run.source_dataset_version} ·{' '}
        <strong>Preprocessing:</strong> {evidence.preprocessing_version ?? 'Not recorded'} ·{' '}
        <strong>Evaluation:</strong> {evidence.evaluation_split ?? 'Not recorded'}
        <br />
        <strong>Dataset digest:</strong> {run.dataset_digest ?? run.source_dataset_digest} ·{' '}
        <strong>Evaluation digest:</strong> {run.evaluation_digest ?? 'Not recorded'}
      </div>

      <div className={styles.tableScroll}>
        <table className={styles.comparisonTable}>
          <caption className={styles.visuallyHidden}>
            Ground-truth comparison metrics from the durable evaluation artifact.
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
            {METRICS.map((metric) => {
              const evidenceMetric = metricByName.get(metric.key)
              const metricStatus = evidenceMetric?.evidence_status ?? 'NOT_RUN'
              return (
                <tr key={metric.key}>
                  <th scope="row">
                    <span className={styles.metricName}>{metric.name}</span>
                    <span className={styles.metricDefinition}>{metric.definition}</span>
                  </th>
                  <td>{formatMetric(evidenceMetric?.active_value ?? null)}</td>
                  <td>{formatMetric(evidenceMetric?.candidate_value ?? null)}</td>
                  <td>{formatDelta(evidenceMetric?.delta ?? null)}</td>
                  <td>{evidenceMetric?.support_count ?? '—'}</td>
                  <td><span className={styles.statusBadge}>{metricStatus}</span></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <details className={styles.metricHelp}>
        <summary>Metric definitions and source</summary>
        <div className={styles.metricHelpBody}>
          {METRICS.map((metric) => (
            <div key={metric.key}>
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
        {run.evidence_status === 'CONTROLLED_SMOKE'
          ? 'Smoke mode exercises queue and artifact ordering only; it does not claim native training quality.'
          : status === 'NOT_ENOUGH_EVIDENCE' || status === 'NOT_RUN'
            ? 'This run does not have enough eligible native evaluation evidence for a comparison or approval gate.'
            : 'Native evidence is bound to this run. The active model remains unchanged; approval and deployment are separate explicit actions.'}
      </div>
    </section>
  )
}
