import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('uses quiet metric chrome inside the shared summary strip', () => {
    render(<StatCard label="Total requests" value={4200} />)

    const labelEl = screen.getByText('Total requests')
    const card = labelEl.closest('div')?.parentElement

    expect(card).not.toBeNull()
    expect(card).toHaveClass('p-3')
    expect(card).not.toHaveClass('rounded-xl')
    expect(card).not.toHaveClass('border')
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
    expect(valueEl).toHaveClass('text-severity-high-text')
    expect(valueEl).not.toHaveClass('text-severity-safe-text')
    expect(screen.getByText('↑ 20 vs prev')).toHaveClass('text-severity-high-text/80')
  })

  it('allows long metric labels to shrink inside responsive grids', () => {
    render(<StatCard label="Allowed non-Normal prediction rate (proxy)" value="—" />)

    const labelEl = screen.getByText('Allowed non-Normal prediction rate (proxy)')
    const card = labelEl.closest('div')?.parentElement

    expect(card).toHaveClass('min-w-0')
  })
})
