import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionLabel } from './ActionLabel'

afterEach(() => {
  cleanup()
})

describe('ActionLabel', () => {
  it('labels a LOW ALLOWED outcome as monitor-only', () => {
    render(<ActionLabel action="ALLOWED" confidenceTier="LOW" />)

    expect(screen.getByText('Monitor Only')).toBeInTheDocument()
    expect(screen.queryByText('Allowed')).not.toBeInTheDocument()
  })

  it('keeps non-LOW ALLOWED outcomes as allowed', () => {
    render(<ActionLabel action="ALLOWED" confidenceTier="HIGH" />)

    expect(screen.getByText('Allowed')).toBeInTheDocument()
    expect(screen.queryByText('Monitor Only')).not.toBeInTheDocument()
  })
})
