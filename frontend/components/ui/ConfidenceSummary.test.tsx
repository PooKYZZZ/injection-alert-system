import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceSummary } from './ConfidenceSummary'

afterEach(() => {
  cleanup()
})

describe('ConfidenceSummary', () => {
  it.each([
    [0.8, 'MEDIUM', '80.00% · MEDIUM'],
    [0.95, 'MEDIUM', '95.00% · MEDIUM'],
    [0.7, 'CRITICAL', '70.00% · CRITICAL'],
    [0.39, 'LOW', '39.00% · LOW'],
    [0, 'INFORMATIONAL', '0.00% · INFORMATIONAL'],
  ] as const)(
    'presents %s using backend tier %s without severity coloring',
    (confidence, confidenceTier, expectedLabel) => {
      const { container } = render(
        <ConfidenceSummary
          confidence={confidence}
          confidenceTier={confidenceTier}
        />
      )

      expect(screen.getByRole('group', { name: `Confidence ${expectedLabel}` })).toBeInTheDocument()
      expect(screen.getByText(confidenceTier)).toHaveClass('text-text-secondary', 'bg-surface-inset')
      expect(screen.getByText(expectedLabel.split(' · ')[0])).toHaveClass('text-text-primary')
      expect(container.querySelector('.bg-accent-analytic')).not.toBeInTheDocument()
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    }
  )

  it('shows compact confidence precision and the canonical tier', () => {
    render(
      <ConfidenceSummary
        confidence={0.999999}
        confidenceTier="CRITICAL"
      />
    )

    expect(screen.getByRole('group', { name: 'Confidence 100.00% · CRITICAL' })).toBeInTheDocument()
  })

  it('uses the unrounded score when deriving a missing tier', () => {
    render(
      <ConfidenceSummary
        confidence={0.3999}
      />
    )

    expect(screen.getByRole('group', { name: 'Confidence 39.99% · LOW' })).toBeInTheDocument()
    expect(screen.getByText('LOW')).toHaveClass('text-text-secondary', 'bg-surface-inset')
  })
})
