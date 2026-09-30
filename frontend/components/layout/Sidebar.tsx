'use client'

import * as Dialog from '@radix-ui/react-dialog'
import Image from 'next/image'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { NAV_ITEMS } from '@/lib/constants'
import { PERMISSIONS, roleHasPermission, type UserRole } from '@/lib/auth/roles'
import { signOut } from 'next-auth/react'
import { AlertsNavItem } from './AlertsNavItem'
import { HelpGuideDialog } from './HelpGuideDialog'
import { MLHealthWidget } from './MLHealthWidget'
import { SidebarIcon, SidebarNavItem } from './SidebarNavItem'

interface SidebarProps {
  displayName?: string | null
  secondaryLabel?: string | null
  role?: UserRole
}

const SIDEBAR_PREFERENCE_KEY = 'cybertrace.sidebar-collapsed'
const SIDEBAR_PREFERENCE_EVENT = 'cybertrace-sidebar-preference-change'
let transientSidebarPreference = false

function getSidebarPreferenceSnapshot(): boolean {
  try {
    transientSidebarPreference = window.localStorage.getItem(SIDEBAR_PREFERENCE_KEY) === 'true'
  } catch {
    // Use the in-memory preference when browser storage is unavailable.
  }
  return transientSidebarPreference
}

function subscribeToSidebarPreference(onChange: () => void): () => void {
  window.addEventListener('storage', onChange)
  window.addEventListener(SIDEBAR_PREFERENCE_EVENT, onChange)
  return () => {
    window.removeEventListener('storage', onChange)
    window.removeEventListener(SIDEBAR_PREFERENCE_EVENT, onChange)
  }
}

function saveSidebarPreference(collapsed: boolean): void {
  transientSidebarPreference = collapsed
  try {
    window.localStorage.setItem(SIDEBAR_PREFERENCE_KEY, String(collapsed))
  } catch {
    // The preference still applies for this page view without browser storage.
  }
  window.dispatchEvent(new Event(SIDEBAR_PREFERENCE_EVENT))
}

function getInitials(name: string): string {
  const cleaned = name.trim()
  if (!cleaned) return 'U'

  const segments = cleaned.split(/\s+/).slice(0, 2)
  const initials = segments.map((segment) => segment.charAt(0).toUpperCase()).join('')
  return initials || 'U'
}

function SidebarBrand({
  collapsed,
  onToggle,
}: {
  collapsed: boolean
  onToggle?: () => void
}) {
  return (
    <div className={`flex h-20 flex-col justify-center border-b border-border-light bg-surface-panel ${collapsed ? 'px-1' : 'px-4'}`}>
      <div className={`flex items-center ${collapsed ? 'justify-center gap-1' : 'justify-between gap-2'}`}>
        <div className="flex min-w-0 items-center gap-2">
          <Image src="/logo.png" alt="" width={32} height={32} className="h-8 w-8 shrink-0" />
          <div className={collapsed ? 'sr-only' : 'min-w-0'}>
            <h1 className="font-orbitron text-base font-bold leading-tight tracking-wide text-text-primary">
              CyberTrace
            </h1>
            <p className="mt-0.5 whitespace-nowrap text-[10px] font-medium tracking-wide text-text-secondary">
              WAF-ML Security Dashboard
            </p>
          </div>
        </div>
        {onToggle ? (
          <button
            type="button"
            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-expanded={!collapsed}
            aria-controls="desktop-primary-navigation"
            title={collapsed ? 'Expand navigation' : 'Collapse navigation'}
            onClick={onToggle}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {collapsed ? <path d="m9 18 6-6-6-6" /> : <path d="m15 18-6-6 6-6" />}
              <path d="M4 5v14" />
            </svg>
          </button>
        ) : null}
      </div>
    </div>
  )
}

function SidebarNavigation({
  role,
  onNavigate,
  collapsed = false,
  id,
}: {
  role?: UserRole
  onNavigate?: () => void
  collapsed?: boolean
  id: string
}) {
  return (
    <nav
      id={id}
      aria-label="Dashboard navigation"
      className="flex flex-1 flex-col overflow-y-auto bg-surface-panel py-4"
    >
      {NAV_ITEMS.filter(
        (item) =>
          !item.requiredPermission ||
          roleHasPermission(role, item.requiredPermission)
      ).map((item) =>
        item.href === '/alerts' ? (
          <AlertsNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ) : (
          <SidebarNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            collapsed={collapsed}
            badge={'badge' in item && typeof item.badge === 'number' ? item.badge : undefined}
            onNavigate={onNavigate}
          />
        )
      )}
    </nav>
  )
}

