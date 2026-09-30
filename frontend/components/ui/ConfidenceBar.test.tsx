import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceBar } from './ConfidenceBar'

afterEach(() => {
  cleanup()
})

describe('ConfidenceBar', () => {
  it.each([
    [0.8, 'MEDIUM', '80%', 'text-severity-blocked-text'],
    [0.95, 'MEDIUM', '95%', 'text-severity-blocked-text'],
    [0.7, 'CRITICAL', '70%', 'text-severity-high-text'],
    [0.39, 'LOW', '39%', 'text-severity-safe-text'],
    [0, 'INFORMATIONAL', '0%', 'text-text-secondary'],
  ] as const)(
    'styles %s using backend tier %s',
    (confidence, confidenceTier, expectedText, expectedClass) => {
      render(
        <ConfidenceBar
          confidence={confidence}
          confidenceTier={confidenceTier}
          prediction="SQL Injection"
        />
      )

      expect(screen.getByText(expectedText)).toHaveClass(expectedClass)
    }
  )

  it('preserves useful precision for very high confidence values', () => {
    render(
      <ConfidenceBar
        confidence={0.999999}
        confidenceTier="CRITICAL"
        prediction="SQL Injection"
      />
    )

    expect(screen.getByText('99.9999%')).toBeInTheDocument()
  })

  it('uses the unrounded score when deriving a missing tier', () => {
    render(
      <ConfidenceBar
        confidence={0.3999}
        prediction="SQL Injection"
      />
    )

    expect(screen.getByText('39.99%')).toHaveClass('text-severity-safe-text')
  })
})
