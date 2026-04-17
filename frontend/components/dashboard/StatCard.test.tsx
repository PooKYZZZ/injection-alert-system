import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('uses set1 card surface token for dashboard stat chrome', () => {
    render(<StatCard label="Total requests" value={4200} />)

    const labelEl = screen.getByText('Total requests')
    const card = labelEl.closest('div')?.parentElement

    expect(card).not.toBeNull()
    expect(card).toHaveClass('bg-surface-card')
  })

  it('uses semantic danger colors for an unfavorable delta', () => {
    render(
      <StatCard
        label="Blocked"
        value={120}
        previousValue={100}
      />
    )

    const labelEl = screen.getByText('Blocked')
    const valueEl = labelEl.nextElementSibling as HTMLElement | null

    expect(valueEl).not.toBeNull()
    expect(valueEl).toHaveClass('text-[var(--color-delta-bad)]')
    expect(valueEl).not.toHaveClass('text-[var(--color-delta-good)]')
    expect(screen.getByText('↑ 20 vs prev')).toHaveClass('text-[var(--color-delta-bad)]')
  })
})
