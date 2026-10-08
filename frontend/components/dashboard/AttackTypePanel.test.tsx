import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AttackTypePanel } from './AttackTypePanel'

vi.mock('recharts', () => ({
  Cell: () => null,
  Pie: ({ data, isAnimationActive }: { data: Array<{ label: string; count: number }>; isAnimationActive?: boolean }) => (
    <div data-testid="pie-data" data-animation-active={String(isAnimationActive)}>
      {data.map(({ label, count }) => `${label}:${count}`).join('|')}
    </div>
  ),
  PieChart: ({ children, width, height }: { children: React.ReactNode; width?: number; height?: number }) => (
    <div data-testid="pie-chart" data-width={width} data-height={height}>{children}</div>
  ),
  Tooltip: ({ contentStyle }: { contentStyle?: React.CSSProperties }) => (
    <div data-testid="pie-tooltip-style" data-background={String(contentStyle?.backgroundColor ?? '')} />
  ),
}))

const counts = {
  'SQL Injection': 4,
  'Code Injection': 2,
  'Other Attacks': 1,
  Normal: 3,
} as const

describe('AttackTypePanel', () => {
  afterEach(cleanup)

  it('defaults to bars and switches to the pie view without changing the shared data', async () => {
    const user = userEvent.setup()
    render(<AttackTypePanel countsByLabel={counts} />)

    const barButton = screen.getByRole('button', { name: 'Bar chart' })
    const pieButton = screen.getByRole('button', { name: 'Pie chart' })

    expect(barButton).toHaveAttribute('aria-pressed', 'true')
    expect(pieButton).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('SQL Injection')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /Attack type distribution pie chart/ })).not.toBeInTheDocument()

    await user.click(pieButton)

    expect(barButton).toHaveAttribute('aria-pressed', 'false')
    expect(pieButton).toHaveAttribute('aria-pressed', 'true')
    expect(
      screen.getByRole('img', {
        name: 'Attack type distribution pie chart. SQL Injection: 4 (67%); Code Injection: 2 (33%).',
      })
    ).toBeInTheDocument()
    expect(screen.getByTestId('pie-data')).toHaveTextContent('SQL Injection:4|Code Injection:2')
    expect(screen.getByTestId('pie-data')).toHaveAttribute('data-animation-active', 'false')
    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-width', '196')
    expect(screen.getByTestId('pie-chart')).toHaveAttribute('data-height', '196')
    expect(screen.getByText('4 · 67%')).toBeInTheDocument()
    expect(screen.getByTestId('pie-tooltip-style')).toHaveAttribute(
      'data-background',
      'var(--color-surface-card)'
    )
  })

  it('explains both chart controls as presentation-only changes', async () => {
    const user = userEvent.setup()
    render(<AttackTypePanel countsByLabel={counts} />)

    const barHelp = screen.getByRole('button', { name: 'About Bar chart' })
    const pieHelp = screen.getByRole('button', { name: 'About Pie chart' })
    expect(screen.getAllByRole('button', { name: 'About Bar chart' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'About Pie chart' })).toHaveLength(1)

    await user.click(barHelp)
    expect(screen.getByRole('region', { name: 'Bar chart explanation' })).toHaveTextContent(
      /presentation, not the data or calculation/i
    )
    await user.click(pieHelp)
    expect(screen.getByRole('region', { name: 'Pie chart explanation' })).toHaveTextContent(
      /switching views does not change the data or calculation/i
    )
  })
})
