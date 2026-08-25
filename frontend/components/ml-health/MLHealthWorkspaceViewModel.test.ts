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
    expect(bands[0]).toMatchObject({ label: 'Low', action: 'allow', rangeLabel: '< 40%' })
    expect(bands[1]).toMatchObject({ label: 'Medium', action: 'throttle', rangeLabel: '40% – ≤ 70%' })
    expect(bands[2]).toMatchObject({ label: 'High', action: 'block', rangeLabel: '> 70% – < 85%' })
    expect(bands[3]).toMatchObject({ label: 'Critical', action: 'block', rangeLabel: '≥ 85%' })
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
    expect(viewModel.calibrationSummary).toBe('Expected calibration error was not reported in this snapshot.')
    expect(viewModel.monitoringStatusLabel).toBe('Incomplete')
    expect(viewModel.monitoringUnavailableCount).toBe(1)
  })

  it('does not turn reported evaluation metrics into invented health judgments', () => {
    const viewModel = buildMLHealthViewModel(baseHealth)

    expect(viewModel.calibrationSummary).toBe(
      'Expected calibration error was reported; no acceptance threshold was provided.'
    )
    expect(viewModel.classMetrics).toEqual([
      { label: 'SQL Injection', f1Display: '0.900' },
      { label: 'XSS', f1Display: '0.840' },
    ])
  })

  it('does not present zero traffic latency as a measured result', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      latency_ms: 0,
      traffic_processed: 0,
    })

    expect(viewModel.latencyDisplay).toBe('Not available')
    expect(viewModel.latencyTrendDisplay).toBe('No previous latency available')
    expect(viewModel.hasTraffic).toBe(false)
    expect(viewModel.servingStatusDetail).toMatch(/no serving traffic/i)
  })

  it('explains when prediction counts have no reported baseline', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      prediction_distribution: {
        baseline: {},
        current: { Normal: 12 },
      },
    })

    expect(viewModel.evaluationEvidenceSummary).toBe('Reported evaluation metrics are included in this snapshot.')
    expect(viewModel.distributionSummary).toBe(
      'Current prediction counts are available; no reference baseline was supplied, so comparison is unavailable.'
    )
    expect(viewModel.distributionHasBaseline).toBe(false)
    expect(viewModel.distributionRows).toEqual([
      { label: 'Normal', baselineDisplay: null, currentDisplay: '12', deltaDisplay: null },
    ])
  })

  it('separates BFF retrieval time from source freshness and evaluation provenance', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      retrieved_at: '2026-08-25T06:30:00Z',
    })

    expect(viewModel.retrievedAtDisplay).toBe('Aug 25, 2026, 6:30 AM UTC')
    expect(viewModel.sourceFreshnessDisplay).toBe('Source timestamp unavailable')
    expect(viewModel.evaluationProvenanceDisplay).toBe(
      'Evaluation run identity and timestamp were not provided.'
    )
  })

  it('does not claim that missing evaluation fields mean the model was evaluated', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      macro_f1: null,
      ece: null,
      per_class_f1: {},
      calibration_bins: [],
      prediction_distribution: undefined,
    })

    expect(viewModel.evaluationEvidenceSummary).toBe('No evaluation metrics were reported in this snapshot.')
    expect(viewModel.evaluationProvenanceDisplay).toBe('No evaluation provenance was provided.')
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
    expect(bands.map((band) => band.label)).toEqual(['Low', 'Medium', 'High', 'Critical'])
  })

  it('orders known prediction classes for an operator-readable comparison', () => {
    const viewModel = buildMLHealthViewModel({
      ...baseHealth,
      prediction_distribution: {
        baseline: { 'Other Attacks': 2, 'SQL Injection': 20, Normal: 80 },
        current: { 'Other Attacks': 3, 'SQL Injection': 24, Normal: 76 },
      },
    })

    expect(viewModel.distributionRows.map((row) => row.label)).toEqual([
      'Normal',
      'SQL Injection',
      'Other Attacks',
    ])
    expect(viewModel.distributionHasBaseline).toBe(true)
  })

  it('does not expose guessed deployment or parameter metadata', () => {
    const viewModel = buildMLHealthViewModel(baseHealth)

    expect('deployedAt' in viewModel).toBe(false)
    expect('paramCount' in viewModel).toBe(false)
  })
})
