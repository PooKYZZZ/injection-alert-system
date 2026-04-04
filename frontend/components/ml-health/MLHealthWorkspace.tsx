'use client'

import { useMemo, useState } from 'react'
import { Activity, Clock3, ShieldCheck } from 'lucide-react'
import { useMLHealth } from '@/features/ml-health/queries'
import { ErrorState, LoadingSkeleton } from '@/components/ui/StateViews'
import { MLHealthOverviewSection } from './MLHealthOverviewSection'
import { MLHealthDiagnosticsSection } from './MLHealthDiagnosticsSection'
import { buildMLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type OverviewMode = 'overview' | 'diagnostics'

export function MLHealthWorkspace() {
  const { data: health, isPending, isError, refetch } = useMLHealth()
  const [view, setView] = useState<OverviewMode>('overview')

  const viewModel = useMemo(() => (health ? buildMLHealthViewModel(health) : null), [health])

  if (isPending) {
    return (
      <div className={styles.loadingWrap}>
        <LoadingSkeleton rows={10} />
      </div>
    )
  }

  if (isError || !health || !viewModel) {
    return (
      <div className={styles.loadingWrap}>
        <ErrorState message="Failed to load ML health data" onRetry={refetch} />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <section className={styles.identityStrip}>
        <div>
          <div className={styles.identityHeader}>
            <ShieldCheck size={16} className={styles.identityShield} />
            <span className={styles.identityTitle}>{health.model_version}</span>
          </div>
          <div className={styles.identityMeta}>
            <span className={styles.identityMetaItem}>
              <Activity size={11} /> {viewModel.granularityLabel}
            </span>
            <span className={styles.identityMetaItem}>
              <Clock3 size={11} /> {viewModel.windowLabel}
            </span>
          </div>
        </div>

        <div className={styles.identityTools}>
          <div className={styles.viewToggle}>
            <button
              type="button"
              className={`${styles.viewToggleButton} ${view === 'overview' ? styles.viewToggleButtonActive : ''}`}
              onClick={() => setView('overview')}
            >
              Overview
            </button>
            <button
              type="button"
              className={`${styles.viewToggleButton} ${view === 'diagnostics' ? styles.viewToggleButtonActive : ''}`}
              onClick={() => setView('diagnostics')}
            >
              Diagnostics
            </button>
          </div>
        </div>
      </section>

      {view === 'overview' ? (
        <MLHealthOverviewSection health={health} viewModel={viewModel} />
      ) : (
        <MLHealthDiagnosticsSection health={health} viewModel={viewModel} />
      )}
    </div>
  )
}
