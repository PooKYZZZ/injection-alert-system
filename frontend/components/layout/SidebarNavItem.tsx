'use client'

import { AnimatePresence, motion } from 'motion/react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface SidebarNavItemProps {
  href: string
  icon: string
  label: string
  badge?: number
}

export function SidebarIcon({ icon }: { icon: string }) {
  switch (icon) {
    case 'dashboard':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      )
    case 'notifications':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      )
    case 'monitor_heart':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8" />
          <path d="M12 17v4" />
          <path d="M7 11l2-3 2 4 2-2 2 1" />
        </svg>
      )
    case 'traffic':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="8" y="2" width="8" height="20" rx="3" />
          <circle cx="12" cy="7" r="1.5" fill="currentColor" stroke="none" />
          <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
          <circle cx="12" cy="17" r="1.5" fill="currentColor" stroke="none" />
        </svg>
      )
    case 'shield_lock':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <rect x="9" y="11" width="6" height="5" rx="1" />
          <path d="M12 11V9a2 2 0 0 0-2-2" />
        </svg>
      )
    case 'history_edu':
      return (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="8" y1="13" x2="16" y2="13" />
          <line x1="8" y1="17" x2="13" y2="17" />
        </svg>
      )
    default:
      return null
  }
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
          ? 'group flex h-[40px] items-center gap-3 border-l-[3px] border-accent-action bg-surface-card px-6 text-text-primary'
          : 'group flex h-[40px] items-center gap-3 border-l-[3px] border-transparent px-6 text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary'
      }
      >
        <SidebarIcon icon={icon} />
        <span className="text-sm font-medium flex-1">{label}</span>
        {badge !== undefined && (
          <AnimatePresence mode="wait">
            <motion.span
              key={badge}
              initial={{ scale: 1.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              className="rounded-full bg-severity-high-accent px-1.5 py-0.5 text-[10px] font-bold text-white"
            >
              {badge}
            </motion.span>
          </AnimatePresence>
        )}
    </Link>
  )
}


