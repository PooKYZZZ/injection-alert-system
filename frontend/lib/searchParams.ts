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

export async function normalizeSearchParams(
  searchParams: Promise<Record<string, string | string[] | undefined>>
): Promise<DashboardFilters> {
  const params = await searchParams
  return {
    severity: (['ALL','LOW','MEDIUM','HIGH'].includes(params.severity as string)
      ? params.severity as SeverityFilter
      : DEFAULT_FILTERS.severity),
    timeRange: (['1h','6h','24h','7d'].includes(params.timeRange as string)
      ? params.timeRange as TimeRange
      : DEFAULT_FILTERS.timeRange),
    search: typeof params.search === 'string' ? params.search : '',
  }
}

export function toQueryString(filters: DashboardFilters): string {
  return new URLSearchParams({
    severity: filters.severity,
    timeRange: filters.timeRange,
    search: filters.search,
  }).toString()
}
