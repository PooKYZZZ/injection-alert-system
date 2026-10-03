import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatCard } from './StatCard'
import userEvent from '@testing-library/user-event'

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

  it('keeps volume deltas neutral so an increase does not imply severity', () => {
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
    expect(valueEl).toHaveClass('text-text-primary')
    expect(valueEl).not.toHaveClass('text-severity-high-text')
    expect(valueEl).not.toHaveClass('text-severity-safe-text')
    expect(screen.getByText('↑ 20 vs previous').closest('div')).toHaveClass('text-text-muted')
  })

  it('explains the equal-duration comparison and absolute delta', async () => {
    const user = userEvent.setup()
    render(<StatCard label="Recorded throttled" value={15} previousValue={10} />)

    const help = screen.getByRole('button', { name: 'About Recorded throttled change vs previous' })
    expect(help).toBeInTheDocument()
    await user.click(help)

    const explanation = screen.getByRole('region', { name: 'Recorded throttled change vs previous explanation' })
    expect(explanation).toHaveTextContent(/immediately preceding window of the same length/i)
    expect(explanation).toHaveTextContent(/absolute difference, not a percentage/i)
    expect(explanation).toHaveTextContent(/measure of whether activity improved/i)
  })

  it('allows long metric labels to shrink inside responsive grids', () => {
    render(<StatCard label="Allowed actionable attack rate (proxy)" value="—" />)

    const labelEl = screen.getByText('Allowed actionable attack rate (proxy)')
    const card = labelEl.closest('div')?.parentElement

    expect(card).toHaveClass('min-w-0')
  })

  it('provides keyboard-operable help for a technical metric', async () => {
    const user = userEvent.setup()
    render(
      <StatCard
        label="Traffic records"
        info="Counts stored rows, not unique requests."
        value={42}
      />
    )

    const control = screen.getByRole('button', { name: 'About Traffic records' })
    control.focus()
    await user.keyboard('{Enter}')

    expect(screen.getByRole('region', { name: 'Traffic records explanation' })).toHaveTextContent('not unique requests')
  })
})
