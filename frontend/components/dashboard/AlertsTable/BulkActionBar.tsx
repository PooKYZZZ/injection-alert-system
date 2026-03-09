'use client'

import { useShallow } from 'zustand/react/shallow'
import { useDashboardStore } from '@/store/dashboardStore'

interface DashboardStoreState {
  selectedAlertIds: Set<string>
}

export default function BulkActionBar() {
  const selectedIds = useDashboardStore(useShallow((s: DashboardStoreState) => [...s.selectedAlertIds]))
  const count = selectedIds.length

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-blue-50 border border-blue-200 rounded-sm">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px] text-blue-600">check_box</span>
          <span className="text-sm font-medium text-blue-700">
            {count} Selected
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={count === 0}
            onClick={() => console.log('Explain Selected', selectedIds)}
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Explain Selected
          </button>
          <button
            type="button"
            disabled={count === 0}
            onClick={() => console.log('Mark False Positive', selectedIds)}
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Mark False Positive
          </button>
          <button
            type="button"
            disabled={count === 0}
            onClick={() => console.log('Apply Mitigation', selectedIds)}
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Apply Mitigation
          </button>
        </div>
      </div>
      <button
        type="button"
        className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline transition-colors"
      >
        View All Logs
      </button>
    </div>
  )
}
