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
