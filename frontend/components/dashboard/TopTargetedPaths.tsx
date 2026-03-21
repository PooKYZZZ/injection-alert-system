'use client'

import { LoadingSkeleton } from '@/components/ui/StateViews'

export interface TargetPathSummary {
  path: string
  hits: number
}

interface TopTargetedPathsProps {
  paths: TargetPathSummary[]
  isPending?: boolean
}

export function TopTargetedPaths({ paths, isPending = false }: TopTargetedPathsProps) {
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  if (paths.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-6 gap-2">
        <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">
          No targeted paths in this window
        </p>
        <p className="text-[10px] text-[var(--color-text-muted)] text-center max-w-[160px] leading-relaxed">
          Paths appear when attack traffic is detected
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      {paths.map((item) => (
        <div
          key={item.path}
          className="flex items-center justify-between py-1 border-b border-[var(--color-text-ghost)] last:border-0 text-[11px]"
        >
          <span className="font-mono text-blue-400 truncate max-w-[120px]">{item.path}</span>
          <span className="text-[var(--color-text-secondary)]">{item.hits} hits</span>
        </div>
      ))}
    </div>
  )
}

