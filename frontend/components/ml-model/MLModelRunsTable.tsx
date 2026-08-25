'use client'

import type { RetrainingRun } from '@/features/ml-model/types'
import { formatStableDateTime } from '@/lib/date-time'
import styles from './MLModelWorkspace.module.css'

interface Props {
  runs: RetrainingRun[]
  selectedRunId: string | null
  onSelect: (runId: string) => void
}

function formatState(state: RetrainingRun['state']): string {
  const labels: Partial<Record<RetrainingRun['state'], string>> = {
    NOT_ENOUGH_EVIDENCE: 'Not enough evidence',
    QUARANTINED_FOR_REVIEW: 'Quarantined for review',
    RETRYABLE_FAILED: 'Retryable failure',
    SKIPPED_NO_APPROVED_DATA: 'Skipped: no approved data',
    pending_approval: 'Pending approval',
    dataset_validated: 'Dataset validated',
  }
  return labels[state] ?? state.replaceAll('_', ' ')
}

function isQuarantined(state: RetrainingRun['state']): boolean {
  return state === 'QUARANTINED_FOR_REVIEW'
}

export function MLModelRunsTable({ runs, selectedRunId, onSelect }: Props) {
  return (
    <section className={styles.runsSection} aria-labelledby="ml-model-runs-heading">
      <div className={styles.sectionHeaderCompact}>
        <div>
          <p className={styles.eyebrow}>Durable run history</p>
          <h2 id="ml-model-runs-heading" className={styles.sectionTitle}>
            Retraining runs
          </h2>
        </div>
        <p className={styles.sectionMeta}>
          Run records show safe operational metadata only. Raw requests and worker output stay out of the workspace.
        </p>
      </div>

      {runs.length === 0 ? (
        <div className={styles.emptyState}>
          <strong>No retraining runs have been requested yet.</strong>
          <span>Request a run after approved verified reviews are ready.</span>
        </div>
      ) : (
        <div>
          <p className={styles.tableHint}>Scroll horizontally to view all columns on narrow screens.</p>
          <div className={styles.tableScroll}>
            <table className={styles.runsTable}>
              <caption className={styles.visuallyHidden}>
                Retraining run history. Exported and rejected counts are not included in the current safe run contract.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Run ID</th>
                  <th scope="col">Trigger</th>
                  <th scope="col">Dataset</th>
                  <th scope="col">Eligible</th>
                  <th scope="col">Exported</th>
                  <th scope="col">Rejected</th>
                  <th scope="col">Quarantined</th>
                  <th scope="col">Candidate</th>
                  <th scope="col">Stage</th>
                  <th scope="col">Status</th>
                  <th scope="col">Attempt</th>
                  <th scope="col">Heartbeat</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => {
                  const selected = run.run_id === selectedRunId
                  const dataset = run.dataset_version ?? run.source_dataset_version

                  return (
                    <tr key={run.run_id} className={selected ? styles.selectedRow : undefined}>
                      <td>
                        <button
                          type="button"
                          className={styles.runIdButton}
                          aria-pressed={selected}
                          onClick={() => onSelect(run.run_id)}
                        >
                          {run.run_id}
                        </button>
                      </td>
                      <td>{run.trigger}</td>
                      <td className={styles.monoCell}>{dataset}</td>
                      <td>{run.approved_sample_count}</td>
                      <td aria-label="Exported count unavailable">—</td>
                      <td aria-label="Rejected count unavailable">—</td>
                      <td>
                        <span className={isQuarantined(run.state) ? styles.statusWarning : styles.statusQuiet}>
                          {isQuarantined(run.state) ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className={styles.monoCell}>{run.candidate_model_version ?? '—'}</td>
                      <td>{run.stage.replaceAll('_', ' ')}</td>
                      <td>
                        <span className={styles.statusBadge}>{formatState(run.state)}</span>
                      </td>
                      <td>{Math.max(1, run.attempt)}</td>
                      <td>{formatStableDateTime(run.heartbeat_at, '—')}</td>
                      <td>{formatStableDateTime(run.created_at, '—')}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
