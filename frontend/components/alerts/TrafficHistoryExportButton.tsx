'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { X } from 'lucide-react'
import { TrafficHistoryExportRequestSchema } from '@/features/alerts/export-contract'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'

const FILTER_KEYS = [
  'include_normal',
  'confidence_tier',
  'severity',
  'search',
  'action',
  'triage_status',
  'prediction',
  'source_ip',
] as const

function localDateInZone(date: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

function subtractCalendarDays(value: string, days: number): string {
  const [year, month, day] = value.split('-').map(Number)
  const result = new Date(Date.UTC(year, month - 1, day - days))
  return [
    result.getUTCFullYear().toString().padStart(4, '0'),
    (result.getUTCMonth() + 1).toString().padStart(2, '0'),
    result.getUTCDate().toString().padStart(2, '0'),
  ].join('-')
}

function filenameFromResponse(response: Response, fallback: string): string {
  const disposition = response.headers.get('Content-Disposition')
  const candidate = disposition?.match(/filename="([A-Za-z0-9_.-]+)"/)?.[1]
  return candidate ?? fallback
}

export function TrafficHistoryExportButton({ role }: { role?: unknown }) {
  const searchParams = useSearchParams()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [download, setDownload] = useState<{ url: string; filename: string } | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const canExport = roleHasPermission(role, PERMISSIONS.TRAFFIC_EXPORT)

  const currentFilters = useMemo(() => {
    const filters: Record<string, unknown> = {}
    for (const key of FILTER_KEYS) {
      const value = searchParams.get(key)
      if (value !== null && value !== '') filters[key] = value
    }
    const confidenceLevels = searchParams.getAll('confidence_level').filter(Boolean)
    if (confidenceLevels.length > 0) filters.confidence_level = confidenceLevels
    if ('include_normal' in filters) {
      filters.include_normal = filters.include_normal === 'true'
    }
    const tier = searchParams.get('confidence_tier') ?? searchParams.get('severity')
    delete filters.severity
    delete filters.confidence_tier
    if (tier && tier !== 'ALL') filters.confidence_tier = tier
    for (const key of ['action', 'triage_status', 'prediction', 'source_ip', 'search'] as const) {
      if (filters[key] === 'ALL') delete filters[key]
    }
    return filters
  }, [searchParams])

  useEffect(() => {
    return () => {
      if (download) URL.revokeObjectURL(download.url)
    }
  }, [download])

  if (!canExport) return null

  function openDialog() {
    const currentTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    const today = localDateInZone(new Date(), currentTimezone)
    setTimezone(currentTimezone)
    setEndDate(today)
    setStartDate(subtractCalendarDays(today, 6))
    setError(null)
    setAnnouncement('')
    setDownload(null)
    dialogRef.current?.showModal()
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setAnnouncement('')
    setDownload(null)

    const parsed = TrafficHistoryExportRequestSchema.safeParse({
      ...currentFilters,
      start_date: startDate,
      end_date: endDate,
      timezone,
    })
    if (!parsed.success) {
      const dateIssue = parsed.error.issues.find((issue) =>
        issue.path.includes('start_date') || issue.path.includes('end_date')
      )
      setError(dateIssue?.message ?? 'Check the export dates and current filters.')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/traffic-history/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        body: JSON.stringify(parsed.data),
      })
      if (!response.ok) {
        const payload: unknown = await response.json().catch(() => null)
        const message =
          typeof payload === 'object' && payload !== null && 'error' in payload &&
          typeof payload.error === 'object' && payload.error !== null &&
          'message' in payload.error && typeof payload.error.message === 'string'
            ? payload.error.message
            : 'Traffic History export could not be completed. Try a shorter date range.'
        setError(message)
        return
      }

      const blob = await response.blob()
      if (blob.size > 5 * 1024 * 1024) {
        setError('The export exceeded the allowed file size. Narrow the date range and retry.')
        return
      }
      const filename = filenameFromResponse(
        response,
        `traffic-history_${startDate}_to_${endDate}.csv`
      )
      setDownload({ url: URL.createObjectURL(blob), filename })
      setAnnouncement('CSV export is ready to download.')
    } catch {
      setError('Traffic History export is unavailable. Check your connection and retry.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        className="min-h-[40px] rounded-md border border-accent-action bg-accent-action px-3 py-2 text-xs font-semibold text-surface-shell transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action focus-visible:ring-offset-2 focus-visible:ring-offset-surface-card"
        aria-haspopup="dialog"
      >
        Export CSV
      </button>
      <dialog
        ref={dialogRef}
        aria-labelledby="traffic-export-title"
        aria-describedby="traffic-export-description"
        onClose={() => {
          if (download) URL.revokeObjectURL(download.url)
          setDownload(null)
        }}
        className="fixed inset-0 m-auto flex max-h-[calc(100dvh_-_2rem)] w-[calc(100vw_-_2rem)] max-w-xl flex-col overflow-hidden rounded-2xl border border-surface-border bg-surface-card p-0 text-[var(--color-text-primary)] shadow-2xl backdrop:bg-black/60"
      >
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-col">
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-surface-border px-5 py-4 sm:px-6">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">
                Traffic History · CSV
              </p>
              <h2 id="traffic-export-title" className="mt-1 text-lg font-semibold">
                Export Traffic History
              </h2>
              <p id="traffic-export-description" className="mt-1 max-w-prose text-sm leading-5 text-[var(--color-text-secondary)]">
                Choose up to 31 calendar days. This replaces the Time Window preset; other Traffic History filters stay applied in {timezone}.
              </p>
            </div>
            <button
              type="button"
              onClick={() => dialogRef.current?.close()}
              aria-label="Close export dialog"
              title="Close"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-surface-border text-[var(--color-text-secondary)] transition-colors hover:bg-surface-inset hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action"
            >
              <X aria-hidden="true" className="h-4 w-4" />
            </button>
          </header>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5 sm:px-6">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium">Start date</span>
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'traffic-export-error' : undefined}
                  className="min-h-11 w-full rounded-lg border border-surface-border bg-surface-inset px-3 text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action"
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium">End date</span>
                <input
                  type="date"
                  required
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'traffic-export-error' : undefined}
                  className="min-h-11 w-full rounded-lg border border-surface-border bg-surface-inset px-3 text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action"
                />
              </label>
            </div>
            <p className="text-xs leading-5 text-[var(--color-text-secondary)]">
              The calendar opens to the selected month. Use its month arrows to browse other dates. Both dates are included. Formula-like CSV values are prefixed for Excel safety, which can change those cell values.
            </p>
            {error && <p id="traffic-export-error" role="alert" className="text-sm text-red-400">{error}</p>}
            {announcement && <p role="status" className="sr-only">{announcement}</p>}
            {download && (
              <div className="rounded-lg border border-surface-border bg-surface-inset p-3">
                <p className="text-xs font-medium text-[var(--color-text-secondary)]">Your CSV is ready</p>
                <a
                  href={download.url}
                  download={download.filename}
                  className="mt-1 block w-fit break-all text-sm font-medium text-accent-action underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action"
                >
                  Download {download.filename}
                </a>
              </div>
            )}
          </div>

          <footer className="flex shrink-0 flex-wrap justify-end gap-2 border-t border-surface-border bg-surface-card px-5 py-4 sm:px-6">
            <button
              type="button"
              onClick={() => dialogRef.current?.close()}
              className="min-h-10 rounded-md border border-surface-border px-3 py-2 text-sm hover:bg-surface-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={loading}
              className="min-h-10 rounded-md bg-accent-action px-3 py-2 text-sm font-semibold text-surface-shell transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action disabled:cursor-wait disabled:opacity-60"
            >
              {loading ? 'Preparing CSV…' : 'Prepare CSV'}
            </button>
          </footer>
        </form>
      </dialog>
    </>
  )
}
