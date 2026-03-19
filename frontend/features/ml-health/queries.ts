import { queryOptions, useQuery } from '@tanstack/react-query'
import { MLHealthData } from './types'

/*
 * QUERY FRESHNESS POLICY
 *
 * ML Health: staleTime = 30_000 (30 second cache)
 * - Rationale: ML health status changes infrequently.
 * - 30s cache balances freshness with performance.
 * - Thresholds are used for confidence band classification.
 *
 * The ML health query throws on non-2xx responses - errors propagate to UI.
 * No placeholderData or fake success states are used.
 */

export const mlHealthKeys = {
  all: ['ml-health'] as const,
  health: () => ['ml-health', 'status'] as const,
}

export function mlHealthOptions() {
  return queryOptions<MLHealthData>({
    queryKey: mlHealthKeys.health(),
    queryFn: async () => {
      const r = await fetch('/api/ml-health')
      if (!r.ok) throw new Error(`/api/ml-health responded with ${r.status}`)
      return r.json()
    },
    staleTime: 30_000,
  })
}

export const useMLHealth = () => useQuery(mlHealthOptions())
