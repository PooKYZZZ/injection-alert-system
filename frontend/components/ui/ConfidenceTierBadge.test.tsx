import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceTierBadge } from './ConfidenceTierBadge'

afterEach(() => {
  cleanup()
})

describe('ConfidenceTierBadge', () => {
  it('renders CRITICAL confidence tiers with the existing high-risk styling', () => {
    render(<ConfidenceTierBadge confidenceTier="CRITICAL" prediction="SQL Injection" />)

    const badge = screen.getByText('CRITICAL')
    expect(badge).toHaveClass('text-severity-high-text')
    expect(badge).toHaveClass('border-severity-high-border/30')
  })
})
