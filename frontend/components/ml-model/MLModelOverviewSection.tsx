'use client'

import { Activity, Database, Download, Play, ShieldCheck, Users } from 'lucide-react'
import type { ReactNode } from 'react'

import type { RetrainingSummary } from '@/features/ml-model/types'
import { formatStableDateTime } from '@/lib/date-time'
import styles from './MLModelWorkspace.module.css'

interface Props {
  summary: RetrainingSummary
  runInProgress: boolean
  canRun: boolean
  actionsDisabled: boolean
  onRequest: () => void
  onExport: () => void
  actionError?: string | null
  notice?: string | null
}

function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string
  value: string | number
  detail: string
  icon: ReactNode
}) {
  return (
    <article className={styles.metricCard}>
      <div className={styles.metricCardHeader}>
        <span className={styles.metricLabel}>{label}</span>
        <span className={styles.metricIcon} aria-hidden="true">
          {icon}
        </span>
      </div>
      <strong className={styles.metricValue}>{value}</strong>
      <span className={styles.metricDetail}>{detail}</span>
    </article>
  )
}

export function MLModelOverviewSection({
  summary,
  runInProgress,
  canRun,
  actionsDisabled,
  onRequest,
  onExport,
  actionError,
  notice,
}: Props) {
  return (
    <section className={styles.overviewSection} aria-labelledby="ml-model-overview-heading">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.eyebrow}>Operational retraining control</p>
          <h2 id="ml-model-overview-heading" className={styles.sectionTitle}>
            Review the next candidate without changing the active model
          </h2>
          <p className={styles.sectionDescription}>
            Approved verified reviews remain reusable. Every run is local, explicit, and bound to the active model snapshot shown here.
          </p>
        </div>
        <div className={styles.actionCluster}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={onRequest}
            disabled={!canRun || actionsDisabled}
          >
            <Play size={14} aria-hidden="true" />
            Request retraining
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onExport}
            disabled={!canRun || actionsDisabled}
          >
            <Download size={14} aria-hidden="true" />
            Export approved samples
          </button>
          {runInProgress && (
            <span className={styles.actionHint} role="status">
              A run is active; actions unlock after the current stage completes.
            </span>
          )}
          {!canRun && <span className={styles.actionHint}>Read-only reviewer access.</span>}
        </div>
      </div>

      {actionError && (
        <div className={styles.errorCallout} role="alert">
          {actionError}
        </div>
      )}
      {notice && (
        <div className={styles.noticeCallout} role="status">
          {notice}
        </div>
      )}

      <div className={styles.metricGrid}>
        <MetricCard
          label="Active model"
          value={summary.active_model_version}
          detail="Current serving identity"
          icon={<ShieldCheck size={15} />}
        />
        <MetricCard
          label="Approved for training"
          value={summary.approved_count}
          detail="Latest eligible review projection"
          icon={<Users size={15} />}
        />
        <MetricCard
          label="Unreviewed"
          value={summary.unreviewed_count}
          detail="Reviews awaiting an analyst"
          icon={<Activity size={15} />}
        />
        <MetricCard
          label="Excluded from training"
          value={summary.excluded_count}
          detail="Latest excluded review projection"
          icon={<Database size={15} />}
        />
        <MetricCard
          label="Dataset snapshot"
          value={summary.latest_dataset_version ?? 'Not created'}
          detail="Most recent run-local version"
          icon={<Database size={15} />}
        />
        <MetricCard
          label="Last trigger"
          value={formatStableDateTime(summary.last_trigger_time, 'Not recorded')}
          detail={summary.latest_run_state ? `Latest state: ${summary.latest_run_state}` : 'No run recorded'}
          icon={<Activity size={15} />}
        />
      </div>
    </section>
  )
}
