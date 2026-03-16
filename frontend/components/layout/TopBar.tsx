'use client'

import { Suspense, useRef } from 'react'
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
    'px-2.5 py-1 rounded-full text-[10px] font-bold border transition-colors cursor-pointer'

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

function TopBarContent() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const rawSeverity = searchParams.get('severity')
  const currentSeverity: SeverityFilter =
    rawSeverity === 'HIGH' || rawSeverity === 'MEDIUM' || rawSeverity === 'LOW'
      ? rawSeverity
      : 'ALL'

  const setSeverity = (severity: SeverityFilter) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('severity', severity)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }

  const handleSearch = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString())

      if (value) params.set('search', value)
      else params.delete('search')

      router.push(`${pathname}?${params.toString()}`, { scroll: false })
    }, 300)
  }

  return (
    <header className="h-16 border-b border-border-light bg-surface-light flex items-center justify-between px-6 flex-shrink-0 shadow-subtle z-10">

      {/* Left side: title + confidence filter */}
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-bold text-text-main tracking-tight">
          SOC Overview
        </h2>

        <div className="h-4 w-[1px] bg-border-light" />

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            ML Confidence
          </span>
          {SEVERITY_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setSeverity(value)}
              className={pillClasses(value, currentSeverity === value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Right side: search only */}
      <div className="flex items-center gap-6">
        <div className="relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-[18px]">
            search
          </span>

          <input
            type="text"
            defaultValue={searchParams.get('search') ?? ''}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search IP address..."
            className="bg-sidebar-active border border-border-light text-sm text-text-main rounded-md pl-10 pr-4 py-1.5 focus:outline-none focus:border-primary w-64 placeholder:text-gray-400"
          />
        </div>
      </div>

    </header>
  )
}

export function TopBar() {
  return (
    <Suspense
      fallback={
        <header className="h-16 border-b border-border-light bg-surface-light flex-shrink-0" />
      }
    >
      <TopBarContent />
    </Suspense>
  )
}
