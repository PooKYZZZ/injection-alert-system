'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
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

  const selectedCount = selectedIds.size

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
    setTimeout(() => setSummary(null), 3000)
  }

  return (
    <AnimatePresence>
      {selectedCount > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
          className="flex items-center justify-between rounded-md border border-[#30363d] bg-[#161b22] px-4 py-2"
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-blue-400">
                check_box
              </span>
              <span className="text-sm font-medium text-[#e6edf3]">
                {selectedCount} selected
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('false_positive')}
                className="rounded border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs font-medium text-[#7d8590] transition-colors hover:border-[#3d444d] hover:bg-[#30363d] hover:text-[#e6edf3] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Processing...' : 'Mark False Positive'}
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('escalated')}
                className="rounded border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs font-medium text-[#7d8590] transition-colors hover:border-red-800 hover:bg-red-950/30 hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Processing...' : 'Escalate'}
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => handleBulkTriage('resolved')}
                className="rounded border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs font-medium text-[#7d8590] transition-colors hover:border-emerald-800 hover:bg-emerald-950/30 hover:text-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Processing...' : 'Resolve'}
              </button>
            </div>

            {summary && (
              <span
                className={`text-xs ${
                  summary.includes('failed')
                    ? 'text-red-400'
                    : 'text-emerald-400'
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
            className="flex items-center gap-1 text-xs text-[#7d8590] transition-colors hover:text-[#e6edf3] disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[14px]">close</span>
            Clear selection
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
