'use client'

import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

export interface TargetPathSummary {
  path: string
  hits: number
}

interface TopTargetedPathsProps {
  paths: TargetPathSummary[]
  isLoading?: boolean
}

export function TopTargetedPaths({ paths, isLoading = false }: TopTargetedPathsProps) {
  if (isLoading) {
    return <LoadingSkeleton rows={4} />
  }

  if (paths.length === 0) {
    return (
      <EmptyState message="No path data" subtext="Top targeted paths will appear here when available" />
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      {paths.map((item) => (
        <div
          key={item.path}
          className="flex items-center justify-between py-1 border-b border-[#21262d] last:border-0 text-[11px]"
        >
          <span className="font-mono text-blue-400 truncate max-w-[120px]">{item.path}</span>
          <span className="text-[#8b949e]">{item.hits} hits</span>
        </div>
      ))}
    </div>
  )
}
