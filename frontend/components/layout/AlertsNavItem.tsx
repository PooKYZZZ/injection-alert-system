'use client'

import { useAlerts } from '@/features/alerts/queries'
import { DEFAULT_FILTERS } from '@/lib/searchParams'
import { SidebarNavItem } from './SidebarNavItem'

interface AlertsNavItemProps {
  href: string
  icon: string
  label: string
}

export function AlertsNavItem({ href, icon, label }: AlertsNavItemProps) {
  const { data } = useAlerts(DEFAULT_FILTERS)

  return (
    <SidebarNavItem
      href={href}
      icon={icon}
      label={label}
      badge={typeof data?.total === 'number' ? data.total : undefined}
    />
  )
}
