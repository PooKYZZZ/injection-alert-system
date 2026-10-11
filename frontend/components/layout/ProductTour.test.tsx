import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProductTour } from './ProductTour'

const tour = {
  id: 'test-tour',
  title: 'Test tour',
  description: 'A test walkthrough.',
  steps: [
    { id: 'first', title: 'First step', description: 'First explanation.', target: 'first-target' },
    { id: 'second', title: 'Second step', description: 'Second explanation.', target: 'second-target' },
  ],
} as const

const originalScrollIntoView = HTMLElement.prototype.scrollIntoView

beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: vi.fn(),
  })
})

afterEach(() => {
  cleanup()
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: originalScrollIntoView,
  })
  vi.restoreAllMocks()
})

describe('ProductTour', () => {
  it('supports next, previous, finish, skip, and restart from the first step', () => {
    const onOpenChange = vi.fn()
    const view = render(
      <>
        <div data-tour-target="first-target">First target</div>
        <div data-tour-target="second-target">Second target</div>
      </>,
    )
    const rerender = (open: boolean) => {
      view.rerender(
        <>
          <div data-tour-target="first-target">First target</div>
          <div data-tour-target="second-target">Second target</div>
          <ProductTour
            open={open}
            onOpenChange={onOpenChange}
            returnFocusRef={{ current: null }}
            tour={tour}
          />
        </>,
      )
    }
    rerender(true)

    expect(screen.getByRole('heading', { name: 'First step' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('heading', { name: 'Second step' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Finish' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByRole('heading', { name: 'First step' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Skip tour' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)

    rerender(false)
    expect(screen.queryByRole('dialog', { name: 'Test tour' })).not.toBeInTheDocument()

    rerender(true)
    expect(screen.getByRole('heading', { name: 'First step' })).toBeInTheDocument()
  })

  it('skips unavailable targets instead of rendering a broken step', () => {
    const onOpenChange = vi.fn()
    const missingTargetTour = {
      ...tour,
      id: 'missing-target-tour',
      steps: [
        { id: 'missing', title: 'Missing step', description: 'Not rendered.', target: 'missing-target' },
        tour.steps[1],
      ],
    } as const

    const view = render(<div data-tour-target="second-target">Second target</div>)
    view.rerender(
      <>
        <div data-tour-target="second-target">Second target</div>
        <ProductTour
          open
          onOpenChange={onOpenChange}
          returnFocusRef={{ current: null }}
          tour={missingTargetTour}
        />
      </>,
    )

    expect(screen.queryByRole('heading', { name: 'Missing step' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Second step' })).toBeInTheDocument()
  })

  it('keeps the callout inside the viewport for a target taller than the screen', async () => {
    const originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      if (this.dataset.tourTarget === 'first-target') {
        return {
          top: 100,
          right: 500,
          bottom: 1200,
          left: 20,
          width: 480,
          height: 1100,
        } as DOMRect
      }
      return originalGetBoundingClientRect.call(this)
    })

    const onOpenChange = vi.fn()
    const view = render(<div data-tour-target="first-target">First target</div>)
    view.rerender(
      <>
        <div data-tour-target="first-target">First target</div>
        <ProductTour
          open
          onOpenChange={onOpenChange}
          returnFocusRef={{ current: null }}
          tour={tour}
        />
      </>,
    )

    await waitFor(() => {
      const top = Number.parseFloat(screen.getByRole('dialog', { name: 'Test tour' }).style.top)
      expect(top).toBeGreaterThan(450)
      expect(top).toBeLessThan(window.innerHeight - 16)
    })
  })
})
