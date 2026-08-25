import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MLHealthData } from '@/features/ml-health/types'
import { useMLHealth } from '@/features/ml-health/queries'
import { MLHealthWorkspace } from './MLHealthWorkspace'

vi.mock('@/features/ml-health/queries', () => ({
  useMLHealth: vi.fn(),
}))

const mockedUseMLHealth = vi.mocked(useMLHealth)

const health: MLHealthData = {
  model_version: 'distilbert_cleaned_120k_20260324',
  status: 'HEALTHY',
  latency_ms: 12.4,
  latency_trend: null,
  drift_score: null,
  drift_status: null,
  traffic_processed: 0,
  thresholds: { low: 0.5, medium: 0.65, high: 0.8, critical: 0.9 },
}

beforeEach(() => {
  mockedUseMLHealth.mockReturnValue({
    data: health,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as never)
})

describe('MLHealthWorkspace', () => {
  it('exposes the selected top-level view to assistive technology', () => {
    render(<MLHealthWorkspace />)

    const overview = screen.getByRole('button', { name: 'Overview' })
    const diagnostics = screen.getByRole('button', { name: 'Diagnostics' })

    expect(overview).toHaveAttribute('aria-pressed', 'true')
    expect(diagnostics).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(diagnostics)

    expect(overview).toHaveAttribute('aria-pressed', 'false')
    expect(diagnostics).toHaveAttribute('aria-pressed', 'true')
  })

  it('associates overview table headers with their columns', () => {
    render(<MLHealthWorkspace />)

    expect(screen.getAllByRole('columnheader').every((header) => header.getAttribute('scope') === 'col')).toBe(true)
  })
})
