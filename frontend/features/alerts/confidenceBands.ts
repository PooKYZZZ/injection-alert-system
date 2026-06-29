import type { AlertConfidenceTier, AlertPrediction } from './contract'

export type ConfidenceBandCounts = {
  critical: number
  high: number
  medium: number
  low: number
}

type CountableAlert = {
  prediction: AlertPrediction
  confidence_level: AlertConfidenceTier
}

export function emptyConfidenceBandCounts(): ConfidenceBandCounts {
  return { critical: 0, high: 0, medium: 0, low: 0 }
}

export function countAlertsByConfidenceTier(
  alerts: readonly CountableAlert[],
  options: { nonNormalOnly?: boolean } = {}
): ConfidenceBandCounts {
  const counts = emptyConfidenceBandCounts()

  for (const alert of alerts) {
    if (options.nonNormalOnly && alert.prediction === 'Normal') continue

    switch (alert.confidence_level) {
      case 'CRITICAL':
        counts.critical += 1
        break
      case 'HIGH':
        counts.high += 1
        break
      case 'MEDIUM':
        counts.medium += 1
        break
      case 'LOW':
        counts.low += 1
        break
    }
  }

  return counts
}
