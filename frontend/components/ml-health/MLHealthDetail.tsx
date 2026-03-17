'use client'

import { useMLHealth } from '@/features/ml-health/queries'

function StatusBadge({ status }: { status: 'HEALTHY' | 'DEGRADED' | 'DOWN' }) {
  const className =
    status === 'HEALTHY'
      ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
      : status === 'DEGRADED'
        ? 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'
        : 'border-severity-high-border bg-severity-high-bg text-severity-high-text'

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${className}`}>
      {status}
    </span>
  )
}

function MetricSkeletonCard() {
  return (
    <div className="rounded-md border border-border-light bg-bg-inset p-3" aria-hidden="true">
      <div className="h-2.5 w-24 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="mt-4 h-6 w-20 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="mt-3 h-2.5 w-16 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
    </div>
  )
}

function ThresholdRow({
  label,
  value,
  barWidth,
  barClassName,
}: {
  label: string
  value: string
  barWidth: string
  barClassName: string
}) {
  return (
    <div className="grid grid-cols-[90px_1fr_auto] items-center gap-3">
      <span className="text-xs text-text-secondary">{label}</span>
      <div className="h-[5px] rounded-full bg-bg-inset">
        <div
          className={`h-full rounded-full opacity-70 ${barClassName}`}
          style={{ width: barWidth, height: '100%' }}
        />
      </div>
      <span className="text-xs text-text-secondary">{value}</span>
    </div>
  )
}

function getModelDisplayName(modelVersion: string | null | undefined): string {
  if (!modelVersion) return 'Unknown model'
  if (modelVersion.startsWith('distilbert_v3')) return 'DistilBERT v3'
  if (modelVersion.startsWith('distilbert_v2')) return 'DistilBERT v2'
  if (modelVersion.startsWith('bert_')) return 'BERT'
  if (modelVersion.startsWith('minilm_')) return 'MiniLM'
  // Fallback: capitalize and clean the raw string
  return modelVersion.split('_').slice(0, 2).join(' ')
}

export default function MLHealthDetail() {
  const { data, isPending, isError, error, refetch } = useMLHealth()

  // Dynamic thresholds with fallback
  const thresholds = data?.thresholds as
    | { low?: number | null; medium?: number | null; high?: number | null }
    | undefined

  const formatPercent = (value: number): string => {
    const pct = value <= 1 ? value * 100 : value
    return `${Math.round(pct)}%`
  }

  // Defaults match previous hardcoded behavior
  let lowValue = '< 50%'
  let mediumValue = '50–80%'
  let highValue = '> 80%'
  let lowWidth = '30%'
  let mediumWidth = '60%'
  let highWidth = '100%'
  let hasMedium = true

  if (thresholds && typeof thresholds.low === 'number' && typeof thresholds.high === 'number') {
    const low = thresholds.low
    const medium = thresholds.medium
    const high = thresholds.high
    const toPct = (v: number) => (v <= 1 ? v * 100 : v)
    const maxVal = typeof high === 'number' ? toPct(high) : 100

    if (maxVal > 0 && toPct(low) >= 0 && toPct(low) <= maxVal) {
      if (typeof medium === 'number' && toPct(medium) >= toPct(low) && toPct(medium) <= maxVal) {
        // Three-band case
        lowValue = `< ${formatPercent(low)}`
        mediumValue = `${formatPercent(low)}–${formatPercent(medium)}`
        highValue = `> ${formatPercent(medium)}`
        lowWidth = `${(toPct(low) / maxVal) * 100}%`
        mediumWidth = `${((toPct(medium) - toPct(low)) / maxVal) * 100}%`
        highWidth = `${((maxVal - toPct(medium)) / maxVal) * 100}%`
        hasMedium = true
      } else {
        // Two-band case
        lowValue = `< ${formatPercent(low)}`
        highValue = `>= ${formatPercent(low)}`
        lowWidth = `${(toPct(low) / maxVal) * 100}%`
        highWidth = `${((maxVal - toPct(low)) / maxVal) * 100}%`
        hasMedium = false
      }
    }
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-lg border border-severity-high-border bg-severity-high-bg p-6">
        <p className="text-sm font-medium text-severity-high-text">Unable to load ML Health data.</p>
        <p className="text-xs text-text-secondary">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
        <button
          onClick={() => void refetch()}
          className="rounded-md border border-accent-blue bg-accent-blue-bg px-4 py-2 text-sm font-medium text-accent-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data && !isPending) {
    return (
      <div className="rounded-lg border border-border-light bg-bg-panel p-4">
        <p className="text-sm text-text-secondary">Unable to load ML Health data.</p>
      </div>
    )
  }

  const showUnavailableNote =
    !isPending && data && (data.latency_trend === null || data.drift_score === null)

  return (
    <div className="flex flex-col gap-6 pb-8" data-testid="ml-health-detail">
      <section className="rounded-lg border border-border-light bg-bg-panel p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-[7px] bg-accent-blue-bg text-sm text-accent-blue">
            DB
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-medium text-text-primary">
                {isPending ? 'Loading model...' : getModelDisplayName(data?.model_version)}
              </h2>
              {!isPending && data ? <StatusBadge status={data.status} /> : null}
            </div>
            <p className="mt-1 font-mono text-[9px] text-text-muted">
              {isPending ? 'Loading model version...' : data?.model_version}
            </p>
          </div>
        </div>
        <div style={{ height: '1px', background: '#1a2236', margin: '12px 0' }} />
      </section>

      <div style={{ height: '1px', background: '#1a2236', margin: '0 0 4px 0' }} />

      <section className="rounded-lg border border-border-light bg-bg-panel p-5">
        <div className="grid gap-4 md:grid-cols-3">
          {isPending ? (
            <>
              <MetricSkeletonCard />
              <MetricSkeletonCard />
              <MetricSkeletonCard />
            </>
          ) : data ? (
            <>
              <div className="rounded-md border border-border-light bg-bg-inset p-3">
                <p className="text-xs text-text-secondary">Current inference latency</p>
                <div className="mt-3 text-2xl font-medium text-accent-amber">
                  {Math.round(data.latency_ms)}ms
                </div>
              </div>
              <div className="rounded-md border border-border-light bg-bg-inset p-3">
                <p className="text-xs text-text-secondary">Drift status</p>
                <div className="mt-3 text-2xl font-medium text-severity-safe-accent">
                  {data.drift_status}
                </div>
              </div>
              <div className="rounded-md border border-border-light bg-bg-inset p-3">
                <p className="text-xs text-text-secondary">Requests scored</p>
                <div className="mt-3 text-2xl font-medium text-accent-blue">
                  {data.traffic_processed.toLocaleString()}
                </div>
                <p className="mt-2 text-[10px] text-text-muted">Current session</p>
              </div>
            </>
          ) : null}
        </div>

        {showUnavailableNote ? (
          <p className="mt-4 rounded-r-md border-l-2 border-l-accent-blue-bg bg-bg-inset px-3 py-2 text-[10px] text-text-muted">
            Latency trend and drift score are not included in the current API response.
          </p>
        ) : null}

        <div className="mt-6 border-t border-[color:var(--color-bg-elevated)] pt-6">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
            Confidence Thresholds
          </h3>
          <div className="mt-4 space-y-3">
            <ThresholdRow
              label="Low"
              value={lowValue}
              barWidth={lowWidth}
              barClassName="bg-severity-safe-accent"
            />
            {hasMedium ? (
              <ThresholdRow
                label="Medium"
                value={mediumValue}
                barWidth={mediumWidth}
                barClassName="bg-accent-yellow"
              />
            ) : null}
            <ThresholdRow
              label="High"
              value={highValue}
              barWidth={highWidth}
              barClassName="bg-severity-high-accent"
            />
          </div>
          <p className="mt-4 border-l-2 border-l-accent-blue-bg pl-2 text-[9px] text-text-muted">
            These thresholds determine how ML confidence scores are mapped to LOW / MEDIUM / HIGH severity bands in the Dashboard and Alerts views.
          </p>
        </div>
      </section>
    </div>
  )
}
