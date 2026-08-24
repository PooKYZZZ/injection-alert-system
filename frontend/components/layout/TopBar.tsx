'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useAlertsFromFilters } from '@/features/alerts/queries'
import { usePathname, useSearchParams, useRouter } from 'next/navigation'
import type { ConfidenceTierFilter } from '@/lib/searchParams'
import { useTheme } from '@/app/providers'
import { cn } from '@/lib/utils'
import { getCurrentSearchParams } from '@/lib/searchParams'

const CONFIDENCE_TIER_OPTIONS: { value: ConfidenceTierFilter; label: string }[] = [
  { value: 'ALL', label: 'ALL' },
  { value: 'HIGH', label: 'HIGH' },
  { value: 'CRITICAL', label: 'CRITICAL' },
  { value: 'MEDIUM', label: 'MEDIUM' },
  { value: 'LOW', label: 'LOW' },
]

const DEFAULT_SEARCH_PLACEHOLDER = 'Search path, attack type...'

function pillClasses(confidenceTier: ConfidenceTierFilter, isActive: boolean): string {
  const base =
    'inline-flex min-h-[26px] cursor-pointer items-center justify-center rounded-[12px] border px-[10px] text-[11px] font-medium transition-all duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel'

  if (confidenceTier === 'ALL') {
    return isActive
      ? `${base} border-accent-action bg-surface-inset text-accent-action`
      : `${base} border-border-light bg-transparent text-text-muted`
  }

  if (confidenceTier === 'HIGH') {
    return isActive
      ? `${base} border-severity-high-border bg-severity-high-bg text-severity-high-text`
      : `${base} border-border-light bg-transparent text-severity-high-text`
  }

  if (confidenceTier === 'CRITICAL') {
    return isActive
      ? `${base} border-severity-high-border bg-severity-high-bg text-severity-high-text`
      : `${base} border-border-light bg-transparent text-severity-high-text`
  }

  if (confidenceTier === 'MEDIUM') {
    return isActive
      ? `${base} border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text`
      : `${base} border-border-light bg-transparent text-text-muted`
  }

  return `${base} border-border-light bg-transparent text-text-muted`
}

interface TopBarProps {
  title: string
  showConfidenceTierControls?: boolean
  showSearch?: boolean
  showLiveStatus?: boolean
  searchPlaceholder?: string
  showNewIndicator?: boolean
}

function TopBarContent({
  title,
  showConfidenceTierControls = true,
  showSearch = true,
  showLiveStatus = false,
  searchPlaceholder = DEFAULT_SEARCH_PLACEHOLDER,
  showNewIndicator = false,
}: TopBarProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const rawConfidenceTier = searchParams?.get('confidence_tier') ?? searchParams?.get('severity')
  const currentConfidenceTier: ConfidenceTierFilter =
    rawConfidenceTier === 'HIGH' || rawConfidenceTier === 'CRITICAL' || rawConfidenceTier === 'MEDIUM' || rawConfidenceTier === 'LOW'
      ? rawConfidenceTier
      : 'ALL'

  const createQueryString = useCallback(
    (name: string, value: string | null) => {
      const params = getCurrentSearchParams(searchParams ?? undefined)
      if (value === null || value === '') {
        params.delete(name)
      } else {
        params.set(name, value)
      }
      return params.toString()
    },
    [searchParams]
  )

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const setConfidenceTier = (confidenceTier: ConfidenceTierFilter) => {
    const params = getCurrentSearchParams(searchParams ?? undefined)
    if (confidenceTier === 'ALL') {
      params.delete('confidence_tier')
    } else {
      params.set('confidence_tier', confidenceTier)
    }
    params.delete('severity')
    const query = params.toString()
    router.push(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }

  const handleSearch = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(() => {
      router.push(`${pathname}?${createQueryString('search', value || null)}`, {
        scroll: false,
      })
    }, 300)
  }

  return (
    <header
      className={cn(
        'z-10 flex min-w-0 flex-shrink-0 items-center justify-between border-b border-border-light bg-surface-panel shadow-subtle',
        showNewIndicator
          ? 'min-h-16 flex-wrap gap-x-3 gap-y-2 py-2 pl-16 pr-3 sm:h-16 sm:flex-nowrap sm:gap-4 sm:py-0 sm:pr-4 lg:gap-6 lg:px-6'
          : 'h-16 gap-3 pl-16 pr-3 sm:gap-4 sm:pr-4 lg:gap-6 lg:px-6'
      )}
    >
      <div
        className={cn(
          'flex min-w-0 items-center gap-4',
          showNewIndicator
            ? 'w-full flex-wrap gap-x-4 gap-y-1 overflow-visible sm:w-auto sm:flex-1 sm:flex-nowrap'
            : 'flex-1 overflow-hidden'
        )}
      >
        <div className="flex min-w-0 items-center gap-3">
          <h2 className="min-w-0 truncate text-lg font-semibold tracking-tight text-text-primary">{title}</h2>

          {showLiveStatus ? (
            <>
              <div className="hidden h-4 w-px bg-border-light sm:block" />
              <div className="hidden items-center gap-1.5 rounded-full border border-severity-safe-border bg-severity-safe-bg px-2 py-0.5 sm:flex">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-severity-safe-text opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-severity-safe-accent" />
                </span>
                <span className="text-[10px] font-medium text-severity-safe-text">Snapshot</span>
              </div>
              <span className="hidden text-[10px] text-[var(--color-text-secondary)] md:inline">Reported in latest refresh</span>
            </>
          ) : null}
        </div>

        {showConfidenceTierControls ? (
          <>
            <div className="h-4 w-px bg-border-light" />
            <div className="flex items-center gap-1.5">
              {CONFIDENCE_TIER_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setConfidenceTier(value)}
                  className={pillClasses(value, currentConfidenceTier === value)}
                  aria-pressed={currentConfidenceTier === value}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        ) : showNewIndicator ? (
          <div className="flex shrink-0 items-center gap-5">
            <div className="h-4 w-px bg-border-light" />
            <NewAlertIndicator />
          </div>
        ) : null}
      </div>

      {showSearch ? (
        <div
          className={cn(
            'flex min-w-0 items-center justify-end gap-2 sm:gap-4 lg:gap-6',
            showNewIndicator ? 'w-full sm:w-auto sm:flex-1' : 'flex-1'
          )}
        >
          <div className="relative min-w-0 flex-1 lg:flex-none">
            <span className="absolute left-3 top-1/2 -translate-y-1/2">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: 'var(--color-text-muted)', flexShrink: 0 }}
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              type="text"
              defaultValue={searchParams?.get('search') ?? ''}
              onChange={(event) => handleSearch(event.target.value)}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className="w-full min-w-0 max-w-64 rounded-md border border-border-light bg-surface-inset py-1.5 pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel"
            />
          </div>
          <ThemeToggleButton />
        </div>
      ) : (
        <div className="hidden w-64 lg:block" aria-hidden="true" />
      )}
    </header>
  )
}

