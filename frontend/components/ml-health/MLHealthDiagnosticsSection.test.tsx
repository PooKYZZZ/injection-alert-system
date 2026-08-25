import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { MLHealthData } from '@/features/ml-health/types'
import { buildMLHealthViewModel } from './MLHealthWorkspaceViewModel'
import { MLHealthDiagnosticsSection } from './MLHealthDiagnosticsSection'

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

describe('MLHealthDiagnosticsSection', () => {
  it('exposes the active diagnostic tab and a named table with scroll guidance', () => {
    render(
      <MLHealthDiagnosticsSection
        health={health}
        viewModel={buildMLHealthViewModel(health)}
      />
    )

    const performance = screen.getByRole('button', { name: 'Performance' })
    const drift = screen.getByRole('button', { name: 'Drift' })

    expect(performance).toHaveAttribute('aria-pressed', 'true')
    expect(drift).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('table', { name: 'Performance snapshot' })).toBeInTheDocument()
    expect(screen.getByText(/scroll horizontally to view all columns/i)).toBeInTheDocument()

    fireEvent.click(drift)

    expect(performance).toHaveAttribute('aria-pressed', 'false')
    expect(drift).toHaveAttribute('aria-pressed', 'true')
  })
})
