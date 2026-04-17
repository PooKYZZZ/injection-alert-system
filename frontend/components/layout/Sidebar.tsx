'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { NAV_ITEMS } from '@/lib/constants'
import Image from 'next/image'
import { useState } from 'react'
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

export function Sidebar({ displayName }: SidebarProps) {
  const [isLogoutDialogOpen, setIsLogoutDialogOpen] = useState(false)
  const resolvedName = displayName?.trim() || 'SOC Analyst'
  const initials = getInitials(resolvedName)
  const handleLogout = () => signOut({ callbackUrl: '/login' })

  return (
    <Dialog.Root open={isLogoutDialogOpen} onOpenChange={setIsLogoutDialogOpen}>
      <>
        <aside className="flex h-full w-[260px] flex-shrink-0 flex-col border-r border-border-light bg-surface-shell">
          <div className="flex h-20 flex-col justify-center border-b border-border-light bg-surface-panel px-6">
            <div className="mb-1 flex items-center gap-2">
              <Image src="/logo.png" alt="logo" width={32} height={32} className="h-8 w-8" />
              <h1 className="font-orbitron text-base font-bold leading-tight tracking-wide text-text-primary">
                CyberTrace
              </h1>
            </div>
            <p className="pl-9 text-[12px] font-medium tracking-wide text-text-secondary">
              WAF-ML Security Dashboard
            </p>
          </div>

          <nav className="flex flex-1 flex-col overflow-y-auto bg-surface-panel py-4">
            {NAV_ITEMS.map((item) =>
              item.href === '/alerts' ? (
                <AlertsNavItem key={item.href} href={item.href} icon={item.icon} label={item.label} />
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

          <div className="bg-surface-panel">
            <div className="border-t border-border-light">
              <MLHealthWidget />
            </div>

            <div className="flex items-center gap-3 border-t border-border-light bg-surface-panel px-4 py-3">
              <div className="flex h-8 w-8 items-center justify-center rounded border border-border-light bg-surface-card">
                <span className="text-xs font-bold text-accent-action">{initials}</span>
              </div>

              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-text-primary">{resolvedName}</div>
              </div>

              <button
                onClick={() => setIsLogoutDialogOpen(true)}
                aria-label="Log out"
                type="button"
                title="Log out"
                style={{
                  marginLeft: 'auto',
                  minWidth: '24px',
                  minHeight: '24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  borderRadius: '4px',
                  padding: '4px',
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          </div>
        </aside>

        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,360px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border-light bg-surface-card p-5 shadow-2xl focus:outline-none">
            <Dialog.Title className="text-base font-semibold text-text-primary">
              Confirm Log Out
            </Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-text-secondary">
              Are you sure you want to log out of CyberTrace?
            </Dialog.Description>
            <div className="mt-5 flex justify-end gap-2">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-md border border-border-light px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-inset"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-md border border-severity-high-border bg-severity-high-bg px-3 py-1.5 text-sm font-medium text-severity-high-text transition-colors hover:bg-severity-high-bg/80"
              >
                Log out
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </>
    </Dialog.Root>
  )
}
