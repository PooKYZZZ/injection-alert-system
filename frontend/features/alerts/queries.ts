import {
  queryOptions,
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import { toQueryString, toAlertQueryString, type DashboardFilters } from '@/lib/searchParams'
import type { AlertFilters } from '@/features/alerts/schemas'
import { Alert, PaginatedAlerts, TriageStatus } from './types'
// Client-side redirect helper for auth failures
function redirectToSignIn(detail?: { retryArgs?: unknown }) {
  if (typeof window === 'undefined') return
  const callback = encodeURIComponent(window.location.href)
  // Open sign-in in a new tab so the analyst doesn't lose context
  try {
    window.open(`/login?callbackUrl=${callback}`, '_blank')
  } catch {
    // Fallback to navigatation if popup blocked
    window.location.assign(`/login?callbackUrl=${callback}`)
  }

  // Notify any React toast listener to show a sign-in toast with optional retry args
  try {
    const ev = new CustomEvent('show-signin-toast', { detail })
    window.dispatchEvent(ev)
  } catch {
    // ignore
  }
}
import type { AlertAction } from './contract'

/*
 * QUERY FRESHNESS POLICY
 *
 * Alerts: staleTime = 5000 (5 second cache)
 * - Rationale: Security alerts are time-critical. Analysts need fresh data.
 * - Alerts are the primary working surface for triage decisions.
 * - Short caching keeps refetches responsive without hammering the BFF.
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
    staleTime: 5000,
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

export function alertListOptionsFromFilters(filters: AlertFilters) {
  return queryOptions<PaginatedAlerts>({
    queryKey: alertKeys.list(toAlertQueryString(filters)),
    queryFn: async () => {
      const url = `/api/alerts?${toAlertQueryString(filters)}`
      const r = await fetch(url)
      if (!r.ok) throw new Error(`${url} responded with ${r.status}`)
      return r.json()
    },
    staleTime: 5000,
  })
}

export const useAlertsFromFilters = (
  filters: AlertFilters
): UseQueryResult<PaginatedAlerts, Error> => useQuery(alertListOptionsFromFilters(filters))

export const useAlert = (id: string | null): UseQueryResult<Alert, Error> =>
  useQuery(alertDetailOptions(id))

export function useTriageMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: string
      status: TriageStatus
    }): Promise<Alert> => {
      const response = await fetch(`/api/alerts/${id}/triage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ triage_status: status }),
      })
      if (!response.ok) {
        throw new Error(`PATCH failed: ${response.status}`)
      }
      return response.json()
    },
    onMutate: async ({ id, status }) => {
      // 1. Cancel outgoing refetches to prevent race conditions
      await queryClient.cancelQueries({ queryKey: alertKeys.all })
      // 2. Snapshot all list queries and the detail query for rollback
      const previousLists = new Map<ReadonlyArray<string>, PaginatedAlerts | undefined>()
      queryClient.getQueriesData<PaginatedAlerts>({ queryKey: alertKeys.all })
        .forEach(([queryKey, data]) => {
          if (queryKey[1] === 'list') {
            previousLists.set(queryKey as ReadonlyArray<string>, data)
          }
        })
      const previousDetail = queryClient.getQueryData<Alert>(
        alertKeys.detail(id)
      )
      // 3. Optimistically update the cache for list queries
      queryClient.setQueriesData<PaginatedAlerts>(
        { queryKey: alertKeys.all },
        (old) => {
          if (!old) return old
          return {
            ...old,
            items: old.items.map((a) =>
              a.alert_id === id ? { ...a, triage_status: status } : a
            ),
          }
        }
      )
      // 4. Optimistically update the cache for detail query
      queryClient.setQueryData<Alert>(alertKeys.detail(id), (old) => {
        if (!old) return old
        return { ...old, triage_status: status }
      })
      return { previousLists, previousDetail }
    },
    onError: (_err, variables, context) => {
      // Rollback on failure - restore all list queries using original keys
      if (context?.previousLists) {
        context.previousLists.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(
          alertKeys.detail(variables.id),
          context.previousDetail
        )
      }
    },
    onSettled: () => {
      // Always invalidate to ensure eventual consistency
      queryClient.invalidateQueries({ queryKey: alertKeys.all })
    },
  })
}

export function useActionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, action }: { id: string; action: AlertAction }): Promise<Alert> => {
      const response = await fetch(`/api/alerts/${id}/action`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_taken: action }),
      })
      if (!response.ok) {
        if (response.status === 401) {
          // Redirect user to sign-in page when unauthenticated
          redirectToSignIn({ retryArgs: { id, action } })
        }
        throw new Error(`PATCH failed: ${response.status}`)
      }
      return response.json()
    },
    onMutate: async ({ id, action }) => {
      await queryClient.cancelQueries({ queryKey: alertKeys.all })
      const previousLists = new Map<ReadonlyArray<string>, PaginatedAlerts | undefined>()
      queryClient.getQueriesData<PaginatedAlerts>({ queryKey: alertKeys.all })
        .forEach(([queryKey, data]) => {
          if (queryKey[1] === 'list') {
            previousLists.set(queryKey as ReadonlyArray<string>, data)
          }
        })
      const previousDetail = queryClient.getQueryData<Alert>(alertKeys.detail(id))

      queryClient.setQueriesData<PaginatedAlerts>({ queryKey: alertKeys.all }, (old) => {
        if (!old) return old
        return {
          ...old,
          items: old.items.map((a) => (a.alert_id === id ? { ...a, action_taken: action } : a)),
        }
      })

      queryClient.setQueryData<Alert>(alertKeys.detail(id), (old) => {
        if (!old) return old
        return { ...old, action_taken: action }
      })

      return { previousLists, previousDetail }
    },
    onError: (_err, variables, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach((data, queryKey) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(alertKeys.detail(variables.id), context.previousDetail)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.all })
    },
  })
}
