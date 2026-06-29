import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ConfidenceTierBadge } from './ConfidenceTierBadge'
import { SeverityBadge } from './SeverityBadge'
import { FilterChip } from './FilterChip'

afterEach(() => {
  cleanup()
})

describe('SeverityBadge', () => {
  it('exports the preferred ConfidenceTierBadge name with matching confidence-tier labels', () => {
    render(<ConfidenceTierBadge confidenceTier="HIGH" prediction="SQL Injection" />)

    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('maps severity labels to semantic token classes', () => {
    const { rerender } = render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    const highBadge = screen.getByText('HIGH')
    expect(highBadge).toHaveClass('text-severity-high-text')
    expect(highBadge).toHaveClass('border-severity-high-border/30')

    rerender(<SeverityBadge severity="CRITICAL" prediction="SQL Injection" />)
    const criticalBadge = screen.getByText('CRITICAL')
    expect(criticalBadge).toHaveClass('text-severity-high-text')
    expect(criticalBadge).toHaveClass('border-severity-high-border/30')

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

  it('preserves the canonical CRITICAL tier for Normal predictions', () => {
    render(<SeverityBadge severity="CRITICAL" prediction="Normal" />)

    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
    expect(screen.queryByText('Benign')).not.toBeInTheDocument()
  })

  it('keeps confidence-level label for non-Normal predictions', () => {
    render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('uses confidence-tier props under the preferred component name', () => {
    render(<ConfidenceTierBadge confidenceTier="MEDIUM" prediction="Code Injection" />)

    expect(screen.getByText('MEDIUM')).toHaveClass('text-severity-blocked-text')
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
