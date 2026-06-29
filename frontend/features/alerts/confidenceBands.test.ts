import { describe, expect, it } from 'vitest'

import { countAlertsByConfidenceTier } from './confidenceBands'
import type { AlertAction, AlertConfidenceTier, AlertPrediction } from './contract'

type FixtureAlert = {
  prediction: AlertPrediction
  confidence: number
  confidence_level: AlertConfidenceTier
  action_taken: AlertAction
}

const alerts: FixtureAlert[] = [
  { prediction: 'Normal', confidence: 0.99, confidence_level: 'CRITICAL', action_taken: 'ALLOWED' },
  { prediction: 'SQL Injection', confidence: 0.99, confidence_level: 'CRITICAL', action_taken: 'BLOCKED' },
  { prediction: 'Normal', confidence: 0.85, confidence_level: 'HIGH', action_taken: 'ALLOWED' },
  { prediction: 'SQL Injection', confidence: 0.7, confidence_level: 'MEDIUM', action_taken: 'THROTTLED' },
  { prediction: 'Code Injection', confidence: 0.3, confidence_level: 'LOW', action_taken: 'ALLOWED' },
  { prediction: 'SQL Injection', confidence: 0.95, confidence_level: 'MEDIUM', action_taken: 'THROTTLED' },
]

describe('countAlertsByConfidenceTier', () => {
  it('counts all persisted alerts by backend-emitted confidence_level', () => {
    expect(countAlertsByConfidenceTier(alerts)).toEqual({
      critical: 2,
      high: 1,
      medium: 2,
      low: 1,
    })
  })

  it('excludes Normal predictions from non-Normal enforcement counts', () => {
    expect(countAlertsByConfidenceTier(alerts, { nonNormalOnly: true })).toEqual({
      critical: 1,
      high: 0,
      medium: 2,
      low: 1,
    })
  })

  it('returns every tier with zero counts for an empty alert set', () => {
    expect(countAlertsByConfidenceTier([])).toEqual({
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    })
  })
})
