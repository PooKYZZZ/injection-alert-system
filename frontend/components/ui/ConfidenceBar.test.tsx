import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceBar } from './ConfidenceBar'

afterEach(() => {
  cleanup()
})

describe('ConfidenceBar', () => {
  it.each([
    [0.8, 'MEDIUM', '80.00% · MEDIUM'],
    [0.95, 'MEDIUM', '95.00% · MEDIUM'],
    [0.7, 'CRITICAL', '70.00% · CRITICAL'],
    [0.39, 'LOW', '39.00% · LOW'],
    [0, 'INFORMATIONAL', '0.00% · INFORMATIONAL'],
  ] as const)(
    'presents %s using backend tier %s without severity coloring',
    (confidence, confidenceTier, expectedLabel) => {
      render(
        <ConfidenceBar
          confidence={confidence}
          confidenceTier={confidenceTier}
          prediction="SQL Injection"
        />
      )

      expect(screen.getByRole('group', { name: `Confidence ${expectedLabel}` })).toBeInTheDocument()
      expect(screen.getByText(confidenceTier)).toHaveClass('text-text-secondary', 'bg-surface-inset')
      expect(screen.getByText(expectedLabel.split(' · ')[0])).toHaveClass('text-text-primary')
      expect(screen.getByRole('group', { name: `Confidence ${expectedLabel}` }).querySelector('[aria-hidden="true"] > div')).toHaveClass('bg-accent-analytic')
    }
  )

  it('shows compact confidence precision and the canonical tier', () => {
    render(
      <ConfidenceBar
        confidence={0.999999}
        confidenceTier="CRITICAL"
        prediction="SQL Injection"
      />
    )

    expect(screen.getByRole('group', { name: 'Confidence 100.00% · CRITICAL' })).toBeInTheDocument()
  })

  it('uses the unrounded score when deriving a missing tier', () => {
    render(
      <ConfidenceBar
        confidence={0.3999}
        prediction="SQL Injection"
      />
    )

    expect(screen.getByRole('group', { name: 'Confidence 39.99% · LOW' })).toBeInTheDocument()
    expect(screen.getByText('LOW')).toHaveClass('text-text-secondary', 'bg-surface-inset')
  })
})
