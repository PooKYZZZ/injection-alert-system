import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SeverityBadge } from './SeverityBadge'
import { FilterChip } from './FilterChip'

afterEach(() => {
  cleanup()
})

describe('SeverityBadge', () => {
  it('maps severity labels to semantic token classes', () => {
    const { rerender } = render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    const highBadge = screen.getByText('HIGH')
    expect(highBadge).toHaveClass('text-severity-high-text')
    expect(highBadge).toHaveClass('border-severity-high-border/30')

    rerender(<SeverityBadge severity="MEDIUM" prediction="Code Injection" />)
    const mediumBadge = screen.getByText('MEDIUM')
    expect(mediumBadge).toHaveClass('text-severity-blocked-text')
    expect(mediumBadge).toHaveClass('border-severity-blocked-border/30')
    expect(mediumBadge).not.toHaveClass('text-accent-action')

    rerender(<SeverityBadge severity="LOW" prediction="Other Attacks" />)
    const lowBadge = screen.getByText('LOW')
    expect(lowBadge).toHaveClass('text-severity-safe-text')
    expect(lowBadge).toHaveClass('border-severity-safe-border/30')
  })

  it('renders Benign when prediction is Normal even if confidence level is HIGH', () => {
    render(<SeverityBadge severity="HIGH" prediction="Normal" />)

    const benignBadge = screen.getByText('Benign')

    expect(benignBadge).toBeInTheDocument()
    expect(benignBadge).toHaveClass('text-text-secondary')
    expect(benignBadge).toHaveClass('border-surface-border')
    expect(screen.queryByText('HIGH')).not.toBeInTheDocument()
  })

  it('keeps confidence-level label for non-Normal predictions', () => {
    render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('uses bronze emphasis on filter chips only when selected', () => {
    const onClick = vi.fn()
    const { rerender } = render(<FilterChip label="Blocked" active={false} onClick={onClick} />)

    const inactiveChip = screen.getByRole('button', { name: /blocked/i })
    expect(inactiveChip).not.toHaveClass('text-accent-action')
    expect(inactiveChip).not.toHaveClass('border-accent-action')

    rerender(<FilterChip label="Blocked" active={true} onClick={onClick} />)

    const activeChip = screen.getByRole('button', { name: /blocked/i })
    expect(activeChip).toHaveClass('text-accent-action')
    expect(activeChip).toHaveClass('border-accent-action')
  })
})
