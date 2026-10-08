'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
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
        className="inline-flex min-h-10 items-center justify-center rounded-md border border-surface-border px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel"
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
        className="w-[min(28rem,calc(100%-2rem))] rounded-xl border border-surface-border bg-surface-card p-0 text-[var(--color-text-primary)] shadow-2xl backdrop:bg-black/60"
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
          <div>
            <h2 id="traffic-export-title" className="text-base font-semibold">
              Export Traffic History
            </h2>
            <p id="traffic-export-description" className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Choose inclusive calendar dates. This custom range replaces the page’s Time Window preset; other supported Traffic History filters are applied in {timezone}.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span>Start date</span>
              <input
                type="date"
                required
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'traffic-export-error' : undefined}
                className="min-h-10 rounded-md border border-surface-border bg-surface-inset px-2 text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span>End date</span>
              <input
                type="date"
                required
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'traffic-export-error' : undefined}
                className="min-h-10 rounded-md border border-surface-border bg-surface-inset px-2 text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
              />
            </label>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)]">
            Maximum range: 31 calendar days. Spreadsheet formula-like values are prefixed for Excel-oriented safety, which can change those cell values.
          </p>
          {error && <p id="traffic-export-error" role="alert" className="text-sm text-red-400">{error}</p>}
          {announcement && <p role="status" className="text-sm text-[var(--color-text-secondary)]">{announcement}</p>}
          {download && (
            <a
              href={download.url}
              download={download.filename}
              className="w-fit text-sm font-medium text-action-accent underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
            >
              Download {download.filename}
            </a>
          )}
          <div className="flex flex-wrap justify-end gap-2 border-t border-surface-border pt-4">
            <button
              type="button"
              onClick={() => dialogRef.current?.close()}
              className="min-h-10 rounded-md border border-surface-border px-3 py-2 text-sm hover:bg-surface-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={loading}
              className="min-h-10 rounded-md bg-action-accent px-3 py-2 text-sm font-semibold text-action-contrast hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border disabled:cursor-wait disabled:opacity-60"
            >
              {loading ? 'Preparing CSV…' : 'Prepare CSV'}
            </button>
          </div>
        </form>
      </dialog>
    </>
  )
}
