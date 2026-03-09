import { queryOptions, useQuery } from '@tanstack/react-query'
import { MLHealthData } from './types'

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
