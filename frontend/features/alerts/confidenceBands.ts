import {
  isActionableAttackClass,
  type AlertConfidenceTier,
  type AlertPrediction,
} from './contract'
import type { ConfidenceBandCounts } from '@/features/stats/types'

export type { ConfidenceBandCounts } from '@/features/stats/types'

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
    if (options.nonNormalOnly && !isActionableAttackClass(alert.prediction)) continue

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
