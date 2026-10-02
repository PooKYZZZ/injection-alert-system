import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TrafficSimulation } from './TrafficSimulation'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('TrafficSimulation', () => {
  it('lets visitors compare fixed request examples without sending a request', () => {
    render(<TrafficSimulation />)

    expect(screen.getByRole('group', { name: 'Sample request scenarios' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Prepared request preview' })).toBeInTheDocument()
    expect(screen.getByText('GET /catalog/search?q=%27%20OR%20%271%27%3D%271')).toBeInTheDocument()
    expect(screen.getByText('Prepared for this walkthrough · never transmitted')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Ordinary search/ }))

    expect(screen.getByText('GET /catalog/search?q=blue+shoes')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ordinary search/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByRole('button', { name: /Open Traffic Details/ })).not.toBeInTheDocument()
  })

  it('allows stage inspection and supports pause, continue, and reset', () => {
    vi.useFakeTimers()
    render(<TrafficSimulation />)

    fireEvent.click(screen.getByRole('button', { name: /Code injection pattern/ }))
    const wafStep = screen.getByRole('button', { name: /WAF/ })
    fireEvent.click(wafStep)
    expect(screen.getByRole('heading', { name: 'Firewall evidence' })).toBeInTheDocument()
    expect(screen.getByText(/no linked firewall finding/i)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Ready.')

    fireEvent.keyDown(wafStep, { key: 'ArrowRight' })
    const modelStep = screen.getByRole('button', { name: /ML/ })
    expect(modelStep).toHaveFocus()
    expect(screen.getByRole('heading', { name: 'Model suggestion' })).toBeInTheDocument()
    fireEvent.keyDown(modelStep, { key: 'ArrowLeft' })
    expect(wafStep).toHaveFocus()

    fireEvent.click(screen.getByRole('button', { name: 'Start walkthrough' }))
    expect(screen.getByRole('status')).toHaveTextContent('Step 1 of 6')

    fireEvent.click(screen.getByRole('button', { name: 'Pause walkthrough' }))
    expect(screen.getByRole('status')).toHaveTextContent('Paused at step 1 of 6')

    fireEvent.click(screen.getByRole('button', { name: 'Resume walkthrough' }))
    act(() => vi.advanceTimersByTime(1050))
    expect(screen.getByRole('status')).toHaveTextContent('Step 2 of 6')

    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(screen.getByRole('status')).toHaveTextContent('Ready.')
    expect(screen.queryByRole('button', { name: /Open Traffic Details/ })).not.toBeInTheDocument()
  })

  it('opens synthetic Traffic Details and keeps the analyst triage state local', () => {
    vi.useFakeTimers()
    render(<TrafficSimulation />)

    fireEvent.click(screen.getByRole('button', { name: 'Start walkthrough' }))
    for (let step = 0; step < 5; step += 1) {
      act(() => vi.advanceTimersByTime(1050))
    }

    fireEvent.click(screen.getByRole('button', { name: /Open Traffic Details/ }))
    const dialog = screen.getByRole('dialog')

    expect(within(dialog).getByText('Observed HTTP status')).toBeInTheDocument()
    expect(within(dialog).getByText('Not established by this demo')).toBeInTheDocument()
    expect(within(dialog).getByText(/fictional linked CRS finding/)).toBeInTheDocument()

    const reviewState = within(dialog).getByRole('combobox', { name: 'Sample review state' })
    expect(reviewState).toBeEnabled()
    fireEvent.change(reviewState, { target: { value: 'resolved' } })
    expect(reviewState).toHaveValue('resolved')
    expect(within(dialog).getByText(/not sent to CyberTrace/)).toBeInTheDocument()
  })

  it('keeps Normal traffic read-only in the sample review flow', () => {
    vi.useFakeTimers()
    render(<TrafficSimulation />)
    fireEvent.click(screen.getByRole('button', { name: /Ordinary search/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Start walkthrough' }))
    for (let step = 0; step < 5; step += 1) {
      act(() => vi.advanceTimersByTime(1050))
    }

    fireEvent.click(screen.getByRole('button', { name: /Open Traffic Details/ }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('Normal traffic remains read-only and does not use the security triage workflow.')).toBeInTheDocument()
    expect(within(dialog).getByText('Read-only sample')).toBeInTheDocument()
    expect(within(dialog).queryByRole('combobox', { name: 'Sample review state' })).not.toBeInTheDocument()
  })
})
