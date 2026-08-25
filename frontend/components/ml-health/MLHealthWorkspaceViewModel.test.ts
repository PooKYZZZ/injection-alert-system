import { describe, expect, it } from 'vitest'

import { buildMLHealthViewModel, buildPolicyBands, deriveHealthTone } from './MLHealthWorkspaceViewModel'
import type { MLHealthData } from '@/features/ml-health/types'

const baseHealth: MLHealthData = {
  model_version: 'distilbert_cleaned_120k_20260324',
  status: 'HEALTHY',
  latency_ms: 32.5,
  latency_trend: null,
  drift_score: 0.034,
  drift_status: 'NORMAL',
  traffic_processed: 1440,
  thresholds: {
    low: 0.5,
    medium: 0.65,
    high: 0.8,
    critical: 0.9,
  },
  macro_f1: 0.91,
  ece: 0.04,
  per_class_f1: {
    'SQL Injection': 0.9,
    XSS: 0.84,
  },
  calibration_bins: [],
  prediction_distribution: {
    baseline: {
      'SQL Injection': 20,
      Normal: 80,
    },
    current: {
      'SQL Injection': 24,
      Normal: 76,
    },
  },
}

describe('MLHealthWorkspace.view-model', () => {
  it('derives warning tone when serving is degraded or drift warning is reported', () => {
    expect(deriveHealthTone({ ...baseHealth, status: 'DEGRADED' })).toBe('warning')
    expect(deriveHealthTone({ ...baseHealth, drift_status: 'WARNING' })).toBe('warning')
  })

  it('builds policy bands from configured thresholds', () => {
    const health = {
      ...baseHealth,
      thresholds: { low: 0.4, medium: 0.55, high: 0.7, critical: 0.85 },
    }
    const bands = buildPolicyBands(health)

    expect(bands).toHaveLength(4)
    expect(bands[0]).toMatchObject({ label: 'Low confidence non-Normal', action: 'allow', rangeLabel: '<40%' })
    expect(bands[1]).toMatchObject({ label: 'Medium confidence non-Normal', action: 'throttle', rangeLabel: '40%-70%' })
    expect(bands[2]).toMatchObject({ label: 'High confidence non-Normal', action: 'block', rangeLabel: '>70%-<85%' })
    expect(bands[3]).toMatchObject({ label: 'Critical confidence non-Normal', action: 'block', rangeLabel: '>=85%' })
    expect(buildMLHealthViewModel(health).normalPolicyException).toBe(
      'Normal predictions remain allowed for all valid confidence tiers.'
    )
  })

  it('uses explicit fallback text when drift score and calibration error are missing', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      drift_score: null,
      ece: null,
      calibration_bins: [],
    })

    expect(viewModel.driftScoreDisplay).toBe('Not reported')
    expect(viewModel.eceDisplay).toBe('Not reported')
    expect(viewModel.calibrationSummary).toBe('Expected calibration error not reported in this snapshot.')
  })

  it('does not present zero traffic latency as a measured result', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      latency_ms: 0,
      traffic_processed: 0,
    })

    expect(viewModel.latencyDisplay).toBe('Not measured')
  })

  it('explains when prediction counts have no reported baseline', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      prediction_distribution: {
        baseline: {},
        current: { Normal: 12 },
      },
    })

    expect(viewModel.evaluationEvidenceSummary).toBe(
      'Reported evaluation evidence is separate from current traffic quality.'
    )
    expect(viewModel.distributionSummary).toBe(
      'Current prediction counts are reported; no reference baseline was supplied.'
    )
  })

  it('marks policy ranges as not configured when thresholds are missing', () => {
    const bands = buildPolicyBands({
      ...baseHealth,
      thresholds: {
        low: null,
        medium: null,
        high: null,
        critical: null,
      },
    })

    expect(bands[0]?.rangeLabel).toBe('Not configured')
    expect(bands[1]?.rangeLabel).toBe('Not configured')
    expect(bands[2]?.rangeLabel).toBe('Not configured')
    expect(bands[3]?.rangeLabel).toBe('Not configured')
    expect(bands.every((band) => band.label.includes('non-Normal'))).toBe(true)
  })

  it('does not expose guessed deployment or parameter metadata', () => {
    const viewModel = buildMLHealthViewModel(baseHealth)

    expect('deployedAt' in viewModel).toBe(false)
    expect('paramCount' in viewModel).toBe(false)
  })
})
