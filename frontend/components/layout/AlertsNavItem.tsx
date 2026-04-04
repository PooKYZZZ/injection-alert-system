'use client'

import { useAlertsFromFilters } from '@/features/alerts/queries'
import { DEFAULT_ALERT_FILTERS } from '@/lib/searchParams'
import { SidebarNavItem } from './SidebarNavItem'

interface AlertsNavItemProps {
  href: string
  icon: string
  label: string
}

export function AlertsNavItem({ href, icon, label }: AlertsNavItemProps) {
  const { data } = useAlertsFromFilters(DEFAULT_ALERT_FILTERS)

  return (
    <SidebarNavItem
      href={href}
      icon={icon}
      label={label}
      badge={typeof data?.total === 'number' ? data.total : undefined}
    />
  )
}
