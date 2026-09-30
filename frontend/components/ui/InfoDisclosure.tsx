import type { ReactNode } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface InfoDisclosureProps {
  label: string
  children: ReactNode
  className?: string
}

/** A compact, keyboard and touch accessible explanation for unfamiliar terms. */
export function InfoDisclosure({ label, children, className }: InfoDisclosureProps) {
  const contentId = useId()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLSpanElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open])

  return (
    <span
      ref={rootRef}
      data-info-disclosure-open={open ? 'true' : undefined}
      onKeyDown={(event) => {
        if (open && event.key === 'Escape') {
          event.preventDefault()
          event.stopPropagation()
          setOpen(false)
          buttonRef.current?.focus()
        }
      }}
      className={cn('group relative inline-block align-middle', className)}
    >
      <button
        ref={buttonRef}
        type="button"
        aria-label={`About ${label}`}
        aria-expanded={open}
        aria-controls={contentId}
        title={`About ${label}`}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false)
        }}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-surface-border text-[10px] font-semibold leading-none text-text-secondary transition-colors hover:border-accent-action hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-panel"
      >
        <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <circle cx="10" cy="10" r="8" />
          <path d="M10 9v5" />
          <path d="M10 6.5h.01" />
        </svg>
      </button>
      {open ? (
        <div
          id={contentId}
          role="region"
          aria-label={`${label} explanation`}
          className="absolute left-0 top-full z-40 mt-1 w-64 max-w-[calc(100vw-2rem)] rounded-md border border-border-light bg-surface-panel p-3 text-xs leading-5 text-text-secondary shadow-xl"
        >
          <p className="mb-1 font-semibold text-text-primary">{label}</p>
          {children}
        </div>
      ) : null}
    </span>
  )
}
