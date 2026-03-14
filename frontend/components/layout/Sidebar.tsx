'use client'

import { NAV_ITEMS } from '@/lib/constants'
import { SidebarNavItem } from './SidebarNavItem'
import { AlertsNavItem } from './AlertsNavItem'
import { MLHealthWidget } from './MLHealthWidget'
import { signOut } from 'next-auth/react'

export function Sidebar() {
  return (
    <aside className="w-[260px] bg-[#111827] flex-shrink-0 flex flex-col h-full border-r border-[#1f2937]">

      {/* Header */}
      <div className="h-20 flex flex-col justify-center px-6 border-b border-[#1f2937] bg-[#1A1A1A]">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-red-500 text-[24px]">
            shield
          </span>

          <h1 className="text-white text-base font-bold leading-tight tracking-wide">
            WAF-ML SOC
          </h1>
        </div>

        <p className="text-gray-400 text-[11px] font-medium tracking-wide pl-8">
          Enterprise Security Console
        </p>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5 overflow-y-auto bg-[#161f32]">
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
      <div className="bg-[#1A1A1A] border-t border-[#1f2937]">

        {/* ML Health Widget */}
        <MLHealthWidget />

        {/* User Profile Row */}
        <div className="px-4 py-3 bg-[#1A1A1A] border-t border-[#1f2937] flex items-center gap-3">

          <div className="h-8 w-8 rounded bg-blue-700 flex items-center justify-center">
            <span className="text-xs font-bold text-white">13</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-white truncate">
              Team 13
            </div>
            <div className="text-[10px] text-gray-400 truncate">
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