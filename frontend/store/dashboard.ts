import { create } from 'zustand'
import {
  type DashboardFilters,
  DEFAULT_FILTERS,
} from '@/lib/searchParams'

interface DashboardStore {
  filters: DashboardFilters
  setFilters: (patch: Partial<DashboardFilters>) => void
  resetFilters: () => void
}

/**
 * Client-side dashboard filter state managed by Zustand.
 *
 * On initial page load, seed this store from the URL via
 * `normalizeSearchParams` in the RSC layout, then pass the result to a
 * client component that calls `useDashboardStore.setState({ filters })`.
 *
 * TanStack Query key arrays should include `filters` as a dependency so
 * queries automatically refetch when the user changes a filter.
 */
export const useDashboardStore = create<DashboardStore>((set) => ({
  filters: DEFAULT_FILTERS,

  setFilters: (patch) =>
    set((state) => ({
      filters: { ...state.filters, ...patch },
    })),

  resetFilters: () => set({ filters: DEFAULT_FILTERS }),
}))
