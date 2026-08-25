import type { AlertConfidenceTier } from '@/features/alerts/contract'

const TIMEZONE_SUFFIX = /(Z|[+-]\d{2}:?\d{2})$/i

/**
 * Parse timestamps from the API as instants.
 *
 * Current API responses are UTC/RFC3339. The UTC fallback keeps legacy SQLite
 * rows safe while the backend contract is being tightened: a timezone-naive
 * value must not be interpreted as the browser's local wall-clock time.
 */
export function parseApiTimestamp(value: string | null | undefined): Date | null {
  if (!value) return null
  const normalized = TIMEZONE_SUFFIX.test(value) ? value : `${value}Z`
  const parsed = new Date(normalized)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatAlertDateTime(
  value: string | null | undefined,
  options: Intl.DateTimeFormatOptions = {}
): string {
  const parsed = parseApiTimestamp(value)
  if (!parsed) return 'Unknown timestamp'

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    ...options,
  })
}

export function formatStableDateTime(
  value: string | null | undefined,
  fallback = 'Unknown timestamp'
): string {
  const parsed = parseApiTimestamp(value)
  if (!parsed) return fallback

  return parsed.toLocaleString('en-US', {
    timeZone: 'UTC',
    timeZoneName: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export function formatRelativeTime(
  value: string | null | undefined,
  nowMs = Date.now()
): string {
  const parsed = parseApiTimestamp(value)
  if (!parsed) return 'Unknown time'

  const differenceSeconds = Math.floor((nowMs - parsed.getTime()) / 1000)
  const absoluteSeconds = Math.abs(differenceSeconds)
  const suffix = differenceSeconds < 0 ? '' : ' ago'
  const prefix = differenceSeconds < 0 ? 'in ' : ''

  if (absoluteSeconds < 60) return `${prefix}${absoluteSeconds}s${suffix}`

  const minutes = Math.floor(absoluteSeconds / 60)
  if (minutes < 60) return `${prefix}${minutes}min${minutes === 1 ? '' : 's'}${suffix}`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${prefix}${hours}hr${hours === 1 ? '' : 's'}${suffix}`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${prefix}${days}day${days === 1 ? '' : 's'}${suffix}`

  const months = Math.floor(days / 30)
  if (days < 365) return `${prefix}${months}month${months === 1 ? '' : 's'}${suffix}`

  const years = Math.floor(days / 365)
  return `${prefix}${years}year${years === 1 ? '' : 's'}${suffix}`
}

export function formatConfidencePercent(confidence: number | null | undefined): string {
  if (confidence == null || !Number.isFinite(confidence)) return '—'

  const percentage = Math.min(Math.max(confidence, 0), 1) * 100
  return `${percentage.toFixed(4).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1')}%`
}

export function formatConfidenceLabel(
  confidence: number | null | undefined,
  confidenceTier: AlertConfidenceTier | string
): string {
  const tierLabel = confidenceTier
    ? `${confidenceTier.charAt(0)}${confidenceTier.slice(1).toLowerCase()} confidence`
    : 'Unknown confidence'
  return `${formatConfidencePercent(confidence)} (${tierLabel})`
}
