import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface InfoDisclosureProps {
  label: string
  children: ReactNode
  className?: string
}

type PopoverSide = 'top' | 'right' | 'bottom' | 'left'

interface RectLike {
  left: number
  right: number
  top: number
  bottom: number
  width: number
  height: number
}

export interface InfoPopoverPosition {
  side: PopoverSide
  left: number
  top: number
  maxHeight: number
}

const VIEWPORT_PADDING = 12
const POPOVER_GAP = 8
const HOVER_CLOSE_DELAY_MS = 150

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

/** Keep the explanation inside the viewport and prefer a vertical placement. */
export function getInfoPopoverPosition(
  anchor: RectLike,
  popover: RectLike,
  viewportWidth: number,
  viewportHeight: number
): InfoPopoverPosition {
  const horizontalPadding = Math.min(VIEWPORT_PADDING, Math.max(0, (viewportWidth - 1) / 2))
  const verticalPadding = Math.min(VIEWPORT_PADDING, Math.max(0, (viewportHeight - 1) / 2))
  const maxHeight = Math.max(1, viewportHeight - verticalPadding * 2)
  const contentHeight = Math.min(popover.height, maxHeight)
  const belowSpace = Math.max(0, viewportHeight - anchor.bottom - POPOVER_GAP - verticalPadding)
  const aboveSpace = Math.max(0, anchor.top - POPOVER_GAP - verticalPadding)
  const rightSpace = Math.max(0, viewportWidth - anchor.right - POPOVER_GAP - horizontalPadding)
  const leftSpace = Math.max(0, anchor.left - POPOVER_GAP - horizontalPadding)
  const width = Math.max(1, Math.min(popover.width, viewportWidth - horizontalPadding * 2))

  let side: PopoverSide
  let availableHeight = maxHeight

  if (belowSpace >= contentHeight) {
    side = 'bottom'
  } else if (aboveSpace >= contentHeight) {
    side = 'top'
  } else if (Math.max(rightSpace, leftSpace) >= width) {
    side = rightSpace >= leftSpace ? 'right' : 'left'
  } else {
    side = belowSpace >= aboveSpace ? 'bottom' : 'top'
    availableHeight = Math.max(1, Math.min(maxHeight, Math.max(belowSpace, aboveSpace)))
  }

  const visibleHeight = Math.min(contentHeight, availableHeight)
  let left: number
  let top: number

  if (side === 'right') {
    left = anchor.right + POPOVER_GAP
    top = clamp(anchor.top, verticalPadding, viewportHeight - verticalPadding - visibleHeight)
  } else if (side === 'left') {
    left = anchor.left - POPOVER_GAP - width
    top = clamp(anchor.top, verticalPadding, viewportHeight - verticalPadding - visibleHeight)
  } else {
    left = clamp(anchor.left, horizontalPadding, viewportWidth - horizontalPadding - width)
    top = side === 'bottom'
      ? anchor.bottom + POPOVER_GAP
      : anchor.top - POPOVER_GAP - visibleHeight
    top = clamp(top, verticalPadding, viewportHeight - verticalPadding - visibleHeight)
  }

  return { side, left, top, maxHeight: availableHeight }
}

const useBrowserLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect

