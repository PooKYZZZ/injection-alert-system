'use client'

import { create } from 'zustand'

interface DashboardStore {
  selectedAlertIds: Set<string>
  activeIncidentId: string | null
  toggleAlertSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  setActiveIncident: (id: string | null) => void
}

export const useDashboardStore = create<DashboardStore>()((set) => ({
  selectedAlertIds: new Set<string>(),
  activeIncidentId: null,
  toggleAlertSelection: (id: string) =>
    set((state) => ({
      selectedAlertIds: state.selectedAlertIds.has(id)
        ? new Set([...state.selectedAlertIds].filter((x) => x !== id))
        : new Set([...state.selectedAlertIds, id]),
    })),
  selectAll: (ids: string[]) => set({ selectedAlertIds: new Set(ids) }),
  clearSelection: () => set({ selectedAlertIds: new Set() }),
  setActiveIncident: (id: string | null) => set({ activeIncidentId: id }),
}))
