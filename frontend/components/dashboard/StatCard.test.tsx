import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatCard } from './StatCard'

describe('StatCard', () => {
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