/** A compact, keyboard and touch accessible explanation for unfamiliar terms. */
export function InfoDisclosure({ label, children, className }: InfoDisclosureProps) {
  const contentId = useId()
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<InfoPopoverPosition | null>(null)
  const rootRef = useRef<HTMLSpanElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const hoverCloseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pointerTypeRef = useRef<string | null>(null)
  const triggerHoveredRef = useRef(false)
  const popoverHoveredRef = useRef(false)
  const openSourceRef = useRef<'click' | 'focus' | 'hover' | null>(null)

  const clearHoverCloseTimer = useCallback(() => {
    if (hoverCloseTimerRef.current !== null) {
      clearTimeout(hoverCloseTimerRef.current)
      hoverCloseTimerRef.current = null
    }
  }, [])

  const scheduleHoverClose = useCallback(() => {
    clearHoverCloseTimer()
    hoverCloseTimerRef.current = setTimeout(() => {
      hoverCloseTimerRef.current = null
      if (
        triggerHoveredRef.current ||
        popoverHoveredRef.current ||
        openSourceRef.current !== 'hover'
      ) {
        return
      }
      openSourceRef.current = null
      setOpen(false)
      setPosition(null)
    }, HOVER_CLOSE_DELAY_MS)
  }, [clearHoverCloseTimer])

  const close = useCallback(() => {
    clearHoverCloseTimer()
    openSourceRef.current = null
    setOpen(false)
    setPosition(null)
    buttonRef.current?.focus()
  }, [clearHoverCloseTimer])

  useEffect(() => clearHoverCloseTimer, [clearHoverCloseTimer])

  useEffect(() => {
    if (!open) return
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target
      if (
        target instanceof Node &&
        (rootRef.current?.contains(target) || popoverRef.current?.contains(target))
      ) {
        return
      }
      openSourceRef.current = null
      setOpen(false)
      setPosition(null)
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open])

  useEffect(() => {
    const containingDisclosure = rootRef.current?.closest('details')
    if (!containingDisclosure) return

    const closeWhenCollapsed = () => {
      if (containingDisclosure.open) return
      openSourceRef.current = null
      setOpen(false)
      setPosition(null)
    }

    containingDisclosure.addEventListener('toggle', closeWhenCollapsed)
    return () => containingDisclosure.removeEventListener('toggle', closeWhenCollapsed)
  }, [])

  useBrowserLayoutEffect(() => {
    if (!open) return

    const updatePosition = () => {
      const trigger = buttonRef.current
      const popover = popoverRef.current
      if (!trigger || !popover) return

      setPosition(
        getInfoPopoverPosition(
          trigger.getBoundingClientRect(),
          popover.getBoundingClientRect(),
          window.visualViewport?.width ?? window.innerWidth,
          window.visualViewport?.height ?? window.innerHeight
        )
      )
    }

    updatePosition()
    window.addEventListener('resize', updatePosition)
    document.addEventListener('scroll', updatePosition, true)
    window.visualViewport?.addEventListener('resize', updatePosition)
    window.visualViewport?.addEventListener('scroll', updatePosition)

    const resizeObserver = typeof ResizeObserver === 'undefined'
      ? null
      : new ResizeObserver(updatePosition)
    if (buttonRef.current) resizeObserver?.observe(buttonRef.current)
    if (popoverRef.current) resizeObserver?.observe(popoverRef.current)

    return () => {
      window.removeEventListener('resize', updatePosition)
      document.removeEventListener('scroll', updatePosition, true)
      window.visualViewport?.removeEventListener('resize', updatePosition)
      window.visualViewport?.removeEventListener('scroll', updatePosition)
      resizeObserver?.disconnect()
    }
  }, [open])

  return (
    <span
      ref={rootRef}
      data-info-disclosure-container
      data-info-disclosure-open={open ? 'true' : undefined}
      onKeyDownCapture={(event) => {
        if (open && event.key === 'Escape') {
          event.preventDefault()
          event.stopPropagation()
          close()
        }
      }}
      onPointerEnter={(event) => {
        if (event.pointerType !== 'mouse') return
        triggerHoveredRef.current = true
        clearHoverCloseTimer()
        if (openSourceRef.current === 'click' || openSourceRef.current === 'focus') return
        openSourceRef.current = 'hover'
        setOpen(true)
      }}
      onPointerLeave={(event) => {
        if (event.pointerType !== 'mouse') return
        triggerHoveredRef.current = false
        if (openSourceRef.current === 'hover') scheduleHoverClose()
      }}
      className={cn('group relative inline-block align-middle', className)}
    >
      <button
        ref={buttonRef}
        type="button"
        aria-label={`About ${label}`}
        aria-expanded={open}
        aria-controls={contentId}
        aria-describedby={open ? contentId : undefined}
        onPointerDown={(event) => {
          pointerTypeRef.current = event.pointerType
        }}
        onFocus={(event) => {
          if (!event.currentTarget.matches(':focus-visible')) return
          clearHoverCloseTimer()
          openSourceRef.current = 'focus'
          setOpen(true)
        }}
        onBlur={() => {
          if (openSourceRef.current !== 'focus') return
          if (triggerHoveredRef.current || popoverHoveredRef.current) {
            openSourceRef.current = 'hover'
            return
          }
          openSourceRef.current = null
          setOpen(false)
          setPosition(null)
        }}
        onClick={() => {
          const pointerType = pointerTypeRef.current
          pointerTypeRef.current = null
          if (pointerType === 'mouse') {
            const next = openSourceRef.current !== 'click'
            openSourceRef.current = next ? 'click' : null
            if (next && !open) setPosition(null)
            if (!next) setPosition(null)
            setOpen(next)
            return
          }
          if (pointerType === null && openSourceRef.current === 'focus' && open) return
          const next = !open
          if (next) setPosition(null)
          openSourceRef.current = next ? 'click' : null
          setOpen(next)
        }}
        className="info-disclosure-trigger inline-flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-semibold leading-none"
      >
        <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <circle cx="10" cy="10" r="8" />
          <path d="M10 9v5" />
          <path d="M10 6.5h.01" />
        </svg>
      </button>
      {open && typeof document !== 'undefined'
        ? createPortal(
            <div
              id={contentId}
              ref={popoverRef}
              role="region"
              data-info-disclosure-popover
              aria-label={`${label} explanation`}
              data-side={position?.side}
              onPointerEnter={(event) => {
                if (event.pointerType !== 'mouse') return
                popoverHoveredRef.current = true
                clearHoverCloseTimer()
              }}
              onPointerLeave={(event) => {
                if (event.pointerType !== 'mouse') return
                popoverHoveredRef.current = false
                if (openSourceRef.current === 'hover') scheduleHoverClose()
              }}
              style={{
                position: 'fixed',
                left: position?.left ?? -10000,
                top: position?.top ?? -10000,
                width: 300,
                maxWidth: 'calc(100vw - 24px)',
                maxHeight: position ? `${position.maxHeight}px` : 'calc(100dvh - 24px)',
                boxSizing: 'border-box',
                visibility: position ? 'visible' : 'hidden',
              }}
              className="info-disclosure-popover z-[100] overflow-y-auto rounded-lg border p-3 text-[13px] leading-5 shadow-xl ring-1 ring-black/10 normal-case tracking-normal"
            >
              <p className="info-disclosure-title mb-1 font-semibold normal-case tracking-normal">{label}</p>
              <div className="normal-case tracking-normal">{children}</div>
            </div>,
            document.body
          )
        : null}
    </span>
  )
}
