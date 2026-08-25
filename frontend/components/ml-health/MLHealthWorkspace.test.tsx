import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MLHealthWorkspace', () => {
  it('leads with the serving answer and exposes the selected top-level view', () => {
    render(<MLHealthWorkspace />)

    expect(screen.getByRole('heading', { name: 'Serving' })).toBeInTheDocument()
    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('Active model')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Monitoring coverage' })).toBeInTheDocument()
    expect(screen.getByText('Incomplete')).toBeInTheDocument()
    expect(screen.queryByText('Inference endpoint')).not.toBeInTheDocument()
    expect(screen.getByLabelText('ML health snapshot freshness')).toHaveTextContent('Source timestamp unavailable')
    expect(screen.getByLabelText('ML health snapshot freshness')).not.toHaveTextContent('Snapshot ·')
    expect(screen.getByRole('link', { name: 'Open Model Operations' })).toHaveAttribute('href', '/ml-model')

    const overview = screen.getByRole('tab', { name: 'Overview' })
    const diagnostics = screen.getByRole('tab', { name: 'Diagnostics' })

    expect(overview).toHaveAttribute('role', 'tab')
    expect(overview).toHaveAttribute('aria-selected', 'true')
    expect(diagnostics).toHaveAttribute('aria-selected', 'false')

    fireEvent.click(diagnostics)

    expect(overview).toHaveAttribute('aria-selected', 'false')
    expect(diagnostics).toHaveAttribute('aria-selected', 'true')
  })

  it('uses overview evidence links to open the owning diagnostic category', () => {
    render(<MLHealthWorkspace />)

    fireEvent.click(screen.getByRole('button', { name: 'Open Model evaluation diagnostics' }))

    expect(screen.getByRole('tab', { name: 'Diagnostics' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Evaluation' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: 'Model evaluation' })).toBeInTheDocument()
  })

  it('supports keyboard navigation across top-level views', () => {
    render(<MLHealthWorkspace />)

    const overview = screen.getByRole('tab', { name: 'Overview' })
    const diagnostics = screen.getByRole('tab', { name: 'Diagnostics' })

    overview.focus()
    fireEvent.keyDown(overview, { key: 'ArrowRight' })

    expect(diagnostics).toHaveAttribute('aria-selected', 'true')
    expect(diagnostics).toHaveAttribute('tabindex', '0')
    expect(document.activeElement).toBe(diagnostics)
  })

  it('keeps unavailable monitoring explicit and supports refreshing the snapshot', () => {
    const refetch = vi.fn()
    mockedUseMLHealth.mockReturnValue({
      data: health,
      isPending: false,
      isFetching: false,
      isError: false,
      refetch,
    } as never)

    render(<MLHealthWorkspace />)

    expect(screen.getAllByText('Not reported').length).toBeGreaterThan(0)
    expect(screen.getByText(/No drift result was included/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /refresh ml health/i }))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('shows refresh progress without replacing the last successful snapshot', () => {
    mockedUseMLHealth.mockReturnValue({
      data: health,
      isPending: false,
      isFetching: true,
      isError: false,
      refetch: vi.fn(),
    } as never)

    render(<MLHealthWorkspace />)

    expect(screen.getByRole('button', { name: /refreshing ml health/i })).toBeDisabled()
    expect(screen.getAllByRole('heading', { name: 'Serving' }).length).toBeGreaterThan(0)
  })
})
