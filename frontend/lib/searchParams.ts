export type SeverityFilter = 'ALL' | 'LOW' | 'MEDIUM' | 'HIGH'
export type TimeRange = '1h' | '6h' | '24h' | '7d'

export interface DashboardFilters {
  severity: SeverityFilter
  timeRange: TimeRange
  search: string
}

export const DEFAULT_FILTERS: DashboardFilters = {
  severity: 'ALL',
  timeRange: '24h',
  search: '',
}

const SEVERITY_VALUES = ['ALL', 'LOW', 'MEDIUM', 'HIGH'] as const
const TIME_RANGE_VALUES = ['1h', '6h', '24h', '7d'] as const
const MAX_SEARCH_LENGTH = 200

export async function normalizeSearchParams(
  searchParams: Promise<Record<string, string | string[] | undefined>>
): Promise<DashboardFilters> {
  const params = await searchParams
  return {
    severity: (
      typeof params.severity === 'string' &&
      (SEVERITY_VALUES as readonly string[]).includes(params.severity)
        ? params.severity as SeverityFilter
        : DEFAULT_FILTERS.severity
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

export function toQueryString(filters: DashboardFilters): string {
  return new URLSearchParams({
    severity: filters.severity,
    timeRange: filters.timeRange,
    search: filters.search,
  }).toString()
}
