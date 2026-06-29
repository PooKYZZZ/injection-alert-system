import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceThresholds } from './ConfidenceThresholds'

afterEach(() => {
  cleanup()
})

describe('ConfidenceThresholds', () => {
  it('renders configured non-Normal policy boundaries and the Normal exception', () => {
    render(
      <ConfidenceThresholds
        thresholds={{ low: 0.4, medium: 0.55, high: 0.7, critical: 0.85 }}
      />
    )

    expect(screen.getByText('Low <40%')).toBeInTheDocument()
    expect(screen.getByText('Medium 40%–70%')).toBeInTheDocument()
    expect(screen.getByText('High >70%–<85%')).toBeInTheDocument()
    expect(screen.getByText('Critical >=85%')).toBeInTheDocument()
    expect(screen.getByText(/non-Normal enforcement policy/i)).toBeInTheDocument()
    expect(
      screen.getByText('Normal predictions remain allowed for all valid confidence tiers.')
    ).toBeInTheDocument()
    expect(screen.queryByText('How ML confidence maps to enforcement actions')).not.toBeInTheDocument()
    expect(screen.queryByText(/90%|80%|50%/)).not.toBeInTheDocument()
  })
})
