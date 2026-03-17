'use client'

import { NAV_ITEMS } from '@/lib/constants'
import { SidebarNavItem } from './SidebarNavItem'
import { AlertsNavItem } from './AlertsNavItem'
import { MLHealthWidget } from './MLHealthWidget'
import { signOut } from 'next-auth/react'

interface SidebarProps {
  displayName?: string | null
  secondaryLabel?: string | null
}

function getInitials(name: string): string {
  const cleaned = name.trim()
  if (!cleaned) return 'U'

  const segments = cleaned.split(/\s+/).slice(0, 2)
  const initials = segments.map((segment) => segment.charAt(0).toUpperCase()).join('')
  return initials || 'U'
}

export function Sidebar({ displayName, secondaryLabel }: SidebarProps) {
  const plannedLabels = new Set(['Traffic', 'Mitigation Log', 'Audit Trail'])
  const activeItems = NAV_ITEMS.filter((item) => !plannedLabels.has(item.label))
  const plannedItems = NAV_ITEMS.filter((item) => plannedLabels.has(item.label))
  const resolvedName = displayName?.trim() || 'Authenticated User'
  const resolvedSecondaryLabel = secondaryLabel?.trim() || 'Signed in'
  const initials = getInitials(resolvedName)

  return (
    <aside className="w-[260px] bg-background-main flex-shrink-0 flex flex-col h-full border-r border-border-light">

      {/* Header */}
      <div className="h-20 flex flex-col justify-center px-6 border-b border-border-light bg-surface-light">
        <div className="flex items-center gap-2 mb-1">
          <img
            src="/logo.png"
            alt="logo"
            className="w-8 h-8"
          />

          <h1 className="text-white text-base font-bold leading-tight tracking-wide font-[Orbitron]">
            CyberTrace
          </h1>
        </div>

        <p className="text-text-muted text-[12px] font-medium tracking-wide pl-9">
          WAF-ML Security Dashboard
        </p>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5 overflow-y-auto bg-surface-light">
        {activeItems.map((item) =>
          item.href === '/alerts' ? (
            <AlertsNavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
            />
          ) : (
            <SidebarNavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              badge={'badge' in item && typeof item.badge === 'number' ? item.badge : undefined}
            />
          )
        )}

        {plannedItems.length > 0 && (
          <div className="mt-4 px-4">
            <div className="border-t border-border-light pt-4">
              <p className="px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-text-muted/70">
                Planned
              </p>

              <div className="mt-2 flex flex-col gap-0.5">
                {plannedItems.map((item) => (
                  <div
                    key={item.href}
                    aria-disabled="true"
                    className="flex items-center gap-3 px-4 h-[40px] rounded-sm border-l-[3px] border-transparent text-blue-200/35 cursor-not-allowed select-none"
                  >
                    <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                    <span className="text-sm font-medium flex-1">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Bottom Panel */}
      <div className="bg-surface-light border-t border-border-light">

        {/* ML Health Widget */}
        <MLHealthWidget />

        {/* User Profile Row */}
        <div className="px-4 py-3 bg-surface-light border-t border-border-light flex items-center gap-3">

          <div className="h-8 w-8 rounded bg-blue-700 flex items-center justify-center">
            <span className="text-xs font-bold text-white">{initials}</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-white truncate">
              {resolvedName}
            </div>
            <div className="text-[10px] text-text-muted truncate">
              {resolvedSecondaryLabel}
            </div>
          </div>

          {/* Logout Button */}
          <button
            onClick={() => signOut({ callbackUrl: '/login' })}
            aria-label="Logout"
            type="button"
            className="text-gray-400 hover:text-red-400 transition-colors"
            title="Logout"
          >
            <span className="material-symbols-outlined text-[16px]">
              logout
            </span>
          </button>

        </div>
      </div>

    </aside>
  )
}
