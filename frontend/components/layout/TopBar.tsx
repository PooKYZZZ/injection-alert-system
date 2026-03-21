'use client'

import { Suspense, useCallback, useEffect, useRef } from 'react'
import { usePathname, useSearchParams, useRouter } from 'next/navigation'
import type { SeverityFilter } from '@/lib/searchParams'

const SEVERITY_OPTIONS: { value: SeverityFilter; label: string }[] = [
  { value: 'ALL', label: 'ALL' },
  { value: 'HIGH', label: 'HIGH' },
  { value: 'MEDIUM', label: 'MEDIUM' },
  { value: 'LOW', label: 'LOW' },
]

const DEFAULT_SEARCH_PLACEHOLDER = 'Search path, attack type...'

function pillClasses(severity: SeverityFilter, isActive: boolean): string {
  const base =
    'inline-flex min-h-[26px] cursor-pointer items-center justify-center rounded-[12px] border px-[10px] text-[11px] font-medium transition-all duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel'

  if (severity === 'ALL') {
    return isActive
      ? `${base} border-accent-blue bg-accent-blue-bg text-accent-blue`
      : `${base} border-border-light bg-transparent text-text-muted`
  }

  if (severity === 'HIGH') {
    return isActive
      ? `${base} border-severity-high-border bg-severity-high-bg text-severity-high-text`
      : `${base} border-border-light bg-transparent text-severity-high-text`
  }

  if (severity === 'MEDIUM') {
    return isActive
      ? `${base} border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text`
      : `${base} border-border-light bg-transparent text-accent-yellow`
  }

  return `${base} border-border-light bg-transparent text-text-muted`
}

interface TopBarProps {
  title: string
  showSeverityControls?: boolean
  showSearch?: boolean
  showLiveStatus?: boolean
  searchPlaceholder?: string
}

function TopBarContent({
  title,
  showSeverityControls = true,
  showSearch = true,
  showLiveStatus = false,
  searchPlaceholder = DEFAULT_SEARCH_PLACEHOLDER,
}: TopBarProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const rawSeverity = searchParams?.get('severity')
  const currentSeverity: SeverityFilter =
    rawSeverity === 'HIGH' || rawSeverity === 'MEDIUM' || rawSeverity === 'LOW'
      ? rawSeverity
      : 'ALL'

  const createQueryString = useCallback(
    (name: string, value: string | null) => {
      const params = new URLSearchParams(searchParams?.toString() ?? '')
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

  const setSeverity = (severity: SeverityFilter) => {
    router.push(`${pathname}?${createQueryString('severity', severity)}`, { scroll: false })
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
    <header className="z-10 flex h-16 flex-shrink-0 items-center justify-between border-b border-border-light bg-bg-panel px-6 shadow-subtle">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold tracking-tight text-text-primary">{title}</h2>

          {showLiveStatus ? (
            <>
              <div className="h-4 w-px bg-border-light" />
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-medium text-emerald-400">Live</span>
              </div>
              <span className="text-[10px] text-[var(--color-text-secondary)]">Last updated: just now</span>
            </>
          ) : null}
        </div>

        {showSeverityControls ? (
          <>
            <div className="h-4 w-px bg-border-light" />
            <div className="flex items-center gap-1.5">
              {SEVERITY_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setSeverity(value)}
                  className={pillClasses(value, currentSeverity === value)}
                  aria-pressed={currentSeverity === value}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        ) : null}
      </div>

      {showSearch ? (
        <div className="flex items-center gap-6">
          <div className="relative">
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
              className="w-64 rounded-md border border-border-light bg-bg-elevated py-1.5 pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel"
            />
          </div>
        </div>
      ) : (
        <div className="w-64" aria-hidden="true" />
      )}
    </header>
  )
}

export function TopBar(props: TopBarProps) {
  return (
    <Suspense fallback={<header className="h-16 flex-shrink-0 border-b border-border-light bg-bg-panel" />}>
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
        showSeverityControls={false}
        showSearch={true}
        showLiveStatus={true}
        searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER}
      />
    )
  }

  if (pathname === '/alerts') {
    return <TopBar title="Alerts" searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER} />
  }

  if (pathname === '/ml-health') {
    return <TopBar title="ML Health" showSeverityControls={false} showSearch={false} />
  }

  const fallbackTitle =
    pathname
      .split('/')
      .filter(Boolean)
      .at(-1)
      ?.split('-')
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(' ') ?? 'Dashboard'

  return <TopBar title={fallbackTitle} showSeverityControls={false} showSearch={false} />
}


