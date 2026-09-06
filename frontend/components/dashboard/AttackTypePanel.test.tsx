import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AttackTypePanel } from './AttackTypePanel'

vi.mock('recharts', () => ({
  Cell: () => null,
  Pie: ({ data }: { data: Array<{ label: string; count: number }> }) => (
    <div data-testid="pie-data">
      {data.map(({ label, count }) => `${label}:${count}`).join('|')}
    </div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ResponsiveContainer: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="responsive-container" data-props={JSON.stringify(props)}>{children}</div>
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
    expect(screen.getByText('4 · 67%')).toBeInTheDocument()
    expect(screen.getByTestId('pie-tooltip-style')).toHaveAttribute(
      'data-background',
      'var(--color-surface-card)'
    )
    expect(JSON.parse(screen.getByTestId('responsive-container').getAttribute('data-props') ?? '{}')).toMatchObject({
      width: '100%',
      height: '100%',
      minHeight: 196,
      initialDimension: { width: 0, height: 196 },
    })
  })
})
