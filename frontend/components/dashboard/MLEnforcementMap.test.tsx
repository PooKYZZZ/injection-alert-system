import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MLEnforcementMap } from './MLEnforcementMap'

afterEach(() => {
  cleanup()
})

describe('MLEnforcementMap', () => {
  it('renders an explicit non-Normal count contract and all policy actions', () => {
    render(
      <MLEnforcementMap
        nonNormalCounts={{ critical: 4, high: 3, medium: 2, low: 1 }}
      />
    )

    expect(screen.getByText('Action policy for non-Normal predictions')).toBeInTheDocument()
    expect(
      screen.getByText('Normal predictions remain ALLOWED for all valid confidence tiers.')
    ).toBeInTheDocument()
    const criticalRow = screen.getByText('CRITICAL non-Normal').closest('div')?.parentElement
    const highRow = screen.getByText('HIGH non-Normal').closest('div')?.parentElement
    const mediumRow = screen.getByText('MEDIUM non-Normal').closest('div')?.parentElement
    const lowRow = screen.getByText('LOW non-Normal').closest('div')?.parentElement
    expect(criticalRow).not.toBeNull()
    expect(highRow).not.toBeNull()
    expect(mediumRow).not.toBeNull()
    expect(lowRow).not.toBeNull()
    expect(within(criticalRow as HTMLElement).getByText('BLOCKED')).toBeInTheDocument()
    expect(within(highRow as HTMLElement).getByText('BLOCKED')).toBeInTheDocument()
    expect(within(mediumRow as HTMLElement).getByText('THROTTLED')).toBeInTheDocument()
    expect(within(lowRow as HTMLElement).getByText('ALLOWED')).toBeInTheDocument()
    expect(screen.queryByText(/strictly bound/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/CRITICAL always BLOCKED/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/CRITICAL confidence always maps to BLOCKED/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/action_taken=CRITICAL/i)).not.toBeInTheDocument()
  })
})
