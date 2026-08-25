import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { MLHealthData } from '@/features/ml-health/types'
import { buildMLHealthViewModel } from './MLHealthWorkspaceViewModel'
import { MLHealthDiagnosticsSection } from './MLHealthDiagnosticsSection'

afterEach(cleanup)

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

    const performance = screen.getByRole('tab', { name: 'Performance' })
    const drift = screen.getByRole('tab', { name: 'Drift' })

    expect(performance).toHaveAttribute('role', 'tab')
    expect(performance).toHaveAttribute('aria-selected', 'true')
    expect(drift).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByRole('table', { name: 'Performance snapshot' })).toBeInTheDocument()
    expect(screen.getByText(/scroll horizontally to view all columns/i)).toBeInTheDocument()

    fireEvent.click(drift)

    expect(performance).toHaveAttribute('aria-selected', 'false')
    expect(drift).toHaveAttribute('aria-selected', 'true')
  })

  it('supports roving focus and automatic activation for diagnostic tabs', () => {
    render(
      <MLHealthDiagnosticsSection
        health={health}
        viewModel={buildMLHealthViewModel(health)}
      />
    )

    const performance = screen.getByRole('tab', { name: 'Performance' })
    const drift = screen.getByRole('tab', { name: 'Drift' })
    const policy = screen.getByRole('tab', { name: 'Policy' })

    expect(performance).toHaveAttribute('tabindex', '0')
    expect(drift).toHaveAttribute('tabindex', '-1')

    performance.focus()
    fireEvent.keyDown(performance, { key: 'ArrowRight' })

    expect(drift).toHaveAttribute('aria-selected', 'true')
    expect(drift).toHaveAttribute('tabindex', '0')
    expect(document.activeElement).toBe(drift)

    fireEvent.keyDown(drift, { key: 'End' })

    expect(policy).toHaveAttribute('aria-selected', 'true')
    expect(document.activeElement).toBe(policy)
  })
})
