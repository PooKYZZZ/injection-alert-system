import { queryOptions, useQuery } from '@tanstack/react-query'
import { toQueryString, DashboardFilters } from '@/lib/searchParams'
import { Alert, PaginatedAlerts } from './types'

export const alertKeys = {
  all: ['alerts'] as const,
  list: (filtersKey: string) => ['alerts', 'list', filtersKey] as const,
  detail: (id: string) => ['alerts', 'detail', id] as const,
}

export function alertListOptions(filters: DashboardFilters) {
  return queryOptions<PaginatedAlerts>({
    queryKey: alertKeys.list(toQueryString(filters)),
    queryFn: async () => {
      const r = await fetch(`/api/alerts?${toQueryString(filters)}`)
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
      return r.json()
    },
    staleTime: 0,
  })
}

export function alertDetailOptions(id: string | null) {
  return queryOptions<Alert>({
    queryKey: alertKeys.detail(id ?? ''),
    queryFn: async () => {
      const r = await fetch(`/api/alerts/${id}`)
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
      return r.json()
    },
    enabled: id !== null,
  })
}

export const useAlerts = (filters: DashboardFilters) => useQuery(alertListOptions(filters))
export const useAlert = (id: string | null) => useQuery(alertDetailOptions(id))
