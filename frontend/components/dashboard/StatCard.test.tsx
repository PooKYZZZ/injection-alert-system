import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('uses red main value color for an unfavorable delta', () => {
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
    expect(valueEl).toHaveClass('text-red-400')
    expect(valueEl).not.toHaveClass('text-emerald-400')
    expect(screen.getByText('↑ 20 vs prev')).toHaveClass('text-red-500/80')
  })
})
