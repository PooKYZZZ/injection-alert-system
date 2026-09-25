import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionLabel } from './ActionLabel'

afterEach(() => {
  cleanup()
})

describe('ActionLabel', () => {
  it('labels LOW allowed actionable attacks as monitor-only', () => {
    for (const prediction of ['SQL Injection', 'Code Injection'] as const) {
      const { unmount } = render(
        <ActionLabel action="ALLOWED" confidenceTier="LOW" prediction={prediction} />
      )

      expect(screen.getByText('Monitor Only')).toBeInTheDocument()
      unmount()
    }
  })

  it('keeps Normal, out-of-scope, and non-LOW allowed outcomes as allowed', () => {
    const cases = [
      { confidenceTier: 'LOW', prediction: 'Normal' },
      { confidenceTier: 'LOW', prediction: 'Other Attacks' },
      { confidenceTier: 'MEDIUM', prediction: 'SQL Injection' },
    ] as const

    for (const props of cases) {
      const { unmount } = render(<ActionLabel action="ALLOWED" {...props} />)

      expect(screen.getByText('Allowed')).toBeInTheDocument()
      expect(screen.queryByText('Monitor Only')).not.toBeInTheDocument()
      unmount()
    }
  })
})
