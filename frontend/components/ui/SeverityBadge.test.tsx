import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { SeverityBadge } from './SeverityBadge'

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
    expect(benignBadge).toHaveClass('border-border-light')
    expect(screen.queryByText('HIGH')).not.toBeInTheDocument()
  })

  it('keeps confidence-level label for non-Normal predictions', () => {
    render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })
})
