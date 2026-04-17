'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { CheckSquare } from 'lucide-react'
import { useTriageMutation } from '@/features/alerts/queries'
import type { TriageStatus } from '@/features/alerts/types'

interface BulkActionBarProps {
  selectedIds: Set<string>
  onClearSelection: () => void
}

const CONCURRENCY_LIMIT = 20

export function BulkActionBar({ selectedIds, onClearSelection }: BulkActionBarProps) {
  const [summary, setSummary] = useState<string | null>(null)
  const { mutateAsync } = useTriageMutation()
  const [isProcessing, setIsProcessing] = useState(false)
  const summaryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const selectedCount = selectedIds.size

  useEffect(() => {
    return () => {
      if (summaryTimeoutRef.current) {
        clearTimeout(summaryTimeoutRef.current)
      }
    }
  }, [])

  const handleBulkTriage = async (status: TriageStatus) => {
    if (selectedCount === 0 || isProcessing) return

    setIsProcessing(true)
    setSummary(null)

    const ids = [...selectedIds]
    const results: PromiseSettledResult<unknown>[] = []

    // Process in chunks to limit concurrency
    for (let i = 0; i < ids.length; i += CONCURRENCY_LIMIT) {
      const chunk = ids.slice(i, i + CONCURRENCY_LIMIT)
      const chunkResults = await Promise.allSettled(
        chunk.map((id) => mutateAsync({ id, status }))
      )
      results.push(...chunkResults)
    }

    const succeeded = results.filter(
      (r): r is PromiseFulfilledResult<unknown> => r.status === 'fulfilled'
    ).length
    const failed = results.filter(
      (r): r is PromiseRejectedResult => r.status === 'rejected'
    ).length

    const summaryMessage =
      failed === 0
        ? `${succeeded} alert${succeeded !== 1 ? 's' : ''} updated`
        : `${succeeded} updated, ${failed} failed`

    setSummary(summaryMessage)
    setIsProcessing(false)

    // Clear selection after successful bulk operation
    if (failed === 0) {
      onClearSelection()
    }

    // Clear summary after 3 seconds
    if (summaryTimeoutRef.current) {
      clearTimeout(summaryTimeoutRef.current)
    }
    summaryTimeoutRef.current = setTimeout(() => setSummary(null), 3000)
  }

  return (
    <AnimatePresence>
      {selectedCount > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
          className="flex items-center justify-between rounded-md border border-border-light bg-bg-card px-4 py-2"
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CheckSquare size={14} className="text-accent-purple" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">
                {selectedCount} selected
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('false_positive')}
                className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-secondary transition-colors hover:border-primary hover:text-accent-purple disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isProcessing ? 'Processing...' : 'Mark False Positive'}
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('escalated')}
                className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-secondary transition-colors hover:border-severity-high-border hover:bg-severity-high-bg hover:text-severity-high-text disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isProcessing ? 'Processing...' : 'Escalate'}
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('resolved')}
                className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-secondary transition-colors hover:border-severity-safe-border hover:bg-severity-safe-bg hover:text-severity-safe-text disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isProcessing ? 'Processing...' : 'Resolve'}
              </button>
            </div>

            {summary && (
              <span
                className={`text-xs ${
                  summary.includes('failed')
                    ? 'text-severity-high-text'
                    : 'text-severity-safe-text'
                }`}
              >
                {summary}
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={onClearSelection}
            disabled={isProcessing}
            className="flex items-center gap-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:text-accent-purple disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[14px]"></span>
            Clear Selection
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}


