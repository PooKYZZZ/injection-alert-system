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

function pillClasses(severity: SeverityFilter, isActive: boolean): string {
  const base =
    'inline-flex min-h-6 min-w-6 items-center justify-center rounded-full border px-2.5 py-1 text-[10px] font-bold transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light'

  if (!isActive) {
    switch (severity) {
      case 'HIGH':
        return `${base} bg-sidebar-active text-red-700 border-sidebar-active hover:bg-red-50 hover:border-red-200`
      case 'MEDIUM':
        return `${base} bg-sidebar-active text-orange-600 border-sidebar-active hover:bg-orange-50 hover:border-orange-200`
      case 'LOW':
        return `${base} bg-sidebar-active text-gray-600 border-sidebar-active hover:bg-gray-50 hover:border-gray-300`
      default:
        return `${base} bg-sidebar-active text-slate-800 border-sidebar-active hover:bg-slate-100 hover:border-slate-300`
    }
  }

  switch (severity) {
    case 'HIGH':
      return `${base} bg-red-50 border-red-200 text-red-700`
    case 'MEDIUM':
      return `${base} bg-orange-50 border-orange-200 text-orange-600`
    case 'LOW':
      return `${base} bg-gray-50 border-gray-300 text-gray-600`
    default:
      return `${base} bg-slate-200 text-slate-800 border-slate-300`
  }
}

interface TopBarProps {
  title: string
  showAlertControls?: boolean
  searchPlaceholder?: string
}

const DEFAULT_SEARCH_PLACEHOLDER = 'Search path, attack type...'

function TopBarContent({
  title,
  showAlertControls = true,
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
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
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
    <header className="h-16 border-b border-border-light bg-surface-light flex items-center justify-between px-6 flex-shrink-0 shadow-subtle z-10">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-bold text-text-main tracking-tight">
          {title}
        </h2>

        {showAlertControls && (
          <>
            <div className="h-4 w-[1px] bg-border-light" />

            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                ML Confidence
              </span>
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
        )}
      </div>

      {showAlertControls ? (
        <div className="flex items-center gap-6">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-[18px]">
              search
            </span>

            <input
              type="text"
              defaultValue={searchParams?.get('search') ?? ''}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-64 rounded-md border border-border-light bg-sidebar-active py-1.5 pl-10 pr-4 text-sm text-text-main placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light"
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
    <Suspense
      fallback={
        <header className="h-16 border-b border-border-light bg-surface-light flex-shrink-0" />
      }
    >
      <TopBarContent {...props} />
    </Suspense>
  )
}

export function DashboardTopBar() {
  const pathname = usePathname()

  if (pathname === '/dashboard') {
    return <TopBar title="Dashboard" searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER} />
  }

  if (pathname === '/alerts') {
    return <TopBar title="Alerts" searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER} />
  }

  if (pathname === '/ml-health') {
    return <TopBar title="ML Health" showAlertControls={false} />
  }

  const fallbackTitle =
    pathname
      .split('/')
      .filter(Boolean)
      .at(-1)
      ?.split('-')
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(' ') ?? 'Dashboard'

  return <TopBar title={fallbackTitle} showAlertControls={false} />
}
