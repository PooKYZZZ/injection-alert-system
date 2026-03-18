import { queryOptions, useQuery, type UseQueryResult } from '@tanstack/react-query'
import { toQueryString, DashboardFilters } from '@/lib/searchParams'
import { Alert, PaginatedAlerts } from './types'

/*
 * QUERY FRESHNESS POLICY
 *
 * Alerts: staleTime = 0 (always refetch on mount)
 * - Rationale: Security alerts are time-critical. Analysts need the latest data.
 * - Alerts are the primary working surface for triage decisions.
 * - No local caching - each mount triggers a fresh fetch.
 *
 * The alerts query throws on non-2xx responses - errors propagate to UI.
 * No placeholderData or fake success states are used.
 */

export const alertKeys = {
  all: ['alerts'] as const,
  list: (filtersKey: string) => ['alerts', 'list', filtersKey] as const,
  detail: (id: string) => ['alerts', 'detail', id] as const,
}

export function alertListOptions(filters: DashboardFilters) {
  return queryOptions<PaginatedAlerts>({
    queryKey: alertKeys.list(toQueryString(filters)),
    queryFn: async () => {
      const url = `/api/alerts?${toQueryString(filters)}`
      const r = await fetch(url)
      if (!r.ok) throw new Error(`${url} responded with ${r.status}`)
      return r.json()
    },
    staleTime: 0,
  })
}

export function alertDetailOptions(id: string | null) {
  return queryOptions<Alert>({
    queryKey: alertKeys.detail(id ?? ''),
    queryFn: async () => {
      if (!id) throw new Error('Alert ID is required')
      const url = `/api/alerts/${id}`
      const r = await fetch(url)
      if (!r.ok) throw new Error(`${url} responded with ${r.status}`)
      return r.json()
    },
    enabled: id !== null,
  })
}

export const useAlerts = (
  filters: DashboardFilters
): UseQueryResult<PaginatedAlerts, Error> => useQuery(alertListOptions(filters))

export const useAlert = (id: string | null): UseQueryResult<Alert, Error> =>
  useQuery(alertDetailOptions(id))
