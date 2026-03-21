'use client'

import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface LoadingSkeletonProps {
  rows?: number
  className?: string
}

export function LoadingSkeleton({ rows = 5, className }: LoadingSkeletonProps) {
  const widths = ['w-full', 'w-4/5', 'w-full', 'w-3/4', 'w-full']

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'h-4 rounded animate-skeleton',
            widths[i % widths.length]
          )}
          style={{ backgroundColor: 'var(--color-bg-elevated)' }}
        />
      ))}
    </div>
  )
}

// AlertCircle icon (20px)
function AlertCircleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" x2="12" y1="8" y2="12" />
      <line x1="12" x2="12.01" y1="16" y2="16" />
    </svg>
  )
}

// Inbox icon (20px)
function InboxIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
    </svg>
  )
}

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Failed to load data', onRetry }: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col items-center gap-2 py-8 text-[#7d8590]"
    >
      <AlertCircleIcon className="h-5 w-5" />
      <span className="text-sm">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded border border-[#30363d] bg-[#161b22] px-3 py-1 text-xs text-[#e6edf3] transition-all hover:border-[#7d8590]"
        >
          Retry
        </button>
      )}
    </motion.div>
  )
}

interface EmptyStateProps {
  message?: string
  subtext?: string
}

export function EmptyState({ message = 'No results found', subtext }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col items-center justify-center w-full h-full min-h-[120px] rounded-lg border border-dashed border-[#30363d] bg-[#161b22]/50 p-6 text-center"
    >
      <svg className="w-6 h-6 text-[#484f58] mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
      <p className="text-[11px] font-medium text-[#7d8590]">{message}</p>
      {subtext && <p className="text-[10px] text-[#484f58] mt-1">{subtext}</p>}
    </motion.div>
  )
}
