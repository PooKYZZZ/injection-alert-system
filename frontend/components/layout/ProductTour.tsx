'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useMemo, useRef, useState } from 'react'

import type { ProductTourDefinition, ProductTourStep } from './productTourSteps'

interface ProductTourProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  returnFocusRef: React.RefObject<HTMLButtonElement | null>
  tour: ProductTourDefinition
}

interface TourRect {
  top: number
  right: number
  bottom: number
  left: number
  width: number
  height: number
}

const SPOTLIGHT_PADDING = 8

function findTourTarget(target: string | undefined): HTMLElement | null {
  if (!target || typeof document === 'undefined') return null

  return Array.from(
    document.querySelectorAll<HTMLElement>('[data-tour-target]')
  ).find((element) => element.dataset.tourTarget === target) ?? null
}

function isStepAvailable(step: ProductTourStep): boolean {
  return !step.target || findTourTarget(step.target) !== null
}

function findAvailableStepIndex(
  steps: readonly ProductTourStep[],
  startIndex: number,
  direction: 1 | -1
): number {
  for (
    let index = startIndex;
    index >= 0 && index < steps.length;
    index += direction
  ) {
    if (isStepAvailable(steps[index])) return index
  }
  return -1
}

function resolveAvailableStepIndex(
  steps: readonly ProductTourStep[],
  requestedIndex: number
): number {
  if (steps.length === 0) return -1

  const normalizedIndex = Math.min(
    Math.max(requestedIndex, 0),
    steps.length - 1
  )
  const forwardIndex = findAvailableStepIndex(steps, normalizedIndex, 1)
  if (forwardIndex >= 0) return forwardIndex

  return findAvailableStepIndex(steps, normalizedIndex - 1, -1)
}

