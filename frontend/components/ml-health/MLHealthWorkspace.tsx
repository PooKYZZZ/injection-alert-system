'use client'

import { useMemo, useRef, useState, type KeyboardEvent } from 'react'
import Link from 'next/link'
import { RefreshCw } from 'lucide-react'

import { ErrorState, LoadingSkeleton } from '@/components/ui/StateViews'
import { useMLHealth } from '@/features/ml-health/queries'

import { MLHealthDiagnosticsSection } from './MLHealthDiagnosticsSection'
import { MLHealthOverviewSection } from './MLHealthOverviewSection'
import { buildMLHealthViewModel } from './MLHealthWorkspaceViewModel'
import styles from './MLHealthWorkspace.module.css'

type WorkspaceView = 'overview' | 'diagnostics'

const tabs: Array<{ key: WorkspaceView; label: string; description: string }> = [
  {
    key: 'overview',
    label: 'Overview',
    description: 'Serving status and the operational snapshot',
  },
  {
    key: 'diagnostics',
    label: 'Diagnostics',
    description: 'Reported evidence and policy details',
  },
]

export function MLHealthWorkspace() {
  const { data: health, isPending, isFetching, isError, refetch } = useMLHealth()
  const [view, setView] = useState<WorkspaceView>('overview')
  const tabRefs = useRef<Record<WorkspaceView, HTMLButtonElement | null>>({
    overview: null,
    diagnostics: null,
  })

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

  const activeTab = tabs.find((tab) => tab.key === view) ?? tabs[0]

  function handleViewTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabs.length - 1
    if (nextIndex == null) return

    event.preventDefault()
    const nextTab = tabs[nextIndex]
    setView(nextTab.key)
    tabRefs.current[nextTab.key]?.focus()
  }

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div className={styles.pageHeading}>
          <p className={styles.eyebrow}>Model observability</p>
          <h1>ML Health</h1>
          <p className={styles.pageDescription}>
            Confirm the serving state first, then open the evidence you need to investigate model behavior.
          </p>
        </div>

        <div className={styles.pageActions}>
          <div className={styles.modelIdentity}>
            <div>
              <span className={styles.metaLabel}>Active model</span>
              <code>{health.model_version}</code>
            </div>
          </div>
          <Link href="/ml-model" className={styles.secondaryLink}>Open Model Operations</Link>
          <button
            type="button"
            className={styles.refreshButton}
            aria-label={isFetching ? 'Refreshing ML health' : 'Refresh ML health'}
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            <RefreshCw size={14} aria-hidden="true" className={isFetching ? styles.spin : undefined} />
            {isFetching ? 'Refreshing…' : 'Refresh snapshot'}
          </button>
        </div>
      </header>

      <section className={styles.viewBar} aria-label="ML health view controls">
        <div className={styles.viewBarMain}>
          <span className={styles.viewLabel}>View</span>
          <div className={styles.tabList} role="tablist" aria-label="ML health views">
            {tabs.map((tab, index) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                id={`ml-health-tab-${tab.key}`}
                aria-controls={`ml-health-panel-${tab.key}`}
                aria-selected={view === tab.key}
                tabIndex={view === tab.key ? 0 : -1}
                className={`${styles.tabButton} ${view === tab.key ? styles.tabButtonActive : ''}`}
                onClick={() => setView(tab.key)}
                onKeyDown={(event) => handleViewTabKeyDown(event, index)}
                ref={(element) => { tabRefs.current[tab.key] = element }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className={styles.snapshotMeta}>
          <span>Snapshot-based</span>
          <span>{viewModel.sourceFreshnessDisplay}</span>
          <span>Retrieved {viewModel.retrievedAtDisplay}</span>
        </div>
      </section>

      <div
        id={`ml-health-panel-${view}`}
        role="tabpanel"
        aria-labelledby={`ml-health-tab-${view}`}
        tabIndex={0}
        className={styles.tabPanel}
      >
        <p className={styles.srOnly}>{activeTab.description}</p>
        {view === 'overview' ? (
          <MLHealthOverviewSection health={health} viewModel={viewModel} />
        ) : (
          <MLHealthDiagnosticsSection health={health} viewModel={viewModel} />
        )}
      </div>
    </div>
  )
}
