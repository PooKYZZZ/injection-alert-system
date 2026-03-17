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

function pillClasses(isActive: boolean): string {
  const base =
    'inline-flex min-h-[28px] cursor-pointer items-center justify-center rounded-[12px] border px-[10px] text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel'

  return isActive
    ? `${base} border-accent-blue bg-accent-blue-bg text-accent-blue`
    : `${base} border-[#243050] bg-transparent text-text-secondary hover:border-[#334155] hover:text-text-primary`
}

interface TopBarProps {
  title: string
  showAlertControls?: boolean
  searchPlaceholder?: string
}

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
        <h2 className="text-lg font-semibold tracking-tight text-text-primary">{title}</h2>

        {showAlertControls ? (
          <>
            <div className="h-4 w-px bg-border-light" />
            <div className="flex items-center gap-1.5">
              {SEVERITY_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setSeverity(value)}
                  className={pillClasses(currentSeverity === value)}
                  aria-pressed={currentSeverity === value}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        ) : null}
      </div>

      {showAlertControls ? (
        <div className="flex items-center gap-6">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-text-secondary">
              search
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
