'use client'

import { NAV_ITEMS } from '@/lib/constants'
import { SidebarNavItem } from './SidebarNavItem'
import { AlertsNavItem } from './AlertsNavItem'
import { MLHealthWidget } from './MLHealthWidget'
import { signOut } from 'next-auth/react'

export function Sidebar() {
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
        {NAV_ITEMS.map((item) =>
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
      </nav>

      {/* Bottom Panel */}
      <div className="bg-surface-light border-t border-border-light">

        {/* ML Health Widget */}
        <MLHealthWidget />

        {/* User Profile Row */}
        <div className="px-4 py-3 bg-surface-light border-t border-border-light flex items-center gap-3">

          <div className="h-8 w-8 rounded bg-blue-700 flex items-center justify-center">
            <span className="text-xs font-bold text-white">13</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-white truncate">
              Team 13
            </div>
            <div className="text-[10px] text-text-muted truncate">
              SOC Analyst
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
