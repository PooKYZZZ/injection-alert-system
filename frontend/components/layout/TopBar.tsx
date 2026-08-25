'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { usePathname, useSearchParams, useRouter } from 'next/navigation'
import { useTheme } from '@/app/providers'
import { cn } from '@/lib/utils'
import { getCurrentSearchParams } from '@/lib/searchParams'

const DEFAULT_SEARCH_PLACEHOLDER = 'Search alerts'

interface TopBarProps {
  /** The active dashboard section shown as lightweight utility context. */
  title?: string
  /** Deprecated compatibility prop retained for existing callers. */
  showTitle?: boolean
  /** Deprecated compatibility prop. Confidence filtering belongs to the Alerts controls. */
  showConfidenceTierControls?: boolean
  showSearch?: boolean
  /** Deprecated compatibility prop. Alert counts are not a global navigation primitive. */
  showLiveStatus?: boolean
  searchPlaceholder?: string
  /** Deprecated compatibility prop. Static counts are intentionally not rendered. */
  showNewIndicator?: boolean
  searchPath?: string
}

function TopBarContent({
  title,
  showSearch = true,
  searchPlaceholder = DEFAULT_SEARCH_PLACEHOLDER,
  searchPath = '/alerts',
}: TopBarProps) {
  const searchParams = useSearchParams()
  const router = useRouter()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const handleSearch = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(() => {
      const query = createQueryString('search', value || null)
      router.push(query ? `${searchPath}?${query}` : searchPath, {
        scroll: false,
      })
    }, 300)
  }

  return (
    <header className="z-10 flex min-h-14 flex-shrink-0 items-center justify-between gap-3 border-b border-border-light bg-surface-panel pl-16 pr-4 shadow-subtle sm:gap-4 sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <span className="max-w-[10rem] truncate text-sm font-semibold tracking-tight text-text-primary sm:max-w-none">
          {title ?? 'Security operations'}
        </span>
      </div>

      <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-3">
        {showSearch ? (
          <div className="relative min-w-0 w-[min(42vw,18rem)] sm:w-72">
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
                className="text-text-muted"
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
              className="h-9 w-full min-w-0 rounded-md border border-border-light bg-surface-inset py-1.5 pl-10 pr-3 text-sm text-text-primary placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel"
            />
          </div>
        ) : null}
        <ThemeToggleButton />
      </div>
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
  const buttonLabel = isMounted ? `Use ${nextTheme} theme` : 'Theme'
  const ariaLabel = isMounted ? `Switch to ${nextTheme} theme` : 'Toggle theme'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={ariaLabel}
      title={ariaLabel}
      className={cn(
        'inline-flex h-9 shrink-0 items-center rounded-md border border-border-light bg-surface-inset px-2 text-xs font-medium text-text-primary transition-colors hover:bg-surface-card',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel sm:px-3'
      )}
    >
      <span aria-hidden="true" className="text-sm leading-none sm:hidden">◐</span>
      <span className="hidden sm:inline">{buttonLabel}</span>
    </button>
  )
}

export function TopBar(props: TopBarProps) {
  return (
    <Suspense fallback={<header className="min-h-14 flex-shrink-0 border-b border-border-light bg-surface-panel" />}>
      <TopBarContent {...props} />
    </Suspense>
  )
}

export function DashboardTopBar() {
  const pathname = usePathname()
  const routeSegment = pathname.split('/').filter(Boolean).at(-1) ?? 'dashboard'
  const routeTitles: Record<string, string> = {
    dashboard: 'Dashboard',
    'ml-health': 'ML Health',
    'ml-model': 'Model Operations',
    mfa: 'MFA',
  }

  const fallbackTitle = routeTitles[routeSegment] ?? routeSegment
    .split('-')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')

  return (
    <TopBar
      title={fallbackTitle}
      showSearch={pathname === '/dashboard' || pathname.startsWith('/alerts')}
      searchPlaceholder={DEFAULT_SEARCH_PLACEHOLDER}
      searchPath="/alerts"
    />
  )
}
