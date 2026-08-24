'use client'

import { useState, useCallback, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import type { Alert, LabelReview } from '@/features/alerts/types'
import { AlertsTable } from '@/components/alerts/AlertsTable'
import { BulkActionBar } from '@/components/alerts/BulkActionBar'
import { AlertDrawer } from '@/components/alerts/AlertDrawer'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'
import { useAlert } from '@/features/alerts/queries'
import { parseAlertDeepLink, removeAlertDeepLink } from '@/features/alerts/deepLink'
import { getCurrentSearchParams } from '@/lib/searchParams'

export function AlertsPageClient({ role }: { role?: unknown }) {
  const canTriage = roleHasPermission(role, PERMISSIONS.ALERTS_TRIAGE)
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const deepLink = useMemo(
    () => parseAlertDeepLink(new URLSearchParams(searchParams.toString())),
    [searchParams]
  )
  const deepLinkId = deepLink.kind === 'valid' ? deepLink.id : null
  const { data: deepLinkedAlert, isError: deepLinkFetchError } = useAlert(deepLinkId)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [manualSelectedAlert, setManualSelectedAlert] = useState<Alert | null>(null)
  const [dismissedDeepLinkId, setDismissedDeepLinkId] = useState<string | null>(null)
  const selectedAlert =
    manualSelectedAlert ??
    (deepLink.kind === 'valid' && dismissedDeepLinkId !== deepLink.id
      ? deepLinkedAlert ?? null
      : null)

  const handleTriageUpdated = useCallback((updatedAlert: Alert) => {
    setManualSelectedAlert(updatedAlert)
  }, [])

  const handleActionUpdated = useCallback((updatedAlert: Alert) => {
    setManualSelectedAlert(updatedAlert)
  }, [])

  const handleReviewUpdated = useCallback((review: LabelReview) => {
    setManualSelectedAlert((current) => {
      const baseAlert = current ?? selectedAlert
      return baseAlert ? { ...baseAlert, label_review: review } : current
    })
  }, [selectedAlert])

  const handleSelectionChange = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids))
  }, [])

  const handleAlertClick = useCallback((alert: Alert) => {
    setDismissedDeepLinkId(alert.alert_id)
    setManualSelectedAlert(alert)
    if (deepLink.kind === 'valid') {
      router.replace(removeAlertDeepLink(`${pathname}?${getCurrentSearchParams(searchParams).toString()}`), { scroll: false })
    }
  }, [deepLink.kind, pathname, router, searchParams])

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const handleDrawerClose = useCallback(() => {
    if (deepLinkId) setDismissedDeepLinkId(deepLinkId)
    setManualSelectedAlert(null)
    if (deepLinkId) {
      router.replace(removeAlertDeepLink(`${pathname}?${getCurrentSearchParams(searchParams).toString()}`), { scroll: false })
    }
  }, [deepLinkId, pathname, router, searchParams])

  const deepLinkMessage =
    deepLink.kind === 'invalid'
      ? 'The requested alert link is invalid.'
      : deepLink.kind === 'valid' && deepLinkFetchError && !selectedAlert
        ? 'The requested alert is unavailable.'
        : null

  return (
    <div className="flex flex-col gap-3">
      {deepLinkMessage && (
        <p role="status" className="rounded border border-surface-border bg-surface-inset p-3 text-sm text-[var(--color-text-secondary)]">
          {deepLinkMessage}
        </p>
      )}
      {canTriage && (
        <BulkActionBar
          selectedIds={selectedIds}
          onClearSelection={handleClearSelection}
        />
      )}
      <AlertsTable
        role={role}
        selectedIds={[...selectedIds]}
        onSelectionChange={handleSelectionChange}
        onAlertClick={handleAlertClick}
        activeAlertId={selectedAlert?.alert_id}
      />
      <AlertDrawer
        role={role}
        alert={selectedAlert}
        onClose={handleDrawerClose}
        onTriageUpdated={handleTriageUpdated}
        onActionUpdated={handleActionUpdated}
        onReviewUpdated={handleReviewUpdated}
      />
    </div>
  )
}
