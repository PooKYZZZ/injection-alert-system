'use client'

import { useState } from 'react'

interface AlertBannerProps {
  variant: 'error' | 'warning'
  message: string
  detail?: string
  onDismiss?: () => void
}

export default function AlertBanner({ variant, message, detail, onDismiss }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  const isError = variant === 'error'

  const containerClass = isError
    ? 'bg-[#fff5f5] border-l-[3px] border-primary'
    : 'bg-yellow-50 border-l-[3px] border-status-throttled'

  const icon = isError ? 'error' : 'psychology'

  const iconClass = isError ? 'text-red-600' : 'text-orange-500'

  function handleDismiss() {
    if (onDismiss) onDismiss()
    setDismissed(true)
  }

  return (
    <div className={`flex items-start gap-3 p-3 rounded-sm ${containerClass}`}>
      <span className={`material-symbols-outlined text-[20px] shrink-0 mt-0.5 ${iconClass}`}>
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-main">{message}</p>
        {detail && (
          <p className="text-xs text-text-muted mt-0.5">{detail}</p>
        )}
      </div>
      <button
        type="button"
        onClick={handleDismiss}
        className="shrink-0 text-text-muted hover:text-text-main transition-colors"
        aria-label="Dismiss"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  )
}
