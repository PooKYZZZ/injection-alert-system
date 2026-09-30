import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceBar } from './ConfidenceBar'

afterEach(() => {
  cleanup()
})

describe('ConfidenceBar', () => {
  it.each([
    [0.8, 'MEDIUM', '80.00% · MEDIUM', 'text-severity-blocked-text'],
    [0.95, 'MEDIUM', '95.00% · MEDIUM', 'text-severity-blocked-text'],
    [0.7, 'CRITICAL', '70.00% · CRITICAL', 'text-severity-high-text'],
    [0.39, 'LOW', '39.00% · LOW', 'text-severity-safe-text'],
    [0, 'INFORMATIONAL', '0.00% · INFORMATIONAL', 'text-text-secondary'],
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

  it('shows compact confidence precision and the canonical tier', () => {
    render(
      <ConfidenceBar
        confidence={0.999999}
        confidenceTier="CRITICAL"
        prediction="SQL Injection"
      />
    )

    expect(screen.getByText('100.00% · CRITICAL')).toBeInTheDocument()
  })

  it('uses the unrounded score when deriving a missing tier', () => {
    render(
      <ConfidenceBar
        confidence={0.3999}
        prediction="SQL Injection"
      />
    )

    expect(screen.getByText('39.99% · LOW')).toHaveClass('text-severity-safe-text')
  })
})
