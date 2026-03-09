'use client'

import { useEffect, useState } from 'react'
import { SidebarNavItem } from './SidebarNavItem'

interface AlertsNavItemProps {
  href: string
  icon: string
  label: string
}

export function AlertsNavItem({ href, icon, label }: AlertsNavItemProps) {
  const [count, setCount] = useState<number | undefined>(undefined)

  useEffect(() => {
    let mounted = true
    const fetchCount = async () => {
      try {
        const res = await fetch('/api/alerts')
        if (!res.ok) return
        const data = await res.json()
        if (mounted && typeof data?.total === 'number') setCount(data.total)
      } catch {
        // ignore
      }
    }
    void fetchCount()
    return () => {
      mounted = false
    }
  }, [])

  return <SidebarNavItem href={href} icon={icon} label={label} badge={count} />
}
