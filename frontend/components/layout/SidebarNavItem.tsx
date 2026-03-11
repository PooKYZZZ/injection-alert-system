'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface SidebarNavItemProps {
  href: string
  icon: string
  label: string
  badge?: number
}

export function SidebarNavItem({ href, icon, label, badge }: SidebarNavItemProps) {
  const pathname = usePathname()
  const isActive =
    href === '/dashboard' ? pathname === href : pathname.startsWith(href)

  return (
    <Link
      href={href}
      className={
        isActive
          ? 'group flex items-center gap-3 px-6 h-[40px] bg-sidebar-active border-l-[3px] border-primary text-white'
          : 'group flex items-center gap-3 px-6 h-[40px] text-blue-100 hover:bg-[#264b82] hover:text-white border-l-[3px] border-transparent transition-colors'
      }
    >
      <span className="material-symbols-outlined text-[18px]">{icon}</span>
      <span className="text-sm font-medium flex-1">{label}</span>
      {badge !== undefined && (
        <span className="bg-primary text-white text-[10px] font-bold px-1.5 py-0.5 rounded-sm">
          {badge}
        </span>
      )}
    </Link>
  )
}
