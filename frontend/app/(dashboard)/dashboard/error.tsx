'use client'

import { useEffect } from 'react'

interface ErrorProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function DashboardError({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('[Dashboard Error]', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8">
      <p className="text-sm font-medium text-red-600">
        Something went wrong loading the dashboard.
      </p>
      {error.digest && (
        <p className="text-xs text-gray-500">Error ID: {error.digest}</p>
      )}
      <button
        type="button"
        onClick={reset}
        className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700 transition-colors"
      >
        Try again
      </button>
    </div>
  )
}
