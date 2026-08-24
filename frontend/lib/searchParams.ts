export type ConfidenceTierFilter = 'ALL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type SeverityFilter = ConfidenceTierFilter
export type TimeRange = '1h' | '6h' | '24h' | '7d'

export interface DashboardFilters {
  confidenceTier: ConfidenceTierFilter
  timeRange: TimeRange
  search: string
}

export const DEFAULT_FILTERS: DashboardFilters = {
  confidenceTier: 'ALL',
  timeRange: '24h',
  search: '',
}

const CONFIDENCE_TIER_VALUES = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const
const TIME_RANGE_VALUES = ['1h', '6h', '24h', '7d'] as const
const MAX_SEARCH_LENGTH = 200

export async function normalizeSearchParams(
  searchParams: Promise<Record<string, string | string[] | undefined>>
): Promise<DashboardFilters> {
  const params = await searchParams
  const rawConfidenceTier =
    typeof params.confidence_tier === 'string'
      ? params.confidence_tier
      : typeof params.severity === 'string'
        ? params.severity
        : undefined

  return {
    confidenceTier: (
      typeof rawConfidenceTier === 'string' &&
        (CONFIDENCE_TIER_VALUES as readonly string[]).includes(rawConfidenceTier)
        ? rawConfidenceTier as ConfidenceTierFilter
        : DEFAULT_FILTERS.confidenceTier
    ),
    timeRange: (
      typeof params.timeRange === 'string' &&
        (TIME_RANGE_VALUES as readonly string[]).includes(params.timeRange)
        ? params.timeRange as TimeRange
        : DEFAULT_FILTERS.timeRange
    ),
    search: typeof params.search === 'string' ? params.search.slice(0, MAX_SEARCH_LENGTH) : '',
  }
}

// Alerts-specific search param normalization
import { AlertFiltersSchema, type AlertFilters } from '@/features/alerts/schemas'

export function toQueryString(filters: DashboardFilters): string {
  const params = new URLSearchParams({
    confidence_tier: filters.confidenceTier,
    timeRange: filters.timeRange,
    search: filters.search,
  })
  return params.toString()
}

export function toAlertQueryString(filters: AlertFilters): string {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null) continue

    if (key === 'confidence_level' && Array.isArray(value)) {
      for (const entry of value) params.append(key, String(entry))
      continue
    }

    params.set(key, String(value))
  }

  return params.toString()
}

export const DEFAULT_ALERT_FILTERS: AlertFilters = {
  page: 1,
  pageSize: 20,
  sort_by: 'timestamp',
  sort_dir: 'desc',
}

/**
 * Read the query string at event time so rapid URL updates do not rebuild a
 * later filter change from React's previous render.
 */
export function getCurrentSearchParams(
  fallback?: Pick<URLSearchParams, 'toString'>
): URLSearchParams {
  if (typeof window !== 'undefined') {
    return new URLSearchParams(window.location.search)
  }
  return new URLSearchParams(fallback?.toString() ?? '')
}

export function normalizeAlertSearchParams(
  params: Record<string, string | string[] | undefined>
): AlertFilters {
  const normalized: Record<string, string | string[]> = {}

  for (const [key, value] of Object.entries(params)) {
    if (key === 'confidence_level') {
      if (typeof value === 'string') normalized[key] = [value]
      else if (Array.isArray(value) && value.length > 0) {
        normalized[key] = Array.from(new Set(value))
      }
      continue
    }

    if (typeof value === 'string') normalized[key] = value
    else if (Array.isArray(value) && value.length > 0) normalized[key] = value[0]
  }

  const rawConfidenceTier = normalized.confidence_tier
  const rawSeverity = normalized.severity
  if (rawConfidenceTier === undefined && typeof rawSeverity === 'string') {
    normalized.confidence_tier = rawSeverity
  }

  const parsed = AlertFiltersSchema.safeParse(normalized)
  return parsed.success ? parsed.data : DEFAULT_ALERT_FILTERS
}
