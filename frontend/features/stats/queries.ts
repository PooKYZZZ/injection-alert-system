import { queryOptions, useQuery } from '@tanstack/react-query'
import { DashboardStats } from './types'

/*
 * QUERY FRESHNESS POLICY
 *
 * Stats: staleTime = 30_000 (30 second cache)
 * - Rationale: Dashboard metrics are expensive aggregates.
 * - 30s cache balances freshness with performance.
 * - Stats are system-wide aggregates, less time-critical than alerts.
 *
 * The stats query throws on non-2xx responses - errors propagate to UI.
 * No placeholderData or fake success states are used.
 */

export const statsKeys = {
  all: ['stats'] as const,
  stats: () => ['stats', 'dashboard'] as const,
}

export function statsOptions() {
  return queryOptions<DashboardStats>({
    queryKey: statsKeys.stats(),
    queryFn: async () => {
      const r = await fetch('/api/stats')
      if (!r.ok) throw new Error(`/api/stats responded with ${r.status}`)
      return r.json()
    },
    staleTime: 30_000,
  })
}

export const useDashboardStats = () => useQuery(statsOptions())
