import { queryOptions, useQuery } from '@tanstack/react-query'
import { getBrowserTimeZone } from '@/lib/time-zone'
import { DashboardStats } from './types'

/*
 * QUERY FRESHNESS POLICY
 *
 * Stats: staleTime = 15_000 (15 second cache)
 * - Rationale: Dashboard metrics are expensive aggregates.
 * - 15s cache balances freshness with performance.
 * - Stats are system-wide aggregates, less time-critical than alerts.
 *
 * The stats query throws on non-2xx responses - errors propagate to UI.
 * No placeholderData or fake success states are used.
 */

export const statsKeys = {
  all: ['stats'] as const,
  stats: (window?: string, timezone?: string) => ['stats', 'dashboard', { window, timezone }] as const,
}

export function statsOptions(window?: string, timezone = getBrowserTimeZone()) {
  return queryOptions<DashboardStats>({
    queryKey: statsKeys.stats(window, timezone),
    queryFn: async ({ signal }) => {
      const params = new URLSearchParams()
      if (window) params.set('window', window)
      if (timezone) params.set('timezone', timezone)
      const url = params.size > 0 ? `/api/stats?${params.toString()}` : '/api/stats'
      const r = await fetch(url, { signal })
      if (!r.ok) throw new Error(`/api/stats responded with ${r.status}`)
      return r.json()
    },
    staleTime: 15_000,
    refetchInterval: 15_000,
  })
}

export const useDashboardStats = (window?: string, timezone?: string) =>
  useQuery(statsOptions(window, timezone))
