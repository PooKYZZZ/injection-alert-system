import { queryOptions, useQuery } from '@tanstack/react-query'
import { DashboardStats } from './types'

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
