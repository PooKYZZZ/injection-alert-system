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
  it('exposes readable diagnostic categories without leaking source fields', () => {
    render(
      <MLHealthDiagnosticsSection
        health={health}
        viewModel={buildMLHealthViewModel(health)}
      />
    )

    const performance = screen.getByRole('tab', { name: 'Performance' })
    const monitoring = screen.getByRole('tab', { name: 'Monitoring' })

    expect(performance).toHaveAttribute('role', 'tab')
    expect(performance).toHaveAttribute('aria-selected', 'true')
    expect(monitoring).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByRole('table', { name: 'Serving metrics' })).toBeInTheDocument()
    expect(screen.queryByText(/scroll horizontally to view all columns/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/source field/i)).not.toBeInTheDocument()
    expect(screen.getByText('No serving traffic in this snapshot.')).toBeInTheDocument()

    fireEvent.click(monitoring)

    expect(performance).toHaveAttribute('aria-selected', 'false')
    expect(monitoring).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Drift result unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Drift monitoring' })).not.toBeInTheDocument()
    expect(screen.queryByText('Drift coverage', { selector: 'small' })).not.toBeInTheDocument()
  })

  it('supports roving focus and automatic activation for diagnostic tabs', () => {
    render(
      <MLHealthDiagnosticsSection
        health={health}
        viewModel={buildMLHealthViewModel(health)}
      />
    )

    const performance = screen.getByRole('tab', { name: 'Performance' })
    const monitoring = screen.getByRole('tab', { name: 'Monitoring' })
    const policy = screen.getByRole('tab', { name: 'Policy' })

    expect(performance).toHaveAttribute('tabindex', '0')
    expect(monitoring).toHaveAttribute('tabindex', '-1')

    performance.focus()
    fireEvent.keyDown(performance, { key: 'ArrowRight' })

    expect(monitoring).toHaveAttribute('aria-selected', 'true')
    expect(monitoring).toHaveAttribute('tabindex', '0')
    expect(document.activeElement).toBe(monitoring)

    fireEvent.keyDown(monitoring, { key: 'End' })

    expect(policy).toHaveAttribute('aria-selected', 'true')
    expect(document.activeElement).toBe(policy)
  })
})
