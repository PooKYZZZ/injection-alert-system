import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MLConfidenceBands } from './MLConfidenceBands'

afterEach(() => {
  cleanup()
})

describe('MLConfidenceBands', () => {
  it('renders explicit non-overlapping confidence boundaries', () => {
    render(<MLConfidenceBands critical={1} high={2} medium={3} low={4} />)

    expect(screen.getByText('Critical >=90%')).toBeInTheDocument()
    expect(screen.getByText('High >80%–<90%')).toBeInTheDocument()
    expect(screen.getByText('Medium 50%–80%')).toBeInTheDocument()
    expect(screen.getByText('Low <50%')).toBeInTheDocument()
    expect(screen.queryByText(/High 80/)).not.toBeInTheDocument()
  })
})
