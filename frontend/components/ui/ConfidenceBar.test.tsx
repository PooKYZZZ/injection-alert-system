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
    [0.49, 'LOW', '49%', 'text-severity-safe-text'],
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
})
