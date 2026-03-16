'use client'

import { useDashboardStore } from 'store/dashboardStore'

interface DashboardStoreState {
  selectedAlertIds: Set<string>
}

export default function BulkActionBar() {
  const count = useDashboardStore((s: DashboardStoreState) => s.selectedAlertIds.size)

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
            disabled
            aria-disabled="true"
            title="Unavailable in the current build"
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white opacity-50 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-50"
          >
            Explain Selected
          </button>
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Unavailable in the current build"
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white opacity-50 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-50"
          >
            Mark False Positive
          </button>
          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Unavailable in the current build"
            className="text-xs font-medium px-3 py-1 rounded border border-blue-300 text-blue-700 bg-white opacity-50 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-50"
          >
            Apply Mitigation
          </button>
        </div>
      </div>
      <span className="text-xs text-blue-700">
        Bulk actions unavailable in the current build.
      </span>
    </div>
  )
}