function SidebarHelpEntry({
  collapsed,
  onOpenHelp,
}: {
  collapsed: boolean
  onOpenHelp: (trigger: HTMLButtonElement) => void
}) {
  return (
    <div className={`border-t border-border-light bg-surface-panel py-2 ${collapsed ? 'px-2' : 'px-3'}`}>
      <button
        type="button"
        aria-label="Help & Guide"
        title="Help & Guide"
        onClick={(event) => onOpenHelp(event.currentTarget)}
        className={`group relative flex h-10 w-full items-center rounded-md border border-transparent text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 ${collapsed ? 'justify-center px-0' : 'gap-3 px-3'}`}
      >
        <SidebarIcon icon="help" />
        <span className={collapsed ? 'sr-only' : 'flex-1 text-left text-sm font-medium'}>Help &amp; Guide</span>
        {collapsed ? (
          <span aria-hidden="true" className="pointer-events-none absolute left-full top-1/2 z-30 ml-2 hidden -translate-y-1/2 whitespace-nowrap rounded-md border border-border-light bg-surface-panel px-2 py-1 text-xs text-text-primary shadow-lg group-hover:block group-focus-visible:block">
            Help &amp; Guide
          </span>
        ) : null}
      </button>
    </div>
  )
}

function SidebarUserFooter({
  resolvedName,
  secondaryLabel,
  role,
  initials,
  collapsed,
  idPrefix,
  onLogout,
}: {
  resolvedName: string
  secondaryLabel?: string | null
  role?: UserRole
  initials: string
  collapsed: boolean
  idPrefix: string
  onLogout: () => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const panelId = `${idPrefix}-account-menu`

  useEffect(() => {
    if (!isOpen) return

    panelRef.current?.querySelector<HTMLElement>('[data-account-first-action]')?.focus()
    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [isOpen])

  return (
    <div
      ref={rootRef}
      data-account-menu-open={isOpen ? 'true' : undefined}
      onKeyDownCapture={(event) => {
        if (isOpen && event.key === 'Escape') {
          event.preventDefault()
          event.stopPropagation()
          setIsOpen(false)
          triggerRef.current?.focus()
        }
      }}
      className={`relative flex border-t border-border-light bg-surface-panel py-3 ${collapsed ? 'justify-center px-2' : 'items-center gap-2 px-3'}`}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-label={`Account menu for ${resolvedName}`}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls={panelId}
        title={collapsed ? resolvedName : undefined}
        onClick={() => setIsOpen((current) => !current)}
        className={`flex min-w-0 items-center rounded-md text-left transition-colors hover:bg-surface-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 ${collapsed ? 'h-10 w-10 justify-center' : 'flex-1 gap-2 px-1 py-1'}`}
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-border-light bg-surface-card text-xs font-bold text-accent-action">
          {initials}
        </span>
        <span className={collapsed ? 'sr-only' : 'min-w-0 flex-1'}>
          <span className="block truncate text-xs font-medium text-text-primary">{resolvedName}</span>
          <span className="block text-[10px] text-text-secondary">Account</span>
        </span>
      </button>

      {isOpen ? (
        <div
          id={panelId}
          ref={panelRef}
          role="dialog"
          aria-modal="false"
          aria-labelledby={`${panelId}-title`}
          className={`absolute bottom-full z-[55] mb-2 rounded-lg border border-border-light bg-surface-panel p-3 shadow-xl ${collapsed ? 'left-2 w-[min(280px,calc(100vw-1rem))]' : 'left-2 right-2'}`}
        >
          <h2 id={`${panelId}-title`} className="text-sm font-semibold text-text-primary">Account</h2>
          <p className="mt-2 truncate text-sm font-medium text-text-primary">{resolvedName}</p>
          {secondaryLabel?.trim() ? (
            <p className="mt-0.5 break-all text-xs text-text-secondary">{secondaryLabel.trim()}</p>
          ) : null}
          {role ? <p className="mt-1 text-xs text-text-secondary">Role: {role}</p> : null}
          <button
            type="button"
            data-account-first-action
            onClick={() => {
              setIsOpen(false)
              onLogout()
            }}
            className="mt-4 w-full rounded-md border border-severity-high-border bg-severity-high-bg px-3 py-2 text-left text-sm font-medium text-severity-high-text transition-colors hover:bg-severity-high-bg/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-severity-high-border"
          >
            Log out
          </button>
        </div>
      ) : null}
    </div>
  )
}

function MLHealthFooter({ role }: { role?: UserRole }) {
  return (
    <div className="border-t border-border-light">
      {roleHasPermission(role, PERMISSIONS.ML_HEALTH_READ) ? <MLHealthWidget /> : null}
    </div>
  )
}

export function Sidebar({ displayName, secondaryLabel, role }: SidebarProps) {
  const [isLogoutDialogOpen, setIsLogoutDialogOpen] = useState(false)
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const isCollapsed = useSyncExternalStore(
    subscribeToSidebarPreference,
    getSidebarPreferenceSnapshot,
    () => false
  )
  const helpReturnFocusRef = useRef<HTMLButtonElement>(null)
  const mobileNavigationTriggerRef = useRef<HTMLButtonElement>(null)
  const resolvedName = displayName?.trim() || 'SOC Analyst'
  const initials = getInitials(resolvedName)
  const handleLogout = () => signOut({ callbackUrl: '/login' })

  const openHelp = (trigger: HTMLButtonElement) => {
    helpReturnFocusRef.current = trigger
    setIsHelpOpen(true)
  }

  return (
    <Dialog.Root open={isLogoutDialogOpen} onOpenChange={setIsLogoutDialogOpen}>
      <>
        <aside
          aria-label="Primary sidebar"
          className={`hidden h-full flex-shrink-0 flex-col border-r border-border-light bg-surface-shell transition-[width] duration-200 lg:flex ${isCollapsed ? 'w-[72px]' : 'w-[260px]'}`}
        >
          <SidebarBrand collapsed={isCollapsed} onToggle={() => saveSidebarPreference(!isCollapsed)} />
          <SidebarNavigation role={role} collapsed={isCollapsed} id="desktop-primary-navigation" />
          <SidebarHelpEntry collapsed={isCollapsed} onOpenHelp={openHelp} />
          <div className="bg-surface-panel">
            {!isCollapsed ? <MLHealthFooter role={role} /> : null}
            <SidebarUserFooter
              resolvedName={resolvedName}
              secondaryLabel={secondaryLabel}
              role={role}
              initials={initials}
              collapsed={isCollapsed}
              idPrefix="desktop"
              onLogout={() => setIsLogoutDialogOpen(true)}
            />
          </div>
        </aside>

        <Dialog.Root open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
          <Dialog.Trigger asChild>
            <button
              ref={mobileNavigationTriggerRef}
              type="button"
              aria-label="Open navigation"
              title="Open navigation"
              className="fixed left-3 top-3 z-30 inline-flex h-10 w-10 items-center justify-center rounded-md border border-border-light bg-surface-panel text-text-primary shadow-subtle transition-colors hover:bg-surface-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel lg:hidden"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </svg>
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 lg:hidden" />
            <Dialog.Content
              onEscapeKeyDown={(event) => {
                if (event.target instanceof Element && event.target.closest('[data-account-menu-open="true"]')) {
                  event.preventDefault()
                }
              }}
              className="fixed inset-y-0 left-0 z-50 flex w-[min(85vw,260px)] flex-col overflow-y-auto border-r border-border-light bg-surface-shell shadow-2xl focus:outline-none lg:hidden"
            >
              <Dialog.Title className="sr-only">Dashboard navigation</Dialog.Title>
              <Dialog.Description className="sr-only">
                Primary navigation for the CyberTrace dashboard.
              </Dialog.Description>
              <div className="flex items-center justify-between bg-surface-panel pr-3">
                <SidebarBrand collapsed={false} />
                <Dialog.Close asChild>
                  <button
                    type="button"
                    aria-label="Close navigation"
                    title="Close navigation"
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border-light text-text-secondary transition-colors hover:bg-surface-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
                  >
                    <span aria-hidden="true" className="text-lg leading-none">×</span>
                  </button>
                </Dialog.Close>
              </div>
              <SidebarNavigation
                role={role}
                id="mobile-primary-navigation"
                onNavigate={() => setIsMobileNavOpen(false)}
              />
              <SidebarHelpEntry
                collapsed={false}
                onOpenHelp={() => {
                  setIsMobileNavOpen(false)
                  helpReturnFocusRef.current = mobileNavigationTriggerRef.current
                  setIsHelpOpen(true)
                }}
              />
              <div className="bg-surface-panel">
                <MLHealthFooter role={role} />
                <SidebarUserFooter
                  resolvedName={resolvedName}
                  secondaryLabel={secondaryLabel}
                  role={role}
                  initials={initials}
                  collapsed={false}
                  idPrefix="mobile"
                  onLogout={() => setIsLogoutDialogOpen(true)}
                />
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>

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

        <HelpGuideDialog
          open={isHelpOpen}
          onOpenChange={setIsHelpOpen}
          returnFocusRef={helpReturnFocusRef}
        />
      </>
    </Dialog.Root>
  )
}
