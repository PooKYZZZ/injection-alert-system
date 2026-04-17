'use client'

import { useState, useCallback } from 'react'
import type { Alert } from '@/features/alerts/types'
import { AlertsTable } from '@/components/alerts/AlertsTable'
import { BulkActionBar } from '@/components/alerts/BulkActionBar'
import { AlertDrawer } from '@/components/alerts/AlertDrawer'

export function AlertsPageClient() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)

  const handleSelectionChange = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids))
  }, [])

  const handleAlertClick = useCallback((alert: Alert) => {
    setSelectedAlert(alert)
  }, [])

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const handleDrawerClose = useCallback(() => {
    setSelectedAlert(null)
  }, [])

  return (
    <div className="flex flex-col gap-3">
      <BulkActionBar
        selectedIds={selectedIds}
        onClearSelection={handleClearSelection}
      />
      <AlertsTable
        selectedIds={[...selectedIds]}
        onSelectionChange={handleSelectionChange}
        onAlertClick={handleAlertClick}
        activeAlertId={selectedAlert?.alert_id}
      />
      <AlertDrawer
        alert={selectedAlert}
        onClose={handleDrawerClose}
      />
    </div>
  )
}