function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme()
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setIsMounted(true)
    })

    return () => window.cancelAnimationFrame(frame)
  }, [])

  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const buttonLabel = isMounted ? `${nextTheme === 'light' ? 'Light' : 'Dark'} theme` : 'Theme'
  const ariaLabel = isMounted ? `Switch to ${nextTheme} theme` : 'Toggle theme'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={ariaLabel}
      title={ariaLabel}
      className="inline-flex h-9 shrink-0 items-center rounded-md border border-border-light bg-surface-inset px-2 text-xs font-medium text-text-primary transition-colors hover:bg-surface-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel sm:px-3"
    >
      <span aria-hidden="true" className="text-sm leading-none sm:hidden">◐</span>
      <span className="hidden sm:inline">{buttonLabel}</span>
    </button>
  )
}

function NewAlertIndicator() {
  const { data: newAlerts } = useAlertsFromFilters({
    page: 1,
    pageSize: 1,
    triage_status: 'new',
    sort_by: 'timestamp',
    sort_dir: 'desc',
  })
  const { data: inReviewAlerts } = useAlertsFromFilters({
    page: 1,
    pageSize: 1,
    triage_status: 'in_review',
    sort_by: 'timestamp',
    sort_dir: 'desc',
  })

  const newCount = newAlerts?.total ?? 0
  const inReviewCount = inReviewAlerts?.total ?? 0

  return (
    <div className="flex shrink-0 items-center gap-5">
      <div className="flex shrink-0 items-center gap-2 whitespace-nowrap">
        <span className="text-sm font-semibold text-[var(--color-text-secondary)]">NEW:</span>
        <span className="text-sm font-semibold text-accent-action">{newCount}</span>
      </div>
      <div className="flex shrink-0 items-center gap-2 whitespace-nowrap">
        <span className="text-sm font-semibold text-[var(--color-text-secondary)]">IN REVIEW:</span>
        <span className="text-sm font-semibold text-severity-blocked-text">{inReviewCount}</span>
      </div>
    </div>
  )
}

export function TopBar(props: TopBarProps) {
  return (
    <Suspense fallback={<header className="h-16 flex-shrink-0 border-b border-border-light bg-surface-panel" />}>
      <TopBarContent {...props} />
    </Suspense>
  )
}

export function DashboardTopBar() {
  const pathname = usePathname()

  if (pathname === '/dashboard') {
    return (
        <TopBar
          title="Dashboard"
          showConfidenceTierControls={false}
          showSearch={true}
          searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER}
        />
    )
  }

  if (pathname === '/alerts') {
    return <TopBar title="Alerts" searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER} showConfidenceTierControls={false} showNewIndicator={true} />
  }

  if (pathname === '/ml-health') {
    return <TopBar title="ML Health" showConfidenceTierControls={false} showSearch={false} />
  }

  if (pathname === '/ml-model') {
    return <TopBar title="Model Operations" showConfidenceTierControls={false} showSearch={false} />
  }

  const fallbackTitle =
    pathname
      .split('/')
      .filter(Boolean)
      .at(-1)
      ?.split('-')
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(' ') ?? 'Dashboard'

  return <TopBar title={fallbackTitle} showConfidenceTierControls={false} showSearch={false} />
}
