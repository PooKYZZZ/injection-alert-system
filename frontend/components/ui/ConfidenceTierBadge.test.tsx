import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceTierBadge } from './ConfidenceTierBadge'

afterEach(() => {
  cleanup()
})

describe('ConfidenceTierBadge', () => {
  it.each(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const)(
    'renders canonical %s tier for Normal predictions',
    (confidenceTier) => {
      render(<ConfidenceTierBadge confidenceTier={confidenceTier} prediction="Normal" />)

      expect(screen.getByText(confidenceTier)).toBeInTheDocument()
      expect(screen.queryByText('Benign')).not.toBeInTheDocument()
    }
  )

  it('renders CRITICAL confidence tiers with the existing high-risk styling', () => {
    render(<ConfidenceTierBadge confidenceTier="CRITICAL" prediction="SQL Injection" />)

    const badge = screen.getByText('CRITICAL')
    expect(badge).toHaveClass('text-severity-high-text')
    expect(badge).toHaveClass('border-severity-high-border/30')
  })
})
