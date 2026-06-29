import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MLConfidenceBands } from './MLConfidenceBands'

afterEach(() => {
  cleanup()
})

describe('MLConfidenceBands', () => {
  it('labels backend-emitted tiers without hard-coded threshold ranges', () => {
    render(<MLConfidenceBands critical={1} high={2} medium={3} low={4} />)

    expect(screen.getByText('Critical confidence tier')).toBeInTheDocument()
    expect(screen.getByText('High confidence tier')).toBeInTheDocument()
    expect(screen.getByText('Medium confidence tier')).toBeInTheDocument()
    expect(screen.getByText('Low confidence tier')).toBeInTheDocument()
    expect(screen.queryByText(/90%|80%|50%/)).not.toBeInTheDocument()
  })
})
