'use client'

import { useAlertsFromFilters } from '@/features/alerts/queries'
import { DEFAULT_ALERT_FILTERS } from '@/lib/searchParams'
import { SidebarNavItem } from './SidebarNavItem'

interface AlertsNavItemProps {
  href: string
  icon: string
  label: string
  collapsed?: boolean
  onNavigate?: () => void
}

export function AlertsNavItem({ href, icon, label, collapsed = false, onNavigate }: AlertsNavItemProps) {
  const { data } = useAlertsFromFilters(DEFAULT_ALERT_FILTERS)

  return (
    <SidebarNavItem
      href={href}
      icon={icon}
      label={label}
      badge={typeof data?.total === 'number' ? data.total : undefined}
      badgeLabel="actionable detections"
      collapsed={collapsed}
      onNavigate={onNavigate}
    />
  )
}
