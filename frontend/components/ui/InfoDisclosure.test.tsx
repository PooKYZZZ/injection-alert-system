import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { getInfoPopoverPosition, InfoDisclosure } from './InfoDisclosure'

afterEach(() => cleanup())

describe('InfoDisclosure', () => {
  it('renders the explanation in a portal so card overflow cannot clip it', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <div className="overflow-hidden">
        <InfoDisclosure label="Confidence">Confidence description.</InfoDisclosure>
      </div>
    )

    await user.click(screen.getByRole('button', { name: 'About Confidence' }))
    const explanation = screen.getByRole('region', { name: 'Confidence explanation' })

    expect(explanation.parentElement).toBe(document.body)
    expect(explanation).not.toBe(container.querySelector('[role="region"]'))
    expect(explanation).toHaveClass('normal-case', 'tracking-normal')
  })

  it('opens with keyboard activation and exposes the explanation to assistive technology', async () => {
    const user = userEvent.setup()
    render(
      <InfoDisclosure label="Confidence">
        Confidence describes support for the predicted classification, not attack severity.
      </InfoDisclosure>
    )

    const control = screen.getByRole('button', { name: 'About Confidence' })
    expect(control).toHaveAttribute('aria-expanded', 'false')

    control.focus()
    await user.keyboard('{Enter}')

    expect(control).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('region', { name: 'Confidence explanation' })).toHaveTextContent(/not attack severity/i)

    await user.keyboard('{Escape}')
    expect(control).toHaveAttribute('aria-expanded', 'false')
    expect(control).toHaveFocus()
  })

  it('closes on an outside pointer interaction', async () => {
    const user = userEvent.setup()
    render(
      <>
        <InfoDisclosure label="Recorded action">Stored label only.</InfoDisclosure>
        <button type="button">Other control</button>
      </>
    )

    await user.click(screen.getByRole('button', { name: 'About Recorded action' }))
    expect(screen.getByRole('region', { name: 'Recorded action explanation' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Other control' }))

    expect(screen.queryByRole('region', { name: 'Recorded action explanation' })).not.toBeInTheDocument()
  })

  it('closes a portaled explanation when its containing disclosure collapses', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <details open>
        <summary>Breakdown</summary>
        <InfoDisclosure label="Confidence">Confidence description.</InfoDisclosure>
      </details>
    )
    const disclosure = container.querySelector('details')
    const trigger = screen.getByRole('button', { name: 'About Confidence' })

    await user.click(trigger)
    expect(screen.getByRole('region', { name: 'Confidence explanation' })).toBeInTheDocument()

    await user.click(screen.getByText('Breakdown'))

    expect(disclosure?.open).toBe(false)
    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Confidence explanation' })).not.toBeInTheDocument()
    })
    expect(trigger).not.toHaveFocus()
  })

  it('places and clamps explanations at all viewport edges', () => {
    const popover = { left: 0, right: 300, top: 0, bottom: 200, width: 300, height: 200 }
    const bottom = getInfoPopoverPosition(
      { left: 0, right: 20, top: 200, bottom: 220, width: 20, height: 20 }, popover, 400, 800
    )
    const top = getInfoPopoverPosition(
      { left: 340, right: 360, top: 700, bottom: 720, width: 20, height: 20 }, popover, 400, 800
    )
    const right = getInfoPopoverPosition(
      { left: 20, right: 40, top: 240, bottom: 260, width: 20, height: 20 },
      { ...popover, width: 180, height: 400, right: 180, bottom: 400 }, 400, 500
    )
    const left = getInfoPopoverPosition(
      { left: 360, right: 380, top: 240, bottom: 260, width: 20, height: 20 },
      { ...popover, width: 180, height: 400, right: 180, bottom: 400 }, 400, 500
    )

    expect(bottom).toMatchObject({ side: 'bottom', left: 12 })
    expect(top).toMatchObject({ side: 'top', left: 88 })
    expect(right).toMatchObject({ side: 'right', left: 48 })
    expect(left).toMatchObject({ side: 'left', left: 172 })
    for (const [position, width, height, viewportHeight] of [
      [bottom, 300, 200, 800],
      [top, 300, 200, 800],
      [right, 180, 400, 500],
      [left, 180, 400, 500],
    ] as const) {
      expect(position.left).toBeGreaterThanOrEqual(12)
      expect(position.left + width).toBeLessThanOrEqual(388)
      expect(position.top).toBeGreaterThanOrEqual(12)
      expect(position.top + Math.min(height, position.maxHeight)).toBeLessThanOrEqual(viewportHeight - 12)
    }
  })
})
