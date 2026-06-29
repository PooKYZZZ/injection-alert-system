import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ConfidenceThresholds } from './ConfidenceThresholds'

afterEach(() => {
  cleanup()
})

describe('ConfidenceThresholds', () => {
  it('renders explicit non-overlapping confidence boundaries', () => {
    render(
      <ConfidenceThresholds
        thresholds={{ low: 0.5, medium: 0.65, high: 0.8, critical: 0.9 }}
      />
    )

    expect(screen.getByText('Low <50%')).toBeInTheDocument()
    expect(screen.getByText('Medium 50%–80%')).toBeInTheDocument()
    expect(screen.getByText('High >80%–<90%')).toBeInTheDocument()
    expect(screen.getByText('Critical >=90%')).toBeInTheDocument()
    expect(screen.queryByText(/High 80%/)).not.toBeInTheDocument()
  })
})