function readRect(element: HTMLElement): TourRect {
  const rect = element.getBoundingClientRect()
  return {
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

export function ProductTour({
  open,
  onOpenChange,
  returnFocusRef,
  tour,
}: ProductTourProps) {
  if (!open) return null

  return (
    <ProductTourSession
      key={tour.id}
      onOpenChange={onOpenChange}
      returnFocusRef={returnFocusRef}
      tour={tour}
    />
  )
}

function ProductTourSession({
  onOpenChange,
  returnFocusRef,
  tour,
}: Omit<ProductTourProps, 'open'>) {
  const [stepIndex, setStepIndex] = useState(0)
  const [targetMeasurement, setTargetMeasurement] = useState<{
    stepId: string
    rect: TourRect
  } | null>(null)
  const [calloutHeight, setCalloutHeight] = useState(0)
  const calloutRef = useRef<HTMLDivElement>(null)
  const steps = tour.steps

  const resolvedStepIndex = useMemo(
    () => resolveAvailableStepIndex(steps, stepIndex),
    [stepIndex, steps]
  )
  const activeStep =
    resolvedStepIndex >= 0 ? steps[resolvedStepIndex] : undefined
  const activeTarget = activeStep?.target
    ? findTourTarget(activeStep.target)
    : null
  const targetRect =
    activeTarget &&
    targetMeasurement &&
    targetMeasurement.stepId === activeStep?.id
      ? targetMeasurement.rect
      : null
  const nextStepIndex = useMemo(
    () => findAvailableStepIndex(steps, resolvedStepIndex + 1, 1),
    [resolvedStepIndex, steps]
  )
  const previousStepIndex = useMemo(
    () => findAvailableStepIndex(steps, resolvedStepIndex - 1, -1),
    [resolvedStepIndex, steps]
  )
  const isLastStep = nextStepIndex < 0

  useEffect(() => {
    if (!activeStep) return

    if (!activeTarget) return

    const updateRect = () => {
      setTargetMeasurement({
        stepId: activeStep.id,
        rect: readRect(activeTarget),
      })
    }
    const viewportMargin = 72
    const initialRect = activeTarget.getBoundingClientRect()
    const outsideViewport =
      initialRect.top < viewportMargin ||
      initialRect.bottom > window.innerHeight - viewportMargin ||
      initialRect.left < viewportMargin ||
      initialRect.right > window.innerWidth - viewportMargin

    if (outsideViewport) {
      activeTarget.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
    }

    const frame = window.requestAnimationFrame(updateRect)
    const settledFrame = window.setTimeout(updateRect, outsideViewport ? 350 : 0)
    const handleViewportChange = () => updateRect()
    window.addEventListener('resize', handleViewportChange)
    window.addEventListener('scroll', handleViewportChange, true)

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(updateRect)
      observer.observe(activeTarget)
      return () => {
        window.cancelAnimationFrame(frame)
        window.clearTimeout(settledFrame)
        window.removeEventListener('resize', handleViewportChange)
        window.removeEventListener('scroll', handleViewportChange, true)
        observer.disconnect()
      }
    }

    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(settledFrame)
      window.removeEventListener('resize', handleViewportChange)
      window.removeEventListener('scroll', handleViewportChange, true)
    }
  }, [activeStep, activeTarget])

  useEffect(() => {
    if (!activeTarget) return

    if (
      activeTarget.matches(
        'a,button,input,select,textarea,[tabindex]:not([tabindex="-1"])'
      )
    ) {
      activeTarget.focus({ preventScroll: true })
    }
  }, [activeTarget])

  useEffect(() => {
    const updateCalloutSize = () => {
      const callout = calloutRef.current
      if (callout) setCalloutHeight(callout.getBoundingClientRect().height)
    }

    const frame = window.requestAnimationFrame(updateCalloutSize)
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(updateCalloutSize)
    if (observer && calloutRef.current) observer.observe(calloutRef.current)

    return () => {
      window.cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [activeStep])

  const spotlight = useMemo(() => {
    if (!targetRect) return null
    const left = Math.max(0, targetRect.left - SPOTLIGHT_PADDING)
    const top = Math.max(0, targetRect.top - SPOTLIGHT_PADDING)
    const right = Math.min(
      typeof window === 'undefined' ? targetRect.right : window.innerWidth,
      targetRect.right + SPOTLIGHT_PADDING
    )
    const bottom = Math.min(
      typeof window === 'undefined' ? targetRect.bottom : window.innerHeight,
      targetRect.bottom + SPOTLIGHT_PADDING
    )
    return {
      left,
      top,
      right,
      bottom,
      width: Math.max(0, right - left),
      height: Math.max(0, bottom - top),
    }
  }, [targetRect])

  if (!activeStep) return null

  const viewportWidth = typeof window === 'undefined' ? 1024 : window.innerWidth
  const viewportHeight = typeof window === 'undefined' ? 768 : window.innerHeight
  const calloutWidth = Math.min(360, Math.max(0, viewportWidth - 32))
  const estimatedCalloutHeight =
    calloutHeight || Math.min(280, Math.max(120, viewportHeight * 0.36))
  const maxCalloutTop = Math.max(16, viewportHeight - estimatedCalloutHeight - 16)
  const calloutLeft = spotlight
    ? clamp(spotlight.left, 16, viewportWidth - calloutWidth - 16)
    : Math.max(16, (viewportWidth - calloutWidth) / 2)
  const belowTop = spotlight ? spotlight.bottom + 16 : 16
  const aboveTop = spotlight
    ? spotlight.top - estimatedCalloutHeight - 16
    : 16
  const canPlaceBelow = belowTop <= maxCalloutTop
  const canPlaceAbove = aboveTop >= 16
  const preferAbove = Boolean(spotlight && spotlight.top > viewportHeight * 0.48)
  const placeAbove = Boolean(
    spotlight &&
      (preferAbove ? canPlaceAbove || !canPlaceBelow : !canPlaceBelow && canPlaceAbove)
  )
  const calloutTop = spotlight
    ? clamp(placeAbove ? aboveTop : belowTop, 16, maxCalloutTop)
    : clamp((viewportHeight - estimatedCalloutHeight) / 2, 16, maxCalloutTop)

  const goToNextStep = () => {
    if (nextStepIndex < 0) {
      onOpenChange(false)
      return
    }
    setTargetMeasurement(null)
    setStepIndex(nextStepIndex)
  }

  const goToPreviousStep = () => {
    if (previousStepIndex < 0) return
    setTargetMeasurement(null)
    setStepIndex(previousStepIndex)
  }

  return (
    <Dialog.Root open onOpenChange={onOpenChange} modal>
      <Dialog.Portal>
        <Dialog.Overlay asChild>
          <div
            aria-hidden="true"
            className="fixed inset-0 z-[60]"
            onClick={(event) => {
              if (event.target === event.currentTarget) onOpenChange(false)
            }}
          >
            {spotlight ? (
              <>
                <div
                  className="absolute bg-black/60"
                  style={{ inset: '0 0 auto 0', height: spotlight.top }}
                />
                <div
                  className="absolute bg-black/60"
                  style={{
                    top: spotlight.top,
                    left: 0,
                    width: spotlight.left,
                    height: spotlight.height,
                  }}
                />
                <div
                  className="absolute bg-black/60"
                  style={{
                    top: spotlight.top,
                    left: spotlight.right,
                    right: 0,
                    height: spotlight.height,
                  }}
                />
                <div
                  className="absolute bg-black/60"
                  style={{
                    top: spotlight.bottom,
                    right: 0,
                    bottom: 0,
                    left: 0,
                  }}
                />
              </>
            ) : (
              <div className="absolute inset-0 bg-black/60" />
            )}
          </div>
        </Dialog.Overlay>

        {spotlight ? (
          <div
            aria-hidden="true"
            className="pointer-events-none fixed z-[61] rounded-lg border-2 border-accent-action shadow-[0_0_0_3px_rgba(255,255,255,0.35)]"
            style={{
              top: spotlight.top,
              left: spotlight.left,
              width: spotlight.width,
              height: spotlight.height,
            }}
          />
        ) : null}

        <Dialog.Content
          ref={calloutRef}
          onCloseAutoFocus={(event) => {
            event.preventDefault()
            returnFocusRef.current?.focus()
          }}
          onPointerDownOutside={(event) => event.preventDefault()}
          onInteractOutside={(event) => event.preventDefault()}
          className="fixed z-[70] flex max-h-[min(70dvh,440px)] flex-col overflow-hidden rounded-xl border border-border-light bg-surface-panel shadow-2xl outline-none"
          style={{
            width: calloutWidth,
            left: calloutLeft,
            top: calloutTop,
            maxHeight: Math.max(0, viewportHeight - 32),
          }}
        >
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border-light px-5 py-4">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-accent-action">
                {tour.title}
              </p>
              <Dialog.Title className="sr-only">{tour.title}</Dialog.Title>
              <h2 className="mt-1 text-lg font-semibold text-text-primary">
                {activeStep.title}
              </h2>
              <Dialog.Description className="mt-1 text-sm leading-5 text-text-secondary">
                {activeStep.description}
              </Dialog.Description>
            </div>
            <button
              type="button"
              aria-label="Close Help & Guide"
              onClick={() => onOpenChange(false)}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border-light text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
            >
              <span aria-hidden="true" className="text-lg leading-none">×</span>
            </button>
          </header>

          <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border-light px-5 py-3 text-xs text-text-muted">
            <span aria-live="polite">Step {resolvedStepIndex + 1} of {steps.length}</span>
            <span>{tour.description}</span>
          </div>

          <footer className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-md px-2 py-2 text-xs font-medium text-text-secondary underline-offset-4 hover:text-text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
            >
              Skip tour
            </button>
            <div className="flex items-center gap-2">
              <button
              type="button"
              onClick={goToPreviousStep}
              disabled={previousStepIndex < 0}
                className="rounded-md border border-border-light px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={goToNextStep}
                className="rounded-md bg-accent-action px-3 py-2 text-xs font-semibold text-surface-shell transition-colors hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel"
              >
                {isLastStep ? 'Finish' : 'Next'}
              </button>
            </div>
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
